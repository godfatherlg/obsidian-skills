import re, sys, io, math
from collections import Counter

def bigrams(s):
    s = re.sub(r'\s+', '', s)
    s = re.sub(r'[^\u4e00-\u9fff]', '', s)
    return [s[i:i+2] for i in range(len(s)-1)]

def load_pdf(path):
    txt = io.open(path, encoding='utf-8').read()
    parts = re.split(r'===== PAGE (\d+) =====', txt)
    return [(int(parts[i]), parts[i+1]) for i in range(1, len(parts), 2)]

def build(pages):
    docs = [{'page': pg, 'bg': Counter(bigrams(b))} for pg, b in pages]
    df = Counter()
    for d in docs:
        for k in d['bg']:
            df[k] += 1
    N = len(docs)
    idf = {k: math.log(N / (1 + v)) for k, v in df.items()}
    for d in docs:
        tot = sum(d['bg'].values()) or 1
        d['vec'] = {k: (v / tot) * idf.get(k, 0) for k, v in d['bg'].items()}
        d['norm'] = math.sqrt(sum(x * x for x in d['vec'].values())) or 1
    return docs

def score(doc, qbg):
    qt = sum(qbg.values()) or 1
    qv = {k: v / qt for k, v in qbg.items()}
    return sum(v * doc['vec'][k] for k, v in qv.items() if k in doc['vec']) / doc['norm']

def main(pdf, md, thresh=3):
    docs = build(load_pdf(pdf))
    n = 0
    for ln in io.open(md, encoding='utf-8').read().split('\n'):
        m = re.match(r'^(\d+)\. (.*)$', ln)
        if not m:
            continue
        p = re.search(r'pdf#page=(\d+)', ln)
        assigned = int(p.group(1)) if p else -1
        body = re.sub(r'\[\[[^\]]*\]\]', '', m.group(2))
        qb = Counter(bigrams(body))
        ranked = sorted(docs, key=lambda d: -score(d, qb))
        best = ranked[0]
        n += 1
        if abs(best['page'] - assigned) >= thresh:
            print(f"cur p{assigned:>4} | glob p{best['page']:>4} ({score(best,qb):.4f}) p{ranked[1]['page']}({score(ranked[1],qb):.4f}) | {body[:60]}")
    print('total items', n)

main(sys.argv[1], sys.argv[2])
