# Obsidian Skills

一组面向 Obsidian 的 CodeBuddy Agent Skills，覆盖 True Recall 卡片制作、vault 写作规范、行跳转、PDF 转 vault 摘要、CSS 片段调试等高频工作流。

## 安装

```bash
# 添加市场
/plugin marketplace add godfatherlg/obsidian-skills

# 安装插件
/plugin install obsidian-skills@obsidian-skills
```

安装后，CodeBuddy 会在匹配到对应场景时自动加载相应 skill。

## Skill 列表（16 个）

### True Recall 卡片

| Skill | 作用 |
|---|---|
| `highlight-to-true-recall` | 把 `==高亮==` 转成 True Recall 的 cloze 挖空卡 |
| `heading-to-true-recall` | 把标题（⭐/⏳）转成 True Recall 的 basic 问答卡 |
| `basic-to-cloze-true-recall` | basic 卡 ⇄ cloze 卡的两级阶梯互换（记不住就挂起 + 建扶手卡，记住了就收口） |
| `gaicuo` | 手写简答答案批改（定位参考答案 + 评分/分析） |

### Vault 写作

| Skill | 作用 |
|---|---|
| `vault-write-discipline` | 写进 vault 的强制终检：零空行、编号格式、全角标点、缩进层级等 |
| `vault-content-summary` | 搜索 vault 后生成汇总/报告/对照文 |
| `vault-annotation-style` | vault 内的标注样式规范 |
| `temp-note-workflow` | 临时记录追加与合并清空的唯一权威流程 |
| `write-into-note` | 把内容写进指定笔记的规范流程 |

### Obsidian 操作

| Skill | 作用 |
|---|---|
| `obsidian-jump-line` | 打开/跳行/聊天里引用 vault 内容（obsidian://adv-uri 链接） |
| `obsidian-css-selector-debug` | 写/调 Obsidian CSS 片段时的类名取证与选择器判据 |
| `obsidian-macro-debug` | 调试 Obsidian QuickAdd 宏的已知陷阱 |
| `obsidian-link-line-sync` | 笔记内链接的行号同步 |
| `obsidian-diagram-to-png` | 把图表渲染成 PNG 并嵌入 vault |

### PDF 与笔记

| Skill | 作用 |
|---|---|
| `pdf-to-vault-summary` | 把 PDF（教资/考研资料等）转成 vault 摘要 markdown |
| `pdf-md-page-align` | 给已有 markdown 的每个编号条目注入对应的 PDF 页码链接 |

## 环境说明

这些 skill 原本是在作者的个人 vault 上打磨的，分享版已做脱敏：

- vault 路径统一写成 `<vault>`，请替换成你自己的 vault 根目录
- Obsidian 安装目录写成 `<ObsidianInstallDir>`
- vault ID 写成 `<vault-id>`，请替换成你自己的（见 Obsidian 的 `obsidian.json`）
- 部分 Python 脚本需要按你的环境调整路径

`scripts/` 下的 Python 脚本依赖本机 Python 环境，运行前请确认已安装所需依赖。

## License

MIT
