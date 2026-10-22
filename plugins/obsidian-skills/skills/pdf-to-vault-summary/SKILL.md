---
name: pdf-to-vault-summary
description: 'Convert a PDF (study notes, exam 教资/考研 material, lecture handouts, any local PDF in the vault) into a vault-content-summary style markdown and save it as <same-basename>.md in the SAME folder as the PDF. Uses LIGHT summarization (restore as much source text as possible, do not over-compress) and follows the vault-content-summary format (𒋙 headings, no numbering, English half-width punctuation, bolded key terms, INLINE source links to the PDF page using the link-alias form `[[name.pdf#page=N|pdf]]`). If an SRT subtitle file is also provided alongside the PDF, fuses subtitle content (oral examples, mnemonics, emphasis) into the markdown as a supplementary layer with inline audio timestamp links `[[name.m4a#t=<seconds>|音频]]` (#t=seconds). Trigger: user says "把pdf转md", "把这个pdf总结成md", "转成同名md到同一个文件夹", "pdf转笔记", or any request to turn a specific PDF file into a markdown summary inside the vault.'
agent_created: true
summary: '把本地 PDF / mp4 / m4a / SRT 转成 vault 体例 md 时先加载（唯一入口）—— 输出同名 .md 到源同文件夹；同时过 vault-write-discipline 的 checklist #14 与 #15。'

---

# PDF → Vault-Content-Summary Markdown

Turn a local PDF into a clean, exam-ready markdown note in the **vault-content-summary**
format, written next to the original PDF (same folder, same basename, `.md` extension).
This is the format the user explicitly requires for ALL generated vault content, applied here
to a PDF source. The default stance is **light summarization** — preserve as much of the PDF's
actual text (考点, 真题 material, 参考答案, 口诀) as possible; compress only for readability,
never into one-line stubs.

## When to use
- User points at a concrete PDF file in the vault and wants a markdown version / summary of it.
- User says "转成同名md", "总结成md到同一个文件夹", "pdf转md", "把这个pdf整理成笔记".
- The output should live in the SAME folder as the PDF (NOT the 临时 default) unless the user
  says otherwise that turn.

## Output location (IMPORTANT)
- Output path = `dirname(pdf) / (basename(pdf) without .pdf) + ".md"`.
- Example: `<vault>\2026上数学教资\2026科2教育知识与能力\主观题\第四章学习心理主观题4.pdf`
  → `<vault>\2026上数学教资\2026科2教育知识与能力\主观题\第四章学习心理主观题4.md`.
  （示例路径只说明"输出到源同文件夹同名 .md"这一条；**目录名会随改名而变，需要时 `ls` 现查**，不要照抄这里的目录名。）
- This OVERRIDES the vault-content-summary default of writing to `<vault>\临时\`. Same-folder
  output is the user's standing instruction for this skill.

## Workflow

### 1. Extract text from the PDF
Use the managed Python + pdfplumber. If the venv is missing, create it and install deps first.

```bash
# WorkBuddy 托管 venv(已就绪, 无需再建): ~/.workbuddy/binaries/python/envs/default/Scripts/python.exe
# (旧注"DSH 独立环境"已过时——DSH 已于 2026-09-10 停用, 该 venv 与 DSH 无关)
# 依赖 pdfplumber/pypdf 已装于该 venv
```

Then run the bundled extractor (pass the PDF absolute path):

```bash
~/.workbuddy/binaries/python/envs/default/Scripts/python.exe \
  "$HOME/.workbuddy/skills/pdf-to-vault-summary/scripts/extract_pdf_text.py" "<PDF_PATH>"
```

- **Auto OCR on image-only PDFs (no need to ask)**: if the extracted text is mostly empty
  (scanned / image-based PDF), do NOT stop and ask the user — automatically run the bundled
  `ocr_pdf_text.py` (LOCAL engine: **PaddleOCR only** — switched 2026-10-11; Tesseract was
  uninstalled 2026-10-07 per user; cloud OCR was removed 2026-09-01 per user). Pipe its `===== PAGE N =====` output straight
  into the summary step below.

- The script prints `===== PAGE N =====` blocks so you can map each piece of content to its
  source page number (you will need the page numbers for the per-item source links).
- If most pages come back EMPTY, the PDF is scanned/image-based. Fall back to OCR with the
  bundled helper (renders via **PyMuPDF** — NO poppler needed — then OCRs):
  ```bash
  # OCR default path: GLM-4V-Flash (free vision model) with offline PaddleOCR as safety net
  ~/.workbuddy/binaries/python/envs/paddle/Scripts/python.exe \
    "$HOME/.workbuddy/skills/pdf-to-vault-summary/scripts/ocr_pdf_text.py" "<PDF_PATH>"
  ```
  - **Engine priority (user rule, 2026-10-08) — top tier wins if usable:**
    1. **`glm`** — Zhipu **GLM-4V-Flash**, free vision model (key already set as `ZHIPUAI_API_KEY`).
       Best accuracy, keeps table layout and numbering. **This is the default**; it auto-falls-back
       on missing key / HTTP error / empty page result. Cost: one API call per page, so
       long PDFs are slow — throttle with `--max N`, or drop to tier 3 for bulk runs.
    2. **`tencent`** — Tencent Cloud GeneralAccurateOCR (1000/month free quota). Deliberately
       **NOT wired into this script and never auto-triggered**: it draws down the user's cloud
       quota. Invoke skill `tencentcloud-ocr` **by hand** only when you need higher fidelity on
       printed text and have confirmed quota remains.
    3. **`paddleocr`** — local & offline (GPU, PP-OCRv6 中文), no key, no quota. The always-available safety net.
  - `--engine` accepts `glm|paddleocr|auto`; `auto` = try glm, then PaddleOCR.
  - **逐页失败隔离（2026-10-18 实装）**：GLM 单页失败不再 raise 炸整本——该页记 `(pno, None, err)`，由 `_fill_failed_pages` 用 PaddleOCR 单独补齐，其余页仍保留 GLM 结果；**连续 3 页失败**才判整体不可用、整本走 PaddleOCR 兜底。`auto` / `glm` 两个分支都接了这条链路。
    **`tesseract` is gone, not just dead** — the binary was uninstalled on 2026-10-07 (never in PATH,
    `tessdata` lacked `chi_sim`, so it never actually ran), and the code branch was removed on
    2026-10-11. **Never suggest reinstalling it as a fallback; there is no tier below PaddleOCR.**
    (Same for EasyOCR: uninstalled 2026-10-11 along with its torch/scipy deps — it is not a fallback either.)
  - **⚠️ External-reference note (added 2026-09-23, updated 2026-10-08)**: skill `tencentcloud-ocr`'s
    quota message says "switch to Zhipu OCR (`pdf-to-vault-summary`'s `--engine zhipu`)" — the real
    name is **`glm`**, not `zhipu`; following that wording verbatim throws a usage error. This section
    is the single source of truth; do not patch the third-party package (no `agent_created`, market
    updates would overwrite it).
  - One-time setup already done in the paddle venv (`~/.workbuddy/binaries/python/envs/paddle`): `paddlepaddle-gpu` + `paddleocr` (PP-OCRv6 模型已缓存). (**No tier below this** — see above.)
  - **Auto-trigger, do NOT ask first**: when the initial pdfplumber extraction returns mostly empty pages (image-only / scanned PDF), automatically run `ocr_pdf_text.py` (default `--engine auto` = GLM then local PaddleOCR) and feed the OCR text straight into the summary without pausing to ask the user.

### 2. Identify logical sections
Group the extracted content into the PDF's own sections (考点 blocks, 真题 material+参考答案,
理论 lists, 口诀). Keep the PDF's section order. Do NOT invent new categories the PDF lacks.
**例外（带背稿 / 讲义类，2026-09-09 补）**：PDF 条目顺序与讲师口述（口诀）顺序冲突时，**按讲师顺序排**——
带背稿的价值在"照口诀背出来"，且能让 `mp4#t=` 单调递增、避开 ORDER? 软提示（带背6 的 83/84/86 题即如此）。
见工作区 `.workbuddy/memory/MEMORY.md`「冲刺带背系列」节（单一真源，本 skill 不复写其正文）。
**（例外型冲突——永久例外, 不进收敛队列; 判据是"本次用户有没有就顺序点名/拍板"（带背稿·讲义类只是它的典型命中场景, 不是判据本身）, 不得写成文件名单。见 `rules-consistency-audit`「冲突收敛准则」第 1 条。）**

