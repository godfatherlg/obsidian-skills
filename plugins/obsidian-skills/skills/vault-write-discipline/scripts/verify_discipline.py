#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
verify_discipline.py — 通用写文件前纪律终检 (vault-write-discipline skill)

对写入 vault (<vault>) 的任意 markdown 做「生成内容格式纪律 + 临时文件夹纪律」
的整体合规复核。

与 vault-content-summary/scripts/verify_vault_summary.py 的关系:
  - vault-content-summary 负责 𒋙/别名/内联链接 等「汇总风格」硬规则 (更严);
  - 本脚本负责 **适用于所有生成文件** 的通用纪律 + 临时文件夹纪律。
  二者互补: 汇总风格文件 present 前两个都跑; 普通笔记只跑本脚本即可。

用法:
    python verify_discipline.py <md-path>            # 通用格式纪律
    python verify_discipline.py --temp-check --since-min 120   # 临时文件夹纪律(只判最近120分钟新增图,
                                                               #  不加 --since-min 会把历史图一并报出, 别照裸命令清)
    python verify_discipline.py --all <md-path>      # 通用格式 + 临时文件夹 (最常用)
    python verify_discipline.py --temp-dir "<vault>/临时" --temp-check --since-min 120

退出码: 0 = 全部通过 (含 WARN); 1 = 存在 FAIL (必须先修再 present_files)。

