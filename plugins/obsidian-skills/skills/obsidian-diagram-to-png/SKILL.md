---
name: obsidian-diagram-to-png
description: Render diagrams requested by the user into PNG images so they can be embedded in Obsidian vault notes using ![[images/...]] indented under the relevant list item. **首选路线：内容已是 HTML（show_widget 产物 / 用户给的 HTML / CSS 排好的表格卡片）时，用 scripts/html_snapshot.py 直接截图，绝不重画**（重画=重排=失真）；只有纯数据无现成排版时才用 matplotlib 重画。This should be used whenever the user asks to draw, illustrate, or visualize a diagram in a note, especially probability trees, flowcharts, or other simple directed graphs. It replaces raw ` ```mermaid ` blocks with rendered images to match the user's preferred image-indent layout.
agent_created: true
summary: '命中「把图渲成 PNG 嵌进笔记 / 图进笔记 / 配图 / 出图」时先加载 —— **有 HTML 就截图（html_snapshot.py，零重排），无 HTML 才 matplotlib 重画**；PNG 存 images/ 并以 ![[images/xxx.png]] 缩进嵌入（上方必须是正文行，不能是标题）。落盘与否由用户点名。'

---

# Obsidian Diagram to PNG

## Overview

This skill renders requested diagrams as PNG images and embeds them in Obsidian vault notes. The user prefers **image embeds** (`![[images/...]]`) indented under the relevant list item, and explicitly forbids raw ` ```mermaid ` code blocks in notes.

**⚠️ 选型路由（2026-09-26 广哥定；用户级 MEMORY 现无该节名，**本条即权威版**，不再指路）**：按难点知识形态选工具 —— 结构型（分类/体系/口诀框架/层级知识）→ `xmind` + `markdown-mindmap-studio`；密度型（多列对比/公式密集/表格）→ 对话直接画 SVG；流程/时间线/决策链 → `mermaid-diagram` 或 XMind 时间轴；单概念示意/几何直觉图 → 对话 SVG；拿不准先按结构型试 XMind、不理想当场切 SVG 重画。**本 skill 只管落盘与嵌入**，落盘与否仍由广哥点名。

**⚠️ 缩进形态跟随目标文件既有约定（2026-09-26 广哥裁决，唯一真源 `vault-write-discipline` Pre-Write Checklist #12）**：本 skill 早期写死"4 空格"，但与带背类笔记既有图片用 Tab 的现实冲突。现口径 —— **先读目标文件**：既有图片用 Tab 就全文件 Tab、用 4 空格就全文件 4 空格，**同一文件内必须一致**；**全新文件默认 4 空格**。

## 配图纪律（2026-09-29 从用户级 MEMORY 搬入）