### 3. Write the markdown in vault-content-summary format

**写前先加载 `vault-write-discipline` skill, 过其 Pre-Write Checklist #14(隶属/并列分行缩进)与 #15(加粗判定)** —— 这两条的单一真源分别在 `vault-write-discipline` 本体与 `references/bold-keyterm-rules.md`, 本 skill 不再重复定义, 仅在此补充 PDF 场景的具体落法 (见规则 3 末段与规则 4).

Apply these HARD rules (mirrors the vault-content-summary skill, which is the user's default
file format):

1. **Title → category, no intro.** File starts with one H1 `# 𒋙<topic title>`, then DIRECTLY
   the first `## 𒋙category` — no intro paragraph, no blank line after the H1.
2. **Category headings**: `## 𒋙<category>` prefixed with 𒋙 and **NO numbering** (no Arabic, no
   一、二、). Use `### 𒋙<sub>` ONLY when a `##` genuinely contains subsections (containment),
   not merely because there are many.
   **Exception (user override, 2026-09-09):** 广哥点名去掉 `𒋙` 的**标题**从其令——`𒋙` 是默认值而非硬约束，判据是"本次用户有没有点名"，不是文件类型。**⚠️ 同一文件 / 同一系列里带 `𒋙` 与不带 `𒋙` 常长期并存（逐次点名决定，不按文件整批统一），故引用时一律现读目标标题原文、不许按"哪个文件"推断**。**（属**例外型**冲突——永久例外, 不进收敛队列, 见 `rules-consistency-audit`「冲突收敛准则」第 1 条。）**
3. **⚠️ RESTORE content, do NOT compress it (user flagged this repeatedly).** Write the PDF's
   actual sentences, examples, 真题 material (keep verbatim), and 参考答案 points (keep verbatim,
   including every ① ② ③ sub-point AND the explanatory sentences between them). Dropping content is the recurring failure mode — the source must be respected, not summarized away.

   Only legitimately omit: (a) blank/填空 practice re-prints of the same 考点 (pages showing only
   "准确的（ ）" etc.); (b) pure decoration — cover pages, page numbers, repeated "考点一"
   stamps, the vertical decoration column, "谢谢大家"; (c) verbatim-duplicated generic blocks
   that already appear once in the 措施类通用答题思路 section. NEVER shrink a multi-sentence answer
   into a one-line stub. **这一条是用户反复强调的硬要求: 宁可长, 不可丢。**
   **(d) 带背稿 / 讲义类 (2026-09-09 补): 讲师本场未讲到的题**——这类材料按"**本场实际讲到的范围**"写, 未讲到的题留待后续场次,
   **不算丢内容**; 覆盖范围的三条约定见工作区 `.workbuddy/memory/MEMORY.md`「冲刺带背系列」节 (单一真源, 本 skill 不复写正文)。
   **RESTORE 只指文字逐字保留, 排版必须按用户分行规则拆开** (2026-09-04 用户复核补): PDF 排版上的 ① ② ③ ...
   并列答题要点 **禁止整段挤在一行**, 必须写成题干条目下 4 空格缩进的 `    N. ` 子列表;
   文字内容逐字保留、只重排版, 口诀可并入题干行; **链接落位按本文件有没有 `mp4#t=` 走两套**: 有(带背稿 / 讲义 / PDF+SRT 融合) → **每个子点各挂自己的落点**(逐条双链接, 秒数互异, 见 `### 4.` 判据与 `### 6.`); 无(纯 PDF 转 md) → pdf 链接组集中贴在该考点最后一个子点的行尾 (Mode B).
   单一真源: `vault-write-discipline` Pre-Write Checklist #14 (隶属→4空格、并列→分行同缩进、最多 2 级 ≤8 空格).
   反例 (2026-09-04, 科目二冲刺带背1 初版): `1. 生产力如何影响教育?...① 决定...② 制约...③ 制约...④ 制约...`
   一行挤 4-5 个并列子点 → 用户当场质疑"为什么没用分行规则".
4. **Bold key terms** (e.g. **准备律**, **功能固着**, **先行组织者**). Bold mnemonics (口诀) too.
   **加粗判定以 `../vault-write-discipline/references/bold-keyterm-rules.md` 为单一真源** (2026-09-04 用户复核补):
   口诀必粗、被定义项名粗、并列分类项名粗、采分名词适度粗; 答题展开文字里的动词/说明/理由/例子一律不粗.
   密度硬指标 (**2026-09-28 更新**): 单条加粗块 —— ≤60 可见字者 ≤3、>60 可见字且已按规则 14 拆行者以 ≤5 **为基准、按整条可见字数浮动上调**(每再长约 60 字 +1 处; **2026-09-29 用户定: 上限按内容长短定**), **一律按「整个条目」合并计、不按物理行计**; ≥30 字条目加粗占比 ≤40%; 整条全粗 ≥15 字 FAIL (verify_discipline.py 会查). 脚本阈值仍写 3 / 2.5, 滞后于本处的 5 / 3.5, 相应 WARN 属已知豁免 (三条前提见 `../vault-write-discipline/references/bold-keyterm-rules.md` 第 4 节).
   反例 (科目二冲刺带背1 初版): 一个答题点一行粗 15 处 (`决定/制约/规模/速度/培养规格...` 整段涂色) = 加粗连成一片等于没粗.
5. **Bold-adjacent punctuation rule (CommonMark/Obsidian):** a `**...**` span silently FAILS
   when punctuation touches `**` from the INSIDE. Punctuation OUTSIDE the span is fine. Fix
   PROACTIVELY: move the punctuation outside the bold — write `**注意的范围**(广度)`,
   `**麦积山**(2014)`, `"**term**"`. When you must keep punctuation inside, insert a
   zero-width space `\u200B` at the inner edge, or use `<b>...</b>`.
6. **English (half-width) punctuation** in all prose: `, . ; : " " ( ) ! ?` instead of full-width Chinese `，。、；："（）！？`. This INCLUDES the enumeration comma 顿号 `、` — in English-punctuation style `、` becomes a half-width comma `,` (do NOT keep `、` on the grounds that "Chinese has no English equivalent"; it is still full-width Chinese punctuation and must be converted). Only `…` (ellipsis) and `·` (middle dot) are exempt — they are typographic, not in this set. Inside `[[ ]]` / `![[ ]]` keep the exact target text (not free prose).
   （同口径亦见 `vault-content-summary` 规则 6，**真源在 `vault-write-discipline` Pre-Write Checklist #4**。两处各存一份供就近阅读，改一处必须同步另一处。）
