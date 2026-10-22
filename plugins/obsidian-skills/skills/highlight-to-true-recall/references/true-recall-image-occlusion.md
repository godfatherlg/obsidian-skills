# True Recall 图片蒙板（Image Occlusion）能力边界

> 来源：`<vault>\.obsidian\plugins\true-recall\main.js`（本机 v2.4.2，与官方 release 逐字节一致），prompt 为逐字原文。
> 结论一句话：**插件不让 AI 做蒙板，AI 只做「找区域」，蒙板由插件前端按矢量数据画。**
> 2026-09-14 补：**编组、揭示变绿、回答页跳转**三件事的源码级结论已并入本文（3.3 节、§七、§八）。
> 引用体例：指向本文中文节（`## 一、`~`## 十一、`）写 `§十一.5`、`§七`；指向阿拉伯子节（`### 3.x`）写 `3.x 节`。**别用「§」加阿拉伯数字那种写法** —— 那是全库历史残留形态，`rules-consistency-audit` 的 A 类会把它当残留引用报出来。

## 一、这个功能长什么样

- 卡型 id：`builtin-image-occlusion`（映射常量 `en`），是内置卡型之一（另四个：`builtin-basic` / `builtin-basic-reversed` / `builtin-cloze` / `builtin-note-review`）。
- **卡型字段只有两个：`["Image","Regions"]`**（`note_types.fields_json` 实测）。模板 `qfmt:"{{Image}}"`、`afmt:"{{Image}}{{Regions}}"`——但**复习时的渲染不走模板**，见 §八。
- **Pro 门控是「分层」的，别一句话概括**（2026-09-14 源码复核，此前口径已修正）：
  - **入口层 = 要 proKey**：命令面板 `create-image-occlusion-card` 的 `checkCallback: e => An(settings,"image-occlusion") ? (...) : false`——无 proKey 时**命令根本不出现**；设置里 "Creation tools" 开关 `disabled:!jp(t,"image-occlusion","pro")`，且无 proKey 时描述直接显示 **`Image Occlusion creation tools are included with True Recall Pro.`**
  - **编辑器内核层 = 只查桌面端，不查 proKey**：`openImageOcclusionEditor()` 的守卫是 `jn.canEditImageOcclusion()`，而它是 `ao()` = `!Platform.isMobile`；卡片操作菜单里的 `Add image occlusion` 同样只判 `jn.canEditImageOcclusion()`。**即：画矩形/椭圆（R / E / Delete 快捷键）这套 UI 本身没有 proKey 检查。**
  - **已实测成立**（2026-09-14）：无 proKey 时**走卡片菜单的 `Add image occlusion` 进编辑器，纯手工画框、存卡全程可用**；用户据此成功造出 3 条 note（`created_via="manual"`）。
  - **AI 检测 = 要 proKey**：`AI detect regions` 按钮的 `hasAIKey` 实参是 `Kr`，而 `Kr = !!settings.proKey`——**变量名叫 hasAIKey 但实际就是 proKey**（名字有误导性），按钮 `disabled:!hasImage||aiLoading||!hasAIKey`。
  - **`jp("image-occlusion")` 里的 `!!proKey` 只认真 proKey，BYOK 不算**（本机 `aiTier="byok"` 是 `wa()` 由 `providerType:"openrouter"` + 有 openRouterApiKey 自动算出的档）。同理 `type-in-mode`（打字模式）走同一道判据。
  - 工具栏设置里 `imageToolbarButtons` 的 `{"id":"io","enabled":true}` 只管**按钮显不显示**，不是功能解锁。
  - **实操结论**：无 proKey 时命令/工具栏主入口被关，**未走 proKey 的口子有两个** —— ① 卡片操作菜单里的 `Add image occlusion`（复习界面/卡片面板的卡 ⋮ 或右键菜单）；② 本机自建的「制作图片蒙板」命令 / 右键项（脚本 `truerecall制作蒙板.js`，见下面「命令入口与右键菜单归属」末条）。
- 仅桌面：`"Image occlusion editor is available on desktop only."`
- 入口：编辑器工具栏 `io` 按钮 → `openImageOcclusionEditor({mode:"add"|"edit", sourceUid, noteId})`，弹窗标题 `Create image occlusion` / `Edit image occlusion`，宽 1120px。
- **命令入口与右键菜单归属（2026-09-14 排查）**：
  - 命令面板里的 `True Recall: Create image occlusion card`（id `create-image-occlusion-card`）是 **`checkCallback`**，判定只有一条 `An(settings,"image-occlusion")`（**不看上下文**）；点下去执行 `openImageOcclusionEditorForActiveNote()` → **作用于当前活动笔记**（打开编辑器让你选图），**不是**「对右键的那张图直接建卡」。
  - 想把它放进右键菜单（配 Commander 用时）：Commander 的 `editorMenu` 与 `fileMenu` 是**两套独立事件**（源码 `cmdr/main.js`：`workspace.on("editor-menu")` / `workspace.on("file-menu")`）——**编辑器正文（含嵌入图片）右键 = Editor menu；左侧文件列表右键文件/文件夹 = File menu**。加在 File menu 里、去正文右键图片 → 永远看不到（2026-09-14 广哥踩过：同一条加了 3 次、其中 2 条 id/name 完全重复，而 Commander 不去重）。配置文件里对应 `editorMenu` / `fileMenu` 两个数组。
  - **快速判位（比翻界面快）**：直接数 `<vault>\.obsidian\plugins\cmdr\data.json` 的 `editorMenu` / `fileMenu` 两个数组长度，就知道加在哪一套。2026-09-14 实测 = `fileMenu` 3 条（2 条 id+name 全同的重复 + 1 条改名为「制作图片蒙板」）、`editorMenu` 空。
  - **界面上的「File menu」在哪（2026-09-14 广哥问过）**：Commander 设置页不是纵向滚动的区块，而是**一排标签页**：`General / Editor Menu / File Menu / Left Ribbon / Right Ribbon / Titlebar / Statusbar / Page Header / Explorer / Toolbar / Macros`，中文界面依次是「通用 / **编辑器菜单** / **文件菜单** / 左侧边栏 / 右侧边栏 / 标题栏 / 状态栏 / 页头 / 探索器 / 工具栏 / 宏」。i18n 原文见 `cmdr/main.js` @14309（en）/ @44252（zh）。另外 `showAddCommand:true` 时**每个菜单里都会出现一个 `Add command` 项**，从哪个菜单点它就加到哪一套，所以「在正文里点 Add command 却进了 File menu」不会发生，反倒容易误以为加对了。
  - **`fileMenu` 对命令类型有额外过滤**（`Ae.applyFileMenuCommands`）：`editorCallback` 型只在 `ctx.view instanceof MarkdownView` 时才添加，`editorCheckCallback` 型遇非 MarkdownView 直接 `continue`；**普通 `checkCallback` 型（TR 这条就是）无约束，进了 File menu 就一直显示**。`editorMenu` 侧（`Te.applyEditorMenuCommands`）则一律先过 `checkCallback(!0)`。
  - **⚠️ 没有 proKey 时，这条命令放进任何菜单都不会出现（2026-09-14 定案，广哥踩坑）**：`checkCallback` = `An(settings,"image-occlusion")`，而 `An(t,e)` → `jp(t,e)` 里 `case "image-occlusion": case "type-in-mode": return !!t.proKey`（**BYOK 不算**，只有 `ai-generation` / `card-polish` / `ai-assistant` 才走 `as()`）。Commander 两侧都写的是 `if(m && !(m.checkCallback && !m.checkCallback(!0)))` → **checkCallback 返回 false 就直接跳过、不添加**。所以「加错菜单」只是第二层原因，**第一层是命令本身没解锁**。本机判据：`true-recall/data.json` 顶层**无 `proKey` 字段**、`aiTier:"byok"` → 恒不显示。**自检**：`Ctrl+P` 搜 `Create image occlusion`，搜不到即被 proKey 挡住（搜得到才是 Commander 没重载）。
  - **但编辑器内核不看 proKey**：`plugin.openImageOcclusionEditorForActiveNote()` → `openImageOcclusionEditor({mode:"add"})` 的守卫只有 `jn.canEditImageOcclusion()`（= `!Platform.isMobile`，`true-recall/main.js` @3632450）；卡片操作菜单里的 `Add image occlusion` 用的是同一个守卫（@591441）。→ **想要「一键建蒙板/图片右键入口」可以自写脚本直调这两个方法，不必绕命令入口。**
  - **参照物（可自检）**：`AI Image OCR` 的 `extract-text-from-embedded-image` 是 **`editorCallback`** 型命令 —— 这类命令由 Obsidian 自动挂到 **Editor menu**，所以正文右键图片能直接看到；它内部用 `editor.getSelection()` 匹配 `![[...]]` / `![](...)`，并用 `findRelevantImageEmbed(editor)` 找目标图。**「图片右键型命令」的标准写法就是这个。**
  - **✅ 已落地的解法（2026-09-14，广哥要「命令面板项 + 右键图片能调用」）**：脚本 `<vault>\Scripts\truerecall制作蒙板.js`，QuickAdd 宏 **`TR制作蒙板`**（`runOnStartup:true`）。三件事：
    - ① `app.commands.addCommand({id:"tr-io-tools:create-image-occlusion-card", name:"制作图片蒙板", icon:"image", callback})` → **命令面板随时可搜到**（绕开 proKey 门控）。调用的是插件自己的 `openImageOcclusionEditorForActiveNote()`，与卡片菜单那条路用的是同一个编辑器 —— **没解锁任何本来做不到的能力**（它在插件源码里唯一的门槛就是 `jn.canEditImageOcclusion()` = 非移动端）。**`.5` 起：解析到图片路径时改调 `openImageOcclusionEditor({mode:"add",imagePath,…})`，只有解析不到才回落到它**（见下面第 ③ 条）。
    - ② **两条右键通道都要挂**（只挂一条就会出现「光标在那行上右键有、直接点图片右键没有」）：
      - `workspace.on("editor-menu")` 追加同名菜单项；**默认不挑位置**（`ONLY_ON_IMAGE = false`），跟 Obsidian 对 `editorCallback` 型命令的默认行为一致（例：AI Image OCR 那条就是任意位置右键都在）。
      - `workspace.on("file-menu")` 追加同名菜单项，判据 = 目标 `file` 扩展名是图片 **且** `source === "link-context-menu"`（或 source 缺省）。**右键「渲染出来的图片」走的就是这条。**
      - **源码依据（`obsidian.asar` 实测，2026-09-14）**：编辑器右键在 `MarkdownView.onContextMenu`（@3115846）里按**鼠标位置的 token** 分流 —— `k = editor.getClickableTokenAt(posAtMouse(e))`；`k.type === "internal-link"` 时调 `workspace.handleLinkContextMenu(menu, k.text, path)`，**只有走到最后才** `workspace.trigger("editor-menu", …)`。而 `handleLinkContextMenu`（@3425132）在目标文件存在时执行 `this.trigger("file-menu", menu, file, "link-context-menu", leaf)`。**⇒ 右键图片只触发 file-menu，永不触发 editor-menu**；右键该行文本/源码才走 editor-menu。
      - `source` 取值可用来分辨场景（同一 asar 内多处调用点）：文件列表右键 = `"file-explorer-context-menu"`、画布 = `"canvas-context-menu"`、链接/嵌入 = `"link-context-menu"`。所以 file-menu 里判 `source` 不会误伤「左侧文件列表右键同一张图片」。
      - 边界：**未解析的嵌入（`file === null`）不会触发 file-menu**（`handleLinkContextMenu` 走 else 分支只给「创建文件」）→ 那时没有我们的菜单项。
    - ③ **打开时自动带图**（`2026-09-14.5` 落地；广哥原话："打开后直接把这个图片加入啊…我主要是不想每次都去选中整个 `![[…]]`"）：光开编辑器不够，必须把图片路径一起喂进去，才是原生「点图片 → IO 按钮」的完整效果 —— 原生 `qre()`（@3120358）就是这条链路：
      - `metadataCache.getFirstLinkpathDest(raw, activeFile.path)` 把 linkpath 解析成真实 vault 路径（拿不到就用原值）；
      - 确保活动笔记有 `sourceNoteUid`：`flashcardManager.getFrontmatterService().getSourceNoteUid(path)`，无则 `generateUid()` + `setSourceNoteUid()`（**会写 frontmatter**，与原生行为一致）；
      - `openImageOcclusionEditor({ mode:"add", imagePath, sourceUid })` —— **`imagePath` 就是「图已经在里面」的开关**，不传就只开个空编辑器。
      - 路径来源四条，优先级从高到低：① `file-menu` 回调的 `file.path`（**TFile 与字符串都吃**，统一走 `filePathOf()`）② 右键那一刻就解析好、存进 `ctx.path`（等价原生 `S6e()` 的 `.internal-embed` 分支：读 `src` 属性，`decodeURIComponent` + 切掉 `#`/`?`/`|` 后缀）③ 点击时对 `ctx.el` 现场再解析一次（`el.isConnected` 为真才用）④ editor 选区/光标行正则（`matchPath()`，wiki 嵌入优先、其次 `![]()`）。
      - 四条全落空 → 退回 `openImageOcclusionEditorForActiveNote()`（空白编辑器，即 `.4` 的旧行为），**不会因为解析失败而报错**。
      - **坑：渲染出来的 `<img src>` 是 `app://local/...`，不是 vault 路径，不能拿它去 `getFirstLinkpathDest`**。所以必须走 `.internal-embed` 元素的 `src` **属性**，或从行文本正则抠。`cleanPath()` 里专门有一条把 `^[a-z]+://` 的绝对 URL 剔掉，防止误取。
      - **调试口**：`globalThis.__trIoMakeCard._test` 暴露 `matchPath / pathFromEl / pathFromEditor / cleanPath / pickPath / isImageTarget / getCtx / setCtx`。改判据时先在假 Obsidian 环境跑一遍 harness，别直接上线试（`setCtx` 用来模拟"右键时 DOM 里有什么"）。
    - **为什么默认不挑位置（2026-09-14 首次实测教训）**：v1 用「右键目标是不是图片」当判据，上线后广哥反馈"没看到"，日志 `editor-menu: fresh=true isImage=false → 跳过（不是图片）` —— 他自认为点在图上，但 DOM 目标判定为假。**靠 DOM 目标猜图片不可靠**（命中点可能是行内 padding、widget buffer、包裹层等）。v2 起 `ONLY_ON_IMAGE` 开关可三路判定：`右键目标像图片` ∥ `光标所在行含图片嵌入` ∥ `选区含图片嵌入`；要收紧时把它改 `true`。
    - **v2 起记录右键目标 DOM 特征**（`fp=TAG.class>祖先…`）与三路判定结果（`img=/onImgLine=/show=`），日志里直接能读到"当时点的是什么"。
    - **v2 起装完自检**：`addCommand` 后用 `commands.findCommand(id)` 复核，日志写「自检：在注册表／不在注册表」，不在就在 Notice 里报警。
    - **v1 有个转义 bug 已修**：`new RegExp("\\\\.(" …)`（文件里 4 个反斜杠 → JS 串 `\\.` → 正则要求"字面反斜杠"）永远匹配不上普通路径；v3 改成字面量 `/\.(png|jpe?g|…)$/i`（`IMG_PATH_RE`），并加了 `app://local/` + 中文 percent-encode 的用例。
    - **Obsidian 侧三条源码事实（`obsidian.asar` 实测，解释了一切）**：
      - `Commands.addCommand(cmd)`（@3589190）**没有任何 owner / id 前缀校验**，直接 `this.commands[cmd.id]=cmd`；`editorCallback`/`editorCheckCallback` 会被自动包装成 `checkCallback` 并另存一份 `editorCommands[id]`。
      - `Commands.listCommands()`（@3590237）= `Object.values(this.commands).filter(c => !c.checkCallback ? true : c.checkCallback(!0))` —— **这就是 TR 那条命令凭空消失的机制**（它有 `checkCallback` 且返回 false → 被滤掉）；Commander 与命令面板同源，所以两边一致。
      - 命令面板 `getCommands()`（@3886066）= `listCommands()` 排序，**没有前缀过滤** → 外部 `addCommand` 的命令**一定**会出现在面板里（名字不打插件名前缀，原样「制作图片蒙板」）。
      - 判据用法：日志里出现 `run(palette)` = 他确实在面板里点到了；没有 = 没找到/没试，别急着怪注册。
      - **本机 Obsidian 源码位置（想复核上面这些结论时用）**：`<ObsidianInstallDir>\resources\obsidian.asar`（24MB，UTF-8 纯文本，可直接字符串检索）；同目录 `app.asar` 只有 465KB、是壳，别搜错。
    - 右键目标怎么记的：在 `document` 上**捕获阶段**监听 `contextmenu` 记标记 —— 捕获一定早于 Obsidian 挂在 CM dom 上的处理（冒泡），所以 `editor-menu` 触发时标记已写好。判"像图片" = `target.tagName==="IMG"`，或 `closest(".image-embed,.internal-embed,.media-embed,img")` 命中的元素是 `<img>` / 带 `image-embed` 类 / `src` 匹配 `IMG_PATH_RE`（非图片嵌入如 pdf 不命中）。标记 **>1.5s 视为过期**（`ONLY_ON_IMAGE=true` 时才影响判定；默认 `false` 时恒显示）。
    - **刻意不用 `editorCheckCallback`**：那样会被 Obsidian **自动**挂进 Editor menu，与手写的项重复；而且光标不在图片行时命令面板里会变灰。用 `callback`（面板常驻）+ 手写 editor-menu（精确到图片）= 两边不打架。
    - **幂等/热更新**：`globalThis.__trIoMakeCard` 存本代句柄，重跑脚本先 `dispose()`（`removeCommand` + `offref`×2 + 摘 contextmenu）再装，**不叠加**。离线假 Obsidian 环境实测 **29/29 PASS**（harness: `~\.workbuddy\skills\highlight-to-true-recall\scripts\test_tr_io_cmd.js`，`node test_tr_io_cmd.js` 即可跑，可用 `TR_IO_SCRIPT` 环境变量换被测脚本；覆盖：六组 —— 纯函数路径解析（wiki/`|300`/`![]()`/`#锚`/percent-encode/`app://` 剔除/`.internal-embed[src]`/光标行）、file-menu 带图（TFile 与字符串两种 file、source 过滤、非图片过滤）、file 为空不误出、editor-menu 带图、命令面板无线索时退回空白入口、重跑后版本号与两条监听各只 1 个）。
    - **当前版本 `2026-09-14.5`**（改脚本务必 +1，日志首行会打印，用来判断"跑的是哪一版"；`.3` = 只有 editor-menu，`.4` = 补 file-menu 通道，`.5` = 打开时自动带图）。
    - 日志 `<vault>/.true-recall/tr-io-cmd.log`（追加式，记安装/触发/异常）。
    - **视图边界**：`editor-menu` 只在**编辑视图**（实时预览/源码）触发；阅读视图右键图片走的是 `handleLinkContextMenu` 一族（同 file-menu 通道），**理论上也能出现我们的项**（2026-09-14 未实测）。真要在阅读视图兜底，可自己 `new Menu()` 挂 contextmenu。
    - 原先加在 Commander `fileMenu` 的 3 条（2 重复 + 1 改名）**已于 2026-09-14 删除**，`fileMenu` 现为 `[]`；备份 `<vault>\.obsidian\plugins\_backup-20260914\cmdr-data-backup-20260914-1901.json`。
- 官方自述（`uee.info`）：
  - description：`Create flashcards by masking regions of images. Draw rectangles and ellipses over diagrams, maps, or any image to test visual recall.`
  - features：`Draw rectangular and elliptical occlusion regions` / `AI-powered automatic region detection` / `Multiple mask modes: hide one / hide all` / `Edit existing occlusion cards`
  - `tier:"pro"`

## 二、AI 在里面到底干什么（**只检测区域，不生成蒙板**）

点击 `AI detect regions`（`sparkles` 图标）→ `HX(vault, imagePath, settings, ..., settings.aiIODetectionPrompt)`。

### 1. 内置检测 prompt（原文，常量 `Mxe`）

```text
Detect the 2D bounding boxes of all key elements in this educational image that a student should memorize. This includes: labels, terms, annotations, named parts, definitions, formulas, important text, and distinct visual components.  For each detected element, return a JSON object with: - "box_2d": bounding box as [y_min, x_min, y_max, x_max] in 0-1000 scale - "label": brief description of the element  Return ONLY the JSON array.
```

### 2. 系统级附加约束（原文，常量 `Oxe`）

```text
Return bounding boxes as a JSON array with labels. Never return masks. Limit to 25 objects.
```

**`Never return masks` 是作者写死的**——AI 明确被禁止输出蒙板（图片/像素遮罩），只能输出矩形框坐标（0-1000 相对刻度）+ 文字标签，且最多 25 个对象。

### 3. 模型与图片输入