覆盖范围 (通用格式纪律):
  1. 零空行 (允许独立 > [!NOTE] callout 前的单个空行)
  2. 有序列表标记 N. 后恰一个空格
  3. 半角英文标点 (无全角 ，。、；：（）！？“”‘’——；排除 [[ ]] 内目标文本)
  4. bold 内边缘标点 (标点不得贴在 ** 内侧；含 **"中文引号"** 紧贴情形)
  5. 顶层裸 4 空格【无标记】行 (前一行非列表项时渲染成代码块, 致 ** 失效;
     4 空格带列表标记 '    N. ' / '    - ' 与 ![[ 嵌入 是合法隶属缩进, 放行;
     列表项之后的无标记 4 空格续行合法 (2026-09-07 用户定稿: 渲染为缩进线), 放行)
  6. 无 \\!\\[\\[ 转义 (应为 ![[)
  7. 分标题的有序列表从 1 重编 (不跨标题连续累加)
  8. 扁平节条目 <= 9
  9. 缩进体例: 列表行缩进必须是 4 的倍数, 不得跳级 (每层只深 4 空格), 且最多 2 级 (<=8 空格)
     —— 隶属关系用 4 空格缩进, 并列分行且继承同层缩进 (2026-09-02 用户定)
 10. 加粗重点判定 (2026-09-03 用户定, 规则见 references/bold-keyterm-rules.md):
     整条被一对 ** 全包裹且 >=15 字 -> FAIL; 单条加粗块 >3 / 单条加粗占比 >40% /
     单节加粗条目占比 >70% -> WARN
 11. 图片引用落地: ![[images/x.png]] 与 [[x.png|图片]] 的目标必须真实存在 (占位图名跳过) -> FAIL
 12. 内部锚链 [[#X]] 必须命中本文件某标题 (^block 引用跳过); 出现 U+2621 误写 -> FAIL（现行符号 𒋙 = U+122D9，2026-10-20 全库由 U+2631 迁来；本脚本只拦误写、不做逐处校验）
 13. 图片缩进: 同文件内 Tab / 空格不得混用, 空格须为 4 或 8 -> WARN

覆盖范围 (本次新增内容, 仅 hook 通过 stdin 传入时检查):
 14. == 与 \\boxed: Edit 传的是 new_string (纯新增) -> FAIL; Write 传的是整篇 content,
     无从区分"AI 新加"与"用户原有的人工标记" -> 降为 WARN 由人眼确认
 15. 新增"补充"类节须回挂反向锚链 -> WARN (常分两次 Edit, FAIL 会误报且不可自消)
 16. 新增图片缩进须跟随文件既有形态 -> FAIL

覆盖范围 (临时文件夹纪律):
  9. 临时目录无图片残留 (svg/png/jpg/jpeg/gif/webp 必须清出; 非图片 txt/srt/py 等可留)
 10. 临时记录.md 若非空则 WARN (内容已转写他处须清空为 0 字节)
"""
import sys
import os
import re
import time

# 全角/需转换标点 (不含豁免的 … 与 ·)
FW_PUNCT = "，。、；：（）！？“”‘’——"
# bold 内边缘会破坏渲染的标点
BOLD_INNER = "，。、；：（）！？“”‘’"

WIKILINK_RE = re.compile(r"!?\[\[[^\]]*\]\]")
# 2026-09-02: 放宽到 #{1,6} —— 正式笔记的 `# 𒋙主题` H1 是合法分节边界,
# 不认它会让 H1 之后的条目并进上一节, 误报"跨节编号/扁平节超限"。
# (临时记录仍禁用 H1, 见 vault-write-discipline checklist #7 / temp-note-workflow 硬规则 7)
HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")
ITEM_RE = re.compile(r"^(\d+)\.(\s)")

TEMP_IMG_EXT = (".png", ".jpg", ".jpeg", ".svg", ".gif", ".webp")
DEFAULT_TEMP_DIR = "<vault>/临时"

VAULT_ROOT = "<vault>"
# 图片引用落地检查: 只认这些扩展名, 其余 (![[某笔记]] 之类) 不算图片
IMG_EXT = (".png", ".jpg", ".jpeg", ".svg", ".gif", ".webp", ".bmp")
# 文档示例里的占位图名 (images/xxx.png 这类), 不是真引用, 跳过不报
PLACEHOLDER_RE = re.compile(r"(^|/)(xxx+|x|y+|foo|bar|example|sample|test|占位|placeholder)\.", re.I)
# 𒋙 的正确码位是 U+122D9（2026-10-20 全库由 U+2631 迁来）; U+2621 (☡ 注意标志) 是历史误写, 会让锚链静默失效
ANCHOR_MARK_CORRECT = "\U000122d9"  # 2026-10-20 全库迁移后的现行符号；仅作文档用——检查逻辑只拦 U+2621 误写，不做逐处校验
ANCHOR_MARK_WRONG = "\u2621"

# 2026-09-02 用户定: 缩进最多 2 级 —— 顶层 0, 子层 4, 孙层 8; 第 3 级 (12) 起违规。
MAX_INDENT_LEVEL = 2
MAX_INDENT = 4 * MAX_INDENT_LEVEL  # = 8


def strip_wikilinks(text: str) -> str:
    return WIKILINK_RE.sub("", text)


def check_format(path: str, since_min=None):
    results = []  # (name, status, detail)
    with open(path, "r", encoding="utf-8") as f:
        raw = f.read()
    # 去掉结尾换行, 避免 split 产生尾随空串被误判为"空行"
    raw = raw.rstrip("\n")
    lines = raw.split("\n")

    # 1. 零空行 (允许独立 callout 前的单个空行)
    bad_blank = 0
    for i, ln in enumerate(lines):
        if ln.strip() == "":
            j = i + 1
            while j < len(lines) and lines[j].strip() == "":
                j += 1
            if j < len(lines) and lines[j].lstrip().startswith("> [!"):
                continue  # callout 前的空行允许
            bad_blank += 1
    results.append(("零空行(允许callout前空行)", "PASS" if bad_blank == 0 else "FAIL",
                    f"found {bad_blank} decorative blank line(s)"))

    # 2. N. 后恰一空格
    dbl = 0
    for ln in lines:
        m = re.match(r"^(\d+)\.\s", ln)
        if m:
            rest = ln[len(m.group(1)) + 1:]
            if rest[:1] != " " or (len(rest) >= 2 and rest[1] == " "):
                dbl += 1
    results.append(("N. 后恰一空格", "PASS" if dbl == 0 else "FAIL",
                    f"found {dbl} bad-spaced item marker(s)"))

    # 3. 半角标点 (排除 wikilink 内; 加粗 span 内的全角标点豁免,
    #    因 **“...”** 引号构造是既定安全写法, 不应被半角规则误伤)
    prose = strip_wikilinks(raw)
    prose_masked = list(prose)
    for m in re.finditer(r"\*\*(.+?)\*\*", prose):
        for k in range(m.start(), m.end()):
            prose_masked[k] = " "
    prose_masked = "".join(prose_masked)
    fw = list(re.finditer("[" + re.escape(FW_PUNCT) + "]", prose_masked))
    results.append(("半角英文标点(无全角)", "PASS" if not fw else "FAIL",
                    f"found {len(fw)} full-width punct(s)" +
                    (f"; first at char {fw[0].start()} {fw[0].group()!r}" if fw else "")))

    # 4. bold 内边缘标点 (flanking 安全: 含 **"中文引号"** 紧贴情形)
    # 规则: **...** 定界符必须 flanking。当内侧首/尾字符是标点(含全角引号)时,
    # 外侧(开**之前 / 闭**之后)必须是空白或标点, 否则 Obsidian/CommonMark 不渲染。
    # 安全写法: 文字 **"引号内"** 文字 (外侧留半角空格); 不安全: 词**"引号内"**词。
    prose2 = strip_wikilinks(raw)
    WHITESPACE = " \t\n\r\f\v"
    PUNCT = FW_PUNCT + ".,;:!?\"'()[]{}<>/\\-_=+*~`@#$%^&"
    bold_spans = list(re.finditer(r"\*\*(.+?)\*\*", prose2))
    n_bad = 0
    bad_examples = []
    for m in bold_spans:
        inner = m.group(1)
        if not inner:
            continue
        prev_char = prose2[m.start() - 1] if m.start() > 0 else ""
        next_char = prose2[m.end()] if m.end() < len(prose2) else ""
        first_inner = inner[0]
        last_inner = inner[-1]
        risky_open = (first_inner in BOLD_INNER) and \
            (prev_char == "" or (prev_char not in WHITESPACE and prev_char not in PUNCT))
        risky_close = (last_inner in BOLD_INNER) and \
            (next_char == "" or (next_char not in WHITESPACE and next_char not in PUNCT))
        if risky_open or risky_close:
            n_bad += 1
            if len(bad_examples) < 5:
                bad_examples.append(m.group(0))
    results.append(("bold内边缘标点(flanking安全)", "PASS" if n_bad == 0 else "FAIL",
                    f"found {n_bad}" + (f": {bad_examples}" if bad_examples else "")))

    # 5. 无标记 4 空格续行的代码块风险检查
    #    2026-09-07 用户定稿: 列表项(N. / - )之后的无标记 4 空格续行在用户的 OB 环境
    #    渲染为缩进线(tab 线), 合法放行; 只有"顶层裸 4 空格无标记行"(前一行非列表项)
    #    才是真正的代码块风险, 仍然 FAIL。
    # 预计算每行是否处于围栏代码块(```)内部
    _bq = chr(96) * 3  # 反引号 x3 = 围栏标记
    fence_inside = []
    _state = False
    for ln in lines:
        fence_inside.append(_state)
        if ln.strip().startswith(_bq):
            _state = not _state
    code_risk = []
    for i in range(0, len(lines)):  # 2026-10-21: 从 0 起, 否则第 1 行(文档开头裸缩进)漏报
        ln = lines[i]
        if fence_inside[i]:
            continue
        _s = ln.strip()
        if not _s or _s.startswith(_bq) or _s.startswith('![['):
            continue
        if not (ln.startswith("    ") and not ln.startswith("     ")
                and not re.match(r"^    (\d+\.|[-*] )", ln)):
            continue
        # 判据(2026-10-21 广哥定, 取代旧的"只看紧邻前一行"):
        #   向上回溯整段无标记续行, 若段首的前一行是列表项(N. / - ), 则整段都渲染为
        #   该列表项下的缩进线, 合法放行; 回溯落点在空行/文档开头/普通正文行 -> 仍是真风险。
        #   旧判据只看 lines[i-1], 导致"列表项 + 多条续行"里第 2 条起必然误报 FAIL。
        j = i - 1
        while j >= 0:
            _p = lines[j]
            if not _p.strip() or not _p.startswith("    "):
                break
            if re.match(r"^\s*(\d+\.|[-*+] )", _p):
                break
            j -= 1
        if j >= 0 and re.match(r"^\s*(\d+\.|[-*+] )", lines[j]):
            continue
        code_risk.append(f"L{i+1}")
    results.append(("顶层裸4空格【无标记】行(代码块风险)",
                    "PASS" if not code_risk else "FAIL",
                    (", ".join(code_risk) +
                     " (真代码块风险: 段首前一行是空行/文档开头/普通正文, 4 空格缩进会渲染成代码块; "
                     "若段首前一行是列表项 N. / - 则合法(渲染为缩进线), 本项不会报; "
                     "确属真风险时改用 3 空格软续行, 不要补 '    N. '/'- ' 列表标记)")
                    if code_risk else "none"))

    # 6. \![[ 转义检查
    esc = raw.count("\\![[")
    results.append(("无 \\!\\[\\[ 转义", "PASS" if esc == 0 else "FAIL",
                    f"found {esc} escaped-embed(s), should be ![["))

    # 7 & 8. 分标题有序列表从 1 重编 + 扁平 <= 9
    sections = []
    cur_level = 0
    cur_items = []
    for ln in lines:
        hm = HEADING_RE.match(ln)
        if hm:
            if cur_items:
                sections.append((cur_level, cur_items))
                cur_items = []
            cur_level = len(hm.group(1))
            continue
        im = ITEM_RE.match(ln)
        if im:
            cur_items.append(int(im.group(1)))
    if cur_items:
        sections.append((cur_level, cur_items))
    lazy = []
    over9 = []
    for lvl, nums in sections:
        if not nums:
            continue
        if nums != list(range(1, len(nums) + 1)):
            lazy.append(f"lvl{lvl} nums={nums}")
        if len(nums) > 9:
            over9.append(f"lvl{lvl} {len(nums)} items")
    results.append(("分标题有序列表从1重编", "PASS" if not lazy else "FAIL",
                    "; ".join(lazy) if lazy else "ok"))
    results.append(("扁平节条目<=9", "PASS" if not over9 else "FAIL",
                    "; ".join(over9) if over9 else "ok"))

    # 9. 缩进体例: 隶属关系用 4 空格缩进; 并列分行且继承同层缩进
    #    - 列表行的缩进必须是 4 的倍数 (4 / 8 / 12 ...), 半吊子缩进(2/3/5/6)一律 FAIL
    #    - 缩进不得跳级: 子层最多比上一列表行深 4 空格 (0 -> 8 属跳级)
    #    (2026-09-02 用户定: 明显的隶属关系用 4 空格缩进表示,
    #     并列内容分行表示, 分行时继承并列内容的隶属关系)
    # 9-pre. YAML frontmatter 区段 (首行 --- 到下一个 ---, 含两端) 不是正文排版:
    #    它的缩进由 YAML 语法决定 (列表项惯例 2 空格), 不参与本节的
    #    "4 的倍数 / 不跳级 / 最多 2 级" 检查。
    #    (2026-09-17 修: hl2tr 建的卡笔记 frontmatter 带 `parents:` 列表,
    #     其 `  - "[[教资]]"` 被误报 L4(2空格) 假 FAIL —— 凡卡笔记都必带这段)
    fm_inside = [False] * len(lines)
    if lines and lines[0].strip() == "---":
        for _i in range(1, len(lines)):
            if lines[_i].strip() == "---":
                for _k in range(0, _i + 1):
                    fm_inside[_k] = True
                break
    LIST_LINE_RE = re.compile(r"^( *)(\d+\.|[-*]) ")
    indents = []  # (lineno, indent, marker)
    for i, ln in enumerate(lines):
        if fence_inside[i] or fm_inside[i]:
            continue
        m = LIST_LINE_RE.match(ln)
        if m:
            indents.append((i + 1, len(m.group(1)), m.group(2)))
    #    无标记缩进纯文本行(如 "    关键词:**内容**")同样受"最多2级"约束,
    #    但豁免"4的倍数"(3 空格续行是合法写法), 故单独收集。
    plain_indents = []  # (lineno, indent)
    for i, ln in enumerate(lines):
        if fence_inside[i] or fm_inside[i] or not ln.strip():
            continue
        if LIST_LINE_RE.match(ln):
            continue
        _s = ln.strip()
        if _s.startswith("![[") or _s.startswith("|") or _s.startswith(">"):
            continue
        _lead = len(ln) - len(ln.lstrip(" "))
        if _lead > 0:
            plain_indents.append((i + 1, _lead))

    bad_mod = [f"L{n}({ind}空格)" for n, ind, _ in indents if ind % 4 != 0]
    results.append(("缩进为4的倍数(隶属层级)", "PASS" if not bad_mod else "FAIL",
                    "; ".join(bad_mod) + " (缩进须为 4/8/12..., 半吊子缩进会让层级失效)"
                    if bad_mod else "ok"))

    bad_jump = []
    for k in range(1, len(indents)):
        prev_ind = indents[k - 1][1]
        cur_ind = indents[k][1]
        if cur_ind > prev_ind + 4:
            bad_jump.append(f"L{indents[k][0]}({prev_ind}->{cur_ind})")
    results.append(("缩进不跳级(每层只深4空格)", "PASS" if not bad_jump else "FAIL",
                    "; ".join(bad_jump) + " (子层只能比上层多 4 空格, 不得 4->8->12 式跳级)"
                    if bad_jump else "ok"))

    # 9c. 缩进深度上限: 最多 2 级 (0 / 4 / 8 空格), 第 3 级 (12 空格及以上) 一律 FAIL
    #     (2026-09-02 用户定: 层级太深会撑爆阅读宽度, 一律压平成 <=2 级)
    #     压平办法: 把更深的孙层提升为父层条目里的 "**关键词**:**内容**" 单行写法,
    #     或另起一个 N. 子项与兄弟并列, 不再往下钻缩进。
    bad_deep = [f"L{n}({ind}空格)" for n, ind, _ in indents if ind > MAX_INDENT]
    bad_deep += [f"L{n}({ind}空格,无标记)" for n, ind in plain_indents if ind > MAX_INDENT]
    results.append(("缩进最多2级(<=8空格)", "PASS" if not bad_deep else "FAIL",
                    "; ".join(bad_deep) +
                    " (最多 0/4/8 两档, 第 3 级 12 空格起违规; 压平为单行 '**关键词**:**内容**' 或并列子项)"
                    if bad_deep else "ok"))

    # 10. 加粗重点判定 (2026-09-03 用户定)
    #     规则单一真源: references/bold-keyterm-rules.md
    #     FAIL: 整条被一对 ** 全包裹 (>=15 字) —— 整句涂色 = 没有扫读锚点
    #     WARN: 单条加粗块 > 3 处 / 单条加粗占比 > 40%(>=30字) / 单节平均加粗块 > 2.5(>=5条)
    BOLD_RE = re.compile(r"\*\*(.+?)\*\*")
    LIST_ANY_RE = re.compile(r"^ *(\d+\.|[-*]) +(.*)$")
    bold_full, bold_many, bold_ratio, hot_sec = [], [], [], []
    _sec_n, _sec_blocks, _sec_name = 0, 0, "(文首)"

    def _flush_sec():
        # 节级只查「平均加粗块数」——术语清单每条 1 块属正常, 不会误伤;
        # 平均 > 2.5 说明该节把说明文字也粗了。
        if _sec_n >= 5 and _sec_blocks / _sec_n > 2.5:
            hot_sec.append(f"{_sec_name}(均{_sec_blocks / _sec_n:.1f}块/条)")

    for i, ln in enumerate(lines):
        if fence_inside[i]:
            continue
        hm = HEADING_RE.match(ln)
        if hm:
            _flush_sec()
            _sec_n, _sec_blocks = 0, 0
            _sec_name = hm.group(2)[:20]
            continue
        m = LIST_ANY_RE.match(ln)
        if not m:
            continue
        content = strip_wikilinks(m.group(2))
        if not content.strip():
            continue
        _sec_n += 1
        # 公式 $...$ 不计入占比统计 (公式本身不粗, 且会虚增条目长度)
        plain = re.sub(r"\$[^$]*\$", "", content)
        blocks = BOLD_RE.findall(plain)
        _sec_blocks += len(blocks)
        # 可见文字 = 去掉 ** 标记本身后的纯文本长度 (不含空白)
        visible = re.sub(r"\s", "", BOLD_RE.sub(lambda mm: mm.group(1), plain))
        n_vis = len(visible)
        n_bold = sum(len(re.sub(r"\s", "", b)) for b in blocks)
        stripped = content.strip()
        is_full = (len(blocks) == 1 and stripped.startswith("**")
                   and stripped.endswith("**")
                   and blocks[0].strip() == stripped[2:-2])
        if is_full and n_vis >= 15:
            bold_full.append(f"L{i+1}")
        if len(blocks) > 3:
            bold_many.append(f"L{i+1}({len(blocks)}处)")
        # 门槛 30 字: 短条目 (术语名 + 并列项) 加粗占比天然偏高, 属正常, 不查
        if n_vis >= 30 and n_bold / n_vis > 0.4:
            bold_ratio.append(f"L{i+1}({n_bold}/{n_vis})")
    _flush_sec()

    results.append(("无整条全加粗(>=15字)", "PASS" if not bold_full else "FAIL",
                    "; ".join(bold_full) +
                    " (整条被一对 ** 包裹 = 无扫读锚点; 只粗术语名/并列项/口诀, 说明留普通字)"
                    if bold_full else "ok"))
    results.append(("单条加粗块<=3(WARN)", "PASS" if not bold_many else "WARN",
                    "; ".join(bold_many) + " (第4处起删掉或拆条)" if bold_many else "ok"))
    results.append(("单条加粗占比<=40%(>=30字,WARN)", "PASS" if not bold_ratio else "WARN",
                    "; ".join(bold_ratio) + " (整条在涂色, 只留术语与结论)"
                    if bold_ratio else "ok"))
    results.append(("单节平均加粗块<=2.5(WARN)", "PASS" if not hot_sec else "WARN",
                    "; ".join(hot_sec) + " (该节把说明也粗了, 每条只留术语名/并列项/口诀)"
                    if hot_sec else "ok"))

    # 11. 加粗 flanking 配对 / 渲染断裂 (2026-09-03 用户定; 2026-09-05 补标点邻位)
    #     CommonMark 规定: 开启 ** 的【右侧】必须非空白 (left-flanking);
    #     闭合 ** 的【左侧】必须非空白 (right-flanking)。
    #     任一不满足 → 该 ** 不被当作定界符, 配对整体错位, Obsidian 会把中间一大段
    #     (甚至跨到下一对 **) 一起加粗, 视觉表现「前段粗、后段没粗」「冒号后整段被粗」。
    #     典型坏写法: "**可乘性 (易错点) **: ..."
    #                                ↑ 这个空格让闭合 ** 失去 right-flanking 资格
    #     正确:      "**可乘性 (易错点)**: ..."  ← 闭合 ** 紧贴 )
    #     ⚠️ 初版用「行内 ** 出现奇数次」判定, 完全抓不到本类 bug ——
    #        这种坏写法里 ** 恰好出现偶数次 (4 次), 只是 flanking 错位。该判定已废弃。
    #     2026-09-05 补充【标点邻位】判定 (此前只查空白, 漏掉 L13 实锤事故):
    #       CommonMark 的 flanking 对标点还有第二条约束 ——
    #       * 开启 **: 若【右侧】是标点 (如 $ 或引号), 则【左侧】必须是 行首/空白/标点;
    #         否则 left-flanking 不成立 (例: 值域**$(0,+∞)$** 的 ** 开不了);
    #       * 闭合 **: 若【左侧】是标点 (如右括号/引号), 则【右侧】必须是 行尾/空白/标点;
    #         否则 right-flanking 不成立 (例: (列数)**而非方程个数 的 ** 合不上, 粗体整段失效)。
    #     判别: 按行内出现顺序交替定角色 (第 1/3/5 个 = 开启, 第 2/4/6 个 = 闭合),
    #           开启查右邻、闭合查左邻: 空白必 FAIL; 邻位为标点时再查另一侧,
    #           另一侧为汉字/字母 (非空白非标点) 也 FAIL。
    flank_bad = []
    for i, ln in enumerate(lines):
        if fence_inside[i]:
            continue
        s = re.sub(r"`[^`]*`", "", ln)  # 去内联代码
        s = re.sub(r"!?\[\[[^\]]*\]\]", "", s)  # 去 wikilink
        s = re.sub(r"\\\*\*", "", s)  # 去转义 \**
        for k, m in enumerate(re.finditer(r"\*\*", s)):
            if k % 2 == 0:  # 开启 **: 右侧非空白, 且右邻为标点时左邻须空白/标点/行首
                nxt = s[m.end():m.end() + 1]
                if nxt == "" or nxt.isspace():
                    flank_bad.append(f"L{i+1}(第{k+1}个**右侧空白)")
                elif nxt in PUNCT:
                    prv = s[m.start() - 1:m.start()] if m.start() > 0 else ""
                    if prv != "" and prv not in WHITESPACE and prv not in PUNCT:
                        flank_bad.append(f"L{i+1}(第{k+1}个**开启失效:右侧紧贴标点{prv+nxt!r}…左邻须空白/标点)")
            else:  # 闭合 **: 左侧非空白, 且左邻为标点时右邻须空白/标点/行尾
                prv = s[m.start() - 1:m.start()] if m.start() > 0 else ""
                if prv == "" or prv.isspace():
                    flank_bad.append(f"L{i+1}(第{k+1}个**左侧空白)")
                elif prv in PUNCT:
                    nxt = s[m.end():m.end() + 1]
                    if nxt != "" and nxt not in WHITESPACE and nxt not in PUNCT:
                        flank_bad.append(f"L{i+1}(第{k+1}个**闭合失效:左侧{prv!r}为标点,右邻{nxt!r}须空白/标点)")
    results.append(("加粗 ** flanking 配对(无渲染断裂)",
                    "PASS" if not flank_bad else "FAIL",
                    "; ".join(flank_bad[:20]) +
                    (f" ...(+{len(flank_bad)-20})" if len(flank_bad) > 20 else "") +
                    " (开启**右侧 / 闭合**左侧不得为空白, 否则该**不成定界符、配对错位, "
                    "会把中间一大段一起加粗; 修法: 删掉那个空格让 ** 紧贴目标短语, "
                    "见 references/bold-keyterm-rules.md 第 9 条)"
                    if flank_bad else "ok"))

    # 图片引用落地 / 内部锚链 / 𒋙 码位 / 图片缩进 (纯追加, 不影响上面既有检查项)
    results += check_figures_anchors(lines, fence_inside, path, since_min)

    return results


def check_figures_anchors(lines, fence_inside, path, since_min=None):
    """图片引用落地 / 内部锚链 / 𒋙 码位 / 图片缩进形态。

    只查机械可判定的那一半; "本次该有几张图" 属会话语义, 脚本查不了, 仍由人工数一遍。
    """
    results = []
    n = len(lines)

    def in_fence(i):
        return i < len(fence_inside) and fence_inside[i]

    # --- 1. 图片引用目标必须真实存在 (占位图名 xxx.png 之类跳过) ---
    img_targets = []
    for i, l in enumerate(lines):
        if in_fence(i):
            continue
        for m in re.finditer(r"!\[\[([^\]|#]+)", l):
            img_targets.append(m.group(1).strip())
        for m in re.finditer(r"\[\[([^\]|#]+)\|图片\]\]", l):
            img_targets.append(m.group(1).strip())
    img_targets = [t for t in img_targets if os.path.splitext(t)[1].lower() in IMG_EXT]
    missing = []
    basename_idx = None
    for t in img_targets:
        if PLACEHOLDER_RE.search(t):
            continue
        if os.path.isfile(os.path.join(VAULT_ROOT, t)):
            continue
        if basename_idx is None:  # 仅在确有疑似缺失时才建索引, 避免每次全库遍历
            basename_idx = set()
            for root, _, files in os.walk(VAULT_ROOT):
                if ".obsidian" in root or ".trash" in root:
                    continue
                for fn in files:
                    basename_idx.add(fn.lower())
        if os.path.basename(t).lower() in basename_idx:
            continue
        missing.append(t)
    if missing:
        results.append(("图片引用落地(引用目标必须真实存在)", "FAIL",
                        f"{len(missing)} missing: {'; '.join(missing[:5])}"
                        "  -> 图必须先渲染成 PNG 存 images/ 再引用, 见 checklist #17"))

    # --- 2. 内部锚链 [[#X]] 必须命中本文件某标题 (^block 引用跳过) ---
    heads = set()
    for i, l in enumerate(lines):
        if in_fence(i):
            continue
        m = HEADING_RE.match(l)
        if m:
            heads.add(m.group(2).strip())
    dead = []
    for i, l in enumerate(lines):
        if in_fence(i):
            continue
        for m in re.finditer(r"\[\[#([^\]|#]+)", l):
            a = m.group(1).strip()
            if a.startswith("^") or a in heads:
                continue
            dead.append(a)
    if dead:
        results.append(("内部锚链目标存在(须命中本文件标题)", "FAIL",
                        f"{len(dead)} dead: {'; '.join(dead[:5])}"
                        "  -> 锚点文本须与标题逐字同码位一致, 见 checklist #18"))

    # --- 3. 𒋙 码位: U+2621 是历史误写, 会让锚链静默失效 ---
    wrong_cnt = 0
    for i, l in enumerate(lines):
        if in_fence(i):
            continue
        wrong_cnt += l.count(ANCHOR_MARK_WRONG)
    if wrong_cnt:
        results.append(("𒋙 码位(U+122D9)", "FAIL",
                        f"{wrong_cnt} 处 U+2621(☡) 误写, 正确码位是 U+122D9(𒋙); "
                        "错一个码位锚链即静默失效, 见 checklist #18"))

    # --- 4. 图片缩进形态: 同文件内 Tab / 空格不得混用; 空格须为 4 或 8 ---
    emb = [(i, l) for i, l in enumerate(lines)
           if not in_fence(i) and re.match(r"^[\t ]*!\[\[", l)]
    if emb:
        has_tab = any(l.startswith("\t") for _, l in emb)
        has_sp = any(re.match(r"^ +!\[\[", l) for _, l in emb)
        if has_tab and has_sp:
            results.append(("图片缩进形态一致(同文件内)", "WARN",
                            "同一文件内 Tab 与空格缩进混用"
                            "  -> 跟随目标文件既有形态: 全 Tab 或全 4 空格, 见 checklist #12"))
        bad = []
        for i, l in emb:
            m = re.match(r"^( +)!\[\[", l)
            if m and len(m.group(1)) not in (4, 8):
                bad.append(f"L{i+1}({len(m.group(1))}空格)")
        if bad:
            results.append(("图片嵌入缩进(须 4 或 8 空格)", "WARN",
                            "; ".join(bad[:10]) +
                            (f" ...(+{len(bad)-10})" if len(bad) > 10 else "") +
                            "  -> 隶属 4 空格, 更深一层 8 空格, 见 checklist #12"))
    return results


def check_new_text(new_text, tool, path):
    """只查"本次新增文本"的项 —— 整文件扫描会误伤用户人工标记。

    tool == "Edit": new_string 就是本次新增, == / \\boxed 判 FAIL (零误伤)。
    tool == "Write": content 是整篇, 脚本无从区分"AI 新加"与"用户原有的人工标记"
      (PostToolUse 时磁盘已是新版, 无旧版可比对), 只能降为 WARN 由人眼确认。
    依据: 全库 1710 个 md 中 546 个含 == (5097 处)、36 个含 \\boxed (693 处),
      整文件 FAIL 会判死三分之一 vault, 故只查新增。
    """
    results = []
    if not new_text or not new_text.strip():
        return results
    t = re.sub(r"```.*?```", "", new_text, flags=re.S)   # 去代码块
    t = re.sub(r"`[^`\n]*`", "", t)                      # 去行内代码
    nl = t.split("\n")
    lvl = "FAIL" if tool == "Edit" else "WARN"

    # --- 1. == 与 \boxed 是用户人工标记, AI 只可读不可写 ---
    marks = []
    for i, l in enumerate(nl, 1):
        if "==" in l:
            marks.append(f"新增L{i}: == 高亮")
        if "\\boxed" in l:
            marks.append(f"新增L{i}: \\boxed")
    if marks:
        results.append(("本次新增内容无 == / \\boxed", lvl,
                        "; ".join(marks[:10]) +
                        (f" ...(+{len(marks)-10})" if len(marks) > 10 else "") +
                        "  -> == 与 \\boxed 是用户人工画重点的专属标记, AI 只可读不可写, 见 checklist #4; "
                        "若本次是用户点名搬运他自己标的 == -> 属已知豁免, 保留并在回复里说明"))

    # --- 2. 新增"补充"类节须回挂反向锚链 (WARN: 常分两次 Edit, 先加节后挂链) ---
    try:
        whole = open(path, encoding="utf-8", errors="replace").read()
    except OSError:
        whole = t
    supp = []
    for l in nl:
        m = re.match(r"^#{1,6}\s+(.*)$", l)
        if m and "补充" in m.group(1):
            title = m.group(1).strip()
            if "[[#" + title not in whole:
                supp.append(title)
    if supp:
        results.append(("新增补充节已回挂反向锚链", "WARN",
                        "; ".join(supp[:5]) +
                        "  -> 须在原内容所在行尾挂 [[#" + supp[0] + "|文末有…解释]], 见 checklist #18"))

    # --- 3. 新增图片缩进须跟随文件既有形态 ---
    new_emb = [l for l in nl if re.match(r"^[\t ]*!\[\[", l)]
    if new_emb and whole is not t:
        base_emb = [l for l in whole.split("\n")
                    if re.match(r"^[\t ]*!\[\[", l) and l not in new_emb]
        b_tab = sum(1 for l in base_emb if l.startswith("\t"))
        b_sp = sum(1 for l in base_emb if re.match(r"^ +!\[\[", l))
        if b_tab or b_sp:
            main = "tab" if b_tab > b_sp else "space"
            for l in new_emb:
                is_tab = l.startswith("\t")
                is_sp = bool(re.match(r"^ +!\[\[", l))
                if (main == "tab" and is_sp) or (main == "space" and is_tab):
                    results.append(("新增图片缩进跟随文件既有形态", "FAIL",
                                    f"文件主流是{'Tab' if main == 'tab' else '空格'}缩进, "
                                    "本次新增用了另一种 -> 同一文件内必须一致, 见 checklist #12"))
                    break
    return results


def check_temp(temp_dir: str, since_min=None):
    """临时目录图片纪律。
    since_min 给定时, 只把 mtime 在最近 since_min 分钟内的图片判为 FAIL(视为本次任务产出);
    更旧的图片只作 INFO 列出, 不判 FAIL、不得删改 —— 与「任务范围纪律: 只做本次任务的文件」一致,
    避免把用户自己放在临时目录的历史图片当成违规删掉/移走。
    """
    results = []
    if not os.path.isdir(temp_dir):
        results.append(("临时目录存在", "FAIL", f"not found: {temp_dir}"))
        return results
    now = time.time()
    img_files = []
    old_img_files = []
    for root, _, files in os.walk(temp_dir):
        for fn in files:
            if fn.lower().endswith(TEMP_IMG_EXT):
                p = os.path.join(root, fn)
                try:
                    age_min = (now - os.path.getmtime(p)) / 60.0
                except OSError:
                    age_min = 0.0
                if since_min is not None and age_min > since_min:
                    old_img_files.append(p)
                else:
                    img_files.append(p)
    if old_img_files:
        shown = "; ".join(os.path.relpath(p, temp_dir) for p in old_img_files[:20])
        more = "" if len(old_img_files) <= 20 else f" ...(+{len(old_img_files)-20})"
        results.append(("临时目录历史图片(非本次任务, 不动)", "INFO",
                        f"{len(old_img_files)} image(s) older than {since_min}min: {shown}{more}"
                        "  -> 非本次任务产出, 不删不移(越界动用户文件比留一张图严重)"))
    if img_files:
        shown = "; ".join(os.path.relpath(p, temp_dir) for p in img_files[:20])
        more = "" if len(img_files) <= 20 else f" ...(+{len(img_files)-20})"
        results.append(("临时无图片残留(want 0)", "FAIL",
                        f"{len(img_files)} image(s) in temp: {shown}{more}  -> 移到 images/ 或删除"))
    else:
        results.append(("临时无图片残留", "PASS", "clean"))

    rec = os.path.join(temp_dir, "临时记录.md")
    if os.path.isfile(rec) and os.path.getsize(rec) > 0:
        results.append(("临时记录.md 待核查(WARN)", "WARN",
                        "存在非空临时记录.md: 若其内容已转写他处, 须清空为 0 字节"))
    return results


def print_results(results, title):
    print("=" * 60)
    print(title)
    print("=" * 60)
    fails = 0
    warns = 0
    for name, status, detail in results:
        if status == "FAIL":
            fails += 1
            mark = "XX "
        elif status == "WARN":
            warns += 1
            mark = "!! "
        elif status == "INFO":
            mark = ".. "
        else:
            mark = "OK "
        print(f"[{mark}] {name}")
        if detail:
            print(f"       {detail}")
    print("-" * 60)
    if fails:
        print(f"RESULT: {fails} FAIL(S), {warns} WARN")
    elif warns:
        print(f"RESULT: ALL PASS ({warns} WARN)")
    else:
        print("RESULT: ALL PASS")
    print("=" * 60)
    return fails


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args:
        print("usage:")
        print("  verify_discipline.py <md-path>            # 通用格式纪律")
        print("  verify_discipline.py --temp-check [--since-min 120]  # 临时文件夹纪律(只判最近120分钟新增图)")
        print("  verify_discipline.py --all <md-path>      # 通用格式 + 临时")
        print("  verify_discipline.py --temp-dir DIR --temp-check")
        print("  (仅 hook 使用, 勿手工带) --new-text-stdin --new-text-tool Edit  <md-path>")
        sys.exit(2)

    temp_dir = DEFAULT_TEMP_DIR
    if "--temp-dir" in args:
        idx = args.index("--temp-dir")
        if idx + 1 < len(args):
            temp_dir = args[idx + 1]

    since_min = None
    if "--since-min" in args:
        i = args.index("--since-min")
        if i + 1 < len(args):
            try:
                since_min = float(args[i + 1])
            except ValueError:
                since_min = None
    # 仅 hook 使用: 从 stdin 读"本次新增文本"(Write 传 content, Edit 传 new_string)。
    # 手工跑时不要带这两个参数 —— 带 --new-text-stdin 会一直等 stdin。
    new_text = ""
    new_text_tool = "Write"
    if "--new-text-stdin" in args:
        new_text = sys.stdin.buffer.read().decode("utf-8", "replace")
    if "--new-text-tool" in args:
        i = args.index("--new-text-tool")
        if i + 1 < len(args):
            new_text_tool = args[i + 1]

    do_temp = "--temp-check" in args
    do_all = "--all" in args
    md_path = None
    skip_next = False
    for a in args:
        if skip_next:
            skip_next = False
            continue
        if a in ("--temp-dir", "--since-min", "--new-text-tool"):
            skip_next = True
            continue
        if not a.startswith("--") and a not in (temp_dir,):
            md_path = a
            break

    total_fails = 0
    if do_all:
        if not md_path or not os.path.isfile(md_path):
            print(f"ERROR: md path not found: {md_path}")
            sys.exit(2)
        total_fails += print_results(check_format(md_path),
                                     f"VERIFY (format+temp): {md_path}")
        total_fails += print_results(check_temp(temp_dir, since_min),
                                     f"VERIFY (temp): {temp_dir}")
    elif do_temp:
        total_fails += print_results(check_temp(temp_dir, since_min),
                                     f"VERIFY (temp): {temp_dir}")
    else:
        if not md_path or not os.path.isfile(md_path):
            print(f"ERROR: md path not found: {md_path}")
            sys.exit(2)
        total_fails += print_results(check_format(md_path),
                                     f"VERIFY (format): {md_path}")

    if new_text.strip():
        total_fails += print_results(
            check_new_text(new_text, new_text_tool, md_path or ""),
            "VERIFY (本次新增内容)")

    sys.exit(1 if total_fails > 0 else 0)