7. **⚠️ NO BLANK LINES ANYWHERE — the #1 discipline failure mode (user has flagged this
   repeatedly).** There must be ZERO empty lines in the entire file: not after the H1, not between
   items, not between sections, not before/after any `##`/`###` heading. The H1 title, every
   `##` heading, every `1.` item (with its inline `[[link|alias]]` written directly at the end of the text line) run back-to-back
   with NO blank line separating ANY of them — even the H1 is immediately followed by the first
   `##` (no blank line). If you feel like adding a blank line "for readability", STOP — that is
   exactly the mistake made before. Final check: scan the written file and count blank lines; the
   answer MUST be 0, or you have failed this rule.
   **唯一空行例外（与 `vault-write-discipline` checklist #1 同源）**：`> [!NOTE]` callout 块**前**那一个空行**必须保留**，
   不计入上面的 0；删空行时按「下一行以 `> [!NOTE]` 开头则保留该空行」处理。
8. **Numbered list markers**: exactly one space after the period (`1. ` not `1.  `). **Use EXPLICIT
   incrementing numbers (1. 2. 3. ...) — do NOT use lazy numbering (writing `1.` on every line).**
   The user's Obsidian does NOT auto-increment lazy `1.` items; they all render as `1`. So within each
   `##`/`###` section, number items 1., 2., 3. explicitly and reset to 1 at each new heading.
9. **Prefer ordered lists; add at most ONE sub-level heading for a clearly DIFFERENT aspect.** Do NOT
   make a heading for every parallel member of ONE category — keep those as an ordered list. E.g. the 4
   气质类型, the 9 加德纳智力, the 8 认知风格, the 4 性格结构特征, the 4 人格特征, the 3 自我意识成分,
   and 奥尔波特的 首要/中心/次要 特质 are ALL parallel members of their parent and stay as list items
   (1. 2. 3. …), NOT headings. Only when a section clearly contains a SEPARATE aspect of content —
   typically the supplementary material that follows the core definitions (教育启示 / 职业推荐 / 做题技巧
   / 真题 / 口诀) — may you break that aspect out under a single LOWER-LEVEL heading (e.g. `#### 𒋙补充内容`
   under a `###`, or `### 𒋙补充内容` under a `##`). The 补充内容 heading is ALWAYS exactly ONE level
   below its parent (`###` under `##`, `####` under `###`, `#####` under `####`, …) — never skip a
   level. Obsidian supports at most 6 heading levels (H1–H6): if the parent is ALREADY H6 (`######`),
   do NOT create a `#######` (invalid); instead just append a new ordered list (no heading) for the
   supplementary content directly under that H6 parent. The guiding principle is MINIMAL headings — do
   not over-split.
   **适用范围（2026-09-26，消解层级口径不一）**：本条的 `####` / `#####` 多级链**仅适用于本 skill 的「补充内容」子标题**；其他 skill 的汇总场景（如 `vault-content-summary`）仍按 `##` / `###` 两级上限，不套本条。
   **补充条目的落点判据（2026-09-24 广哥定）**：给已有文件补充对照图/串记条时，落点按**题型归属**判定——依据类的内容落到依据类标题下续编，**不按"最初提问时点名的那个标题"**判定。
   **新增行不挂落点链接（2026-09-24 广哥定）**：给带背稿/刷题笔记**新增**的子项/串记条，内容若含视频与 PDF 之外的课标、教材例证，**不挂 `pdf#page=` / `mp4#t=` 落点链接**——落点对不上必然错挂，宁可不挂（实例：科二刷题 181 条"小学科学=广域课程"下补的子项 3-5）。
