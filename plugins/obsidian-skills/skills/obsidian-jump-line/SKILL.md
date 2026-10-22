---
name: obsidian-jump-line
description: '打开 / 跳行 / 聊天里引用 vault 内容时先加载（唯一权威）—— 按措辞三分流：不提「打开」只回答并文字列文件；说「打开 XXX」自动开最相关一篇并跳行；说「打开所有 XXX」再生成 HTML 链接页。本机跳行由 FakeLink 注册的 adv-uri 协议接管（未装 Advanced URI），它只认 filepath 与 line。引用行 / 标题 / 整篇一律转 obsidian:// markdown 链接，显示文字分别为行号数字 / 标题 / 文章。'
summary: '打开 / 跳行 / 聊天里引用 vault 内容时先加载（唯一权威）—— 按措辞三分流：不提「打开」只回答并文字列文件；说「打开 XXX」自动开最相关一篇并跳行；说「打开所有 XXX」再生成 HTML 链接页。本机跳行由 FakeLink 注册的 adv-uri 协议接管（未装 Advanced URI），它只认 filepath 与 line。引用行 / 标题 / 整篇一律转 obsidian:// markdown 链接，显示文字分别为行号数字 / 标题 / 文章。'
agent_created: true

---

# 跳转到 Obsidian 指定行 / 打开某知识点的相关笔记

用户说"打开 XXX""打开所有 XXX""找 XXX 相关的笔记""XXX 怎么算/怎么做"等，都走本 skill。核心能力：**在 vault 搜出所有相关内容 → 自动打开最相关的一篇并跳行 → 其余相关文件按模式呈现**（默认=文字列表，说"所有"才出 HTML 链接页）。

> **本文是 Obsidian 行跳转的唯一权威源。** 两层 MEMORY、日志、其他 skill 只写"见 obsidian-jump-line"，不复制本文正文。凡与本文冲突的旧表述一律以本文为准。

## 本机环境事实（唯一真源，勿在别处重复定义）

1. **vault id** = `<vault-id>`（vault 名 `<vault-name>`），根目录 `<vault>`。
2. **未装 Advanced URI 插件**；行跳转由 **FakeLink** 插件注册 `obsidian://adv-uri` 协议接管（`data.json` 的 `jumpEnabled: true`，`main.js` 里 `registerObsidianProtocolHandler("adv-uri")`）。
3. FakeLink 的 adv-uri handler **只认 `filepath` + `line`**：
   - 有 `line` → `jumpToLine`（内部 `openFileOnly` 打开/聚焦 + 等编辑器就绪 + `setCursor` + `scrollIntoView` 居中；**文件未打开时它会自己打开**）。
   - 无 `line` → 仅 `openFileOnly`（打开/聚焦）。
   - **不认** `close` / `heading`(其余 `openmode` / `view-mode` 对插件逻辑也无影响,纯透传)——插件只解析 `filepath` + `line` 两个参数。
   - **URI 模板仍统一带 `openmode=true`**(与插件自身 `copyLineUri` 输出、用户历史链接格式一致;2026-09-05 实测带与不带均能外部直达)。

## AI 直跳唯一流程（说"打开 XXX"/"打开第 N 行"时执行）

> **🔒 全局标准（2026-09-10 广哥拍板："以后以你这个打开逻辑为准"）**：以后**所有**"打开"类请求一律走下面这套，不再逐次试探别的通路：
> **① 定位**：Grep 全库（或按限定目录）找落点行 → 读上下文确认。
> **② 发送**：`~\.workbuddy\binaries\python\versions\3.13.12\python.exe "~\.workbuddy\skills\obsidian-jump-line\scripts\jump_activate.py" "<vault相对路径>" <行号>`（`dangerouslyDisableSandbox: true`）。
> **③ 置前**：脚本内自动完成（`Processed URI` 收据 + `ShowWindow/SetForegroundWindow`）。
> **④ 回执**：读完上下文 + 一句落点结论回复；多落点（冲刺班 vs 精讲班）时主落点开文件、次落点文字给出。
> 不用再问用户"开没开"、不用 `os.startfile`、不用先试 `ShellExecuteW`。只有脚本自身报错（无 `Processed`)时才按第 6 条排查。

