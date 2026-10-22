#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
verify_vault_summary.py — 终检脚本 (Final holistic verification)

对用 vault-content-summary / pdf-to-vault-summary 生成的 markdown 交付物做
**整体、严格** 的合规复核, 覆盖两个 skill 的全部 HARD 规则。

用法:
    python verify_vault_summary.py <path-to-md> [--strict-links pdf]

退出码: 0 = 全部通过; 1 = 存在 FAIL (必须先修掉再 present_files)。

覆盖范围 (两个 skill 的共同硬约束):
  1. 零空行 (整个文件 0 个空行)
  2. 单一 H1 且以 𒋙 前缀, 首行即 H1
  3. H1 后无引言段 (紧跟第一个 ## 标题)
  4. 所有 ##~###### 标题以 𒋙 前缀, 且标题内无编号 (阿拉伯/中文/（数字）)
  5. 半角英文标点 (无全角 ，。、；：（）！？“”‘’——；排除 … 和 ·；且不计 [[ ]] 内目标文本)
  6. bold 内边缘标点规则: 标点不得贴在 ** 内侧 (即 **标点 或 标点** 的写法)
  7. 有序列表标记 `N. ` 后恰好一个空格 (非双空格/tab)
  8. 显式递增编号: 每个标题块内编号应为 1,2,3... 连续, 不得全写 1. (lazy)
  9. 扁平节条目数 <= 9 (超过须用 补充内容 子标题拆分)
 10. 无反引号包裹路径/链接 (交付物禁止 `` ` ``)
 11. 存在内联来源链接 (至少若干 [[...]]；PDF 来源须含 pdf#page)
 12. 引用链接别名白名单 (共享规范 skills/shared/citation-link-aliases.md):
     带别名 [[..|x]] 的 x 必须是 图片/视频/音频/pdf/标题/文章/行 之一;
     裸 [[note]] (无别名) 作为整篇回退仍放行, 不误伤旧文件。
 13. 连续同集合链接已合并 (防重复书写同页/同标题链接)
 14. 链接别名与目标文件类型匹配: .mp4/.webm 等视频 -> |视频]],
     .m4a/.mp3 等音频 -> |音频]], .pdf -> |pdf| (嵌入页可 |图片|), 图片 -> |图片|
     (防 mp4 误用 |音频| 之类的错位)。
 15. 无下划线连写: 填空占位禁用 ______ (Obsidian/CommonMark 解析为强调符
     导致渲染错乱), 一律用 ……; [[...]] 链接目标内部不计。
"""
import sys
import re

# 全角/需转换标点集合 (不含豁免的 … 与 ·)
FW_PUNCT = "，。、；：（）！？“”‘’——"
# bold 内边缘会破坏渲染的标点 (与上面同源, 取会贴边的那些)
BOLD_INNER = "，。、；：（）！？“”‘’"

WIKILINK_RE = re.compile(r"!?\[\[[^\]]*\]\]")
# markdown 行号链接（Advanced URI）：[标题](obsidian://adv-uri?...&line=N...)
MD_LINK_RE = re.compile(r"\[[^\]]*\]\(obsidian://[^)]*\)")
HEADING_RE = re.compile(r"^(#{2,6})\s+(.*)$")
ITEM_RE = re.compile(r"^(\d+)\.(\s)")


def strip_wikilinks(text: str) -> str:
    return WIKILINK_RE.sub("", text)


def strip_links(text: str) -> str:
    """剥掉 wikilink 与 markdown 行号链接；URI 体内 %2F/&/__ 不属于正文，检查标点/下划线时须跳过。"""
    return MD_LINK_RE.sub("", WIKILINK_RE.sub("", text))


def verify(path: str, strict_links: str = ""):
    with open(path, "r", encoding="utf-8") as f:
        raw = f.read()
    # 去掉结尾单个换行, 避免 split 产生尾随空串被误判为"空行"
    if raw.endswith("\n"):
        raw = raw[:-1]
    lines = raw.split("\n")

    results = []  # (check_name, status, detail)

    # 1. 零空行
    blank = sum(1 for ln in lines if ln.strip() == "")
    results.append(("零空行 (want 0)", "PASS" if blank == 0 else "FAIL", f"found {blank} blank line(s)"))

    # 2. 单一 H1 + 𒋙 前缀 + 首行
    h1 = [i for i, ln in enumerate(lines) if re.match(r"^#\s+𒋙", ln)]
    results.append(("单一 H1 𒋙 (want 1)", "PASS" if len(h1) == 1 else "FAIL",
                    f"found {len(h1)} H1 line(s)"))
    first_nonempty = next((i for i, ln in enumerate(lines) if ln.strip() != ""), -1)
    results.append(("首行即 H1", "PASS" if first_nonempty in h1 else "FAIL",
                    f"first non-empty line idx={first_nonempty}, h1 idx={h1}"))

    # 3. H1 后无引言段 (紧随其后的非空行应为 ## 标题)
    if h1:
        after = h1[0] + 1
        while after < len(lines) and lines[after].strip() == "":
            after += 1
        ok = after < len(lines) and re.match(r"^##\s+𒋙", lines[after]) is not None
        results.append(("H1 后紧跟 ## 标题 (无引言)", "PASS" if ok else "FAIL",
                        f"line after H1: {lines[after][:40]!r}"))

    # 4. 标题 𒋙 前缀 + 无编号
    heading_issues = []
    for i, ln in enumerate(lines):
        m = HEADING_RE.match(ln)
        if not m:
            continue
        core = m.group(2)
        if not core.startswith("𒋙"):
            heading_issues.append(f"L{i+1} 标题缺 𒋙: {core[:30]!r}")
        else:
            body = core[1:].lstrip()
            if re.match(r"^\d", body) or re.match(r"^[一二三四五六七八九十]+[、.]", body) \
               or re.match(r"^（\d", body):
                heading_issues.append(f"L{i+1} 标题含编号: {core[:30]!r}")
    results.append(("标题 𒋙 前缀且无编号", "PASS" if not heading_issues else "FAIL",
                    "; ".join(heading_issues) if heading_issues else "all headings OK"))

    # 5. 半角标点 (排除 wikilink 内)
    prose = strip_links(raw)
    fw = [(m.start(), m.group()) for m in re.finditer("[" + re.escape(FW_PUNCT) + "]", prose)]
    results.append(("半角英文标点 (无全角)", "PASS" if not fw else "FAIL",
                    f"found {len(fw)} full-width punct(s); first: "
                    + (f"L approx {fw[0][0]} {fw[0][1]!r}" if fw else "")))

    # 6. bold 内边缘标点
    prose2 = strip_links(raw)
    bad_open = list(re.finditer(r"\*\*([" + re.escape(BOLD_INNER) + "])", prose2))
    bad_close = list(re.finditer(r"([" + re.escape(BOLD_INNER) + r"])\*\*", prose2))
    n_bad = len(bad_open) + len(bad_close)
    results.append(("bold 内边缘标点 (want 0)", "PASS" if n_bad == 0 else "FAIL",
                    f"found {n_bad} (opening-inner={len(bad_open)}, closing-inner={len(bad_close)})"))

    # 7 & 8. 列表标记空格 + 显式递增编号 (按标题块)
    sections = []  # (level, [item_numbers])
    cur_level = 0
    cur_items = []
    for i, ln in enumerate(lines):
        hm = HEADING_RE.match(ln)
        if hm:
            lvl = len(hm.group(1))
            # finalize current section if it had items
            if cur_items:
                sections.append((cur_level, cur_items))
                cur_items = []
            cur_level = lvl
            continue
        im = ITEM_RE.match(ln)
        if im:
            # 双空格 / tab
            n = im.group(1)
            after = ln[len(n) + 1:]
            if after[:2] in ("  ", "\t") or (len(after) >= 1 and after[0] in (" ", "\t") and len(after) >= 2 and after[1] in (" ", "\t")):
                pass  # counted below
            cur_items.append(int(n))
    if cur_items:
        sections.append((cur_level, cur_items))

    # 7: 检查 N. 后恰一空格
    dbl_space = 0
    for ln in lines:
        m = re.match(r"^(\d+)\.\s", ln)
        if m:
            # 看 . 后是否恰好一个空格 (且不是 tab)
            rest = ln[len(m.group(1)) + 1:]
            if rest[:1] != " " or (len(rest) >= 2 and rest[1] == " "):
                dbl_space += 1
    results.append(("N. 后恰一空格", "PASS" if dbl_space == 0 else "FAIL",
                    f"found {dbl_space} bad-spaced item marker(s)"))

    # 8: 显式递增 (每节 1,2,3... 连续)
    lazy = []
    for lvl, nums in sections:
        if not nums:
            continue
        expected = list(range(1, len(nums) + 1))
        if nums != expected:
            lazy.append(f"level{lvl} nums={nums}")
    results.append(("显式递增编号 (非 lazy 1.)", "PASS" if not lazy else "FAIL",
                    "; ".join(lazy) if lazy else "all sections increment correctly"))

    # 9. 扁平节 <= 9 条 (按标题块计各自条目)
    over9 = []
    for lvl, nums in sections:
        if len(nums) > 9:
            over9.append(f"level{lvl} has {len(nums)} items")
    results.append(("扁平节条目 <= 9", "PASS" if not over9 else "FAIL",
                    "; ".join(over9) if over9 else "all sections <= 9"))

    # 10. 反引号包裹
    bt = raw.count("`")
    results.append(("无反引号 (want 0)", "PASS" if bt == 0 else "FAIL",
                    f"found {bt} backtick(s)"))

    # 11. 来源链接存在 (wikilink 与 markdown 行号链接都算)
    link_count = len(WIKILINK_RE.findall(raw)) + len(MD_LINK_RE.findall(raw))
    md_count = len(MD_LINK_RE.findall(raw))
    pdf_count = len(re.findall(r"pdf#page=\d+\|pdf\]", raw))
    results.append(("存在内联来源链接", "PASS" if link_count > 0 else "FAIL",
                    f"{link_count} source link(s) ({md_count} line-uri); pdf#page={pdf_count}"))

    if strict_links == "pdf" and pdf_count == 0:
        results.append(("PDF 来源链接 (strict)", "FAIL", "no pdf#page link found"))

    # 12. 引用链接别名白名单 (共享规范: skills/shared/citation-link-aliases.md)
    ALLOWED_ALIASES = {"图片", "视频", "音频", "pdf", "标题", "文章", "行"}
    alias_bad = []
    for m in WIKILINK_RE.finditer(raw):
        inner = m.group(0)[2:-2]  # 去 [[ ]] 或 ![[ ]]
        if "|" not in inner:
            # 裸 [[note]] / ![[img]] 无别名, 作为整篇/嵌入回退放行
            continue
        if inner.split("|", 1)[0].strip().startswith("#"):
            # 同文件内部导航锚链(vwd #18 回挂锚链; shared「Scope」①): 别名写描述句是规定形态, 不判白名单
            continue
        alias = inner.rsplit("|", 1)[1].strip()
        if alias not in ALLOWED_ALIASES:
            alias_bad.append(f"{m.group(0)} -> 别名={alias!r}")
    results.append(("引用链接别名白名单", "PASS" if not alias_bad else "FAIL",
                    "; ".join(alias_bad) if alias_bad else
                    "全部带别名链接均用固定词(图片/视频/音频/pdf/标题/文章/行)"))

    # 14. 链接别名与目标文件类型匹配 (防 mp4 误用 音频 等错位)
    # 共享规范: 视频(.mp4/.webm/.m4v/.mov) -> 视频; 音频(.m4a/.mp3/.wav/.ogg/.flac/.aac) -> 音频;
    # PDF 页面 -> pdf (嵌入页可 图片); 图片(.png/.jpg/.jpeg/.gif/.webp/.svg) -> 图片。
    VIDEO_EXTS = (".mp4", ".webm", ".m4v", ".mov")
    AUDIO_EXTS = (".m4a", ".mp3", ".wav", ".ogg", ".flac", ".aac")
    IMG_EXTS = (".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg")
    ext_bad = []
    for m in WIKILINK_RE.finditer(raw):
        inner = m.group(0)[2:-2]
        if "|" not in inner:
            continue
        target = inner.rsplit("|", 1)[0].strip()
        alias = inner.rsplit("|", 1)[1].strip()
        low = target.lower().split("#", 1)[0]  # 去掉 #t= / #page= 片段再判扩展名
        ext = None
        for cand in VIDEO_EXTS + AUDIO_EXTS + IMG_EXTS + (".pdf",):
            if low.endswith(cand):
                ext = cand
                break
        if ext is None:
            continue  # 未知/笔记链接, 不判
        if ext in VIDEO_EXTS:
            if alias != "视频":
                ext_bad.append(f"{m.group(0)} -> 视频文件须用 |视频]], 不能用 |{alias}]]")
        elif ext in AUDIO_EXTS:
            if alias != "音频":
                ext_bad.append(f"{m.group(0)} -> 音频文件须用 |音频]], 不能用 |{alias}]]")
        elif ext == ".pdf":
            if alias not in ("pdf", "图片"):
                ext_bad.append(f"{m.group(0)} -> PDF 须用 |pdf]] (嵌入页可 |图片]])")
        else:
            if alias != "图片":
                ext_bad.append(f"{m.group(0)} -> 图片文件须用 |图片]], 不能用 |{alias}]]")
    results.append(("链接别名与文件类型匹配", "PASS" if not ext_bad else "FAIL",
                    "; ".join(ext_bad) if ext_bad else
                    "mp4→视频, m4a/mp3→音频, pdf→pdf, 图片→图片 均一致"))

    # 15. 无下划线连写 (Obsidian/CommonMark 把 ___ 解析为强调符, 渲染错乱)
    # 填空占位一律用 ……, 禁用 ______ 等连写下划线; 跳过 [[...]] 与行号链接 URI 内部。
    prose3 = strip_links(raw)
    und = [(m.start(), m.group()) for m in re.finditer(r"_{2,}", prose3)]
    results.append(("无下划线连写 (want 0)", "PASS" if not und else "FAIL",
                    f"found {len(und)} underscore run(s); first: "
                    + (f"L approx {und[0][0]} {und[0][1]!r}" if und else "")))

    # 13. 连续同集合链接已合并 (防重复书写同页/同标题链接)
    # 规则: 连续的列表条目若引用完全相同的(非空)链接集合, 应合并到末条, 不应每条重复写。
    # 实现: 逐行记录列表条目的链接集合(wikilink + markdown 行号链接都计入; 非列表行=标题/段落, 打断连续)。
    per_line_links = []
    for ln in lines:
        if ITEM_RE.match(ln):
            links = set(WIKILINK_RE.findall(ln)) | set(MD_LINK_RE.findall(ln))
            per_line_links.append(tuple(sorted(links)))
        else:
            per_line_links.append(None)  # 非列表行打断连续
    merge_viol = []
    i = 0
    N = len(per_line_links)
    while i < N:
        t = per_line_links[i]
        if t is None or len(t) == 0:
            i += 1
            continue
        j = i
        while j + 1 < N and per_line_links[j + 1] == t:
            j += 1
        if j > i:  # 连续 >=2 条相同链接集合
            merge_viol.append((i, j, t))
        i = j + 1
    if merge_viol:
        det = "; ".join(f"L{v[0]+1}-{v[1]+1} 应合并 {v[2]}" for v in merge_viol)
        results.append(("连续同集合链接已合并", "FAIL", det))
    else:
        results.append(("连续同集合链接已合并", "PASS", "无重复同集合链接"))

    # 输出报告
    print("=" * 60)
    print(f"VERIFY: {path}")
    print("=" * 60)
    fails = 0
    for name, status, detail in results:
        mark = "OK " if status == "PASS" else "XX "
        if status == "FAIL":
            fails += 1
        print(f"[{mark}] {name}")
        if detail:
            print(f"       {detail}")
    print("-" * 60)
    print(f"RESULT: {'ALL PASS' if fails == 0 else str(fails) + ' FAIL(S)'}")
    print("=" * 60)
    return fails


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: verify_vault_summary.py <md-path> [--strict-links pdf]")
        sys.exit(2)
    p = sys.argv[1]
    sl = ""
    if "--strict-links" in sys.argv:
        idx = sys.argv.index("--strict-links")
        if idx + 1 < len(sys.argv):
            sl = sys.argv[idx + 1]
    fails = verify(p, sl)
    sys.exit(1 if fails > 0 else 0)
