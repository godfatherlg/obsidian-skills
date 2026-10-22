---
name: basic-to-cloze-true-recall
description: 'True Recall 的「两级阶梯」工具 —— 命中「阶梯 / 降级 / 毕业」时先加载。标题问答卡（basic）记不住就挂起它、把卡面里手画的 ==高亮== 挖空成一张 cloze 扶手卡；挖空卡记住了再删挖空卡、取消挂起原来那张 basic 卡。两个方向都在 scripts/bc2tr.py 里（卡对卡，源笔记一个字不动，配对键 = 同一行 source_text，幂等比对必须排除源卡 id 否则静默一张不建）。'
summary: 'True Recall 的「两级阶梯」工具 —— 命中「阶梯 / 降级 / 毕业」时先加载。标题问答卡（basic）记不住就挂起它、把卡面里手画的 ==高亮== 挖空成一张 cloze 扶手卡；挖空卡记住了再删挖空卡、取消挂起原来那张 basic 卡。两个方向都在 scripts/bc2tr.py 里（卡对卡，源笔记一个字不动，配对键 = 同一行 source_text，幂等比对必须排除源卡 id 否则静默一张不建）。'
agent_created: true

---

# True Recall 两级阶梯：标题卡 ⇄ 高亮挖空卡

用户说「把（这张/这些）suspend 的卡转成高亮挖空卡」「suspend 的标题卡转 cloze」「这张挖空卡记住了，收口」「恢复原来那张标题卡」时走本 skill。

> **本文是「basic ⇄ cloze 阶梯互换」的唯一权威源。** 两层 MEMORY、日志只写一句话 + 指向本文，不复制正文。
> 另两个卡源见 `highlight-to-true-recall`（`==高亮==` → cloze）与 `heading-to-true-recall`（⭐/⏳ 标题 → basic）；那两篇定死的东西（Local API 鉴权 / token 取法 / `/query` 降级 / 删卡连带机制 / `TR清理` 宏 / 孤儿 note）本文**只指路、不复写**。

## 0. 阶梯是什么（先读这一段）

```
标题问答卡(basic)  ──记不住就挂起──▶  它 + 一张高亮挖空卡(cloze)  ──挖空卡记住了──▶  删挖空卡
      ▲                            卡面带标记：🪜 待掌握 → ✅已掌握                        │
      └──────────────────── 取消挂起，重回标题卡（复习进度原样保留）◀───────────────────┘
```

- **降级（down）**：`basic` 卡 → 挂起它 + 按**卡面里手画的 `==…==`** 造一张 `cloze` 卡当扶手。
- **毕业（graduate）**：`cloze` 卡达标 → **先**取消挂起源 basic 卡、**再**软删挖空卡。
- **为什么这个循环是闭合的**：`==` 留在 basic 卡的卡面里（源卡只挂起、从不删）⇒ 挖空卡删掉后随时能零成本重造；而 basic 卡的 FSRS 进度一直没动过 ⇒ 毕业即回到原来的复习轨道。
- **怎么一眼认出阶梯卡（2026-09-19 用户要求"要有标记"）**：挖空卡的 `Extra` **首行**永远是卡面标记 —— 待掌握时是 `🪜 TR阶梯卡 · 待掌握`，达标后翻成 `🪜 TR阶梯卡 · ✅已掌握，可收口`。
  **判据**：插件的卡片列表搜索是 `question.includes(q) || answer.includes(q)`（源码核对），而 cloze 卡的 `answer` = 渲染后的 Text + `<br>` + Extra ⇒ **在插件搜索框输入 `TR阶梯卡` 就能筛出全部阶梯挖空卡，输入 `已掌握` 就是可收口的那批**（搜索在整个卡池上做，不受浏览列表 200 条上限影响）。
  ⚠️ 记得跑 `--sync-marks --apply` 才会把达标的标记翻成 ✅。

用户 2026-09-19 原话：「当我记不住这个标题问答的卡片的时候，我去 suspend 这个卡片，并把关键点变成高亮挖空卡片。当这个高亮挖空卡片记住了，则再删掉这张挖空卡片，恢复之前的 suspend 的卡片。」

## 0.5 铁律（先读）

1. **只处理用户点名的那些卡**（任务范围纪律）。降级模式的默认扫描范围 = **suspend 的 basic 卡**（用户就是拿 suspend 当"待降级"的记号）；毕业模式的默认候选 = 所有配对里达阈值的。不主动扫全库乱动。
2. **⚠️ 降级时源卡只挂起、绝不删除**（2026-09-19 定的阶梯要求，**旧版"建完就软删源卡"已作废**）。原因：插件 Local API **没有任何 undelete 路由**（71 条路由全表核对过；撤销删除只在 UI 的 Undo 通知里，且只在当次会话内有效，走的是插件内部方法 `cardStore.cards.restoreWithCascade()`，Python 侧够不着）⇒ 删了就只能拿库里残留的 `notes.fields_json` 重建（内容在、**FSRS 进度归零**）。老行为仍可用 `--delete-source` 调出，但**不该再用**。
3. **卡对卡 —— 卡面是唯一权威，源笔记不参与**。用户 2026-09-19 原话：「这个就卡对卡改变吧，我不可能一直保持卡和源文件一致，只能说来源于这个源文件。」⇒
   - 挖空位置**只认卡面 `Back` 里已有的 `==…==`**，笔记正文里有没有高亮**一概不管**；
   - **本 skill 一个字符都不写源笔记**（这是它与另两个 TR skill 最大的不同：它们都要读/写笔记）；
   - **绝不猜挖空位置**：卡面一处 `==` 都没有 → **不建卡**，只报告。
