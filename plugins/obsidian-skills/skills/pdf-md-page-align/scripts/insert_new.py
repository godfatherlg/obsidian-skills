# -*- coding: utf-8 -*-
"""按行号插入新增条目（倒序插入，避免位移）。"""
import sys, json

MD = sys.argv[1]
INS = json.load(open(sys.argv[2], encoding='utf-8'))  # [[after_line, ["text",...]], ...]

lines = open(MD, encoding='utf-8').read().split('\n')
for after, texts in sorted(INS, key=lambda x: -int(x[0])):
    idx = int(after)
    lines[idx:idx] = texts
open(MD, 'w', encoding='utf-8', newline='').write('\n'.join(lines))
print('inserted groups:', len(INS))
