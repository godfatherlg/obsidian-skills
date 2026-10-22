# -*- coding: utf-8 -*-
"""生成 最后一遍疯狂刷题-科目一单选题.md"""
import re, json

D = r"~\.workbuddy\tmp\k1"
B = json.load(open(D + r"\blocks.json", encoding="utf-8"))
items = json.load(open(D + r"\items.json", encoding="utf-8"))["items"]
al = {a["no"]: a["sec"] for a in json.load(open(D + r"\align.json", encoding="utf-8"))}

BASE = "最后一遍疯狂刷题-科目一单选题"
PDF = BASE + ".pdf"
MP4 = BASE + ".mp4"

# --- 修正 290 题(OCR 成 390) ---
qmap_raw = {}
for q in B["q"]:
    if q.get("no") is None or q.get("tip"):
        continue
    qmap_raw.setdefault(q["no"], q)
qraw = {no: q["text"] for no, q in qmap_raw.items()}
if 390 in qmap_raw:
    for it in items:
        if it["no"] == 290:
            it["page"] = qmap_raw[390]["page"]
            it["stem"] = re.sub(r"\s+", "", qmap_raw[390]["text"])

# --- 重新配对无题号答案块: page+1 优先, 其次 page+2 ---
loose = [a for a in B["a"] if a["no"] is None]
loose.sort(key=lambda a: a["page"])
used = set()


def clean_ans_text(t):
    t = re.sub(r"^【答案】\s*[ABCD]?\s*", "", t, count=1)
    t = re.sub(r"^答案[:：]\s*[ABCD]?\s*", "", t, count=1)
    return t.strip()


amap = {}
for a in B["a"]:
    if a.get("no") is not None:
        amap.setdefault(a["no"], a)

for it in items:
    if not it["stem"]:
        continue
    # 一律重配: 优先同题号答案块
    a = amap.get(it["no"])
    if a:
        m = re.search(r"【答案】\s*([ABCD])", a["text"]) or re.search(r"答案[:：]\s*([ABCD])", a["text"])
        it["ans"] = m.group(1) if m else None
        it["ans_page"] = a["page"]
        it["analysis"] = clean_ans_text(a["text"])
        continue
    P = it["page"]
    cand = None
    for delta in (1, 2):
        for i, a in enumerate(loose):
            if i in used:
                continue
            if a["page"] == P + delta:
                cand = (i, a)
                break
        if cand:
            break
    if cand:
        i, a = cand
        used.add(i)
        m = re.search(r"答案[:：]?\s*([ABCD])", a["text"]) or re.search(r"【答案】\s*([ABCD])", a["text"])
        it["ans"] = m.group(1) if m else None
        it["ans_page"] = a["page"]
        it["analysis"] = clean_ans_text(a["text"])

FW = {"，": ",", "。": ".", "、": ",", "；": ";", "：": ":", "？": "?", "！": "!",
      "（": "(", "）": ")", "“": '"', "”": '"', "‘": "'", "’": "'", "—": "-",
      "－": "-", "～": "~", "％": "%"}


def halfwidth(s):
    return "".join(FW.get(c, c) for c in s)


def clean(s, keep_space=True):
    if not s:
        return ""
    s = halfwidth(s)
    s = re.sub(r"\s+", " ", s)
    s = re.sub(r"[（(]\s*[）)]", "……", s)
    s = re.sub(r"……\s*[.。]", "……", s)
    s = re.sub(r"[.。]{2,}", "", s)
    s = re.sub(r"\s*([,;.])\s*", r"\1 ", s)
    s = re.sub(r"\s*([:!?])\s*", r"\1", s)
    s = re.sub(r"\s+", " ", s).strip()
    s = re.sub(r"(?<=[\u4e00-\u9fa5])\s+(?=[\u4e00-\u9fa5])", "", s)
    s = re.sub(r"\s+…", "…", s)
    s = re.sub(r"[,;:.]\s*$", "", s)
    return s