1. **无需授权弹窗,但可用通路只有一条**(2026-09-04 用户确认无需授权; 2026-09-10 修正通路):**一律走上面「🔒 全局标准」的 `jump_activate.py**(内部是 Obsidian.exe 直调)**, 不要用** PowerShell `Start-Process` / 托管 Python `os.startfile` —— 这两条在本机实测**完全静默**(进程 PID 零变化, 见第 2 条), 照本条旧措辞走会白跑。另: 沙箱会静默吞掉 `obsidian://`(exit 0 零报错、Obsidian 无反应), 故发 URI 那一侧**必须带 `dangerouslyDisableSandbox: true`**。
2. **单发一条 URI 即可**(无论文件开没开,FakeLink 会自开+跳):
   `obsidian://adv-uri?vault=<vault-id>&filepath=<编码相对路径>&line=<N>&column=1&openmode=true&view-mode=source`
   - **⚠️ 本条旧措辞已作废(2026-09-10 第 14 次审查修正)**:原写"用托管 Python `os.startfile(uri)` 或 PowerShell `Start-Process $uri`,**优先 Python 直发**"——这条**已失效**,照做必定白跑:本机 `os.startfile` / `ShellExecuteW` 对本 URI **完全静默**(进程 PID 零变化),`Start-Process` 亦静默;且 PowerShell 命令里的百分号编码(`%E4%B8%8A` 等)会被安全 hook 误判为 cmd 的 `%VAR%` 语法而整条拦截。
     **现按上面「🔒 全局标准」执行**:只走 `scripts/jump_activate.py`(内部 Obsidian.exe 直调 + 置前)。旧措辞保留在此仅为说明"为什么不能再用",**不要照它发**。
   - 托管 Python 路径(供 `jump_activate.py` 使用):`~\.workbuddy\binaries\python\versions\3.13.12\python.exe`。
   - **⚠️ 最强通路（2026-09-10 定，首选）：直接执行 `"<ObsidianInstallDir>\Obsidian.exe" "<uri>"`**（`subprocess.run` 即可，需 `dangerouslyDisableSandbox: true`）。程序会回显 `Processed URI ...`，**收据可查**。当日 `os.startfile` / `ctypes.ShellExecuteW` 对本 URI **完全静默**（进程 PID 零变化，对照 `obsidian://open?vault=<vault-id>` 同样静默；`uriCallbacks` 为 true、注册表 HKCU/HKCR 双写正常，故属**系统协议关联层失效**），换此通路首次即成功。**判定顺序：先试 Obsidian.exe 直调（有 `Processed URI` 回显），只有在它也不回显时才怀疑 `uriCallbacks`/注册表**。
   - **⚠️ 直调通路的代价：可能"要用户再点一下 ob 才真正跳"（2026-09-10 广哥实测反馈，未复现到确定成因）**——直调 exe 起的是**瞬间子进程**，易受窗口焦点（前台锁定）/ `requestSingleInstanceLock` 转发时序影响，导致 Obsidian **不自动置前**；此时光标其实已 `setCursor` 到目标行，只是窗口没抢到焦点，用户点一下窗口就"看见跳了"。
     - **标准做法：用配套脚本 `scripts/jump_activate.py`**（skill 目录下），一步完成"直调发 URI + 置前主窗口"：
       `C:\Users\...\python.exe <skill目录>\scripts\jump_activate.py "<vault相对路径>" <行号>`
       脚本逻辑：① `subprocess.run([Obsidian.exe, uri])` 发 URI；② `sleep 2.5`；③ 枚举窗口取标题**含 ` - OB - Obsidian`** 的那个（⚠️ 标题尾巴带版本号 `Obsidian 1.14.2`，**不能用 `endswith("Obsidian")`**，否则永远返回 None）；④ **只在 `IsIconic`（最小化）为真时**才 `ShowWindow(hwnd,9)`（⚠️ 无条件调 `SW_RESTORE` 会把**已最大化**的 Obsidian 还原成普通窗口，2026-09-10 广哥反馈"ob 总是变成窗口化"即此因，已修）+ `AttachThreadInput` 绕过前台锁定后 `SetForegroundWindow`。
     - **读判据**：`workspace.json` 的 active leaf 已指向目标文件 = URI 已送达且防抖计时已启动，**不能证明窗口已置前**；两者要分开判。最终仍以广哥是否看到跳转为准。
     - 仍是**首选**，因为它是本机唯一有送达收据的通路；不要为这点副作用退回 `os.startfile`（那条在本机已完全静默）。
   - **FakeLink 侧固有延迟（读源码确认，非 bug）**：`openFileOnly` 打开文件后无条件 `await waitForEditor(view, targetLine, jumpDelayMs)`，而 `waitForEditor` 的循环条件是 `view.editor.lineCount() >= targetLine` 且**无提前返回**——只要行数未即时达标就**一直轮询到 `jumpDelayMs` 超时**（本机实测该值 **8000ms**）。因此"文件新开"场景下光标可能延迟数秒才落位；`jumpDelayMs` 调小（如 1500~2500）可明显改善观感，代价是超大文件等编辑器就绪不足时可能落点不准。
