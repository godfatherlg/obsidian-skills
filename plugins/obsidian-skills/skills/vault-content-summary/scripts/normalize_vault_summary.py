#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
normalize_vault_summary.py — 生成后自动规范化 (在 verify_vault_summary.py 之前跑)

确定性地修五类易错点, 减少手工出错与"规则没执行"的反复:
  1. 合并连续同集合链接: 连续列表条目若引用完全相同的(非空)链接集合, 把该集合只保留在末条,
     其余条删除(对应 vault-content-summary 的"合并链接"规则)。
  2. 修加粗内边缘标点: 在 **...** 内边缘的括号/引号处插入零宽空格 U+200B (隐形且永远安全,
     防止 CommonMark/Obsidian 渲染失效)。
  3. 全角标点转半角: 将 FW_PUNCT 全角标点转半角, 但跳过 [[...]] / ![[...]] 内部
     (链接目标文本须保持原样, 否则链接失效)。
  4. 连写下划线转省略号: 链接外的 ______ 等连写下划线替换为 …… (Obsidian/CommonMark
     把连写下划线解析成强调符导致渲染错乱, 填空占位一律用 ……), 跳过链接目标内部。
  5. 媒体链接别名对齐: .mp4/.webm 等视频链接别名强制为 |视频|, .m4a/.mp3 等音频链接
     别名强制为 |音频| (防 mp4 误用 |音频| 之类的错位), PDF/图片/笔记链接不动。

用法:
    python normalize_vault_summary.py <path-to-md> [--dry]
