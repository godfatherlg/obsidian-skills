import re, sys, io

def analyze(path):
    lines = io.open(path, encoding='utf-8').read().split('\n')
    cur_sec = None
    cur_sub = None
    secs = {}   # sec -> {'min':..,'max':..,'items':[(page,line)]}
    order = []
    for ln in lines:
        m2 = re.match(r'^## (.*)$', ln)
        m3 = re.match(r'^### (.*)$', ln)
        m1 = re.match(r'^(\d+)\. (.*)$', ln)
        if m2:
            cur_sec = m2.group(1).strip()
            cur_sub = None
            order.append((cur_sec, None))
            secs.setdefault(cur_sec, {'items': [], 'subs': []})
            continue
        if m3:
            cur_sub = m3.group(1).strip()
            order.append((cur_sec, cur_sub))
            secs[cur_sec]['subs'].append(cur_sub)
            continue
        if m1:
            p = re.search(r'pdf#page=(\d+)', ln)
            pg = int(p.group(1)) if p else -1
            secs[cur_sec]['items'].append((pg, cur_sub, ln))
    print('=== FILE:', path)
    for sec in [k for k, _ in order]:
        d = secs[sec]
        pages = [p for p, _, _ in d['items'] if p > 0]
        main = [p for p, s, _ in d['items'] if s is None and p > 0]
        subs = {}
        for p, s, _ in d['items']:
            if p > 0:
                subs.setdefault(s or '(MAIN)', []).append(p)
        if not pages:
            print(f'{sec}: NO PAGE')
            continue
        flag = ''
        if main and max(main) > min(main) and any(main[i] > main[i+1] for i in range(len(main)-1)):
            flag += ' [MAIN-UNSORTED]'
        print(f'P{min(pages):>4}-{max(pages):>4} n={len(pages):>3} {sec}{flag}')
        if len(subs) > 1:
            for k, v in subs.items():
                print(f'        sub {k}: {min(v)}-{max(v)} n={len(v)}')
    # global check
    print('--- sections in file order (min page) ---')
    mins = []
    for sec in dict.fromkeys([k for k, _ in order]):
        pages = [p for p, _, _ in secs[sec]['items'] if p > 0]
        if pages:
            mins.append((min(pages), sec))
    bad = [i for i in range(len(mins)-1) if mins[i][0] > mins[i+1][0]]
    print('section-order violations:', len(bad))
    for i in bad:
        print('   ', mins[i], '->', mins[i+1])

for p in sys.argv[1:]:
    analyze(p)
    print()
