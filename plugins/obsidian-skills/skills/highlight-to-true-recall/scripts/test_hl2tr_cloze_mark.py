# -*- coding: utf-8 -*-
"""挖空内容包裹标记（`==`）的**渲染层**自测：证明它在阅读视图里真能开出钩子，
且**只命中挖空**、不误伤用户自己画的粗体。

背景（2026-09-17 源码级查实）：
  · 复习卡面是 Obsidian 的 CM6 编辑器（实时预览），**不是** MarkdownRenderer
    —— 插件源码 Oa 组件用 EmbeddableEditor；插件 styles.css 里
      `.true-recall-review-answer .cm-editor .cm-content` 也印证。
  · 所以 `**x**` 在卡面渲染成 `<span class="cm-strong">`，不是 `<strong>`；
    行内 HTML（第一版用的 `<span class="tr-cloze">`）按**单个标签**走 HtmlWidget
    + sanitizeHTMLToDom，开/闭标签被拆成两个孤立 widget → 只剩一个空 span，钩子抓不住。
  · `==` 是 Obsidian 原生语法 → 实时预览 `span.cm-highlight`、阅读视图 `<mark>`。

本文件用 markdown-it 模拟**阅读视图**那条路（markdown-it 不认 `==`，所以先把
`==x==` 换成 `<mark>x</mark>` 再渲染，等价于 Obsidian 的解析结果），断言：
  ① 挖空内容渲染成 <strong> 里面的 <mark>（钩子存在）
  ② 用户自己的粗体只有 <strong>、没有 <mark>（CSS 不会误染）
  ③ 去掉 WJ 后 `**` 开不了 → 星号字面显示（证明 mark 与 WJ 是绑定的）

⛔ 2026-10-12 广哥定：**彻底走官方原生** ⇒ `plan_cloze()` / `cloze_fill()` 的
`mark` 默认改为 **False**，卡面不再包 `==`。本文件的断言全部**显式传 `mark=True`**
——它验的是「一旦开启 `==`，钩子链路仍然成立」这条能力，能力本身没删。
末尾另加一节断言**默认调用不再产生 `==`**（新口径的唯一硬判据）。

需要 markdown_it（托管 venv：binaries\\python\\envs\\default）；没装时自动只跑字符串层。
"""
import os, re, sys, importlib.util

sys.stdout.reconfigure(encoding="utf-8")

P = os.path.join(os.path.dirname(os.path.abspath(__file__)), "hl2tr.py")
spec = importlib.util.spec_from_file_location("hl2tr", P)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

try:
    from markdown_it import MarkdownIt
    md = MarkdownIt("commonmark", {"html": True})
except Exception:
    md = None

WJ = m.WJ
MARK = m.CLOZE_MARK
PLUG = re.compile(r"\{\{c(\d+)::([^}]*?)(?:::([^}]*?))?\}\}")


def plugin_answer(text, idx=1):
    """模拟插件 zS(t,e)：命中的 cloze → **内容**，其余 cloze → 裸内容。"""
    def rep(mm):
        num, inner = mm.group(1), mm.group(2)
        return ("**%s**" % inner) if int(num) == idx else inner
    return PLUG.sub(rep, text)


def obsidian_reading(html_text):
    """模拟 Obsidian 阅读视图对 `==x==` 的处理（markdown-it 不认 `==`）。"""
    return re.sub(r"==(.+?)==", r"<mark>\1</mark>", html_text, flags=re.S)


fail = 0
print("== 字符串层：默认不再包 `==`（2026-10-12 新口径）==")
d_text, _ = m.plan_cloze("前置词 ==**关键词**== 后置词")
print("  默认 Text :", repr(d_text))
ok = MARK not in d_text and "{{c1::" in d_text
print(("PASS " if ok else "FAIL ") + "默认调用不含 `==` 标记（彻底走原生）")
if not ok:
    fail += 1
d_hint_text, _ = m.plan_cloze("甲 ==**乙**== 丙 %%提问%%")
ok = ("::提问}}" in d_hint_text) and ("::==" not in d_hint_text)
print("  默认 hint :", repr(d_hint_text))
print(("PASS " if ok else "FAIL ") + "默认 hint 是裸文本（不再包 `==`）")
if not ok:
    fail += 1

print("\n== 字符串层：`--cloze-mark` 开启时仍包 `==`（旧能力未删）==")
text, _ = m.plan_cloze("前置词 ==**关键词**== 后置词", True, mark=True)
print("  卡面 Text :", repr(text))
ans = plugin_answer(text)
print("  答案面    :", repr(ans))
ok = MARK in ans and ("**" + WJ + MARK) in ans and (MARK + WJ + "**") in ans
print(("PASS " if ok else "FAIL ") + "答案面 = ** + WJ + ==内容== + WJ + **")
if not ok:
    fail += 1

if md is None:
    print("\n（未装 markdown_it，跳过渲染层）")
    print("\nFAIL 合计:", fail)
    sys.exit(0)

print("\n== 渲染层（模拟阅读视图）==")


def render(ans):
    return md.render(obsidian_reading(ans)).strip()


# ① 挖空内容：<strong> 里套 <mark>
html = render(ans)
n_mark_in_strong = len(re.findall(r"<strong>\s*" + WJ + r"?<mark>", html))
print("  HTML:", html[:200])
ok = n_mark_in_strong == 1
print(("PASS " if ok else "FAIL ") + "挖空内容 = <strong>…<mark>关键词</mark>…</strong>（钩子存在）")
if not ok:
    fail += 1

# ② 用户自己的粗体：只有 <strong>，没有 <mark>
raw = "→ **历史性** 是 ==**杜威**== 提的"
text2, _ = m.plan_cloze(raw, True, mark=True)
ans2 = plugin_answer(text2)
html2 = render(ans2)
print("  HTML:", html2[:260])
n_plain_strong = len(re.findall(r"<strong>(?!\s*" + WJ + r"?<mark>)", html2))
ok = n_plain_strong == 1 and html2.count("<mark>") == 1
print(("PASS " if ok else "FAIL ")
      + "用户粗体 1 个（无 mark）+ 挖空 mark 1 个 → CSS 只染挖空（实测 plain_strong=%d mark=%d）"
      % (n_plain_strong, html2.count("<mark>")))
if not ok:
    fail += 1

# ③ 去掉 WJ：`**` 后紧跟 `=`（标点）而前面紧贴中文 → 开不了 → 星号字面显示
#    （用「中文紧贴」的上下文，两侧带空格时 `**` 仍能开，测不出问题）
raw_no_space = "若==**关键词**==经"
text5, _ = m.plan_cloze(raw_no_space, True, mark=True)
ans5 = plugin_answer(text5)
ans5_no_wj = ans5.replace(WJ, "")
html5 = render(ans5_no_wj)
ok = ("<mark>" in html5) and ("**" in html5)
print("  无 WJ 的 HTML:", html5[:200])
print(("PASS " if ok else "FAIL ") + "无 WJ 时 `**` 开不了、星号字面显示（两者绑定）")
if not ok:
    fail += 1

# ④ 只留 WJ 不留标记：仍是 <strong>，无 mark（说明标记是唯一钩子）
ans4 = ans.replace(MARK, "")
html4 = render(ans4)
ok = "<mark>" not in html4 and "<strong>" in html4
print(("PASS " if ok else "FAIL ") + "去掉 `==` 后只剩 <strong>、无 <mark>（标记是唯一钩子）")
if not ok:
    fail += 1

print("\nFAIL 合计:", fail)