4. **`==高亮==` 与 `\boxed{}` 是用户人工专属标记，只读不写**（`vault-write-discipline` 第 4 条）。卡面里现成的高亮是**用户画的**，本 skill 只把它当"哪里要挖空"的判据搬进 cloze。
5. **先预览、后落盘**。脚本不带 `--apply` 只打印，不写任何东西。**给用户看过预览再落盘**；落盘会建卡 / 改挂起状态 / 删卡，属"改既有物"，按用户纪律要先弹窗确认。
6. **毕业默认"脚本筛候选、用户确认"**（用户 2026-09-19 定）：`--graduate` 只列候选，`--graduate --apply` 才执行；`--card=<挖空卡id>` 可点名绕过阈值。
7. **必须看住幂等**：`--apply` 跑完**立刻原地复跑一次**——降级应看到「建卡：新增 0 张」，毕业应看到「可毕业 0 张」。没复跑就别说"弄好了"。
8. **⚠️ 源卡与挖空卡共用同一个 `source_text`**（都是那行标题）⇒ 降级的幂等比对**必须排除源卡 id**，否则把"源卡还在"误判成"新卡已存在"→ **一张都不建、还不报错**（静默空转）。反过来，这同一把钥匙正是**毕业阶段识别"谁配谁"的配对键**。
9. **`GET /cards/:id` 是 basic 卡的原文出入口**：basic 卡型的模板是 `{{Front}}` / `{{Back}}`，没有渲染变换 ⇒ 它的 `question` / `answer` 就是**存值原文**（`==` 都在）。⚠️ **别把这套照搬到 cloze 卡**——cloze 卡的 `question`/`answer` 是渲染态（挖空已变 `[==⁠...⁠==]` / 揭示内容），两边混用会拿到被挖空的文本。
10. **库快照会滞后**，全库扫描可能漏掉刚改动的卡 ⇒ 脚本自己会比对"插件内存活卡数 vs 磁盘快照活卡数"并打 ⚠️。**点名永远无滞后**（`--card=` 与 `--pairs <笔记路径>` 都读插件内存）。
11. **默认不跑 `TR清理`**（用户 2026-09-19 定「软删但先不清孤儿」）：收尾**只报数**（孤儿 note 数 + `<vault>\临时\` 本轮中间文件），用户说清再跑宏（用法全见 `highlight-to-true-recall` 第 9 步路线 A）。
12. **本 skill 不覆盖图片蒙板卡**（`builtin-image-occlusion` 不是 basic，会被直接跳过）。

## 1. 本机不可变事实（本 skill 特有）

| 项 | 值 |
|---|---|
| 输入卡型 | `cardType == "basic"`（`note_type_id = builtin-basic`、`fields = {Front, Back}`、`template_ord = 0`） |
| 输出卡型 | `cardType == "cloze"`（`builtin-cloze`，`fields = {Text, Extra}`）；经 `POST /cards` 建，**不带 `clozeTemplate`**（与另两个 skill 出卡同源 ⇒ 删卡不连带） |
| **挂起 / 取消挂起** | **`POST /cards/:id/suspend`，body `{suspended: boolean}`** —— 一个路由两个方向，返回 `{cardId, suspended}`；缺 `suspended` 会 400。批量用 `POST /cards/bulk-suspend {card_ids, suspended}`。（源码级核对 handler `G7` + 2026-09-19 往返实测✓） |
| 软删卡 | `DELETE /cards/:id`；**没有任何恢复路由**（见铁律 2；只能从 `notes.fields_json` 重建，进度归零） |
| suspend 卡怎么枚举 | `GET /cards/:id` 与 `GET /notes/cards` 都返回 `suspended`；**但 `GET /cards`（浏览列表）不返回 `suspended`，也没有任何"按 suspend 筛选"的服务端参数**（2026-09-19 实测：`?suspended=1` / `?filter=suspended` 全被忽略）⇒ 全库枚举只能**只读读库** |
| ⚠️ `GET /cards` 的条数上限 | **返回被截到 200 条**（`limit=1000` 仍 `count=200`），且**不按新旧排序** ⇒ 刚建的卡可能整条看不见，**不能拿它当"枚举全库"用**（2026-09-19 撞过：新卡的 API 兜底扫描恒返回 0）。它的 `total` 字段倒是权威的活卡数（拿来算滞后） |
| 卡状态语义 | `state`：0=New / 1=Learning / 2=Review / 3=Relearning；`reps`=复习次数、`lapses`=忘记次数。毕业判据**不看 reps**，权威口径见 2.5.3（最近 `--min-goods` 次 Good/Easy + `lapses≤0` + 未挂起 + `state==2`） |
| 脚本 | `scripts/bc2tr.py`（**直接 `import hl2tr`**，复用 token 三级取法、Local API、`plan_cloze()` 挖空格式、`card_fields_key()`、`_render_cloze()`；不复制骨架） |
| 恢复脚本（对比图扶手路线） | `restore_suspended_by_note.py` 已移到 **`obsidian-diagram-to-png`** skill（见该 skill 的「多卡对比表」一节），负责"整组 suspend + 对比图当扶手"的达标恢复。本 skill 仅管 cloze 阶梯的毕业恢复（`bc2tr.py --graduate --apply`）。 |
| 收口脚本（JS） | **`<vault>\Scripts\truerecall收口.js`** —— QuickAdd 宏 **`TR收口`**（`runOnStartup=true`，开 OB 自动跑一次，也可命令面板手动跑）。职责：① 按判据把挖空卡 Extra 首行的标记刷成「待掌握 / ✅已掌握可收口」；② `MODE="auto"` 时**自动收口**达标卡（先取消挂起源卡、再软删挖空卡）；③ **连续 4 次 Hard 且未挂起的卡常驻提示"建议改写卡片"——每次启动都弹、没有"已确认"状态**（2026-09-25.1 起；suspend 该卡或改写后评分断链才不再提；**2026-09-25.3 起重置边界 = suspend，见第 8 条**）；④ Notice 汇报「已收口 N 张 / 失败 N 条」，**不报「挂起待降级」**（suspend 就是用户"处理了"的记号，2026-09-25 删）。日志 `.true-recall/tr-ladder.log` + `~\.workbuddy\tmp\truerecall-ladder.log`。**分工：降级归 Python（要读卡面 `==` + 造 WJ/占位符，格式真源在 hl2tr），收口与刷标记归 JS（纯卡片状态操作，开 OB 就顺手做了）**。 |
| 离线自测 | `scripts/test_bc2tr.py`（**77 项**，不需要 Obsidian、不碰库；改 `split_tail` / `extra_from_answer2` / `build_cloze` / `heading_text` / `is_graduatable` / `swap_mark_line` 后必跑） |
| 本机 token | 沿用 `highlight-to-true-recall/.local-api-token`（`hl2tr.api_token()` 自己会找；本 skill 目录不放 token 文件也能跑） |

依赖关系：本 skill 与 `highlight-to-true-recall` 是**运行期耦合**（`sys.path` 插到对方的 `scripts/`）。若那个 skill 被改名/移走，本 skill 会直接报「找不到同族 skill 的脚本目录」并退出——**别在本 skill 里再复制一份 `plan_cloze`**，挖空格式必须只有一处真源。

## 2. 降级口径（basic → cloze）

**一条 basic 卡 → 一张 cloze 卡（一条 note + 一张 card）。**

1. **标题**＝源卡 `Front`（原样，保留 `𒋙` 与 `⭐⏳`），放在新卡 `Text` 的**第一行**，下接一个空行再放正文。（用户 2026-09-19 选「带标题行」。）
2. **正文**＝源卡 `Back` 摘掉末尾那行跳转链接后的**整段**。
3. **挖空**＝走 `hl2tr.plan_cloze()`，与 `highlight-to-true-recall` **逐字节同款**：`==x==` → `{{c1::x}}`（**全部同一个 `c1`**，一块一个 index，混 c1/c2 必然互相泄题）；**清掉内容里的文本格式**（`**` `__` `*` `_` `~~`）；**三类原样保留**：`$…$` 公式、`` `行内代码` `` 与 HTML 标签（2026-09-20 广哥定，实现 `hl2tr.strip_inline_md()`）；外层 Word Joiner（**必须留**，护的是插件那对 `**` 的 flanking，见 `highlight-to-true-recall` 2 节）。
   ⛔ **2026-10-12 起：内容外与 hint 都不再包 `==`**（`mark` 默认 `False`，彻底走官方原生）⇒ 答案面 = 官方粗体，问题面 = 原生黑字 `[...]` / `[提问]`。要恢复旧黄底钩子得显式 `--cloze-mark`。
4. **`Extra` = 两行：卡面标记行 + 标题链接行**
   - **第一行 = 标记行**（`--no-mark` 可关）：待掌握 `🪜 TR阶梯卡 · 待掌握`；达标后由 `--sync-marks` 翻成 `🪜 TR阶梯卡 · ✅已掌握，可收口`。两行都含可搜 token `TR阶梯卡` —— 用户在插件搜索框里筛卡片就靠它（机制见 0 节）。
   - **第二行 = 标题链接** `[[笔记名#标题原文|标题]]`（用户 2026-09-19 定：「这种由标题卡转的高亮挖空卡，下面给的链接直接给标题链接就好不用是行链接」）。**不造死链**：标题含 `#` `|` `[` `]` 或拿不到笔记名 → 退回源卡 `Back` 里原来那行。源卡原本是 adv-uri 行链接 → **照样换成标题链接**（预览会打一行「来源：标题链接（重建）；源卡原本是：…」）。
   摘取旧尾行的判据（`split_tail()`，看**最后一行非空行**是否整行匹配）：`^[[…|…]]$` / `^[《…》·第 N 块](obsidian://…)` / `^《…》·第 N 块$` / `^[…](obsidian://…)`。⇒ 正文里那种 `5. 鉴别![[笔记#别的标题|别的标题]]` **行首有文字**，不会误摘。`--keep-tail` 可整体关掉摘取。
5. **`source_text` ＝ 继承源卡的 `source_text`**（= 标题行原文，含 `## `），三个理由：① 它是源笔记里**逐字存在**的行 ⇒ `indexOf` 跳转可用、落点在整段开头；② 它是"这张卡从哪来"的坐标；③ 当幂等主键 + 毕业阶段的**配对键**。
6. **源卡**：默认**保留** + 顺手置 `suspended: true`（若它还没挂起）；`--no-suspend-source` 连挂起都不动；`--delete-source` 是已废弃的老行为（软删，见铁律 2）。
7. **幂等 = 双键 + 排除源卡**：键①`source_text`；键②归一化 `{"Text","Extra"}`（本地侧先过 `_render_cloze(Text)` 才与降级路由的渲染态可比）。⚠️ 比对时**必须排除源卡 id**（铁律 8）。
   ⚠️ **`extra_from_answer2()` 必须无条件取「最后一个 `<br>` 之后的全部内容」**——它的判据是 cloze 模板 `{{cloze:Text}}<br>{{Extra}}`。**别学 `hl2tr._extra_from_answer()` 只认 `[《…》·第 N 块]` 开头的尾段**：卡面标记改成 `🪜 …` 开头后那个闸会失配（2026-09-19 实测：Extra 被切空 ⇒ 复跑永远"需要改"、降级幂等也错判）。
   ⚠️ 加了标记就**改了 Extra ⇒ 幂等字段键会变**；既有老卡靠 `source_text` 键兜住（不会重复建卡），但标记要用 `--sync-marks` 补。
8. **源笔记不动**：不加 `flashcard_uid`（本来就有）、不加高亮、不改任何字符。**注意：降级动作不改源笔记，但"挂起源卡"改的是卡片状态**。

## 2.5 配对与毕业口径（cloze → 删挖空 + 复活 basic）

1. **配对键 = （`source_uid`, `source_text`）**（实现即 `pair_key()` 双键；两级 MEMORY 所记「同一行 `source_text`」是同一口径的简化说法）。挖空卡的 `source_text` 继承自源 basic 卡 ⇒ 同一行标题。⚠️ 只认 `source_text` **形如标题行**（`^#{1,6}\s`）的 cloze 卡，免得把 `highlight-to-true-recall` 建的（块原文当 `source_text`，标题是硬边界、永不以 `#` 开头）误配进来。
2. **遍历方式二选一**：
   - **点名笔记**（`--pairs <md路径>` / `--graduate <md路径>`）：走 `GET /notes/cards?source_uid=`（插件内存，**无滞后**）+ 逐张 `GET /cards/:id` ⇒ 精确。
   - **全库**（不带路径）：只读读库枚举 + **滞后告警**（铁律 10）。
3. **"记住了"的判据**（`is_graduatable()`；用户 2026-09-19 定「**两次 good 才算**」+「脚本给候选、他确认」）：**最近 `--min-goods` 次复习的评分全部 ≥ 3（Good/Easy）** + `lapses ≤ --max-lapses`（默认 0）+ 未挂起 + 进 Review 态；`--min-interval=N`（默认 0 不看；填 21 = 插件的 Mature 口径）可再加一道间隔闸。`--any-state` 放开 state 要求；`--card=` 点名**完全绕过阈值**。
   ⚠️ 评分来自 `GET /cards/:id` 的 `reviewHistory`，而插件是 `getCardReviewHistory(id, 20)` ⇒ **只给最近 20 条**（新→旧）——只能判「最近 N 次」，**不能统计历史累计**（源码级核对 2026-09-19）。
   ⚠️ 插件本身**没有**"记住/毕业"这种设置（搜 `graduat` 命中 0，连 Anki 的 graduating interval 都没有）；它只有成熟度分档 `new/learning/young/mature`（`mature` = Review 态且 `scheduled_days ≥ 21`，21 是硬编码）和 leech（本机 `leechThreshold=8`、`leechAction="tag-only"`，即只打标签**不会**自动挂起）。所以那颗 ✅ 是**本 skill 的启发式**，不要当成插件功能。
4. **毕业动作顺序：先取消挂起源卡，再软删挖空卡**。反了的话，删卡成功而取消挂起失败 ⇒ 两头都没有（只剩一张挂起的 basic，还得手工放出来）。现在这样最坏是"两张都活跃"，多复习一张而已。
5. **毕业后的已知副作用**：源卡的 `due` 早就在过去 ⇒ **取消挂起后立刻变 due 并进入复习队列**。这是有意为之（毕业当天就能验证"现在能不能当标题卡答出来"）。API 没有直接改 `due` 的路由，想推迟只能插件 UI 里手动 bury。
6. **挖空卡是软删**（不是挂起）：软删掉的卡不会被"重复建卡"闸拦住（闸只看活跃卡）⇒ **同一张 basic 卡以后能重新降级**，这是循环闭合的关键。若改成"挂起保留"就会踩坑：下次再降级时幂等闸会发现那张挂起的卡已存在 → 跳过建卡 → 结果扶手指向一张挂着的卡。

## 2.6 谁提示用户：收口脚本（JS 侧，开 OB 自动跑）

用户 2026-09-19 定的答案：「写个 TR 收口的 QuickAdd 脚本，开 ob 的时候运行一次」⇒ 落地为
**`<vault>\Scripts\truerecall收口.js`** + QuickAdd 宏 **`TR收口`**（`runOnStartup: true`）。

1. **它做什么**（`MODE = "auto"`，文件顶行可改）：
   - 刷标记：按判据把每张阶梯挖空卡 Extra 首行刷成 `🪜 TR阶梯卡 · 待掌握` 或 `… ✅已掌握，可收口`；
   - 自动收口达标的卡：**先** `cardStore.cards.bulkUnsuspend([源卡])`、**再** `cardStore.cards.softDeleteWithCascade(挖空卡)`（顺序与 Python 侧 `--graduate` 一致）；
   - 连续 Hard 常驻提醒（机制见第 8 条）；
   - Notice 汇报（只有值得一提才弹）：`已收口 N 张：标题…`｜失败条数。**不报「挂起待降级」**——2026-09-25 广哥定「suspend 了就表示我处理了，不需要它报的」，该报告已删；
   - 什么都不用做时**静默**（只写日志）。
2. **`MODE`**：`"auto"`（默认，自动收口）/ `"mark"`（只刷标记+提示，不删卡，想自己确认就用它）/ `"report"`（只报告，一个字节都不改）。
3. **判据与 Python 侧同口径**：最近 `MIN_GOODS(2)` 次评分全 ≥3 + `lapses ≤ MAX_LAPSES(0)` + 未挂起 + `state==2`；评分从 `cardStore.stats.getCardReviewHistory(id, 20)` 取（只 20 条）。
4. **它用什么内部方法**（都已源码核对）：`plugin.flashcardManager.getAllFSRSCards()` 枚举 → `plugin.cardStore.cards.get(id)` 取卡片视图（带 `noteId/sourceText/suspended/state/reps/lapses`）→ `cardStore.notes.getById(noteId).fields` 拿 Extra → `flashcardManager.updateNoteFields(noteId, fields, "manual")` 写回 → `cardStore.markDirty()` + `await cardStore.saveNow()` 落盘。
   ⚠️ **别去 new 插件里的 `bl` / `Sl` / `Li`**：那是压缩包里的模块私有类（挂起/撤挂起/删卡命令），外部拿不到 ⇒ 只能走 store 门面（`bulkSuspend/bulkUnsuspend/softDeleteWithCascade`）。
   ⚠️ `getAllFSRSCards()` 返回的对象**不一定带 `sourceText`** ⇒ 脚本里 `stOf()` 会回退问 `store.cards.get(id)`（不回退会让配对静默失效、脚本变成一声不响的空跑）。
5. **接线（⚠️ 有个坑；同一事实详见 skill `obsidian-macro-debug`，两处各写一份不属重复、不许删，改一处要同步另一处）**：QuickAdd **没有** `onExternalSettingsChange`，且它的 `onunload(){ … this.requestSave.run() }` 会在关闭 OB 时把内存配置回写 ⇒ **必须在 Obsidian 关着的时候改 `<vault>\.obsidian\plugins\quickadd\data.json`**，写完由它下次启动 `loadSettings()` 读。趁 OB 开着写、然后关 OB，等于白写。宏条目结构（照抄现有 TR 宏）：
   ```json
   {"id":"<uuid>","name":"TR收口","type":"Macro","command":true,"runOnStartup":true,
    "macro":{"name":"TR收口","id":"<uuid>","commands":[
      {"name":"truerecall收口","type":"UserScript","id":"<uuid>","path":"Scripts/truerecall收口.js","settings":{}}]}}
   ```
   写完复核 `choices` 条数比改前 **+1**、`path` 对应的文件存在（**不写死具体条数**——宏会随迭代增减，写了必然腐）。备份在 `~\.workbuddy\tmp\quickadd-data.json.bak-20260919` 与原地 `data.json.bak-20260919`。
6. **怎么验证它真的跑了**：看 `.true-recall/tr-ladder.log`（每次运行覆盖写，第一行有版本与判据，末尾有 `落盘 saveNow → true`）。**别只看 Notice**。
7. **它不做什么**：不造挖空卡（降级归 Python）、不改笔记、不动 FSRS 进度、不清孤儿 note（那是 `TR清理` 宏）。
8. **连续 Hard 提示（2026-09-19 用户加：「连续 4 次的 hard 的卡，给我个提示，建议我重新改写卡片」；2026-09-25 改口径：「我没 suspend 的话，每次都要提醒我。因为我可能要有时间才去处理」）**：
   - 判据：`hardRun()` 从**最近一次往回数**连续 Hard（评分 `1=Again 2=Hard 3=Good 4=Easy`）≥ `HARD_STREAK_MIN(4)`；中间出现 Good/Easy 就断链、重新计数。
   - **挂起中的卡不提示**（`HARD_SKIP_SUSPENDED`）——suspend 就是用户"我处理了"的记号。
   - **每次启动命中就弹、没有"已确认"状态**（2026-09-25.1）：旧机制「点掉才算已确认 / 连续次数升级才再提 / 状态存 `.true-recall/tr-hard-flagged.json`」已**作废删除**——用户可能要有时间才处理，只要卡还命中且未挂起，每次开 OB 都常驻提醒；改写卡片后评分断链 ⇒ `hardRun < 4` 自然不再提。旧状态文件留着无害，脚本不再读写。
   - **重置边界：触发点 = 卡被 suspend（2026-09-25.3，替代 .2 的"毕业时刻"）**：凡当前 suspended 的卡，每次运行都把该卡时刻写入/刷新 `.true-recall/tr-hard-reset.json`（`{cardId: epochMs}`）；`hardRun` 只统计该时刻**之后**的复习 ⇒ **挂起即清零**，恢复后从 0 重计，要再满 4 次才二次提示（用户原话："凡是被 suspend 的卡都视为需要清零一次，从 suspend 之后开始计算 hard 的次数"）。毕业恢复 basic 卡时同样写一次——两者都是清零、不冲突。复习时间戳用 `reviewTimeMs()` 多候选兼容，解析不出则跳过过滤、保原行为。
   - ⚠️ **③ Hard 检查是全池扫描**（遍历 `all`，含 image-occlusion 图卡），**不只扫阶梯配对卡** ⇒ 图片蒙板卡同样会触发这条常驻提示，被挂起也同样清零 ⇒ 图片阶梯自动被覆盖，`图片综合记忆阶梯收口.js` 无需改。
   - **提示是常驻的，点一下才消失**（`HARD_NOTICE_STICKY=true`）：`new Notice(msg, 0)` 在 Obsidian 里 = **不设自动隐藏定时器**（源码级核对 `obsidian.asar`：`setAutoHide(0)` 里 `if (duration)` 为假），且 notice 容器自带 `click → hide()` ⇒ 天然"必须点掉"。点掉只是关掉这条 Notice，**不是**"已确认"。设 `false` 退回 12 秒自动消失。
   - 检查本身不改卡、不动调度；**但 2026-09-25.3 起会写重置边界状态文件 `tr-hard-reset.json`**（挂起即清零所需，已非"全程不写状态"）。`MODE="report"` 下也弹。

## 3. 参数

**降级模式**（默认）

| 参数 | 说明 |
|---|---|
| `--list` | 只读列出全库所有 suspend 的 basic 卡（**整串 36 位 UUID** + 标题行 + 卡面 Front），用来挑 id |
| `--card=<id>[,<id>…]` | 点名 basic 卡（**首选**）。⚠️ 必须给**整串 36 位 UUID**：给前 8 位会 404，并被报成「已处理过·源 basic 卡已不在活跃卡里」（误导，2026-09-19 撞过）。`--list` 已改为打印整串，照抄即可 |
| `<md路径>`（位置参数） | 该笔记名下所有 suspend 的 basic 卡（读它的 frontmatter `flashcard_uid` 再按 uid 查） |
| `--all` / 什么都不给 | 全库所有 suspend 的 basic 卡（只读读库枚举 → 逐张 `GET /cards/:id` 复核） |
| `--delete-source` | 已废弃：降级时软删源卡（见铁律 2） |
| `--no-suspend-source` | 降级时不动源卡的 `suspended` |

**毕业 / 配对模式**

| 参数 | 说明 |
|---|---|
| `--pairs [<md路径>…]` | 只读列出配对与两侧状态（带笔记路径 = API 精确；不带 = 全库 + 滞后告警） |
| `--sync-marks [<md路径>…]` | **刷卡面标记**：按判据把每张阶梯挖空卡 Extra 首行刷成「待掌握 / ✅已掌握可收口」（只写 Extra，不动 Text 与调度）。加 `--apply` 才写；跑完复跑应「需要改标记 0 张」 |
| `--graduate [<md路径>…]` | 预览毕业候选（判据见 2.5） |
| `--graduate --apply` | 执行：取消挂起源卡 + 软删挖空卡 |
| `--graduate --card=<挖空卡id> --apply` | 点名毕业（**不看阈值**，人说了算） |
| `--min-goods=N` / `--max-lapses=N` / `--min-interval=N` / `--any-state` | 调毕业阈值（默认：最近 2 次全对、0 次忘记、不看间隔、要 Review 态） |

**通用**

| 参数 | 说明 |
|---|---|
| `--apply` | 落盘（不带就只预览） |
| `--keep-tail` | 不把末尾链接行摘到 Extra（此时 Extra 只留标记行，链接行留在卡面 Text 里） |
| `--no-mark` | 不在 Extra 加 `🪜 TR阶梯卡` 标记行 |
| `--no-hint` / `--no-wj` / `--keep-cloze-bold` | 挖空格式开关 |
| `--cloze-mark` | **（2026-10-12 翻转，取代旧的 `--no-cloze-mark`）** 给挖空内容与 hint 包 `==…==`；⛔ **默认不包**（走官方原生），加了才开。`--no-wj` 会连带把它一起关掉 |
| `--limit=N` | 单轮处理上限，默认 20（超了会打 ⚠️） |
| `--token=<token>` | 显式给 Local API token（一般不用，`hl2tr` 会自己找） |

## 4. 执行流程

**降级（用户说"这张记不住，帮我做成挖空卡"）**

1. **确认目标**：`--card=<id>` / 笔记路径 / 全库。不知道 id 就先 `--list`（⚠️ 从别处拿到的 8 位短 id 用不了，必须整串 UUID；只给 `--card` 时**不要求源卡已 suspend**，脚本会顺手挂起它）。
2. **前置自检**：Obsidian 在跑 + Local API 已开（脚本先探 `/status`；401 = token 不对；连不上直接退出——本 skill **没有**只读预览路线，因为建卡/改挂起必须在插件内存里做）。
3. **预览**：`<python> "…\basic-to-cloze-true-recall\scripts\bc2tr.py" --card=<id>`
   输出：源卡 id / 卡型 / suspend 状态 / uid / 标题 / **挖空处数 + 每处挖空的内容** / 新卡 Text 前 170 字 / 新卡 Extra 与来源 / 计划动作（是否要顺手挂起源卡）。
4. **向用户回报预览**（几张卡、每张挖空几处、**挖的是哪几句**、Extra 是什么、源卡会不会被挂起），**等他确认**再落盘。⚠️ 「挖的是哪几句」必须逐条打出来——挖空位置是他手画的，报出来他才能当场发现标错地方。
5. **落盘**：同一条命令加 `--apply`。**紧接着原地复跑**：应看到「建卡：新增 0 张 / 已存在跳过 N 张」（预览里会先提示"其中 N 张库里已有同款"）。
6. **让用户核对**：命令面板 `True Recall: Open flashcard panel`（当前笔记）→ 新 cloze 卡在列、原 basic 卡**不在列**（因为它被挂起了，面板默认只看活跃卡）。复习界面看一张：问题面是「标题 + 正文，挖空处黄底三个点」，揭示后挖空处黄底（2026-09-20 起不加粗）。
7. **跳转验证**：揭示答案后点卡面下方那行 → 打开源笔记并定位到该段落的**标题行**。
8. **收尾自检**（铁律 11）：只读报两个数——孤儿 note 数、`<vault>\临时\` 本轮中间文件；**默认不删**。

**毕业（用户说"这张挖空卡记住了 / 收口"）**

1. **看现状**（三选一，都是只读）：
   - 插件里：卡片列表搜索框输入 `TR阶梯卡` 看全部阶梯卡、`已掌握` 看可收口的（0 节）。
   - 命令行：`--pairs`（或 `--pairs <笔记路径>`）→ 每对显示：标题、笔记、挖空卡 `state/reps/lapses/间隔`、**最近几次评分**、原卡 `suspended`、以及"毕业判据 ✅/⏳"。
   - `--graduate` 直接筛候选。
2. **刷卡面标记**（可选但建议）：`--sync-marks --apply` —— 把达标的翻成 `✅已掌握，可收口`，你在插件里一搜就知道该收哪张。复跑应「需要改标记 0 张」。
3. **预览候选**：`--graduate`（或带笔记路径 / `--card=<挖空卡id>`）。
4. **回报并按用户意思落盘**：`--graduate --apply` 或 `--graduate --card=<id> --apply`。
5. **原地复跑** `--graduate`：必须「可毕业 0 张」。
6. **提醒用户**：源卡已放出、**立刻变 due**（2.5 节 5）；挖空卡留了空壳 note，要清就跑宏 `TR清理`。

## 5. 自检清单（每次执行后核对）

1. 预览里**每张卡的「挖空」条数 = 你手画的 `==` 处数**；对不上就停下来看原文。
2. 新卡 `Text` 首行 = 源卡 `Front` 原文（含 `𒋙` 与 `⭐⏳`）；标题与正文之间是**一个空行**。
3. `Extra` 首行是 `🪜 TR阶梯卡` 标记（或已达标时 `✅已掌握，可收口`），第二行是标题链接；`Text` 里**不再有**那行链接、也**不含**标记（标记只放 Extra，别污染题面）。挖空内容里**没有文本格式残留**（`**` `*` `_` `~~` 全清；`` `代码` ``、HTML 标签、`$…$` 公式原样）。
4. 全文只有 `{{c1::}}`、**没有 `{{c2::}}`**。
5. `source_text` = 源卡那一行标题（`## ` 前缀在内），不是卡面正文。
6. **降级复跑**：预览「其中 N 张库里已有同款」+ 落盘「新增 0 张 / 已存在跳过 N 张」。
7. **毕业复跑**：`--graduate` 显示「可毕业 0 张」。
8. **源卡状态**：降级后源卡 `suspended=True` 且**仍在活跃卡里**（不是被删）；毕业后源卡 `suspended=False` 且挖空卡已不在活跃列表。
9. **源笔记 `git diff` / 前后对比一个字符都没动**（size / mtime / 含 `==` 行数）。
10. 孤儿 note 数已报（降级不产生新的；毕业会 +1）；且**没有**擅自跑 `TR清理`。
11. 离线自测 `test_bc2tr.py` 仍 77/77 PASS（改过脚本必须先跑它）。
12. **卡面标记在位**：`--sync-marks` 复跑「需要改标记 0 张」；插件搜索框搜 `TR阶梯卡` 能筛出这批卡。

## 6. 已知边界与实跑记录

**实跑记录 1 —— 降级 + 毕业往返（2026-09-19，对象 `科目二冲刺带背2.md` 的 `## 𒋙基础型,拓展型与研究型课程的特点⭐`）**

- 源卡 `72729158`：`editCount = 9`，卡面被手工改过（`Back` 里有 `==必须有严格的考试==`、`==**灵活性**==` 与一段 `(补充)` 文字，**这些在源笔记里都不存在**）—— 正是"卡对卡"口径的现实依据。源笔记第 38~55 行**没有任何 `==`**（全篇只在第 83、106 行各有 1 处）⇒ 走 `highlight-to-true-recall` 在这张卡上根本无从下手。
- 降级（旧默认，软删源卡）建出 cloze `e7e9bf3b`：挖空 2 处、`Extra` = 标题链接；库计数 247 活卡不变、活 note +1、孤儿 note +1；复跑「可转 0 张 / 已转换过 1 张」。
- **善后**：改用"只挂起不删"后，那张被软删的源卡用**库里保留的 `notes.fields_json` 重建**（`POST /cards` + `POST /cards/:id/suspend {suspended:true}`），新 id `eefa3416`，`Back` 与库里原文**逐字相同**、两处 `==` 都在；代价是 FSRS 归零（原 `Learning/reps=4` → `New/reps=0`）。**这就是为什么要遵守铁律 2。**
- 毕业实跑：`--graduate --card=e7e9bf3b --apply` → 源卡取消挂起 + 挖空卡软删；复跑「可毕业 0 张」✓。
- 再降级实跑：`--card=eefa3416 --apply` → 又建出 cloze `ac4c7509`（内容与上一张同款）+ 源卡自动回到 `suspended=True`；复跑「可转 1 张（其中 1 张已有同款）/ 新增 0 张 / 已存在跳过 1 张」✓。**阶梯闭合验证成立。**
- `POST /cards/:id/suspend {suspended:true/false}` 往返实测✓（返回 `{cardId, suspended}`；缺 body → 400 "Body must contain { suspended: boolean }"）。
- 离线自测：`test_bc2tr.py` **77/77 PASS**（含 `swap_mark_line` / 标记相关断言）。

**实跑记录 2 —— 卡面标记（2026-09-19 同日，用户要求"转过来的挖空卡要有标记、学会了也要有标记"）**

- 判据改成用户定的「最近两次全答对（Good/Easy）」：读数来自 `reviewHistory`（插件只给最近 20 条）。
- 新建卡 Extra 首行 = `🪜 TR阶梯卡 · 待掌握`，第二行 = 标题链接；`--sync-marks` 把达标卡翻成 `🪜 TR阶梯卡 · ✅已掌握，可收口`。
- 实跑：`--sync-marks <笔记路径> --apply` 给既有卡 `ac4c7509` 补上标记 → 复核卡面 `answer` 尾部为 `…<br>🪜 TR阶梯卡 · 待掌握\n[[科目二冲刺带背2#𒋙基础型…|标题]]`；复跑「需要改标记 0 张」✓；随后降级复跑仍正确报「其中 1 张库里已有同款」✓（说明带标记后字段键两侧仍对得上）。
- **踩坑并修掉**：`extra_from_answer2()` 原先只认 `[`/`《` 开头的尾段 ⇒ 标记改成 `🪜` 开头后切不出 Extra ⇒ 复跑反复"需要改"、降级幂等会错判。改成**无条件取最后一个 `<br>` 之后的内容**（那正是模板里 Extra 的位置）。

**实跑记录 3 —— 降级（2026-09-19，对象 `科目二冲刺带背2.md` 的 `## 𒋙国家课程与地方课程的特点⏳`）**

- 用户先在**卡面**手画 4 处 `==`（源笔记同段一个 `==` 都没有、源卡 `editCount=0`）：`编制,实施和评价` / `课程标准及各地发展需要` / `==**衔接与补充**==` / `==**延伸与特色**==`。同组第 1 项「**核心与基础**」他**故意没画** —— 预览时逐条报出 4 处，他一眼就能看出漏没漏，不必替他补。
- 建出 cloze `71df2294`（4 处全 c1、Extra = 标记行 + 标题链接）、源卡 `ec1c9883` 保留并置 suspend；复跑「可转 1 张（其中 1 张已有同款）」✓，库计数 活卡 12→13。
- **撞坑**：`--list` 的 8 位前缀直接喂给 `--card=` ⇒ 报「已处理过 …源 basic 卡已不在活跃卡里」（卡其实活得好好的）⇒ 得回库里捞整串 UUID。已按上文修掉（`--list` 打整串 + 措辞改清楚）。
- **卡面没有 `==` 时预览会打「卡面里没有 ==高亮==（本 skill 不猜挖空位置）」并跳过**——这是硬闸，**别代画**。用户答"我刚加上了"之后**重读卡面**再跑，不要拿旧读数下结论。

**其它已知边界**

- **卡 id 是 36 位 UUID，不是 8 位短码** ⇒ `--card=` 给前 8 位会 404，预览却报成「已处理过 …源 basic 卡已不在活跃卡里」（**完全误导**：卡明明活着、在 `--list` 里也看得见）。2026-09-19 已修：`--list` 改打整串、那行措辞改成「卡不存在 / id 不完整（须给整串 36 位）/ 源 basic 卡已不在活跃卡里」。**这类报错先怀疑 id 长度，别怀疑卡被删了。**
- **`GET /cards` 浏览列表被截到 200 条且不按新旧排序** ⇒ 刚建的卡可能隐身（实测：新建的 basic/cloze 两张都不在那 200 条里，导致"API 兜底扫描"恒返回 0，已废弃该设计）。要精确枚举就**按笔记**走 `/notes/cards?source_uid=`。
- **`/query` 关着**（v2.5.0 起默认关）⇒ 一切"查库"都退化成"读磁盘快照 + 逐张 API"。滞后告警是唯一的诚实提示，**点名是最可靠的入口**。
- **源卡 `source_text` 为空**时：新卡也是空 ⇒ 失去主键①与配对键（毕业会报"配不上"）。脚本照常建卡，但在预览里会看到 `(无 source_text)`。
- **源卡 `source_uid` 为空** → 跳过并报错，不建卡（缺 `sourceUid` 的卡挂不到笔记上）。
- **`--keep-source` 已删**（它的语义被新默认"保留+挂起"取代）；**`--delete-source` 只是留给旧流程**。
- **Cloze 与 basic 混在一篇笔记里是安全的**（2026-09-15 实测 + 源码级核对，见 `heading-to-true-recall` 铁律 6）——本 skill 执行完正是这种局面。
- **不做"再转回去"**：cloze → basic 的反向转换需要重建 `Front`/`Back`（标题从哪来、正文怎么拼回链接都有多解）。阶梯的"回去"是靠**挂起/取消挂起同一张 basic 卡**完成的，不是转换。
- **`Extra` 里的标题链接同样会被 `Link Progress Indicators` 挂装饰**（圆环 + `N new · M lrn`），与 `heading-to-true-recall` 6 节描述的是同一支线，用户已决定接受。
- **卡面样式无需改 CSS**：~~占位符 `[==⁠...⁠==]` 与揭示后的 `==…==` 都命中 `span.cm-highlight`，snippets 目录下那个「挖空-高亮黄加粗」CSS 片段 自动生效。~~ ⛔ **2026-10-12 起那个 CSS 片段已删、去加粗补丁也停用**（见 `highlight-to-true-recall` 2.2 节「停用启事」）。**同日起脚本侧那两层 `==` 包裹也一并默认关闭**（`hl2tr.mark_hint(mark=)` / `plan_cloze(mark=)` / `cloze_fill(mark=)` 与 `bc2tr.build_cloze(mark=)` 默认全 `False`、`DEFAULT_HINT` 改裸 `...`）⇒ 现在**卡面完全走官方原生**：问题面 = 原生黑字 `[...]` / `[提问]`，答案面 = 官方粗体；不再有「hint 冷色底」，也不再有脚本给的那层黄底。要恢复旧口径得显式 `--cloze-mark`。
- **毕业阈值是启发式**：「最近 `--min-goods` 次全 Good/Easy + `lapses==0` + 未挂起 + `state==2`」只是"看起来记住了"的代理指标，**真正的裁判是人**（用户 2026-09-19 选的就是"脚本给候选、他确认"）。别拿它当自动删卡的理由。

## 7. 三个 TR skill 的分工（单一真源对照）

| | `highlight-to-true-recall` | `heading-to-true-recall` | 本文 `basic-to-cloze-true-recall` |
|---|---|---|---|
| 输入 | 笔记里人工画的 `==高亮==` | 带 ⭐ / ⏳ 的标题 + 它的正文 | **库里已存在的卡**（basic ⇄ cloze 互换） |
| 读源笔记 | 是（切块、读行号） | 是（扫标题、读正文） | **否**（卡面即全部） |
| 写源笔记 | 只写 frontmatter `flashcard_uid` | 同左 | **什么都不写** |
| 输出卡型 | `builtin-cloze` | `builtin-basic` | 双向：basic→cloze（降级）/ cloze→删（毕业） |
| 一卡 = | 一个知识块（块内高亮共用 c1） | 一个标题 + 整段正文 | 一张 basic 卡的标题 + 正文 |
| 幂等主键 | 归一化 `fields_json` + 块 `source_text` | `source_text`（标题行） | **`source_text` + `fields_json`，且必须排除源卡 id** |
| 卡面跳回 | `Extra` 写 adv-uri 行链接 | `Back` 末尾写标题链接 | **`Extra` = 标记行 + 标题链接；标记即"阶梯卡/已掌握"的识别符** |
| 改卡片状态 | 否 | 否 | **是**（`POST /cards/:id/suspend {suspended}`） |
| 副产物 | 空壳 note | 同左 | 同左（毕业时 +1） |
| 共用 | Local API + token、`/query` 降级、frontmatter `flashcard_uid`、`TR清理` 宏、`plan_cloze()` 挖空格式 | 同左 | **同左 + 直接 `import hl2tr`**（挖空格式的唯一真源） |
