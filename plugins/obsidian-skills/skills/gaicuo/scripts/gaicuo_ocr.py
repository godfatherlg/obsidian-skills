#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""gaicuo 手写答案 OCR 转写。

主流程(2026-10-10 广哥定, 纠正后口径; 2026-10-18 增自检):
  1. 优先走智谱 GLM-4V-Flash(免费多模态): 喂参考答案当词表, 看不清的字直接按答案靠拢写。
  2. GLM 响应慢/失败(超时、限流、网络错、无 key) -> 自动回退本机 PaddleOCR(GPU, 本地, 不联网)。
  3. 静默复述防护(2026-10-18): GLM 有时不看图、直接复述参考答案(只查非空即成功会漏判),
     输出与 ref 高度相似时用本机 PaddleOCR 对拍: 图片内容与输出不符才判复述、采用 PaddleOCR;
     两路一致说明作者工整默写, GLM 输出可信(防误杀)。
  4. PaddleOCR 只出纯转写; 语义纠错由"当前对话模型"在核对时做, 沿用 GLM 那套纠错逻辑——喂参考答案当词表,
     先对着答案猜这个字像什么、往答案靠拢, 实在猜不到再按正常语言先验正常猜, 补漏字/改错字, 脚本不再调 GLM
     (兜底场景 GLM 往往也不可用, 再调纯文本也是白调)。

用法:
  python gaicuo_ocr.py <图片路径> --ref <答案md路径> --refline N,M   # 标准: GLM 喂答案
  python gaicuo_ocr.py <图片路径> --no-glm                          # 强制走 PaddleOCR
  python gaicuo_ocr.py <图片路径> --dir cw                           # 顺时针旋转一版(方向歪才加)

输出: stdout 打印纯文本转写, 供 AI 读取后做批改核对。
环境: ZHIPUAI_API_KEY(本机已配), 回退 ZHIPU_API_KEY; 无 key 直接走 PaddleOCR。
      本机兜底 PaddleOCR 装在独立 venv envs/paddle(PP-OCRv6 模型已缓存, GPU 推理)。
"""
import base64
import io
import json
import os
import sys
import time
import urllib.error
import urllib.request

from PIL import Image

ENDPOINT = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
MODEL = "glm-4v-flash"
GLM_TIMEOUT = 60  # 秒; 2026-10-18 由 45 上调: 实测 1600px 密字大图 24.3s, 留一倍余量
GLM_MAX_RETRY = 3     # 429 限流退避重试次数(3/6/9s), 与 ocr_pdf_text.py 对齐
REF_ECHO_RATIO = 0.85    # 输出与参考答案相似度阈值: 达此值进对拍(不直接判死)
REF_ECHO_MIN_RUN = 15    # 或最长公共子串达此字数进对拍
ECHO_CROSS_RATIO = 0.5   # 对拍: PaddleOCR 与 GLM 输出相似度低于此值 -> 判"没看图复述"
MAX_SIDE = 1600  # 长边超此值等比缩小, 控 base64 体积(智谱单图有大小限制)

PROMPT_NO_REF = (
    "你是手写体 OCR 转写引擎。逐字转写图片里的手写中文答案。\n"
    "规则:\n"
    "1. 保留原序号(如 ①②③④、(1)(2) 等)与分点结构、换行顺序。\n"
    "2. 数学公式用普通文本近似(如 x^2、√x、∫_a^b、分数写 a/b)。\n"
    "3. 看不清、拿不准的字一律写 X(?)，严禁瞎猜。\n"
    "4. 只输出转写文本本身，不要任何解释、前缀、后缀、代码块。"
)

PROMPT_REF = (
    "你是手写体 OCR 转写引擎。逐字转写图片里的手写中文答案。\n"
    "规则:\n"
    "1. 保留原序号(如 ①②③④、(1)(2) 等)与分点结构、换行顺序。\n"
    "2. 数学公式用普通文本近似(如 x^2、√x、∫_a^b、分数写 a/b)。\n"
    "3. 图里看不清、拿不准的字: 一律按文末参考答案里对应的词直接写(作者照答案背写, 答案就是真源), "
    "不要标 X(?)。\n"
    "4. 图里明显整句没写的, 不要凭答案凭空补句子; 只补个别认不清的字。\n"
    "5. 只输出转写文本本身，不要任何解释、前缀、后缀、代码块。\n"
    "\n参考答案原文(作者照此背诵默写, 只作认字真源, 不是图片内容):\n"
)


def _api_key():
    return os.environ.get("ZHIPUAI_API_KEY") or os.environ.get("ZHIPU_API_KEY") or ""


def _load_env():
    """Inject ~/.workbuddy/.env into os.environ if present (best-effort).
    2026-10-18 增加, 与 ocr_pdf_text.py 对齐: 堵住"换入口无 key、一次 API 都不发
    直接静默走 PaddleOCR"的坑。"""
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


