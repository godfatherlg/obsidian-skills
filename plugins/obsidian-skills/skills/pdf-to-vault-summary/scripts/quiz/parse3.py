# -*- coding: utf-8 -*-
"""生成 1..323 完整题目数据: 题干(去选项) + 答案 + 解析 + 页码 + SRT秒数(后续填)."""
import re, json

BL = r"~\.workbuddy\tmp\k1\blocks.json"
B = json.load(open(BL, encoding="utf-8"))
qb, ab = B["q"], B["a"]

tips = []
qb2 = []
for q in qb:
    if q.get("tip"):
        tips.append({"page": q["page"], "text": q["text"]})
    else:
        qb2.append(q)

# 题干索引
qmap = {}
for q in qb2:
    if q["no"] is None:
        continue
    qmap.setdefault(q["no"], q)
# 答案索引
amap = {}
loose = []
for a in ab:
    if a["no"] is None:
        loose.append(a)
    else:
        amap[a["no"]] = a
    if a["no"] is not None:
        amap[a["no"]] = a

MAXNO = 323


def split_opts(text):
    m = re.search(r"(?m)^\s*A\s*[\.．、]?\s*", text)
    if not m:
        m = re.search(r"(?<![\u4e00-\u9fa5])A\s*[\.．、](?![\u4e00-\u9fa5]*?[\u3002\uff1b])", text)
    stem = text[:m.start()].strip() if m else text.strip()
    opts = text[m.start():].strip() if m else ""
    ol = []
    for mm in re.finditer(r"(?m)^\s*([ABCD])\s*[\.．、]?\s*([^\n]*)", opts):
        ol.append((mm.group(1), mm.group(2).strip()))
    if not ol:
        for mm in re.finditer(r"([ABCD])\s*[\.．、]\s*([^A-D]*)", opts):
            ol.append((mm.group(1), mm.group(2).strip()))
    return stem, ol


items = []
for no in range(1, MAXNO + 1):
    q = qmap.get(no)
    a = amap.get(no)
    if q is None:
        items.append({"no": no, "page": None, "stem": None, "options": [], "ans": None, "ans_page": None, "analysis": None})
        continue
    stem, ol = split_opts(q["text"])
    stem = re.sub(r"\s+", "", stem)
    it = {"no": no, "page": q["page"], "stem": stem, "options": [list(o) for o in ol],
          "ans": None, "ans_page": None, "analysis": None}
    if a:
        it["ans"] = a["ans"]
        it["ans_page"] = a["page"]
        an = re.sub(r"【答案】\s*[ABCD]?[。．]?\s*", "", a["text"], count=1)
        an = re.sub(r"^答案[:：]\s*[ABCD]?\s*", "", an, count=1)
        it["analysis"] = an.strip()
    items.append(it)

# 松散答案块按页序分配给尚缺答案的题
pending = [it for it in items if it["stem"] and not it["ans"]]
li = 0
for it in pending:
    while li < len(loose) and loose[li]["page"] <= it["page"]:
        li += 1
    if li < len(loose):
        a = loose[li]
        m = re.search(r"答案[:：]?\s*([ABCD])", a["text"]) or re.search(r"【答案】\s*([ABCD])", a["text"])
        it["ans"] = m.group(1) if m else None
        it["ans_page"] = a["page"]
        an = re.sub(r"^【答案】\s*[ABCD]?\s*", "", a["text"], count=1)
        an = re.sub(r"^答案[:：]\s*[ABCD]?\s*", "", an, count=1)
        it["analysis"] = an.strip()
        li += 1

missing_stem = [i["no"] for i in items if not i["stem"]]
missing_ans = [i["no"] for i in items if not i["ans"]]
print("总数:", len(items))
print("缺题干:", missing_stem)
print("缺答案:", missing_ans)
print("技巧块:", len(tips))
json.dump({"items": items, "tips": tips}, open(r"~\.workbuddy\tmp\k1\items.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
for i in items[:3]:
    print(i["no"], i["page"], i["ans"], i["stem"][:60] if i["stem"] else None)
