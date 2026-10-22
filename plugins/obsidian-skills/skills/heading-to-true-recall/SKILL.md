---
name: heading-to-true-recall
description: '把笔记里【带 ⭐ 或 ⏳ 的标题】做成 True Recall 的 basic 问答卡 —— 命中「标题问答 / 标题挖空 / 把这些标题做成卡」时先加载。标题当问题、标题下正文当答案；只做含 ⭐⏳ 的标题、只处理用户点名的那个 md，卡面答案末尾接一行 adv-uri 行链接（2026-10-10 起为默认，因为卡面里标题链接不跳）。'
summary: '把笔记里【带 ⭐ 或 ⏳ 的标题】做成 True Recall 的 basic 问答卡 —— 命中「标题问答 / 标题挖空 / 把这些标题做成卡」时先加载。标题当问题、标题下正文当答案；只做含 ⭐⏳ 的标题、只处理用户点名的那个 md，卡面答案末尾接一行 adv-uri 行链接（2026-10-10 起为默认，因为卡面里标题链接不跳）。'
agent_created: true

---

# 标题问答（标题挖空） → True Recall 卡

用户说「把（这个文件里）带 ⭐ 或 ⏳ 的标题做成卡」「标题问答」「标题挖空」「标题当问题、下面当答案」时走本 skill。

> **本文是「标题转 True Recall 卡」的唯一权威源。** 两层 MEMORY、日志只写一句话 + 指向本文，不复制正文。
> 与 `highlight-to-true-recall`（`==高亮==` → cloze 卡）的分工见「7. 三个 TR skill 的分工」（含 `basic-to-cloze-true-recall`）；那篇里已经定死的东西（Local API 鉴权、token 取法、TR清理 宏、删卡连带机制、孤儿 note）本文**只指路、不复写**。

## 0. 铁律（先读）

1. **只处理用户点名的那个文件**（任务范围纪律）。不主动扫全库、不顺手做同系列其他带背文件。一次点名多个文件就按点名顺序做。
2. **只做「标题里出现 ⭐ 或 ⏳」的标题** —— 这是用户定的筛选闸。用户 2026-09-15 原话："就是标题中含有那两个符号啊，也许以后会放在标题前面的，我还没确定，但是肯定是我刻意加的表示重点的" ⇒ **判据按「含」、与位置无关，不要偷偷改成"只认末尾"**。标记是否出现**只看标题原文**，不做语义推断。
   ⚠️ 已知假阳性：带背7 的 `## 𒋙附录:考前必背30题与⭐标记对照表` 里那个 ⭐ 是标题正文的一部分，会被命中。**排除闸有两个**：`--tail-only`（只认末尾）、`--skip=附录,对照表`（标题含这些词跳过）。**兜底还是"预览时逐条看 Q"** —— 这种脏卡在预览里一眼可见。