def _similarity(a, b):
    """两段文本相似度 0~1(difflib ratio); 任一为空返回 0。"""
    import difflib
    if not a or not b:
        return 0.0
    return difflib.SequenceMatcher(None, a, b, autojunk=False).ratio()


def _looks_like_ref_echo(text, ref_text):
    """初筛: GLM 输出是否"没干活"——空转/纯 X(?)/疑似复述参考答案。

    2026-10-18 针对 GLM 静默复述参考答案增加(该现象不报错不回退, 旧逻辑只查
    非空即成功, 完全漏判)。判据(满足其一进对拍, 不直接判死):
      1. 输出与 ref 整体相似度 >= REF_ECHO_RATIO;
      2. 输出与 ref 的最长公共子串 >= REF_ECHO_MIN_RUN 字。
    无 ref 时: 输出为空、或 X(?) 占比过高(约占三分之一篇幅)视为空转。
    注意: 触发本函数只代表"像背答案", 最终判死由调用方用 PaddleOCR 对拍——
    作者工整默写时输出也会像 ref, 但图片内容与输出一致, 对拍能放行(防误杀)。
    """
    if not text:
        return True
    if not ref_text:
        body = text.replace("X(?)", "").replace(" ", "").replace("\n", "")
        return (not body) or (text.count("X(?)") * 3 >= len(text))
    if _similarity(text, ref_text) >= REF_ECHO_RATIO:
        return True
    import difflib
    sm = difflib.SequenceMatcher(None, text, ref_text, autojunk=False)
    m = sm.find_longest_match(0, len(text), 0, len(ref_text))
    return m.size >= REF_ECHO_MIN_RUN


def _to_b64_jpeg(im):
    # 等比压缩到安全尺寸, JPEG 质量 85
    w, h = im.size
    m = max(w, h)
    if m > MAX_SIDE:
        r = MAX_SIDE / m
        im = im.resize((int(w * r), int(h * r)), Image.LANCZOS)
    buf = io.BytesIO()
    im.convert("RGB").save(buf, "JPEG", quality=85)
    return base64.b64encode(buf.getvalue()).decode()


def _call(payload, key):
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        ENDPOINT,
        data=data,
        headers={
            "Authorization": "Bearer " + key,
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=GLM_TIMEOUT) as r:
        return json.loads(r.read().decode())


def _load_ref(argv):
    # --ref <路径> [--refline N,M]: 只喂该题几行, 防超上下文
    if "--ref" not in argv:
        return ""
    rp = argv[argv.index("--ref") + 1]
    if not os.path.exists(rp):
        print("ERR: --ref 文件不存在: " + rp)
        sys.exit(1)
    with open(rp, "r", encoding="utf-8") as f:
        lines = f.readlines()
    seg = lines
    if "--refline" in argv:
        a, b = [int(x) for x in argv[argv.index("--refline") + 1].split(",")]
        seg = lines[max(0, a - 1):b]
    return "".join(seg).strip()


