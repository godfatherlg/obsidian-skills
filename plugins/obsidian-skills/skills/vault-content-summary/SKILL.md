---
name: vault-content-summary
description: 'DEFAULT skill for any task where you SEARCH the user''s local Obsidian vault (or any local markdown workspace) and then GENERATE a written text deliverable (report / summary / compilation / 汇总文) from what you found. The user does NOT need to say "查找/汇总/罗杰斯" — the trigger is the behavior itself: you performed a local file search and are about to write it up. Produce a categorized report that writes out the FULL relevant source text (not compressed one-liners), bolds key terms (bold is the ONLY emphasis device; never use ==highlight== — EXCEPT when the user explicitly asks to MOVE his own hand-made highlights, see Pre-Write Checklist #10 exception), groups by category with 𒋙-prefixed headings (NO Arabic numerals; use ### sublevels ONLY when there is genuine containment between sections, NOT merely because there are many), and places each Obsidian wikilink INLINE right after the item text (or, when CONSECUTIVE items cite the SAME heading/article, a single merged link after the last of them) using the link-alias form: media links use a fixed alias by type — **图片** for images (`[[images/xxx.png|图片]]`), **视频** for videos (`[[name.mp4#t=<seconds>|视频]]`), **音频** for audio (`[[name.m4a#t=<seconds>|音频]]`), **pdf** for PDF pages (`[[name.pdf#page=N|pdf]]`); plain note links use `[[note#heading|标题]]` (heading) or `[[note|文章]]` (whole note) alias form — and for `.md` notes with NO heading, or when an exact row is needed, use the Advanced URI line link `[N](obsidian://adv-uri?vault=<vault-id>&filepath=<%2F-encoded rel path>&line=<N>&column=1&openmode=true&view-mode=source)` instead (see Link rules). Links are written directly after the text on the same line (NOT on a separate soft-break line, NOT a new paragraph), and multiple links MAY be space-separated on the same inline position (`[[a|视频]] [[b|音频]]`). When the source references an image/chart, surface it with the image alias link `[[images/xxx.png|图片]]` so the referenced picture is linked out. Now ALSO the DEFAULT format for ANY content written into files in this vault (stories, notes, articles, page material) — not limited to search-then-summarize tasks. Do NOT use this for ordinary chat-only Q&A with no file output.'
agent_created: true
summary: '搜 vault（或任意本地 markdown 工作区）后要生成文字交付物（报告 / 汇总 / 整理稿）时的默认 skill —— 新建整篇成文必加载，且必须与 vault-write-discipline 同时加载，缺一会翻车。'

---

## ⚠️ Pre-Write Checklist (MANDATORY before every file Write)

**RE-READ this checklist every time before writing a markdown file. Do NOT generate from memory — memory drops constraints. Run each point against your draft; any miss is a violation the user will catch.**

1. **No backticks** around ANY path or link in the deliverable.
2. **Title → category, no intro.** File starts with one H1 `# 𒋙title`, then DIRECTLY the first `## 𒋙category` — no intro paragraph, no blank line after the H1. **Exception (user override, 2026-09-09): 广哥点名去掉 `𒋙` 的**标题**从其令——`𒋙` 是通用体例的默认值而非硬约束；判断依据是"本次用户有没有点名"，不是文件类型。⚠️ **同一文件 / 同一系列里带 `𒋙` 与不带 `𒋙` 常长期并存（逐次点名决定，不按文件整批统一），引用时一律现读目标标题原文、不许按"哪个文件"推断**。**（`𒋙` 是默认值而非硬约束; 属**例外型**冲突——永久例外, 不进收敛队列, 见 `rules-consistency-audit`「冲突收敛准则」第 1 条。）**
3. **Inline alias links.** Every SOURCED item ends its text line with its wikilink written directly after the text (same line, no soft-break/newline before the link) using the link-alias form: images `[[images/xxx.png|图片]]`, videos `[[name.mp4#t=<seconds>|视频]]`, audio `[[name.m4a#t=<seconds>|音频]]`, PDF pages `[[name.pdf#page=N|pdf]]`; plain note links use `[[note#heading|标题]]` (heading) or `[[note|文章]]` (whole note). Multiple links from one item are space-separated on the same inline position (`[[a|视频]] [[b|音频]]`). NOT on a separate line, NOT a block of links at the file end.
4. **Link to the SPECIFIC heading** (`[[note#heading text|标题]]`), never a whole-note link when a heading exists. The alias is the literal word **标题** (NOT the heading text) — only the TARGET keeps the verbatim heading text so the link resolves; the displayed alias is always `标题`. For a whole-note citation use `[[note|文章]]` (alias **文章**). Canonical alias rules (shared with pdf-to-vault-summary): `../shared/citation-link-aliases.md`.
5. **No fabricated source.** Synthesis-only sections (your own explanation, no real source note/media) get NO link line at all. Never write the output file's own storage path as a fake source.
6. **English (half-width) punctuation** everywhere in prose: `, . ; : " " ( ) ! ?` instead of full-width Chinese `，。、；："（）！？`. This INCLUDES 顿号 `、` → half-width comma `,`. Only `…` (ellipsis) and `·` (middle dot) are exempt (typographic, not in this set). Inside `[[ ]]` / `![[ ]]` keep the exact target text (it is not free prose).
   （同口径亦见 `pdf-to-vault-summary` 规则 6，**真源在 `vault-write-discipline` Pre-Write Checklist #4**。两处各存一份供就近阅读，改一处必须同步另一处。）
