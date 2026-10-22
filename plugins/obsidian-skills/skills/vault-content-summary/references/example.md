# Worked Example - 教资作文开头结尾段内容汇总

This is the exact shape the skill should produce. Topic requested: content in the
vault about 教资作文 开头段 / 结尾段 写法. User permitted `#` headings
("这些可以写成标题"), requires the 𒋙 prefix on every heading, and asked to drop
the redundant intro paragraph and keep the file compact (no decorative blank lines).

> 2026-09-07 合规化重写: 旧版示例含全角标点, 链接被放到 3 空格续行(链接必须内联在条目文字行尾, 不能单独占续行), 且缺别名, 三处都与现行硬规则冲突(会被 `verify_vault_summary.py` 判 FAIL). 本版已按现行规则修正——**半角标点 + 别名链接 + 链接内联在条目文字行尾**, 以本示例为准, 勿照抄旧版写法. (注: 3 空格惰性续行本身合法, 见 `vault-write-discipline` checklist #5; 被判 FAIL 的是"链接放在续行"这一落法.)
>
> ⚠️ **本文件是「说明文字 + 代码围栏示例」的文档, 不是产出物**: 说明段里的空行、全角标点、英文小节标题、反引号都会让产出物 verifier 报 FAIL,
> 这属设计内(verifier 针对的是产出 md, 不是本文)。**要照抄的只有代码围栏内的 `#`/`##` 标题与 `N. ` 条目部分**;
> 不要照抄说明段的排版, 也不要把本文件的整体结构当产出模板。若确实需要一份可直接对照的干净样例, 取代码围栏内的内容单独存一份再跑 verifier。

```markdown
# 𒋙教资作文开头结尾段内容汇总
## 𒋙作文模板笔记
1. 开头万能格式(四步) [[反观当下模版#𒋙二,开头万能格式(四步)|标题]]
   第一步 引述材料:"当……时,一幅……的画面映入眼帘,这不禁让人深思:"
   第二步 分析材料:"这看似……,实则揭示了……" / "这并非……,而是……" / "其背后,暗合了……的深刻逻辑"
   第三步 结合自身:"置身于……的时代洪流中,我辈青年 / 教育者愈发深刻体认到……"
   第四步 亮明观点:"因此,……是……的必由之路." / "吾深信,……"
   四步顺序固定:引述材料 -> 分析材料 -> 结合自身 -> 亮明观点,照抄句式即可成首段.
2. 结尾万能模板 [[反观当下模版#𒋙九,结尾万能模板|标题]]
   师者匠心,止于至善;师者如光,微以致远.让我们以………………为笔,以………………为墨,在每一个孩子的心田书写下希望的篇章;让我们以………………为帆,以………………为桨,在教育的长河中乘风破浪,为培养担当民族复兴大任的时代新人,贡献自己的全部力量!
   四处"……"分别填:精神,行动,信念,担当,落笔即收束升华.
3. 整体写作流程速记 [[反观当下模版#𒋙十,整体写作流程速记|标题]]
   第一步 取题目(套模板或化用古文成语)
   第二步 写开头(引述 -> 分析 -> 结合自身 -> 亮明观点,万能四步)
   第三步 写分论点(3段:分论点 -> 素材 -> 分析 -> 总结;可用变形结构)
   第四步 写结尾(套用结尾万能模板)
   首尾段嵌在流程的第二,四步,带"……"处需按题目关键词自行填充.
## 𒋙科一写作理论笔记
1. 文章的开头与结尾(出自第四章写作第二节) [[05基本能力#(二)文章的开头与结尾|标题]]
   开头要写成"凤头",给人先声夺人之感,三种开头法:
   ①设问/反问式开头法:通过自问自答突出主题,如"警察能只顾及个人利益而对坏人坏事视而不见吗?……答案是否定的."
   ②引言式开头法:引用名人名言作开头引语,如陶行知"爱是一种伟大的力量,没有爱就没有教育."
   ③排比式开头法:三个或以上结构相似句子连用造势.
   结尾要写成"豹尾",两种方法:
   ①自然收尾式:自然而然收束,不雕琢哲理语句.
   ②首尾呼应式:结尾与开头呼应,既呼应又不简单重复.
2. 议论文理论知识(开头亮观点,结尾回扣的底座) [[05基本能力#一,议论文理论知识|标题]]
   议论文三要素:①论点 ②论据 ③论证.
   五种论证方法:举例论证,道理论证,对比论证,比喻论证,引用论证.
## 𒋙作文审题范文
1. 爱坐前排的学生成功比例高 [[爱坐前排的学生成功比例高|文章]]
   以"教授选座实验"主题作文为例,演示立意拆解与高分拟题:拟题用"古诗前半句+主题词+固定后缀"结构,如"欲穷千里目,积极向阳行".可对照模板看真实题目如何落到四步开头与万能结尾.
2. 煮书细小之处非小事 [[煮书细小之处非小事|文章]]
   整理朱子读书法六条,王国维人生三境界等通用素材与立意工具,可用于开头引用与论证段填充,跨题通用.
3. 作文审题/ 文件夹
   该文件夹另有三十余篇训练稿(如作文审题1路是自己的和领路人,作文训练8扎根叶活等),均为实际成稿,可对照实际首尾如何落笔.
   路径:<vault>\2026上数学教资\2026科1综合素质\作文\作文审题\
```

## Why this shape

- Title is an H1 with the 𒋙 prefix; NO separate intro paragraph (it would just repeat the title).
- Every heading (H1 and `##`/`###`) carries the 𒋙 prefix and NO numbering.
- Categories are `##` headings; `###` sublevels only for genuine containment.
- The file is COMPACT: NO decorative blank lines between sections or between items — each list item's link line is immediately followed by the next item, and the last item of a section is immediately followed by the next heading.
- Each numbered item writes the FULL template/source text — not a one-line summary.
- Key terms are bolded for scanning.
- **The wikilink is written INLINE directly after the item text on the SAME line** (never on a soft-break continuation line, never as a block at the file end), using the **alias form**:
  - Item with a matching heading → `[[note#heading text|标题]]` (alias is the literal word 标题, never the heading text).
  - Whole-note citation / no heading → `[[note|文章]]` (alias is the literal word 文章).
  - Folder item → plain path text, not a wikilink.
  - Canonical alias list (six fixed words: 图片 / 视频 / 音频 / pdf / 标题 / 文章) lives at `../shared/citation-link-aliases.md`; a bare `[[note]]` with no alias is only a last-resort fallback.
- **Half-width (English) punctuation everywhere in prose**: `, . ; : " " ( ) ! ?` instead of `，。、；：（）！？`. Only `…` and `·` are exempt. Em dash `—` is full-width and FAILS — write `-` instead.
- An unmarked 4-space continuation line directly after a list item is legal (renders as an indent line); a top-level unmarked 4-space line is not. Containment is expressed with a marked 4-space child list (`    N. `), capped at 2 levels (0/4/8 spaces). See `../vault-write-discipline` Pre-Write Checklist #5/#14.
- No backticks wrap any path or link.
- File saved to a `.md` under `<vault>\临时\` (name given by the user; the file name in older revisions of this example no longer exists in the vault — do not treat it as a real target).
