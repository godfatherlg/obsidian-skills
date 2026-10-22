# -*- coding: utf-8 -*-
"""把 323 题按讲解顺序对齐到 SRT 秒数."""
import re, json, sys

D = r"~\.workbuddy\tmp\k1"
srt = open(D + r"\srt.txt", encoding="utf-8").read().splitlines()
lines = []
for ln in srt:
    m = re.match(r"\[(\d+)\]\s*(.*)", ln)
    if m:
        lines.append((int(m.group(1)), m.group(2).strip()))
MAXT = max(t for t, _ in lines)
bucket = {}
for t, s in lines:
    bucket.setdefault(t, []).append(s)
full = "".join(s for _, s in lines)


def win(lo, hi):
    out = []
    for t in range(max(0, lo), min(MAXT, hi) + 1):
        if t in bucket:
            out.append("".join(bucket[t]))
    return "".join(out)

items = json.load(open(D + r"\items.json", encoding="utf-8"))["items"]

STOP = set("的了是在有和与及对为不这一我你他我们你们他们其之将于被把很也都还就要会能可得着过呢吧啊嘛吗")


def keywords(stem, n=10):
    s = re.sub(r"[^\u4e00-\u9fa5A-Za-z0-9]", "", stem or "")
    grams = {}
    for L in (5, 4, 3, 2):
        for i in range(len(s) - L + 1):
            g = s[i:i + L]
            if any(c in STOP for c in g):
                continue
            if g in grams:
                continue
            c = full.count(g)
            if 1 <= c <= 300:
                grams[g] = L * L
    ks = sorted(grams.items(), key=lambda kv: (-kv[1], -len(kv[0])))[:n]
    return [k for k, _ in ks]


def score(kws, t, half=12):
    w = win(t - half, t + half)
    return sum(len(k) ** 2 for k in kws if k in w)


avg = MAXT / len(items)
prev = 0
result = []
for it in items:
    kws = keywords(it["stem"])
    best_t, best_s, best_raw = None, -1e9, 0
    lo = prev + 3
    hi = min(MAXT, int(prev + 90))
    for t in range(lo, hi + 1, 2):
        s = score(kws, t) - 1.2 * abs(t - (prev + avg))
        if s > best_s:
            best_s, best_t, best_raw = s, t, score(kws, t)
    if best_t is None:
        best_t = min(MAXT, int(prev + avg))
        best_raw = 0
    result.append({"no": it["no"], "sec": best_t, "score": best_raw, "kws": kws[:6]})
    prev = best_t

json.dump(result, open(D + r"\align.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
hit = sum(1 for r in result if r["score"] > 0)
print("总题:", len(result), " 有命中:", hit, " 命中率: %.1f%%" % (100 * hit / len(result)))
print("秒数范围:", result[0]["sec"], result[-1]["sec"], "MAXT", MAXT)
for r in result[:15] + result[150:155] + result[-5:]:
    print(r["no"], r["sec"], r["score"], win(r["sec"] - 6, r["sec"] + 6)[:70])