3. **先预览、后落盘**。脚本不带 `--apply` 只打印，不写任何东西。**给用户看过预览再落盘**；落盘算"改既有文件"（会往 md 写 frontmatter），按用户纪律要先弹窗确认。
4. **只出 basic 卡，不出 cloze 卡**（本 skill 的产出形态固定）。**与 `highlight-to-true-recall` 混在同一篇笔记里是安全的**——旧版的"别混用"警告已于 2026-09-15 被实测证伪，理由见铁律 6。
5. **必须写 `source_text`**（默认就写，= 标题行原文含 `## ` 前缀）。它同时是「跳回原文」的定位坐标与幂等主键。不写就两头都废。
6. **混用 basic 与 cloze 是安全的（2026-09-15 实测；本条的旧版写反了，别再拦着；**机制真源在 `highlight-to-true-recall` 铁律 9**，本节是同一机制在 basic 侧的结论复述，改那边要同步本节）**：旧版这里写"一篇笔记只走一条路线"，理由是"删一张 basic 会顺带赔掉一张 cloze"——**错的**。真实机制只有两支，且都不命中：
   ① **cloze 支**：`cardType==="cloze" && clozeTemplate && sourceUid` → `getClozeSiblings(sourceUid, clozeTemplate)`。判据是 SQL `WHERE n.source_uid = ? AND c.deleted_at IS NULL` 再逐条比 `clozeTemplate` 字符串 ⇒ **只有"源笔记级 + 该字段逐字相同"这一层，没有"块"这个概念**。
      ⚠️ **这一支对本 skill 建的卡整个不触发**：`POST /cards` 的处理函数只传 `noteTypeId / fields / sourceUid / sourceText`，`createCardFromGenerated` 的返回对象里没有 `clozeTemplate`，SQLite 的 `cards` 表也没有该列 ⇒ 该字段恒为 `undefined`，而这支的外层条件要求它非空。（这是 2026-09-15 源码级核对，不是实测推断。）
      带该字段的只有**手工建卡 / Collect / Anki 导入 / 走过 `updateClozeTemplate`** 的卡；对它们，**同一篇笔记里两处文本完全相同的高亮块会互成兄弟**（比的是 `clozeTemplate` 字符串，不是"同块"）——旧版写的"同块才连坐"是错的。
   ② **反卡支**：`!reverseOf` → `getCardByReverseOf(id)` = 同**一条 note** 里 `template_ord != self` 的另一张（`LIMIT 1`）。而 `POST /cards` 是**逐条建 note + card**（一张卡一条 note）⇒ 同 note 里没有别人 ⇒ **永远查不到目标**。
   **实测（2026-09-15）**：`科目二冲刺带背7 1.md` 名下 18 张 basic + 2 张 cloze（两块不同文本，`sourceText` 一张"人的需要由低级到高级…"、一张"教育过程中…"）→ `DELETE /cards/:id` 删掉一张 basic → 20 张变 19 张、**cloze 两张原封不动**；再跑一次 `--apply` 重建（「新增 1 / 跳过 17」），复跑「新增 0 / 跳过 18」。
   ⇒ **判据：对本 skill 建的卡（`POST /cards` 出的 basic/cloze），删任何一张都只删它自己**。唯一的例外挂在 ① 支上，且**只在带 `clozeTemplate` 的卡上才可能发生**（手工建卡 / Collect / Anki 导入 / `updateClozeTemplate`）：那时删一张会带走「同源笔记里 `clozeTemplate` 逐字相同」的那批。**本 skill 建的卡没有该字段，例外不存在**（旧版写的"同块里有多张 cloze 卡"是把 ① 支的集合缩到了"块"，已作废）。
7. **⚠️ 幂等主键 = `source_text`，绝不能用 `GET /notes/cards` 的 `question`/`answer`**：那两个是**卡面渲染态**（`{{Front}}`/`{{Back}}` 渲染后的结果），拿它比键会永远不相等 ⇒ 每跑一次多一整批卡（2026-09-15 在 cloze 那边用血换来的教训）。脚本已经用 `GET /cards/:id` 的 `sourceText`（未渲染原文）当主键，**复跑必须打印「新增 0 张」**；看到「新增 N>0」立刻停手查键，不要接着跑。
8. **`--apply` 跑完立刻原地复跑一次**，确认「新增 0 张 / 已存在跳过 N 张」才算幂等生效。没复跑验证就别说"建好了"。
9. **不要重建卡来改内容**：正文改了、标题改名了，走 `--refresh`（`POST /cards/:id/update`，只改 `Back`，**不重置复习进度、不新建 note、不攒孤儿 note**）。只有"标题增删"这类结构性变化才需要 `POST /cards/remove-from-note {source_uid}` 清空重来。
10. **收尾按 `highlight-to-true-recall` 第 9 步做残留自检**：库里孤儿 note 数（每张卡一条 note，删卡必然留空壳）+ `<vault>\临时\` 里本轮中间文件；**默认只报告不擅自删**，用户说清后跑 QuickAdd 宏 `TR清理`。清理步骤、还原方式、就绪闸/避让闸、`obsidian://quickadd` 触发法**全部见 `highlight-to-true-recall`**，本文不复写。
11. **`==高亮==` 与 `\boxed{}` 是用户人工专属标记**：本 skill 只读不写，**绝不新增**（详见 `vault-write-discipline` 第 4 条）。本 skill 也不改笔记正文一个字符（只可能加 frontmatter 的 `flashcard_uid`）。

## 1. 本机不可变事实（本 skill 特有；其余 TR 事实见 `highlight-to-true-recall` 第 1 节）

