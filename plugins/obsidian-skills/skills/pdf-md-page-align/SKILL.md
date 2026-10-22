---
name: pdf-md-page-align
description: 'Existing video/SRT-derived vault md + a newly added SAME-NAME PDF: align every numbered item to its real PDF page and inject `[[<basename>.pdf#page=N|pdf]]` next to the existing `[[<basename>.mp4#t=秒|视频]]` link, so the note becomes dual-coverage without re-authoring it. Trigger: user says "新加了同名pdf, 结合pdf重新总结", "这个md配上pdf页码", "给我的笔记补pdf链接", or any request to fuse a newly added PDF into an already-existing same-name .md built from video/SRT.'
agent_created: true
summary: '已有视频 / SRT 生成的 vault md，又新增了同名 PDF 时先加载 —— 把每条按真实 PDF 页码对齐并注入 [[文件名.pdf#page=N|pdf]]。'

---

# 已有 md + 新加同名 PDF → 逐条补 pdf 页链接（双链接融合）

## 何时用（与 `pdf-to-vault-summary` 的分工）

- `pdf-to-vault-summary`：PDF 是**唯一/主要源**，从零成文。
- 本 skill：md **已经存在**（由 mp4+SRT 生成，每条已有 `mp4#t=`），现在**新加了同名 PDF**，
  要求"结合 pdf 重新总结"。此时**不要重写全文**——把条目对齐到 PDF 页码、注入 `pdf#page=` 即可，
  再补几条 PDF 独有而视频没讲的考点。这样既省时又不丢已核对过的视频秒数。

## 流程

### 1. 抽取 PDF 文本（复用 pdf-to-vault-summary 的脚本）

```bash
PY="~/.workbuddy/binaries/python/envs/default/Scripts/python.exe"
"$PY" "$HOME/.workbuddy/skills/pdf-to-vault-summary/scripts/extract_pdf_text.py" "<PDF>" > "<TMP>/x.txt"
```

产物是 `===== PAGE N =====` 分块，后面所有页码都以此为准。

### 2. 写"章节窗口"配置（人工，关键一步）

对齐靠 **章节窗口 + TF-IDF 二元组打分**：先给每个 `##` 章节手工圈定它在 PDF 里的页码区间
（读一遍抽取文本就能定），脚本只在窗口内搜，避免跨专题误匹配。
`###` 子标题继承父窗口（脚本里按 `len(hashes)<=2` 才重置窗口）。
少数"视频跳讲"的条目（如时政零散题、视频后半段回头讲的题）用 `overrides` 直接指定页码。

配置格式 `cfg.json`：
```json
{"windows": [["章节标题关键字", 起始页, 结束页], ...], "overrides": {"行号": 页码}}
```

### 3. 跑对齐脚本，人工复核

```bash
"$PY" scripts/map_items.py "<MD>" "<PDFTXT>" "<MAP_OUT>" "<CFG>"
```

输出 `行号 \t 页码 \t 得分 \t 标记 \t 条目文本`；`LOW` = 最高分与次高分之差 <0.15，需人眼过一遍。
判定经验：**讲师口述改写过的条目**（定义、判据、口诀）天然低分，落在"该专题的引言页/口诀页"即可；
**题干型条目**（含人名、句子）通常能精确命中到题目所在页。复核后把修正写进 `overrides` 重跑。

### 4. 注入链接

```bash
"$PY" scripts/apply_links.py "<MD>" "<MAP_OUT>"
```

插在既有 `[[...mp4#t=...|视频]]` **之前**（pdf 在前、视频在后），已带 `pdf#page=` 的行跳过，自动先备份 `.bak-<date>`。

### 5. 补 PDF 独有考点

对齐后仍会有 PDF 里有、视频没讲的条目。定位办法：
- 在 SRT 里 grep 特征词，**零命中** → 该条属"pdf-only"合法分支（见 `pdf-to-vault-summary` 的 `### 6.` Rules 段两支）；
- **有命中** → 用 `parse_srt.py` 取绝对秒数，配上 `mp4#t=`。
新条目若落在已满 9 条的 `##` 节下，另起 `### 𒋙PDF补充` 子节（链接另起编号从 1）。
⚠️ 同一节的多个 pdf-only 条目若**页码相同**，`normalize` 会把相同链接集合并到末条——这是 Mode B 规则，属预期。

### 6. 收尾校验（同 `pdf-to-vault-summary` 的 `### 7.` 终检段，必须全绿）

> **⚠️ 节号引用说明（2026-09-13 修订）**：`pdf-to-vault-summary` 全文用阿拉伯数字编号（Workflow 为 `### 1.`–`### 7.`；末步 **`Step 8` 是节内加粗行、不是 `###` 标题**；另有顶层末节 `## 9.`），
> **没有任何 `§N` 标题**；引用它时写原始编号即可（`### 7.` / `Step 8` / `## 9.`），**不要写 `§N`**（写了会扑空）。本节标题是本文自己的 `### 6.`，与它不属同一套编号。

```
normalize_vault_summary.py "<MD>"
verify_vault_summary.py "<MD>" --strict-links pdf
verify_discipline.py --all "<MD>"
verify_video_links.py "<MD>" "<同名.srt>"      # IDLE=0 DUP=0
```

### 7. 可选：按 PDF 顺序重排（含"打平"）

补完页码后，广哥可能要求**顺序以 PDF 为准**（视频会跳讲）。先量化再动手：

```bash
"$PY" scripts/analyze_order.py "<MD>"        # 打印每节的 min/max 页 + 节间逆序
"$PY" scripts/check_pages.py "<PDFTXT>" "<MD>" # 已分配页 vs 全局最优页，差 ≥3 才打印
```

