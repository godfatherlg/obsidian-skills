# -*- coding: utf-8 -*-
"""hl2tr.py 的 %%提问%% 同行归属规则 + 挖空内容包裹(`==` 标记 / WJ)：离线自测（不落库、不碰 vault）"""
import os, sys, importlib.util

P = os.path.join(os.path.dirname(os.path.abspath(__file__)), "hl2tr.py")
spec = importlib.util.spec_from_file_location("hl2tr", P)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

CASES = [
    # (说明, 块原文, 期望 Text)
    ("基础同行", "教学原则 ==**启发性原则**== %%这个原则叫什么%%",
     "教学原则 {{c1::启发性原则::这个原则叫什么}}"),
    ("同行多高亮取最近", "==**A**== 与 ==**B**== %%B 是什么%%",
     "{{c1::A}} 与 {{c1::B::B 是什么}}"),
    ("注释在前=无归属", "%%提示%% ==**A**==",
     "%%提示%% {{c1::A}}"),
    ("注释单独成行=无归属", "==**A**==\n%%孤立%%",
     "{{c1::A}}\n%%孤立%%"),
    ("跨行高亮+末行注释", "定义:==**甲\n乙**== %%叫什么%%",
     "定义:{{c1::甲\n乙::叫什么}}"),
    ("一高亮两注释:只认第一个", "==**A**== %%Q1%% %%Q2%%",
     "{{c1::A::Q1}} %%Q2%%"),
    ("无高亮不建卡(此处只看不崩)", "普通文字 %%Q%%",
     "普通文字 %%Q%%"),
    ("未闭合注释不动", "==**A**== %%没闭合",
     "{{c1::A}} %%没闭合"),
    # 2026-09-17 广哥报「题面粘连」：注释右侧紧贴链接 → 必须回填一个空格
    # ⚠️ 2026-09-19 追加：`}}` 与紧邻的 `[[` 之间还要由 norm_link_gap 补成**两个**空格
    #    （一个空格会触发链接解析，把问题面上的 `[hint]` 吃成链接文字）
    ("注释紧贴链接:右侧回填 + 补成两个空格",
     "小学生通过列提纲等方式学习 → ==**组织策略**== %%学习策略%%[[x.pdf#page=72|pdf]] [[x.mp4#t=3924|视频]]",
     "小学生通过列提纲等方式学习 → {{c1::组织策略::学习策略}}  [[x.pdf#page=72|pdf]] [[x.mp4#t=3924|视频]]"),
    ("注释紧贴行内嵌入图:同样回填",
     "==**A**== %%Q%%![[images/x.png]]",
     "{{c1::A::Q}} ![[images/x.png]]"),
    ("注释紧跟字母:回填", "==**A**== %%Q%%pdf",
     "{{c1::A::Q}} pdf"),
    ("注释紧跟句点:不回填", "==**实习作业法**==%%教学方法%%. [[x.pdf#page=86|pdf]]",
     "{{c1::实习作业法::教学方法}}. [[x.pdf#page=86|pdf]]"),
    ("注释紧跟中文:不回填", "==**A**== %%Q%%经",
     "{{c1::A::Q}}经"),
    ("注释在块尾:不回填不留尾空格", "==**A**== %%Q%%",
     "{{c1::A::Q}}"),
]

# 挖空内容外面套的 `==…==` 标记（见 hl2tr.CLOZE_MARK）与 Word Joiner(U+2060)。
# 老用例的期望值写的是「裸内容」形态，比较时统一剥掉这两层包裹；
# 包裹本身另有一组专门用例（下方 LAYER_*）。
WJ = "\u2060"
MARK = m.CLOZE_MARK


def wrap(s):
    return MARK + s + MARK


def strip_all(s):
    """剥掉**默认第三段**（DEFAULT_HINT）、`==` 标记与 WJ，回到裸内容形态。

    ⚠️ 2026-09-17 起，没有 `%%提问%%` 的挖空也会被填上 `::==⁠...⁠==`（占位符黄底）。
    老用例的期望值写的是「裸内容」形态，比较时统一剥掉这三层；默认占位符本身
    另有一条专门用例（下方 DEF_TAIL 断言）。
    ⚠️ **顺序**：先剥 `::==…==`（它含 WJ 与 `==`），再剥 WJ/MARK，否则剥不干净。
    """
    return s.replace("::" + m.DEFAULT_HINT, "").replace(WJ, "").replace(MARK, "")