7. **Bold inner-edge rule (parentheses included).** A `**...**` span silently fails if punctuation touches `**` from the INSIDE. This includes HALF-WIDTH and FULL-WIDTH PARENTHESES: `**麦积山(2014)**` and `**麦积山（2014）**` BOTH break, because `)` / `）` sits at the inner edge of the closing `**`. If the first or last INNER character is punctuation, the PREFERRED visible fix is to move that punctuation OUTSIDE the bold — write `**麦积山**(2014)` (not `**麦积山(2014)**`), and `**莫高窟**(1987), **龙门**(2000), **云冈**(2001)` (not `**莫高窟(1987), 龙门(2000), 云冈(2001)**`). Fallbacks when you must keep punctuation inside one bold span: insert a zero-width space `\u200B` at that inner edge, or use `<b>...</b>`. Punctuation on the OUTER edge (before the opening `**` or after the closing `**`) is harmless.
8. **Compact, numbered & indented-by-containment.** List markers `N. ` use EXACTLY one space. Zero blank lines between items and between sections. Category headings `## 𒋙...` carry NO numbering (no Arabic, no 一、二、). **Containment (隶属) → 4-space indent; siblings (并列) → each on its OWN line at the SAME indent, inheriting the parent's level** — do NOT squash siblings into one line joined by `,`/`;`. Indent must be a multiple of 4 and is CAPPED at 2 levels (only 0/4/8 spaces — 12+ is a violation); it must NOT skip levels (no 0→8 jump). A 4-space continuation expressing containment MUST carry a list marker (`    N. ` / `    - `) or be a `![[` embed; an UNMARKED 4-space plain-text continuation is legal ONLY directly after a list item (renders as an indent line, 2026-09-07) — a top-level unmarked 4-space line (previous line is not a list item) renders as a code block and kills `**`; at top level use 3 spaces or a list marker. Canonical rule + before/after examples: `vault-write-discipline` Pre-Write Checklist #14 (single source of truth; if this line and that file disagree, that file wins).
9. **Consolidate consecutive same-source links (合并链接).** When ≥2 CONSECUTIVE list items cite the EXACT same link set (e.g. four items all from `[[x.pdf#page=5|pdf]]`, or the same `[[note#heading|标题]]`), write that link set ONCE, INLINE after the LAST of those items — never repeat it on every item. Items citing different pages/headings keep their own links. The verifier now HARD-FAILS files that repeat an identical link set on consecutive items, so this is not optional. **Exception (2026-09-08): 文件里含 `mp4#t=` 视频链接时走 `pdf-to-vault-summary` 的 `### 4.` 的「逐条双链接」判据 —— 每个条目各挂自己落点的秒数(互不相同), 本条合并不适用; 秒数互异本身就避免了"连续相同链接集合"的 FAIL.** Before/after:
   - BAD: `1. 胆汁质... [[a.pdf#page=5|pdf]]` / `2. 多血质... [[a.pdf#page=5|pdf]]` / `3. 黏液质... [[a.pdf#page=5|pdf]]`
   - GOOD: `1. 胆汁质...` / `2. 多血质...` / `3. 黏液质... [[a.pdf#page=5|pdf]]` (link only on the last).