3. **filepath 铁律**:vault 根起**完整相对路径**(含 `2026上数学教资` 等全部嵌套前缀,漏一层即失效),中文做百分号编码、`/` 编码为 `%2F`——用 `urllib.parse.quote(rel, safe="")` 或 PowerShell `[System.Uri]::EscapeDataString($rel)`。
   - **⚠️ 路径存在性闸（2026-10-21 第二次链接事故根因，最优先）**:判据一句话——**生成的 rel 必须能在 `<vault>` 下 `os.path.exists` 为 True**。本机 **vault 根 = `<vault>`**，而 `2026上数学教资` 只是它的**子目录**（会话工作区），所以 `冲刺班/科二/xx.md` 这种「工作区起」写法**天然漏掉 `2026上数学教资/` 这一层** ⇒ 百分号编码可以完全正确、`--check` 也全绿（它只验编码 round-trip），但 `<vault>\冲刺班\…` 不存在 ⇒ FakeLink **找不到文件、静默不跳、零报错**（实测长度 118 vs 170）。
   - **执行动作**：① 一律用 `gaicuo/scripts/gaicuo_link.py` 生成，**禁手拼**；② 传参**优先传绝对路径**（`-f "<vault>/2026上数学教资/冲刺班/科二/xx.md"`，正斜杠），脚本自动剥 `<vault>` 前缀，不必记层级；③ 看它打印的 `FILE=` 行——出现「漏了工作区前缀，已自动补全」说明我给的是工作区相对路径（脚本已纠正、但要用补全后的路径），出现 `ERROR`／`ambiguous` 直接停下，不许带病交付。
