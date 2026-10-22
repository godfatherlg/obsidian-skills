---
name: obsidian-css-selector-debug
description: 写或调 Obsidian CSS 片段（snippets）时的类名取证与选择器判据。触发场景：CSS 片段写了不生效、要按「行类型／缩进层级／代码块／引用」给编辑器行上样式、怀疑行级类名记错、或要确认某个类名是否真实存在。核心手段是直接扫官方 obsidian.asar 取证，不靠记忆猜。
summary: '写或调 Obsidian CSS 片段（snippets）时先加载 —— 片段写了不生效、要按行类型或缩进层级给编辑器行上样式、怀疑行级类名记错、要确认某个类名是否真实存在。核心手段是直接扫官方 obsidian.asar 取证，不靠记忆猜。'

---

# Obsidian CSS 片段：类名取证与选择器判据

**铁律：不要凭记忆写行级类名。** Obsidian 的行类名有一半是运行时字符串拼接出来的，网上和记忆里流传的 `cm-list-N` 之类多为讹传。先在 asar 里取证，再写选择器。

## 1. 取证脚本

本机 Obsidian 装在 `<ObsidianInstallDir>\`，核心包是 `resources\obsidian.asar`（约 24MB，CSS 与 JS 都在里面）。直接二进制扫描即可：

```python
import re
from collections import Counter
b = open(r'<ObsidianInstallDir>\resources\obsidian.asar', 'rb').read()
t = b.decode('utf-8', 'replace')

# ① 某个类名是否存在（0 = 不存在）
print(len(re.findall(r'cm-list', t)))

# ② 枚举全部行级类名：JS 里行类是按 b += " line-HyperMD-xxx" 拼的
c = Counter()
for p in re.findall(r'b\+="((?:\s*line-[A-Za-z0-9-]+)+)"', t):
    for x in p.split():
        c[x] += 1