10. **Bold key terms and keep bold edges clean.** Bold keywords and 口诀. Never let punctuation touch `**` from the INSIDE — prefer moving it OUTSIDE the bold (`**麦积山**(2014)`, `"**term**"`); the verifier flags inner-edge punctuation as a FAIL.
    **示例里的引号只为演示 flanking 位置**: 中文全角引号 `“”` 本身属第 6 条的禁用全角标点（verifier 的 FW_PUNCT 含它，写了直接 FAIL），
    写作中一律改用**半角引号** `"` 或书名号《》，不要照抄示例里的全角引号（与 `vault-write-discipline` checklist #4 同一口径）。 The companion normalizer (step 6) auto-inserts a zero-width space at bold inner edges, but write it correctly the first time when you can.
    **Bold is the ONLY permitted emphasis device (user rule, 2026-08-30).** NEVER write `==highlight==` (Obsidian highlight) in generated content — the user authorized bold only; highlighting was never in the spec and was an unrequested addition on my part. Emphasis = `**...**`, nothing else. Legacy `==...==` already sitting in existing files must be LEFT AS-IS (do not retroactively strip); the ban applies to all NEW content written from now on. **Exception (user override, 2026-09-10, 永久例外·不进收敛队列):** 广哥点名「把某文件里**他自己标的** `==高亮==` 搬到另一文件的对应处」时从其令——那是对**用户人工标记**的搬运, 不是 AI 自行添加样式。判据是"本次用户有没有点名要搬高亮", 不是文件类型; 搬进目标文件的 `==` 同样视为用户人工标记, 不回改、不因本禁令删除。落法（目标行有对应文字→就地 `==包住==`; 无对应文字→把该知识点以 `==片段==` 追加到该条目行尾、链接之前; 目标文件里根本没这个考点的题→跳过并说明, 不硬塞）见 `../vault-write-discipline` Pre-Write Checklist #4（唯一权威源）。
    **What deserves bold — canonical decision rules (user rule, 2026-09-03): `../vault-write-discipline/references/bold-keyterm-rules.md`.** This line only covers bold MECHANICS (edge punctuation); that file covers bold JUDGEMENT. Load it whenever you are unsure whether something should be bolded. Gist: bold is a **skim anchor**, not importance-painting — reading only the bold words must recover ~80% of the note's skeleton. Three-question filter (delete it and the sentence still works → don't bold; is it a noun-term or process/prose → bold nouns only; is it scarce in this section → if bold already covers 1/3 of the section, cut half). **Bold whitelist (7)**: defined term NAME (not its definition), names in a parallel classification, conclusion core (theorem name / iff / uniqueness), **qualifying conditions** (非零 / 可逆 / n阶 / 闭区间 — the highest-value bolds, since dropping a condition is exactly how marks are lost), mnemonics/口诀, numeric facts (year / count), negation words (不 / 无 / 不能 / 除外). **Never bold (8)**: a whole sentence or whole line (FAIL), connectives (因此 / 所以 / 也就是说 / 总之), explanations / reasons / examples, derivations and calculation steps, sources and page numbers, a word already in the section heading, generic高频 words (教学 / 学生 / 方法 / 特点 / 意义…), and the appraisal word itself — bold what it POINTS AT (`注意, **n 必须为正整数**`, not `**注意**, n 必须为正整数`). **Density caps (updated 2026-09-29)**: ≤3 bold spans in an item of ≤60 visible chars, **≤5 as the BASE** in a longer item that has been split per rule 13 below, **scaled up by item length (user rule 2026-09-29: roughly +1 span per extra ~60 visible chars — the cap follows content length, it is no longer a fixed two-tier table)** (**counted for the WHOLE ITEM — the first line plus ALL its unmarked 4-space continuation lines merged — never per physical line**); ≤40% of a ≥30-char item's text (unchanged); ≤3.5 average bold spans per item in a ≥5-item section; a line fully wrapped in one `**...**` (≥15 chars) is a hard FAIL (unchanged). Full table: `../vault-write-discipline/references/bold-keyterm-rules.md` 4 节 (canonical).
11. **⚠️ NO underscore runs for fill-in blanks (observed error 2026-07-27).** Never write `______` / `___` in prose — Obsidian's CommonMark parses consecutive underscores as emphasis delimiters and the line renders broken. Fill-in placeholders ALWAYS use the ellipsis `……`: write `所谓……,就是……`, `可见……/这启示我们……`. The normalizer auto-converts `_{2,}` runs outside wikilinks to `……`; the verifier flags any that remain. Also: media link aliases MUST match the file type — `.mp4`/`.webm` video → **视频**, `.m4a`/`.mp3` audio → **音频** (a `[[x.mp4#t=..|音频]]` link is a FAIL).
   （同口径亦见 `pdf-to-vault-summary` 规则 13。两处各存一份供就近阅读，**真源在 `vault-write-discipline`**——改一处必须同步另一处，不要只改一边。）