10. **Lean toward the rule-9 sub-heading split when the core list is long (>9).** If a section's core
    ordered list would exceed 9 items, pull the clearly-different supplementary aspect into a `补充内容`
    sub-heading so the core list stays ≤9. If the items are ALL the same topic with NO separable
    different aspect (a single long run of same-kind definitions), you CANNOT split — instead MERGE to
    cut the count: (a) FIRST fuse trailing auxiliary blocks (做题技巧 / 真题 / 补充 / 音频补充) into ONE
    item; (b) if STILL over 9, cluster closely-related definitions into one item with each sub-definition
    on its own 3-space-indented soft line. **3 空格软行只是「扁平节超 9 条且无可拆子标题」时的兜底合并手段, 不是并列子点的常规落法**——日常并列子点(如 PDF 上的 ①②③)一律按规则 3 写成 4 空格带标记子列表 (`    N. `); 单一真源: `vault-write-discipline` Pre-Write Checklist #5/#14。Never drop content; never exceed 9 items in a flat section.
    **兜底软行的链接落位 (2026-09-09 补)**: 软行只是**文本换行**, **链接仍按 `### 4.` 内联在该条目文字行尾**——不得挂在软行上、也不得单占一行。
    被 `verify_vault_summary.py` 判 FAIL 的是"**链接放在续行/软行**"这一落法; 3 空格惰性续行本身合法 (见 `vault-write-discipline` checklist #5)。
11. **Consolidate citations — don't repeat a link per short item.** If several consecutive items are
    short one-liners or cite the SAME source page, place the `[[link|pdf]]` ONCE at the end of that
    group/section rather than repeating it after every item. Only give an item its own link when it cites
    a genuinely different page.
12. **No backticks** around any path or link in the deliverable.
13. **⚠️ NO underscore runs for fill-in blanks (observed error 2026-07-27).** Never write
    `______` / `___` in prose — Obsidian's CommonMark parses consecutive underscores as
    emphasis delimiters and the line renders broken. Fill-in placeholders ALWAYS use the
    ellipsis `……` instead: write `所谓……,就是……`, `可见……/这启示我们……`. (The
    normalizer auto-converts `_{2,}` runs outside wikilinks to `……`; the verifier flags any
    that remain.)
    （同口径亦见 `vault-content-summary` 规则 11。两处各存一份供就近阅读，**真源在 `vault-write-discipline`**——改一处必须同步另一处，不要只改一边。）
14. **长条目必须按语义断点拆行 (2026-09-28 用户定; PDF 场景最易踩——口述原话译成书面, 一逗到底)**
    PDF 讲稿里一个知识点常是一大段一口气的话, 转成 md 时**禁止原样贴成一条长行**。判据: **单个条目可见字数 > 60 就拆** (= 首行 + 该条所有无标记 4 空格续行的合并字数; 计算时删 `[[...]]`、`$...$`、`**` 本身与全部空白, 与 verifier 的 `n_vis` 同口径; 肉眼估 = 超过一行半)。
    落法: 首行保留为 `N. ` 列表项, 其余子句写成**连续的无标记 4 空格续行**——**连续多条续行不受"连续两条会 FAIL"那条旧限制约束** (2026-09-28 用户定放开); verifier 的 `顶层裸4空格` 一项**已于 2026-10-21 改为回溯判据、此形态不再报警**（旧判据下曾误报，属已知豁免）, **不得**为消警把行并回去、也**不得**给它们补 `    N. ` / `    - ` 列表标记。
    断点放在: 换主语 / 换时间、"是什么"转到"怎么用" (口诀 · 判据 · 答题步骤)、出现但 · 然而 · 因此这类连词 (连词跟着新行开头)、出现新的限定条件或反例。
    **加粗密度按「整个条目」合并计、不按物理行计**: >60 可见字且已拆行的条目以 ≤5 处为基准、按整条可见字数浮动上调, ≤60 字仍是 ≤3 处; 占比 ≤40% 与"整条被一对 `**` 包裹"两条不变。
    **注: 本条与规则 10 的 3 空格软行是两个场景**——软行只是"扁平节超 9 条"时的兜底合并手段, **拆长句一律用本条的 4 空格续行**, 不要混用两套缩进。
    单一真源: `vault-write-discipline` Pre-Write Checklist #19 (含 5 类断点与三组 ❌/✅) 与 `../vault-write-discipline/references/bold-keyterm-rules.md` 第 4 节 (密度表); 本 skill 不复写其正文。

### 4. Source links (the crux)
The genuine source IS the PDF, so every item must cite its source page. Two linking modes,
choose per section based on density:

**Mode A — per-item link (default, for long items from different pages):**
Each item ends its text line with the source link written **INLINE** directly after the text (same line, no soft-break), using the alias form `[[<basename>.pdf#page=N|pdf]]`:

```
1. <item text...> [[<basename>.pdf#page=N|pdf]]
```

**Mode B — consolidated links (for short items or items from the same page):**
When multiple consecutive items are short (a few words each) or all come from the same page,
write all the text items first, then put all the links together INLINE at the end of the last
item's text line (space-separated, alias form):

```
1. <short item text>
2. <short item text>
3. <short item text> [[<basename>.pdf#page=N|pdf]] [[<basename>.pdf#page=M|pdf]]
```

Rules:
- `<basename>` is the PDF filename without path (e.g. `第四章学习心理主观题4.pdf`).
- `page=N` is the source page number from the extractor.
- This satisfies the no-fabricated-source rule: points back to the real original.
- If all items in a `## 𒋙` section come from the same page, use Mode B: write all items, then one consolidated inline link at the end of the group.
- If items span different pages and are long, use Mode A: per-item inline links.
- Mixed is fine: some sections use Mode A, others use Mode B, within the same file.
- **与「逐条双链接」的优先级 (2026-09-08 定, 消除歧义)**: 判据只有一条 —— **本文件里有没有 `mp4#t=` 视频链接**。有(PDF+SRT 融合 / 带背稿 / 讲义类) → 一律**逐条双链接**, Mode A/B 的合并**不再适用**, 每条各挂自己的 `mp4#t=` 与 `pdf#page=` 且秒数互异; 无(纯 PDF 转 md) → 按 Mode A/B 正常合并 `pdf#page=`。

**Canonical citation-link alias rules (shared with `vault-content-summary`):** the authoritative, single-source list of all alias words (图片 / 视频 / 音频 / pdf / 标题 / 文章) lives at `../shared/citation-link-aliases.md` — both skills follow it. This skill's PDF/音频 alias forms already match it; if you ever cite a `.md` note, use `[[note#heading|标题]]` (heading) or `[[note|文章]]` (whole note) — never the original heading/note title as the alias. When the `.md` note has NO heading, or an exact row is needed, use the Advanced URI line link `[N](obsidian://adv-uri?vault=<vault-id>&filepath=<相对路径,%2F编码>&line=<N>&column=1&openmode=true&view-mode=source)` instead (display = the line number itself, not 标题/文章); `line` is 1-indexed, never pair it with `offset`, and **always include `column=1`** (模板惯例, 与 FakeLink `copyLineUri` 输出一致, 带上无害;**本机未装 Advanced URI, FakeLink 只解析 `filepath` + `line`, `column` 纯透传**——"无 column 时 setCursor 的 ch=NaN 致跳转不可靠"属误归因, 本机无法复现) - details in citation-link-aliases.md.

**Temporary-note fusion also gets source links (2026-08-31 user rule):** these linking rules are NOT
limited to PDF→md jobs. When 临时记录 (`<vault>\临时\临时记录.md`) content is summarized / merged into
another `.md` (temp-note-workflow flow B), every knowledge item must also get its real source link
INLINE at the end of the item text, using the exact same alias forms above. Priority for locating the
source: ① the PDF/video analyzed in the current conversation (measure page via `extract_pdf_text.py`,
seconds via the same-name SRT) — attach `[[x.pdf#page=N|pdf]]` / `[[x.mp4#t=秒|视频]]`; ② local vault
search for the corresponding note heading — attach `[[note#heading|标题]]` or `[[note|文章]]`.
Consolidate: consecutive items from the same source keep ONE link at the last item (Mode B). The
no-fabricated-source rule applies unchanged: if the real source cannot be located, leave the item
linkless — NEVER invent a page number / timestamp / heading.

### 5. Write & present
- Write the file to the same-folder path from step "Output location".

### 6. When audio/video subtitles (SRT) are also available — DUAL COVERAGE (default)

**冲刺班带背稿(如 `科目二冲刺带背N`)另有本工作区三条约定**——以讲师口述为准 / 只写本场实际讲到的题 / PDF 条目顺序与口诀顺序冲突时按口诀排 / 单节超 9 条的拆法。**见工作区 `.workbuddy/memory/MEMORY.md`「冲刺带背系列」节, 动手前先读; 本 skill 不复写其正文**(单一真源原则)。
If the user provides an SRT subtitle file (or .m4a/.mp3/.mp4 with a sibling .srt) alongside
the PDF, fuse the subtitle content into the markdown AND — **by default, whenever a same-name
`.mp4`+`.srt` pair exists — add a `[[<basename>.mp4#t=<seconds>|视频]]` link to EVERY numbered
item**. Every knowledge point then carries BOTH its `[[<basename>.pdf#page=N|pdf]]` page link
AND a video timestamp link. This is the user's standing requirement: when a PDF page is hard
to read, clicking `视频` jumps straight to the teacher's spoken explanation of that exact
point. No separate skill or extra trigger phrase is needed — it is auto-applied.
**Sibling-PDF mandate (IMPORTANT, observed 2026-07-27):** Even when the user's explicit
request names ONLY the `.srt` / `.mp4` / `.m4a` file, ALWAYS check the same folder for a
sibling `<same-basename>.pdf`. If one exists, it is the PRIMARY source for page links — you
MUST run Steps 1-4 on it and add `[[<basename>.pdf#page=N|pdf]]` links. Do NOT skip the PDF
just because the request pointed at the subtitle/video; the SRT/mp4 becomes the supplementary
layer (timestamp links `[[...mp4#t=<seconds>|视频]]`) fused onto the PDF-derived skeleton,
with dual coverage applied to every item.
**越界豁免(2026-09-07 定)**: 上述 sibling-PDF mandate 与本 skill 的 auto-OCR 自动触发, 都属"用户点名文件"的**任务内动作, 不算越界**; 越界禁令(禁扫描目录摸排、禁处理未点名文件、禁收尾提议下一个)只针对**未点名的其他文件**。权威版见用户级 MEMORY「一 每次对话都用的硬偏好」节的「**任务范围**」条（用户级 MEMORY 路径权威版见 `workbuddy-memory` 读取清单第 2 条；凡指向「`.workbuddy` 根目录那份无 `user-*-personal` 前缀的同名 MEMORY」的写法都是过期副本，勿用）。

**Step 1 — Parse the SRT into compact readable text (USE `parse_srt.py`, absolute seconds):**
Run the bundled `parse_srt.py`. It outputs `[绝对秒数] 文本` lines where seconds = `3600*h+60*m+s`,
exactly the form Obsidian `[[mp4#t=秒|视频]]` needs:

```bash
~/.workbuddy/binaries/python/envs/default/Scripts/python.exe \
  "$HOME/.workbuddy/skills/pdf-to-vault-summary/scripts/parse_srt.py" \
  "<SRT_PATH>" "<OUT_PATH>"
```

Read the compact text in batches (Read tool, limit=500-1000) and, for each numbered item,
locate the keyword's **LATER occurrence** (the real teaching segment — see Step 4b).

**Step 2 — Read the compact text and extract supplements:**
Read the compact text in batches (Read tool, limit=500-1000). For each PDF section, identify
content in the subtitles that the PDF does NOT cover:
- Teacher's oral examples (口述案例, e.g. "范进中举是激情的例子")
- Additional mnemonics (口诀, e.g. "爱奇艺感前巨星")
- Easy-to-confuse distinctions (易错点, e.g. "转移vs宣泄看前提条件")
- Teacher's emphasis on key points (强调内容)

**Step 3 — Timestamps are already absolute seconds (no reset math needed):**
`parse_srt.py` outputs `[绝对秒数] 文本` where seconds = `3600*h + 60*m + s`, so each line is
already the exact value Obsidian needs for `[[mp4#t=秒|视频]]`. No hour-reset math required.
Always use `parse_srt.py`; if you ever hand-parse raw `[mm:ss]`, add 3600s per hour boundary
at `\[00:00\]` resets (raw mm:ss drops the hour and breaks videos >1h).

**Step 4 — Fuse supplements into the markdown:**
Two integration patterns:
- **Enrich existing items**: add subtitle content directly into the PDF item's text (e.g. add
  "范进中举是激情的经典例子" to the existing 激情 item). Add the video link alongside the
  existing PDF link INLINE at the end of the item text, space-separated.