- 模型默认 `google/gemini-3.7-flash`（常量 `Nxe`，与出卡同款），走 Vision：读 vault 图片 binary → base64 → `image/png|jpeg|gif|webp|svg+xml`。
- 温度 0.5；Pro 档额外带 `call_context:"generation"`。
- 设置项 `aiIODetectionPrompt`（"AI detection prompt"，textarea，mono 字体）可覆盖内置 prompt，留空即用内置。

### 4. 检测结果的落地

```js
// 返回框 → 每个框分配递增 groupKey
let Ut = Number(RA(regions));
let list = detected.map(x => ({...x, groupKey: String(Ut++)}));
```

框转成归一化 `x/y/w/h`（`Wl()`：>1 的值先当百分数除以 100，再 clamp 到 0-1）。

## 三、蒙板数据本体（regions），这是"挖空"真正的实现

字段落在 note 的 `fields` 上（image-occlusion 卡的 note）：

- `Image`：图片引用字符串，`![[图片名]]` 或 `![alt](路径)` 都能被 `Ja()` 解析出路径。本机实例：`images/皮亚杰认知发展四阶段对比.png`（vault 相对路径，不带 `[[ ]]`）。
- `Regions`：JSON 字符串，`pa()` 解析。写入形态（`Om()`）：

```json
{"version":1,"maskMode":"solo","regions":[{"id":"io-0","x":0.1,"y":0.2,"w":0.3,"h":0.08,"groupKey":"0","shape":"rect","label":"..."}]}
```

- `x/y/w/h`：**归一化 0-1**（不是像素，不是 0-1000）。
- `shape`：`"rect"` 或 `"ellipse"`（`t2()` 兜底为 rect）。
- `maskMode`：`"solo"`（hide one，一个区域一张卡）或 `"all"`（hide all，同组一起遮）。
- `groupKey`：**决定有几张卡**——`Mm()` 取 groupKey 去重，**每个 groupKey = 一张卡**；同 groupKey 的多个区域属于同一张卡。
- 卡片数推导：`ace(note)` 返回 groupKey 列表 → `wd()` 按此生成 card 记录（`templateOrd` = groupKey）。

### 1. groupKey 是怎么被分配的（编组的底层）

```js
function RA(t){ let e = Mm(t); let r = e.length>0 ? Math.max(...e)+1 : 0; return String(r) }
```

**每次新画一个框，编辑器都调 `RA()` 取「当前最大 groupKey + 1」**，所以：

- 画 3 个框 = 3 个不同 groupKey = **3 张各自独立的卡**，不是「一个蒙板」；
- `maskMode:"all"`（hide all）只影响**同一 groupKey 内**多个框的联合揭示，跨 groupKey 无效。
- **推论（2026-09-14 广哥追问「不用 `%%` 就不会有多组了吧」时复核）：「多组」是插件默认产物，不是 `%%io:%%` 的产物** —— `RA()` 的调用点就一处，是 `YX()`（鼠标松手提交新框）里写死的 `groupKey: RA(t)`；AI detect 也递增。所以**「多个框合成一题」必须靠合并器**（现役只有守卫 `TR自动编组` 的 all 分支；旧的手动宏 `TR蒙板编组` 已于同日 22:46 退役），放弃 `%%` 不等于摆脱多组，详见 §十一.5 第 10 条。（补记：`%%` 支持本身已于同日 v3 从脚本删除，见 3.4 节。）

### 2. 编辑器 UI 里**没有编组入口**（源码枚举确认）

侧栏四块，逐个查过，没有任何 group / merge / ungroup 按钮：

1. `Image`（选图）；
2. `Tools`：`Select` · `Rectangle` · `Ellipse` · `AI detect`；
3. `Mask mode`：`Solo` · `All`；
4. `Regions` 列表：每行只显示 `#groupKey`，可选中、可删（**能看编号，但不能改编号**）+ Selected region 的 `X / Y / W / H` 数值框。

**2026-09-14 第二轮加硬证据（用户质疑「有编号就肯定能编组」，逐条证伪）**：

- `groupKey` 全库仅 **16 处**，其中**唯一**的 UI 处是区域项渲染：`title: \`Select region #${t.groupKey}\`` + `children:[d("span",{children:["#",t.groupKey]}), d("span",{children:t.shape})]` —— 纯展示文本。
- 区域项组件 `Gxe({region, selected, onSelect, onDelete})` 只有 `onSelect` 与 `trash-2`（删除）两个回调；列表容器 `iee({regions, selectedRegionId, onSelectRegion, onDeleteSelected})` 的 **`selectedRegionId` 是单个 id 而非数组** → **不支持多选**，"选中多个再合并"这条路从根上不存在。
- 编辑器整段（main.js @523000–@557000）内 `Merge` / `merge` / `Group` / `onContextMenu` / `onDrag` 命中 **0 次**；唯一一处 `draggable` 是 `<img draggable={!1}>`（关掉浏览器原生拖图），与 region 无关。
- **编辑器快捷键全集**：`V` Select、`R` Rectangle、`E` Ellipse、`Delete` 删除选中区域、`Space + drag` 平移画布。页面上的 kbd 提示只有一条 `Space + drag  pan`（`class:"true-recall-io-canvas-shortcuts"`、`title:"Editor shortcuts"`）。**没有任何编组快捷键。**
- `Solo` / `All` 两个按钮的 onClick 分别是 `a(xt=>({...xt,maskMode:"solo"}))` / `a(xt=>({...xt,maskMode:"all"}))` —— **只改 `maskMode` 一个字段，完全不触碰 `regions`**，所以切换模式不会重排 groupKey（库里实测亦印证：`maskMode:"all"` 的 note 仍可以是 `groupKey:["0","1"]`）。
- 插件设置 `data.json` 中无任何编组相关项。
- **官方说明核查（2026-09-14）**：GitHub README 全文只提一次 image occlusion（仅在隐私章节提"image-occlusion detection 需要配 AI provider"），**无操作说明**；`truerecall.app/docs`、`/plugins/image-occlusion/`、`/sitemap.xml` 均 404；检索无该站 IO 编组文档。→ **官方文档里不存在编组功能可查。**
- **推论（非文档原话）**：`groupKey` 存在是为兼容 Anki 的图片遮挡数据模型 —— manifest 明列 `Anki Compatible: Import .apkg decks`，而同类插件 LearnKit 的官方文档把 Groups 写得很直白：*"Each mask can have a group key. Masks with the same group key behave as one unit."* 即**数据结构必须能表达「多框一组」，但作者没给自己的编辑器做这个入口**。所以 `#0` `#1` 是**解释性**的（让你看清这个框归哪张卡），不是**操作性**的。
- **结论**：插件 UI 侧编组 = 不可能；唯一路径是改写 `Regions.groupKey`（3.3 节 的脚本，⛔ 该脚本已随 `TR蒙板编组`／`TR自动编组` 双双退役而不存在，**本条转为底层机制档案**）。写入 groupKey 的三个来源也全是「一框一新编号」：新画框 `qA()`（当前最大值 + 1）、AI detect（`detected.map(x=>({...x,groupKey:String(Ut++)}))`）、画完后提交 `dX()`（`groupKey: qA(t)`）—— **没有任何一处产生「多框同编号」**。（⚠️ 订正 2026-09-15：早前这里把「删框」也列成编号来源，**不对** —— 删框 `sX()` 是纯 `filter`，不碰任何 `groupKey`，只是留下编号空洞。）

### 3. 编组只能在数据层做（2026-09-14 落地；**当日 22:46 该手动宏退役**）

> ⛔ **本节的手动宏 `TR蒙板编组` 已于 2026-09-14 22:46 退役**（广哥定「删」：它的两项本事都有现役替代品，且它是全家唯一**绕开守卫直接写 `groupKey` 落库**的脚本 —— 插件升级最先失效、误用方向是「给 0 活卡的 note 新建卡」，脚本自己的预检就警告这点）。**以下内容转为机制档案**：`groupKey` 如何表示分组、`updateNoteFields` + `reconcileImageOcclusionCards` 如何对账、为何不能直写 SQLite —— 这些仍是「并组 / 拆组」的底层事实。**要动手时改走这两条路径**：① 多框并一组 = ⛔ ~~编辑器点 `All` 再保存（守卫并组）~~ **守卫已于 2026-10-12 退役**，现役做法 = 点 All 保存后自己数卡数、多出来的用 `TR清理` 收回；② 一图出多题 = 「一图一题」，同一张图多嵌几行、每处 1 组（**此条仍成立**）。备份：`~\.workbuddy\tmp\tr-io-group-backup-20260914\`（脚本 + harness + 退役时的 quickadd 配置）。

- 脚本（**已退役，文件已删除**，备份见 2026-09-14 日志）：原 QuickAdd 用户脚本 `truerecall蒙板编组.js`，宏名 `TR蒙板编组`，本机脚本与宏均已移除。
- 常量：`GROUP_PLAN = [3,1,2]`（★「一张图出多道题」用这个；例 a b c d 要 a | b+c | d 就写 `[1,2,1]`）| `GROUP_MAP = "1,2,2,3"`（逐框点名，长度=框数，给「要并的框顺序上不相邻」用，优先于 `GROUP_PLAN`）| `GROUP_SIZE = 0`（两者都空时的退路：0 = 全部并成一组）| `FORCE_SOLO = true`（产生多组时自动把 `maskMode` 改成 solo）| `SCOPE = "active"`（只处理当前打开的笔记）/ `"all"` | `DRY_RUN`（只预演不落盘，会打印「框→组」映射）。
- 做法：`fields.Regions` 解析 → 重写每个 region 的 `groupKey = String(floor(i / size))` → 整体 `JSON.stringify` 回 `Regions` → 调 **官方路径** `flashcardManager.updateNoteFields(noteId, newFields, "manual")` 落库。
- 为什么不直写 SQLite：`updateNoteFields` 内部对 `image-occlusion` 会走 `reconcileImageOcclusionCards(noteId, fields, createdVia)`——`o` = 现有 card 的 templateOrd 集，`a = wd(...)`，交集保留（**调度与复习历史不动**），多余的 `bulkSoftDelete` + `sessionPersistence.removeReviewedCards`，缺的 `createCardFromGenerated` 新建。手改库会绕过这套对账。
- 落盘（该宏已退役）：脚本末尾 `store.markDirty()` + `saveNow()`，并写诊断日志 `<vault>/.true-recall/tr-io-group.log`（本地时间戳）。
- 幂等：已是目标分组则跳过，复跑结果为「跳过 N 条」。
- **★ `GROUP_PLAN` 详解（2026-09-14 落地，专门解决「一张图多道题，且有的题几个框、有的题单框」）**：
  - 语义 = 按「框在 `Regions` 数组里的先后顺序」（= 编辑器 Regions 列表从上到下的顺序 = **画框顺序**）逐段切分：`[3,1,2]` → 前 3 框 1 组、第 4 框单独 1 组、第 5~6 框 1 组 → **3 组 = 3 张卡**。数组或字符串 `"3,1,2"`（逗号/加号/空格/顿号都认）都可以。
  - **最小例子（广哥 2026-09-14 问「a b c d，b+c 是一题」）**：4 个框 a b c d，要「a 一题 · b+c 一题 · d 一题」→ **`GROUP_PLAN = [1,2,1]`**（前提：a b c d 就是按这个顺序画的）。
  - **⚠️ 限制：`GROUP_PLAN` 只能按「连续段」切**。要并为一组的框若在画框顺序上不相邻（例如顺序 a b d c，想把 b 与 c 并一起），分段方案表达不了 → 用 **`GROUP_MAP`（逐框点名）**：`"1,2,3,2"`（4 项）→ `#0→组0 · #1→组1 · #2→组2 · #3→组1` = b 与 c 同组。长度必须 = 框数，组号随便写（按首次出现顺序归一成 0,1,2…），**非空时优先于 `GROUP_PLAN`**；方案不符的拒绝日志里也会提示改用它。
  - **常态做法**：画框时把「同属一道题」的框**连着画**，之后就只需要 `GROUP_PLAN`。`GROUP_MAP` 是顺序画乱时的逃生口。
  - **区域对象没有文字标签**（实测字段仅 `id/x/y/w/h/groupKey/shape`，跨 10 条 note 核过）→ 只能按序号认。所以日志把每个框打成 `#序号(形状 中心x%,中心y%)`，方便跟编辑器列表对上号。
  - **安全阀（拒绝写入，不猜不截断）**：元素和 ≠ 该 note 框数 → 该条**一条都不改**，Notice 报「方案与框数不符」，日志列出实际框数、每个框的位置、差值。方案里出现 0 / 负数 / 非数字也拒绝 —— **不做静默丢弃**，否则 `[3,0,3]` 会悄悄变成 `[3,3]`（少一组却毫无提示）。
  - **多组自动改 solo**（`FORCE_SOLO=true` 默认）：多组 + all 既冗余又会被 ⛔~~`TR自动编组` 守卫~~（**已退役，2026-10-12**）并回一组；置 `false` 可关。
  - **`DRY_RUN=true` 会预演**：逐条打印「现 N 框 / maskMode / 现分组 / 每个框位置 / 目标分组 / 映射 `#0→组0 …`」，方案不符打 `✗`。**改了方案先跑它看一眼最稳。**
  - 离线 harness（**已随宏退役移出 skill 目录**，备份在 `~\.workbuddy\tmp\tr-io-group-backup-20260914\test_tr_io_group.retired.js`）：`scripts/test_tr_io_group.js`（**30 项全 PASS**，覆盖数组/字符串方案、单框、混合 `[2,1,3]`、框数不符拒绝、`[3,0,3]` 拒绝、强制 solo、`FORCE_SOLO=false`、幂等、分组对但模式错、DRY_RUN 映射）。跑法：`TR_IO_GROUP_SCRIPT=<脚本路径> node test_tr_io_group.js`。
- **脚本触发口径（2026-09-14 定）**：`SCOPE="active"` 是按「**当前激活笔记** frontmatter 里的 `flashcard_uid`」去找 note，不是「当前编辑器里打开的那张卡」。所以流程是「先画框存卡 → 回到那篇源笔记 → 运行宏」。同一篇源笔记下的**全部**图片蒙板 note 会被一次性处理。

### 3.1 调用的精确形状（2026-09-14 二轮源码核对，写脚本前必看）

- `flashcardManager.updateNoteFields(e, r, n = "manual")` —— **同步方法，不是 async**。`e` = noteId；`r` = **完整 fields 对象**（整体替换，不是增量 patch）；`n` = reason（`"manual"` / `"ai"` / `"system"`）。
  源码：`if(this.store.notes.update(e,{fields:r},n), s.id===en) return this.reconcileImageOcclusionCards(i,s,r)` —— **注意 reconcile 的第二参数是 noteType 对象、第三参数才是 fields**，与从外面看像的顺序不同，别记错。
- **返回值** = `reconcileImageOcclusionCards(...)` 的结果，形如 `{ updatedCardIds: [...] }`；GUI 层就是同步读 `Va.updatedCardIds`，没有 await（@271880）。
- 等价关系：官方 `updateImageOcclusionNote(noteId,{imagePath,definition})` → `updateNoteFields(noteId,{Image:Ja(path),Regions:Om(definition)})`。**即「整字段替换」是正规写法。**
- **`Om()` 保留已有 groupKey**：`groupKey: typeof e.groupKey==="string" && e.groupKey.trim().length>0 ? e.groupKey : String(r)` → **在编辑器里保存已有卡片不会打散已编好的组**；只有**新画**的框才走 `RA()` 拿「当前最大值+1」的新编号。故：已有组**不会**被保存动作打散，只有**新画**的框才走 `RA()` 拿「当前最大值+1」的新编号。所以「加框后想仍是一张卡」= 保存时保持 `maskMode:"all"`，自动路线（3.4 节）会再并一次 —— 旧宏 `TR蒙板编组` 退役后这是**唯一**路径。

### 3.2 取数据用插件自己的 API，别手写 SQL（2026-09-14 二轮核对）

- `store.notes.getBySourceUid(uid)` → `SELECT * FROM notes WHERE source_uid=? AND deleted_at IS NULL`，再经 `xS()` 映射成 **camelCase** 对象：`{id, noteTypeId, fields(已 JSON.parse), tags, sourceUid, sourceText, userComment, createdVia, createdAt, updatedAt}`。
- `store.notes.getByNoteTypeId(noteTypeId)` 同理。
- **`store` 就是 `flashcardManager.store`**（源码里遍地 `this.store`）—— 反射探测时应先试 `fm.store`，成功率高得多。
- 数某 note 名下活卡：`store.cards.getCardsByNoteId(noteId)`；按源笔记取卡：`store.cards.getCardsBySourceUid(uid)`（`SELECT ... WHERE c.source_uid=? AND c.deleted_at IS NULL`）。
- 真要手写 SQL 时：`store.db.query(sql, params)` 返回**数组**（可直接 `.map`），`store.db.get(sql, params)` 返回**单行或 null**（全库 67 / 41 处用法一致）。
- `notes.getBySourceUid` 会把**同一篇源笔记下的文字挖空卡一起带出来**，所以脚本必须再按 `noteTypeId === "builtin-image-occlusion"` 过滤。

### 3.3 实操步骤 + 已实测运行（2026-09-14 16:50:12 首次成功；**该宏当晚 22:46 退役，本节转为历史记录**）

> ⛔ **本节三步自 2026-10-12 起整段作废**：`TR自动编组` 已由广哥点名有意删除、脚本与宏一并移除 ⇒ 第 3 步「点 All 再保存、守卫在入库前并组」**不再成立**。**现役手势 = 手动点 All + 保存后自己数卡数，N 张就用 `TR清理` 收回。**

**三步（`SCOPE="active"` 时的唯一正确姿势，历史记录）**：
1. 在图片蒙板编辑器（卡片菜单 `Add image occlusion`）里画框、存卡；
2. **把那篇源笔记切为「当前激活笔记」**（本例 = `临时/皮亚杰感知运动阶段汇总 1.md`，frontmatter 第 2 行 `flashcard_uid: 98d8dc8d`）——脚本按「激活笔记的 flashcard_uid」找它名下的 note，站错笔记会直接报 `当前笔记没有 flashcard_uid`；
3. （**此步已随宏退役消失，本机无对应命令**）⛔ ~~现役做法 = 编辑器里把 Mask mode 点成 `All` 再保存，`TR自动编组` 守卫在入库前并组~~ **该守卫已于 2026-10-12 退役** ⇒ 现在点 All 保存**不会**自动并组；现役做法 = 点 All 保存后自己数卡数、多出来的用 `TR清理` 收回（详见本节 3.4）。

**本机已实测通过**（该次日志原文摘要）：`flashcardManager 命中: flashcardManager | store 命中: fm.store` → `当前笔记: 临时/皮亚杰感知运动阶段汇总 1.md` → `flashcard_uid（来自 frontmatter）: 98d8dc8d` → `找到图片蒙板 note: 5 条` → 逐条 `已改 xxx: [0,1] → [0,0] | 卡 0 → 1 | 返回 updatedCardIds=1` → `saveNow 返回 true` → `小结 已处理=5 跳过=0 失败=0 | 活卡 0 → 5`。**即：编组本身一次成功，不需要重启、不需要停插件。**

**Notice 文案对照（照着判状态，别猜）**：`已编组 N 条…，活卡 X → Y` = 成功；`没有需要改的（跳过 N 条，已是目标分组）` = 已经编好，复跑的正常结果；`当前笔记没有 flashcard_uid（不是卡片源笔记）` = 站错笔记；`当前笔记下没有图片蒙板卡` = 那篇笔记名下没有蒙板；`定位不到插件数据层` = 插件没启用/版本变了（**未改任何数据**，安全中止）；`注意：N 条 note 活卡为 0，编组会新建卡` = 预检预警（见下条）。

**⚠️ 前置预检会预警，且预警内容是必然发生的**：`reconcileImageOcclusionCards` 的规则是「保留交集、软删多余、新建缺失」——若某些 note 名下活卡为 0，编组会**替它们新建**活卡。上例 5 条 note 全部活卡为 0 → 跑完就得到 **5 张全新的卡**（`state=0` 未复习）。

**⚠️ 想减重复 note，顺序不能反（`TR清理` 收不掉「有活卡」的 note）**：`TR清理` 只处理「`deleted_at` 为空**且名下没有任何活卡**的孤儿 note；一条 note 只要还挂着 1 张活卡就不算孤儿。所以「5 条重复 note → 1 条」的正确顺序是 **先删多出来的卡 → 那几条 note 变成孤儿 → 再跑 `TR清理`**，反过来先跑清理会一条都清不掉。

**想只预览不落盘**：把脚本第 47 行 `DRY_RUN = false` 改成 `true`，跑一次，日志里只有预检与配置，不改数据、不建卡。**脚本每次运行都从磁盘重读，改完不用重启 ob。**