| 项 | 值 |
|---|---|
| 卡型 | **`builtin-basic`**（`type=0`、`fields=["Front","Back"]`、`slug:"basic"`） |
| 模板原文 | `qfmt: "{{Front}}"` / `afmt: "{{Back}}"` —— **答案面只有 Back 本身，没有 Extra**，所以"跳回原文"的链接只能接在 Back 末尾 |
| `template_ord` | basic 卡恒为 **0**（源码 `browserQuery` 的 basic 判据是 `nt.type = 0 AND c.template_ord = 0`）；reversed 才是 `>0` |
| 建卡接口 | `POST /cards`，`card_type` 传 `"basic"`（或任何非 `"cloze"` 值）→ 服务端写 `{Front: question, Back: answer}`；`createdVia` 固定记成 `claude_code` |
| 改卡接口 | `POST /cards/:id/update` body `{question?, answer?}`；basic 分支写 `fields.Back` / `fields.Front`（cloze 分支才写 `Text`/`Extra`） |
| 清空某笔记全部卡 | `POST /cards/remove-from-note {source_uid}` —— "清整条"的正确粒度 |
| 笔记属性 | frontmatter **`flashcard_uid`**（8 位小写十六进制；插件只认 `[a-f0-9]`）—— 生成与写入逻辑同 `highlight-to-true-recall` |
| 本机 Local API | 已开、端口 27182、**要 token**（v2.5.0 起）。token 文件本脚本按「`--token=` → `TRUE_RECALL_TOKEN` → 本 skill 目录 `.local-api-token` → `highlight-to-true-recall` 目录 `.local-api-token`」四级取，两个 TR skill 共用同一份 token |
| 脚本 | `scripts/hq2tr.py`（骨架复制自 `hl2tr.py`：token 鉴权、幂等、`/query` 降级、行链接、frontmatter 读写都同源） |

## 2. 切分口径（本 skill 的核心口径）

**一个命中标题 = 一张卡 = 一条 note + 一张 basic card。**

1. **命中判据**：标题行（`^#{1,6}\s+`，代码围栏内的伪标题不算）**文本里出现 `⭐` 或 `⏳`**（位置无关 —— 现在都在末尾，用户说以后可能挪到前面）。层级不限（`##`、`###` 都做，`--max-level=N` 可收紧）。
   - **已知假阳性**：`## 𒋙附录:考前必背30题与⭐标记对照表`（带背7）那个 ⭐ 是正文用字，会被命中。实测同一篇 `科目二冲刺带背7.md`：按「含」是 19 张、`--tail-only` 是 18 张，差的就是它。收紧用 `--tail-only`（只认末尾）或 `--skip=附录,对照表`。
   - **不要手改笔记的标题来"修"命中问题** —— 标题原文是 `anchor` 与 `source_text` 的依据，改一个字就得重跑 `--refresh --apply`。
2. **问题（Front）** = 标题文本，去掉 `#` 前缀。**默认连 `𒋙` 与 `⭐⏳` 都原样保留**（用户 2026-09-15 定："可以都不去"）—— 理由是这些符号在卡面上不碍事，且能一眼看出哪些是必背（⭐）。想去掉时加 `--strip-marks`。
3. **答案（Back）** = 标题行**下一行**起，直到**下一个「层级 ≤ 本层级」的标题**之前。⇒ 子标题连同它下面的内容**自动并入**本题答案（带背7 那种 `## 大标题` 下挂 `### 小标题` 的结构，小标题内容归大标题那道题）。
4. **标题下正文为空** → 跳过，不建卡（脚本会报"命中 N 个 → 拟建 M 张"的差额）。
5. **答案里的行内链接（`[[X.pdf#page=N|pdf]]`、`[[X.mp4#t=N|视频]]`）原样保留**（用户 2026-09-15 定）。卡面走 MarkdownRenderer，点得开、能看到出处。`![[images/x.png]]` 图片嵌入同理保留。
6. **答案末尾接一行 adv-uri 行链接**（**2026-10-10 广哥改定，现行默认**）：形态
   `[《<笔记 basename>》·<标题>](obsidian://adv-uri?vault=<id>&filepath=<编码相对路径>&line=<标题行号>&column=1&openmode=true&view-mode=source&anchor=<标题前40字>)`。
   - **改默认的原因**：卡面（TR 内嵌编辑器）里 **wikilink 的 `#标题` 锚不跳**（TR 自己没实现锚点跳转），而 adv-uri 行链接能跳——广哥 2026-10-10 实测「行链接能跳、标题链接不能」。旧默认 `[[笔记#标题|标题]]` 因此作废。
   - `--heading-link` 可退回旧的 `[[<笔记>#<标题原文>|标题]]` 形态（保留给需要"抗行漂移"的场合）。
   - **代价（已告知并接受）**：行链接**会随源笔记行号漂移**。广哥 2026-10-10 明确"我的插件自带漂移自愈功能，这个你不用管" ⇒ 不再把漂移当反对理由。
   - **行号基准**：脚本用 `text.split("\n")` 的读盘内容算行号（含 frontmatter），写入 frontmatter 带来的行号后移**已包含在内**，不必另做偏移修正。
   - **target 仍须与标题原文逐字一致**（含 `𒋙`、含 `⭐⏳`、含 `(70题)`）：`𒋙` 跟随该文件的现状，不自行增删。
   - 标题里若含 `#` `|` `[` `]`（会拆坏 wikilink），两种形态都会自动降级成行链接，不生成死链。

