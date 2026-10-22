---
name: obsidian-macro-debug
description: 调试 Obsidian QuickAdd 宏（toggle-加粗.js / latex高亮.js 等 <vault>\Scripts\ 下的宏）的方法论与已知陷阱。当用户反馈宏行为异常（选区错乱、还原不干净、改了不生效）、要求修改宏，或处理"实时预览下选区/光标行为"相关问题时触发。
summary: '调试或修改 <vault>\Scripts\ 下的 QuickAdd 宏（toggle-加粗.js、latex高亮.js 等）时先加载 —— 宏行为异常、选区错乱、还原不干净、改了不生效，或处理实时预览下的选区与光标行为问题。'

---

# Obsidian 宏调试方法论（2026-09-05 实战沉淀）

本 vault 的 QuickAdd 宏在 `<vault>\Scripts\`：`toggle-加粗.js`（文本 `**` + 公式 `\boldsymbol`）、`latex高亮.js`（文本 `==` + 公式 `\boxed`，配套 CSS 片段 `公式高亮-Temml-boxed.css`）。两宏分支骨架保持**镜像**，改一个要对照另一个。

## 1. QuickAdd 缓存铁律
- QuickAdd 会**缓存宏模块**：改了宏文件，必须**完整重启 Obsidian**（或在 QuickAdd 设置里重选宏）才生效。
- 用户快速反馈"还是不行"时，**先核对时间线**——改文件和反馈间隔若只有几十秒，大概率测的还是缓存旧版。
- 必要时在宏里放 Notice 版本文案（如"加粗+公式粗已应用·选区"），让用户确认看到的文案，先确定加载的是新版再谈现象。
- **⚠️ 外部改 `quickadd/data.json`（加/改宏条目）必须趁 Obsidian 关着**（2026-09-19 源码级查实）：QuickAdd 2.26.0 **没有实现 `onExternalSettingsChange`**（它对插件外部改动完全无感），而它的 `onunload(){ … this.requestSave.run() }` 会在**关闭 OB 时把内存里的配置回写**。⇒ 趁 OB 开着改文件、然后关掉 OB = 白改（被它覆盖）。正确顺序：**关 OB → 改 data.json → 开 OB**（启动时 `loadSettings()` 会读）。
  宏条目的形状（照抄现有条目）：`{"id":uuid,"name":"宏名","type":"Macro","command":true,"runOnStartup":bool,"macro":{"name":"宏名","id":uuid,"commands":[{"name":"脚本名","type":"UserScript","id":uuid,"path":"Scripts/xxx.js","settings":{}}]}}`；写完复核 `choices` 条数 +1、`path` 指向的文件存在。
  （同一族的事实：**真回忆的卡片库也一样**——外部直写 SQLite 会被插件内存覆盖，见 `highlight-to-true-recall`；两处的病根相同：**有内存副本的存储，一律"改文件前先让持有者停下来"**。）

## 2. 调试方法论：先埋运行时数据，不盲改
- 涉及**选区/光标/坐标/运行时状态**的问题，纸面模拟（Node 跑纯字符串）只能验证纯逻辑，**无法复现 Obsidian 的选区渲染行为**。
- 正确做法：在宏里埋 `new Notice(\`[诊断] ...\`)` 或 `console.log`，暴露 `getSelection()`/`getCursor()` 的**实际值**，让用户复现一次把原文发回，拿到真实输入输出对再修。
- 实战教训：选区类问题盲改 4 轮未果，靠一条 Notice 诊断（期望坐标 vs 实际坐标 vs 实际选区内容）一次定位。

## 3. 实时预览选区陷阱（实测结论）
- 实时预览（Live Preview）渲染事务会把**含数学块 widget（`$..$`）的选区**显示扩展到包含 markdown 标记（`**`/`==`）——**纯文字选区无此现象、源码模式也无此现象**（所以诊断时"立即读回"选区是正确的，视觉含标记发生在之后的渲染事务里）。
- 这是 Obsidian 的**显示层行为，宏 JS 层不可控**：同步 setSelection、延迟 setTimeout(50/150ms) 都改变不了"它怎么画"。
- 功能层（选区实际内容、还原）不受影响——选区实际=正文，再按能正常还原。处理：让用户接受视觉瑕疵（用户 2026-09-05 已选此方案），或切源码模式用宏。

## 4. 抗吸附还原模式（已验证可靠）
还原时**不依赖选区坐标精确性**（坐标会被吸附/漂移）：
- 用"选区中点"当锚，在所在行搜所有标记对，找中点落在 `[开, 闭+2]` 内的那一对，剥该对 + 内部公式命令（`\boldsymbol`/`\boxed`），选区设为还原后正文。
- 中点对吸附鲁棒（吸附后的选区中点仍在正文附近，含开/含闭/往前越界都能命中同一对）。
- 正向加粗/高亮后：`setCursor` 到正文尾（无选区，再按走无选中还原路径，最稳）或延迟 `setSelection` 保留选区（视觉受陷阱 #3 影响但功能正常）。

## 5. JS RegExp 转义层级坑（剥 LaTeX 命令时）
- 剥 `\boldsymbol{...}` / `\boxed{...}`：
  - 正则字面量 `/\\cmd\{/` 正确。
  - `new RegExp` 字符串构造必须 `new RegExp("\\\\" + cmd + "\\{", "g")`——JS 字符串 4 斜杠 → RegExp 解析为匹配 1 个字面反斜杠。
  - 写成 `new RegExp("\\" + cmd + "\\{")` 会拼出 `\boldsymbol\{`，其中 `\b` 被当成**词边界断言**而非字面反斜杠，匹配恒失败（2026-09-05 实测踩坑，函数原样返回导致"提示还原了但公式没还原"）。
- 剥命令要支持嵌套花括号（depth 计数），见 `toggle-加粗.js` 的 `stripBraceCmd`。

## 6. 判定操作走哪条分支（排错速查）
宏的有选区分支顺序：中点定位还原（在标记对内）→ 选区含公式命令无包裹 → 只剥公式 → 左右是 `$` → 只包公式 → 正向加粗/高亮。现象异常时先确定走了哪条：看 Notice 文案 + 埋诊断输出 selection 实际值。

## 7. 插件命令 id 前缀坑（宏"静默完全失效"的头号嫌疑）
- **宏里写死的 `xxx:yyy` 命令 id 会随插件 id 变化而失效**：Obsidian 内部命令 id = `<manifest.id>:<命令定义里的 id>`。插件换成 fork/二改版（如 `media-extended` → `mediaextended-custom`）后，旧 id 在 `app.commands.commands` 里**不存在**，`if (app.commands.commands[ID])` 直接为假 → 不 preventDefault、不执行任何动作，表现是"按了完全没反应"，**不报错、无任何提示**。
- **查证三步**：
  1. 看 `<vault>\.obsidian\plugins\<目录>\manifest.json` 的 `id`（**不是目录名**）→ 当前真实前缀。
  2. 搜 `main.js` 里命令定义数组的 `id:"..."`（如 `{id:"toggle-play",label:"Play/pause"}`）→ 拼出完整 id。
  3. 翻 `<vault>\.obsidian\hotkeys.json`：新旧前缀**同时存在**就是迁移过（旧热键同样已失效，可在命令面板按 label 手动执行该命令验证插件本身是否正常）。
- **修法（不要再写死）**：运行时探测——先试候选 id 列表，再 `Object.keys(app.commands.commands).find(id => /(^|:)yyy$/.test(id) && /关键词/i.test(id))`；并给一条**不依赖插件命令的兜底路径**（如媒体类直接 `el.play()/pause()`）。执行完可延迟 ~150ms 校验状态是否真的变了，没变就走兜底。
- 生效前提仍是铁律 #1：**改完必须完整重启 Obsidian**（QuickAdd 缓存宏模块）。

## 8. `Scripts/auto.js`：空格播放/暂停宏
- 形态：QuickAdd 宏 `auto`（`runOnStartup: true`，`data.json` 的 choices 里 `runOnStartup` 为 true），注册全局 `keydown` 监听，按空格对可见 `video`/`audio` 做 toggle。
- 依赖：`shouldInterceptSpace`（光标在 `-`/`#`/数字. 后不拦）、`isInNoticeOrModal`、`getVisibleVideos/getVisibleAudios`（含 `.mx-player-shadow-root` 的 Shadow DOM）、`pickTarget`（优先活动 leaf）。
- 已知脆弱点（2026-09-09 已加固）：非 `workspace-leaf` 容器（悬浮窗/弹窗）会被整体过滤；Shadow DOM 内 `offsetParent` 不可靠；`parentElement` 链跨不过 shadow 边界（要用 `getRootNode().host` 跳回宿主再找 leaf）。
- 排查入口：宏内 `DEBUG` 开关的 `console.log('[auto.js]', ...)`（控制台 Ctrl+Shift+I），看"命令"那行是否打印出可用 id 或走直控。

## 9. "生效后动作被执行两次"（如空格：播一下立刻停）
两个来源，按概率排查：
- **来源 A：目标插件自己也绑了同一个键**（见下）。
- **来源 B（更隐蔽，2026-09-09 实证）：自己的"校验 + 兜底"补刀成了第二次动作**。典型错误写法：
  ```js
  app.commands.executeCommandById(cmd);
  const before = medias.map(m => m.paused); // ❌ 在动作之后读
  setTimeout(() => { if (没变) 直控(); }, 500);
  ```
  这样测的是"动作后 vs 500ms 后"，**永远测不出命令是否生效**；一旦判为"没变化"就补刀，于是按键被 toggle 两次 → 表现为"播放后立马暂停"。
  正确写法：`before` 必须在执行动作**之前**读；命令同步路径若已生效（vidstack 的 `paused` 同步翻转）立即 return；只有"状态仍等于命令前"才允许补刀一次，且补刀窗口 ≤250ms。
- **查证手段（不要靠猜）**：埋 `paused`/状态的时间线采样（0/30/80/150/300/500ms）+ 按键上下文（target / activeElement / 是否焦点在播放器内）+ `event.__seen` 标记（判断同一事件是否二次进入 handler = 监听器重复注册）。用户跑一次贴日志即可定性。

### 来源 A：插件自带同一按键
- 案例：Media Extended 用 vidstack 播放器，自带空格快捷键（main.js 里 `_onKeyDown` / `_onPreventVideoKeys`），焦点在播放器内时它 toggle 一次 + 宏 toggle 一次。**宏此前失效时反而"正常"，因为只被执行 0 次** —— 修好命令 id 后才暴露。
- 查证：在插件 `main.js` 里搜 `keydown` / `keypress` 监听与快捷键定义表。
- 修法（三道保险，可叠加）：
  1. **让位**：焦点在播放器/组件内时宏直接 return，交给它自带的处理器。识别要跨 Shadow DOM（`getRootNode().host` 跳回宿主），认 `mx-player-shadow-root` / `media-player` / 自定义标签 `media-player`。
  2. **截断**：捕获阶段 `event.stopPropagation()`，阻止事件到达组件自身的监听器（注意：`preventDefault()` 只挡默认行为，**挡不住别的 JS 监听器**）。
  3. **节流**：时间戳（~200ms）吞掉重复触发，并用一个 `swallowed` 标记阻止后续异步兜底再补一刀。
- 反向教训：宏里的"执行后校验 + 兜底"逻辑，在存在第二个处理者时会变成第二次动作——**补刀窗口一律 ≤250ms**（见来源 B 的正确写法），且必须能感知"已被别处处理"。**⚠️ 早期"校验窗口放宽到 ≥500ms"是把「诊断采样窗口」误当成「动作窗口」, 已废, 勿复用**; 长窗口只用于埋点采样, 不用于补刀。

## 10. 标记嵌套顺序：** 在内、== 在外（2026-09-09 用户拍板）
- 现象：`**==商量着布置==**`（高亮在加粗内）在 Obsidian 渲染异常；`==**商量着布置**==`（高亮在外）正常。**正确顺序恒为 `==**...**==`**。
- 两宏各管一半、必须镜像：`latex高亮.js` 保证 `==` 加在已有 `**` 的**外侧**；`toggle-加粗.js` 保证 `**` 加在已有 `==` 的**内侧**。只改一个，另一个会把顺序重新弄反。
- **无选区也能判断，不必依赖选区内容**（用户担心的点）：判据是"本行标记配对 + 覆盖范围"，不是选区文本。做法：
  1. 扫本行所有 `==` / `**` 起始下标 → **必须跳过行内 `$...$` 区间**（否则公式里的 `a==b`、`a**b` 被当标记，配对全乱）。
  2. 偶数下标=开、奇数下标=闭，找覆盖 `[a,b]` 的那一对（无选区时 `a=b=光标ch`，有选区用中点 `mid` 抗吸附）。配对奇偶天然抵抗 `**甲**和**乙**` 这类误判。
  3. 命中后整块替换（连标记一起），`==` 写外 / `**` 写内，光标 `ch+2`。
- 有选区时只在"选区贴满该块内容"才升级到外层：判据 `from>=o && to<=c+2 && from<=o+2 && to>=c`（选了内容或连标记一起选）。只选了块内一部分（`**甲乙丙**` 只选"乙"）**不动**，按原样在内部加——不擅自扩大用户明确选定的范围。
- 取消优先于正向：两宏都先查自己的标记、命中即取消。所以旧的错误嵌套 `**==x==**` 按高亮宏 = 取消高亮得 `**x**`（用户 2026-09-09 选定：不做自动规整，维持取消语义）。
- **自测手法（有效）**：宏是 CommonJS（`module.exports = async params => {}`），可在 Node 里造 `global.app = {workspace:{activeEditor:{editor: fake}}, commands:{executeCommandById}}` + `global.Notice = class{}`，再 `require` 真实文件跑用例。假 editor 只需实现 `getSelection / getCursor("from"|"to") / getLine / getRange / replaceRange / replaceSelection / setCursor / setSelection`。纯字符串分支（嵌套顺序、配对、公式加框）能完整验证；只有"实时预览选区吸附"这类渲染行为测不了。