### 3.4 「保存即分组」（⛔ **已退役**：原「现行 v3」所述的守卫于 2026-10-12 删除，本节整节为历史留档）

- ⛔ **本节整段自 2026-10-12 起只作历史留档**：`TR自动编组`（脚本 `truerecall自动编组.js`，曾 `command:true` + `runOnStartup:true`，版本 `2026-09-15.5`）已由广哥**点名有意删除**，脚本与宏一并移除 ⇒ **「点 All + 保存即自动并成一组」这道守卫现在不存在**，All + 多框不会被自动并回 1 张。现役手势 = 手动点 All + 保存后**自己数一遍卡数**，N 张就用 `TR清理` 收回。下面各条描述的是该脚本在被删之前的机制，**别照它安排现在的操作**。
  当时它的常量在脚本顶部：`AUTO=true`（false = 只记日志、不改数据）、`TRIGGER_MASK_MODE="all"`（并组触发值）、`REARM_MS=3000`。日志 `<vault>/.true-recall/tr-io-autogroup.log`（**append**，与覆盖式的 `tr-io-group.log` 不同；该日志已随脚本停写）。
- **★ v3 只有一件事：`maskMode === "all"` 且各框 `groupKey` 不止一种 → 并成一组（并到最小编号那组）**。其余情形（单框 / 已是一组 / `solo` / 非图片蒙板）一律原样放过，零行为变化。
- **沿革一句话**：v1 =「点 All 保存即并组」；v2 曾支持在图片嵌入行写 `%%io:1,2,1%%` / `%%io:map:…%%` 出多组；**v3 把整套 `%%` 代码删掉**（删掉的：`PLAN_RE` / `pickIoPlan()` / `parsePlanText()` / `readPlanForImage()` / 文件同步读与 mtime 缓存 / `resolvedLinks` 反查 / `report()` 的 `warn` 与 `plan` 分支 / `planFields()` 的方案分支）。理由：广哥改用 **「一图一题」**（要几道题就**对同一张图重复「制作蒙板」**，或同一篇笔记里**多嵌几行**同一张图 —— 二者等价，见 §十一.5 第 10.1 条；每处只放 1 组），这条路更稳，且 `%%` 在"每图一组"下永远不触发。
  ⇒ **现在 `%%io:…%%` 只是普通注释，写了也没人读**；守卫**不再读任何笔记文件**，只在入库前看 `fields`（纯内存判断，无 IO）。
- **做法 = 前置改写，不是事后补救**：在「保存」与「新建」两条链**真正落地**的那个对象的方法上各包一层，命中判据就把 `fields.Regions` 的 groupKey 全改成一个值，再调原方法。
  ```js
  // v2.5.0 起要包的是「真正落地」的那两层；门面上的同名方法编辑器根本不经过，包了也白包。
  const targets = [
      [fm,                  "updateNoteFields", "update"],   // 门面：API / AI / 命令入口
      [fm,                  "createNote",       "create"],
      [fm.noteMutation,     "updateNoteFields", "update"],   // ← 编辑器保存真正落到这层
      [fm.noteCreation,     "createNote",       "create"],   // ← 编辑器新建真正落到这层
  ];
  for (const [holder, key, kind] of targets) {
      const orig = holder[key];
      holder[key] = function (a1, a2, a3) {
          const hit = (kind === "create" && a1 && a1.fields)
              ? planFields(a1.noteTypeId, a1.fields, "all")
              : planFields(noteTypeOf(fm, a1), a2, "all");        // 纯函数：只读判断 + 改副本
          if (hit && kind === "create") a1 = Object.assign({}, a1, { fields: hit.fields });
          if (hit && kind !== "create") a2 = hit.fields;
          return orig.apply(holder, [a1, a2, a3]);
      };
  }
  ```
  **为什么必须前置**：reconcile 在保存那一瞬间就跑完、`cards:bulk` 事件在其后 —— 事后补救只能再跑一次 reconcile，会经历「建了新编号的卡 → 又把它删掉」的往返并多攒软删记录。前置改写让插件**第一次** reconcile 就看到正确分组（保留最小编号那张、软删多余的，一步到位）。
- **要包哪几个对象（4 个）**：编辑器保存 / 新建**不经过门面**，真实链路是
  `编辑器 → fm.updateImageOcclusionNote`（门面）→ `imageOcclusion`（`P0` 实例）`.updateImageOcclusionNote` → `this.updateFields(...)`（**构造时注入的箭头函数**）→ **`noteMutation.updateNoteFields`**；
  新建则是 `fm.createImageOcclusionNote` → `imageOcclusion.createImageOcclusionNote` → **`noteCreation.createNote`**。
  ⇒ 只包门面上的 `fm.updateNoteFields` / `fm.createNote`，**一次都不会被调到**（实测：点 All 保存出 2 张卡、日志里一条 `[并组]` 都没有）。**教训**：插件大版本重构后，「门面方法还在」不等于「调用链还经过它」——要从编辑器那端顺着追每一跳的 `this`。重复经过是幂等的（第二层看到的已是单组 → 放过）。
- **判据（四条全中才动手）**：① noteTypeId 是 `builtin-image-occlusion`（拿不到时退化为「fields 里同时有 `Image` 与 `Regions`」）；② `def.regions.length >= 2`；③ `maskMode === "all"`（**`maskMode` 缺失视作 `solo`** ⇒ 缺字段的畸形数据不会被动）；④ 各框编号去重后 **> 1 种**。任一条不满足 → 原样返回，**零行为变化**。
- **离线测试（已退役）**：守卫的纯逻辑 harness 原为 33 项全 PASS（v3 后重写），前 3 项断言 `%%` 接口已不再导出，其余覆盖 `readRegionsDef` 各种输入、非法 / 负数编号退回下标、并到最小编号（`[2,3]`→`2`、乱序→最小值）、`solo` / 单框 / 已单组 / 缺 `maskMode` / 非 IO 全放过、**noteTypeId 拿不到但有 `Image` 仍动手**、Regions 传对象、**regions 含 `null` 元素不炸**、不就地修改入参、**幂等（对输出再跑一次 = 放过 ⇒ 守卫可安全重复包裹）**、`triggerMaskMode` 可参数化。⛔ 2026-10-12 守卫退役，harness 一并删除，**本条留档为机制说明、当前不可跑**。
- **并到「现有最小编号」而不是硬写 `"0"`（重要）**：`wd()` 用 `templateOrd = parseInt(groupKey)` 出卡，`reconcileImageOcclusionCards` 只保留 `templateOrd` 有交集的那张。若原编号是 `[2,3]` 却硬写 `"0"`，插件会**新建** ord=0 的卡、把原来的全 `bulkSoftDelete` → **白丢复习进度**。取 `min` 则保住原本 ord 最小的那张。
- **幂等**：已单组的卡再保存 → 判据④不满足 → 放过；`solo` 的卡全程不介入。
- **自动维护**：脚本注册 `window.setInterval(REARM_MS)`（句柄存 `globalThis.__trAutoGroupTimer`，重跑先 clear 旧的）每 3 秒检查包裹是否还在（在函数上打 `__trAutoGroup = VERSION` 标记）→ **插件被禁用又启用、或插件重载换了实例，都会自动补装**。
- **两条帮不了的边界**：① **不保存就不落库**（`maskMode` 是编辑器内存状态，插件设计如此）；② 重载 / 启动过程中那一小段窗口（页面 JS 已清、启动宏还没跑完）里保存的蒙板不受保护。
- ⛔ **历史结论（守卫已于 2026-10-12 退役，本条不再有适用对象）** —— 「重载后要不要手动重跑守卫」→ 不用（此前写的"`Ctrl+R` 会让守卫消失、需重跑"是错的）：QuickAdd 在 `onload` 里注册启动宏（`this.app.workspace.layoutReady ? i() : this.app.workspace.onLayoutReady(i)`），`Ctrl+R` 整窗重载 ⇒ 插件重新 `onload` ⇒ **本宏自动重跑、守卫自动重装**（实证：三个常驻宏曾在同一秒各写一条启动记录，那是一次重载后的批量装载）。⇒ 真正需要手动重跑的情形只剩**宏注册丢了 / 脚本被改名或删了 / `runOnStartup` 被关**（这几种守卫根本装不上）。**判据**：看 `tr-io-autogroup.log` 有没有对应你那次保存的 `[create]` / `[并组]` 行。
- **离线实测**（假 fm 模拟 reconcile，六条全 PASS）：

  | 场景 | 卡 templateOrd |
  |---|---|
  | all + 三组 `[0,1,2]` | `[0,1,2]` → `[0]` |
  | solo + 三组 | 不动 |
  | all + 已单组 | 不动 |
  | all + `[2,3]` | `[2,3]` → `[2]`（并到 2，保住原卡） |
  | all + 非图片蒙板 | 不动 |
  | `createNote` + all + 三组 | `[0]`（1 张） |

- **⚠️ 语义边界（要跟用户讲清）**：本守卫的含义是「**这张卡 `maskMode=all`，以后只要再保存就并成一组**」（`all` 在插件语义里就等于"这张图要全遮" = 只要一张卡）。想「all 显示 + 故意多张卡」是自相矛盾的，出路只有两条：① 把 `AUTO=false` 关掉守卫（多组留得住，但 `all` 保存从此也不并组）；② 改 `TRIGGER_MASK_MODE`（换成任何非 `all` 的值 ⇒ 守卫不再对 `all` 动手）。
- **想造「多组卡」怎么办**：**用 Solo 保存就完全不受影响** —— 守卫只认 `maskMode=all`，Solo 路径它一次都不介入，每个框保持自己的 groupKey、每框一张卡。两种模式的语义对照（源码 `Fxe()` 的 class 分支 + `Mask mode` 那组按钮）：
  - **Solo = hide one**：复习一张卡只遮**自己那一组**，其余组拿 `is-outline-passive`（只描边、露着答案）；
  - **All = hide all**：复习时**所有组一起遮**（非当前组拿 `is-mask-passive`）→ 所以 All 下多组是**冗余的**（每张卡遮的都是同一张全遮图、答案一样，等于重复出题），这也正是守卫在 `all + 多组` 时并成一组的原因。
  - **⇒ 结论**：要「一张图出多道题」→ 用 **Solo** 建（多组各遮各的）；要「一次遮全部、只要一张卡」→ 用 **All**（守卫自动并）。两者不冲突。
  - 保存已有框不会打散分组：`Om()` 写的是「已有 groupKey 原样保留」，只有新框才拿 `max+1`（`RA()`）→ 多次加框、多次保存可持续累积多组。
  - **唯一会"吃掉"多组的动作**：把一条 **Solo 建好的多组卡**打开编辑器、切成 **All** 再保存 → 守卫出手并成 1 组，多余卡软删（可还原，但调度只保留最小编号那张）。
- **❌「All 模式下分两次加框、各保存一次 → 2 组卡」做不到**：新画的框走 `RA()` 拿 `max+1`，每次 All 保存守卫都再并一次 ⇒ **累积不出第二组**。而且即便临时关掉守卫，All + 多组本身也是冗余的。
  ⇒ **想要「多组卡」必须在保存那一刻是 Solo**（All 只是"这张图要全遮"的声明，天然等价于单组）。且编辑器**没有编组 UI**；「一张图出多组卡」现在**没有任何工具支持**（v2 的 `%%io:` 已在 v3 移除；手动宏 `TR蒙板编组` 已退役）—— 广哥的实际选择正是彻底不走多组这条路，改用「一图一题」（见 §十一.5 第 10.1 条）。
  - **⚠️ 卡数跟「打开编辑器几次 / 保存几次」无关**：**卡数 = 该 note 的 `groupKey` 种数**。写入 groupKey 的每一条来源都是「一框一新编号」→ **Solo 下卡数 = 框数**（分 3 次打开、每次加 2 框 = 6 框 = 6 张卡，不是 3 张）。**并组只能让卡数变少，永远不会因为"多保存一次"而多出一张卡。** 三种情形对照：

    | 保存时的 mode | 守卫在不在 | 结果卡数 |
    | --- | --- | --- |
    | solo | 无所谓（守卫只认 all） | = 框数（每框一卡） |
    | all | 在 | **恒 1 张**（每次保存都并成 1 组） |
    | all | 不在（宏注册丢了 / 脚本被改名删了 / `runOnStartup` 被关 / `AUTO=false` / 那批卡建在守卫装上之前） | = 框数，但每张卡看到的都是同一张全遮图 |

  - **⚠️ `maskMode` 是「整条 note = 整张图」一个值，不是每组一个**：一张图内**不可能**「有的组 solo、有的组 all」。能做到的"混"是**组的大小**混 —— 同一张图、同一个 `solo`，有的组 3 个框、有的组 1 个框。真正"两种模式并存"只发生在**一篇笔记有多张图**时（每张图是各自独立的 note）。
  - **建多道题期间的操作纪律**：可以分次打开、分次加框保存（新框总是追加到末尾、已有 groupKey 不动）；但**期间别在 All 下保存** —— 守卫会把已建的多组并掉并软删多余的卡。
- **两个 TR 蒙板宏的分工**：
  - `TR制作蒙板`（`truerecall制作蒙板.js`，`runOnStartup:true`）= **入口** —— 右键图片 / 文本行 / 命令面板 → 带图开编辑器。
  - `TR自动编组`（`truerecall自动编组.js`，`runOnStartup:true`）= ~~**常驻守卫** —— 点 All + 保存即并组~~ ⛔ **已于 2026-10-12 随宏删除，该能力当前不存在**。
  - ~~`TR蒙板编组`~~（手动，**已退役**）—— 曾是「不开编辑器、直接改库里已存在 note 的 `groupKey`」，`SCOPE="all"` 时可全库批处理。现在**命令面板里没有它**；「一张图本该 1 张卡却出了 N 张」的修法 = 删掉多余的卡 → 进编辑器点 `All` 重存（守卫接手并组）。
  - ⛔ **历史排查项（守卫已退役，仅供处理旧卡时参考）** —— 「守卫不在的四种情形」（此前误写成"`Ctrl+R` 后忘了重跑"）：① QuickAdd 里 `TR自动编组` 条目被删 / 脚本被改名或删了 / `runOnStartup` 被关 ⇒ 从来没装上；② `AUTO=false` 观察模式；③ 那批卡建在守卫写出之前；④ 别的设备 / 别的 vault 副本上建的卡（守卫只在本机这个 app 实例里）。
    - **怎么知道发生了**：看**卡数**。一张图本该 1 张卡却出了 N 张 = 当时没并成一组。⛔ ~~再核 `tr-io-autogroup.log`：你保存那一下若守卫在，必有一行 `[create]` / `[并组]` 记录。
### 3.5 「新建时错开编号」—— 同一张图多题时卡名不再重名（2026-09-15 v8，广哥要求；同分钟打了补丁 → `.5`）

**问题**：卡面正面文本的生成式是 `Image occlusion ${templateOrd+1}`（main.js @3531755，**只有 groupKey 参与、不带图名**），而每条 note 的编号都从 0 起（`qA()` = 本 note 内最大值 + 1）⇒ 同一张图做出来的 N 条 note 全叫 `Image occlusion 1`，在卡片浏览器 / 侧面板里分不出谁是谁（改图片文件名也没用，见 §十一.5 第 4 条）。

**做法（v8）**：在**新建那一刻**（`createNote` 分支）把本条 note 的编号整体平移到「**同一张图现存所有蒙板 note 的 `groupKey` 最大值 + 1**」起 —— 多框顺延（`[0,1]` → `[3,4]`），保持框之间的相对编号关系。⇒ 同一张图的卡名依次 1 / 2 / 3 …，不再重复。

- 读库依据：`fm.store.notes.getByNoteTypeId("builtin-image-occlusion")` → 只取 `fields.Image` 相同的**其他** note → 收集各自 `Regions` 里的 groupKey 数值 → `max + 1`（`keysUsedByImage` / `nextBaseKey`）。
  ⚠️ 该接口返回的是**活跃 note**，**已无卡的空壳 note 也算在内**（它们的 groupKey 照样占号）⇒ 编号只**递增、不回收**，会被历史残留的 note 抬高。2026-09-15 实测：那张图上有老 note 占着 `0/1/2`（其中 8 条已是空壳）⇒ 新建的第一条从 `#3` 起、卡名就是 `Image occlusion 4`，广哥当场问「是不是有孤儿文件残留」。**这不是 bug、是刻意的编号策略** —— 保证「不与任何现存 note 撞号」比「编号紧凑」更重要（要紧凑只能整图清掉重建）。**广哥 2026-09-15 明确选「先不动」**（另两个选项：只让 base 跳过空壳 / 清空重来从 1 开始）。
- 顺序：**先并组、再平移**（all + 多框 → 一组，再把这一组抬到新起点）。
- 安全降级：读不到库 / 该图还没有别的 note ⇒ base = 0 ⇒ 一个字都不改。
- 纯函数 `planOffset(noteTypeId, fields, base)`（已进 harness，48 项）：`base ≤ 当前最小编号` 时返回 `null`（幂等，二次包裹安全）；非法/负数编号同 `currentKeys` 口径退回下标。

**⚠️ 为什么「每次保存都改编号」不行**（广哥原话是"每次保存的时候改下"）：插件 reconcile 按 `templateOrd` 取交集保留卡（`reconcileImageOcclusionCards`）—— 已建过卡之后再改编号 = 旧 ord 不在新集合里 ⇒ **旧卡软删 + 新建卡 ⇒ 那张卡的复习进度归零**。所以错开**只在 `createNote`（首次建卡）做**，`updateNoteFields` 路径绝不碰编号。

**⚠️ 存量 note 的编号不会变**：已存在的 note 保持原编号（改它们 = 清进度）。想整理只能删掉重建（新卡从 0 开始计进度）。

**⚠️ v8 自己踩的坑（`.3/.4` 的回归，`.5` 已修，值得记）**：v7 把两个包裹函数抽成 `wrapOne()` 之后，它内部仍引用 `fm` —— 而 `fm` 只是 `install()` 的**形参**、不在 `wrapOne` 的作用域里 ⇒ 每次走到那行就抛 `ReferenceError: fm is not defined`，被兜底 `catch` 吞掉、只写一行日志 ⇒ **update 路径（改已有卡再保存）的并组静默失效**；create 路径当时不引用 `fm`，所以**只坏了一半、更难发现**。判据：日志出现 `并组判断失败(noteMutation): fm is not defined`。修法 = 把 `fm` 作为 `wrapOne` 的第一个形参显式传进去。
⚠️ **通用教训**：**兜底 `catch` 会把"自己的编码错误"伪装成"插件不配合"** —— 包裹式补丁的兜底日志必须带**错误原文**（带了才一眼看出是 ReferenceError），而且每加一个分支都要拿**真实运行日志**复查；离线 harness 只测纯函数，抓不到这类作用域错误。