4. **模板统一带 `column=1`**(写法惯例, 与 FakeLink `copyLineUri` 输出一致, 带上无害)、**必带 `view-mode=source`**;禁 `offset`(有 offset 会忽略 line)。**⚠️ 本机未装 Advanced URI, FakeLink 的 handler 只解析 `filepath` + `line`, `column` 属纯透传参数**——早期"不带 column 会算成 `NaN` 致跳转失效"是**误归因**, 本机无法复现, 别按它去查插件源码;协议事实见 `shared/citation-link-aliases.md`「Line links」节。
5. 发完 **sleep 6 秒** 再结束(`Processed URI` 是**异步日志**,无 sleep 会来不及回显;最终**以用户确认光标为准**,cursor 不落盘无法从文件侧验证)。**sleep 时长全文统一取 5-6 秒**——第 6 条"读判据前必先 sleep"是同一件事,不设两套数字。
6. **偶发静默失败可重发**:同格式 URI 曾实测一次免沙箱发送无任何反应,4 分钟后原样重发即成功——属瞬态丢包而非格式错误。判据(不打扰用户时自证成功)=Obsidian 窗口标题切换为新文件名 / `workspace.json` 里出现目标文件 leaf(激活文件在 leaf 的 `n.state.state.file`,两层 state);文件**未打开时应新建标签**(插件 `jumpOpenInNewTab: true`),标签数 +1 也是成功信号。
   - ⚠️ **读判据前必须先 sleep ≥5 秒**(2026-09-08 教训):`workspace.json` 由 Obsidian **异步落盘**,发完立刻读会读到上一次的旧状态 → 误判"没打开" → 触发本不需要的重发(而重发又要求间隔 ≥5 秒,反而更容易撞车)。正确动作:发 → sleep 5-6 秒 → 再读 leaf / 看窗口标题;仍以**用户确认光标**为最终判据。
   - **丢包定位(2026-09-05)**:发生在 **Obsidian 主程序的外部 URI 转发握手**(Windows 拉起新 Obsidian.exe 进程 → 第二实例把 URI 转发给主实例的 IPC 环节),**与 FakeLink 插件无关**——URI 压根没进插件 handler(证据:丢包时连标签都不建、无任何报错)。插件 API 无法增强该层,不用改插件。
   - **避免短时间连发多条**(每条都会拉起一个新进程做转发,握手易撞车):连跳多条时**逐条发、间隔 ≥5 秒**;单发失败原样重发一次即成功。
   - **"整批 URI 全无反应"的排查顺序(2026-09-10 实战定型:先试 Obsidian.exe 直调,再查 `app.json` 的 `uriCallbacks`,最后怀疑丢包)**——三者症状极像(都是静默无反应),但根因层不同,别一上来就重发:
     0. **零号判据 = 换 Obsidian.exe 直调通路**。`subprocess.run([r"<ObsidianInstallDir>\Obsidian.exe", uri])` 若回显 `Processed URI`，说明 URI 已送达 Obsidian，问题在插件侧或聚焦；若**连它也不回显**，才往下查系统层。（2026-09-10 第二轮实测：`os.startfile`/`ShellExecuteW` 静默但 Obsidian.exe 直调成功 → 属系统协议关联层失效，与 `uriCallbacks` 无关，别再改 app.json。）
     1. **第二判据 = 有没有新 Obsidian.exe 进程被拉起**。丢包发生在"转发握手",**一定会**瞬起一个新进程;若 `tasklist` 前后 PID 集合完全不变(no new / no gone),说明 URI 连 ShellExecute 之后的"拉起新实例"都没发生 → **不是丢包**。
     2. 此时查 `<vault>\.obsidian\app.json` 的 **`uriCallbacks`**。它为 **`false`** 时 Obsidian **完全忽略外部 `obsidian://` 链接**(不转发、不报错、不建标签,进程零变化)。修法:改成 `true`(该文件是 JSON,`Edit` 工具直接改即可,改完用 Python `json.load` 校验)。**这是 2026-09-10 上午「连续三发全无反应」的真实根因**,此前 skill 未收录。
        - 写回时机:Obsidian 只在自身退出/改设置时重写该文件;如发现被改回 `false`,提醒用户在 Obsidian 里正常退出重进或检查设置项。
        - 注意 `uriCallbacks` 与"该协议有无注册"无关:注册表 `HKCU\Software\Classes\obsidian\shell\open\command` 正常、`.obsidian\plugins\` 下无 `obsidian-advanced-uri`、FakeLink `jumpEnabled: true`,**这四项全正常时仍可能因 `uriCallbacks:false` 全盘失效**。排查顺序:进程 → `uriCallbacks` → 注册表 → 插件冲突 → 丢包重发。
     3. 顺带核实的两项(与本次无关,但属常备检查):注册表 `obsidian` 协议指向 `"<ObsidianInstallDir>\Obsidian.exe" "%1"`;`.obsidian\community-plugins.json` 含 `fakelink` 且无 Advanced URI。
   - **"这整个问题页面都在冲刺班里找"类措辞 = 限定搜索根目录**:(2026-09-10)用户嫌跨目录命中杂时,会把搜索范围收到点名文件夹;本工作区高频为 `<vault>\2026上数学教资\冲刺班`。收到后**只在该目录内 Grep**,文字列表也只列该目录内的命中。

## 🔒 收到行链接时的解读纪律（2026-09-10 广哥定，最高优先级）

广哥在聊天里发 `obsidian://adv-uri?...&line=N`（或 `[N](obsidian://...)`）行链接时，**唯一含义是"看这篇的这行"**，作用等于他手打文件名 + 行号省打字。
- **不解读为**"这行有错 / 需要检查 / 需要讲解 / 需要溯源 / 需要改写"；
- **不发散**去排查该行所属的章节、同名 PDF/SRT、前后邻近条目；
- **附了明确问句**时按问句办（问句本身才是任务）；**未附问句**时**只确认落点，等他的下一步指令，什么都不做**。
这条用来防止"见链接就自动开一整套溯源分析"的误处理。