print(c)
```

带数字的后缀（`HyperMD-list-line-1`、`-2`…）是运行时 `.concat(Y)` 拼的，**asar 里搜不到字面量**，只能搜到 `line-HyperMD-list-line-` 这个前缀 —— 搜不到 ≠ 不存在。

## 2. 已知事实（v1.14.2 实证）

**行级类名全集**（除此之外没有别的）：

`HyperMD-list-line`、`-nobullet`、`-N`（N = 1..6）／`HyperMD-codeblock`、`-begin`、`-end`／`HyperMD-header`、`-line`、`-N`／`HyperMD-quote`、`-N`、`-lazy`／`HyperMD-table-N`、`-rtl`／`HyperMD-footnote`／`HyperMD-task-line`

- **`cm-list-N` 不存在**（旧 snippet 里常见；写了不报错，静默失效）。
- **没有任何跟缩进挂钩的行级类**。
- 列表缩进的实现：行内 span `.cm-indent`（`display:inline-block; min-width:var(--list-indent)`）做占位，宽度 `--list-indent: calc(var(--indent-unit) * var(--indent-size))`（默认 `0.5625em × 4`）。`.cm-indent` / `.cm-hmd-list-indent` 是**行内元素**，不是行类。
- **行首的普通空格在 DOM 里只是文本节点**，没有任何元素或类 —— 4 个、7 个都一样，**纯 CSS 选不中**（实测确认）。**Tab 缩进同样抓不到**：`.cm-tab` 元素实测不存在（2026-09-20 DevTools 定案，见下文高频判据第 11 条），Tab 缩进行 = 完全无类的裸行。所以「给缩进块上色」只有两条路：
  1. 依赖列表结构 —— `.cm-line.HyperMD-list-line-nobullet`（缩进续行，判据是缩进宽度 ≥ 标记宽度，统一 5 空格最稳）或 `.HyperMD-list-line-N`（嵌套层级）；
  2. 写 CodeMirror 扩展（`ViewPlugin` + `Decoration.line`）按行文本补类，覆盖所有空格缩进。
- 本机 vault `<vault>` 的 `app.json` 里 `useTab: false`（所以敲 Tab 键插入的是空格）。

## 3. 高频判据

| 想要 | 判据 |
|---|---|
| 4 空格缩进的续行 | `.cm-line.HyperMD-list-line-nobullet` |
| 第 N 级列表项 | `.cm-line.HyperMD-list-line-N` |
| 缩进块的块首行 | `.cm-line:not(<缩进集合>):has(+ .cm-line:is(<缩进集合>))` |
| 「上一行满足条件」 | 一律用 `:has(+ …)`（CSS 没有 previous-sibling，只能反向写） |

- `nobullet` 的语义正好是「有缩进、但没有列表标记」；**顶格的续行 Obsidian 直接不给任何类**，所以拿它当缩进判据不会误伤顶格行。
- `:has()` / `:is()` 在 Obsidian 1.14（Electron 30+ / Chromium 124+）可用。

## 4. 坑

1. **别给 `.cm-line` 加 `padding`**：缩进是靠 `.cm-indent` 内联占位撑的，行本身 padding 一改，文字与光标位置双双错位。要动只动 `background-color`。
2. **纯空格缩进（普通段落下面的续行）CSS 选不到**：那种行没有任何类。只有「列表项下面的续行」才带 `nobullet`。想统一，就把那行改成 `- ` 列表项。
3. **缩进式代码块必须前面有空行**才算（CommonMark：缩进代码块不能打断段落），否则那 4 个空格只是段落续行。
4. **snippet 文件常带 UTF-8 BOM**：ripgrep / Grep 类工具可能整份跳过。搜内容用 Python `encoding='utf-8-sig'`；改完复核 BOM 仍在。
5. 改完自检：`{}` 与 `()` 计数各自相等、旧类名零残留。
6. 多条规则特异性相同时**文件里靠后的赢** —— 排查「写了不生效」先看是不是被后面的泛化选择器盖掉（例：`.HyperMD-list-line` 会盖掉任何平级的细分规则）。
7. **多层视觉用特异性分层，别用 `!important`**：要「所有行有一层通用底色、其中一部分再叠一层强调色」时，写两条规则，让强调层的选择器特异性天然更高即可（例：通用层 `.markdown-source-view.mod-cm6 .HyperMD-list-line` = (0,3,0)，强调层 `.markdown-source-view.mod-cm6 .cm-line:is(...)` = (0,4,0)，块首行带 `:has()` = (0,6,0)）。后写的层覆盖前面的同属性，但 `border-radius` 这类**未被覆盖的属性会从通用层漏下来** —— 不想让它漏就在强调层重新声明或干脆去掉。

8. **`:has()` 不能嵌套**（Chromium / Edge 实测）：`:has(+ .x:has(.y))` 这种写法无效。更坑的是——**选择器列表里只要有一个选择器无效，整条规则会被丢弃**，所以把「好的」和「坏的」用逗号写进同一条规则，会一起失效。要表达「下一行里含某后代」，改用**后代选择器**（例：`:has(+ .cm-line span.cm-highlight)`，只留一层 `:has()`；**别拿 `.cm-tab` 当后代**——它实测不存在，见高频判据第 11 条），并且**一个选择器一条规则**。
9. **离线验证选择器命中**（比在 Obsidian 里反复试快得多）：写一份模拟 DOM 的 HTML，用 `msedge --headless=new --dump-dom` 跑，脚本里把 `getComputedStyle` 的结果塞进 `<title>`，就能一眼看出哪几行命中、哪条规则被丢弃。
   ```
   msedge --headless=new --disable-gpu --no-sandbox --dump-dom file:///C:/tmp/test.html
   ```
   Edge 路径 `C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe`（**本机实测只有上面这一条**，「`C:\Program Files\Microsoft` 下无 Edge 目录」；Chrome 同理，装在哪查哪）。

10. **取真实 DOM 的取样命令**（在 Obsidian 的 DevTools Console 里跑）：
    ```js
    [...document.querySelector('.cm-content').children].map(l=>[l.className,getComputedStyle(l).backgroundColor,l.innerHTML.slice(0,60)].join(' | ')).join('\n')
    ```
    **务必先把光标放到目标行** —— `.cm-content` 只含当前视口的行，否则会抓到完全不相干的区域（本次就抓错一次，白绕一轮）。输出里的「实际背景色」是判断「规则没命中」还是「snippet 没加载」的试金石。
11. **缩进在 Obsidian 里怎么才能被 CSS 看见（2026-09-20 DevTools 实测定案）**：
    - 缩进本身（空格数 / Tab）在 DOM 里**没有任何类**；**`.cm-tab` 元素实测不存在**（挂在缩进行上取样得 `cmTab=false`）⇒ 所有基于它的选择器都是死代码，别写。
    - **Tab 缩进行 = 完全无类的裸行**（连代码块都不是），CSS 永远抓不到。**别用 Tab 缩进做需要样式的块**。
    - **唯一能被识别的形态 = 列表项下面的空格续行**（拿到 `HyperMD-list-line-nobullet`）。判据是**缩进宽度 ≥ 标记宽度**：`1. ` 占 3 列 ⇒ 4 空格就够；`145. ` 占 5 列 ⇒ 要 5 空格（`145. ` + 4 空格时 Obsidian **一个类都不给**）。**统一用 5 空格最稳**（7 空格会让 `1. ` 的续行变成代码块）。
    - 「非列表行 + 下一行有缩进」要上色，只能靠 `:has(+ .cm-line:is(nobullet, -2~-6, codeblock))`；**非列表下的纯空格缩进无解**（非要它只能上 `ViewPlugin` 按行首字符补类）。

## 5. 落盘位置

本 vault 的 snippet 目录：`<vault>\.obsidian\snippets\`；启用清单在 `.obsidian\appearance.json` 的 `enabledCssSnippets`（里面可能残留已删除的文件名，Obsidian 静默忽略）。保存后 Obsidian 会自动热重载。
