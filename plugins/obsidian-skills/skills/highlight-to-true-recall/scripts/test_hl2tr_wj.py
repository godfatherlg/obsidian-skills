# -*- coding: utf-8 -*-
"""hl2tr 的 Word Joiner(U+2060)修复：离线自测。

验证「插件答案面那对 ** 能不能开闭」——用 markdown-it（与 Obsidian 同一套
CommonMark 规则）把 zS() 展开后的答案面渲染一遍，检查是否真的出 <strong>。

需要 markdown_it（托管 venv 里有）：
  C:\\Users\\<user>\\.workbuddy\\binaries\\python\\envs\\default\\Scripts\\python.exe
没有则自动跳过渲染部分，只跑字符串层断言。
"""
import os, sys, importlib.util

P = os.path.join(os.path.dirname(os.path.abspath(__file__)), "hl2tr.py")
spec = importlib.util.spec_from_file_location("hl2tr", P)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

WJ = "\u2060"
try:
    from markdown_it import MarkdownIt
    md = MarkdownIt("commonmark")
except Exception:
    md = None

# (说明, 块原文, 该场景不加 WJ 时是否应该失效)
CASES = [
    ("内容以 $ 开头 + 前面紧贴中文", "若==$A$==经", True),
    ("内容以 。 结尾 + 后面紧贴中文", "是==重要。==在", True),
    ("内容以 ） 结尾 + 后面贴字", "在==力量（大）==之", True),
    ("内容以 \" 开头 + 前面贴字", "看到==\"公民\"==选", True),
    ("普通中文内容（本来就没问题）", "这是==重要==的", False),
    # 2026-09-17 真实数据回归：教育学 207 被手动挖空的三处（内容两端都有引号/括号）
    ("真实数据 207：引号+括号包住", "所以见==\"组织起来的教育内容\"归斯宾塞(内容说)==, 三者别混", True),
    ("真实数据 207：结尾是右括号", "所以见==\"预期的学习结果\"归泰勒(目标说)==, 三者别混", True),
]

fail = 0
print("== 字符串层：WJ 外一处（给 `**`）+ 内一处（给 `==`，仅内容贴标点时）==")
for name, raw, _ in CASES:
    got, _ = m.plan_cloze(raw, True, True, True, True)
    # 2026-09-17 起每个挖空都带默认第三段（DEFAULT_HINT）⇒ 断言要把 hint 一起算上：
    # 外层 WJ 在内容开头；内容尾部的外层 WJ 紧接 `::`。
    # ⛔ 2026-10-12 起 `==` 默认关闭 ⇒ 这里显式 mark=True；hint 侧也要 mark_hint 包过后的形态。
    want_hint = m.mark_hint(m.DEFAULT_HINT, mark=True)
    ok = ("{{c1::" + WJ + m.CLOZE_MARK) in got and (WJ + "::" + want_hint + "}}") in got
    if not ok:
        fail += 1
    print(("PASS " if ok else "FAIL ") + name + " -> %r" % got)

if md is None:
    print("\n（未装 markdown_it，跳过渲染验证）")
else:
    print("\n== 渲染层：答案面 **内容** 是否真的加粗 ==")
    print("   （off = 裸内容，既不加 WJ 也不加 == —— 用它复现原始的 flanking 失效）")
    for name, raw, should_fail in CASES:
        text_on, _ = m.plan_cloze(raw, True, True, True, True)     # == 包裹 + WJ
        text_off, _ = m.plan_cloze(raw, True, True, False, False)  # 裸内容
        def render(t):
            # 模拟插件 zS()：命中编号的 cloze → **内容**
            import re
            return md.render(re.sub(r"\{\{c\d+::([^}]*?)(?:::[^}]*?)?\}\}",
                                    lambda x: "**%s**" % x.group(1), t))
        on = "<strong>" in render(text_on)
        off = "<strong>" in render(text_off)
        ok = on and (off == (not should_fail))
        if not ok:
            fail += 1
        print(("PASS " if ok else "FAIL ") + "%-30s 包裹后加粗=%s / 裸内容=%s（预期裸内容失效=%s）"
              % (name, on, off, should_fail))

    print("\n== 关键：只包 == 不加 WJ 会怎样（应当失效 → 所以两者是绑定的）==")
    for name, raw, _ in CASES:
        t, _ = m.plan_cloze(raw, True, True, False, True)   # 只 span、无 WJ
        import re
        html = md.render(re.sub(r"\{\{c\d+::([^}]*?)(?:::[^}]*?)?\}\}",
                                lambda x: "**%s**" % x.group(1), t))
        bad = "<strong>" not in html
        # 预期：夹在文字中间的场景都失效；行首/行尾那种可能侥幸能开，只提示不判失败
        print("   %-30s 加粗=%s%s" % (name, not bad, "  ← 失效（符合预期）" if bad else ""))

print("\n== 字符串层：`==` 内侧的 WJ（内容首/尾贴标点时必须，否则 `==` 露字面量）==")
EXPECT = [
    # (挖空内容, 期望的 == 内核形态)
    ('"组织起来的教育内容"归斯宾塞(内容说)',
     "==" + WJ + '"组织起来的教育内容"归斯宾塞(内容说)' + WJ + "=="),
    ("$A$", "==" + WJ + "$A$" + WJ + "=="),
    ("跑道", "==跑道=="),                       # 普通中文：内侧不加
    ("重要。", "==重要。" + WJ + "=="),          # 只有结尾贴标点：只在尾侧加
]
for inner, core in EXPECT:
    got = m.cloze_fill(inner, mark=True)
    want = "{{c1::" + WJ + core + WJ + "}}"
    ok = got == want
    if not ok:
        fail += 1
    print(("PASS " if ok else "FAIL ") + "%-34s -> %r" % (inner[:32], got))
    if not ok:
        print("      期望 %r" % want)

print()
print("== ⛔ 2026-10-12 新口径：默认不包 `==`，但**外层 WJ 必须还在** ==")
print("   （WJ 是给插件那对 `**` 用的，与 `==` 无关；去掉它加粗仍会 flanking 失效）")
for name, raw, _ in CASES:
    got, _ = m.plan_cloze(raw)
    ok = (WJ in got) and (m.CLOZE_MARK not in got)
    if not ok:
        fail += 1
    print(("PASS " if ok else "FAIL ") + "默认 %-28s -> %r" % (name, got))

print()
print("FAIL 合计:", fail)