12. **Images must land in the file too (user rule, 2026-09-04).** Whenever the content involves a figure, that figure MUST be written into the deliverable — a figure that exists only in the chat is a violation (a `show_widget` SVG does NOT auto-persist into any note). Three cases, all mandatory: a figure drawn in chat → re-render it to PNG with the `obsidian-diagram-to-png` skill into `<vault>\images\` and embed it; a figure already in the source material (`![[images/..]]`, `[[x.pdf#page=N&rect=..|图片]]`, a user-provided image) → carry it into the item as an inline `[[images/xxx.png|图片]]` / `![[images/xxx.png]]`; a figure generated during drafting → render and embed as well. Embed it as an indented child line of the item it serves (`    ![[images/xxx.png]]`) — **indent follows the target file's existing convention** (Tab or 4 spaces, consistent within that file; 4 spaces for brand-new files), canonical rule: `vault-write-discipline` Pre-Write Checklist #12 — with ONE sentence before it saying what the figure shows and the key points explained after — one figure per key conclusion, never back-to-back figures without text. Before presenting, count the figures involved vs the `![[` / `|图片]]` occurrences in the file; they must match. **Exception (2026-09-10): 写进 `<vault>\临时\临时记录.md` 时按 `../vault-write-discipline` Pre-Write Checklist #17 的例外条款 —— 图只写一句图名 + 嵌入，图后不写逐框/逐条解读**（"零发挥"纪律在该场景优先于本条的"图后解释"）。Canonical rule (single source of truth): `../vault-write-discipline` Pre-Write Checklist #17.
13. **Long items MUST be split at semantic breaks (user rule, 2026-09-28).** An item whose **visible char count > 60** must never be written as one run-on line. Count = the item's first line + ALL its unmarked 4-space continuation lines merged, then strip `[[...]]` blocks, `$...$` inline math, the `**` delimiters themselves and all whitespace (identical to the verifier's `n_vis`); as a rule of thumb, anything longer than about one and a half screen lines is over 60. Shape: keep the first line as the `N. ` list item and write the remaining clauses as consecutive **UNMARKED 4-space continuation lines** — no `    N. ` / `    - ` markers (those would wrongly claim subordination), and consecutive continuation lines under one item are legal (they no longer violate the indentation rule; a verifier `顶层裸4空格` here is a known exemption (and since 2026-10-21 that check back-tracks the whole continuation block, so this shape no longer reports at all) — never merge the lines back or add markers just to silence it). Break at: subject change / time or stage change / "what it is" → "how to use it" (preconditions, steps, decision flow, 口诀 each get their own line) / adversative-causal connectives (但, 然而, 因此 — the connective STARTS the new line) / a new qualifying condition or boundary case (若…则, 当且仅当, 反例, 易错点). **Bold density is counted for the ENTIRE item, never per physical line** — an item split into three lines may NOT carry three times the bolds. **The verifier cannot check any of this** (its sampler only matches `^ *(\d+\.|[-*]) +` lines, so unmarked continuation lines are invisible to it): this is a manual self-check, count it yourself before presenting. Canonical rule with 5 break types and worked ❌/✅ pairs (single source of truth): `../vault-write-discipline` Pre-Write Checklist #19; density caps: `../vault-write-discipline/references/bold-keyterm-rules.md` 4 节.

# Vault Content Summary

Turn ANY "search local files, then write it up" task into a 罗杰斯汇总-style
report that the user can read in Obsidian and click through to the original. This is the
user's DEFAULT behavior — the moment your workflow is "look in local files, then generate
a text deliverable", apply this skill automatically. No keyword (查找/汇总/罗杰斯) required.

## When to use

- **边界优先 (第一判据) — 本 skill 决定 "怎么写", 不决定 "是否写".** Route here ONLY when the user has asked for a FILE / deliverable (汇总/汇总文/资料/报告/写到临时/新建一份/存起来). If the user is merely ASKING A QUESTION or asking you to LOOK SOMETHING UP (例如 "有多少理论" / "在工作区找找" / "本地有吗"), ANSWER IN CHAT — do NOT create a new file. Creating a file the user did not ask for violates the user-level rule that new-file creation requires an explicit 产出动词 from the user (2026-09-19, 事故: 用户只问 "学习动机有多少理论" + "在工作区找啊", 被误落盘成 汇总.md).
- DEFAULT for ALL generated file content. Any time you write new markdown INTO a file — a story, a note, an article, material appended to an existing page, or a summary — apply this format by default (compact, 𒋙-prefixed headings, bolded key terms, English punctuation, inline alias links). The user explicitly requires this for every generated deliverable, NOT just search-then-summarize tasks. Do NOT skip it merely because the content came from memory rather than a local search. **Exception (2026-09-07): 临时记录.md (`<vault>\临时\临时记录.md`) — its format is owned by `temp-note-workflow`, which OVERRIDES this skill there: NO H1 (starts directly at `## 𒋙` sections) and only `verify_discipline.py --all` runs on it (verify_vault_summary would FAIL on the missing H1 by design). Its items also carry NO source links (temp-note-workflow 硬规则 1: 零出处引用), so the checklist #3/#5 inline-source-link requirements do NOT apply there. When appending to / merging from 临时记录, load temp-note-workflow first.** **H1 标题该写什么（点名媒体源 / 从临时记录搬出 / 其他生成文件三条口径）见 `temp-note-workflow` 硬规则 13 的优先级总表。**
- The task involved searching the local vault (Grep/Glob/Read/code-explorer over local files) AND you are about to produce a written text deliverable (report/summary/compilation) from those findings. This still triggers the skill — apply even if the user never said "查找" or "汇总".
- User references or wants the "罗杰斯内容汇总" format (逐文件列举 + 加粗关键词 + 末尾原文链接).
- User wants a reference doc, not a chat-only answer.
- A plain "本地查下X" / "本地有讲X的资料吗" / "帮我看下仓库里X相关的内容" routes here for how to ANSWER, but a plain lookup is a QUESTION — answer IN CHAT by default; open the file-writing workflow ONLY when the user also asks you to write it out / 汇总 / 存起来.

## Workflow

### 1. Locate source files

Start from files already surfaced earlier in the conversation. Otherwise search the vault:
use Grep (content search) and Glob (filename patterns) rooted at the vault directory.
When the vault is large, prefer the code-explorer subagent for broad sweeps.

Collect the candidate files, then group them into the categories the user names (e.g.
作文模板笔记 / 科一写作理论笔记 / 作文审题范文). If the user did not name categories,
infer them from file types or ask once.

### 2. Read the actual source — never summarize from filenames

Open each candidate file with Read and extract:
- the exact heading text (for precise wikilinks),
- the verbatim content to quote (template sentences, formulas, example sentences).

Do NOT guess heading names. The wikilink target must match the real `## heading` in
the note, otherwise the link is dead in Obsidian.

**Record line numbers for line links.** When the source note has NO heading, or you want the link
to land on an exact row, capture the 1-indexed line number: prefer Grep `-n` on the key term (the
hit line IS the target line), or note the line numbers while reading the file. Line links
(`[<N>](obsidian://adv-uri?...&line=N...)`, see Link rules — display text is the target line number itself, e.g. `[249]`) need these numbers — do NOT skip the
Grep/read step or the link cannot point at the exact row.

If the user says to exclude a specific file (e.g. "不需要作文训练14竹.md"), drop it.

**Media / transcript sources (.srt, .mp4, .pdf, etc.):** Course-vault notes commonly embed
lecture quotes via links like `[[4.3xxx.mp4#t=1109|视频]]` (alias **视频**, timestamp in seconds). The quoted text usually lives
in a sibling `.srt` file, NOT in a `.md` note. When you pull a quote from an `.srt`/`.mp4`,
record the real filename and the `mm:ss` timestamp — do NOT assume a `.md` note of that name exists.

### 3. Write the summary in 罗杰斯 style

Produce a markdown file with this shape:

- **Title**: the topic as an H1 (`# 𒋙正项级数敛散性判别法汇总`), prefixed with 𒋙 like
  the section headings. Do NOT add a separate intro paragraph after the H1 — the user finds
  intro paragraphs redundant and has repeatedly required their omission. Go straight from the
  H1 into the first `## 𒋙` category heading. No coverage-scope paragraph, no "本汇总整理自…"
  lead-in sentence. (This is a hard constraint; see Hard constraints.)
- **Categories**: one `##` heading per category, **prefixed with the 𒋙 symbol and NO numbering** (e.g. `## 𒋙作文模板笔记`, `## 𒋙科一写作理论笔记`). Do NOT use Arabic numerals (`1.`) or Chinese (`一、`). Use `### 𒋙...` sublevels ONLY when a `##` category genuinely contains subsections (a containment relationship) — NOT merely because there are many sections. This is a
  *generated markdown file*, so `#`/`##` headings are normal and expected — the user's
  strict chat-reply format rule (which bans `#`) applies ONLY to my chat replies, NOT to
  file content. Use headings freely in the deliverable.
- **Items**: within each category, an ordered (numbered) list. Each item:
  1. Write out the FULL relevant source text — template sentences, the four-step formulas,
     example sentences, the ending-template paragraph, etc. Do NOT compress into a
     one-line summary. The user explicitly rejected over-shortened versions.
  2. Bold the key terms (e.g. **引述材料**, **凤头**, **首尾呼应式**).
  3. Keep my organized/paraphrased framing as the primary text; the source is quoted
     inside it.
  4. Put the Obsidian link INLINE directly after the item text (same line, no soft-break before the link), using the link-alias form (see Link rules).
  5. If the source content references an embedded IMAGE (lecture screenshot / chart, e.g. `![[images/xxx_MD5.png]]` or a `![[教材...pdf#page=...&rect=...]]` embed), surface that image in the deliverable too: write the image alias link `[[images/xxx.png|图片]]` (or `[[教材...pdf#page=...&rect=...|图片]]`) INLINE directly after the item text, so the referenced chart is linked out. Do NOT leave only the prose description plus a note link — the user explicitly requires referenced pictures to be linked out ("把图片链接给出来").

### 4. Link rules (the crux of this skill)

For each item, end its TEXT LINE with the source link written INLINE (directly after the text, same line — never on a separate soft-break line, never a new paragraph). Use the **link-alias form** with a fixed alias by media type:

- **Image** → alias **图片**: `[[images/xxx.png|图片]]` (or `[[file.pdf#page=..&rect=..|图片]]` for a PDF page-rect embed).
- **Video** → alias **视频**: `[[name.mp4#t=<seconds>|视频]]` (e.g. `[[4.3认知人本建构主义学习理论.mp4#t=1109|视频]]` — `<seconds>` is the timestamp in integer seconds). The alias is always the literal word **视频**, not the timestamp.
- **Audio** → alias **音频**: `[[name.m4a#t=<seconds>|音频]]` (e.g. `[[第五章学生发展心理1.m4a#t=4290|音频]]`).
- **PDF** → alias **pdf**: `[[name.pdf#page=N|pdf]]` (e.g. `[[第四章学习心理主观题4.pdf#page=3|pdf]]`).
- **Plain `.md` note (heading link)** → alias is the literal word **标题**: `[[note-name#heading text|标题]]` (e.g. `[[反观当下模版#𒋙二,开头万能格式(四步)|标题]]`). The TARGET keeps the heading text verbatim (so the link resolves); the alias is always `标题`, never the heading text. **TARGET 的 `𒋙` 跟随目标文件现状**: 默认体例标题带 `𒋙` → target 带; 用户点名去 `𒋙` 的文件(冲刺带背系列)标题无 `𒋙` → target 不能带, 否则死链。**链接侧不自行增删 `𒋙`**。 **Whole-note link** → alias is the literal word **文章**: `[[note-name|文章]]` (use when citing the whole note). When a specific heading exists, ALWAYS link the heading (`|标题`), never a whole-note link.
- **Line link (Advanced URI, for no-heading notes or exact rows)** → when the `.md` note has NO heading (`[[note#heading|标题]]` would be dead), or the item must land on an exact row inside a section, use a markdown external link whose display text is the target line number itself: `[N](obsidian://adv-uri?vault=<vault-id>&filepath=<相对路径,%2F编码>&line=<N>&column=1&openmode=true&view-mode=source)` (display = the line number, never "标题"/"文章"/描述文字). `line` is 1-indexed; capture it via Grep `-n` (hit line) or from Read line numbers. **MUST include `column=1`** (模板惯例, 与 FakeLink `copyLineUri` 的输出一致; 带上无害, 日后若改用原生 Advanced URI 也仍需要). NEVER combine with `offset` (it overrides `line`). **⚠️ 归因更正 (2026-09-09 核对 `fakelink/main.js` 源码)**: 本机**未装** Advanced URI, `adv-uri` 由 **FakeLink** 接管且其 handler **只解析 `filepath` 与 `line`**, `column` 属**纯透传参数**; 早期"Advanced URI 2.0.0 的 `setCursor` ch=NaN"是**误归因**, 本机无法复现, 按它去查插件源码会走错方向. 协议事实见 skill `obsidian-jump-line`. It is a SUPPLEMENT — keep heading wikilinks whenever a heading exists (line numbers drift on edit).

Rules:
- If the source is media/transcript, NOT a `.md` note: NEVER write `[[basename]]` — Obsidian wikilinks resolve only to `.md` notes, so that becomes a dead link. Mirror the media alias form above. If you quoted an `.srt` transcript, prefer the matching `.mp4#t=` / `.m4a#t=` link; otherwise `[[name.srt|视频]]` (or `音频`) is acceptable (Obsidian opens attachments). Do NOT invent a `.md` wikilink for a media source.
- If an item is a folder/directory with no single note: write the folder path as plain text, not a wikilink.
- If the item references an embedded IMAGE (lecture chart/screenshot) from the source note, the image alias link `[[images/xxx.png|图片]]` is written inline at the end of that item, in addition to any source-note link. The user wants the referenced picture linked out, not just described.
- **Merge consecutive same-source links.** When a run of CONSECUTIVE items all cite the SAME heading (`[[note#heading|标题]]`) or the SAME whole-note/article (`[[note|文章]]`), write the link ONCE — inline after the LAST item's text on the same line. Do NOT repeat it on every item, and do NOT move it to a separate line/block at the section or file end. This mirrors the pdf-to-vault-summary segment-link merge (one link per source segment). Items from DIFFERENT headings/articles still each get their own inline link. The merged link still points to the SPECIFIC shared heading (alias `标题`), never a whole-note link.

The link is ONLY a "go check the original if I don't understand" pointer. It is written INLINE right after the item text, space-separated from other links when an item draws on MULTIPLE sources (e.g. `[[高等数学7#对数函数的广义积分]] [[常错的公式]]` or `[[x.pdf#page=3|pdf]] [[x.m4a#t=4290|音频]]`). Keep it on the same line as the text — do NOT push it to a soft-break continuation line.

**Canonical alias rules (shared with `pdf-to-vault-summary`):** the authoritative, single-source list of all alias words (图片 / 视频 / 音频 / pdf / 标题 / 文章) lives at `../shared/citation-link-aliases.md` — both skills follow it; if this section and that file disagree, the shared file wins.

### 5. Output location

Write the file to the vault's 临时 folder (default `<vault>\临时\`) unless the user
specifies another path that turn. This is the user's established cross-project preference.

### 6. Verify then Present (⚠️ holistic check is MANDATORY)

Before `present_files`, run the shared verifier on the written file and confirm **ALL PASS**.
Any FAIL must be fixed and re-verified first. The user explicitly requires a final strict
compliance check after generating with this skill — do not skip it or fall back to ad-hoc greps.

**Step 0 — auto-normalize (run this FIRST, before the verifier).** The companion normalizer
deterministically fixes the two recurring failure modes (un-merged consecutive links, bold
inner-edge punctuation) and normalizes punctuation. It is idempotent and safe to run on every
generated file; run it, then run the verifier below.

```bash
~/.workbuddy/binaries/python/envs/default/Scripts/python.exe \
  "$HOME/.workbuddy/skills/vault-content-summary/scripts/normalize_vault_summary.py" \
  "<OUTPUT_MD_PATH>"
```

Then run the shared verifier:

```bash
~/.workbuddy/binaries/python/envs/default/Scripts/python.exe \
  "$HOME/.workbuddy/skills/vault-content-summary/scripts/verify_vault_summary.py" \
  "<OUTPUT_MD_PATH>"
```

**⚠️ `--strict-links pdf` 加不加的判据（真源在 `pdf-to-vault-summary`「### 7.」末段，本处只指路、不复制正文）**：源是 **PDF**（存在同名 `.pdf`）→ **加**；**纯 SRT / 纯视频 / 无同名 PDF** → **不加**（加了会报找不到 `pdf#page` 链接，那是参数误用、不是文件本身的问题）。

**ALSO run the vault-write-discipline verifier (mandatory — 本 skill 的 verifier 只查 𒋙/链接/编号/标点等汇总规则; 缩进分层 / 加粗密度 / flanking / 临时文件夹等通用纪律在 verify_discipline.py 里, 两者互补):**
```bash
~/.workbuddy/binaries/python/envs/default/Scripts/python.exe \
  "$HOME/.workbuddy/skills/vault-write-discipline/scripts/verify_discipline.py" \
  --all "<OUTPUT_MD_PATH>"
```
- **两个 verifier 都 ALL PASS 才 present_files**(2026-09-04 补: 此前本段只跑自身 verifier, 加粗/缩进纪律靠执行者另记 vault-write-discipline, 曾漏跑导致违规文件过检).
- Exit code `0` = ALL PASS (safe to present). Exit `1` = at least one FAIL — fix and re-run.
- The verifier checks every HARD rule in one pass: zero blank lines; single 𒋙-prefixed H1;
  no intro paragraph after H1; 𒋙-prefixed unnumbered headings; half-width punctuation
  (excluding `[[ ]]` target text); no bold-inner-edge punctuation; single-space `N. ` markers;
  explicit incrementing numbering (no lazy `1.`); ≤9 items per flat section (**已知豁免: 用户点名「不分标题、整篇平铺 1-N」的文件, 判据见 `vault-write-discipline` Pre-Write Checklist #8**); no backticks;
  presence of inline source links; and **consecutive identical link sets merged** (an identical
  non-empty link set repeated on ≥2 consecutive list items is a FAIL — merge to the last).
- If the deliverable is genuinely synthesis-only (no real source to link), the link-count
  check will flag — in that case confirm the file truly has no source and consciously accept,
  but still satisfy all other rules.
- Only after ALL PASS: call `present_files` with the written `.md` so the user can open/preview it.

## Hard constraints

- No backticks (`` ` ``) wrapping paths or links in this style of report (a deliberate
  report-style choice, independent of the chat-reply format rule).
- Generated files use NORMAL markdown, including `#`/`##` headings — the user's chat-only
  strict format (first-line summary, no `#`, ordered-list-only) does NOT apply to file
  content. Only my chat replies follow that rule.
- Write full source text; never one-line-summarize the body.
- Link is written INLINE directly after each item's text (same line, no soft-break/newline before the link); NOT on a separate continuation line, NOT a hard new paragraph. Use the link-alias form (图片/视频/音频/pdf by media type; plain note **heading** links use `[[note#heading|标题]]` with the literal word **标题** as alias, never the heading text; whole-note links use `[[note|文章]]` with alias **文章**). When an item has MULTIPLE links, they are space-separated on the same inline position (e.g. `[[a|视频]] [[b|音频]]`).
- Numbered list markers use EXACTLY ONE space after the period (`1. ` not `1.  `). Always normalize `N.  ` → `N. ` before writing. The item text and its wikilink are on the SAME line — the link is written INLINE directly after the text (no soft-break / no separate 3-space continuation line before the link), per the Link rules above. Do NOT push the link to a new soft-break line; the user explicitly requires links inline after the text, on the same line. Exception: when CONSECUTIVE items cite the SAME heading/article, a single merged link after the last of them is allowed (see Link rules: Merge consecutive same-source links) — still inline on that last item's line, never a separate block.
- Category headings are prefixed with 𒋙 and have NO numbering (no Arabic numerals, no Chinese 一、二、); use `### 𒋙...` sublevels ONLY for genuine containment (a section that contains subsections), NOT just because there are many sections.
- **层级上限的场景裁决（2026-09-26，消解三处口径不一）**：本 skill 的汇总场景到 `##` / `###` 两级；`####` / `#####` 只在 `pdf-to-vault-summary` 的「补充内容」子标题链出现（见该 skill 规则 9）；冲刺带背系列「单节超 9 条」时拆**并列 `## 𒋙`**（判据 = 本次处理的是不是带背系列，权威版见教资工作区 `.workbuddy/memory/MEMORY.md`「冲刺带背系列」节）。三者场景不同，不互相套用。
- File MUST start with a single H1 `# 𒋙title` (𒋙-prefixed; **例外：`<vault>\临时\临时记录.md` 不写 H1、直接 `## 𒋙` 分节开头，见 `temp-note-workflow` 硬规则 2 第 7 条**), then go DIRECTLY into the first `## 𒋙` category section — NO intro paragraph after the title. The user finds intro paragraphs redundant and has repeatedly required their omission. If a previously generated file happens to contain an intro paragraph, that was a violation of this rule, not the rule itself — do not treat it as precedent and do not reintroduce it.
- If source content references embedded images/charts, surface the image link/embed (`[[images/xxx.png|图片]]` or the PDF embed `[[file.pdf#page=..&rect=..|图片]]`) INLINE at the end of that item — the user explicitly requires referenced pictures to be linked out, not just described.
- **Indent by containment (隶属/并列 缩进体例).** Any genuine containment relationship in the text MUST be written as a 4-space-indented child list (`    1. ` / `    - ` -- the marker follows the target file's existing style, see `vault-write-discipline` #14), NOT flattened into one line. Sibling items each get their own line at the SAME indent — inheriting the parent's containment. Indent is a multiple of 4, never skips a level, and is CAPPED at 2 levels (only 0 / 4 / 8 spaces — 12+ is a violation; flatten deeper layers into a single `**关键词**:**内容**` line or promote them to sibling `N. ` items). Full rule and worked before/after examples live in `vault-write-discipline` Pre-Write Checklist #14 (single source of truth). Example — do NOT write `1. 德育途径:思想品德课;班主任工作;校会班会;社会实践`; DO write `1. 德育途径` then six child lines each indented 4 spaces.
- Keep the file COMPACT with NO extra blank lines. A list item's link/image continuation line is immediately followed by the next item (no blank line between items), and the last item of a section is immediately followed by the next `##`/`###` heading (no blank line between sections). Only the H1 title line sits alone at the very top. Do not insert decorative blank lines between sections or between items — the user explicitly wants the clean, gapless look (confirmed on the 正项级数汇总 file, which has zero inter-block blank lines and renders correctly in Obsidian).
- Keep key terms bolded for scannability.
- Use ENGLISH (half-width) punctuation in generated files: write `, . ; : " " ( ) ! ?` instead of full-width Chinese `，。、；："（）！？`. This INCLUDES 顿号 `、` → `,`. Only `…` (ellipsis) and `·` (middle dot) are exempt (typographic, not in this set). Wiki/embed syntax `[[...]]` and `![[...]]` is NOT punctuation and stays unchanged. The user added this as a hard rule for ALL generated content.
- **Bold-adjacent punctuation rule (CommonMark / Obsidian rendering):** A bold span `**...**` silently FAILS to render when punctuation touches the delimiter from the INSIDE: (a) first character of the bolded text is punctuation, then the opening `**` is followed by punctuation and, unless it is also preceded by whitespace/punctuation, is NOT left-flanking, so it will not OPEN; (b) last character of the bolded text is punctuation, then the closing `**` is preceded by punctuation and, unless it is also followed by whitespace/punctuation, is NOT right-flanking, so it will not CLOSE. Punctuation OUTSIDE the span (the char before the opening `**` or after the closing `**`) does NOT break rendering - it actually helps flanking - so ignore it. This is the INNER-edge bug; an earlier draft wrongly blamed the outer edge. Common triggers in our content: `**"quoted term"**`, `**\u200B《book》\u200B**`, and crucially **parentheses at the inner edge** — `**麦积山(2014)**` / `**麦积山（2014）**` both break because `)` / `）` sits at the inner edge of the closing `**`. Fix PROACTIVELY when generating: PREFER moving the punctuation OUTSIDE the bold (visible, no hidden chars) — write `**麦积山**(2014)`, `**莫高窟**(1987)、**龙门**(2000)、**云冈**(2001)`, `**维生素缺乏病**(营养代谢性)`. When you must keep punctuation inside a single bold span, insert a ZERO-WIDTH SPACE (\u200B, U+200B) at the inner edge that touches punctuation - right after the opening `**` if the first inner char is punctuation, right before the closing `**` if the last inner char is punctuation. \u200B is invisible and is NOT whitespace/punctuation, so the delimiter validates while the bold range is unchanged. Hidden-char-free alternatives when a clean source is required: move the punctuation OUTSIDE the bold (`"**term**"`, `《**book**》`) or replace `**...**` with HTML `<b>...</b>` (Obsidian renders `<b>` the same and is immune). Full-width Chinese punctuation triggers the SAME inner-edge failure (e.g. `**"term"**`, `**《book》**`), so the fix applies to it too - only the OUTER edge is harmless. The user hit this exact bug (`**"\u200B教师减负十条\u200B"**` failed to render) - apply the fix automatically, do not wait for breakage.
**Note on the examples above:** the full-width Chinese quotes `" "` shown in these examples are there ONLY to demonstrate the flanking position — they are themselves banned full-width punctuation in generated files (see checklist #6 / `vault-write-discipline` checklist #4); when writing, use half-width quotes `"` or 《》 instead of copying the example's full-width ones.
- ALWAYS link to the SPECIFIC heading when the source content sits under a heading. Do NOT substitute a whole-note link `[[note]]` just because it is quicker — open the source file, find the real `## heading` text, and use `[[note#heading text|标题]]` (alias is the literal word **标题**, never the heading text — the user explicitly requires precise heading links; never a whole-note link when a heading exists). A whole-note link uses `[[note|文章]]` (alias **文章**) and is only for genuinely whole-note citations.
- **Line-link supplement (Advanced URI).** When the source `.md` note has NO heading (a `[[note#heading|标题]]` would be dead), or the item must land on an exact row, use a markdown line link `[N](obsidian://adv-uri?vault=<vault-id>&filepath=<相对路径,%2F编码>&line=<N>&column=1&openmode=true&view-mode=source)` (display = the line number itself). Capture `line` via Grep `-n` / Read line numbers; keep `line` 1-indexed; never add `offset`. Do NOT use it to replace working heading links (line numbers drift on edit) — it is the no-heading / exact-row form.
- **No-fabricated-source rule:** The per-item / end-of-file link exists ONLY to point readers back to a REAL original (a vault note, or a media/transcript file). When the deliverable is generated from user-pasted text, a chat transcript, or pure memory — i.e. there is NO genuine source note or media file to link — DO NOT write a fake "来源/来源:" trailing line, and DO NOT write the output file's own storage path (e.g. `<vault>\临时\`) as if it were a source. Omit the trailing link line entirely in that case. Applying the visual format (𒋙 headings, bolding, compactness, English punctuation) is still required; only the fabricated source line is forbidden.

## Reference

See `references/example.md` for a fully worked example (the 教资作文开头结尾段
summary) showing the title, `##` category headings, ordered items with verbatim template
text, and per-item wikilinks (inline alias form) on the same line as the text.