## 🔒 回答引用一律用 obsidian:// 链接（2026-09-23 广哥扩定，取代 2026-09-11 只提行链接的旧版）

- **🔴 形态第 0 判据：必须写成 markdown 链接，禁裸 URI（2026-10-21 广哥当场退回"你写的链接我不能点"后定，最优先）**：聊天回复里每一条都必须长成 `[显示文字](obsidian://adv-uri?…)` —— **有方括号、有圆括号包壳**。**光秃秃的 `obsidian://adv-uri?…` 不算链接**（客户端不渲染成可点元素，点了没反应），百分号编码再正确也等于零分。交付前扫一遍：凡 `obsidian://` 前面紧邻的不是 `](`、或整串结尾不是 `)`，一律判不合格、重写。
- **🔴 路径存在性判据（第 0.5 判据，2026-10-21 同日第二次退回后补，与形态并列最优先）**：形态对、编码对，**路径错了照样点不动、而且零报错**。判据 = `<vault>` 下能否 stat 到该 rel；本机 vault 根是 `<vault>`，`2026上数学教资` 只是子目录。⇒ **交卷前第三问**：`gaicuo_link.py` 的 `FILE=` 行有没有「已自动补全」/`ERROR`/`ambiguous`？有就是路径没按规则写。写法上直接给绝对路径最省事（脚本剥前缀）。详见「本机环境事实」第 3 条的路径存在性闸。
- **⚠️ 本 skill 与 gaicuo 旧文里的"裸写"＝"外面不套反引号 / 不套 `$…$` / 不加代码围栏"，绝不等于"裸 URI"（2026-10-21 归因）**：把"裸写"误读成"只写 URI"正是当日链接点不动的真实根因；见词即按此解，别再退回纯 URI。
- **适用范围（2026-09-28 广哥定，修"经常不写链接"根因）**：本节是**回复格式规则**，适用于**一切聊天回答**，**不依赖**本 skill 的"搜索/打开"流程被触发——skill 只在"打开/搜索"类请求时才被加载，答疑中引用库内容时它往往不在场。四类场景**必写**链接（漏写=违规，不是可选项）：
    1. 答疑中引用库内原文/知识点/口诀/落点；
    2. 检查/核对后汇报**查看了哪些位置**；
    3. 写入/修改后汇报**改了哪些地方**（逐处附链接）；
    4. 末尾「相关 vault 笔记」列表。
    5. **对象边界（2026-09-28 广哥定）**：链接对象只限 **vault 内可打开的笔记**；`.workbuddy/` 等点开头目录下的工作区内部文件（两层 MEMORY、每日日志）**一律不加链接**——Obsidian 不索引点开头目录，链接必然打不开，如实写文件路径即可。

凡回答里**引用了 vault 内内容**（某句原文、某个知识点、某个口诀、某个落点、某篇笔记），无论落在哪种情形（查找 / 默认 / 全量），一律写成**可点的 obsidian:// markdown 链接**，**显示文字默认用简单别名（行号数字 / `标题` / `文章`）；若想表达链接大致内容，可自行改成想表达的文字（仍可点），不写裸路径、不写纯文本出处**。（本自定义改名规则**仅限聊天回答**；写进 .md 仍按 `shared/citation-link-aliases.md`「Line links」节显示行号，不自定义改名。）