## 3. 参数

| 参数 | 说明 |
|---|---|
| 无 | 预览，不写任何东西 |
| `--apply` | 真正写：加 frontmatter `flashcard_uid` + 经 Local API 建卡 |
| `--refresh` | **不新建卡**，把库里每张卡的 `Back` 刷成本地最新（正文改了 / 标题改名后用）。不带 `--apply` 只预览 |
| `--marks=⭐` | 只认 ⭐ 的标题（默认 ⭐ 与 ⏳ 都认） |
| `--tail-only` | 只认标题**末尾**的标记（默认"标题里出现即算"，见第 2 节） |
| `--skip=附录,对照表` | 标题里含这些词的直接跳过（逗号分隔，用来排掉附录/对照表这类假阳性） |
| `--max-level=N` | 只做层级 ≤ N 的标题（默认 6，全部） |
| `--strip-marks` | 问题里去掉 `𒋙` 与 `⭐⏳`（默认原样保留） |
| `--plain-back` | 答案末尾不接链接（默认接行链接） |
| `--heading-link` | 答案末尾退回**标题链接** `[[笔记#标题\|标题]]`（旧的 2026-10-10 前默认） |
| `--line-link` | 显式写行链接（**已是默认**，保留兼容旧命令） |
| `--no-source-text` | 不写 `source_text`（会同时失去跳回原文能力与幂等主键，一般不用） |
| `--limit=N` | 预览条数，默认 20 |
| `--token=<token>` | v2.5.0 起 Local API 要鉴权，显式给 token |

## 4. 执行流程

1. **确认目标**：用户点名的 md 路径（vault 相对或绝对都可，可一次给多个）。
2. **前置自检**：Obsidian 在跑 + True Recall 的 Local API 已开。脚本自己会探 `/status`；**401 = token 缺失或不对**（会直接停并指路设置页 Copy token），**连不上**只警告并退回只读预览。
3. **预览**：`<python> "~\.workbuddy\skills\heading-to-true-recall\scripts\hq2tr.py" "<md路径>" [--limit=30]`
   输出：命中标题数、拟建卡数、uid 是新生成还是已有、每条卡的 Q（标题）与 A 前 100 字、前两条的末尾链接行。
4. **向用户回报预览**（命中几个标题、拟建几张卡、uid 新旧、前后各抽查一条），**等他确认**再落盘。
5. **落盘**：同一条命令加 `--apply`。这一步 ① 给笔记 frontmatter 写 `flashcard_uid`（已有则不动）② 分批（每批 20 张）`POST /cards`，每张带 `source_text`，已存在的跳过。
   **紧接着原地复跑同一条命令**：必须看到「新增 0 张 / 已存在跳过 N 张」。若第二次又报"新增 N 张"，说明幂等没生效 —— **停下查键，不要继续跑**。
   建脏了/建多了：`POST /cards/remove-from-note {source_uid:"<uid>"}` 清空后重来（别用 bulk-delete）。
