# -*- coding: utf-8 -*-
"""按出现顺序切分题目块与答案块, 统计块数以便配对。"""
import re, json

SRC = r"~\.workbuddy\tmp\k1\pdf.txt"
txt = open(SRC, encoding="utf-8").read()
parts = re.split(r"===== PAGE (\d+) =====", txt)
pages = [(int(parts[i]), parts[i + 1]) for i in range(1, len(parts), 2)]

QNUM = r"(?m)^\s*(\d{1,3})\s*[\.．、]\s*"
ANSPAT = re.compile(r"【答案】|^答案[:：]|^\s*答案[:：]|\d{1,3}\s*[\.．]\s*【答案】")

qblocks = []
ablocks = []
for p, body in pages:
    # 去掉做题技巧行单独记录
    tips = [m.group(1).strip() for m in re.finditer(r"(?m)^\s*【做题技巧】\s*(.*)$", body)]
    # 切块: 以行首题号切
    idxs = [m.start() for m in re.finditer(QNUM, body)]
    if not idxs:
        # 整页无题号: 可能是无题号答案页
        if re.search(r"【答案】|答案[:：]|【解析】", body):
            marks = [m.start() for m in re.finditer(r"【答案】|答案[:：]", body)]
            for i, s in enumerate(marks):
                e = marks[i + 1] if i + 1 < len(marks) else len(body)
                seg = body[s:e].strip()
                if len(seg) > 25:
                    ablocks.append({"page": p, "no": None, "text": seg, "ans": None})
        continue
    for i, s in enumerate(idxs):
        e = idxs[i + 1] if i + 1 < len(idxs) else len(body)
        seg = body[s:e].strip()
        m = re.match(QNUM, seg)
        no = int(m.group(1))
        content = seg[m.end():].strip()
        is_ans = bool(re.match(r"\s*(【答案】|答案[:：]|答案\s*[ABCD])", content)) or bool(
            re.search(r"【答案】", content[:30])
        )
        if is_ans:
            mm = re.search(r"【答案】\s*([ABCD])", content) or re.search(r"答案[:：]\s*([ABCD])", content)
            ablocks.append({"page": p, "no": no, "text": content, "ans": mm.group(1) if mm else None})
        elif re.search(r"(?m)^\s*[ABCD]\s*[\.．\s]", content) or re.search(r"[ABCD]\s*[\.．]", content):
            qblocks.append({"page": p, "no": no, "text": content})
        else:
            # 无选项无答案: 多半是题目续页, 归题目
            qblocks.append({"page": p, "no": no, "text": content})
    if tips:
        for t in tips:
            qblocks.append({"page": p, "no": None, "text": "【做题技巧】" + t, "tip": True})

print("题目块:", len(qblocks), " 答案块:", len(ablocks))
qn = [q["no"] for q in qblocks if q["no"]]
an = [a["no"] for a in ablocks if a["no"]]
print("题目块有题号:", len(qn), "答案块有题号:", len(an))
print("题目首末:", qn[:5], qn[-5:])
print("答案首末:", an[:5], an[-5:])
# 题目块题号重复
from collections import Counter
cq = Counter(qn)
print("题目重复题号:", [k for k, v in cq.items() if v > 1][:20])
ca = Counter(an)
print("答案重复题号:", [k for k, v in ca.items() if v > 1][:20])
sq, sa = set(qn), set(an)
print("答案有题目没有:", sorted(sa - sq)[:20])
print("题目有答案没有:", sorted(sq - sa)[:20])
json.dump({"q": qblocks, "a": ablocks}, open(r"~\.workbuddy\tmp\k1\blocks.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
