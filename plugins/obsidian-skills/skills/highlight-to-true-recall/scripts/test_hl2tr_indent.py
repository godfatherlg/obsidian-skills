"""hl2tr.py 的「缩进归属」规则：离线自测（不落库、不碰 vault）

2026-09-17 广哥定：行首带缩进的行 = 上方最近未缩进行的续体，合并成一张卡。
跑法：python scripts/test_hl2tr_indent.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hl2tr  # noqa: E402

CASES = [
    ("父项+子项合并",
     "- ==**父概念**==\n"
     "    - ==**子概念**==\n",
     1),
    ("父项无高亮、子项有高亮也合并",
     "- 父行没高亮\n"
     "    - ==**子概念**==\n",
     1),
    ("多级缩进归同一父块",
     "- ==**父**==\n"
     "    - ==**子**==\n"
     "        - ==**孙**==\n",
     1),
    ("两个平级父项 = 两块",
     "- ==**甲**==\n"
     "- ==**乙**==\n",
     2),
    ("空行切断归属：缩进孤儿行各成一块，不并入空行前的父项",
     "- ==**甲**==\n"
     "\n"
     "    - ==**孤立缩进**==\n",
     2),
    ("标题是硬边界",
     "- ==**甲**==\n"
     "## 标题\n"
     "- ==**乙**==\n",
     2),
    ("段落 + 缩进续行合并",
     "这是==**父段**==\n"
     "    这是缩进续行==**子**==\n",
     1),
]


def main():
    ok = True
    for name, text, want in CASES:
        lines = text.split("\n")
        hl2tr.MERGE_INDENT = True
        blocks = hl2tr.build_blocks(lines)
        got = len(blocks)
        flag = "OK " if got == want else "FAIL"
        if got != want:
            ok = False
        print("[%s] %s  期望%d块 实得%d块" % (flag, name, want, got))
        for b in blocks:
            print("      block %d-%d: %r"
                  % (b["start"], b["end"], "\n".join(lines[b["start"]:b["end"] + 1])))
    # 开关有效性：关掉后回到「每行独立成块」
    hl2tr.MERGE_INDENT = False
    lines = "- ==**父**==\n    - ==**子**==\n".split("\n")
    got = len(hl2tr.build_blocks(lines))
    print("[%s] --no-indent-merge 回退  期望2块 实得%d块" % ("OK " if got == 2 else "FAIL", got))
    if got != 2:
        ok = False
    hl2tr.MERGE_INDENT = True
    print("\n全部通过" if ok else "\n有用例未通过")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