6. **让用户用命令面板 `True Recall: Open flashcard panel`（Show flashcards for current note）核对张数**，并**关掉 Obsidian 重开确认卡还在**（留存验证）。
7. **跳转验证**：复习界面揭示答案后，点卡面最后那行链接——应打开源笔记并定位到该标题。**行链接（现行默认）无需改名后重跑**；若用了 `--heading-link` 且标题改过名，重跑 `--refresh --apply`。
8. **收尾自检**（铁律 10）：报库里孤儿 note 数与 `<vault>\临时\` 中间文件清单，按用户意思跑 `TR清理`。

## 5. 自检清单（每次执行后核对）

1. 命中标题数 = 肉眼数出的「带 ⭐/⏳ 的标题数」；差额只应该来自"标题下没正文"的那些。**特别检查附录/对照表那类标题有没有被误命中**（`科目二冲刺带背7.md` 的 `## 𒋙附录:考前必背30题与⭐标记对照表` 是标准反例 —— 按「含」判会命中，要建就认，不要就 `--tail-only` 或 `--skip=附录`）。
2. 每条卡的 Q = 标题原文（默认含 𒋙 与 ⭐⏳）；没有把两个标题的正文合成一题、也没有把子标题内容漏掉。
3. 答案末尾是 adv-uri 行链接 `[《笔记 basename》·标题](obsidian://adv-uri?...&line=N&anchor=...)`，**line 与 anchor 都由脚本现读现算**（别手打）；退回标题链接时（`--heading-link`）target 须与笔记里的标题逐字一致（含 `𒋙`、含 `⭐⏳` 的顺序、含题号括号）。
4. `flashcard_uid` 是 8 位十六进制；同一篇笔记没有两个 `flashcard_uid` 行。
5. API 返回的 `created` 数 + 跳过数 = 拟建卡数；失败数为 0。
6. **复跑第二次必须 `created=0`**（幂等生效的唯一证据）。看到"新增 N>0"就停手。
7. 答案里的 `[[X.pdf#page=N|pdf]]`、`[[X.mp4#t=N|视频]]`、`![[images/x.png]]` 是**故意保留**的，不是错误。
8. `--refresh` 复跑应显示「需改 0 张」；若每次都要改，先查是不是 `/query` 关着导致拿了渲染态（那是已知弱判据，写回内容仍正确，只是不美观）。
9. 笔记正文除 frontmatter 外**一个字符都没动**（`git diff` / 前后对比抽查）。
10. **收尾残留自检已做并回报**（孤儿 note 数 + 临时目录清单）。

## 6. 已知边界与待实测项

- ✅ **首次落地实测记录（2026-09-15，对象 `冲刺班/科二/科目二冲刺带背7 1.md`，`--skip=附录,对照表` 建 18 张）**：
  1. **`GET /cards/:id` 对 basic 卡照样返回 `sourceText`** ✓（实测该卡 `sourceText = '## 班主任工作的基本内容⭐'`，即标题行原文含 `## ` 前缀）—— 幂等主键可用，这条是本 skill 的地基。
  2. **复跑幂等成立** ✓：首跑「新增 18 张 / 跳过 0 / 失败 0」，紧接着原地复跑「**新增 0 张 / 已存在跳过 18 张**」。注意本机 `/query` 是关的，幂等走的正是 `GET /notes/cards` + 逐张 `/cards/:id` 的降级路径 ⇒ 命中的只能是 `sourceText` 键（降级路径的 `question`/`answer` 是渲染态、比不中），**等于顺带证明了主键选得对**。
  3. **「删卡不连带」已从"间接证据"升级为实测 ✓（2026-09-15）**：这 18 张 `template_ord` 全部 = 0、且每张卡各自一条 note（活 note 也是 18）⇒ 连带删除的第 ③ 支（`template_ord != self` 的 `LIMIT 1`）查不到目标。同日**真删了一张 basic**（`班主任工作的基本内容⭐`）实测：20 张 → 19 张（17 basic + 2 cloze，cloze 原封不动）⇒ 铁律 6 的判据成立。**旧版这里写的"尚未真删一张实测"已作废**。
  4. 落盘副作用核对：内存在线 18 张、`cardType` 全 `basic`；磁盘库 `活卡 18 / 活 note 18 / 孤儿 note 0`；笔记正文逐字未动，只在文件头插入 3 行 frontmatter（`flashcard_uid: 5b11e9e3`）⇒ **注意预览里打印的 `L###` 行号是"写 frontmatter 之前"的，写后会整体后移 3 行**（卡内容用的是标题文本，不受影响）。