fail = 0
for name, raw, want in CASES:
    got, info = m.plan_cloze(raw, True)
    ok = (strip_all(got) == want)
    if not ok:
        fail += 1
    print(("PASS " if ok else "FAIL ") + name)
    if not ok:
        print("   want: %r" % want)
        print("   got : %r" % got)
    print("   hints=%d orphan=%s" % (info["hints"], info["orphan"]))

print()
# ⛔ 2026-10-12 广哥定（彻底走官方原生）：默认 hint 改为**裸 `...`**。
#    没有 %%提问%% 的挖空仍带第三段 ⇒ 问题面显示 `[...]`（插件 `GS()` 拼的纯文本），
#    与「不填第三段」视觉完全一致。旧口径 `::==⁠...⁠==`（黄底三个点）需 `--cloze-mark`。
got, _ = m.plan_cloze("教学原则 ==**启发性原则**==", True)
want = "教学原则 {{c1::" + WJ + "启发性原则" + WJ + "::" + m.DEFAULT_HINT + "}}"
ok = got == want
if not ok:
    fail += 1
print(("PASS " if ok else "FAIL ") + "默认占位符 hint 已填(裸 ...) -> %r" % got)
if not ok:
    print("   want: %r" % want)

got, _ = m.plan_cloze("教学原则 ==**启发性原则**==", True, mark=True)
want = "教学原则 {{c1::" + WJ + wrap("启发性原则") + WJ + "::" + MARK + WJ + "..." + WJ + MARK + "}}"
ok = got == want
if not ok:
    fail += 1
print(("PASS " if ok else "FAIL ") + "--cloze-mark 占位符 hint 包 ==(旧口径) -> %r" % got)
if not ok:
    print("   want: %r" % want)

print()
# 幂等归一化必须与插件展示态一致（标记只改第二段，_render_cloze 只吃第三段 → 不受影响）
R = [
    ("{{c1::A}}", "[...]"),
    ("{{c1::A::Q}}", "[Q]"),
    ("a {{c1::A::Q}} b {{c1::B}} c", "a [Q] b [...] c"),
    ("{{c1::" + WJ + wrap("A") + WJ + "::Q}}", "[Q]"),
]
for src, want in R:
    got = m._render_cloze(src)
    ok = got == want
    if not ok:
        fail += 1
    print(("PASS " if ok else "FAIL ") + "render %r -> %r" % (src, got))

print()
# 标记与 WJ 的层次：** 标记在内、WJ 在外 **（WJ 必须紧贴插件那对 `**`）
LAYER_CASES = [
    # ⛔ 2026-10-12 起默认不再包 `==`：默认形态 = 内容 + 外层 WJ（WJ 仍必须，
    #    它保证插件那对 `**` 永远能开能闭，与 `==` 无关）。
    ("默认 只留 WJ", dict(), "{{c1::" + WJ + "A" + WJ + "}}"),
    ("默认 带 hint 也是裸文本", dict(hint="Q"),
     "{{c1::" + WJ + "A" + WJ + "::Q}}"),
    # `--cloze-mark` 开启时：** 标记在内、WJ 在外 **
    ("--cloze-mark 标记在内 WJ 在外", dict(mark=True),
     "{{c1::" + WJ + wrap("A") + WJ + "}}"),
    # ⚠️ 2026-09-19 起 hint 也被包一层 `==…==`（`mark_hint()`），两层各包各的
    ("--cloze-mark 带 hint 时两层各自包", dict(hint="Q", mark=True),
     "{{c1::" + WJ + wrap("A") + WJ + "::" + wrap("Q") + "}}"),
    # ⚠️ 函数层允许「只标记不 WJ」，但 main() 会拦：实测 `**==` 的 `**` 后面
    #    紧跟 `=`（标点）→ 夹在文字中间开不了，所以 main 里标记会自动一起关。
    ("--no-wj 只留标记（函数层，main 会拦）", dict(wj=False, mark=True),
     "{{c1::" + wrap("A") + "}}"),
    ("两个都关=裸内容", dict(wj=False, mark=False), "{{c1::A}}"),
]
for name, kw, want in LAYER_CASES:
    got = m.cloze_fill("A", **kw)
    ok = got == want
    if not ok:
        fail += 1
    print(("PASS " if ok else "FAIL ") + "LAYER " + name)
    if not ok:
        print("   want: %r" % want)
        print("   got : %r" % got)

