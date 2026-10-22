import re, io, sys, shutil, datetime

def fix_missing(lines):
    """items without pdf#page= inherit the page of nearest item in same ## block"""
    blocks = []          # list of (start,end) item index ranges per ## block
    cur = []
    out_blocks = []
    for ln in lines:
        if ln.startswith('#'):
            if cur:
                out_blocks.append(cur)
            cur = []
            continue
        if re.match(r'^\d+\. ', ln):
            cur.append(ln)
    if cur:
        out_blocks.append(cur)

    fixed = {}
    for bl in out_blocks:
        pages = [int(re.search(r'pdf#page=(\d+)', x).group(1))
                 for x in bl if re.search(r'pdf#page=(\d+)', x)]
        if not pages:
            continue
        for x in bl:
            if not re.search(r'pdf#page=(\d+)', x):
                fixed[x] = pages[0]
    return fixed


def flatten(path, backup_dir):
    raw = io.open(path, encoding='utf-8').read()
    lines = raw.split('\n')
    fixed = fix_missing(lines)

    h1 = None
    items = []
    for ln in lines:
        if h1 is None and ln.startswith('# '):
            h1 = ln
            continue
        if ln.startswith('#'):
            continue
        m = re.match(r'^\d+\. (.*)$', ln)
        if not m:
            continue
        body = m.group(1)
        if ln in fixed:
            pdfname = re.search(r'([^\[\]|/\\]+\.pdf)', raw)
            body = body.rstrip() + ' [[' + pdfname.group(1) + '#page=' + str(fixed[ln]) + '|pdf]]'
        p = re.search(r'pdf#page=(\d+)', body)
        items.append((int(p.group(1)) if p else 9999, body))

    items.sort(key=lambda t: t[0])   # stable
    out = [h1] + [f'{i}. {b}' for i, (_, b) in enumerate(items, 1)]
    txt = '\n'.join(out) + '\n'

    if backup_dir:
        import os
        name = os.path.basename(path)
        stamp = datetime.datetime.now().strftime('%Y%m%d-%H%M')
        shutil.copy2(path, os.path.join(backup_dir, name + '.bak-' + stamp))
    io.open(path, 'w', encoding='utf-8', newline='\n').write(txt)
    print(f'{path}: {len(items)} items, pages {items[0][0]}..{items[-1][0]}')
    inv = sum(1 for i in range(len(items)-1) if items[i][0] > items[i+1][0])
    print('  remaining inversions:', inv, '| fixed missing links:', len(fixed))


if __name__ == '__main__':
    bd = sys.argv[1]
    for p in sys.argv[2:]:
        flatten(p, bd)