- **落盘延迟仍要记**：本次 13:2x 只读查库时全库活卡显示 0，13:3x 同一脚本已读成 18 —— 磁盘快照滞后于插件内存是常态，**判断状态一律以 `GET /notes/cards` 为准，别信刚写完的磁盘**。
- **`--refresh` 在 `/query` 关闭时是弱判据**：`GET /notes/cards` 给的是渲染态 `answer`，与本地生成的 `Back` 永远不相等 ⇒ 每次都会"需改 N 张"并写回同样的内容。**写回的内容永远取自本地笔记（权威源）**，所以不会写坏，只是看起来不幂等。想精确判定就让用户在插件设置里开一次 `apiEnableSqlQuery`，或接受这个噪声。
- **标题改名 / 正文增删行都会让末尾的行链接失效或错位**（行链接是坐标，不是语义）。这是 2026-10-10 换行链接的代价；广哥明确"漂移自愈归插件管，不用我操心"。**脚本在生成前一定从本地文件现读标题与行号**（不凭记忆、不手打 target）；标题改名或大段增删后重跑 `--refresh --apply`。
- **⚠️ 卡面那行链接会被插件的 `Link Progress Indicators` 挂装饰（已知、用户已决定接受）**：功能 id `link-status-indicators`，总开关 `showLinkStatusIndicators`，另有 "Show in flashcard panel" / "Show during review" 两个子项（本机三项都开着）。它扫渲染容器里**能解析到「有 `flashcard_uid` 的笔记」的 `a.internal-link`**，然后 `insertAdjacentElement("beforebegin", 圆环)` + `insertAdjacentElement("afterend", "4 new · 14 lrn (18)")` —— **插入位置写死**，所以「标题」必然被夹在圆环与统计中间，**只要保 wikilink 就换不了顺序**。用户 2026-09-15 看截图后定：**接受现状、不改**（别为了"让标题落到最后"去换 adv-uri 外链，那会丢掉标题链接的抗改名能力）。
- **★ 同一功能的第二条支线：给「标题」挂汇总（2026-09-15 源码级查实；此前只记了链接支）**：同一个渲染回调 `Yq` 在扫完 `a.internal-link` 之后，紧接着 `querySelectorAll("h1,h2,h3,h4,h5,h6")` —— 对每个标题调 `i0e(标题, app, sourcePath, frontmatterService, cardStore)`：**从该标题往下扫到「同级或更高级标题」为止**，只取这段范围内的内部链接 → `metadataCache.getFirstLinkpathDest` 解析成笔记 → `frontmatterService.getValues("flashcard_uid", 笔记path)` **只留带 uid 的** → 按 uid 去重 → 每篇取其卡片进度；**`g.length < 2` 直接跳过**（不足 2 个带卡笔记就不挂）。命中则圆环 `prepend` 到标题元素最前、汇总（class `ep-heading-summary`）`append` 到标题末尾，数字是**这些笔记的卡数相加**（`zC` 累加 `new/learning/dueToday/total`）。
  **实测后果（2026-09-15，对象 `科目二冲刺带背7.md`）**：它的 H1 与 `## 𒋙附录:考前必背30题对照表` 都被挂上、并显示 `90 new (90)` —— 因为这两段范围里正文链接全是 `[[xxx.pdf#page=N|pdf]]` / `[[xxx.mp4#t=N|视频]]`（**没有 `flashcard_uid`，全被跳过**），唯一带卡的是**附录对照表右列那批跨文件标题链接**（指向带背 1 到 7 七个文件）⇒ 12+11+18+14+10+7+18 = **90**。⇒ **一般判据：给一篇笔记写进 `flashcard_uid` 之后，它内部「引用了 ≥2 篇带卡笔记」的标题会立刻长出汇总，且数字是跨文件的累计卡数、可能远大于本笔记的卡数**（本篇其它 ⭐ 标题没被挂，正是因为那些范围里收集数为 0）。
  **开关共用**：标题支与链接支都走 `Jr(settings,"link-status-indicators")` ⇒ **设置里没有"只关标题"的子项**，要关就是整体关（正文链接的圆环与计数一起消失）。
  真想去掉装饰只有两条路：① 改用 adv-uri 外链（插件只认 `a.internal-link`）——**2026-10-10 起末尾链接已默认是 adv-uri 外链，装饰问题随之消失**；② 关掉插件那条设置（全局生效）。**留档的第三路**：把链接改成**同文件锚链** `[[#标题|标题]]`（不带笔记名）—— 插件那步 `metadataCache.getFirstLinkpathDest("#标题", path)` 拿不到文件就会 `continue`，理论上不挂装饰。**没实测过，已不再需要**（走 ① 即可）。