print()
# ⚠️ 2026-09-19 广哥定：**第三段(hint)也包 `==…==`**（`mark_hint()`）——
#    问题面 `[==提问==]` 与占位符 `[==⁠...⁠==]` 一样是原生高亮黄底（2026-09-20 起不加粗）。
#    笔记原文一个字不动，只改「笔记 → 卡面」这一步。
HINT_CASES = [
    ("纯文字提问", "这个原则叫什么", wrap("这个原则叫什么")),
    ("字母提问", "Q", wrap("Q")),
    ("含空格", "B 是什么", wrap("B 是什么")),
    # `==` 自己也吃 flanking：首 / 尾是标点时才往 `==` **内侧**补 WJ（只补贴着的那侧）
    ("尾字是标点 → 只补尾侧", "这个原则叫什么？", wrap("这个原则叫什么？" + WJ)),
    ("首字是标点 → 只补首侧", "“甲”是什么", wrap(WJ + "“甲”是什么")),
    ("首尾都是标点 → 两侧都补", "“甲”是什么？", wrap(WJ + "“甲”是什么？" + WJ)),
    ("已包过 → 原样（幂等）", wrap("这个原则叫什么"), wrap("这个原则叫什么")),
    ("含 `==` → 不包（并 WARN）", "a==b", "a==b"),
    ("首字是 `=` → 不包", "=x", "=x"),
    ("空 → 原样", "", ""),
]
for name, hint, want in HINT_CASES:
    got = m.mark_hint(hint, mark=True)
    ok = got == want
    if not ok:
        fail += 1
    print(("PASS " if ok else "FAIL ") + "HINT " + name)
    if not ok:
        print("   want: %r" % want)
        print("   got : %r" % got)

# 占位符必须与 `mark_hint("...")` 同构，否则两条 hint 来源样式会分叉
# ⛔ 2026-10-12 起默认口径：裸 `...` ⇔ mark_hint(..., mark=False)
got = m.mark_hint("...")
ok = got == m.DEFAULT_HINT
if not ok:
    fail += 1
print(("PASS " if ok else "FAIL ") + "DEFAULT_HINT == mark_hint('...') 默认裸 -> %r" % got)

# 旧口径（`--cloze-mark`）下占位符必须包成 `==⁠...⁠==`
ok = m.mark_hint("...", mark=True) == MARK + WJ + "..." + WJ + MARK
if not ok:
    fail += 1
print(("PASS " if ok else "FAIL ") + "DEFAULT_HINT == mark_hint('...') -> %r" % got)

# 端到端（⛔ 2026-10-12 起默认口径）：带 `%%提问%%` 的块，插件展示态（问题面）
# = `[提问]` 裸文本（插件 `GS()` 是 `s ? '['+s+']' : "[...]"`）。
got, _ = m.plan_cloze("教学原则 ==**启发性原则**== %%这个原则叫什么%%", True)
want = "教学原则 {{c1::" + WJ + "启发性原则" + WJ + "::这个原则叫什么}}"
rend = m._render_cloze(got)
ok = got == want and rend == "教学原则 [这个原则叫什么]"
if not ok:
    fail += 1
print(("PASS " if ok else "FAIL ") + "端到端：默认语义 hint 是裸文本 -> %r" % got)
if not ok:
    print("   want  : %r" % want)
    print("   render: %r" % rend)

# 端到端（旧口径 `--cloze-mark`）：问题面必须是 `[==提问==]`
got, _ = m.plan_cloze("教学原则 ==**启发性原则**== %%这个原则叫什么%%", True, mark=True)
want = "教学原则 {{c1::" + WJ + wrap("启发性原则") + WJ + "::" + wrap("这个原则叫什么") + "}}"
rend = m._render_cloze(got)
ok = got == want and rend == "教学原则 [==这个原则叫什么==]"
if not ok:
    fail += 1
print(("PASS " if ok else "FAIL ") + "端到端：--cloze-mark 语义 hint 包 `==` -> %r" % got)
if not ok:
    print("   want  : %r" % want)
    print("   render: %r" % rend)

