---
name: "obsidian-link-line-sync"
description: '源笔记被编辑导致行号漂移后，需要重新同步下游 HTML / MD / 数据脚本里指向它的 obsidian:// 行号链接时先加载 —— 支持体检 dry-run、写回、人工 override。'
title: "obsidian-link-line-sync"
summary: '源笔记被编辑导致行号漂移后，需要重新同步下游 HTML / MD / 数据脚本里指向它的 obsidian:// 行号链接时先加载 —— 支持体检 dry-run、写回、人工 override。'
agent_created: true

---

# obsidian-link-line-sync

源笔记被编辑（增删行、软换行拆开、补内容）→ 之前生成的复习清单 / 链接页 / 数据脚本里
`&line=N` 跳行链接指错位置。本 skill 用文本相似度自动把漂移的行号重新对齐回去。

## 何时触发

1. 用户编辑/重排了某个笔记后说"链接页/清单/MD 里的行号要更新""笔记行变了，同步下链接"。
2. 用户怀疑某些跳行链接失效，要求"体检/检查一下哪些链接坏了"。
3. 用户生成了一批带 `obsidian://adv-uri?...&line=N` 或 `obsidianjump://jump?...&line=N` 链接的产物，源笔记之后又被改动。

## 不触发 / 注意

- 只动 `line=` 数值，**不修正路径**（路径错了不属于"行号漂移"）。
- 纯聊天答疑、不需要改文件时不触发。
- 产物是 Obsidian vault 之外的普通网页、无行号链接时不触发。

## 脚本与运行环境

- 脚本：`scripts/sync_note_lines.py`
- Python：必须用受管解释器 `~/.workbuddy/binaries/python/versions/3.13.12/python.exe`
  （避免污染用户环境；脚本已 `sys.stdout.reconfigure(utf-8)`，中文不乱码）
- 仓库根默认 `<vault>`；链接里的相对路径从 URI 的 `filepath=` / `p=` 解出后拼到根下。

## 模式（自动判断，也可 `--mode` 强制）

- `.html` / `.htm` → `html`：解析 `<a class="jump" href="obsidian...&line=N">P N</a>` 及普通 `obsidian://` 链接
- `.md` → `md`：解析正文里的 `[N](obsidian://...&line=N)`（显示文字=目标行号数字）
- `.py` → `pydata`：解析数据脚本里的 `(N, "文本"),` 元组（路径取自同文件 `append(("相对/路径.md", ...))`，前缀取 `BASE="..."` 常量或 `--base`）

## 标准工作流（务必先 --only 单篇验证，再放开全量）

```bash
PY="~/.workbuddy/binaries/python/versions/3.13.12/python.exe"
S="~/.workbuddy/skills/obsidian-link-line-sync/scripts/sync_note_lines.py"

# 1) 体检：只读，列出疑似失效（不动文件、不改任何东西）
"$PY" "$S" "<vault>/临时/科三数学-复习重点.md" --check

# 2) dry-run：报告会改哪些行（不落盘），先用人眼确认
"$PY" "$S" "<vault>/临时/科三数学-复习重点.html" --only 普通高中课程标准

# 3) 确认无误后真正写回（默认生成 .bak 备份）
"$PY" "$S" "<vault>/临时/科三数学-复习重点.html" --apply --only 普通高中课程标准
```

- 可一次传多个产物：`"$PY" "$S" a.html b.md c.py --apply`
- `--only SUBSTR` 可重复，只处理路径含该子串的源笔记（建议先单篇，再全量）
- `--override 关键字|旧行=新行,旧行=新行` 人工指定映射，绕过自动匹配（算法拿不准时用）
- `--force` 忽略 mtime 门控、强制比对所有笔记（仅产物是复制来的 / mtime 不可信时用）
- `--min-score 0.30` 自动接受的最低置信；低于列 UNMATCHED 待人工
- `--no-backup` 写回时不生成 .bak
- 退出码：0=全部成功；2=存在 UNMATCHED / ERROR（需人工 `--override`）

## 算法（为什么能自动对齐而不靠手填）

1. 产物条目是"整理/改写过的摘要"，与 md 原文行**不逐字相同**，不能直接字符串相等匹配。
2. 用 **字符 bigram 覆盖率 + 前 6 字锚点 + 首句互含** 给 (条目, 每一行) 打分。
   - 覆盖率用 `min(len(a),len(b))` 归一化（不是召回），否则内容更长的"表现/内容"子行会压过小标题行，落点漂到子行。
   - 首句互含是定位"小标题行"的关键（条目摘要横跨 小标题+子内容 两行）。
3. 条目按原文顺序整理 → 行号必然**递增** → 单调对齐 DP 求全局最优分配，纠正大量"局部相似"误配。
4. **相对判据**：只有当"新行明显比当前行更像"(差值 > 0.15) 或"当前行已经完全不像"(< 0.25) 才判为漂移，否则不动——避免把一份已同步的产物无谓改写。
5. **笔记级判据**：编辑一个笔记会让它的所有条目**集体偏移**而非零星几条。整篇平均增益 < 0.08 或新落点均分 < 0.45 → 认为该笔记没被编辑，一条都不动（误改比漏改危害大）。
6. **mtime 硬证据**：源笔记 mtime 不晚于产物 → 产物生成后笔记没动过，行号不可能漂，直接跳过（这是正常用法下零误报的根因）。

## 置信度与人工介入

- `HIGH`(≥0.60) / `MID`(≥0.40) / `LOW`：LOW 不自动改，列出来人工核对。
- 写回前务必看 dry-run 明细；`--check` 与 dry-run 都不改动任何文件。

## 实战踩过的坑（必读，重写同类脚本照此避坑）

- HTML 条目正文在 `<li>` 内，解析时取 `<li>` 去掉 `<a>` 按钮后的剩余文本；直接取 `<a>` innerText 只会得到 "P8"，毫无匹配价值。
- `rewrite_html` / `rewrite_md` 里 `entries` 是四元组 `(path,line,txt,span)`，**index 是位置**；`changes` 里的 `i` 也是 enumerate 序号——两者必须一致，否则 `span_of[i]` 取不到键直接 KeyError（已修）。
- 绝对阈值（如 fine_score < 0.25 就判失效）会把 143 条正确链接误报；必须用**相对判据 + 笔记级判据**。
- pydata 模式回写按 `(旧行号, 归一化文本)` 定位逐行替换；若数据脚本不是 `(N,"文本"),` 元组格式，需先改 `PY_ITEM_RE` / `PY_PATH_RE` 正则。
- `--check` 模式没有 mtime 门控时（加 `--force`）会测出大量"单条疑似"，那多是重写摘要的误报；看笔记级判据是否触发（"笔记级判据未触发…视为误报，跳过"）即可判断真伪。正常不加 `--force` 时 mtime 门控让它们全被跳过，体检结果干净。