- `analyze_order.py` 报"节顺序错位 N"= N 处 `##` 的 min 页比后一节大。
- `check_pages.py` 用来抓**配错页**；但**全局最优经常是错的**（如"洛扎诺夫暗示教学法"会被拉到 p21），
  所以只把它当"可疑清单"，仍以人工窗口结果为准。

确认要排后用：

```bash
"$PY" scripts/flatten.py "<备份目录>" "<MD1>" "<MD2>" ...
```

行为：删掉全部 `##`/`###`、把 `N. ` 条目按 `pdf#page=` **稳定排序**、重新连续编号 1..N；
同一块内缺 `pdf#page=` 的条目自动继承该块首个有页码条目的页。平铺形态的两个已知 FAIL 见
`vault-write-discipline` checklist #8（已登记豁免）。

## 踩过的坑（2026-09-10 科二两篇刷题笔记实做）

- **别重写全文**：440 条 × 双链接的手写成文成本极高，且会丢掉已核对的秒数。脚本注入 + 少量补条是正解。
- **章节窗口必须人工给**：不限窗口时，"德育原则"会匹配到"教学原则"页（同词汇不同专题）。
- **SRT 与 PDF 的人名常不一致**（心仪/欣怡、张力/张丽），所以打分用二元组而不是专名精确匹配。
- `verify_discipline` 的"单条加粗占比 ≤40%(≥30 字)"很容易在**新增的判据条**上触发——一条里最多 2-3 个加粗块（>60 可见字且已按 vwd checklist #19 拆行的条目可到 5，按整个条目合并计）。
- 注入用的引号必须是**半角直引号** `"`：写 JSON 时若直接粘中文弯引号，会挂"半角英文标点"检查。
- **讲义尾部常有"无题号补充题块"**（如教育学 PDF 的 p105-109 就是附加题区，题号只到 443 就断）。
  视频里讲到的同类题会落到这些页，**看着像配错页其实是真的在那儿**——先读那几页原文再判断，
  不要因为"这条主题属于第 3 章"就改回前面的页。
- **排序后 `verify_video_links` 会出现 ORDER? 软提示**（mp4#t= 不再单调），这是按 PDF 排序的必然结果，
  只卡强制门槛 `IDLE=0 DUP=0` 即可。
- **平铺后再跑 `normalize` 会留下裸条目**：同页的 pdf-only 条目链接集合相同，Mode B 把链接合并到末条，
  前面的条目就变成无链接的裸行（实测心理学 6 条）。**这是预期，不要为补链接而编造页码或秒数**——
  **裸条目的具体条数会随补条/重跑而变，不要在本文件里写死数字**（本条曾写"科一成品 2 条无 pdf / 10 条无视频"，
  2026-09-10 审查实测该文件已 0/0，属陈述过期）。**裸条目一律不得超过"真无源"的边界**：若确实要补，
  只能补 SRT 里**真命中**的 `mp4#t=`，或该考点**确实存在**的 PDF 页。
- **目标 md 可能被改名或删掉**：本系列笔记用户会自己重命名或直接删除（**改名后的具体文件名不写死**——文件会腐，需要时按内容特征全库 find；本条不列举已失效的旧名）。
  发现"md 不存在"时**先查 `flatten.py` 的 backup_dir 里的 `.bak-*`，并全库 grep 文件内容确认**，
  能用 .bak 恢复就恢复再重跑 flatten，**绝不要从 PDF 重新成文**（几百条双链接的成本极高且会丢已核对的秒数）。

## 8. 当 md 编号与 PDF 题号系统性漂移时（2026-09-10 科一刷题笔记实做）

上面的"章节窗口 + 二元组"法假设 **md 条目顺序 ≈ PDF 顺序且章节能对上**。若遇到
**md 编号 ≠ PDF 题号、且偏移还是分段的**（实测：md 25→PDF 27、md 63→PDF 62、md 125→PDF 126、
md 253→PDF 252、md 291→PDF 292、md 322→PDF 323），窗口法不够用，改走下面这条：

1. **先按题号把 PDF 切成 (题干, 答案, 答案页)**：题目页按 `^N.` 切块，答案页按 `【答案】`/`答案：` 切块，
   带题号的直接归属，不带题号的按块序归属给"该页之前最近一组尚无答案的题"。
   **印刷坑必查**：重复题号（第二个 `68` 才是第 69 题）、错号（`290` 印成 `390`）、无题号前缀（`62【答案】`）、
   只有答案页没有题干页的题（153 / 197 / 271）、答案页排在题干页**前面**的（p47 答案 / p48 题干）。
2. **打分**：`recall(md 文本, PDF 题干)×2 + recall(md 文本, PDF 答案前150字)×1.2 - 0.06(匹配基础代价)`
   ＋ 答案字母一致 +0.5 / 不一致 -0.15。recall 用 **3-gram**、`grams(md) - 高频停用 gram(DF≥20)` 作分母。
   **⚠️ 千万别把 SRT 上下文并进 md 文本**：`t ~ t+22s` 会串进下一题的口述，把相似度带偏
   （实测加上下文 score 96 → 去掉 192 → 调参 271）。
3. **人工锚点 + 分段 DP**：先打印 `md_num→pdf_num pN | md 前38字 || pdfq 前38字` 逐段人眼扫，
   挑 10-20 个**咬得准**的锚点（md_num → pdf_num，须严格递增），按锚点切段，段内跑 DP
   （跳过 PDF 代价 0、跳过 md 代价 -0.5）。**锚点必须人眼比对内容后钉，光看编号会被漂移骗。**
4. **跳号处理**：能补的题（PDF 里有、讲师没讲）补成 pdf-only 条目；**PDF 该段确实无题的跳号保留**
   （如科一的 30→35），并在 `vault-write-discipline` checklist #8 登记为豁免，不得为过检而重编号。