def _run_glm(im, ref_text, key):
    """GLM 转写: 成功返回文本, 慢/失败返回 None(交给 PaddleOCR 兜底)。"""
    prompt = PROMPT_REF if ref_text else PROMPT_NO_REF
    if ref_text:
        prompt = PROMPT_REF + ref_text
    b64 = _to_b64_jpeg(im)
    payload = {
        "model": MODEL,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64," + b64}},
                    {"type": "text", "text": prompt},
                ],
            }
        ],
    }
    # 429 限流退避重试(3 次, 3/6/9s); 其余(超时/网络错/其他)一律不回磨, 交 PaddleOCR
    for attempt in range(GLM_MAX_RETRY):
        try:
            resp = _call(payload, key)
            return resp["choices"][0]["message"]["content"].strip()
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < GLM_MAX_RETRY - 1:
                time.sleep(3 * (attempt + 1))
                continue
            return None
        except Exception:  # noqa: BLE001 超时/网络错 -> 慢, 回退
            return None
    return None


def _run_paddleocr(im):
    """本机 PaddleOCR 兜底(GPU, 本地; 首次需联网下载 PP-OCRv6 模型, 之后走 ~/.paddlex 缓存)。"""
    import os
    import numpy as np
    from paddleocr import PaddleOCR
    # 跳过模型源连接检查(兜底场景可能网络不好, 别卡在连通性探测)
    os.environ.setdefault("PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK", "True")
    ocr = PaddleOCR(
        use_doc_orientation_classify=False,
        use_doc_unwarping=False,
        use_textline_orientation=False,
        lang="ch",
    )
    arr = np.array(im.convert("RGB"))
    result = ocr.predict(arr)
    lines = []
    for res in result:
        lines.extend(res["rec_texts"])
    return "\n".join(lines)


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    _load_env()
    p = sys.argv[1]
    ref_text = _load_ref(sys.argv)

    im = Image.open(p)

    # 只旋转一版: --dir cw 顺时针 / ccw 逆时针
    if "--dir" in sys.argv:
        d = sys.argv[sys.argv.index("--dir") + 1]
        deg = -90 if d == "cw" else 90 if d == "ccw" else None
        if deg is None:
            print("--dir 只接受 cw 或 ccw")
            sys.exit(1)
        im = im.rotate(deg, expand=True)

    key = _api_key()
    use_paddleocr = "--no-glm" in sys.argv or not key

    if not use_paddleocr:
        text = _run_glm(im, ref_text, key)
        if text and not _looks_like_ref_echo(text, ref_text):
            print(text)
            return
        if text:
            # 自检触发(2026-10-18): 空转/纯 X(?)/疑似复述参考答案
            if not ref_text:
                print("(GLM 空转或大量 X(?), 回退本机 PaddleOCR)", file=sys.stderr)
            else:
                # 有 ref: 疑似背答案 -> PaddleOCR 对拍, 防误杀"作者工整默写"
                print("(GLM 输出与参考答案高度相似, 疑似未看图复述, 转 PaddleOCR 对拍)", file=sys.stderr)
                try:
                    paddle_text = _run_paddleocr(im)
                except Exception as e:  # noqa: BLE001
                    print("ERR: PaddleOCR 对拍失败 " + str(e), file=sys.stderr)
                    paddle_text = ""
                if paddle_text and _similarity(text, paddle_text) >= ECHO_CROSS_RATIO:
                    print("(对拍一致: 作者工整默写, 采用 GLM 转写)", file=sys.stderr)
                    print(text)
                    return
                if paddle_text:
                    print("(对拍不符: 判定 GLM 复述, 采用 PaddleOCR 转写)", file=sys.stderr)
                    print(paddle_text)
                    return
                print("ERR: PaddleOCR 无输出, 保留 GLM 结果供人工核对", file=sys.stderr)
                print(text)
                return
        else:
            print("(GLM 慢/失败, 回退本机 PaddleOCR)", file=sys.stderr)

    # PaddleOCR 兜底
    try:
        print(_run_paddleocr(im))
    except Exception as e:  # noqa: BLE001
        print("ERR: PaddleOCR 也失败 " + str(e), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