- **在复习视图里点这行链接会新开标签（必然，与链接写法无关）**：机制有两层，都已核到源码。
  ① **绑的是什么**：渲染出一个内部链接时，Obsidian 绑的点击是 `workspace.openLinkText(href, sourcePath, isModEvent(e))`（`obsidian-1.14.2.asar` 实证；`isModEvent` = 有没有按 Ctrl/Cmd）⇒ 不按修饰键时第三个参数是 **false**。
  ② **false 的含义**：`newLeaf=false` 只在「当前 leaf 是 markdown 视图」时复用当前 leaf，**否则新建 leaf** —— 而卡面渲染在 True Recall 的复习视图 / 卡片面板里，那是**自定义视图、不是 markdown 视图**，所以每次点击都新建标签。
  ⇒ 结论：**「wikilink + 卡面里点」= 每次新开**，这不是我们写法的锅。
  两条**能改**的路：走 `obsidian://adv-uri`（FakeLink 的 `jumpToLine` 自己先 `getLeavesOfType("markdown")` 找同文件 leaf、命中就 `setActiveLeaf`，所以能复用；`jumpOpenInNewTab` 只管"没打开时"要不要新开），或打开 FakeLink 的 `enableInternalLinkSyntax`（默认 false，开了由它接管内部链接语法）。**用户 2026-09-15 决定不改。**
- **答案会很长**：带背题的正文常有 8~10 条、几百字。basic 卡不截断，全量进 Back —— 这是刻意的（简答题本来就要背全）。
- **本 skill 不覆盖图片蒙板（Image Occlusion）**：那类卡建不了（`POST /cards` 只认 basic/cloze；插件没暴露建/改 regions 的接口），走 `highlight-to-true-recall` 里写的编辑器手工画框路线。
- **不处理 `==高亮==`**（本 skill 只读标题行，不碰高亮）：同一篇笔记里两种都做**没问题** —— 混用不会互相误删（2026-09-15 实测，见铁律 6），只是两类卡会并排出现在同一篇笔记的卡片面板里。

## 7. 三个 TR skill 的分工（单一真源对照）

> **第三个（消费端）见文末那行**：把本 skill 建出来的卡再转成 cloze 走 `basic-to-cloze-true-recall`；下表只对照本文与 `highlight-to-true-recall`。

| | `highlight-to-true-recall` | 本文 `heading-to-true-recall` |
|---|---|---|
| 触发源 | 人工画的 `==高亮==` | **带 ⭐ / ⏳ 的标题** |
| 卡型 | `builtin-cloze`（`Text`/`Extra` 两字段，`{{c1::}}` 挖空） | `builtin-basic`（`Front`/`Back` 两字段） |
| 一卡 = | 一个知识块（含高亮的那一段） | 一个命中标题 + 它的整段正文 |
| `template_ord` | 1 | 0 |
| 幂等主键 | 归一化 `fields_json`（+ 块 `source_text`） | **`source_text`（标题行原文）** |
| 卡面跳回 | `Extra` 里写 adv-uri 行链接 | `Back` 末尾写 adv-uri 行链接（2026-10-10 起） |
| 共用 | Local API + token、`/query` 降级、frontmatter `flashcard_uid`、`TR清理` 宏、`hl2tr.py` 与 `hq2tr.py` 同源骨架 | 同左（细节全在左列那篇里） |

**第三个 skill（消费本文的产出）—— `basic-to-cloze-true-recall`**：把库里**已存在的 basic 卡**（默认只挑 `suspended=1` 的）就地转成 **cloze 挖空卡**，脚本 `bc2tr.py`。
- **它不读源笔记**：挖空位置**只认卡面 `Back` 里手画的 `==…==`**；本 skill 建的卡若卡面有 `==`（含手工改卡加上的）就正合它用，**一处高亮都没有就不建卡**。
- 它产出的 `Extra` **一律重建为标题链接**（`[[笔记#标题|标题]]`），卡面首行保留原来的标题行。
- 它是**两级阶梯**：降级时把 basic 卡**挂起**（`POST /cards/:id/suspend`）并造 cloze 卡当扶手；挖空卡达标后再删掉它、取消挂起原来这张 basic 卡 ⇒ **源卡从不删除**（2026-09-19 定，因为插件没有 undelete 路由）。空壳 note 只在毕业那一步留下，且不自动跑 `TR清理`。
- ⚠️ 它特有的坑：源 basic 卡与新 cloze 卡**共用同一行标题当 `source_text`** ⇒ 幂等比对必须排除源卡 id（这也是它识别"谁配谁"的配对键）。口径全在那篇，本文不复写。