**已向作者反馈（2026-09-15）**：本节（错开编号）与 §七「solo 非本卡框改中灰蒙板」两条思路，连同「删卡连带（`getCardByReverseOf` 名不副实、`LIMIT 1` 随意赔一张）」一并提交为 issue **[pieralukasz/true-recall#61](https://github.com/pieralukasz/true-recall/issues/61)**（英文正文，open）。**若作者采纳，`TR自动编组` 的并组/错开两件事与那个 CSS snippet 都可以考虑退休** —— 届时要先复核插件新行为再动本机补丁，别直接删。

### 3.6 「PDF 页 → 图片蒙板」（2026-09-15 新增，广哥要求；实现于 `TR制作蒙板` 的第三条通道）

**需求原话**：「对于 pdf 类的能够右键创建后把这页 pdf 转成图丢到编辑中吗」—— 想在 PDF 讲义上直接右键做挖空，而不是先截图、再导成图片。

**为什么必须新开一条通道**：`editor-menu` 只认 markdown 正文右键、`file-menu` 只认文件列表与笔记里渲染出的图片；**PDF 是自定义视图，这两条都不触发**。所以第三条 = 在 PDF leaf 的 `containerEl` 上监听 DOM `contextmenu`，弹**同一个 `Menu`、同一个菜单项名**（只多一个「（此页）」后缀），体验与右键图片一致。

**链路**（`Scripts/truerecall制作蒙板.js` 的 `runPdf()`）：

1. **取当前页号** —— 多路试探、命中即用。**优先级 2026-09-15.8 重排过**（起因：广哥报「PDF 里右键，加入的图**常常是上面一页**的」）：
   | 顺序 | 来源 | 性质 |
   |---|---|---|
   | ① | **右键落点那一页**：DOM `closest("[data-page-number]")` | **唯一精确对应「你点的那一页」** |
   | ② | `view.child / view.viewer / view.pdfViewer` 里的 `pdfViewer.currentPageNumber` | pdf.js **实时**当前页（吃 `pagechanging` 事件，随滚动走） |
   | ③ | `leaf.getEphemeralState().page` | 持久化快照，可能滞后 |
   | ④ | `view.getState().page` | 持久化快照，可能滞后 |

   - ① 的源码依据：pdf.js 给每页 div 写了 `class="page" data-page-number="N"`（asar @16190392），侧栏缩略图是 `div.thumbnail[data-page-number]`（@16221407）；Obsidian 自己也这么读（@16312267 `e.closest(".page")` + `getAttribute("data-page-number")`）。⇒ 点子元素（textLayer 的 span、annotationLayer）也能 `closest` 上去；**在缩略图上右键也认**。
   - **根因（这个 bug 的真身）**：③④ 是**持久化快照**，只在特定时机写；旧顺序把 ④ 排在第二位，而实测它恰好是唯一命中的那路（日志 `来源=view.getState().page`）⇒ **往前翻几页再右键，就会渲染到上一页**。所以顺序必须把「落点页」与「实时页」放在两个快照之前。
   - **全落空就中止**（宁可不动，也不要渲染错页），并把各路试探的原始结构整条写日志（`dom-page=… ｜ viewKeys=… ｜ ephemeral=… ｜ state=…`；Obsidian 升级后据此重新定位）。

2. **渲染** —— `child_process.execFileSync(PY_EXE, [Scripts/render_pdf_page.py, <pdf绝对路径>, <页号>, <png绝对路径>, 160])`；`PY_EXE` = 托管 venv `~/.workbuddy/binaries/python/envs/default/Scripts/python.exe`（已核实 PyMuPDF 1.28.2 可用）。分辨率常量 `RENDER_DPI = 160`。
   ⚠️ **`dpi` 必须传 int**：PyMuPDF 1.28 的 `get_pixmap(dpi=…)` 内部走 `set_dpi` → `fz_pixmap_xres_set`，给 float 直接抛 `TypeError: in method 'fz_pixmap_xres_set', argument 2 of type 'int'`（2026-09-15 首次实测踩到，`render_pdf_page.py` 已改成 `int(round(float(argv[4])))`）。
3. **落盘** —— `<vault>\images\<pdf基名>-p<N>.png`（遵守 vault 写入纪律第 9 条：图片一律进 `images/`）。**文件名固定** ⇒ 同页重做覆盖同一文件 ⇒ 同一页做几次 = 多条共用一张图的独立 note，与「一图一题」等价、删卡不连带。
4. **开编辑器** —— 复用 `openWithImage()` 那条链路（`getFirstLinkpathDest` 解析 → 保证 `sourceUid` → `openImageOcclusionEditor({mode:"add", imagePath})`）。
5. **宿主笔记** —— PDF 视图没有 md 可以挂 frontmatter ⇒ 按「**最近打开的文件顺序**」挑一篇 md（`workspace.getLastOpenFiles()` 里第一个 `.md`；活动文件是 md 就直接用它；都没有才退回任意打开的 md leaf）。2026-09-15 实测：早前一版「活动 leaf 优先、否则随便抓一篇」把卡片挂到了**完全不相干的笔记**（《皮亚杰感知运动阶段汇总 1》）上，已改。注意**「笔记里嵌入的 PDF」那个入口不用这套**（宿主 = 当前活动笔记，见本节末）。Notice 与日志都会写明卡片挂到哪篇。

**判据**（`<vault>/.true-recall/tr-io-cmd.log`）：装载时 `PDF 通道：已给 N 个已打开的 PDF 视图挂上右键`；触发时 `runPdf(pdf-menu)：pdf=… ｜ 页号=… ｜ 来源=… ｜ ephemeral=…`；成功后 `runPdf 渲染完成 → images/…png ｜ OK 1200x1697 page=N`。

**边界与坑**：① 只对 `.pdf` 视图生效；② 转出来的是**静态快照**，原 PDF 改了不会自动更新（要更新就再右键一次，覆盖同名文件，已有卡跟着换图）；③ 这条 DOM 通道比前两条**脆**（Obsidian 改 PDF 视图结构就可能失效），失效表现 = 右键不弹菜单，先看日志有没有那行 `PDF 通道：已给 N 个…`；④ 命令面板入口 `tr-io-tools:pdf-page-to-occlusion`（名「制作图片蒙板（当前 PDF 页）」）只在活动视图是 PDF 时可见。
> ⚠️ **与 PDF++ 的冲突 + 现行解法（2026-09-15 广哥实测，源码级）**：本机 `pdf-plus` **已启用**（v0.40.31），它**也在 PDF 视图上挂自己的右键菜单** —— 关键原文 `t.defaultPrevented || await Wg(n, e, t)`（`Wg` 里用 `Nu.fromMouseEvent(...)` 构造它的 Menu 再 `showAtMouseEvent`）⇒ **它先看事件有没有被 preventDefault，被处理过就让位**。实测（09:37 前）：普通右键**只看到 PDF++ 的菜单**、本脚本的项根本不出现。
> **现行解法（脚本 `2026-09-15.3`）＝ Alt+右键 $+$ 捕获阶段**：
> · 普通右键 → 本脚本直接 `return`、**不 preventDefault** ⇒ PDF++ 的菜单照常；
> · **Alt+右键** → `containerEl`（最外层）在**捕获阶段**早于 PDF++ 的 handler 执行，弹自己的菜单并 `preventDefault()` ⇒ PDF++ 看到 `defaultPrevented` 自动让位。
> 另一条永远可用的入口 = 命令面板 `tr-io-tools:pdf-page-to-occlusion`（只在活动视图是 PDF 时可见）。
> ⚠️ **教训**：**PDF 视图的右键不是"无主之地"** —— 想往那儿挂菜单，先查同库其他插件有没有占位（PDF++ 是最常见的占位者），别硬抢。

**入口二：笔记里嵌入的 PDF（2026-09-15.4 起；机制在 `.6` 被**订正**）** —— 广哥的常用形态是 ``![[最后一遍疯狂刷题-科目一单选题.pdf#page=68|…, p.68]]``。

> ⚠️ **机制订正（2026-09-15.6 实测）**：`.4` 时推断它走 **file-menu**（以为像嵌入图片那样经 `internal-link` → `handleLinkContextMenu` → `trigger("file-menu", …)`），**实测不成立** —— 右键嵌入的 PDF（点在 pdf.js 画面上）取不到编辑器 token，那个分流**根本到不了 file-menu**（日志里一条 `file-menu:` 行都没有）。现行做法 = **在 document 捕获阶段直接接管**：`onCtx()` 里调 `handlePdfEmbedCtx()`，命中「`.internal-embed` $+$ `.pdf` $+$ Alt」就弹菜单并 `preventDefault()` $+$ `stopPropagation()`（捕获顺序是 window → document → … → target，比谁都早），不再依赖任何分流猜测。

- file-menu 那条 PDF 分支**保留**：右键**链接源码行**（编辑器里的 `[[…]]` 文本）时仍会走它，是另一条有效入口。
- 图片 → 老行为（**不需要** Alt）；**PDF → 要 `Alt`**（把普通右键留给 PDF++）。
- 页码从嵌入链接的 `#page=N` 抠（`pdfPageFromEl` / `pdfPageFromText`，editor 选区与光标行兜底）—— **抠不到就中止、不渲染**（`pickPdfPage` 返回 `page: 0`）。
- **宿主 = 当前活动 md**（嵌入场景本来就在笔记里，比 PDF 视图场景明确得多）。
- 纯函数已进 harness：`pdfPageFromText` / `isPdfFile` / `pickPdfPage` / `toAbsPath` / `resolveVaultFile`，**46 项全 PASS**。
- 判据：点中后日志出现 `pdf-embed-ctx：src=… ｜ page=68`；没带 `#page=N` 时写 `page=(无 #page=N，会中止)`。
- ⚠️ **`linkpath ≠ vault 路径`（2026-09-15.7 修的 bug，必记）**：从 `.internal-embed[src]` 抠出来的是**链接里写的形态**，常见就是裸文件名（`最后一遍疯狂刷题-科目一单选题.pdf`），**不是**库内路径。当时直接拼 `<vault>\<文件名>.pdf` → python 报 `pdf not found`（真实文件在 `2026上数学教资/冲刺班/科一/` 下）。**正解**：一律经 `resolveVaultFile()` → `metadataCache.getFirstLinkpathDest(linkpath, 活动md路径)` 解析（＝Obsidian 自己的「同名就近」规则），拿不到再按文件名在 `vault.getFiles()` 里唯一匹配兜底；**解析不出来就中止不渲染**，绝不猜路径。PDF 视图那条入口不受影响（它的 `file` 本来就是 TFile）。
- ⚠️ **同版本另修的一个坑**：`execFileSync` 必须带 `env: {PYTHONUTF8:"1", PYTHONIOENCODING:"utf-8"}` —— 否则 python 的 stderr 走 locale(cp936)、被 node 按 utf8 解出来全是「�」，报错里**中文路径整段乱码**，光看乱码会把「路径错了」误判成「编码错了」。顺带：`runPdfCore` 现在渲染前先用 `vault.getAbstractFileByPath` 自查一遍，找不到就直接中止（不开 python、Notice 写清是哪条路径）。

## 四、能不能用脚本/API 让 AI 批量做？

**不能，三条路都堵死（2026-09-14 实测确认）：**

1. **Local API 没有 image-occlusion 通道**。`POST /cards` 的 handler（`pZ`）只认两种：
   ```js
   let A = u.card_type === "cloze";
   let noteTypeId = A ? Pi /*builtin-cloze*/ : ri /*builtin-basic*/;
   let fields = A ? {Text: u.question, Extra: u.answer} : {Front: u.question, Back: u.answer};
   ```
   即 `card_type:"cloze"` → cloze 卡；**其余任何值（含 "image-occlusion"）一律落成 basic 卡**。全部 70 条路由里也没有建/改 image-occlusion 的接口。
2. **`createImageOcclusionNote` / `updateImageOcclusionNote` 只在编辑器回调里被调用，未暴露 HTTP**。
   - 签名：`createImageOcclusionNote({imagePath, definition, sourceUid, sourceText, createdVia})` → `createNote({noteTypeId:en, fields:{Image, Regions:Om(definition)}, ...})`；
   - `updateImageOcclusionNote(noteId, {imagePath, definition})` → `updateNoteFields(noteId, {Image, Regions})`。
   - **注意**：这两个是 `flashcardManager` 上的方法，QuickAdd UserScript 里能反射拿到 → **不新增区域、只改已有 region 的 `groupKey` 可以走它/走 updateNoteFields**（3.3 节 即此路线）。
3. **直写 SQLite 路线已证伪**（`softDeleteWithCascade` 级联软删，见 SKILL.md 铁律）。

## 五、AI 助手（chat 那套）也不管图片

助手工具集全量（11 个）：`create_cards` / `update_card` / `update_draft` / `update_proposal` / `remove_proposal` / `read_note` / `create_note` / `append_to_note` / `insert_diagram` / `search_images` / `get_related_cards` / `report_fact_check`。

- 没有任何建/改 image-occlusion 或 regions 的工具。
- `search_images` 只是搜 Openverse 的 CC 图并提"附图"草案；`insert_diagram` 是 Mermaid/SVG **图**，都不是蒙板。
- 「卡片方法学」prompt 通篇只讲 basic/cloze（原子化、1-3 词答案、禁列表答案…），**一个字没提图片**。

## 六、结论与建议

1. **想让 AI 自动生成"图片蒙板挖空"——插件没这条路，且它是被作者刻意封死的**（`Never return masks`）。
2. 作者的设计是：**AI 找区域 → 人在编辑器里验收/微调 → 蒙板由插件按矢量 regions 画**。这是对的：
   - 蒙板必须是**可撤销的矢量数据**（揭示答案时撤掉），做成像素图就永远遮死了，失去图片蒙板的意义；
   - 教学图的"该遮哪里"本身是主观判断（这个词要不要考、这个标签是否重要），AI 顶多给候选框。
3. **实际建议**：图片蒙板就自己做。用卡片菜单 `Add image occlusion` 进编辑器（无 proKey 可用）→ 点 `AI detect regions` 拿一版框（**要 proKey**）→ 手工增删/改形状 → 要"多框同组"就把 `Mask mode` 点成 `All` 再存（守卫并组）；一图要出多题就走「一图一题」（同一张图多嵌几行，**或对同一处重复「制作蒙板」—— 二者等价，后者笔记更干净**，见 §十一.5 第 10.1 条）。**别指望脚本批量造 regions。**

## 七、揭示态 CSS 陷阱：揭示后盖成一块实心绿（2026-09-14 定位；**2026-09-15 v2.5.0 已由作者修复**）

> **★ 现状（2026-09-15 复核，先看这段）**：**插件 v2.5.0 自己修好了，本机 workaround 已停用。**
> `styles.css` 现行规则原文：`.true-recall-io-shape.is-revealed-active{fill:#00000000;stroke:var(--color-green);stroke-width:.003px}` —— **完全透明填充 $+$ 绿描边，且 `@keyframes true-recall-io-pulse` 已整块删除**（`true-recall-io-pulse` 在该文件 0 命中）。比本机早先那个 workaround（淡绿 `fill-opacity:.16`）更彻底：现在揭示后**一点填充都没有**，只剩一圈绿描边。
> 本机那个 workaround snippet —— `<vault>\.obsidian\snippets\true-recall-图片蒙板.css` —— 先于 2026-09-15 08:29 从 `appearance.json` 的 `enabledCssSnippets` 里取消勾选，又在同日 **08:47 应广哥要求移出 vault**（备份 `~\.workbuddy\tmp\backup-20260915-tr-snippet-revealed-css\`）⇒ `snippets` 目录里已经没有它，现在生效的完全是**插件原生样式**。（判据只看 **`snippets` 目录里在不在那个 css 文件**，**别拿 `enabledCssSnippets` 的条目数当判据**——该列表长期挂着大量无对应文件的条目，数它会得出错误结论。）
> ⚠️ **别再把那个 snippet 勾上**：它写着 `fill: var(--color-green) !important; fill-opacity: 0.16 !important`，会把新样式盖回去、给揭示区加一层淡绿。**下面整节只对 v2.4.2 及更早有效，留作历史与回滚参考。**

**现象**：做出蒙板 → 复习时按揭示 → 遮挡框**换成一个颜色继续蒙着**，看不到底下的答案。

**根因**（插件 `styles.css` 原文）：

```css
.true-recall-io-shape.is-revealed-passive { fill:#00000000; stroke:var(--text-faint); stroke-width:.002px; opacity:.7 }
.true-recall-io-shape.is-revealed-active  { fill:var(--background-modifier-success); animation:.82s ease-out true-recall-io-pulse }
@keyframes true-recall-io-pulse { 0%{fill:var(--background-modifier-success)} 55%{fill:var(--background-modifier-success)} to{...} }
```

- 分类由 `Fxe(region, templateOrd, revealed, maskMode, revealSingleOnly)` 决定：`is-revealed-active` = 本卡要揭示的那个框，`is-revealed-passive` = 已透明。
- **作者显然按「半透明成功色」写的**，但 Obsidian 内置主题里 `--background-modifier-success` = `var(--color-green)`，**是不透明色**（light `#08b94e` / dark `#44cf6e`）→ 揭示后那块框变成整片实心绿，把答案盖死。`@keyframes` 的 0%/55% 两帧也是同一个不透明色，闪烁动画同样看不出内容。
- **本机主题**：`appearance.json` → `theme:"moonstone"`、`cssTheme:""`（默认）、`accentColor:"#303e78"`。

**修法（当时已落地，2026-09-14 18:30 恢复；⚠️ 该片段已于 v2.5.0 之后被停用，见本节顶部「现状」）**：`<vault>\.obsidian\snippets\true-recall-图片蒙板.css`，当时写入了 `appearance.json` 的 `enabledCssSnippets`（当时 **39 项**）。
- 时间线：13:55 首建 → 18:24 按广哥要求**整体删除**（他要先看原生）→ 18:30 他实测「一删又出现问题了，揭示后蒙板换个颜色还遮着」→ **只恢复揭示态这一块**，另两块不带回。
- **这一块是真 bug 修复，别随手删**：删掉即回到原生不透明实心绿，答案被整块盖死（广哥 18:30 实测复现一次）。
- 备份：`~\.workbuddy\tmp\backup-20260914-tr-snippet\`（`.css` + `appearance.json`），是 18:24 删除时的三块完整版。
- **片段增删会被 Obsidian 的 watcher 自动重载**（见「九、回答页注入」），不必手动 Ctrl+R。

```css
/* 现用版（与 vault 内文件逐字一致，只这一块） */
.true-recall-io-shape.is-revealed-active {
    fill: var(--color-green) !important;
    fill-opacity: 0.16 !important;
    stroke: var(--color-green) !important;
    stroke-width: 0.003px !important;
    animation: none !important;
}
/* 备用·当前未启用：.true-recall-io-shape.is-revealed-passive { fill-opacity: 0 !important; }
   —— 冗余，插件原生已是 fill:#00000000 */
```

想保留那 0.82s 的脉冲动画，就删掉 `animation: none !important;` 那一行（动画本身无害，有害的是不透明填充）。**当前采用的就是「只修揭示态、mask 配色保原生」这条路**（18:30 恢复时定的）。

### 提问态（未揭示）的四个 class，以及「选了 all 却遮不全」的真相（2026-09-14 补）

判类函数 `Fxe(region, templateOrd, revealed, maskMode, revealSingleOnly)`（@524805 原文可还原为下表）：

| 状态 | 本卡的框（同 groupKey） | 非本卡的框（跨 groupKey） |
|---|---|---|
| 未揭示 · `maskMode:"all"` | `is-mask-active` | **`is-mask-passive`** |
| 未揭示 · `maskMode:"solo"` | `is-mask-active` | **`is-outline-passive`** |
| 已揭示 | `is-revealed-active` | `is-revealed-passive`（`revealSingleOnly` 时回落到上面两种 passive） |

```css
.is-mask-active   { fill:var(--interactive-accent); fill-opacity:1 }          /* 实心，明显 */
.is-mask-passive  { fill:var(--background-modifier-hover); fill-opacity:1 }   /* 浅色主题下≈5%黑，看不见 */
.is-outline-passive{ fill:#00000000; stroke:var(--text-muted); stroke-width:.002px; opacity:.85 }  /* 等同透明 */
```

**关键结论：`maskMode:"all"` 里的「all」= 同一个 groupKey 内的全部，不是整张图全部。** 因此**没编组的卡（多 groupKey）用 all 也永远遮不全**：非本组的框必然落到 passive/outline 类。用户会误判成"all 没生效"，实际是分组没做。

**本机曾用过、现已弃用（2026-09-14 18:24 随 snippet 一并删除；18:33 广哥明确「还是不用换」）**：
```css
.true-recall-io-shape.is-mask-passive { fill: var(--interactive-accent) !important; fill-opacity: 0.45 !important; }
```
（比本组那个实心的淡、又能一眼看出是遮罩）。~~`is-outline-passive` 不动 —— 那是 solo「只遮一个」的设计语义~~（**这句 2026-09-15 已被新决定取代，见下面「★ solo 非本卡框改中灰蒙板」**）。
⚠️ **这层淡蓝是 AI 加的、不是插件原样**（广哥 2026-09-14 18:23 指出，当时是「点了 all 感觉没盖住」引发的）——原生在 moonstone 浅色主题下就是「约 5% 的黑」，压在图上几乎看不见；深色主题下才是偏亮的灰。**判断「all 有没有生效」不能以这层颜色为准，要看 groupKey 是否同组**（同组才都是 `is-mask-active`）。

- **决定（2026-09-14 18:33 广哥定死）：`is-mask-passive` 永久保持插件原生，不再改。** 原话「这个地方还是不用换」。→ **以后再遇到「点了 all 好像没全盖住」，不许加回淡蓝配色**：那是分组问题（靠 `TR自动编组` 守卫并组：编辑器里点 `All` 再保存），不是配色问题。（⚠️ `is-outline-passive` 是另一个类、另一件事 —— 2026-09-15 已单独改成中灰蒙板，见下条，**不与这条冲突**。）
- （历史）当时那个 snippet（`<vault>\.obsidian\snippets\true-recall-图片蒙板.css`，**2026-09-15 08:47 已移出 vault**）**只有一条真规则** —— `.true-recall-io-shape.is-revealed-active`；文件里出现的 `is-mask-passive` 字样只在注释的「已弃用」说明里。改动前可用「去注释后数 `.` 开头的选择器行」自检。

**要真正「提问时全遮」= all + 单组**：要把各框的 groupKey 并成同一个（并成一个 `is-mask-active` 组）才行。⛔ **原「唯一现役路径」已作废**（守卫 2026-10-12 退役）：在编辑器里点 `All` 再保存**不会**再自动并组。**当前做法 = 自己把各框并到同一组；或点 All 保存后数一遍卡数，多出来的用 `TR清理` 收回**（3.4 节已整段转为历史留档）。（旧的手动宏 `TR蒙板编组` 已于 2026-09-14 22:46 退役。）

**★ solo 非本卡框改中灰蒙板**（2026-09-15 广哥定；**⛔ 2026-10-12 起改由插件官方原生开关承担，本地 CSS 片段已删**）

- **他的原话与诉求**：「solo 情况生成的卡，提问的时候是蒙一个、其他的是一个框线……我觉得其他的也应该用一个颜色蒙住，因为往往这些部分会相互提醒。然后答案页面也只打开那一个蒙板。」⇒ 要求两条：① 非本卡框**实色蒙住**（别露出底图内容）；② **揭示后仍只揭开本卡那一个框**。
- **为什么改一条规则就能同时满足**：复习界面渲染 `Qc` 时写死 `revealSingleOnly:!0`（main.js @1013843），代入 `Fxe` ⇒ **solo 模式下「提问时的非本卡框」与「揭示后的非本卡框」是同一个类 `is-outline-passive`**。（只有 all 模式才分流到 `is-mask-passive`。）
- **落地物（历史方案，⛔ 2026-10-12 已删片段并移出 `enabledCssSnippets`）**：曾新建 snippet snippets 目录下那个「图片蒙板-solo 非本卡实色蒙住」CSS 片段（改前的备份 `~\.workbuddy\tmp\appearance.json.bak-20260915-solo-mask`）。规则全文留档：
  ```css
  .true-recall-io-shape.is-outline-passive {
      fill: var(--color-base-50) !important;   /* 中灰；--color-base-30 更浅 / 60 更深 */
      fill-opacity: 1 !important;
      stroke: var(--color-base-60) !important;
      stroke-width: 0.002px !important;
      opacity: 1 !important;                   /* 原生 .85 是元素整体透明度，会连填充一起削淡，必须压回 1 */
  }
  ```
- **刻意不动的地方**：① all 模式的 `is-mask-passive` 仍保持插件原生浅灰（上面 18:33 那条决定继续有效）；② 单框卡没有「非本卡框」，不受影响；③ 卡片面板 / 卡片详情里的揭示态走 `is-revealed-passive`（那边 `revealSingleOnly≠true`），也未改 —— 所以**复习界面与面板的观感会不一致**，是已知的、有意的。
- **想回退**：删掉 snippet 文件（或注释掉整块）即回到原生「只有一圈细框线」；`fill-opacity:0` 是同效果的轻量写法。**片段已于 2026-10-12 删除，本机现在就是这个「原生」状态。**

- **★ 官方替代路径（2.10.0 起，现行做法）**：判类函数 `UMe(ordinal, active, revealed, maskMode, revealSingleOnly, hideOtherRegions)` 的**第 6 个参数 `hideOtherRegions`** 为真时，非本卡框改走 **`is-mask-passive`**（实色中灰）⇒ **与本片段效果等价**。
  - **开关位置**：**图片蒙板编辑器侧栏**（与 `maskMode` 同一区），值随 `hideOtherRegions` 写进该卡自己的 regionsJson ⇒ **逐张卡**生效。
  - ⚠️ **存量卡不自动继承**：老的多框卡要**逐张打开编辑器勾选**；新建的卡也同理 —— 官方目前**没有**「默认全开」的全局设置项（`data.json` 里无此字段）。
  - ⚠️ 广哥据此于 2026-10-12 决定删除本地片段；将来若发现某批卡又露底图，先确认那张卡的编辑器里 `hideOtherRegions` 有没有勾上，别再去 snippets 目录找片段。

**`Fxe` 原文还原（2026-09-14 17:58 补，@524805）**：`const s = (t.ord === e)` —— `e` = `templateOrd`（本卡），`t.ord` = `Pxe(t, idx)` = `Number.parseInt(t.groupKey, 10)`（NaN 时退回数组下标）→ **`s` 就是「这个框属于当前这张卡吗」**。完整分支：

```js
revealed
  ? (s ? "is-revealed-active" : (revealSingleOnly ? (n === "all" ? "is-mask-passive" : "is-outline-passive") : "is-revealed-passive"))
  : (n === "all" ? (s ? "is-mask-active" : "is-mask-passive") : (s ? "is-mask-active" : "is-outline-passive"))
```

**`Solo`/`All` 不是编组开关 —— 两个维度正交**（2026-09-14 广哥问「点 all 不能自动编组吗」时定死）：`maskMode` 只管「**非本组**的框怎么显示」，`groupKey` 只管「出几张卡」。所以点 All **不改变卡数**，视觉上只是把别的组的框从「透明描边」换成「淡填充」——广哥看到的「all 建的只是背景颜色不一样」即此（那层淡色当时是本机 snippet 改的、**不是插件原样**；snippet 已于 18:24 删除，现在回到原生 `--background-modifier-hover`）。

- **写回时机（决定「能不能点 All 自动编组」）**：按钮 onClick 只改编辑器内部状态（`a(xt=>({...xt,maskMode:"all"}))`），**必须保存**才落进 note。编辑器保存段（`main.js` @162 打包段）逻辑：`_n = noteType.fields.some(f => 新fields[f] !== 旧fields[f])`，为真才 `flashcardManager.updateNoteFields(noteId, 新fields)`（`Om()` 序列化时 `maskMode` 与 `groupKey` 一并写出）。→ **任何「自动编组」只能挂在保存之后，做不到「按钮一点就编组」**。
- ⛔ **已落地落法（2026-09-14 广哥点名要「自动」，但已于 2026-10-12 随 `TR自动编组` 一并退役、只作留档）**：当年是不挂按钮、挂**保存** —— Scripts 目录下那个「自动编组」用户脚本（宏名 `TR自动编组`、`runOnStartup:true`）在 `flashcardManager.updateNoteFields` / `createNote` 外面包一层**前置改写**：判定「图片蒙板 + `maskMode==="all"` + 框数>1 + groupKey 不止一种」就把全部 groupKey 统一成**现有最小编号**，再交给插件自己的 reconcile。完整机制、判据、边界与实测见 3.4 节。⇒ **现在没有任何脚本做这件事**，「点 All 自动编组」这个能力**当前不存在**。
- **为什么当初写「不建议」而现在这么做**：当初的顾虑是「每次保存都静默 `bulkSoftDelete` 多余卡」。用户明确「点 All 就是要编组」之后，把触发面收窄成**只在 all 这一支**动手（solo 全程零介入）、只在多组时动手（幂等）、并把「框 N 个 / 卡 X→Y」写进日志与 Notice。副作用（多余卡软删，可还原）仍在，但已绑在他自己的显式意图上，且留了 `AUTO=false` 的观察模式。

## 八、复习面（回答页）能放什么、不能放什么（2026-09-14 源码级）

### 1. 渲染结构

`kq({card, isAnswerRevealed, onOpenSourceNote, presetName, ..., typeIn, audioPath})` 按卡型分支：

- **image-occlusion 分支**（`M = cardType==="image-occlusion" && !!ioImagePath && !!ioRegionsJson`）：
  ```js
  d("div", {class:"true-recall-review-card-container ..."}, [
      d(id, {imagePath, regionsJson, templateOrd, revealed:isAnswerRevealed, revealSingleOnly:true, expandable:true}, card.id),
      d(pee, {card, isAnswerRevealed, presetName, presetOptions, leechThreshold, onPresetChange, onOpenSourceNote})
  ])
  ```
  → **问题面与回答面都是同一个图片组件 `id()`，只是 `revealed` 不同**；`card.question` / `card.answer` **完全不参与渲染**。
- cloze / basic / reversed 分支才渲染 `La({content, field:"question"|"answer", ...})`（= `MarkdownRenderer`）——**文字挖空卡的"卡面 Extra 链接"就是靠这个位**。

### 2. 回答页底部那块（`pee`）长什么样

```js
function pee({card, isAnswerRevealed, presetName, presetOptions, leechThreshold, onPresetChange, onOpenSourceNote}){
  return isAnswerRevealed ? d("div", {class:"ep:flex ep:flex-col ep:items-center ep:gap-4 ep:pt-8"}, [
      d(Gx, {card, leechThreshold}),                                   // 评分条
      card.sourceNoteName && onOpenSourceNote
        && d(Z, {onClick:onOpenSourceNote, children:["Source: ", card.sourceNoteName]}),   // ← 唯一可点元素
      presetName && presetOptions && onPresetChange ? d(Ny,{...}) : d("span",{children:["FSRS: ", presetName]})
  ]) : null
}
```

- **没有 markdown 位、没有 userComment 位**——所以**蒙板卡回答页塞不进 `obsidian://adv-uri` 之类的自定义链接**。
- `id()` 组件 props 全集：`{imagePath, regionsJson, templateOrd, revealed, class, maskModeOverride, revealSingleOnly, expandable, onRegionClick}`。`onRegionClick`（选中时给 shape 挂 click + `true-recall-io-shape-clickable`）**全库只出现 1 次 = 定义处，无调用方**，即复习面里遮挡框点不动。
- 另外还有个全卡型通用的 **user comment 条** `Iq({comment, onEdit, onRemove})`：`comment` 存在才渲染，**内容是原样纯文本**（`children: t`，`whitespace-pre-wrap`），**不渲染 markdown、不可点**。

### 3. `Source:` 链接的真实行为

- 复习弹窗绑定：`onOpenSourceNote: () => this.handleOpenSourceNote()`：
  ```js
  handleOpenSourceNote(){ let r=this.review.getCurrentCard();
    if(!r||!r.sourceNoteName){ K().warning("Source note not found"); return }
    let n=this.resolveSourceFile(r);
    n ? this.app.workspace.openLinkText(n.path,"",false) : K().warning(`Source note "${r.sourceNoteName}" not found`) }
  ```
  → **只开笔记文件，不带行号/子路径，不定位**。
- `sourceNoteName` / `sourceNotePath` 不是库里存的列，而是 `enrichCard()` 现算：`sourceUid` → `findPathByUidSync(uid)` → 命中文件的 `basename` / 相对路径。**所以蒙板 note 只要 `source_uid` 对得上源笔记 frontmatter 的 `flashcard_uid`，`Source:` 链接就会显示。**
- **精确落行只认 `source_text`**，机制是字符偏移 `indexOf` 不是行号：
  ```js
  // requestSourceHighlight → 源笔记 CM6 扩展
  let s = this.view.state.doc.toString().indexOf(r.sourceText);
  if(s===-1) return;
  l = [Decoration.of({from:s, to:s+r.sourceText.length, className})];
  r.mode==="jump" && l.push(EditorView.scrollIntoView(s, {y:"center"}));
  ```
  调用点：**卡片面板**的 `onOpenSource: S => S.sourceText ? h(S) : m()`（h = 开文件 + `requestSourceHighlight(path, sourceText, "jump")`）、**卡片列表项悬停**预览。**复习弹窗不走这条路。**
- **本机实测数据**：图片蒙板 note 的 `source_uid` **有值**（`98d8dc8d`），`source_text` 为 **NULL**。→ 结论：回答页能看到可点的 `Source: 皮亚杰感知运动阶段汇总 1`（开整篇）；要**精确跳到「那张图所在行」**需另行解决：
  - 路线 A：给该 note 补 `source_text` = 那行 `![[images/xxx.png]]` 原文（注意 `flashcardManager` **没有** `updateNoteSourceText` 接口；store 层 `store.notes.update(id,{sourceText})` 支持）。补完**卡片面板的 Open Source 与悬停预览会精确高亮定位**，但**复习弹窗仍只开文件**。
  - 路线 B（**2026-09-14 已落地**）：QuickAdd 用户脚本 `<vault>\Scripts\truerecall跳原图.js`，宏名 `TR跳原图`。做法见 §九。

## 九、回答页注入「跳到原图」链接（2026-09-14 实现）

**能做的根据**：卡片对象上**直接挂着图片路径** —— `card.ioImagePath`（值形如 `images/xxx.png`，vault 相对路径）；同一对象还有 `card.sourceNotePath` / `card.sourceNoteName` / `card.templateOrd`。复习面渲染处即 `d(id,{imagePath:t.ioImagePath, regionsJson:t.ioRegionsJson, templateOrd:t.templateOrd, revealed:e, revealSingleOnly:!0, expandable:!0}, t.id)`（@556533）。所以「当前遮的是哪张图、出自哪篇笔记」拿得到，剩下只是定位行号。

### 0. 三类卡分别跳到哪 —— 按图名反推 + 入口记录（**2026-09-15.2 起，`.4`/`.9` 补入口记录**）

> 需求原话：「那个链接也要改吧，如果是 pdf 的，显示的链接要能跳到对应 pdf 的页；如果是嵌入的，就跳转到对应的 md 行。」

原先只有一条路 —— 在源笔记里反查「这张图所在的行」。但 `TR制作蒙板` 的 PDF 通道生成的图是 `images/<pdf基名>-p<N>.png`，**它不被任何笔记引用** ⇒ 反查必然落空，链接退化成「打开源笔记（未定位到图片行）」（实测日志 `源笔记里没找到图片行`，2026-09-15 09:58 那条）。

改用**按图名反推**（零存储、不改插件数据，**对已经建好的卡也立刻生效**）：

| 判据（依次） | 目标 | 链接文案 |
|---|---|---|
| ⓪ **有建卡入口记录** `k=pdf` | **打开 PDF 到第 N 页** | `跳到 PDF 第 N 页` |
| ① 源笔记里真有这张图（`![[images/xxx.png]]`） | 跳到那一行 | `跳到原图（第 N 行）` |
| ② 记录不是 `k=pdf`（`k=md` 或无记录），且**源笔记里有嵌入该 PDF 第 N 页的那一行** | 跳到那一行（`adv-uri` 带 line/anchor） | `跳到 PDF 嵌入行（第 M 行）` |
| ③ 同上但源笔记里没有嵌入行 | **打开 PDF 到第 N 页** | `跳到 PDF 第 N 页` |
| ④ 都不是 | 只打开源笔记（不猜行号） | `打开源笔记（未定位到图片行）` |

- **⓪「建卡入口记录」= 2026-09-15.9/.4 新增的机制**（`.true-recall/io-source.json`，`TR制作蒙板` 写、`TR跳原图` 读）。**为什么必须有**：图名固定 `<pdf基名>-p<N>.png`，只靠文件名分不清「从 PDF 视图建的」还是「从笔记里嵌入的 PDF 建的」，而二者想要的跳转目标相反（视图 → PDF 第 N 页；嵌入 → 那篇 md 的那一行）。派生规则只能偏向一边，于是「PDF 视图里右键建的卡」会被误跳到嵌入行（2026-09-15 广哥报：从 PDF 页右键建的卡，链接跳去了嵌入该页的 md 行）。
  - 文件形状：`{"v":1,"notes":{"<noteId>":{"k":"pdf"|"md","at":毫秒,"img":…,"pdf":…,"page":N}},"cards":{"<cardId>":"<noteId>"}}`；查找按 `card.noteId`（实测复习卡对象上**有** `noteId`，见 `tr-img-jump.log` 的 `卡键=` 判据），其次 `card.id` → `cards` 表。
  - **记录由编辑器返回值触发**：`openImageOcclusionEditor(...)` 的 promise 解出 `{cancelled, createdCards}`，从 `createdCards` 里取 `noteId`/`id` ⇒ **不必再包 `createNote` 补丁**（这正是当初没选「写 source_text」的原因之一）。
  - 写入走 `vault.adapter`（`.true-recall/` 是**点目录，Obsidian 不索引** ⇒ 读它必须用 adapter，`getAbstractFileByPath` 恒为 null）；超过 800 条按 `at` 裁旧。
  - ⚠️ **只对新卡生效**：改动前建的卡没有记录 ⇒ 仍走派生（②③）。2026-09-15 广哥明确选「**不回填**」旧卡（当时 10 张能按创建时间 100% 对齐入口，他没要回填）—— 所以任何「旧卡跳错」都要先问是不是这个原因，别急着改脚本。

- ②/③ 靠**图名即协议**：命名是 PDF 通道自己固定的（`<pdf基名>-p<N>.png`），所以「哪个 PDF、第几页」能从文件名反解出来 —— 不需要在建卡时写任何来源字段。PDF 用 `metadataCache.getFirstLinkpathDest(stem+".pdf", 源笔记)` 找，找不到再按文件名在 `vault.getFiles()` 里唯一匹配。
- **为什么 ② 优先于 ③**：②命中说明源笔记里就嵌着那一页（跳过去**就地看到该页**，比另开 PDF 更贴近「笔记即工作台」）；PDF 视图入口那种「源笔记里没有这一页」的情形才走 ③。
- ③ 的打开方式（**2026-09-15.3 改**，`.2` 不是这样）：**能就地翻页就绝不重挂视图** —— 先找已打开的 PDF leaf（`getLeavesOfType("pdf")` 里 `getViewState().state.file` 相同者）→ `setActiveLeaf` → **`view.applySubpath("#page=N")`**（原生 API，obsidian.asar 里就是 Obsidian 自己解析 `#page=` 的那条路：解析成 dest → `pdfViewer.applySubpath(dest)`）；退化顺序 `pdfViewer.currentPageNumber` → 才用 `setViewState` 兜底。**没有已开的 leaf 才 `getLeaf("tab")` 新开**（新开一个 PDF 本质就是正常打开）。**绝不用当前 leaf**（复习视图会被顶掉）。  - ⚠️ **为什么必须避开 `setViewState`**：`.2` 用 `setViewState({type:"pdf", state:{file,page}})` 统一处理，那等于把 PDF 视图卸载再装载 ⇒ **会重跑第三方插件的 load 补丁**。本机 PDF++ 0.40.31 补丁尾巴有一句**没做空值保护**的 `h.firstElementChild`（`h = this.findBar?.findNextButtonEl`，`h` 可能 undefined，前缀有 `?.` 后半句却没有）⇒ 每次重挂就抛 `TypeError: Cannot read properties of undefined (reading 'firstElementChild')`（`Uncaught (in promise)`，控制台位置 `plugin:pdf-plus:77:13055`）。**通用教训：改「同一视图的显示状态」时优先找原生就地 API，别用 `setViewState` 重挂** —— 重挂会连带触发所有第三方插件的视图生命周期补丁。
  - PDF 那个叶子页的报错**在 Obsidian ≥1.7 上实际无害**：那一行只做「把 find 按钮图标从 ↑ 换成 ↓」的兼容修复，而且前后有 `!requireApiVersion("1.7.0")` 短路 ⇒ 新版本来就跳过；崩溃点在补丁函数**最后一句**，PDF++ 需要做的挂载都已完成。
- `source_text` **仍然不写**（保持 NULL）：这条链路完全是只读推导，插件原生那条 `Source: <笔记名>` 不受影响。
- 判据日志（`.true-recall/tr-img-jump.log`）：`PDF 反推: png=… → pdf=… ｜ 嵌入行=… → 目标=…`。实测 2026-09-15 10:02:41 → `嵌入行=7 → 目标=md 第 7 行`（那张 p68 卡的源笔记正好嵌着这一页）。
- 离线测试：`scripts/test_tr_img_jump.js`（**23 项**，覆盖图名反推、页码抠取、嵌入行命中/页码不符不猜、渲染态别名、以及「普通图片那条老口径没被改坏」）。改脚本前先跑它。
- ✅ **三支都已真机走到**（2026-09-15 10:45 广哥自己点的）：①/② 见 `10:02:41 嵌入行=7 → 目标=md 第 7 行`；③ 见 `10:45:42 已注入 → 跳到 PDF 第 72 页` + `10:45:44 打开 PDF: 复用已开的 leaf → …科目一单选题.pdf 第 72 页`、`10:45:36 打开 PDF: 新 tab → …作文万能模版课.pdf 第 25 页`（复用与新开两条都通）。

### 1. 三个锚点（都可源码溯源）

| 用途 | 锚点 | 依据 |
|---|---|---|
| 找复习视图 | `[data-type="true-recall-review"]`；命中不到时退回 `.true-recall-review` | 前者：插件自己就这么用（@3090629），常量 `Ui="true-recall-review"` 即 viewType，Obsidian 会给 leaf-content 打 `data-type`；后者：渲染出的根节点 class 就带它（@570824 `De("true-recall-review ep:relative …")`）。class 命中多个时**只保留最外层**，避免嵌套容器重复注入 |
| 判断已揭示 + 找插入容器 | 容器内「以 `Source: ` 开头且无匹配后代」的最小元素，取其父节点（`pee` 的 `ep:flex-col` div） | `pee` 只在 `isAnswerRevealed` 时渲染，其中 `Source:` 是唯一可点元素（@555298） |
| 退化锚点 | `.true-recall-io-render-frame` / `.true-recall-io-render` | `id()` 组件的稳定语义类 |

### 2. 取「当前卡」

**首选：Obsidian 视图实例上的官方方法（2026-09-14 修正，早先写法是错的）**

```js
app.workspace.getLeavesOfType("true-recall-review")   // li 的 view
  → leaf.view.getCurrentReviewedCard()                // 源码 @579430：getCurrentReviewedCard(){return this.review.getCurrentCard()}
```

★ **会话对象挂在「视图实例」上，不在 plugin 实例上。** 早先写的是"遍历 plugin 实例找带 `getReview` 的对象"，实测返回「会话对象: 未找到」—— 16:55:06 那条日志就是证据。`view.review` 也可直接 `view.review.getCurrentCard()`。

**四级兜底**（前一档拿不到才退下一档）：

1. 上面这条视图 API（`typeof view.getCurrentReviewedCard === "function"`）。
2. plugin 实例上的会话对象（鸭子型：`typeof o.getReview === "function"` → `getReview()` → `getCurrentCard()`）。
3. **vnode 属性**：Obsidian 渲染用 **Preact**，DOM 元素上的私有键是 `__k` / `__c` / `__v`，**`__reactFiber$` / `__reactProps$` 根本不存在** —— 早先按 React 写的 fiber 兜底等于没兜底。Preact vnode 沿 `__` / `__r` / `return` 向上找 `props.card`。
4. 纯 DOM（完全不碰插件内部）：源笔记名 ← 「`Source: xxx`」那行文字；图片路径 ← 容器里 `<img>` 的 `src` 反解（`app://local/<绝对路径>` 或 `app://<vaultid>/<相对路径>`，再减掉 `vault.adapter.getBasePath()` 得 vault 相对路径）。

可用字段：`ioImagePath` / `sourceNotePath` / `sourceNoteName` / `templateOrd` / `id`。

⚠️ **两个必须自己动手才发现的坑**：

- **诊断日志必须每轮落盘。** 原脚本的 `flush()` 只在 `main()` 结束（= 注册观察器那一刻）调一次，之后 `sync()` 的每次结果都只 push 进内存数组、**永远不写盘**。所以日志里只有 `[init]` 那一行，看下去像"脚本没跑"，实际是"跑了但看不到"。**常驻型脚本的日志要在每轮同步后落盘**（本次改成 `sync` 的 `finally` 里 `void flush()`，并给 `lines` 加上限 400 行防膨胀）。
- **重跑脚本要能热更新。** 原来靠 `globalThis.__trImgJumpInstalled` 做"只注册一次"的闸门 → 改完脚本重跑会走"已存在，只做一次同步"分支，新逻辑不接管。改成**代次**：`GEN = (globalThis.__trImgJumpGen||0)+1`，观察器回调与 `sync()` 开头都判 `globalThis.__trImgJumpGen !== GEN` 即 return，旧代自动沉默。

### 3. 点击与 href

- 点击**自己实现**：`editor.setCursor({line:n-1,ch:0})` → 按 DOM 实测位置滚动。**不依赖 FakeLink 的任何设置项**。
- **打开策略（2026-09-14 17:50 补，广哥要求"文件已经在 tab 里开着就地定位、别新开"）**：三级判定 —— ① `workspace.activeLeaf.view.file.path === 目标` → 原地不动，直接定位；② 否则在 `getLeavesOfType("markdown")` 里按 `getViewState().state.file === file.path` 找 → 命中就 `setActiveLeaf(opened,{focus:true})` **复用**（先等 120ms，`view.editor` 仍为空才补一次 `openFile` 兜底）；③ 都没开 → 才 `getLeaf(false)` + `openFile`。**判据口径与 FakeLink `openFileOnly`（`main.ts` @793-799）一致**。
- **对照：FakeLink 侧本来就有复用** —— `openFileOnly` 先找已打开的 markdown leaf，命中就 `setActiveLeaf` 复用，找不到才 `getLeaf`。设置项 `jumpOpenInNewTab`（**默认 true**）**只影响"文件未打开"那一种情形**（UI 原文 `When the target file is not already open, open it in a new tab`）。所以行链接若出现"又开了一个 tab"，先确认目标笔记当时是不是真的没打开；把这个开关关掉 = 未打开时也复用当前 tab，**代价是当前 tab（复习视图）会被目标笔记顶掉**，不建议。
- ★ **最大的坑：href 绝不能写成 `obsidian://adv-uri`（2026-09-14 17:2x 定位）**。本机装着广哥自己写的 FakeLink，它在 `workspace.containerEl` 上注册的是**捕获阶段**监听（`fakelink/main.ts` @1061-1075）：只要 `href.startsWith('obsidian://adv-uri')` 就 `evt.preventDefault(); evt.stopImmediatePropagation();` 然后自己 `jumpToLine`。**捕获阶段的 stopImmediatePropagation 会让元素上的 `onclick` 永远收不到事件** —— 症状是"点得动、也确实跳了，但日志里一条跳转记录都没有"（本次日志 192 行全是注入记录、跳转 0 行，而用户确实点了并跳了）。对策：`href="#"`，真 URI 存 `data-tr-uri`（中键走 `onauxclick` 自己 `window.open`）。**复用旧 `<a>` 元素时必须无条件把 href 压回 `#`**：判重只看 `data-tr-target`，只改 href 不触发重绑，旧元素会一直带着 adv-uri。
- **滚动**（广哥两次实测"看不到完整图片"后重写）：
  1. **先 `setCursor`** —— 不可省：CM6 虚拟滚动下，没滚到那一行附近，图片 widget **根本不会被渲染**，DOM 里就找不到 `<img>`。
  2. 再**多轮覆盖式校正**（8 轮，首轮 150ms、后续每轮 220ms）：每轮重测 `<img>.getBoundingClientRect()` 与滚动容器矩形，`scrollTop = clamp(scrollTop + delta − PAD)`（PAD = 24px），连续两轮 `|after − PAD| ≤ 3` 才收工。**必须多轮**：图片加载完才知道真实高度，CM6 量完高度还会自己再动一次滚动条，单次设置必被覆盖。
  3. 找不到 `<img>`（源码模式 / 未渲染）时**也不要用居中**：改用含 `img` 的 `.cm-line` 的 `scrollIntoView({block:"start"})` —— 居中对"被图片撑高的行"只会露一角。
- ⚠️ **匹配 `<img>` 必须解码 URL**：Obsidian 给本地图片的 src 是 `app://local/<percent-encoded 绝对路径>`，**中文文件名会被编码成 `%E7%9A%AE…`**，拿未解码的 basename 去 `indexOf` 永远匹配不到 —— 这正是"改了代码却和改之前表现一模一样"的原因（每轮都掉进退路）。两侧都做 `decodeURIComponent` + 反斜杠归一 + 去 query/hash + 小写再比；先比全名，再退化比"去掉扩展名的主干"。
- 滚动容器：**先从 `<img>` 向上找第一个真正可滚的祖先**（`overflowY` 为 auto/scroll 且 `scrollHeight > clientHeight`），再退 `.cm-scroller` → `.markdown-preview-view` → `contentEl`。编辑器与阅读视图通吃。
- 日志：每轮都 `flush()` 并打印 `delta / after / scrollTop / max / 图高 / 视口高`；脚本开头打印 `version=`（常量 `VERSION`，改脚本就 +1）—— **确认"跑的是哪一版"永远看日志，不要靠猜**。
- 实测尺寸（2026-09-14）：源图 `images/皮亚杰认知发展四阶段对比.png` = **1387×672 px**，编辑器里显示宽度约 700–1000px → 显示高仅 340–490px，**远小于视口高（约 800px）**。所以"看不到完整图片"从来不是图太大，而是**滚动位置滚过头**。
- 对照：FakeLink 自己的 `jumpToLine`（`main.ts` @814）的滚动策略是 `const center = safeLine >= 15;` 然后 `scrollIntoView({from:{line,ch:0},to:{line,ch:0}}, center)`。第 7 行 → `safeLine = 6` → `center = false`（nearest），对"被图片撑高的行"会滚过头。
- ★ **"超高行"的通用改法（2026-09-14 已落地：广哥自己改的 `main.ts`，AI 只读核对、未动文件；FakeLink 仓库 `~\OneDrive\桌面\fakelink`）**：
  - **实际落地位置**：`jumpToLine` 尾部（`main.ts` **@849-853**）在 `scrollIntoView` 之后加一行 `this.alignTallLine(view, safeLine);`；新方法 `alignTallLine` 在 **@856-882**（含判据注释）。`resolveLineByAnchor`（@753）、`openFileOnly`（@792）、捕获拦截（@1061）、协议处理（@1092）**都没动** —— 改动面就这一处。
  - **为什么必须自己算**：Obsidian 只给 `Editor.scrollIntoView(range, center?: boolean)`（`obsidian.d.ts` @2536）——**一个布尔**，要么居中要么"最小滚动使其可见"（目标在下方=贴底边）。对超高行两个都不对：贴底边只露下沿、居中上下各切一半。`Editor.getScrollInfo()`（@2515）**只返回 `{top,left}`，没有视口高度**，所以高度只能从 DOM 取。
  - **取 CM6 EditorView 用公开 API，不碰私有属性**：`EditorView.findFromDOM(el)`（`@codemirror/view` 导出，`main.ts` 顶端**已经 import 了 EditorView**）+ `cm.lineBlockAt(pos)` → `{top, height, bottom}`。**本机先例**：`obsidian-outliner/main.js`（@49897 `getEditorViewFromHTMLElement` 里用 `EditorView.findFromDOM`；@44838 与 @90657 用 `lineBlockAt(...).top/.height/.bottom`）—— 即本机 Obsidian 上这条路径实测可用。**不要用 `(editor as any).cm`**。
  - **判据**：`block.height > cm.scrollDOM.clientHeight * 0.8`（超高行）**或** `block.top < cm.scrollDOM.scrollTop`（行首落到视口外）→ `cm.scrollDOM.scrollTop = block.top - 16`；否则**什么都不做**，普通行行为一字不变（零回归面）。要跑两轮（+250ms），图片加载完高度会变。
  - **收益面**：所有 `adv-uri` 行链接一次受益（文字挖空卡的 Extra 链接、本脚本注入的"跳到原图"、任何手写/导出的行链接）。改完本脚本那 8 轮滚动校正可退化成"只负责注入链接"。
  - **构建链路**：`npm run build` = `tsc -noEmit -skipLibCheck` + `esbuild.config.mjs production`，`outfile:'main.js'` 落在**仓库根目录，不自动进 vault** → 要手动把 `main.js` 复制到 `<vault>\.obsidian\plugins\fakelink\` 再重载插件。发版走打 tag（`.github/workflows/release.yml`，Node 20 + `npm ci` + `npm run build` + 附 main.js/manifest.json/styles.css）。
  - **两份 main.js 已比对**（2026-09-14 17:33 复核）：仓库版与 vault 版（`<vault>\.obsidian\plugins\fakelink\main.js`）**SHA256 完全相同**（`20ACC125…D090B`，均 271223B）→ 新代码已同步进 vault。构建产物 `outfile:'main.js'` 落在**仓库根目录、不自动进 vault**，本地流程是手动复制过去；若 Obsidian 自己往 vault 那份追加 `/* nosourcemap */`，会出现 1 行差异，属正常。链路上的**生效条件**是重载插件（设置里关开，或 Ctrl+R 重载窗口）——只覆盖文件不重载，跑的还是旧代码。
  - `Editor` 是 `export abstract class`（`obsidian.d.ts` @2403），`scrollTo(x?, y?)` @2531 可直接用；但**优先直接设 `cm.scrollDOM.scrollTop`**，坐标系与 `lineBlockAt().top` 完全一致。

### 4. 状态

- 脚本已写、语法通过，宏 **`TR跳原图` 已写入** `<vault>\.obsidian\plugins\quickadd\data.json`（2026-09-14 14:00:43，`type:"Macro"`、`command:true`、**`runOnStartup:true`**，指向 `Scripts/truerecall跳原图.js`；写入时共 19 个 choices，已自动备份）。挂载脚本：`~\.workbuddy\tmp\add_jump_macro.py`（`json.loads` → append → `dumps(indent=2)` 整文件回写 + 自动备份；**不要再用字符串插值拼 JSON**，上次括号配平算错过）。
- ⚠️ **"必须趁 Obsidian 关闭才写"这条已被实测修正**：QuickAdd 只在启动/重载读一次配置，**但不会主动回写**——所以 obs 开着写也是安全的（本次 14:00:43 写入、14:06 复查 mtime 未变）。真正的坑是另外两个：① 写完之后**用户打开 QuickAdd 设置改任何一项**，它会把内存里的旧 `choices` 整份序列化回写、冲掉新宏；② 写配置的**时间晚于 obs 启动**，则本次会话按名字找不到该宏。
  判断"这次会话到底加载没有"：比 `data.json` 的 mtime 与 obs 进程启动时间（本次 obs 起于 13:54:42，而宏写于 14:00:43 → **当前会话没加载**，需关/开 QuickAdd 插件或下次冷启动）。取进程启动时间：本机 PowerShell 工具返空，改走 `tasklist /FO CSV /NH` 取 PID → Python `ctypes` `OpenProcess(0x1000)` + `GetProcessTimes`，FILETIME 减 `116444736000000000` 除 `1e7` 得 Unix 秒。**别用"挂后台监听等 obs 进程消失再写配置"这一招**（本次实测 600s 白等超时）：用户的重启多为 Ctrl+R 重载窗口，**主进程不退出**。
- 实测落点校验：源笔记 `临时/皮亚杰感知运动阶段汇总 1.md` 第 7 行 = `    ![[images/皮亚杰认知发展四阶段对比.png]]`；脚本按「行含图片 basename 且含 `![[` 或 `<img`」命中该行。
- **2026-09-14 16:55 首跑不显示链接，根因是取卡失败**：运行时日志只有 `[init] 未揭示或无锚点，移除注入`，而取卡走的是错的 plugin 路径 + 根本不存在的 React fiber 键 → `imagePath` 恒空 → 被判为「非蒙板卡」直接把注入撤掉。已按「九.2」四级兜底重写，并补上「每轮落盘」+「代次热更新」。**取卡失败的表现是"什么都不显示"、不报错 —— 排查第一步永远是看日志里那句 `card=有/无 img=(空)`。**
- 宏可用性已实测：**`TR跳原图` 本次会话能执行**（16:55:06 有运行记录，`params` 含 `app/quickAddApi/obsidian/abort/variables`），说明 QuickAdd 已加载它，不必再纠结「配置写入晚于启动」那件事；脚本内容改动**只要重跑一次宏即可生效**（每次 `vault.read` 重读）。
- 脆弱点：锚点靠 `Source: ` 那块的结构，插件改版会失灵（表现 = 不显示链接，**不会损坏卡片**）。

### 5. 已实测的库内实况（`local.nosync/true-recall-*.db`，只读查询，**2026-09-14 13:57 快照**）

| note id | 建卡时间 | maskMode | regions（归一化 x 位置） | groupKey | note 状态 | 卡状态 |
|---|---|---|---|---|---|---|
| `18223fbe…` | 13:10:30 | all | 1 rect（x≈0.07 左） | `"0"` | 已软删(13:18) | 1 张已软删 |
| `9fa0620c…` | 13:15:53 | all | 1 rect（x≈0.54 右） | `"0"` | 已软删(13:18) | 1 张已软删 |
| `42a6c432…` | 13:21:26 | all | 2 ellipse（x≈0.54 / 0.77 右） | `"0"`,`"1"` | 活 | 2 张**均**已软删(13:22) |
| `616a5b75…` | 13:47:24 | solo | 2 rect（x≈0.07 / 0.29 左） | `"0"`,`"1"` | 活 | 2 张**均**已软删(13:50) |
| `3f2be3d9…` | 13:48:21 | all | 2 rect（x≈0.54 / 0.79 右） | `"0"`,`"1"` | 活 | 2 张**均**已软删(13:50) |
| `3cf2893a…` | 13:52:05 | solo | 2 rect（x≈0.08 / 0.29 左） | `"0"`,`"1"` | 活 | 2 张**均**已软删(13:54) |
| `b2240660…` | 13:52:58 | all | 2 rect（x≈0.54 / 0.78 右） | `"0"`,`"1"` | 活 | 2 张**均**已软删(13:54) |

- 7 条全指向同一图 `images/皮亚杰认知发展四阶段对比.png`，`source_uid` 均为 `98d8dc8d`（= `临时/皮亚杰感知运动阶段汇总 1.md` 的 frontmatter `flashcard_uid`）→ **一条源笔记下挂了 7 条蒙板 note**。
- **每一组「画两个框」都是 2 个 groupKey = 2 张卡**，正好印证 3.1 节：不并组就不是「一块蒙板」。
- 两个值得注意的现象：① 建卡后约 1~3 分钟，一对卡**同时**被软删（13:50 删一对、13:54 删一对）；② 归属明显**左右交替**（左组 / 右组轮流）——像是在反复试「两个区域」的效果。截至 13:57，**活 note 5 条、活卡 0 张**。
- 推论（**已于 16:50:12 被实测证实**；当时用的是现已退役的手动宏 `TR蒙板编组`）：`TR蒙板编组` 在这种情况下跑，`reconcileImageOcclusionCards` 发现「现有活卡集合为空」→ 给每条 note **新建** 1 张活卡。实际结果：5 条 note 全部 `[0,1] → [0,0]`、各新建 1 张活卡（`state=0`），全库活卡 `0 → 5`。所以**先清理掉多余的重复 note、再编组**，结果才干净 —— 见 3.3 节 的「顺序不能反」。

### 6. 16:51 快照（编组跑完之后的实况，可作为对照基线）

| note id | 建卡时间 | maskMode | regions | groupKey | 活卡 |
|---|---|---|---|---|---|
| `42a6c432…` | 13:21:26 | all | 2 ellipse（右） | `"0"`,`"0"`（**已编组**） | 1 张（16:50 新建，未复习） |
| `616a5b75…` | 13:47:24 | solo | 2 rect（左） | `"0"`,`"0"` | 1 张（同上） |
| `3f2be3d9…` | 13:48:21 | all | 2 rect（右） | `"0"`,`"0"` | 1 张（同上） |
| `3cf2893a…` | 13:52:05 | solo | 2 rect（左） | `"0"`,`"0"` | 1 张（同上） |
| `b2240660…` | 13:52:58 | all | 2 rect（右） | `"0"`,`"0"` | 1 张（同上） |

- 两个 1 框 note（`18223fbe` / `9fa0620c`）仍在软删状态（13:18 删）。**5 条活 note 指向同一张图、各自 1 张卡 = 复习队列里 5 张近似重复卡**——**已于 18:22 清理完毕**（见下）。
- 五条的身份便于辨认：`42a6c432` 两个**椭圆**在右侧；`616a5b75` 与 `3cf2893a` 两个矩形在左侧（几乎一样）；`3f2be3d9` 与 `b2240660` 两个矩形在右侧（几乎一样）。
- **18:22 清理终态（广哥「我都在测试、还没真正用，你看着删吧」→ AI 自行决定）**：全库 `活 note` 从 8 → **1**、`活卡` 从 4 → **2**、孤儿 0。保留的是 `7312342b…`（17:51:47 建，`all` + 2 框 `[0,1]` = 2 张卡），其余 7 条（6 条原本就没活卡 + `8dfe7909` 这条 solo）先删卡、再交由 `TR清理` 软删。保留理由是它正好是**给 `TR自动编组` 守卫准备的第一份测试样本**（`all` + 多分组 → 一保存就该并成 1 张卡）。
- **顺带确认的库状态（18:20 快照）**：`notes` 共 380 条，其中 `builtin-cloze` 369 条**全部已软删**、`builtin-basic` 1 条已软删、`builtin-image-occlusion` 10 条（8 活 + 2 已删）。即**整个 True Recall 库当时只剩蒙板测试卡**，与「都在测试」一致；cloze 那批的删除是当天上午三次清理（262 条 10:58、52 条 11:19、52 条 12:22）的结果，属预期、不是故障。

### 7. 「为什么得先跑一次 `TR跳原图` 宏（首次装探针）」——宏是扳机，链接是日常用法；**冷启动 / 重载会自动跑，不是每次手动**

- 脚本**不会自己启动**：Obsidian 没有"自动跑我的脚本"这种机制，QuickAdd 宏就是那个**扳机**。跑一次宏 = 执行脚本 = 注册一个 `MutationObserver`；从此它盯着复习界面，揭示答案后自动把「跳到原图」那行插进去。
- 分工：**宏跑一次（装探针）→ 之后每次点那行字（真跳转）**，不需要每次跳转都跑宏。
- 宏已开 `runOnStartup:true`，**冷启动 / 重载 obs 会自动跑**；只有"配置写入晚于本次启动"这种一次性情况才要手动 `Ctrl+P → TR跳原图`。脚本内容改动**重跑一次宏**即生效（QuickAdd 每次都 `vault.read` 重读脚本文件）。
- 版本确认：日志第一行的 `version=` 与脚本里的 `VERSION` 常量比对即可。
- **两种模式（脚本顶部常量 `MODE`，当前 = `"inject"`）**：`inject` = 注册观察器常驻注入（日常用法，链接自己出现）；改成 `"jump"` = 不常驻，跑一次只对**当前这张卡**跳一次（想用命令面板代替点链接时才用，改完要重跑宏）。
- **症状排查（广哥 2026-09-14 17:35 问「不都是我自己点链接吗」）**：复习页底部只有 `Source:` 与 `FSRS: Default`、没有「跳到原图」→ 链接是脚本注入的、插件原生没有。**先看 `<vault>\.true-recall\tr-img-jump.log` 里有没有「=== TR跳原图 开始 ===」这一轮（带时间戳）**，别预设"重载后宏没跑"：
  - **2026-09-14 更正**：旧版此处写「被 `Ctrl+R` 重载窗口清掉后需重跑一次宏（重载不触发 `runOnStartup`）」——**两头都错**。源码里 `runOnStartup` 是在 QuickAdd 的 `onload` 中注册的（`layoutReady ? i() : onLayoutReady(i)`），`Ctrl+R` 整窗重载 ⇒ 插件重新 `onload` ⇒ 启动宏**会**跑；实证就是 `22:07:20` / `22:35:58` 两次三个常驻宏在同一秒各写一条启动记录（批量装载，非手动）。所以 **重载不会让宏消失**。
  - ⇒ 若日志里**有**这一轮的「开始」记录、页面却仍没链接，问题在**注入判据**（`[dom]` 那几行：容器命中 / `锚点=无` / 未揭示），不在宏有没有跑；若日志里**压根没有**这一轮，才去查宏注册与 `runOnStartup`。

### 8. 启动警告 `Ignoring inability to install OPFS sqlite3_vfs`（无害，别去修）

- 原文：`plugin:true-recall:914 Ignoring inability to install OPFS sqlite3_vfs: The OPFS sqlite3_vfs cannot run in the main thread because it requires Atomics.wait().`
- 成因：插件的 SQLite WASM 支持多种 VFS，其中 **OPFS**（Origin Private File System）那一种内部用 `Atomics.wait()` 做同步等待，而 `Atomics.wait()` **在主线程被禁用**（只允许在 Worker 里）。插件在主线程初始化 → WASM 侧打印这条 warning 并**忽略该 VFS**，换其他 VFS 继续。关键字是 "Ignoring"，不是 error，不影响任何功能。
- 持久化实测正常：库文件在 vault 内 `.true-recall/local.nosync/true-recall-x1naa2u0.db`（1.0 MB，mtime 随使用刷新），同目录有 `.bak`，`backups.nosync/` 下还有 gz 备份（最近一次 16:54:45）。
- 结论：**没有开关可修，也不需要修**；它跟本 skill 的任何改动无关，属插件初始化 SQLite 时的固定输出。

### 9. 开弹窗时报 `NotAllowedError: Sharing constructed stylesheets in multiple documents is not allowed`（跨插件，无害）

- 完整栈（广哥 2026-09-14 17:49 贴的控制台原文）：`Uncaught NotAllowedError … at eval (plugin:advanced-canvas:6281:31)` ← `e.tryTrigger` ← `e.trigger` ← `t.openPopout` ← `t.openPopoutLeaf` ← `eval (plugin:true-recall:162:59603)` ← `Bs`。
- **不是 True Recall 的错**：TR 只调了 Obsidian 公开 API `workspace.openPopoutLeaf()`。`Bs` = 闪卡编辑器窗口（`jn.canOpenPopout()` 为真走 popout，否则 fallback `new Dp(t.app,t,e).openAndWait()` 内嵌模态）。任何插件开 popout 都会走同一条 `openPopoutLeaf → window-open` 路径。
- **报错方是 Advanced Canvas（本机 v7.0.0，也是上游最新版，2026-08-26 发布）**：`color-palette-canvas-extension` 在 `init()` 里注册 `workspace.on("window-open", … updateCustomColorModStyleClasses)`（`advanced-canvas/main.js` **@6279-6282**）；该函数遍历 `windowsManager.windows`，对未登记的 document 执行 `doc.adoptedStyleSheets = [...doc.adoptedStyleSheets, sheet]`（**@6310**；全文件只有 **@6296/@6310** 两处碰 `adoptedStyleSheets`）。Chrome 规定一个 constructed `CSSStyleSheet` 只能被一个 document adopt，这种**整体赋值**只要数组里含已在别处注册过的 sheet 就抛 `NotAllowedError`。
- **影响 ≈ 0**：异常在 Obsidian `Events.tryTrigger`（栈里在 `trigger` 内层）被吞掉 → TR 弹窗照常打开，复习与卡片数据毫发无损；代价仅是 Advanced Canvas 的自定义画布颜色在**新弹出的那个窗口**里没注入。@6310 抛错时后续 `styleSheets.set`（@6311）未执行，**不留脏数据**，下次 openPopout 重走一遍。
- **触发入口有两个，不止一个**（2026-09-14 18:25 广哥贴第二条栈后核实）：
  - ① `window-open`（注册在 **@6279-6282**）—— 开 popout 时触发，低频。
  - ② **`css-change`（注册在 @6283-6286）—— 任何样式变动都触发，高频**：加/删 CSS 片段、换主题、`obsidian-style-settings` 改任一项配置。
  - 实测栈：删掉 snippet 文件那一刻 → Obsidian `FSWatcher._handle.onchange` → `e.reconcileFile` → `readSnippets` → `loadSnippets` → `css-change` → @6285 回调 → @6310 抛错；同一批还有一条来自 `obsidian-style-settings`（`Jt.setCSSVariables` → `Jt.setConfig`）→ 同样落到 `css-change`。**两条栈都是 @6310，说明 `if (!sheet)` 新建分支每次都进（Map 里压不住那个 doc）。**
  - 由此可反推：**Obsidian 有 watcher 盯着 `.obsidian/snippets`，片段增删会自动重载**（不必手动 Ctrl+R 才生效）。
- **触发频率**：一次事件报一次，不循环刷屏。TR 的四个弹窗入口会触发第一条路 —— 闪卡编辑器 `Bs` / 卡片类型编辑器 `Au` / 笔记类型管理器 `lH` / AI 助手窗口 `vE`（均在 `main.js` line 162 打包段）。
- **不可修（两层都关不掉）**：① 上游无更新（v7.0.0 即最新，2026-08-26 发布）；② **Advanced Canvas 自己也没有关掉这个扩展的开关** —— `ColorPaletteCanvasExtension.isEnabled() { return true }`（**@6274-6276**）硬编码，且它注册的是全局 `workspace.on("css-change"/"window-open")`，跟画布有没有打开无关。TR 侧同样无开关（`jn.canOpenPopout = () => ao()` 只判"是否桌面"）。处置 = 忽略，或临时禁用整个 Advanced Canvas。
- **别误判成"删 snippet 删坏了"**：删片段只是按下了这个 bug 的开关，把片段加回去照报不误；后果仍只有一条 —— 该窗口的自定义画布颜色没注入。
- **若想彻底静音（本机可做，属改第三方插件，需广哥点头）**：`advanced-canvas/main.js` **@6308-6312** 那段包 `try { … } catch {}`，并把 `this.styleSheets.set(doc, sheet)` 也放进成功路径 —— 首次 adopt 失败后 Map 有记录，第二次起不再进新建分支 → **每个新 document 只报一次即静音**，行为与现状等价（现在 sheet 本来也没 adopt 成功）。代价：Advanced Canvas 每次升级都要重打这个补丁。
- 应急处置口径：与「九.8」的 OPFS 警告同类 —— **看着吓人、实际无害**，**不要为它去改 TR 或本 skill 的任何脚本**。

## 十、Anki 的图片蒙板与本插件的关系（2026-09-14 源码实证，广哥提问引出）

### 1. 结论先说：**`.apkg` 的导入与导出都没有做 IO 转换**

- **导入**：转换器 `t0.convertCard()` 只有 3 个分支 —— `n.type===1` → cloze、`type===0 && tmpls.length>1 && ord===1` → reversed、其余 → basic（`main.js` @3577xxx，`convert`/`convertBasicCard`/`convertClozeCard`/`convertReversedCard`）。`Pm.matchBuiltin()` 也只认三种模型：`Front/Back`+1 模板 → `builtin-basic`、`Front/Back`+2 模板 → `builtin-basic-reversed`、`type=1` 且 `Text/Extra` → `builtin-cloze`。**Anki 的 IO 模型字段名是 `Occlusion`/`Image`/`Header`/…，一个都对不上** → 走 `createFromAnkiModel()` 新建一个自定义笔记类型（字段/模板照抄 Anki），产出的卡是普通卡，**蒙板形状完全不解析**。
- **导出**：`MC.buildModelsJson()` 只生成 3 个 Anki 模型（Basic / Basic (and reversed card) / Cloze）；`insertNotesAndCards()` 里凡是非 cloze 且非 reversed 的卡一律按 `BB`(Basic) 落库，`flds = question \x1f answer`。IO 卡因此被导成**普通 Basic 卡**，正文是 `{{Image}}` 与 `{{Image}}{{Regions}}` 的渲染结果 —— 图片路径那串文字 + 一大坨 `Regions` JSON。
- ⇒ 别指望用 `.apkg` 在 Anki 与本插件之间搬运 IO 卡，两个方向都是退化的。要搬只能自己写转换（见「十.4」）。

### 2. 但两边的数据模型是**同构**的（这才是"怎么写卡"的关键）

| 概念 | Anki（23.10+ 内置 IO） | True Recall |
|---|---|---|
| 笔记字段 | `Occlusion`｜`Image`｜`Header`｜`Back Extra`｜`Comments`（`kind = Cloze`） | `Image`｜`Regions`（`builtin-image-occlusion`，`type = 0`） |
| 形状存放 | `Occlusion` 里一串 cloze 标记：<br>`{{c1::image-occlusion:rect:left=.2325:top=.3261:width=.202:height=.0975}}`<br>形状规格 = `shape:prop=value:…`，`rect`/`ellipse`/`polygon`/`text` | `Regions` 一个 JSON：<br>`{"version":1,"maskMode":"solo","regions":[{id,x,y,w,h,groupKey,shape,label}]}` |
| 分组 | **同一个 cloze 号** = 一张卡的多个形状（编组入口 = 编辑器 "Group selection"）；`{{c1,2::…}}` = 一个形状同时挂两张卡 | **同一个 `groupKey`** = 一张卡的多个形状 |
| 卡数 | = 不同 cloze 号的个数 | = 不同 `groupKey` 的**种数**（`ace()` = `[...new Set(regions.map(groupKey))].sort()`，每个一个 `templateOrd`） |
| 两种模式 | Hide All, Guess One｜Hide One, Guess One | `maskMode:"all"`｜`"solo"`（`r2()` 只认这两个值，默认 solo） |
| 坐标 | 图内比例（`.2325`） | `x/y/w/h` 0~1 小数；**写 0~100 也认**（`Wl()`：`t>1 ? t/100 : t`，再夹到 `[0,1]`） |
| 形状种类 | rect / ellipse / polygon / text | 只有 rect / ellipse（`t2()` 把其余**一律当 rect**） |

- 一句话：**TR 的 `groupKey` 就是 Anki 的 cloze 号，`maskMode` 就是 Anki 那两种 IO 模式** —— 作者是照着 Anki 抄的，连"All 模式下非当前组实心遮住"都与 Anki 的 Hide All 一致。
- 只有两处不如 Anki：① 不存 `polygon`/`text`（静默退化成矩形）；② 没有"一个形状挂多张卡"的写法（Anki 的 `{{c1,2::…}}`），要复现只能写两条 region 各带一个 groupKey。

### 3. 于是「怎么写这个卡」有三条路

1. **编辑器手画**（现状流程）：右键图片 → 制作图片蒙板 → 画框 → **点 `All` 保存** ⛔（~~守卫并组 ⇒ 1 张卡~~ 守卫已退役，不会自动并组；保存后自己数卡数，多出来的用 `TR清理` 收回）；要一张图出多题就「一图一题」：**对同一处重复「制作蒙板」**（或同一张图多嵌几行，二者等价），每次 1 组。
2. **直接写 note 字段**（等价于在 Anki 里手写 `Occlusion`）：
   - `Image` = `images/xxx.png`（`Ja()` 也认 `![[…]]` / `![](...)` 写法）；`Regions` = `Om(definition)` 那个 JSON 形状；
   - 保存时插件调 `reconcileImageOcclusionCards()`：按新的 groupKey 集合**建缺的卡 / 软删多的卡 / 保留已存在的 `templateOrd`**（= 保留复习进度）；
   - 参考实现（**已退役**，2026-09-14 22:46）：`Scripts/truerecall蒙板编组.js`（走 `updateNoteFields`，改**已存在**的 note；备份在 `~\.workbuddy\tmp\tr-io-group-backup-20260914\`）。
3. **从 Anki 的 IO 转过来**（可行，尚未写）：解析 `.apkg` 的 `Occlusion` 字段 → 每个 `{{cN::image-occlusion:<spec>}}` 变一条 region（`cN-1` → `groupKey`；`left/top/width/height` **直接当** `x/y/w/h`，Anki 那侧本身就是比例，不用换算；`rect`/`ellipse` 直用，`polygon` 只能取外接矩形）→ 拼 `Regions` JSON + 把图片落到附件目录 → 建 `builtin-image-occlusion` note。若真要做，起点是 `Ub.parseAndConvert`（= `a0.parseApkg` + `t0.convert`）之后**加一个 IO 分支**。

### 4. 两个容易误会的点（都已在源码/库里核实）

- `cards` 表**不存 question/answer**（只有 `note_id`/`template_ord`/FSRS 各列），内容每次从 note 字段渲染 → **改 `Regions` 就是改卡面**，不存在"卡面要另外同步"的问题。
- `ioGroupKey = String(templateOrd)`、`ioImagePath = Ja(fields.Image)`，卡题面文本被覆写成 `Image occlusion N`（N = `templateOrd + 1`）→ 这就是卡浏览器里 IO 卡显示成 "Image occlusion 1" 的原因。
- 本轮库内实况（只读快照）：活 note 里 IO 只剩 `57737bc2`（`maskMode:"all"`、2 region 都是 `groupKey:"0"` → 1 张活卡）；另有 `7312342b`（`all` + `groupKey 0/1` → 2 张卡）等一批软删记录。**自定义 note type 一个都没有** → 本库从未导入过 Anki 的 IO 笔记。

## 十一、删卡与空壳 note（2026-09-14 源码级，广哥问「怎么完整的删卡」引出）

### 1. 结论：完整删卡 = 两步，插件的每条删除路径都只做第一步

1. **第一步·删卡**：所有入口最终都只给 `cards.deleted_at` 打时间戳（软删、可还原）。入口五条：
   - 复习界面 `Shift+1` / 右键 `Delete card`（`Nx` → `Mi([card.id])`）；
   - 卡片面板 `⋯ → Delete all cards`（`Mi(该文件全部卡的 id)`，带 Undo）；
   - 卡片面板 `⋯ → Delete note & cards`（同上 **+ `fileManager.trashFile(md)`**，confirm 写着 *This cannot be undone*）；
   - 手动删/回收 `.md` → 插件 `O6.handleFileDeletion` 自动 `bulkSoftDelete(该文件全部卡)`，并 `notification.cardsDeleted(n)`；
   - API：`DELETE /cards/:id` / `POST /cards/bulk-delete` / `POST /cards/remove-from-note`。
2. **第二步·清空壳**：**插件代码里只有 `disableNoteReview`（关 note-review）一处调用 `notes.delete`** → 上述五条路径**没有一条**会删 `notes` 行 → **删完必然留空壳 note**（活 note、0 活卡）。要干净就得再跑 `TR清理`（或 `tr_db_cleanup.py`）。**2026-09-14.3 起 `TR清理` 一趟还顺带按判据重建统计** —— 删卡连带软删的 `review_log` 会让 `daily_stats` 过期，这一步正好把面板上残留的复习数字一起校准（见 `true-recall-stats.md` §七）。
3. 所以「Delete note & cards」是唯一"一步到位"的入口，代价是**把源笔记本身丢进回收站**；图片蒙板/挖空卡的 note 就绑在你那篇学习笔记上，**别拿它当清理按钮**。

### 2. ⚠️「删一张会连带删另一张」——对图片蒙板多组卡尤其致命

`Mi` → `deleteBatchWithCascade(ids)`，删除集合 = 每个 id 的 `collectCascadeDeleteIds(id)` 之并。单个 id 贡献：

- 它自己；
- **cloze 卡才有的**一支：同源 uid + 同 `clozeTemplate` 的全部活卡（`getClozeSiblings`）；
- **`reverseOf` 为空时**（cloze / basic / **图片蒙板**都为空，只有 reversed 卡带 `reverseOf`）一支：`getCardByReverseOf(id)` 的实现**不是**找配对的 reverse 卡，而是 **`SELECT ... WHERE c.note_id = ? AND c.template_ord != ? LIMIT 1`** —— 也就是"**同 note 里换一张**"。

后果：

- 图片蒙板 note 有 2 张卡（`groupKey 0/1`）→ 删任意一张，**两张全没**，再删第二张返回 404（命中上面第 3 支；此前记的"note 级联"就是这个现象，解释已更正）。
- 图片蒙板 note 有 **≥3 张卡** → 删一张只掉 `2` 张（它自己 + 随机一张同 note 的），**剩 `N-2` 张**、掉哪张不可控。
- `Suspend` / `Bury` 走 `getGroupSiblingIds`，三分支与上面完全同构 → **对图片蒙板卡同样是"一次动两张"**。
- ⇒ **多组图片蒙板卡别在复习界面单张删**；要清就整条清（`POST /cards/remove-from-note {source_uid}`，可撤销）。
- **★ 但「只想去掉某一题」有精确解：回编辑器删掉那个框再保存**（2026-09-15 补，源码级）—— 编辑器删框 `sX()` = `{...t, regions: t.regions.filter(r => r.id !== e)}`，**纯 filter、不重排 `groupKey`**（只有新画框才走 `qA()` = 当前最大值 + 1，所以删完会留下编号空洞，如 `[0,1,2]` 删中间那个 → `[0,2]`）；保存走 `reconcileImageOcclusionCards`，按 `templateOrd` **保留交集、软删多余** ⇒ **删哪个框就精确删掉哪张卡**，且全程不经过 `Mi`、**不连带**。**这是唯一一条"条目级精确删卡"的路子**，与"删卡"是两套机制，别混。
- 库内实证（2026-09-14 20:24 只读快照）：8 条 IO note 全为空壳、IO 卡 40 张全部软删；多个 note 的卡在同一秒被批量删（如 20:23:39 一次带走 note `78486a27` 的 ord 0/1/2 与 note `70aa530c` 的 ord 0）→ 与"卡片面板 Delete all cards = 按文件批量删"一致。

### 3. 浏览界面（card browser）**并不例外**（2026-09-14 广哥追问「browse 界面删不会连带吧」→ 会）

1. **全插件只有一处删除实现**，所有 UI 入口共用：`Mi`（命令类，`type:"card:delete"`、`description` = `Delete card` / `Delete N cards`）→ `execute()` → `flashcardManager.removeFlashcardsByIdsWithDetails(cardIds)` → `cardRepository.deleteBatchWithCascade(ids)` → 对每个 id 取 `collectCascadeDeleteIds(id)` 的**并集** → `bulkSoftDelete(并集)`。
2. **浏览器那一处** = 选择工具栏组件 `hne`（`N selected` / `Select all N` / `Suspend` / `Unsuspend` / `Unbury` / `Forget` / `Change type` / `Move` / `Delete`），其 `Delete` 就是 `new Mi(选中的 id 数组)`（`l = Array.from(selectedIds)`）。⇒ **浏览器里单张删照样连带**，和复习界面 / 侧边面板 / Local API 一模一样。
3. **唯一不连带的情形**：该 note 总共只有 1 张卡 —— ③ 支的 `WHERE template_ord != ?` 查不到行。
4. **"掉哪张"其实有准头**：`getCardByReverseOf` 的 SQL 没有 `ORDER BY`，SQLite 按存储顺序返回第一行 → 只读模拟（库里 4 卡 note `e6d427d3`）结果显示：删 `ord0` → 带 `ord1`；删 `ord1/2/3` → **都带 `ord0`**。所以"不可控"实际上多半就是 **`ord 0` 那张**（用 `GROUP_PLAN` 编组后 = 第 1 组那张）。**这属实现细节、不保证**，不要依赖。
5. **但浏览器仍是对的地方**：它**一行一张卡**（IO 多组 = 多行 `Image occlusion 1/2/3`），所以**把整条 note 的卡全部勾上再删** → 并集正好覆盖整条 note，干净、可控、不留残卡。复习界面只给当前那一张，做不到这一点。
5.1. **库内实测复现（2026-09-14 21:05:52，广哥亲手操作 + Local API 快照）**：3 卡 note `a20e6d0b`（`ord 0/1/2`、`maskMode=solo`，由图片行 `%%io:1,2,1%%` 生成 —— 该语法属 v2，**v3 已从脚本移除**）在浏览器删 **`Image occlusion 2`（= `ord 1`）一行** → 快照显示**同一毫秒软删 `{ord 1, ord 0}`**（`deleted_at` 完全相同）、存活 `ord 2`、note 行未删（活卡 1 / 总卡 3）⇒ 第 4 条的"删非 0 号必带走 `ord 0`"在真实库复现，**连带方向由 `ord 0` 承接**（不是随机）。浏览器里 `N` 号卡 = `ord N-1`，别按显示号猜序号。
6. **浏览器的两个坑**：① **跨 note 混选会被放大**（选 note A 的 1 张 + note B 的 1 张 → 各带一张 → 实删 4 张）；② **`Select all N` = "当前查询命中的卡"**，若筛选/搜索把某条 note 的卡拆到查询外，删的时候仍会从查询外把兄弟拉进来 —— **不等于安全**。
7. **浏览器比复习界面可控的一面**：工具栏的 `Suspend` / `Unsuspend` / `Forget` 走 `bulkSuspend` / `bulkUnsuspend` / `bulkForget(选中的 id)`，**只动选中的卡、不连带**；而复习界面的 `Suspend` / `Bury` / `Forget` 走 `getGroupSiblingIds`（IO 同构 → 一次动两张）。
8. **一句话判据**：**「删」在哪个界面都一样会连带；「暂停 / 埋葬 / 忘记」只有复习界面会连带。** 要绝对干净地清一条 note：`POST /cards/remove-from-note {source_uid}`（显式传该 note 全部卡 id，可撤销），或在浏览器里**整条全选**再删。
9. 另注：浏览器里还有个 `Remove N orphaned cards?` 按钮（`getOrphanedCardIds()` → `new Mi(ids)`），那是清"源文件已消失"的孤儿卡，同样走级联 —— 但孤儿卡的兄弟也是孤儿，所以这里无副作用。
10. **⚠️ 删卡能 Undo，但 Undo 只复活卡、不复活 note（2026-09-14 补核，与"清空壳"直接相关）**：`Mi` 的撤销侧原文 `undo(e){for(let r of this.deletedCardsData) e.cardStore.set(r.id,r), e.cardStore.cards.restoreWithCascade(r.id)}` → `restoreWithCascade` 的 SQL 只还原两张表：`UPDATE review_log SET deleted_at = NULL WHERE card_id = ? AND deleted_at = ?` + `UPDATE cards SET deleted_at = NULL WHERE id = ?`，**从不碰 `notes`**。而撤销入口是常驻的（`CommandService` 持 `stack` / `redoStack`，有 `canUndo()` / `canRedo()` / `peekDescription()`；复习视图用 `newestUndoService([sessionCommandService, plugin.commandService], …)` 取"最新的那个"），删除提示 `cardsDeletedWithUndo` 也带一个 Undo 链接。⇒ **先跑 `TR清理`（notes 已软删）再按 Undo 把卡复活，就得到「活卡挂在已软删 note 上」的半残状态**。所以清空壳之前先确认没有待撤销的删卡动作；万一踩到，修复 = 把那几条 note 的 `deleted_at` 置回 NULL —— **`TR清理` 现成就有这条路**：建 `<vault>/.true-recall/undo-restore.flag` 再跑一次宏即进入还原模式（见 §十一.4 第 3 条），它还原的正是最近一批被清理的 note；只有更早的批次才需要照 `tr-cleanup-undo.jsonl` 手工置回。

### 4. 插件自带的三种「孤儿」，以及它为什么替代不了 `TR清理`（2026-09-14 广哥截图问「他是不是有这个功能」）

**有，功能真实存在**：设置 → `Database integrity` → `Check now`（实现是 `Ah` 类，挂在 `cardStore.integrity`）。但它查的「孤儿」和 `TR清理` 查的**不是一件事**。插件里「孤儿」共三种含义、三个互不相干的入口：

1. **设置 → Database integrity → Check now**（`Ah.check()`，三条 SQL 原文）：
   - `SELECT c.id FROM cards c LEFT JOIN notes n ON c.note_id = n.id WHERE n.id IS NULL AND c.deleted_at IS NULL` → 卡指向的 `notes` **行不存在**；
   - `SELECT n.id FROM notes n LEFT JOIN note_types nt ON n.note_type_id = nt.id WHERE nt.id IS NULL AND n.deleted_at IS NULL` → note 指向的 `note_types` **行不存在**；
   - `SELECT rl.id FROM review_log rl LEFT JOIN cards c ON rl.card_id = c.id WHERE c.id IS NULL AND rl.deleted_at IS NULL` → 复习日志指向的 `cards` **行不存在**。
   - 动作 `Ah.repair()`：三类各自 `UPDATE ... SET deleted_at = now`（**软删**、一个事务、逐 id）。手动路径会先 `createBackup()`（失败只 `console.warn` 仍继续）；**加载时的自动路径不备份**。
2. **卡片浏览器（Card Browser）的孤儿筛选 + `Remove N orphaned cards?`**：判据 `getOrphanedCardIds()` —— 卡**没有 `sourceUid`**，或 `sourceUid` 在 vault 里**找不到对应 `flashcard_uid` 的文件**（源笔记被删/改名/去掉 uid）。动作是 `new Mi(ids)`（同一套级联软删），**带 Undo**（`cardsDeletedWithUndo` → `commandService.undo()`）。筛选态由 `orphanedOnly` 驱动（面板里显示成 `(orphaned)`）。
3. **`TR清理`**（本机 QuickAdd 宏，脚本 `<vault>\Scripts\truerecall清理.js`）：判据 `SELECT n.id FROM notes n WHERE n.deleted_at IS NULL AND NOT EXISTS (SELECT 1 FROM cards c WHERE c.note_id = n.id AND c.deleted_at IS NULL)` —— note 行在、note type 也在，但**名下已经没有活卡**（空壳 note）。动作 `store.notes.delete(id)`。
   3.1. **`2026-09-14.2` 升级（广哥「按你的建议改」）**：① **就绪闸**取代旧的「全库活卡 = 0 就中止」+ `force-clean.flag` 哨兵 —— 优先 `store.isReady()`（= `isLoaded && db.isReady()`，插件自己封的组合判据），退化用 `store.isLoaded` + `store.db.isReady()`，**两条都拿不到**才退回旧保守判据；② **避让闸** —— `store.persistenceHalted`（**只有 `haltPersistence()`、没有 resume**）、后台备份、云同步 / 设备同步进行中一律等 3×1.5s 后仍忙则中止；③ **删前写 undo 清单** `<vault>/.true-recall/tr-cleanup-undo.jsonl`（JSONL，追加；**写不进去就不删**），并支持**还原模式**（建 `<vault>/.true-recall/undo-restore.flag` → 把最近一批的 `deleted_at` 置回空，跑完自动删 flag；插件无 notes 级 restore，走 `store.db.run("UPDATE notes SET deleted_at = NULL…")`，与 `cards.restoreWithCascade` 同写法）；④ 日志新增就绪判据 / `persistenceHalted` / `getPersistenceDebugInfo()` / undo 写入结果 / 类型分布。**判据与忙碌信号均已在源码核对过出处**（`isReady`、`persistenceHalted`、`getStatus().isBackupInProgress`、`coordinator.isSyncing.value`），离线测试台 `scripts/test_tr_cleanup.js` **57/57 PASS**。

两条硬结论：

1. **第 1、2 种都碰不到空壳 note，所以 `TR清理` 不可替代**：第 1 种的 ①② 用的是**物理行存在性**（`LEFT JOIN` 条件里**都没有** `n.deleted_at IS NULL` / `nt.deleted_at IS NULL`）→ note 被软删、note type 被软删都**不算**孤儿；空壳 note 的 `notes` 行与 `note_types` 行一直都在 → 两头都不沾。第 2 种只按"卡能不能找到源文件"筛**卡**，源笔记还在就一切正常，它也只软删**卡**、不软删 note。
2. **它只在库第一次加载时自动跑一次，之后永不再跑**：`cardStore.load()` 里固定调 `integrity.checkAndRepairOnce()`，但开头先读 `meta.integrity_checked`，**等于 `'1'` 就直接 `return 0`**，跑完（无论有没有修）写回 `'1'`。⇒ 静默、无提示、无备份地只在**首次加载**检查一次；之后再攒多少孤儿都不会自动跑，要手动点 `Check now` 才有第二次。
3. **一句话边界**：`Check integrity` 管的是**数据库指针悬空**（真损伤，多来自换机/同步/迁移残留），`TR清理` 管的是**正常使用攒出的空壳 note**（删卡副作用）。截图上那句 `Detect and repair orphaned cards, notes, and review logs` 指的是第 1 种，**不是**空壳 note。

顺带修正 §十一.1 第 2 条涉及的一处旧结论：

- `notes` 行的**软删**其实有 **2** 处 —— `disableNoteReview`（关闭 note-review）与 `integrity.repair`（本小节第 1 种）；**硬删（`DELETE FROM notes`）全插件 0 处**，且 `notes.delete()` 自身实现就是 `UPDATE notes SET deleted_at = ? WHERE id = ?`（软删）。
- 所以「插件永不**物理**删 note」仍成立；但那句"只有 `disableNoteReview` 一处会动 `notes`"要按上面收窄成"软删两处、硬删零处"。
- 附带一条：卡侧 `bulkSoftDelete(ids)` 会**同时软删这些卡的 `review_log`**（`UPDATE review_log SET deleted_at ... WHERE card_id IN (...)`），所以正常删卡不会攒出第 1 种③那类孤儿日志。

### 5. 替代路线：「一图一题」而不是「一图多组」（2026-09-14 广哥提出，源码核完，**成立且更稳**）

广哥的替代思路：需要多道题时**不在一张图上分多组**，而是**一张图一道题**（把图复制成不同文件名），每张图只留 1 个组（或单框 solo）。核结论：**成立，且删卡安全性优于多组方案**。

1. **级联删除按 `note_id`、不按文件**。`collectCascadeDeleteIds(e)` 原文就三段：`let n=new Set([e])` → `if(r.cardType==="cloze" && r.clozeTemplate && r.sourceUid){ getClozeSiblings(...) }` → `if(!r.reverseOf){ getCardByReverseOf(e) }`。**唯一按 `source_uid` 撒网的那支被 `cardType==="cloze"` 硬挡住** ⇒ IO 卡（`cardType==="image-occlusion"`）永远进不去，**同一文件里的多张图不会互相牵连**。
2. **每张图 = 独立 note**：`createImageOcclusionNote` → `createNote({noteTypeId: en, fields:{Image, Regions}, sourceUid})` → `notes.create(n)`（每次新 uuid）。**全插件没有按 `Image` 路径查重的逻辑**（`findImageOcclusionNote` 0 命中、`json_extract(… Image)` 0 命中）⇒ 同一张图点 N 次 IO = N 条独立 note、N 张独立卡，各自 `Regions` 互不干扰。
3. ⇒ **每张图只有 1 组时该 note 只有 1 张卡**，`getCardByReverseOf` 的 `WHERE c.note_id = ? AND c.template_ord != ?` 查不到行 → **删卡永不连带**。推论比方案本身更值钱：**单卡 note 下「删」在任何入口都一样安全**（浏览器 / 侧面板 / 复习界面 `Shift+1` / Local API），不必再依赖浏览器里小心勾选。
4. **真正的代价是卡名**：`_s()` 里 `u = a && c ? "Image occlusion " + (templateOrd+1) : "Image occlusion"`（`a` = `fields.Image`，`c` = 解析出的 regions）——**卡名只带 `templateOrd`，不含图片名**。所以 N 张单组卡在浏览器 / 侧面板里**全显示 `Image occlusion 1`**，源笔记列也相同，名字上无法区分；而"一图多组"因 `templateOrd` 不同反而有 `1/2/3` 编号可辨。**这才是两种方案的真实取舍**（不是删卡安全性）。
5. **「取不同的名字」不是插件要求 —— 2026-09-14 v3 之后连"建议取"的理由也没了**：同名技术上也能各自建卡、互不干扰，删卡同样不连带。**曾经**唯一的硬理由是本库 `TR自动编组` 的保存守卫按 **basename** 匹配图片行（同一文件里两行同名图会共用同一份 `%%io:…%%` 方案 → 可能误改两张卡的分组），而**这条机制已随 v3 删除 `%%` 代码而消失**。现在同名的唯一代价只剩**人工辨认**（卡名不带图名，见第 4 条）⇒ 想同名就同名。
6. **改题入口**：`updateCardContent` 对 IO 卡直接抛 `Image occlusion cards must be edited in the image occlusion editor.`；要改只能 `openImageOcclusionEditor({mode:"edit", noteId, note})`，入口是复习界面（`handleEditCardModal`）、侧面板与浏览器（都经 `wne(cardId)` → 卡 → note → 编辑器）⇒ 即使同名，"改某一题"仍可用（先选中对应行）。
7. **对现有脚本的影响**（⛔ 历史记录）：`TR自动编组` v3 在"每图一组"下自然空转（单组图不满足"多组"判据）；若偶尔误画成 all + 多组，它的**唯一动作**（all + 多组 → 并一组）正好把卡并回 1 张，与"每图一题"自洽 ⇒ **别停这个宏**，它同时是"忘了点 All"时的兜底。
8. **⚠️ 由第 2 条推出的操作硬规矩：想「改某一条已有卡」时，只能用「编辑」入口，绝不能再点一次「制作蒙板」**（2026-09-14 二次源码核对补；⚠️ **限定在"改"的语境** —— 若是**故意要再加一道题**，重复制作恰恰是正解，见第 10.1 条）。add 模式在源码里是**无条件新建** —— 编辑器保存回调原文 `if(tt){ let Ut = …updateImageOcclusionNote(t.noteId, {imagePath:i, definition:o}) …; return } let Ar = …createImageOcclusionNote({imagePath:i, definition:o, sourceUid:Ot, createdVia:"manual"})`，其中 `tt` = 传入的 `noteId`，**只有 edit 模式才有值**；也**没有任何"该图已有卡"的提示**。更隐蔽的是初始画布：`lee(t)` = `t.mode==="edit" ? t.note.fields.Image : t.imagePath`、`cee(t)` = `t.mode==="edit" ? pa(t.note.fields.Regions) : Lm("solo")` —— **add 模式一律给一张"空定义"（`Lm("solo")`），根本不读旧 note**。所以对一张已有卡的图再制作一次 = 画布空白、看不见之前画的框、存完多出**整套重复卡**，两套并存互不覆盖。原生 IO 按钮（`qre`）与 `TR制作蒙板` v5 同形，都传 `mode:"add"`、都不带 `noteId` ⇒ **两者都踩**。这也正是那批空壳 note 的另一半来源：反复「制作 → 删卡」，每次制作都新建一条 note，删卡只软删 card。
9. **同名图在同一篇笔记里贴两次（或对同一处重复制作 N 次 —— 2026-09-15 复核二者等价，见第 10.1 条）：建卡与删卡都安全**（2026-09-14 广哥追问「不用改图片名吧」）。把同一张图嵌两次、各右键做一次蒙板 = **两条独立 note、两张独立卡**（add 模式无查重），每 note 1 张卡 ⇒ 删哪张都不连带 —— **这一层与"改不同文件名"完全等价**。历史上还有**两处按 basename 取首个命中行**的地方：① `TR自动编组` 的 `pickIoPlan`（读 `%%io:%%` 方案）—— **该函数已随 v3 删除整套 `%%` 代码，撞车点不存在了**；② `TR跳原图` 的 `findImageLine` —— `names.some(n => row.includes(n))` 取首次命中，**两张同名卡的「跳到原图」都指最早那处引用**（本库工作流里最早那处就是正文的阅读用图，所以正是想要的效果；只有"两处都想各自跳回"时才需要不同文件名）。**根因是数据层无从消歧**：IO 卡的 `source_text` 为空、`fields` 只有 `Image`/`Regions`，插件**不记录这张卡来自哪一行**。另外同名叠加"卡名只带 `templateOrd`"会让浏览器里彻底分不出谁是谁（见第 4 条）。
10. **广哥定下的工作流（2026-09-14 确立，此后按此走；同日 v3 已把 `%%` 代码真正删掉落地）**：图片蒙板改用 **一图一题** —— 要出多道题就**重复制作**同一张图的蒙板（**不必复制图片文件，也不必在笔记里多嵌几处**；2026-09-15 广哥实测提出、源码复核认定二者等价，见下方第 10.1 条），每次只放 1 组（或单框）；**两种等价形状**：① **同一处**右键「制作图片蒙板」做 N 次；② 在末尾连写 N 行完全相同的 `![[图A.png]]`、逐行右键。两种都得到 N 条独立 note、N 张独立卡（add 模式不看"这张图是否已有卡"，所以"制作几次 = 几张卡"，与文件名是否重复无关；磁盘上仍只有 1 个 png）⇒ **推荐形状 ①，笔记里不必多出那几行引用**。**放弃 `%%io:…%%` 多组方案** ⇒ 第 9 条的 `pickIoPlan` 撞行问题自然失效（该函数随后已在 v3 从脚本物理删除）。

10.1 **「同一处重复制作」与「多嵌几处」等价（2026-09-15 广哥实测提出，同日源码复核）**：两条都走 `createImageOcclusionNote` → `createNote`，每次新 uuid、无查重 ⇒ 生成的 note 与卡**完全同形**（同一 `Image` 路径、各自独立的 `Regions`），删卡同样不连带。差别只有两处、都不影响功能：① 笔记里的引用行数（形状 ① 只留正文那一行，更干净）；② 卡名 —— `_s()` 只带 `templateOrd`、不带图名，所以两种形状下 N 张卡在浏览器里**都显示 `Image occlusion 1`**，"换不同文件名"也换不来可辨认性（见第 4 条）。唯一要守的规矩仍是**每条 note 只留 1 组**，否则又变回多张卡、删卡会连带。

⚠️ **但「多组」不是 `%%` 带来的，是插件的默认行为 —— 这点必须记牢**（2026-09-14 广哥以为「不用 `%%` 就不会出现多组」，源码复核后纠正）：`YX()`（鼠标松手提交新框，`se` 处理器里调用）写死 `groupKey: RA(定义)`，而 `RA()` = **当前最大组号 + 1** ⇒ **每画一个框就是一个新组**；AI detect 同形（`detected.map(x => ({...x, groupKey: String(Ut++)}))`）。3 个框 = 3 组 = 3 张卡（`ace()` 按 `Mm()` 去重组号算卡数）。所以**「多个框组成一题」必须有人把组并回去**，`TR自动编组` 不是可有可无的安全网，**它就是「一图一题」的合并器，不能停**。
守卫的生效条件就一条（v3 之后 `planFields` 只剩这一个分支）：`if (maskMode !== triggerMaskMode) return null;`，其中 `TRIGGER_MASK_MODE = "all"` —— 即 **`all` + 多组才并，`solo` 下一律放行**。这条刻意如此：**`solo` 是"我要一张图出多题"的声明**，守卫不该插手（旧宏 `TR蒙板编组` 手动产出的多组正是靠 solo 放行；该宏已于当日 22:46 退役，但这条判据不变 —— 新建编辑器给的开局定义本来就是 solo）。
⇒ **一图一题的正确手势（⛔ 已随守卫退役作废，仅作历史记录）：画完所有框 → 在编辑器把 Mask mode 点成 `All` → 保存**，~~守卫会在入库前（`createNote` / `updateNoteFields` 两个入口都包了）把多组并成一组、只建 1 张卡，并到**最小组号**~~ ⇒ **现役做法：点 All 保存后自己数一遍卡数，N 张就用 `TR清理` 收回**（保留那张的复习调度与历史）。**若忘了点 All、停在默认 Solo，守卫不救，会得到 N 张卡** —— 修法 = 删掉多余的卡 → 编辑器点 `All` 重存（守卫接手并组）。（旧的手动宏 `TR蒙板编组` 已退役，不再有这个"事后补刀"入口。）**（若选了形状 ②）出题用的那几处重复嵌入统一贴到文章末尾**，正文只保留阅读用的那一处；形状 ①（同处重复制作）则根本不用动笔记 —— 两种形状下「跳到原图」都成立，是因为「跳到原图」的 `findImageLine` **从首行往下扫、返回第一个"含该 basename 且形如嵌入（`![[` / `[[` / `<img>`）"的行**（第 233-246 行），**取的就是行号最小那处**，所以只要阅读用那张在正文靠前位置，跳转必落正文、不会跳进末尾那堆卡片载体。两个配套事实：① 行号缓存键 = `笔记路径|图片路径|mtime`（`imageLineCache`，第 255 行），**正文增删行后 mtime 变 ⇒ 缓存失效重算，行号不会跳错**；② 卡面图片取的是 `fields.Image`（文件路径），**与嵌入位置无关** ⇒ 贴哪儿都不影响复习形态。若正文那处被删，跳转自动落到下一个命中（末尾那处），不会失效。