- **三种形态**（同一条 URI 模板，只改 `line=` 与显示文字）：
  - 精确定位某行 → 显示**行号数字**：`[223](obsidian://adv-uri?vault=<vault-id>&filepath=<编码相对路径>&line=223&column=1&openmode=true&view-mode=source)`
  - 指向某标题 → `line=` 取该**标题所在行**，显示文字写 **`标题`**
    - （本三态是**聊天引用**的唯一真源；写进 .md 的行链接形态与"显示行号、禁占位符标题"那套口径见 `shared/citation-link-aliases.md`「Line links」节。两处场景不同、不构成冲突，勿互相套用。）
  - 指向整篇 → `line=1`，显示文字写 **`文章`**
- **媒体引用例外**：pdf 页 / 视频时间点**保持 wikilink** `[[x.pdf#page=N|pdf]]` / `[[x.mp4#t=N|视频]]`——FakeLink 的 `adv-uri` handler 只解析 `filepath`+`line`，带不了 `page=`/`t=`，硬转 obsidian:// 会丢页码/时间点。
- **取消纯文本出处（2026-09-23 广哥原话）**："以后回答的时候，在引用我库里的文章时，都写成链接的形式……以前我的规则里会让你写出处，现在既然能直接从你这里跳转到 ob，以后就直接写链接就行了。" ⇒ **不再出现"裸 vault 路径 + 文字行号"**（如 `<vault>/…/xxx.md（第N行）`）这种写法。
- **末尾「相关 vault 笔记」列表同此口径**：条目仍可写 `《文件名》第N行 — 一句话简述`，但**行号必须是链接**、且**不写"（路径：…）"**。
- **依据（用户原话，2026-09-11）**："这个链接可以跳转到 ob 行，以后你能都用这个逻辑来吗，如果回答的内容在 ob 有对应的话"（确认可点、可跳）。**2026-08-28 那条"聊天回复绝不给 obsidian:// 链接"的禁令已作废**，别按它退回"给序号→用户说打开第N条"的老流程。
- **内嵌链接 ≠ 打开文件**：链接只交给用户自己点（点开即跳，见下节「点击行为」）；查找模式依旧**不主动开文件**，默认模式的开文件逻辑也不受影响。要"打开"仍是本 skill「AI 直跳唯一流程」的事。
- 落点在**同一文件多处**时，每条各附自己的链接；跨文件同理。
- vault 里**没有对应落点**时（纯知识讲解、纯推理、无笔记可指）**不硬塞链接**。
- 生成方式：相对路径一律 `urllib.parse.quote(rel, safe='')` 编码（**勿手工编码中文**；PowerShell 直接写百分号编码会被安全 hook 拦，改由 Python 生成或写临时文件再读），URI 模板与下节完全一致。
    - ⚠️ **禁止复用/改写上一轮回复里的旧串（2026-10-05 广哥当场抓出的漏字事故）**：每个链接都必须**当场用 Python `quote()` 重新生成**，不许照抄历史串、不许凭记忆改字。事故原型：手写时把「最后一遍**疯狂刷题**科目二」的 `刷` 整字漏掉（串长 250 vs 正确 259），FakeLink 找不到文件 ⇒ **链接静默不跳、零报错**，只能靠自查发现。
    - 30 秒自查：`len(手写串)` vs `len(quote(真路径))` 不等即有漏字；或 `unquote(手写串)` 与真路径逐字 diff（本例 unquote 出「疯狂题」一眼看出少字）。