默认原地改写文件; --dry 只打印 unified diff 不写文件。
幂等: 连续跑两次结果一致 (无 full-width 可转 / 无内边缘标点可修 / 无同集合可合并 / 无连写下划线时 no change)。
"""
import sys
import re

# 全角 -> 半角映射 (与 verify_vault_summary.py 的 FW_PUNCT 对应, 含 —— 转 -)
FW_MAP = {
    '\u201c': '"', '\u201d': '"', '\u2018': "'", '\u2019': "'",
    '\uff08': '(', '\uff09': ')', '\uff0c': ',', '\u3002': '.',
    '\uff1a': ':', '\uff1b': ';', '\uff01': '!', '\uff1f': '?',
    '\u3001': ',', '\u2014': '-',
}
WIKILINK_RE = re.compile(r"!?\[\[[^\]]*\]\]")
# markdown 行号链接（Advanced URI）：[标题](obsidian://adv-uri?...&line=N...)
MD_LINK_RE = re.compile(r"\[[^\]]*\]\(obsidian://[^)]*\)")
ITEM_RE = re.compile(r"^(\d+)\.(\s)")
# 加粗内边缘需要 U+200B 保护的符号 (全角 + 半角括号/引号)
EDGE = "（）()\u201c\u201d\u2018\u2019\"'"


def _link_ranges(s):
    """wikilink + markdown 行号链接的 (start, end) 区间; 转换标点/下划线时跳过。"""
    ws = [(m.start(), m.end()) for m in WIKILINK_RE.finditer(s)]
    ms = [(m.start(), m.end()) for m in MD_LINK_RE.finditer(s)]
    return ws + ms


def _in_ranges(pos, ranges):
    return any(a <= pos < b for a, b in ranges)


def convert_punct(s):
    """全角转半角, 跳过 [[...]] 与 markdown 行号链接内部。"""
    ranges = _link_ranges(s)
    out = []
    for i, ch in enumerate(s):
        if _in_ranges(i, ranges):
            out.append(ch)
        else:
            out.append(FW_MAP.get(ch, ch))
    return ''.join(out)


def convert_underscores(s):
    """把链接外的连写下划线 (2+) 替换为 …… (Obsidian 把 ___ 解析为强调符, 渲染错乱)。

    填空占位一律用省略号; 跳过 [[...]] 链接目标与 markdown 行号链接 URI 内部
    (文件名/URI 可能含下划线, 如 xxx__yyy.md)。
    幂等: 转换后不再含连写下划线。
    """
    ranges = _link_ranges(s)
    out = []
    i = 0
    n = len(s)
    while i < n:
        if _in_ranges(i, ranges):
            j = i
            while j < n and _in_ranges(j, ranges):
                j += 1
            out.append(s[i:j])
            i = j
            continue
        if s[i] == '_':
            j = i
            while j < n and s[j] == '_':
                j += 1
            if j - i >= 2:
                out.append('……')
            else:
                out.append(s[i:j])
            i = j
        else:
            out.append(s[i])
            i += 1
    return ''.join(out)


VIDEO_EXTS = (".mp4", ".webm", ".m4v", ".mov")
AUDIO_EXTS = (".m4a", ".mp3", ".wav", ".ogg", ".flac", ".aac")


def fix_media_aliases(s):
    """链接别名与目标文件类型对齐 (防 mp4 误用 |音频| 错位)。

    .mp4/.webm/.m4v/.mov 视频 -> 别名强制为 |视频|;
    .m4a/.mp3/.wav/.ogg/.flac/.aac 音频 -> 别名强制为 |音频|;
    PDF/图片/笔记链接不动 (pdf 可合法用 |图片| 做嵌入, 不误改)。
    幂等: 全部对齐后不再变化。
    """

    def repl(m):
        inner = m.group(0)[2:-2]
        if "|" not in inner:
            return m.group(0)
        target, alias = inner.rsplit("|", 1)
        low = target.strip().lower().split("#", 1)[0]
        new_alias = alias
        if low.endswith(VIDEO_EXTS):
            new_alias = '视频'
        elif low.endswith(AUDIO_EXTS):
            new_alias = '音频'
        if new_alias == alias:
            return m.group(0)
        return '[[' + target + '|' + new_alias + ']]'

    return WIKILINK_RE.sub(repl, s)


def fix_bold_edges(s):
    """在 **...** 内边缘的括号/引号处插入 U+200B。"""
    out = []
    i = 0
    n = len(s)
    while i < n:
        if s[i:i + 2] == '**':
            j = s.find('**', i + 2)
            if j == -1:
                out.append(s[i:])
                break
            inner = s[i + 2:j]
            if inner and inner[0] in EDGE:
                inner = '\u200b' + inner
            if inner and inner[-1] in EDGE:
                inner = inner + '\u200b'
            out.append('**' + inner + '**')
            i = j + 2
        else:
            out.append(s[i])
            i += 1
    return ''.join(out)


def _remove_links_from_line(line, links):
    for lk in links:
        line = line.replace(lk, '')
    line = re.sub(r'  +', ' ', line)   # 清理删除后留下的双空格
    line = re.sub(r' $', '', line)      # 清理行尾空格
    return line


def merge_links(lines):
    """连续相同(非空)链接集合只保留在末条 (wikilink + markdown 行号链接都计入)。"""
    per = []
    for ln in lines:
        if ITEM_RE.match(ln):
            links = set(WIKILINK_RE.findall(ln)) | set(MD_LINK_RE.findall(ln))
            per.append(tuple(sorted(links)))
        else:
            per.append(None)  # 非列表行打断连续
    i = 0
    N = len(per)
    while i < N:
        t = per[i]
        if t is None or len(t) == 0:
            i += 1
            continue
        j = i
        while j + 1 < N and per[j + 1] == t:
            j += 1
        if j > i:
            for k in range(i, j):
                lines[k] = _remove_links_from_line(lines[k], t)
        i = j + 1
    return lines


def normalize(text):
    # 顺序: 转标点 -> 修连写下划线 -> 对齐媒体链接别名 -> 修加粗边 -> 合并链接
    text = convert_punct(text)
    text = convert_underscores(text)
    text = fix_media_aliases(text)
    text = fix_bold_edges(text)
    lines = text.split('\n')
    lines = merge_links(lines)
    return '\n'.join(lines)


def main():
    if len(sys.argv) < 2:
        print("usage: normalize_vault_summary.py <md-path> [--dry]")
        sys.exit(2)
    p = sys.argv[1]
    dry = '--dry' in sys.argv
    raw = open(p, encoding='utf-8').read()
    new = normalize(raw)
    if new == raw:
        print("no change")
        return
    if dry:
        import difflib
        for d in difflib.unified_diff(raw.splitlines(), new.splitlines(),
                                      lineterm='', n=1):
            print(d)
    else:
        open(p, 'w', encoding='utf-8').write(new)
        print("normalized:", p)


if __name__ == '__main__':
    main()
