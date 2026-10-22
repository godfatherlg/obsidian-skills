# -*- coding: utf-8 -*-
"""把 pdf 页链接按映射表注入 md（插在 mp4 链接之前）。先备份。"""
import re, sys, shutil, os

MD = sys.argv[1]
MAP = sys.argv[2]
PDFNAME = os.path.basename(MD)[:-3] + '.pdf'

shutil.copy(MD, MD + '.bak-' + '20260910')
pairs = {}
for line in open(MAP, encoding='utf-8'):
    parts = line.rstrip('\n').split('\t')
    if len(parts) < 2:
        continue
    pairs[int(parts[0])] = int(parts[1])

lines = open(MD, encoding='utf-8').read().split('\n')
n = 0
for i, line in enumerate(lines, 1):
    if i not in pairs:
        continue
    if '.pdf#page=' in line:
        continue
    link = ' [[%s#page=%d|pdf]]' % (PDFNAME, pairs[i])
    m = re.search(r' \[\[[^\]]*mp4#t=', line)
    if m:
        lines[i - 1] = line[:m.start()] + link + line[m.start():]
    else:
        lines[i - 1] = line.rstrip() + link
    n += 1
open(MD, 'w', encoding='utf-8', newline='').write('\n'.join(lines))
print('injected', n, 'of', len(pairs))