- **⚠️ 链接原样输出, 禁任何包裹符号(2026-09-26 广哥连续两次纠错; 措辞澄清 2026-10-21——此处"裸写"指"不套反引号 / 不套 `$…$` / 不加围栏", **不是**"裸 URI", markdown 包壳 `[]()` 必须写, 见本节第 0 判据)**: 聊天回复里的 `[N](obsidian://…)` 必须**原样输出**, 不得套任何定界符——**不得**用反引号包成代码块、**不得**用 `$…$` 包成行内公式; 两种包法都会让链接**失去可点性**(广哥原话: "为什么要带代码符号? 这样写的链接是有问题的")。
    - `$…$` 是**数学公式专用**(用户统一的聊天格式规则), 链接不是公式, 永远不套。
    - wikilink 六词形态 `[[note#heading|标题]]` 是**写进文件**用的, 聊天回复里**不要出现**——聊天一律走本节的三态 obsidian:// 链接。
    - **⚠️ 列表项本身也不要用 ``` 三反引号包裹(2026-09-26 二次纠错, 同一个坑)**: 把 `1. 内容…[361](obsidian://…)` 整条写进 ``` ``` ``` 围栏/行内代码, 整段会被渲染成代码块, 里面的链接同样**不可点**。聊天回复就是**纯有序列表 + `[N](obsidian://…)` 形态链接**, 不要给列表项加任何栅栏; **也不要留裸 URI**(见本节第 0 判据)。
- 样板（广哥确认可点可跳）：正文写"点此跳 [141](obsidian://adv-uri?...)"，单击即在 OB 跳到该行。

## 行号链接（写进笔记正文 / 内嵌聊天回复，交用户点击）

- 格式：`[N](obsidian://adv-uri?vault=<vault-id>&filepath=<编码相对路径>&line=N&column=1&openmode=true&view-mode=source)` —— **必须是这套带 `[]()` 的完整 markdown 链接**；只贴 `obsidian://…` 裸 URI 等于没给链接（2026-10-21）。
- **显示文字**：纯行链接（精确落到某行）显示**目标行号数字本身**（如 `[249]`）；**指向标题 / 整篇**时写别名 **`标题` / `文章`**（2026-09-23 扩定；**聊天**一律按本三态。**写进 .md 时**：行链接仍按 `shared/citation-link-aliases.md`「Line links」节显示行号，本句的 `标题`/`文章` 别名只指标题/整篇链接）。勿写描述文字或单字"行"。
- **`vault=` 的值不影响跳转**（2026-09-06 读 FakeLink 源码证实）：插件 handler 只取 `filepath` 与 `line`，**完全不读 `vault`**，所以 `vault=<vault-id>`（vault 名）与 `vault=<vault-id>`（vault ID）**都能打开**。模板统一写 ID，但用户手写/插件生成的 `vault=<vault-id>` **不要当成错误去纠正**。
    - 依据 `<vault>\.obsidian\plugins\fakelink\main.js`：`registerObsidianProtocolHandler("adv-uri", data => { const filepath = data["filepath"]||""; const line = parseInt(data["line"]||"",10); ... jumpToLine(filepath,line) })`。
    - 生成端 `copyLineUri()`：`vaultId = app.vault.getId?.() ?? app.vault.getName()`，剪贴板写 `[${line}](${uri})`——这就是广哥在聊天里贴的 `[24](obsidian://adv-uri?...)` 的来源（FakeLink 命令 "Copy line link (adv-uri)"）。
    - 前提：Advanced URI 插件**未启用**时 FakeLink 才注册 adv-uri 协议（源码内有此判断；本机 `.obsidian/plugins/` 下无 obsidian-advanced-uri）。
- 点击行为：目标文件**未打开**时，第一次点只打开、**再点一次**才跳（单链接无法内置延时）；已打开则点击即跳。**⚠️ 本条只描述「用户手点链接」这条通路**：AI 侧直跳走上面「🔒 全局标准」的 `jump_activate.py`(发一次即开+跳), 两条通路不同、结论不同, 不要互相套用。权威规则另见 `shared/citation-link-aliases.md`「Line links」节。

## 三种情形（按用户措辞分流）

| 用户说法 | 情形 | 是否打开文件 | 相关文件如何呈现 |
|---|---|---|---|
| 只提问/查内容（**不含"打开"**） | 查找模式 | 一个都不打开 | 文字列表（可点 obsidian:// 链接+简述） |
| "打开 XXX"（含"打开"、不含"所有"） | 默认模式 | 自动开最相关 1 篇并跳行 | 文字列表 |
| "打开所有 XXX"（含"所有"/"全部"） | 全量模式 | 自动开最相关 1 篇并跳行 | obsidianjump:// HTML 链接页全列 |

1. 三种情形都**先搜索、都精确到行**；文字列表每条必须带行号**并附可点链接**（见上节「回答引用一律用 obsidian:// 链接」）。
2. 文字列表格式：`N. 《文件名》第N行 — 一句话简述` + 该条内嵌 `[行号](obsidian://adv-uri?...)` 链接；**不写"（路径：…）"**（2026-09-23 起取消纯文本出处，见上节「回答引用一律用 obsidian:// 链接」）。
3. 查找/默认模式不生成文件、不占预览面板；只有全量模式才生成 HTML 链接页。
4. 搜索用 Grep（`output_mode=content -n` 拿行号），可多关键词并行。

## 落点判据（2026-09-08 实测补充）

- **用户说「第 N 行」却没点名文件时，一律指当前激活文件的第 N 行**，不要沿用上一轮提过的文件（2026-09-08 教训：默认沿用上一轮提过的文件会插错地方）。
  激活文件读法：`<vault>\.obsidian\workspace.json` 里 `active` 给 leaf id，再取该 leaf 的 `n.state.state.file`（**两层 state**；只读 `n.state.file` 恒为 undefined）。"当前文件夹" = 该激活文件所在目录，不必再问用户当前打开的是哪个文件。
- **同一文件开了多个标签时，单发带 `line` 的 URI 落在 FakeLink 聚焦的那个标签**（FakeLink 不认 `close`，关标签需用户手动关）。

## HTML 链接页（仅全量模式 / 浏览器点击场景）

用 `obsidianjump://` 自定义协议（HKCU 注册、按需拉起 pythonw handler、无常驻进程）。链接 `href` 直接写协议（不用 `href="#"` + onclick）。

```
obsidianjump://jump?p=<urllib.parse.quote(rel, safe="")>&line=<N>
<a href="obsidianjump://jump?p=...&line=5">第5行</a>
```

- **`p` 必须是 vault 根起的完整相对路径（含全部嵌套前缀）**：生成后必做校验 `os.path.exists(os.path.join(r"<vault>", *rel.split("/")))` 必须 True，否则 handler 存在性检查会 NOT EXIST 静默跳过、按钮无反应。
- handler 脚本 `<vault>\临时\obsidian_jump_handler.py`（pythonw 执行，日志 `<vault>\临时\obsidian_jump.log`）。
- **无黑框三条**：① 注册表 command 用 `pythonw.exe`（不是 python.exe）；② 脚本内禁止 `subprocess` 调 powershell/cmd（console 子系统会闪黑框）；③ 用 `time.sleep` + `os.startfile`（ShellExecuteW，零子进程零控制台）。pythonw 下禁止 print，异常写日志。
  **⚠️ 适用范围限定（2026-09-11 第 15 次审查）**：本条的 `os.startfile` 只描述 `obsidianjump://` **handler 脚本内部**的发链方式，
  **不是**「AI 直跳」的通路——AI 侧跳行一律按上面「🔒 全局标准」走 `jump_activate.py`。`os.startfile` / `ShellExecuteW` 对本机
  `obsidian://` 实测**完全静默**（见第 1/2 条）；若 handler 也出现无反应，**改用 `Obsidian.exe` 直调**
  （`subprocess.run([r"<ObsidianInstallDir>\Obsidian.exe", uri])`，有 `Processed URI` 收据），不要反复重发 `os.startfile`。

## 行号漂移同步

行号链接的固有弱点是**源笔记一编辑就漂移**。清单类产物（HTML/MD）**改生成脚本的数据再重跑，不要手工改产物**：重定位行号（按关键短语找新行号）→ 批量回写脚本数据 → 重跑 → 正则抽产物链接解码逐条核对落点。
