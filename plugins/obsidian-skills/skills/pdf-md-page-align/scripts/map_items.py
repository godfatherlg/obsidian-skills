# -*- coding: utf-8 -*-
"""把 md 条目按章节窗口对齐到 PDF 页码，输出映射表供人工复核。"""
import re, sys, math, json
from collections import defaultdict

MD = sys.argv[1]
PDFTXT = sys.argv[2]
OUT = sys.argv[3]
CFG = json.load(open(sys.argv[4], encoding='utf-8'))  # {"windows":[[heading,start,end],...],"overrides":{"lineno":page}}

# ---- parse pdf ----
pages = {}
cur = None
buf = []
for line in open(PDFTXT, encoding='utf-8'):
    m = re.match(r'=====\s*PAGE\s+(\d+)\s*=====', line.strip())
    if m:
        if cur is not None:
            pages[cur] = ''.join(buf)
        cur = int(m.group(1)); buf = []
    else:
        buf.append(line)
if cur is not None:
    pages[cur] = ''.join(buf)

def bigrams(text):
    s = re.sub(r'[^一-鿿]', '', text)
    return {s[i:i+2] for i in range(len(s)-1)}

pg_bi = {p: bigrams(t) for p, t in pages.items()}
N = len(pages)
df = defaultdict(int)
for b in pg_bi.values():
    for w in b:
        df[w] += 1
idf = {w: math.log(N / (1 + c)) + 1.0 for w, c in df.items()}

# ---- parse md ----
lines = open(MD, encoding='utf-8').read().split('\n')
win_cfg = CFG['windows']
overrides = {int(k): v for k, v in CFG.get('overrides', {}).items()}

cur_sec = None
win = (1, max(pages))
results = []
for i, line in enumerate(lines, 1):
    h = re.match(r'^(#{1,6})\s*(.+?)\s*$', line)
    if h:
        cur_sec = h.group(2)
        if len(h.group(1)) <= 2:
            for key, a, b in win_cfg:
                if key in cur_sec:
                    win = (a, b); break
            else:
                win = (1, max(pages))
        continue
    m = re.match(r'^(\d+)\.\s+(.*)$', line)
    if not m:
        continue
    text = re.sub(r'\[\[[^\]]*\]\]', '', m.group(2))
    ib = bigrams(text)
    if not ib:
        continue
    if i in overrides:
        results.append((i, overrides[i], 999, 'OVR', text[:60]))
        continue
    best, bs, second = None, -1, -1
    for p in range(win[0], win[1] + 1):
        if p not in pg_bi:
            continue
        sc = sum(idf.get(w, 1.0) for w in ib if w in pg_bi[p]) / len(ib)
        if sc > bs:
            second = bs; bs = sc; best = p
        elif sc > second:
            second = sc
    results.append((i, best, round(bs, 2), 'LOW' if bs - second < 0.15 else '', text[:70]))

with open(OUT, 'w', encoding='utf-8') as f:
    for i, p, sc, flag, t in results:
        f.write(f'{i}\t{p}\t{sc}\t{flag}\t{t}\n')
print('items:', len(results))
low = [r for r in results if r[3] == 'LOW']
print('low-confidence:', len(low))
for r in low:
    print(r)