- **Add new items**: for content the PDF doesn't cover at all (e.g. "主体性=主观性"),
  add a new numbered item at the end of the section. Prefix with "视频补充:" to distinguish.

**Step 4b — Give EVERY item its video timestamp (dual coverage, scripted):**
1. For each numbered item, search the parsed SRT for a *distinctive* keyword and take the **LATER occurrence** as the real teaching segment — NOT the first hit (the first mention is usually an early example / wrong-statement that jumps to the wrong place). E.g. "五育" first at t=1341 (oral example), real lecture t=4799+; "历史继承性" first t=739, real drill t=2871. If a keyword is too broad ("教学","教育"), use a specific phrase ("特殊的认识过程","福勒布朗","思想品德课").
2. Write `<md_path>.vmap.txt` (same folder), one line per item: `<1-based file line number>\t<seconds>`. **Line numbers = the TRUE 1-based line numbers from the Read tool, NOT an item count.** The md has `# 𒋙` at L1 and `## 𒋙` at L2, so the first numbered item is at L3. (A prior run wrongly put "出题特点"'s link on the H1 title line.)
3. Inject with the bundled script — it appends ` [[<basename>.mp4#t=<seconds>|视频]]` to each mapped line, **skips lines already holding a video link** (idempotent, never duplicates), and derives `<basename>` from the md filename:
```bash
~/.workbuddy/binaries/python/envs/default/Scripts/python.exe \
  "$HOME/.workbuddy/skills/pdf-to-vault-summary/scripts/inject_video_links.py" \
  "<MD_PATH>" "<MD_PATH>.vmap.txt"
```
⚠️ **Never parallel-edit the same md with multiple Edit calls** — they overwrite each other and drop changes. Always use this single scripted pass. If you must clear old links first, use the loose regex `mp4#t=[^|]*` (do NOT `re.escape` the `[[` prefix — that double-escapes and the regex silently matches nothing, so links pile up). The injector's skip-logic makes clearing unnecessary in normal use.
4. After injecting, run the **video-link semantic audit** (`Step 8` below) and resolve every mandatory ⚠ before present. Also confirm coverage: **every numbered item has a video link (0 missing)** —— 但"缺链"的**合法情形不止标题行与图行**, 还有 `### 6.` Rules 的两支 **pdf-only**: ① 该考点在 SRT 里确实零命中; ② 该考点在文件内二次出现且属同一段逐字复读。这四类缺失都是**设计内**, 不计入 0 missing 的核查口径。**实证 (2026-09-09 `作文不跑题技巧课.md`)**: 视频只讲到 PDF P51 就收尾, P52 起大量条目走①的 pdf-only, 属合规, 不要当成"大面积缺链"去补挂秒数。

**Step 5 — Audio/Video timestamp link format:**
```
[[<basename>.m4a#t=<seconds>|音频]]
[[<basename>.mp4#t=<seconds>|视频]]
```
- `<basename>` is the audio/video filename without path (e.g. `第五章学生发展心理1.m4a`).
- `<seconds>` is the timestamp in seconds (integer) from Step 3.
- **The alias must match the file type (observed error 2026-07-27):** `.m4a`/`.mp3` audio →
  the literal word **音频**; `.mp4`/`.webm` video → the literal word **视频** — NEVER put
  `|音频|` on an `.mp4` file (the verifier now fails such links). The alias is never the timestamp.
- Audio/video links go INLINE at the end of the item text, space-separated with PDF links:
```
1. **激情**:... **范进中举**是激情的经典例子. [[第五章学生发展心理1.pdf#page=34|pdf]] [[第五章学生发展心理1.mp4#t=4290|视频]]
```
- If an item only has an audio source (no PDF page), the audio link goes alone inline at the
  end of the text.

**Rules:**
- The PDF is always the skeleton — never restructure sections based on subtitle content.
- **Dual coverage is mandatory**: every numbered knowledge point ends with BOTH a `[[...pdf#page=N|pdf]]` and a `[[...mp4#t=秒|视频]]`. **pdf-only 只有两支(2026-09-08 裁决)**: ① 该考点在 SRT 里确实零命中(纯 PDF 独有内容); ② 该考点在文件内二次出现且属同一段逐字复读 → 第二次出现 pdf-only(见下方 TWICE 规则)。除这两支外一律逐条挂秒, 但任何条目都不得 video-only-without-source。
- **★ 带背稿 / 讲义类同样逐条双链接 (2026-09-07 用户拍板, 单一口径)**: **每个条目都要挂自己落点的 `mp4#t=`**(同一考点多个条目须各取该考点讲授区间内**互不相同**的秒数——**禁止**多条共用同一秒数, 共用会同时触发 `verify_video_links.py` 的 DUP 硬门槛与连续相同链接集合合并 FAIL; 实在只有一段讲授区间的, 就取该区间内相邻的不同秒数)。某条确实找不到对应 PDF 答案页时(如整题只有填空页), 按 no-fabricated-source 规则挂**该考点所在的 PDF 页**, 不得编造页码, 也不得只挂视频。
- Only add subtitle content that is genuinely supplementary (not already in the PDF).
- Keep the same compact format (no blank lines, English punctuation, bold terms).
- Multiple video links from different timestamps can share one inline position (space-separated) at the end of the item text.

### 7. ⚠️ Final holistic verification — MANDATORY last step (run BEFORE present_files)

> **⚠️ 跨文件引用写法（2026-09-13 修订）**：本 skill 全文用阿拉伯数字编号（Workflow 为 `### 1.`–`### 7.`；末步 **`Step 8` 是节内加粗行、不是 `###` 标题**，引用时就写 `Step 8`；另有顶层末节 `## 9.`），
> **没有任何 `§N` 标题**；别处引用时写原始编号即可（如 `pdf-to-vault-summary` 的 `### 7.`、`Step 8`、`## 9.`），
> **不要写 `§7` / `§8` / `§9`**（写了会扑空）。

After writing the `.md` (whether PDF-only path or PDF+SRT fusion path), you MUST run the
shared verifier and confirm **ALL PASS** before calling `present_files`. Any FAIL must be
fixed and re-verified first. This overrides the earlier ad-hoc grep checks — always do this
holistic pass; the user explicitly requires a final strict compliance check.

**Step 0 — auto-normalize (run FIRST).** Run the companion normalizer to deterministically
fix the two recurring failure modes (un-merged consecutive links, bold inner-edge punctuation)
and normalize punctuation; it is idempotent. Then run the verifier.

```bash
~/.workbuddy/binaries/python/envs/default/Scripts/python.exe \
  "$HOME/.workbuddy/skills/vault-content-summary/scripts/normalize_vault_summary.py" \
  "<OUTPUT_MD_PATH>"
```

Then run the shared verifier:

```bash
~/.workbuddy/binaries/python/envs/default/Scripts/python.exe \
  "$HOME/.workbuddy/skills/vault-content-summary/scripts/verify_vault_summary.py" \
  "<OUTPUT_MD_PATH>" --strict-links pdf
```
**⚠️ 纯 SRT / 纯视频（无同名 PDF）场景不要加 `--strict-links pdf` (2026-09-09 定)**: 该参数强行要求每个条目有 `pdf#page=` 链接,
纯字幕转写文件里一条都没有 → 必定 FAIL(`no pdf#page link found`), 不是文件的问题。这类文件按 `### 6.` 挂 `[[x.mp4#t=秒|视频]]` 单链接即可,
校验只跑 `verify_vault_summary.py "<MD>"`(不带该参数) + `verify_discipline.py --all` + `verify_video_links.py`。
**ALSO run the vault-write-discipline verifier (mandatory since 2026-09-04 — the 分行/加粗 rules live there):**
```bash
~/.workbuddy/binaries/python/envs/default/Scripts/python.exe \
  "$HOME/.workbuddy/skills/vault-write-discipline/scripts/verify_discipline.py" \
  --all "<OUTPUT_MD_PATH>"
```
- Both verifiers must pass before `present_files`. `verify_discipline.py` 的 FAIL 与 WARN(占比 >40%、整条全粗 ≥15 字等)都要修到 OK. **例外 (2026-09-28)**: 脚本的「单条加粗块 >3」「单节均块 >2.5」阈值滞后于新版的 5 / 3.5, 符合新密度三条前提 (已按规则 14 拆行 / 整条占比 ≤40% / 加粗内容在白名单内) 时这两条 WARN 属**已知豁免**, 不必删掉合法的第 4~5 处加粗 (见 `../vault-write-discipline/references/bold-keyterm-rules.md` 第 4 节); 且按 **`vault-write-discipline` checklist #5 情形 B**, 为拆长句而产生的连续无标记 4 空格续行所报的 `顶层裸4空格` 同属已知豁免（2026-10-21 判据改为回溯后，此形态已不再报警）, 不得并回原行.
- Exit code `0` = ALL PASS (safe to present). Exit `1` = at least one FAIL — fix and re-run.
- The verifier checks every HARD rule in one pass: zero blank lines; single 𒋙-prefixed H1;
  no intro paragraph after H1; 𒋙-prefixed unnumbered headings; half-width punctuation
  (excluding `[[ ]]` target text); no bold-inner-edge punctuation; single-space `N. ` markers;
  explicit incrementing numbering (no lazy `1.`); ≤9 items per flat section; no backticks;
  presence of inline source links (`--strict-links pdf` enforces `pdf#page=` links for
  this skill); and **consecutive identical link sets merged** (a non-empty link set repeated
  on ≥2 consecutive list items is a FAIL — merge to the last, per rule #11 / Mode B above).
- Do NOT present a file that fails any check.

**Step 8 — ⚠️ Video-link semantic audit (MANDATORY when SRT fusion produced `mp4#t=` links):** The format verifier above only checks that links *exist* and have the right alias — it does NOT check whether `mp4#t=N` actually points at the spoken explanation of *that* item. A link can be perfectly formatted yet jump to the wrong segment (e.g. an early example, or a between-segment idle chat). This is exactly the failure mode observed 2026-09-02 on `主观专项-教学技能2.md` (half the latter links pointed at wrong segments; only caught when the user clicked them). Run the bundled auditor BEFORE present_files:

```bash
~/.workbuddy/binaries/python/envs/default/Scripts/python.exe \
  "$HOME/.workbuddy/skills/pdf-to-vault-summary/scripts/verify_video_links.py" \
  "<OUTPUT_MD_PATH>" "<SAME_NAME_SRT_PATH>"
```

It reads every `mp4#t=N` in the md, looks up the subtitle window around second N, and prints a per-link audit table. Three signals:
- **⚠ IDLE** (hard): the window contains between-segment chatter markers (卷子/歌曲/休息/下课/插播/广告…). Almost always a wrong segment — **must fix**.
  **⚠️ 但 IDLE 词表会误伤"正当内容里正好出现这些词"(2026-09-09 两例 + 2026-09-10 收窄)**: `作文万能模版课` t=684 讲"阅卷只看20秒"窗口内出现"试卷"、t=3848 讲顾明远窗口内出现"私信", 都被判 IDLE, 内容本身完全正当。
  **已按此把裸词收窄 (2026-09-10)**: 删掉裸词 `试卷` / `私信` / `卷子`（它们在"讲试卷""回私信""把这张卷子讲一下"里全是正当表达），保留语境明确的形式 `这套卷子` / `这套卷啊` / `私信我发` / `私信发我` 等。**新增词条前先自问"这个字符串会不会出现在正当讲授内容里"**——会，就必须加限定字。（37→35 条，已跑回归测试：5 个正当语境零命中、3 个闲聊/广告语境正常命中。）
  **处理原则: 改秒比改内容快** —— 在该考点的讲授区间内挪到不含该词的相邻秒(两例分别改 705 / 3875)即可, 不要为了躲词表去改写条目文字。判 IDLE 前先人眼扫一遍窗口, 确认是"闲聊"还是"在讲这个词"。
- **⚠ DUP** (hard): the same timestamp N is used by ≥2 links. **must fix** — two possible causes, resolve differently: (a) mapping error → move one link to a different second inside **its own** teaching window; (b) the two items really are one re-broadcast segment (recording looped / rewound — see the "appearing TWICE" rule below) → the later item keeps pdf only.
- **· ORDER?** (soft): a backward timestamp jump within a `## 𒋙` section. Often a legitimate "taught earlier" reference — eyeball the window; ignore if it clearly matches.
- **· KEYMISS** (soft): none of the item's keywords appear in the window. Usually a too-narrow match or a generic line — eyeball the window; ignore if it clearly matches.

Exit code `0` requires **zero IDLE and zero DUP** (soft hints don't block). If any hard ⚠ appears, locate the correct teaching segment in the parsed SRT (search for the item's distinctive keyword, take the **LATER** occurrence — never the first hit), update `<md>.vmap.txt`, and re-inject. Do NOT present until the audit is clean.

## Reference example (shape of the output)
```
# 𒋙第四章 学习心理 主观题总结
## 𒋙操作技能与心智技能的培养措施
1. 操作技能的培养措施.口诀:**失恋反动**.
    1. **准确的示范与讲解**
    2. **必要而适当的练习**
    3. **充分而有效的反馈**
    4. **建立稳定清晰的动觉**. [[第四章学习心理主观题4.pdf#page=3|pdf]]
2. 心智技能的培养措施.口诀:**主机原型的言语差异**.
    1. **激发学习的主动性与积极性**
    2. 注意**原型的独立性,完备性与概括性**
    3. 根据培养的阶段特征,**正确使用言语**
    4. 注意**学生的个体差异**. [[第四章学习心理主观题4.pdf#page=5|pdf]]
## 𒋙认知发展阶段(Mode B — 同页短条目合并链接)
1. **感知运动阶段**(0~2岁):感觉与动作分化;9~12个月获得**客体永恒性**
2. **前运算阶段**(2~7岁):万物有灵;自我中心;思维不可逆;未获守恒
3. **具体运算阶段**(7~11岁):去自我中心;思维可逆;形成守恒;具体逻辑推理
4. **形式运算阶段**(11岁后):抽象逻辑思维;假设-演绎推理;思维可逆、补偿、灵活 [[第四章学习心理主观题4.pdf#page=17|pdf]] [[第四章学习心理主观题4.pdf#page=19|pdf]]
```

## Reference example — PDF + SRT subtitle fusion (Step 6 output, dual coverage)
When a same-name `.mp4`+`.srt` pair is available alongside the PDF, every numbered item gets
BOTH a pdf page link and a video timestamp link (dual coverage), with spoken supplements fused in:
```
# 𒋙第五章 学生发展心理
## 𒋙情绪的种类（考点四）
1. **心境**:一种微弱、平静和持久的情绪状态,具有**弥散性**(感染性)和**长期性**(持久性). [[第五章学生发展心理1.pdf#page=33|pdf]] [[第五章学生发展心理1.mp4#t=3980|视频]]
2. **激情**:一种爆发强烈而持续时间短暂的情绪状态,通常由重大事件引起.例:恐惧时毛骨悚然;愤怒时全身发抖;狂喜时手舞足蹈.**范进中举**是激情的经典例子——查到成绩过后狂喜跳跃、欢呼雀跃. [[第五章学生发展心理1.pdf#page=34|pdf]] [[第五章学生发展心理1.mp4#t=4290|视频]]
3. 视频补充——转移vs宣泄:**打沙包**要看前提条件——对特定对象发泄情绪=**转移**,单纯释放情绪=**宣泄**. [[第五章学生发展心理1.mp4#t=6976|视频]] [[第五章学生发展心理1.mp4#t=7691|视频]]
```

## 9. 刷题类 PDF（题干页 + 答案页交替）→ 平铺双链接 md（2026-09-10 首做）

适用：PDF 是「题目页 N 道 → 答案页 N 道」交替排版的题库（科一/科二「最后一遍疯狂刷题」系列），
同名 `.mp4`+`.srt` 是讲师逐题讲解。这类文件按广哥 2026-09-10 定的口径 —— **不分 `##`、整篇平铺、
编号 1-N 连续、按 `pdf#page=` 升序**（见 `vault-write-discipline` checklist #8 豁免）。

`scripts/quiz/` 下四个脚本串起来跑：

1. `parse2.py` —— 按行首题号把 PDF 切成题目块 / 答案块，输出 `blocks.json`。
   判定：块首 30 字内出现 `【答案】`/`答案：` 即答案块；否则归题目块。
2. `parse3.py` —— 合成 1..MAXNO 的 items（题干/选项/答案/解析/页码）。
3. `align.py` —— 每题对齐到 SRT 秒数。
4. `gen.py` —— 出 md（题干 + `选x (**正确选项**)` + 逐条 `pdf#page=` 与 `mp4#t=`）。

**⚠️ 路径与 `BASE` 是写死的**（`gen.py` 顶部的 `BASE` 常量 + 文件末尾的绝对输出路径）：换系列或文件被改名时**先改这两处再跑**。
本系列用户会自己改名 / 删文件（2026-09-10 科一旧版即如此），脚本不会自动跟随。

### 三个必踩的坑

- **答案配对**：带题号的答案块直接归位；**无题号的松散答案块按"题干页 +1 / +2"配**。
  早先按"块序递进"配会在后半段整体错位一格（实测第 313-316 题答案全错），改用页距约束后全对。
  交付前务必**随机抽 10+ 条**把 md 显示的选项文本与 PDF 答案块原文对一遍。
- **PDF 印刷坑**：错号（`290` 印成 `390`）、只有答案页没有题干页的题（153/197/271）、题号凭空消失（69）。
  处理：错号手工改回；无题干页的题**跳过不编号**（编号要连续，不要留空号）。
  **同名历史版本带跳号时**（"能补的已补、确实无题的才留空"那种）的豁免口径与"不得为过检而重编号"约束，
  见 `vault-write-discipline` checklist #8（唯一权威源，本 skill 不复写）。
- **SRT 对齐**：关键词取题干 2-5 字 n-gram（滤停用字、只保留 SRT 全文频次 1-300 的，太常见/太生僻都不要），
  ±12s 窗口打分 `Σlen(kw)²`，**单调贪心 + 惩罚 `-1.2×|t-(prev+平均间隔)|`** ——
  不加惩罚项时末尾会挤成一团（第 320-323 题全落在 7282-7285），加了才均匀铺开。
  命中率 96%+ 即可，剩下的按平均间隔兜底。

### 文本清洗

- 题干里的填空括号 `（ ）` 一律转 `……`（不是删除，删了会出现"不得将等智能终端产品"这种断句）。
- 选项常被 pdfplumber 挤成一行（`A.有利于教育质量提升B.不利于学生全面发展C....`），
  必须按 `[BCD][.．]` 二次切分，否则会把 B、C 的文本一起塞进 A。
- 加粗：正确选项文本整体加粗；**超过 22 字时只加粗第一个逗号前的部分**（如 `选c (**不合法**, 教师…应使用普通话)`），
  否则会触发 `verify_discipline` 的「单条加粗占比 ≤40%」WARN。
- 题干中的【做题技巧】块并入该页之后的第一条题目（消费式，不重复挂）。

## Notes / pitfalls
- Always use the MANAGED python (`...\binaries\python\envs\default/Scripts/python.exe`), never a
  global `pip install`.
- `pdfplumber` text extraction can mangle layouts with heavy tables/columns; if a section looks
  wrong, re-extract that page range and verify before writing.
- Image-only PDFs need OCR (see step 1). Tell the user rather than silently producing empty text.
- **SRT multi-hour timestamps (IMPORTANT, observed 2026-08-27):** the OLD `parse_srt2.py` wrote `[mm:ss]` and DROPS the hour, breaking videos >1h. The current `parse_srt.py` outputs ABSOLUTE seconds (`3600*h+60*m+s`) directly, so this is fixed — always use `parse_srt.py` and the `[[mp4#t=秒|视频]]` form. Do NOT re-derive from `mm:ss`; if you ever hand-parse, the `#t=<seconds>` link MUST be total seconds `3600*hour + 60*min + sec`, never `min*60+sec` alone.
- **Where to put SRT supplements — two valid patterns:** `### 𒋙视频补充` 子标题是合法写法(早期一度被禁, 现已确认可用); 真正的失败模式只有 *空行* 与 *lazy 编号*, 两者都可避免. Pick per section:
  - **(a) Inline inside the parent list** (Step 6 example: `3. 视频补充:... [[x.mp4#t=秒|视频]]`) — best when the parent list has room (total items stay ≤9).
  - **(b) A dedicated `### 𒋙视频补充` sub-heading at the end of the parent `##`** — best when the parent `##` already has many PDF items and the video has a lot to add (long 2h+ lessons); it keeps the core list ≤9 without dropping content. This is **legal and verified ALL PASS** (2026-08-31, 26下 心理学材料分析重点带练.md) as long as you keep ZERO blank lines around the heading and restart numbering at `1.` inside it.
  - Either way the item text starts with `视频补充:` and ends with the inline `[[...mp4#t=秒|视频]]` link.
- **Run BOTH verifiers:** Always run `normalize_vault_summary.py`, then `verify_vault_summary.py --strict-links pdf` (catches link-alias / numbering / SRT-fusion rules), then `verify_discipline.py --all` from vault-write-discipline (catches 缩进分层 / 加粗密度 / flanking 等通用纪律). A summary file must pass BOTH before present_files. Caveat: `verify_discipline.py`'s indent checks only validate indents that EXIST — they cannot detect "该缩进却没用" or "该拆的 ①② 没拆", and bold-over-density is only a WARN; the 分行/加粗 judgement itself still depends on loading vault-write-discipline before writing (see Step 3).
- **Content-boundary refusals (pitfall, observed 2026-07-25):** Some 教资/考研 课件 — especially
  **综合素质 / 考研政治 / 教育法律法规 / 教师职业道德** chapters — contain text in a restricted
  category. When such pages are fed in for summarization, the model may refuse with
  "这个话题目前不在我的能力覆盖范围内，我没有办法就此展开讨论" and repeat PER PAGE (because the
  extractor splits by `===== PAGE N =====`), which looks like a refusal loop. If this happens:
  (1) locate the exact triggering pages via the `===== PAGE N =====` extractor blocks; (2) ask the
  user whether to SKIP those pages or confirm they are fine to include; do NOT silently drop or
  invent content. The refusal originates from the model, NOT from this skill's logic.
- The user's chat-reply strict format (first-line summary, no `#`, ordered-list-only) applies ONLY
  to chat replies, NOT to this generated file. Use normal `#`/`##` markdown here.
- SRT multi-hour pitfall: `parse_srt.py` outputs absolute seconds, so just use it. If you ever hand-parse, grep for `\[00:00\]` to find hour boundaries and add 3600s per hour; do NOT assume all `\[03:15\]` are 3 minutes — they could be 1h3m15s.
- **em dash `—` counts as full-width punctuation (observed 2026-08-31):** the verifier's `FW_PUNCT`
  string contains `——`, and inside a regex character class that collapses to the single U+2014
  character — so **every** `—` in your prose FAILS the 半角英文标点 check. Rewrite all of them as a
  half-width hyphen before writing: `耶克斯-多德森定律`, `P68-P75`, `4-5条`, `识记-保持-回忆`. Safe
  (not in the banned set): 《》书名号, `…` ellipsis, `·` middle dot, `×`, `±`, `~`.
- **Heading-numbering check looks at the START of the heading only (observed 2026-08-31):** the
  verifier rejects a heading when its text begins with `\d`, `[一二三四五六七八九十]+[、.]`, or
  `（\d`. Consequences: (1) `### 𒋙2026年上至2022年下` FAILS (starts with a digit) — write
  `### 𒋙真题第一问(2026年上至2022年下)` instead; (2) PDF sections literally named 考点一/二/三 or
  三、四、五 must have the numbering stripped in headings — use `## 𒋙认知发展过程`, not
  `## 𒋙考点一 认知发展过程`; (3) numbers in the MIDDLE are fine (`## 𒋙心理学考点九大方向` passes).
- **⚠️ Same knowledge point appearing TWICE in one file — 先判"老师说了两遍"还是"同一段被复读"(observed 2026-09-03 `主观专项-教学技能4.md`; 判定标准 2026-09-08 用户拍板):** 汇总 / 清单 / 附录这类二次出现的条目, **默认按"老师分开讲了两遍"处理**——正文讲一遍, 后面的带背/复述/总结又讲一遍, 两处**都要逐条挂各自的 `mp4#t=`**。撞秒就在该考点讲授区间内**取与正文不同的相邻秒**(正文占 5536-5544 则附录取 5546; 正文占 5520-5532 则附录取 5519), 校验标准不变: DUP=0, IDLE=0。只有当两处命中**完全相同**时(同一段**逐字重复**, 多因录制时循环播放或回倒了一段), 才走"第二次出现只留 `[[x.pdf#page=N|pdf]]`、不挂视频"这一支。
  **判据**: 在解析后的 SRT 里搜该考点的**特征词**——命中落在时间上分开的两段、表述不同 = 老师说了两遍 → 各挂各的秒; 命中落在同一窗口或逐字重复 = 复读 → 第二次出现 pdf only。
  **⚠️ 禁止把视频链接挂到 `##`/`###` 标题上**(2026-09-08 用户质疑"为什么把视频写到标题上?"): 标题是范围名不是知识点, 点进去不知跳哪。**任何情况下都不许用"挂到标题"来回避逐条挂秒**(含上面 pdf-only 那一支: 第二次出现就是条目里只留 pdf, 标题保持干净)。已验证可行(`科目二冲刺带背7.md` 附录30题, 链接 135→164, DUP 仍 0)。
- **⚠️ Video timestamp links can be FORMAT-valid but SEMANTICALLY WRONG (observed 2026-09-02, `主观专项-教学技能2.md`):** `verify_vault_summary.py` only checks links *exist* with the right alias — it does NOT check that `mp4#t=N` lands on the spoken explanation of *that* item. When you build the vmap by searching the SRT for a keyword, the **first hit is usually wrong** (early example / wrong-statement / between-segment idle chat). Half of 教学技能2's latter links pointed at the wrong segment and passed every format check. **Prevention (mandatory):** after injecting, ALWAYS run `verify_video_links.py` (Step 8) and resolve every ⚠ IDLE / ⚠ DUP before present. When locating a timestamp, take the **LATER** occurrence of a *distinctive* keyword, print the subtitle window, and confirm the keyword actually appears there. (That "later, not first" rule is about the **first hit being a wrong segment**; it does NOT mean a term may only be linked once. If the teacher genuinely taught the point twice in two separate passages, both are valid landing spots — see the "appearing TWICE" rule below.) Red flags: a window mentioning 卷子/歌曲/休息 (idle), the same N used twice (DUP), or non-monotonic ordering within a section.
- **⚠️ KEYMISS clusters = systematic drift, not narrow matches (same file, 2026-09-03):** fixing that file surfaced that ALL 9 数学思想 video links had slid one slot (或然与必然's `t=1545` landed on 方程思想, 极限's `t=1774` on 或然与必然, 类比's `t=1952` on 特殊到一般). One KEYMISS is usually a too-narrow match and can be ignored; **≥3 consecutive KEYMISS in one section means the mapping slid**. Then: open the parsed SRT, locate each term's NAMING moment (`首先转化与化归思想`, `分类讨论在哪里`, `那什么是模型呢`, `这不就是一种极限思想吗`), re-map the whole run, and pick seconds NOT already used elsewhere in the file (the 实例 section often holds nearby seconds) so no DUP appears.
