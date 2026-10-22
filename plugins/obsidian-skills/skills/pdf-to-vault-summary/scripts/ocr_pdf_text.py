#!/usr/bin/env python3
"""OCR a (possibly image-only) PDF into text, printing each page as ===== PAGE N ===== blocks.

Rendering: PyMuPDF (fitz) -- no poppler needed.

Engine priority (user rule, 2026-10-08; local fallback -> PaddleOCR 2026-10-11;
per-page failure isolation 2026-10-18):
  1. glm       -- Zhipu GLM-4V-Flash, FREE vision model, best accuracy (needs ZHIPUAI_API_KEY)
  2. tencent   -- handled OUTSIDE this script (see note below): needs the user's Tencent Cloud
                 key + draws down the 1000/month free quota, so it is NEVER auto-triggered.
  3. paddleocr -- offline local fallback (GPU, PP-OCRv6), no key/quota involved.
Pick with --engine glm|paddleocr|auto. Default `auto` = try glm first, then fall back
to PaddleOCR if glm is unavailable (no key / network error / empty result).
2026-10-18: glm 失败不再"一页挂整本挂"——单页失败仅该页转 PaddleOCR 补齐, 其余页
保留 GLM 结果; 连续 3 页失败才判定 glm 整体不可用、整本转 PaddleOCR。

Usage:
    python ocr_pdf_text.py "<PDF_PATH>" [--engine glm|paddleocr|auto]
                            [--dpi 200] [--max N]
"""
import sys
import io
import os
import json
import time
import base64
import urllib.request
import urllib.error

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

# --- Zhipu GLM-4V-Flash (free tier) -----------------------------------------
GLM_ENDPOINT = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
GLM_MODEL = "glm-4v-flash"
GLM_MAX_SIDE = 1600   # shrink long edge so base64 stays small
GLM_MAX_RETRY = 3     # free tier has low concurrency; 429 -> backoff retry
GLM_PROMPT = (
    "You are a printed-document OCR engine. Transcribe ALL visible text on this page.\n"
    "Rules:\n"
    "1. Keep the original reading order, line breaks and any numbering.\n"
    "2. Math formulas as plain text (x^2, sqrt(x), int_a^b, a/b).\n"
    "3. Unreadable characters -> X(?) never guess.\n"
    "4. Output transcription only, no explanation, no code fence."
)

try:
    import pymupdf as fitz  # PyMuPDF (fitz API)
except ImportError:
    try:
        import fitz  # fallback old alias
    except ImportError:
        sys.stderr.write("NEED_PYMUPDF: install PyMuPDF into the managed venv\n")
        sys.exit(2)


def _load_env():
    """Inject ~/.workbuddy/.env into os.environ if present (best-effort)."""
    p = os.path.join(os.path.expanduser("~"), ".workbuddy", ".env")
    if not os.path.exists(p):
        return
    try:
        with open(p, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())
    except Exception:
        pass


def glm_key():
    """Zhipu key if configured, else '' (glm unavailable)."""
    return os.environ.get("ZHIPUAI_API_KEY") or os.environ.get("ZHIPU_API_KEY") or ""


def pick_engine():
    """本地 OCR 引擎(仅作 glm 兜底): 固定返回 paddleocr。
    NOTE (2026-10-07): Tesseract 已卸载; (2026-10-11): 本地兜底已换 PaddleOCR(GPU, PP-OCRv6)。"""
    return "paddleocr"


def render_pages(pdf_path, dpi=200, max_pages=None, max_edge=1600):
    pages = []
    with fitz.open(pdf_path) as doc:
        total = len(doc)
        if max_pages:
            total = min(total, max_pages)
        zoom = dpi / 72.0
        for i in range(total):
            mat = fitz.Matrix(zoom, zoom)
            pix = doc[i].get_pixmap(matrix=mat)
            # shrink very large pages so the base64 upload stays reasonable
            if max(pix.width, pix.height) > max_edge:
                s = max_edge / float(max(pix.width, pix.height))
                mat = fitz.Matrix(zoom * s, zoom * s)
                pix = doc[i].get_pixmap(matrix=mat)
            buf = pix.tobytes("png")
            pages.append((i + 1, buf))
    return pages


def ocr_paddleocr(images):
    import numpy as np
    from PIL import Image
    from paddleocr import PaddleOCR
    os.environ.setdefault("PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK", "True")
    ocr = PaddleOCR(
        use_doc_orientation_classify=False,
        use_doc_unwarping=False,
        use_textline_orientation=False,
        lang="ch",
    )
    out = []
    for pno, buf in images:
        arr = np.array(Image.open(io.BytesIO(buf)).convert("RGB"))
        result = ocr.predict(arr)
        lines = []
        for res in result:
            lines.extend(res["rec_texts"])
        out.append((pno, "\n".join(lines)))
    return out