print()
# ⚠️ 2026-09-19：`}}` 与紧邻的 `[[` 之间必须**两个空格** ——
#    一个空格时问题面上的 `[hint]` 会被解析成链接文字（广哥报「把学习动机变成链接了」）。
GAP_CASES = [
    ("一空格 → 两空格", "a {{c1::x}} [[b]]", "a {{c1::x}}  [[b]]"),
    ("已两空格 → 不动（幂等）", "a {{c1::x}}  [[b]]", "a {{c1::x}}  [[b]]"),
    ("三空格 → 不动", "a {{c1::x}}   [[b]]", "a {{c1::x}}   [[b]]"),
    ("嵌入 `![[` 不动（按 2026-09-19 指令）", "a {{c1::x}} ![[b]]", "a {{c1::x}} ![[b]]"),
    ("后面不是链接 → 不动", "a {{c1::x}} pdf", "a {{c1::x}} pdf"),
]
for name, src, want in GAP_CASES:
    got = m.norm_link_gap(src)
    ok = got == want
    if not ok:
        fail += 1
    print(("PASS " if ok else "FAIL ") + "GAP " + name)
    if not ok:
        print("   want: %r" % want)
        print("   got : %r" % got)

# 端到端：带 `%%提问%%` 的块，`}}` 与链接之间落成两个空格
got, _ = m.plan_cloze("==**A**== %%Q%%[[x.pdf#page=1|pdf]]", True)
ok = got.endswith("}}  [[x.pdf#page=1|pdf]]")
if not ok:
    fail += 1
print(("PASS " if ok else "FAIL ") + "端到端：`}}` + 两个空格 + 链接 -> %r" % got)
if not ok:
    print("   期望以 %r 结尾" % "}}  [[x.pdf#page=1|pdf]]")

print()
# 幂等：内容里已带 `==` 时不再二次包裹（重跑同一篇笔记的关键）
got = m.cloze_fill(wrap("A"))
ok = got == "{{c1::" + WJ + wrap("A") + WJ + "}}" and got.count(MARK) == 2
if not ok:
    fail += 1
print(("PASS " if ok else "FAIL ") + "幂等：已有 `==` 不重复包 -> %r" % got)

# 空内容不加包裹
got = m.cloze_fill("   ")
ok = got == "{{c1::}}"
if not ok:
    fail += 1
print(("PASS " if ok else "FAIL ") + "空内容不包裹 -> %r" % got)

# 含 ** 的内容：先剥粗体再包标记（`==` 不含 `*`，不会被误剥）
got = m.cloze_fill("**启发性**", mark=True)
ok = got == "{{c1::" + WJ + wrap("启发性") + WJ + "}}"
if not ok:
    fail += 1
print(("PASS " if ok else "FAIL ") + "剥粗体后再包标记 -> %r" % got)

print()
# ⚠️ 2026-09-20 广哥定（升级自旧的「只去加粗」）：挖空内容里**文本格式都清掉，
#    只留纯文字**，再补高亮 —— 否则这些标记和 `==` 叠一起，卡面经常渲染坏。
#    实现 `strip_inline_md()`；**`$…$` 公式整段原样**（里面的 `_` `*` 是数学内容）。
#    ⚠️ 广哥 2026-09-20 补定：**行内代码 `` `…` `` 与 HTML 标签原样不动**（代码是内容
#    不是格式，HTML 标签删了丢语义）；`` ` `` 与 `<` `>` 都是符号 → 两端补内层 WJ。
FMT_CASES = [
    ("斜体 *…*", "*斜体*", WJ + wrap("斜体") + WJ),
    ("斜体 _…_", "_斜体_", WJ + wrap("斜体") + WJ),
    ("删除线 ~~…~~", "~~旧说法~~", WJ + wrap("旧说法") + WJ),
    ("行内代码原样保留（连内部的 _ 一起保）", "`file_name`",
     WJ + MARK + WJ + "`file_name`" + WJ + MARK + WJ),
    ("HTML 标签原样保留", "<b>重点</b>",
     WJ + MARK + WJ + "<b>重点</b>" + WJ + MARK + WJ),
    ("多种格式混排（删标记后多余空格压成一个）", "**粗** *斜* ~~删~~ `码`",
     WJ + MARK + "粗 斜 删 `码`" + WJ + MARK + WJ),
    ("公式里的 _ 与 * 不动", "$x_1 * y$",
     WJ + MARK + WJ + "$x_1 * y$" + WJ + MARK + WJ),
    ("公式 + 格式混排", "**重点** 见 $x_1$",
     WJ + MARK + "重点 见 $x_1$" + WJ + MARK + WJ),
]
for label, inner, want_body in FMT_CASES:
    got = m.cloze_fill(inner, mark=True)   # ⛔ 2026-10-12: mark 默认关,旧用例显式开启
    want = "{{c1::" + want_body + "}}"
    ok = got == want
    if not ok:
        fail += 1
    print(("PASS " if ok else "FAIL ") + "清格式 " + label + " -> %r" % got)
    if not ok:
        print("   want: %r" % want)