- 数学问题（几何、坐标变换、函数图像、概率统计、数列、证明思路、流程）**主动配图**：聊天内用 `show_widget`（**先 `read_me`**）；写进笔记则渲 PNG 存 `<vault>\images\` 再缩进嵌入。
- **图少而准，一图一结论**；**图前说画的是什么、图后逐条解释要点**，**禁止连续 `show_widget` 之间没有文字**。
- **写入 Obsidian 时有图必须一并进文件**（广哥原话）：三类图全覆盖 —— widget 画过的、源材料里有的、写作中新画的；收尾自查"涉及几张图"与文件里 `![[` 数量相等，临时目录不留本次产出的图。真源 `vault-write-discipline` #17。
- **写入 = 文字 + 图整体交付**：出图默认只内联展示，**AI 不主动问"要不要落盘"、不擅自写**；广哥说"写入"时图必须随文一起进文件。

## Trigger

Use this skill when the user says things like:

- "画个图"
- "画个概率树"
- "画个流程图"
- "把这部分可视化"
- "这个题可以画个图说明"
- Any request to draw/illustrate/diagram content that will be written into an Obsidian note.
- Any diagram shown in chat as an inline preview (show_widget) whose topic belongs to a note being written/edited in this session, or to an existing vault note on the same topic. (chat preview is NOT a vault embed — see Core Rule 1.)

## Core Rules

0. **🏆 三档路线，快照优先（2026-09-30 广哥定，最高优先级；此前连错四版的根本教训）**: 把图落进笔记前，**先判断内容当前是什么形态**，按以下优先级选路——**能用快照就绝不重画**：
   - **档 1｜内容已是 HTML（或 CSS 排好的表格/卡片）→ 直接截图（快照）**：用 `scripts/html_snapshot.py <input.html> <out.png> --scale 3`。它调无头 Edge/Chrome 按**原始布局**截图，逐像素忠实、**零重排**——这才是广哥要的"像拍照一样快照粘贴"。**适用**：show_widget 输出的 widget、用户提供的 HTML、任何浏览器里排好的内容。**这是默认首选路线。**
   - **档 2｜内容在聊天里是 widget 形态、但没存成 HTML 文件 → 先把 widget 的 HTML 存盘再走档 1**：`show_widget` 的 `widget_code` 本身就是 HTML 片段，落盘为 `.html`（补一个 `<meta charset="utf-8">` 和必要的字体声明）后截图。
   - **档 3｜内容只是纯数据/文字、没有任何现成排版 → 才用 matplotlib 重画**（`render_*.py` 或临时脚本），并遵守 Core Rule 6/9/10。
   - **🔴 铁律：重画 = 重排 = 必然失真**。用 matplotlib 逐块重画 HTML 内容时，坐标/字号/折行全靠二次计算 ⇒ 越界、串列、行距变松。**只要原内容是 HTML，就不许重画，只许快照。**这是 2026-09-30 连做四版废图的唯一根因——广哥的原话："我不希望你去重排它，为什么每次转 PNG 都需要重排？不能像拍照一样，直接快照下来粘贴过来吗？" 答案是：能，且本该如此。
   - **清晰度只在快照的 `--scale` 上调（scale=3 即 3 倍像素、放大不糊），不靠重画**；裁边由脚本自动完成（去掉空白边）。

1. **Chat inline preview (show_widget) is the DEFAULT for Q&A; disk-embedding only on explicit user order (2026-09-06 rule).** show_widget stays the carrier for Q&A answers, even on topics that have existing notes. AI must NOT proactively ask 「要不要落盘/嵌入」 and must NOT render/embed a Q&A diagram unprompted; when the user explicitly orders it (「写入笔记最后」「嵌入笔记」), render to `<vault>\images\` and embed with `![[images/文件名.png]]` under the relevant list item. Exception (still mandatory, 2026-09-04): when this session is actively writing a note whose content involves the figure, that figure must be embedded as part of the write (vault-write-discipline checklist #17). A write order covers its figures: when the user says 「把…写入/写入笔记最后」, the figures discussed along with that content MUST be written into the target file in the SAME delivery (embed under the matching item, indent follows the target file's existing convention — see the indent rule above); text-only or figure-only partial delivery is a defect. Never split the delivery into isolated sub-questions (e.g. asking about the figure alone) — that misleads the user's judgement (2026-09-06 second clarification).
   **★ 先渲染、后提图 (2026-09-07 用户定, 当天连犯两次, 铁律)**: 任何**提到图的话术**("上面这张图""如图所示""见图 N")之前, 本轮必须**真的调用过渲染工具**(`read_me` + `show_widget`, 或渲染 PNG)——只写"见图"而本轮没渲染 = 用户端根本没有图。当天两次事故(11:5x 与 12:02)都是只调了搜索/只发文字就说"上面这张图", 被当场指出"图又没出来"。**执行顺序固定: 先有渲染调用, 后有指图文字; 发现自己没调用就想配图时, 先补调用再回复。**
2. **Never embed a raw ` ```mermaid ` fence block** in an Obsidian note, even at top level. If a mermaid representation is useful internally, it must be rendered to a PNG first.
3. **Always save generated images** to `<vault>\images\` (the vault's central image folder) with a descriptive, hyphen-connected Chinese or English filename such as `概率树-甲乙食堂.png` or `flowchart-极限步骤.png`.
4. **Always embed using `![[images/文件名.png]]`** indented under the list item it belongs to (**indent form = the target file's existing convention**: Tab or 4 spaces, consistent within that file; 4 spaces for a brand-new file). No blank lines between the item and the embed.
5. **Use compact, readable styling**: light boxes, dark edges, red highlights for target/outcome nodes, and clear Chinese labels.
6. **字号优先，dpi 配套（2026-09-26 广哥定；2026-09-30 量化 + 两次回调）**: 嵌入笔记的图按固定显示宽度（如 `|1150`）展示，清晰度由**两个独立参数**决定，分头治、别混调：
   - **字/画布比 → 管"适配宽度下读不读得清"**：屏显字高(px) = `字号pt × 显示宽 ÷ (72 × 画布宽in)`，与 dpi 无关。**判据（按实际需求，别定死）：在 Obsidian 里按 `|1150` 显示、放大后能认清字即可**。经验锚点：10.5~11in 画布配 9.5~10.5pt、13.6in 配 12.5pt 均可读；**13.6in 配 8pt 那种"明显偏小"才是要返工的**。分辨率救不了字太小。
   - **dpi → 管"放大 k 倍后糊不糊"**：原生像素宽 `W = 画布宽 × dpi`。**硬标准：W ≥ 2000px（够 1.7 倍 1150 显示宽放大；广哥实测 1680px 偏软、2000~2500px 足够）**。⚠️ **2026-09-30 广哥两次回调，明确"规则要求可能太高了" ⇒ 不要盲目拔高**：满足"Obsidian 里放大能看清"就达标，3000px+ 只增体积与渲染耗时，无正当理由。模板脚本默认值已按此区间写死（11in→190~280、13.6in→230、15.5in→200、12in→250、9.2in→330、9in→340、7.2in→420）；手写临时脚本按公式自算。
   - **提 dpi 不改任何布局**：折行/行距全按数据坐标排，dpi 只是把同一矢量画面光栅化更密。图不够清的唯一合规补救 = **改 dpi 重渲**（布局逐像素不变、字号折行原样）。
   - **🚫 二次处理禁令（2026-09-30 广哥定）**：禁止把生成图拿去做 AI 放大/重绘/增强——那会重排文字（一行拆多行、行距变松），广哥实测"处理后文字变清晰但观感不如原版、对比效果反而差"。清晰度不足一律回渲染脚本提 dpi 重出。
   - **🚫 原图够用就别动（2026-09-30 广哥定，优先级最高）**：如果现有的图（原作者的图 / 已交付的图）**在 Obsidian 里放大能看清字**，就**尊重原作者、保留原图**，不要为"更清晰"重渲、更不要二次处理。**只有"放大了仍看不清"才算缺陷**；判据是广哥的实际观感，不是我算出的理论值。这条凌驾于上面所有 dpi 数字之上。
   - **交付前自检**：PIL 验原生宽 ≥ 2000px；脚本内最小 fontsize 参照上条经验区间、以"放大可读"为准。
9. **版式优先于 dpi —— 有 HTML/既有版式时先 1:1 复刻，别自创（2026-09-30 广哥定，当日返工四次）**: 广哥说某图"看着舒服"时，往往指的是**版式**（卡片结构、表格维度行、紧凑行距、配色），不是分辨率。**收到 HTML 原图（或"按这个版式"的指令）时，先逐元素复刻它的结构再渲染**——本次事故：他给的 HTML 是"双卡 + 7 行维度对照表 + 说明条"，我却自创了"双卡 + 三条文字"，信息密度与观感双双劣化，做了两遍才对上。**硬规则**：① 有 HTML/既有图 → 抽其 DOM 结构与 CSS 配色（本例取色 `#E6F1FB/#185FA5`、`#E1F5EE/#0F6E56`、`#F1EFE8`、`#FAEEDA/#EF9F27`）逐块复刻（**但别为清晰度毁掉它的紧凑行距**，见 Core Rule 6 末条）；② **渲染后必须回读 PNG 自查**：卡片文字是否越出框、是否压到 tag、表格单元格是否串列/贴边。**禁止"我改完就交付"**——本次前两版都因未回读而把"文字越出卡片"的废图发出去，被广哥当场看出。
10. **🚫 禁用手工估算字宽 —— 必须用 `TextPath` 实测（2026-09-30 广哥定，连错三版的血训）**: 中文字宽 ≠ 字号（SimHei 全角实际 ≈1.0~1.05em 且随字形浮动），**用 `len(s)*字号` 或 `0.55/1.0` 系数估算必然折错行**，表现为"两卡文字互相越界、表格串列"。唯一可靠做法：
    - `FP = FontProperties(fname="C:/Windows/Fonts/simhei.ttf")`；`w = TextPath((0,0), s, size=fs, prop=FP).get_extents().width` 得到**真实 pt 宽**；
    - 折算：`1 数据单位 = FIG_W×72/100` pt（画布 0-100 且 `subplots_adjust(0,0,1,1)`）；
    - 折行按"逐字累加实测宽 > 可用宽则换行"，绝不用定长切字（`wrap(s,n)`）；
    - **横向并排容器必须留足中缝**：两卡各 43 单位时中缝须 ≥8~10 单位（本次中缝 4→10 才不互相侵入）；空间不够就**加宽画布**（本次 11in→13in、`dpi` 相应降到 214 保证 ≥2700px）而不是压字号。
7. **聊天图底部的补充说明块，落盘嵌入时必须一并画进 PNG（2026-09-26 广哥定）**: show_widget 图下方若带说明块（易混辨析 / 口径解释 / 名词解释等），渲染落盘 PNG 时**不得只画主图**——广哥原话"底下的说明部分也是需要的……那块我也要的"。
8. **缩进嵌入绝不能是标题下第一行（2026-09-30 广哥定，当日连翻两次）**: 缩进（4 空格或 Tab）的 `![[images/...]]` 若紧跟 `##` 标题（上一行没有文字/列表项），CommonMark/Obsidian 会把它解析成**缩进代码块**——图不渲染、整行显示成原始文本（广哥观感："变成代码块""像链接""下面标题加粗全乱"）。**嵌入行必须挂在某一行文字/列表项正下方**（作为该行续行才正常渲图）；标准位置 = 所在节**最后一条**列表项之下（即广哥说的"标题内容的最下方"），放节首也可以但上方必须至少有一行正文。自查判据：**嵌入行的上一行必须是正文或列表行，不能是 `#` 标题行、不能是空行**。⚠️ 缩进本身必须保留（AI 新增内容首行即缩进的通则对图片嵌入同样适用）——治代码块的正确方法是挪位置，不是去缩进。

## Workflow

0. **Decide note-context FIRST, before drawing**: if this session is actively writing a note and its content involves the figure, render + embed as part of that write (vault-write-discipline checklist #17). If it is a Q&A answer (even on a topic with an existing note), show_widget chat preview only — do NOT ask about embedding, do NOT embed unless the user explicitly orders it (2026-09-06 rule).
0.5. **⭐ 选路（Core Rule 0）**：内容已是 HTML/widget → `scripts/html_snapshot.py` 快照（**默认**）；纯数据无排版 → 才用 matplotlib 重画。**有 HTML 却去重画 = 违规**。
1. Understand the diagram the user wants (nodes, edges, labels, what to highlight).
2. Render the diagram to a PNG using the bundled `scripts/render_tree.py` for probability trees or a similar matplotlib-based script for other simple diagrams.
3. Verify the PNG renders Chinese text correctly (uses SimHei or another CJK system font).
4. Place the PNG in `<vault>\images\`.
5. In the note, insert the embed line `    ![[images/文件名.png]]` directly under the relevant numbered item — with the indent form the target file already uses (Tab or 4 spaces; see the indent rule in Overview). ⚠️ The line ABOVE the embed must be a text/list line, never the `##` heading itself — an indented embed as the first line under an `##` renders as an indented code block (Core Rule 8). ⚠️ **Write the indent as real spaces, never `\t` in the tool argument** — the Write/Edit tools emit a literal two-character `\t` instead of a Tab, so the indent silently dies (canonical rule: `vault-write-discipline` Pre-Write Checklist #12末条).
6. Run `verify_discipline.py --all` on the note and ensure ALL PASS before presenting.
7. **Self-check before delivery**: count the figures involved in what you WROTE into notes this session; each must exist as an embedded PNG in the target note (vault-write-discipline #17). Q&A-only diagrams that the user never ordered into a note stay chat-only by design and are NOT defects (2026-09-06 rule).
8. **🔴 交付前必须回读 PNG 亲眼确认（Core Rule 9）**：`Read` 一下刚生成的 PNG，确认文字没越出框/没压 tag/没串列。**未回读就交付 = 前四版废图的直接原因**，属违规。

## HTML → PNG 快照（首选路线，2026-09-30 加）

`scripts/html_snapshot.py <input.html> <out.png> [--scale 3] [--width 760] [--no-crop]`

- 调无头 Edge/Chrome（自动探测；可用 `CHROME` 环境变量指定）按原始布局截图，**零重排**。
- `--scale 3` = 3 倍像素，放大不糊（清晰度只在这里调，不靠重画）；默认自动裁掉白边。
- 中文路径坑已绕开（内部转存到 `%TEMP%` 的 ASCII 路径再截）。
- 典型用法：用户给了 HTML，或 `show_widget` 的内容要落盘 —— 存成 `.html` 后直接跑它。


## For Probability Trees

Probability trees are common in the user's math study. Use `scripts/render_tree.py`:

- Define nodes with `id`, `label`, `x`, `y`, and optional `hl` (highlight).
- Define edges with `s`, `d`, `lab`, and optional `hl`.
- Call `draw_tree(nodes, edges, outpath, title)`.
- The script uses `C:\Windows\Fonts\simhei.ttf` by default. If SimHei is missing, locate another CJK TTF and update the `fontManager.addfont()` call.

## Embedding Example

```markdown
1. 例题: 甲,乙两家食堂, 第一天随机选一家就餐...
    ![[images/概率树-甲乙食堂.png]]
2. 建模与翻译条件: 设 A=...
```

（示例里的 4 空格是**新建文件的默认**；目标文件既有图片用 Tab 时照 Tab 写，见 Overview 的缩进规则。）

## For Two-Column Concept Comparisons (双栏辨析图)

科二/科一的概念辨析（如"两个维度上的归属""A 与 B 不矛盾"）用双栏容器 + 高亮子块的
结构图最清楚。模板 `scripts/render_two_column.py`（默认出图
`<vault>\images\布鲁纳-学科中心与发现学习.png`）：

- 布局法：**数据坐标固定 0-100 × 0-100**，`figsize=(11, 6.2), dpi=280`，`ax.axis("off")`；
  这样所有 x/y/w/h 都是百分数，改内容不用换算像素。
- 两个 `FancyBboxPatch` 外层容器（左右各占 46 宽），内嵌 2-4 个子块；**被辨析的主角子块
  换成另一色系高亮**（如 amber 50/600），一眼看出它跨在两栏之间。
- 跨栏关系用 `ax.plot(..., linestyle=(0, (4, 2)))` 虚线连接，不用箭头。
- 底部放一条"判据条"（gray 50 填充 + 两行文字：粗体结论 + 细体解释），是这类图的记忆锚点。
- 复用方式：改脚本底部的 `items` 列表、两栏标题、底部两行文字与 `out` 路径即可。
- **圆形坑（2026-09-24）**：画布宽高比非 1:1 时 `Circle` 会被横向拉成椭圆 → 改用 `Ellipse((x, y), width=2r, height=2r*fig_w/fig_h)`，按画布宽高比补偿 y 半径（数据坐标 0-100 × 0-100、axes 铺满画布时）。
- **figsize 高度贴合内容（2026-09-24）**：布局只占画布上部时底部留大片空白、图显"扁" → `figsize` 高度须贴合内容实际高度；**多卡对比表已由脚本自动按内容算高度**（见下节「🔴 行高必须按每行实际行数分配」条），其他版式手调同理。

## For Multi-Card Comparison Tables (多卡对比表)

用户 suspend 了 N 张卡、想横向对比记忆时（如「四大教学原则对比」），用
`scripts/render_multi_compare.py`（固化模板，2026-09-23 加）：

- **一行 = 一张卡，一列 = 一个对比维度**（如 原则名 / 核心定义 / 识别标志 / 基本要求）。
  典型场景：几个易混概念辨析、几个公式/定理横向对照。
- **换内容只改底部 `_demo_data()` 区块**：`title` / `headers` / `rows`（每格写一整句，
  **不用手算换行**，脚本按列宽自动折行）/ `col_widths` / `col_colors` / `col_aligns` /
  `col_red_first_line` / `out`。运行 `python render_multi_compare.py`；
  或临时改输出 `python render_multi_compare.py --out=路径.png`（不覆盖已交付图）。
- **🔴 行高必须按每行实际行数分配，禁止 uniform 撑满（2026-10-02 广哥定，作图铁律）**：多卡对比表最常见的废图是「**按最大行数统一撑满所有行**」⇒ 短行底下留一大段空白，整图显得松垮、对比性也散掉。**已在 `scripts/render_multi_compare.py` 落地为默认行为，不需要手算任何高度**：
  - 脚本先把每格按列宽折行，取该行最大行数 `lines_i`；
  - **纵向尺寸全部以 pt 设计再换算成 y 单位**（`LINE_PT=17` 每行文字、`PAD_PT=9` 每格内边距、`TITLE_PT=30` 顶部标题区），因此**行距与 `figsize` 高度解耦**，改分辨率不会让文字重叠；
  - `figsize` 高度**自动按内容算**（`figsize=(13.6, None)`，只吃宽度），内容刚好铺满整图 ⇒ 底部不留大空白；
  - 最后 `ax.set_ylim(bottom, 100)` 让内容撑满 + `savefig(bbox_inches="tight")` 裁掉边缘。
  - 运行时 stdout 会打印 `每行行数 [...] ｜ 行高pt [...]`，**先看这行再回读 PNG**（Core Rule 9）：若某行行数明显少于同表其他行、图上却仍等高，说明走的是旧脚本。
  **配套铁律（对比性与紧凑性必须同时兼顾）**：`figsize`/dpi 只控制像素密度，`row_h` 才决定视觉密度 —— **调 figsize 不等于解决了留白**；figsize 现在只作最后的分辨率旋钮（宽度 13.6in × dpi230 ≈ 3128px，Core Rule 6 的 W≥2000 天然满足）。
  **判据一句话**：短行下面不该有一块和它内容无关的空白。
- **压扁参数（2026-09-25 加、行高内容驱动后已作废）**：~~传 `figsize=(13.6, 4.4)` 压扁~~ —— **现在高度自动算，短表自然就扁**（实测 2 行表 = 13.6×2.5in、4 行表 = 13.6×5.8in），再手传高度反而会拉伸行距。唯一可调的分辨率旋钮是 `dpi`（默认 230）与 `title_fs`（默认 18）。
- **`col_widths` 之和必须 = 96**（画布左右各留 2 单位当外边框）；不等会在 `assert` 处直接报错。
- **自动折行的原理（改列宽/字号时要懂）**：脚本用 `fig.subplots_adjust(0,0,1,1)` 让 axes 铺满
  figure ⇒ `1 x 单位 = 9.792pt`；每列容量 ≈ `(列宽-2.6)*9.792/字号*0.97` 个全角字（半角按 0.55 折算）。
  ⚠️ **别去掉那句 `subplots_adjust`** —— matplotlib 默认 axes 只占 figure 的 0.775 宽，
  每单位 pt 会从 9.792 掉到 7.589，折行容量算大一截 ⇒ 文字跨列溢出（2026-09-23 就踩过）。
- **红色口诀**：把要求列的下标放进 `col_red_first_line`，该列每格**第一行**渲染成红色
  （`C_SLOGAN = "#C0392B"`），其余行正常色 —— 让"口诀"当记忆锚点一眼扫到。
- **配色沿用**：首列淡蓝 `#D6E6F7`、定义列 `#F7FAFD`、标志列 `#FBF7EF`、要求列 `#F5FAF2`，边框 `#8A94A6`。
- 交付文件示例 = `<vault>\images\四大教学原则-对比记忆.png`（四大教学原则，4 行 × 4 列）。
- **与卡片状态的联动**：这类图常常是"**卡被 suspend + 图当扶手**"的记忆组件；图本身是静态 PNG，
  不会自己改卡片。等记住了要"把卡恢复"，走**本 skill** 的 `scripts/restore_suspended_by_note.py`：
  - **一图对多卡**（单篇笔记一张图）：`python scripts/restore_suspended_by_note.py "<笔记md>" [--apply]` —— 图处理完即恢复该笔记挂起的卡。
  - **多图对多卡**（多篇各一张图）：`python scripts/restore_suspended_by_note.py <md1> <md2> ... [--apply]` —— 脚本先检查每篇笔记嵌的 `![[images/...png]]` 是否都已生成，**全部到位才一次性恢复**，缺图则只打印"等待中"退出。
  - **自动收口（JS，开 OB 就跑）**：`<vault>\Scripts\图片综合记忆阶梯收口.js`（QuickAdd 宏 `图片综合记忆阶梯收口`，`runOnStartup=true`；**配置表驱动**，配对写在 `<vault>\.true-recall\image-ladder.json`，一组可配 `images` 多个图卡关键词 + `cardTitleIncludes` 多个待恢复卡标题词 + `minGood`）。判据：组内**所有**图卡都"最近 minGood 次全 Good/Easy + lapses=0 + 未挂起 + state=2" ⇒ `bulkUnsuspend` 对应源卡。
  - **图卡毕业（2026-09-22.3）**：组达标恢复源卡后，**把该组图卡挂起**退出队列——**用挂起而非删除**：图卡没有脚本重建路径（对比图 + 蒙板 Regions 要人工重做，不像 cloze 能靠 `bc2tr.py` 从 `==` 重建），保留可让二次降级直接取消挂起复用；且与 `TR收口` 2026-09-25.3 口径协同，**挂起=清零**，图卡的连续 Hard 连击一并归零。⚠️ 副作用：毕业后该组**永远判不达标**（`judgeImg` 对挂起卡返回 not ready），**若源卡二次降级，须先手动取消挂起图卡**。顺序安全闸：先恢复源卡成功、才挂起图卡（避免两头都空）。

## For "Common Core + N Rows" Comparisons (共同带 + N 题行)

题族横向对照、且**先共用一段内核、再各自补独有项**时（如科二「影响因素类」微观族三题），用
`scripts/render_common_plus_rows.py`（固化模板，2026-09-24 加；默认出图 `<vault>\images\因素题-三题内部外部对照.png`）：

- 四段版式：标题 / 副标题 → **共同带**（题族共用条，末条用强调色 `C_ACCENT` 渲染）→
  **一行一题**（左栏淡蓝＝内部/学生自身、右栏琥珀＝外部/环境与他人，右上角 chip 放口诀，
  `chip` 里含「无口诀」三字时 chip 自动用灰而非红）→ **底部判据条**（多行：记忆判据 + 视频提示）。
- **换内容只改底部 `_demo_data()`**：`title` / `subtitle` / `common_title` / `common_lines` /
  `common_extra` / `rows`（`name` `chip` `inner` `outer`，inner/outer 按栏宽自动折行）/ `bar` / `out`；
  或临时 `--out=路径.png` 不覆盖已交付图。`common_lines` 条目支持 `(前段, 后段)` 元组——
  前段正文色、后段强调色（2026-09-28 加，行内标新增共用条用，如「身心发展的规律与需要」）。
- **高度全自动**：共同带按条数、题行按折行行数、判据条按行数算，剩余空间平均摊进各段间隙 ⇒ 整幅恒填到底。
  内容过多时在 `assert gap >= 1.0` 处直接报错，把行写短或调大 `figsize` 即可（不要手调坐标）。
- 坐标系 0-100 × 0-100 且 `fig.subplots_adjust(0,0,1,1)` ⇒ 1 x 单位 ＝ `FIG_W*72/100` pt
  （本模板 13.6in → 9.792pt），`_wrap()` 的折行容量按此换算；**别删那句 subplots_adjust**。
- 配色沿用：共同带 `#F1F6FC/#7FA8D4`、内部 `#EAF3FB/#6FA3CE`、外部 `#FDF4E6/#D9A55A`、
  判据条 `#F2F4F7/#8A94A6`、正文 `#1F2933`。**蓝＝内部、琥珀＝外部这条映射与用户笔记里的
  「蓝点＝内部（学生自身），琥珀点＝外部（环境与他人）」一致，换题别改这两色。**
- **换新版图要删旧 PNG 时**：`scripts/trash_to_recycle_bin.py <路径>`（回落系统回收站、可还原）。
  ⚠️ 本机两个常用路子都不通 —— PowerShell 的 `Add-Type …Microsoft.VisualBasic` 被安全 hook 拦，
  `send2trash` 走 legacy 分支会拼出 `\\?\J:/…` 报 FileNotFoundError；
  `SHFileOperationW` 返回 rc≠0（J: 盘稳定 rc=2）也**不代表失败**，判据只看"原路径是否还存在"。

## For Hierarchy / Branch Diagrams (层级分支图)

科二「思维形式」「概念体系」这类**顶层一个概念 → 下分左右两支、其中一支再展开成容器 + 横排子块**的
层级结构，用 `scripts/render_logic_thinking.py`（默认出图 `<vault>\images\思维形式-形式逻辑与辩证逻辑.png`）：

- 坐标系 0-100 × 0-100，`figsize=(11, 5.6), dpi=280`，`ax.axis("off")`，`bbox_inches="tight"` 自动去空白；
- 三个 helper：`box(x, y, w, h, fc, ec, rs)` 圆角框（**`fc="none"` 得到空心容器**，用于"框住一组子块"）、
  `txt(x, y, s, size, color, weight)` 居中文字、`arrow(x1, y1, x2, y2)` 单箭头；
- **分叉画法**：两条 `ax.plot` 画竖线 + 横线（不用箭头），再在两支端点各打一个 `arrow()`；
  只作注释的下行连接用虚线 `linestyle=(0, (3, 2))`；
- **容器内横排子块**：`blocks = [(x, 宽, 文字, 字号)]` 循环出框 + 居中文字，块间「→」用 `txt()` 摆在两个块的间隙中点；
- **配色分工**：左支蓝系（主角/展开项）、右支琥珀系（对照/提示），容器描边用各自 ramp 的 200 档淡色；
- 复用：改顶层 / 左支 / 右支 / `blocks` 四组文字与坐标即可，不必动布局代码。
- **丰富版（2026-09-11 加）**：`scripts/render_logic_thinking_rich.py`，**出图路径与 base 版相同**（覆盖式更新）。
  当同一主题要从"一个概念"扩到"上位分类 + 阶段映射"时用这版：顶部加一条**三块横排的分类带**（表现"凭借物由实物走向概念"，
  最右块为主角、向下接主体结构），中部照旧分叉展开，底部加一条**灰底判据条**（粗体一行结论 + 两行细体皮亚杰阶段映射）。
  画布 `figsize=(11, 8.2)`（比 base 版高，多出的两条带各占 ~15 单位）；三段之间留 4-5 单位空隙即可不挤。

## For Flowcharts (程序框图)

The 教资 科三 chapter 算法与框图 needs program flowcharts with the seven standard symbols. Use
`scripts/render_flowchart.py` (self-contained, edit the node/label block near the bottom to change
the algorithm):

- Run: `python render_flowchart.py` → writes `<vault>\images\程序框图七种符号示例.png` (≈2440x2950, dpi340).
  （该 PNG 是**脚本运行后才生成的示例产物**，不是仓库里必须既有的资产；文件路径不存在属正常，不要据此判"引用悬空"。）
- Shape helpers inside: `rbox()` rounded rect (起止框 with `rr=0.48` for the capsule look, 处理框 with
  `rr=0.08`), `pbox()` parallelogram (输入,输出框, slant via `sk=0.3`), `diam()` diamond (判断框),
  `arw()` straight arrow, `poly()` polyline for the loop-back edge, dashed rect + dashed arrow for
  注释框, `Circle` for 连接点.
- **matplotlib gotcha:** a dashed line style MUST be written `linestyle=(0, (4, 2))` (offset + a
  dashes tuple). Writing `linestyle=(3, 2)` raises `TypeError: 'int' object is not iterable`.
- SimHei has no bold face — the `findfont: Failed to find font weight bold` warning is harmless
  (falls back to 400). Set `mathtext.fontset="dejavusans"` and write math as `$i\leq n$`.

## For Non-Tree Diagrams (number triangles, matrices, tables)

`render_tree.py` only covers directed graphs. For grid/table-style diagrams (杨辉三角, matrices, value tables), draw directly with matplotlib patches:

- Use `scripts/render_number_triangle.py [rows] [outfile]` for Yang Hui / Pascal triangles (defaults: 7 rows → `<vault>\images\杨辉三角-前七行.png`).
- Use `scripts/render_rotation_compare.py [outfile]` for the "rotate the point vs rotate the axes" comparison figure (defaults → `<vault>\images\坐标旋转-转点与转轴对比.png`). It is also the template for geometric diagrams: `axis_line()` draws an axis with an arrowhead, `arc_arrow()` draws angle arcs via `annotate(arrowprops=dict(connectionstyle="arc3,rad=0.55"))`, and mathtext labels mix freely with SimHei Chinese.
- Use `scripts/render_polar_rotation_proof.py [outfile]` for the polar-coordinate proof figure (defaults → `<vault>\images\坐标旋转-极坐标证明.png`): left panel shows the polar angle going $\varphi \to \varphi+\alpha$ (转点), right panel shows $\varphi-\alpha$ relative to the new axis (转轴). Its `arc(a0,a1,r,color)` helper draws a real arc polyline plus a tip arrow — better than `arc_arrow()` when the arc must sit at an exact radius.
- Use `scripts/render_basis_proof.py [outfile]` for the basis-vector proof figure (defaults → `<vault>\images\坐标旋转-基向量合成与分解.png`): left = 转点 as vector addition (parallelogram), right = 转轴 as orthogonal projection with right-angle marks. Its `right_angle(ax, foot, u, v)` helper draws the small L-shaped right-angle mark from a foot point along two unit directions; projections are computed as `float(P @ E1) * E1`.
- Use `scripts/render_projection_3step.py [outfile]` for the "projection onto a line through the origin" figure (defaults → `<vault>\images\投影变换-旋转三步法.png`): four panels 初始 → 乘 $R(-\alpha)$ 转平 → 投 x 轴 → 乘 $R(\alpha)$ 转回. Reusable helpers: `draw_l(ax, ang, ...)` draws a line through the origin at any angle, `arc()` draws a labelled angle arc in either direction, `right_angle()` marks the perpendicular foot, `foot_notes()` puts two caption lines under a panel. Same file is the template for any multi-panel geometric sequence.
- For other grids: place cells with `FancyBboxPatch(boxstyle="round,pad=0.02,rounding_size=0.10")`, light fill `#DCE9F7` (normal) / `#F2F4F7` (edge or header), edge `#3E7CB1` / `#8A94A6`, text `#1F2933`, `ax.axis("off")`, `ax.set_aspect("equal")`, save with `bbox_inches="tight", facecolor="white"`.
- Math labels: set `plt.rcParams["mathtext.fontset"]="dejavusans"` and pass raw strings like `r"$(a+b)^{%d}$"`.
- **mathtext 不支持 `\begin{pmatrix}` / `\begin{array}`**: any label written as `$\begin{pmatrix}1&0\\0&0\end{pmatrix}$` raises `ParseFatalException: Unknown symbol: \begin` at savefig time, killing the whole render. There is no escape — mathtext only implements a subset of LaTeX. **Put matrices in the note text (`$...$` in the md renders fine), and keep figure labels in Chinese** (e.g. "左乘 x 轴投影矩阵"). Safe mathtext constructs verified in use: `\alpha`, `^{2}`, `_{1}`, `\frac{}{}`, `\sqrt{}`, `\vec{}`, `\to`, `\neq`, `\cdot`, `\tan`.

## Verifying the PNG When You Cannot View Images

The active model may not support reading images, so never assume the render succeeded. Verify programmatically:

1. Open with PIL, print `im.size` and file size (a blank/broken render is tiny or huge-but-uniform).
2. `collections.Counter(im.getdata()).most_common(4)` — expect white dominant, then the fill colors you used.
3. Count dark pixels (`sum(rgb) < 300`); a few thousand means glyphs actually rendered. Near zero means CJK text came out as tofu or the figure is empty.
4. Confirm the CJK font file exists (`C:\Windows\Fonts\simhei.ttf`) so `plt.rcParams["font.family"]="SimHei"` actually took effect.

## Environment Notes

- matplotlib must be installed in the managed Python venv at `~\.workbuddy\binaries\python\envs\default`. Install with `python -m pip install matplotlib` if missing.
- The script uses `matplotlib.use("Agg")` so it runs headlessly without a display.
- When running the script, prefer the managed Python interpreter: `~\.workbuddy\binaries\python\envs\default\Scripts\python.exe`.