def split_options(text):
    """返回 {A:txt, B:txt, ...}"""
    t = text.replace("\n", " ")
    t = re.sub(r"\s*([BCD])\s*[\.．、]\s*", r"\n\1.", t)
    t = re.sub(r"(?m)^\s*A\s*[\.．、]?\s*", "A.", t)
    out = {}
    for m in re.finditer(r"(?m)^\s*([ABCD])\s*[\.．]\s*(.*)$", t):
        out[m.group(1)] = m.group(2).strip()
    if len(out) < 2:
        # fallback: 选项无点号, 形如 "A每日十八时至次日八时B每日二十时..."
        parts = re.split(r"\s*([ABCD])\s*(?=[\u4e00-\u9fa5\d(])", t)
        cand = {}
        for i in range(1, len(parts) - 1, 2):
            cand[parts[i]] = parts[i + 1].strip()
        if len(cand) >= 2:
            out = cand
    return out


def first_sentence(s, limit=70):
    s = re.sub(r"^解析[:：]\s*", "", s)
    s = re.sub(r"^本题考查", "", s)
    return s


tips = json.load(open(D + r"\items.json", encoding="utf-8"))["tips"]
tips = [(t["page"], clean(re.sub(r"^【做题技巧】\s*", "", t["text"]))) for t in tips]
tips = [(p, t) for p, t in tips if t]
tips.sort()
ti = 0

out = []
seq = 0
for it in items:
    if not it["stem"]:
        continue
    seq += 1
    raw = qraw.get(it["no"], it["stem"] or "")
    mopt = re.search(r"(?m)^\s*A\s*[\.．、]?\s*", raw)
    if not mopt:
        mopt = re.search(r"(?<![\u4e00-\u9fa5])A\s*[\.．、]\s*", raw)
    raw_stem = raw[:mopt.start()] if mopt else raw
    raw_opts = raw[mopt.start():] if mopt else ""
    stem = clean(raw_stem)
    stem = re.sub(r"^\s*\d{1,3}\s*[\.．]\s*", "", stem)
    if len(stem) > 130:
        stem = re.sub(r"[,;:.]\s*$", "", stem[:126]) + "..."
    opts = split_options(raw_opts)
    ans = it["ans"]
    piece = ""
    if ans and ans in opts:
        ot = clean(opts[ans])
        ot = re.sub(r"[.。,;:]\s*$", "", ot)
        if len(ot) > 34:
            ot = re.sub(r"[,;:.]\s*$", "", ot[:33]) + "..."
        if len(ot) > 22:
            pre = ot.split(", ")[0]
            if len(pre) < len(ot) - 4 and len(pre) <= 16:
                piece = "选%s (**%s**, %s)" % (ans.lower(), pre, ot[len(pre) + 2:])
            else:
                piece = "选%s (%s)" % (ans.lower(), ot)
        else:
            piece = "选%s (**%s**)" % (ans.lower(), ot) if ot else "选%s" % ans.lower()
    elif ans:
        piece = "选%s" % ans.lower()
    # 技巧并入(消费式, 只挂一次)
    tp = []
    P = it["page"] or 0
    while ti < len(tips) and tips[ti][0] <= P:
        tp.append(tips[ti][1])
        ti += 1
    tip_txt = ""
    if tp:
        tip_txt = "做题技巧: " + "; ".join(tp)
        tip_txt = re.sub(r"[.。,;:]\s*$", "", tip_txt)
    text = stem
    if piece:
        text += ", " + piece
    if tip_txt:
        text += ". " + tip_txt
    text = re.sub(r"[.。,;:]\s*$", "", text) + "."
    page = it["page"]
    sec = al.get(it["no"], 0)
    line = "%d. %s [[%s#page=%d|pdf]] [[%s#t=%d|视频]]" % (seq, text, PDF, page, MP4, sec)
    out.append(line)

md = "# 𒋙最后一遍疯狂刷题-科目一单选题\n" + "\n".join(out) + "\n"
open(r"<vault>\2026上数学教资\冲刺班\科一\最后一遍疯狂刷题-科目一单选题.md", "w", encoding="utf-8").write(md)
print("条数:", len(out))
print("缺答案:", sum(1 for l in out if "选" not in l))