# 公式保护：清完 `_`/`*` 必须还在（误删就毁了数学内容）
got = m.strip_inline_md("**重点** 见 $x_1 * y$")
ok = "$x_1 * y$" in got and "**" not in got
if not ok:
    fail += 1
print(("PASS " if ok else "FAIL ") + "公式段原样保留 -> %r" % got)

# 幂等：清一次和清两次完全相同
for s in ["**粗** *斜* $x_1$", "~~B~~", "`a_b`", "<b>A</b>"]:
    ok = m.strip_inline_md(s) == m.strip_inline_md(m.strip_inline_md(s))
    if not ok:
        fail += 1
    print(("PASS " if ok else "FAIL ") + "清格式幂等 %r" % s)

# 行内代码整段原样（广哥 2026-09-20：代码是内容不是格式，内部的 _ * 一律不动）
for s, want in [("`file_name`", "`file_name`"),
                ("`a * b`", "`a * b`"),
                ("见 *斜* 与 `x_1`", "见 斜 与 `x_1`")]:
    got = m.strip_inline_md(s)
    ok = got == want
    if not ok:
        fail += 1
    print(("PASS " if ok else "FAIL ") + "行内代码原样 %r -> %r" % (s, got))
    if not ok:
        print("   want: %r" % want)

# HTML 标签原样（广哥 2026-09-20：删了丢语义）
for s, want in [("<b>重点</b>", "<b>重点</b>"), ("**粗** <sub>2</sub>", "粗 <sub>2</sub>")]:
    got = m.strip_inline_md(s)
    ok = got == want
    if not ok:
        fail += 1
    print(("PASS " if ok else "FAIL ") + "HTML 标签原样 %r -> %r" % (s, got))
    if not ok:
        print("   want: %r" % want)

# 第三段(hint)同样清格式（2026-09-20 广哥定：与内容侧同一把尺子）
for label, h, want_h in [("加粗", "**这个原则叫什么**", wrap("这个原则叫什么")),
                         ("斜体", "*叫什么*", wrap("叫什么")),
                         ("公式留着", "$x_1$ 是什么", MARK + WJ + "$x_1$ 是什么" + MARK)]:
    got = m.cloze_fill("A", h, mark=True)
    want = "{{c1::" + WJ + wrap("A") + WJ + "::" + want_h + "}}"
    ok = got == want
    if not ok:
        fail += 1
    print(("PASS " if ok else "FAIL ") + "提问清格式 %s -> %r" % (label, got))
    if not ok:
        print("   want: %r" % want)

# 内容首/尾本身就是 `=` 时不包（`==A===` 会解析坏）
for label, inner in [("以 = 结尾", "A="), ("以 = 开头", "=A")]:
    got = m.cloze_fill(inner)
    ok = MARK not in got
    if not ok:
        fail += 1
    print(("PASS " if ok else "FAIL ") + "%s 不包标记 -> %r" % (label, got))

# 插件正则必须能命中带包裹的 cloze —— 即 `==` 包裹**不引入新的失配**
# （`==` 里不含 `}`，所以只在「内容本身含 `}`」时才失配，
#  那是**已知缺口**、按 2026-09-17 广哥定的「先只补文档」处理，见 SKILL.md 坑 1。）
PLUG = __import__("re").compile(r"\{\{c(\d+)::([^}]*?)(?:::([^}]*?))?\}\}")
for label, text in [("无 hint", m.cloze_fill("A")),
                    ("带 hint", m.cloze_fill("A", "Q")),
                    ("含 `}` 的字面", m.cloze_fill("甲}乙"))]:
    expect = "字面" not in label
    ok = bool(PLUG.search(text)) == expect
    if not ok:
        fail += 1
    print(("PASS " if ok else "FAIL ") + "插件正则（%s）预期%s -> %r"
          % (label, "命中" if expect else "失配", text))

print()
print("hint 含 } 的清洗:", m.cloze_fill("A", "问}题"))
print("WARN:", m.WARN)
print()
print("FAIL 合计:", fail)