def ocr_glm(images):
    """Zhipu GLM-4V-Flash, page by page.

    2026-10-18 逐页隔离: 某页失败不再 raise 炸掉整本, 而是记 (pno, None, err),
    由调用方 _fill_failed_pages 对该页跑 PaddleOCR 补齐; 连续 3 页失败才 raise
    RuntimeError(判定 glm 整体不可用, 如 key 失效/断网), 让调用方整本转 PaddleOCR,
    避免逐页空等重试。
    """
    from PIL import Image

    key = glm_key()
    if not key:
        raise RuntimeError("no ZHIPUAI_API_KEY")

    def _b64(buf):
        im = Image.open(io.BytesIO(buf))
        w, h = im.size
        m = max(w, h)
        if m > GLM_MAX_SIDE:
            r = GLM_MAX_SIDE / float(m)
            im = im.resize((int(w * r), int(h * r)), Image.LANCZOS)
        ob = io.BytesIO()
        im.convert("RGB").save(ob, "JPEG", quality=85)
        return base64.b64encode(ob.getvalue()).decode()

    out = []
    consec_fail = 0
    for pno, buf in images:
        payload = {
            "model": GLM_MODEL,
            "messages": [{
                "role": "user",
                "content": [
                    {"type": "image_url",
                     "image_url": {"url": "data:image/jpeg;base64," + _b64(buf)}},
                    {"type": "text", "text": GLM_PROMPT},
                ],
            }],
        }
        data = json.dumps(payload).encode()
        last_err = ""
        txt = ""
        for attempt in range(GLM_MAX_RETRY):
            try:
                req = urllib.request.Request(
                    GLM_ENDPOINT, data=data,
                    headers={"Authorization": "Bearer " + key,
                             "Content-Type": "application/json"},
                    method="POST",
                )
                with urllib.request.urlopen(req, timeout=120) as r:
                    resp = json.loads(r.read().decode())
                txt = (resp["choices"][0]["message"]["content"] or "").strip()
                break
            except urllib.error.HTTPError as e:
                last_err = "HTTP %s %s" % (e.code, e.read().decode()[:200])
                if e.code == 429:
                    time.sleep(3 * (attempt + 1))
                    continue
                break
            except Exception as e:  # noqa: BLE001
                last_err = str(e)
                break
        if not txt:
            consec_fail += 1
            sys.stderr.write("GLM page %d failed (%s) -> 该页转 PaddleOCR\n"
                             % (pno, last_err or "empty response"))
            out.append((pno, None, last_err or "empty response"))
            if consec_fail >= 3:
                raise RuntimeError("glm 连续 %d 页失败, 判定整体不可用" % consec_fail)
        else:
            consec_fail = 0
            out.append((pno, txt, ""))
        time.sleep(0.4)  # free tier has low concurrency; be gentle
    return out


def _fill_failed_pages(results, images):
    """逐页隔离(2026-10-18): GLM 记 None 的页用 PaddleOCR 单页补齐, 其余页保留
    GLM 结果。results 为 ocr_glm 返回的 (pno, txt_or_None, err) 列表;
    返回统一的 (pno, txt) 列表。"""
    failed = [pno for (pno, txt, _err) in results if txt is None]
    if not failed:
        return [(pno, txt) for (pno, txt, _err) in results]
    bufs = dict(images)
    sys.stderr.write("ENGINE: %d 页 GLM 失败, 单页转 PaddleOCR 补齐\n" % len(failed))
    fixed = dict(ocr_paddleocr([(p, bufs[p]) for p in failed]))
    return [(pno, fixed[pno] if txt is None else txt)
            for (pno, txt, _err) in results]


def main():
    if len(sys.argv) < 2:
        sys.stderr.write("usage: ocr_pdf_text.py <PDF_PATH> [--engine ...] [--dpi 200] [--max N]\n")
        sys.exit(1)

    _load_env()

    pdf_path = sys.argv[1]
    engine = "auto"
    dpi = 200
    max_pages = None
    if "--engine" in sys.argv:
        engine = sys.argv[sys.argv.index("--engine") + 1]
    if "--dpi" in sys.argv:
        dpi = int(sys.argv[sys.argv.index("--dpi") + 1])
    if "--max" in sys.argv:
        max_pages = int(sys.argv[sys.argv.index("--max") + 1])

    images = render_pages(pdf_path, dpi=dpi, max_pages=max_pages)

    if engine == "auto":
        # priority per user rule 2026-10-08 (local fallback -> PaddleOCR 2026-10-11;
        # per-page failure isolation 2026-10-18): glm -> local paddleocr
        results = None
        if glm_key():
            sys.stderr.write("ENGINE: auto -> glm (per-page fallback paddleocr)\n")
            try:
                results = ocr_glm(images)
            except Exception as e:  # noqa: BLE001 连续失败/无 key -> 整本兜底
                sys.stderr.write("ENGINE: glm unavailable (%s) -> %s\n" % (e, pick_engine()))
                results = None
        else:
            sys.stderr.write("ENGINE: auto -> no glm key -> %s\n" % pick_engine())
        if results is None:
            results = ocr_paddleocr(images)
        else:
            results = _fill_failed_pages(results, images)
    elif engine == "glm":
        sys.stderr.write("ENGINE: GLM-4V-Flash (per-page fallback paddleocr)\n")
        try:
            results = ocr_glm(images)
        except Exception as e:  # noqa: BLE001 连续失败 -> 整本兜底
            sys.stderr.write("ENGINE: glm unavailable (%s) -> paddleocr 整本\n" % e)
            results = None
        if results is None:
            results = ocr_paddleocr(images)
        else:
            results = _fill_failed_pages(results, images)
    else:
        sys.stderr.write("ENGINE: PaddleOCR\n")
        results = ocr_paddleocr(images)

    for pno, txt in results:
        print("\n===== PAGE %d =====" % pno)
        print(txt)


if __name__ == "__main__":
    main()
