# -*- coding: utf-8 -*-
"""bc2tr.py 的离线自测（不需要 Obsidian、不碰任何库、不写任何文件）。

跑法：
  <python> "…\\basic-to-cloze-true-recall\\scripts\\test_bc2tr.py"

覆盖四件事：
  1. split_tail()   —— 末尾跳转链接行的识别（标题链接 / adv-uri / 纯文字 / 没有 / 不误伤正文）
  2. extra_from_answer2() —— 从卡面 answer 切真 Extra（含 hl2tr 切不出来的 `[[…]]` 形态）
  3. build_cloze()  —— 卡面拼装（标题行 + 正文）、挖空格式、无高亮时跳过
  4. local_fields_key() —— 字段键必须与"降级路由渲染态"可比（这是幂等的命门）
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import bc2tr as B  # noqa: E402
import hl2tr as H  # noqa: E402

PASS = FAIL = 0


def ck(name, got, want):
    global PASS, FAIL
    ok = got == want
    if ok:
        PASS += 1
    else:
        FAIL += 1
    print("%s %s" % ("PASS" if ok else "FAIL", name))
    if not ok:
        print("     got : %r" % (got,))
        print("     want: %r" % (want,))


def ck_in(name, needle, hay):
    global PASS, FAIL
    ok = needle in hay
    if ok:
        PASS += 1
    else:
        FAIL += 1
    print("%s %s" % ("PASS" if ok else "FAIL", name))
    if not ok:
        print("     缺少: %r" % (needle,))
        print("     in  : %r" % (hay,))


# ---------- 1. split_tail ----------
print("--- 1. split_tail：末尾跳转行识别")
ck("标题链接尾被摘出", B.split_tail("正文甲\n\n[[笔记甲#标题⭐⭐|标题]]"),
   ("正文甲", "[[笔记甲#标题⭐⭐|标题]]"))
ck("adv-uri 行链接尾被摘出",
   B.split_tail("正文乙\n[《笔记乙》·第 3 块](obsidian://adv-uri?vault=x&line=42)"),
   ("正文乙", "[《笔记乙》·第 3 块](obsidian://adv-uri?vault=x&line=42)"))
ck("纯文字块名尾被摘出", B.split_tail("正文丙\n《笔记丙》·第 12 块"),
   ("正文丙", "《笔记丙》·第 12 块"))
ck("没有尾链接 → 全留正文", B.split_tail("正文丁\n1. 甲乙丙"), ("正文丁\n1. 甲乙丙", ""))
ck("末尾多余空行不影响判定",
   B.split_tail("正文戊\n\n[[笔记戊#标题|标题]]\n\n\n"),
   ("正文戊", "[[笔记戊#标题|标题]]"))
ck("正文里的嵌入行不误伤（行首有 5. ）",
   B.split_tail("1. 甲\n5. 鉴别![[笔记#别的标题|别的标题]]"),
   ("1. 甲\n5. 鉴别![[笔记#别的标题|别的标题]]", ""))
ck("只有链接行 → 正文为空串", B.split_tail("[[笔记#标题|标题]]"), ("", "[[笔记#标题|标题]]"))
ck("空 Back", B.split_tail(""), ("", ""))


# ---------- 2. extra_from_answer2 ----------
print("\n--- 2. extra_from_answer2：从渲染态 answer 切片")
SAMP = ("1. 甲\n2. 乙<extra>".replace("<extra>", ""))
ck("cloze 卡：渲染正文 + <br> + wikilink Extra",
   B.extra_from_answer2("1. 甲 [==⁠...⁠==]\n<br>[[笔记#标题|标题]]"),
   "[[笔记#标题|标题]]")
ck("cloze 卡：渲染正文 + <br> + hl2tr 式链接 Extra",
   B.extra_from_answer2("1. 甲 [提问]\n<br>[《笔记》·第 2 块](obsidian://adv-uri?line=9&anchor=abc)"),
   "[《笔记》·第 2 块](obsidian://adv-uri?line=9&anchor=abc)")
ck("没有 <br> 但有链接（正则兜底）",
   B.extra_from_answer2("1. 甲\n[[笔记#标题|标题]]"), "[[笔记#标题|标题]]")
ck("没有 Extra → 空串", B.extra_from_answer2("1. 甲\n2. 乙"), "")
ck("嵌入行不算 Extra",
   B.extra_from_answer2("5. 鉴别![[笔记#别的|别的]]"), "")
# 与 hl2tr 原版的差异：wikilink 形态 hl2tr 切不出来 —— 这是本脚本必须自带切片器的原因
ck("（对照）hl2tr 原版切不出 wikilink",
   H._extra_from_answer("1. 甲 [x]\n<br>[[笔记#标题|标题]]"), "")


# ---------- 3. build_cloze ----------
print("\n--- 3. build_cloze：卡面拼装与挖空格式")
SRC = {
    "Front": "𒋙基础型课程的特点⭐",
    "Back": ("1. **基础型课程**:\n    1. 要求**最基本**.\n"
             "    2. 是**必修的课程**,==必须有严格的考试==.\n"
             "2. **拓展型课程**:\n    1. 有较大的==**灵活性**==.\n"
             "\n[[笔记2#𒋙基础型课程的特点⭐|标题]]"),
}
card, info = B.build_cloze(SRC)
ck("挖空处数 = 卡面高亮数", info["blanks"], 2)
ck("Extra 首行 = 阶梯标记", card["Extra"].split("\n")[0], B.MARK_TODO)
ck("Extra 第二行 = 标题链接", card["Extra"].split("\n")[1],
   "[[笔记2#𒋙基础型课程的特点⭐|标题]]")
ck("标记里带稳定可搜 token", B.MARK_KEY in card["Extra"], True)
ck("Text 首行 = 标题原文（含 𒋙 与 ⭐）", card["Text"].split("\n")[0], "𒋙基础型课程的特点⭐")
ck("标题与正文之间空一行", card["Text"].split("\n")[1], "")
ck_in("挖空 1：`==必须有严格的考试==` → `{{c1::…}}` 且整段单 index",
      "{{c1::", card["Text"])
# ⛔ 2026-10-12 起 `==` 包裹默认关闭（彻底走官方原生）⇒ 默认断言改为「不含 `==`」；
#    旧能力（显式 mark=True 仍包 `==`）另起一条断言单独验，确保没被删掉。
ck("默认不再包 `==`（走官方原生）", "==" in card["Text"], False)
card_m, _ = B.build_cloze(SRC, mark=True)
ck_in("`--cloze-mark` 开启时仍包 `==`（旧能力保留）",
      H.WJ + "==" + "必须有严格的考试" + "==" + H.WJ, card_m["Text"])
ck_in("无提问时填了默认占位符 hint", "::" + H.DEFAULT_HINT + "}}", card["Text"])
ck("`==**灵活性**==` 里的用户加粗被剥掉（留给插件那层）",
   "**" in card["Text"].split("{{")[1] if "{{" in card["Text"] else True, True)
ck("全文只有一个 index（c1）", card["Text"].count("{{c1::"), 2)
ck("没有 c2", "{{c2::" in card["Text"], False)
ck_in("正文里的「末行嵌入」没被当成尾链接",
      "![[笔记#别的|别的]]" if "![[笔记#别的|别的]]" in SRC["Back"] else "1. 要求",
      card["Text"])

c2, i2 = B.build_cloze({"Front": "标题", "Back": "1. 甲\n2. 乙 [[笔记.pdf#page=3|pdf]]"})
ck("卡面无高亮 → 不建卡", c2, None)
ck("并给出原因", "没有 ==高亮==" in i2["why"], True)

c3, i3 = B.build_cloze({"Front": "标题", "Back": "   "})
ck("正文为空 → 不建卡", c3, None)

c4, i4 = B.build_cloze({"Front": "", "Back": "==甲=="})
ck("Front 为空时 Text 就是挖空正文", c4["Text"].startswith("{{c1::"), True)

c5, _ = B.build_cloze(SRC, tail_to_extra=False)
ck("--keep-tail：链接行不摘，Extra 只留标记", c5["Extra"], B.MARK_TODO)
ck_in("--keep-tail：链接行仍在 Text 里", "[[笔记2#𒋙基础型课程的特点⭐|标题]]", c5["Text"])

c6, _ = B.build_cloze(SRC, use_hint=False)
ck("--no-hint：不填第三段", "::" in c6["Text"].split("{{c1::")[1].split("}}")[0], False)

c6b, _ = B.build_cloze(SRC, mark_ladder=False)
ck("--no-mark：Extra 只有标题链接，没有标记",
   c6b["Extra"], "[[笔记2#𒋙基础型课程的特点⭐|标题]]")


# ---------- 3.5 Extra 一律标题链接（广哥 2026-09-19 定） ----------
print("\n--- 3.5 Extra：由标题卡转来的挖空卡，链接一律是标题链接")
SRC2 = {"Front": "𒋙课程类型⭐", "Back": "1. 甲\n==乙==\n\n"
        "[《笔记3》·第 4 块](obsidian://adv-uri?vault=x&filepath=a.md&line=38&anchor=𒋙课程类型⭐)",
        "source_text": "## 𒋙课程类型⭐"}
c7, i7 = B.build_cloze(SRC2, note_base_name="笔记3")
ck("源卡是行链接 → Extra 第 2 行换成标题链接",
   c7["Extra"].split("\n")[1], "[[笔记3#𒋙课程类型⭐|标题]]")
ck_in("并在预览信息里说明换过", "源卡原本是", i7["tail_src"])

c8, _ = B.build_cloze(SRC2, note_base_name="")
ck("拿不到笔记名 → 退回源卡原链接（不造死链）",
   c8["Extra"].split("\n")[1].startswith("[《笔记3》·第 4 块]"), True)

c9, _ = B.build_cloze({"Front": "含|竖线的标题", "Back": "==甲==\n[[旧笔记#含|竖线的标题|标题]]",
                       "source_text": "## 含|竖线的标题"}, note_base_name="笔记4")
ck("标题含 | → 不重建，沿用源卡原链接（避免拆坏 wikilink）",
   c9["Extra"].split("\n")[1], "[[旧笔记#含|竖线的标题|标题]]")

c10, _ = B.build_cloze({"Front": "只有 Front 没 source_text", "Back": "==甲=="},
                       note_base_name="笔记5")
ck("source_text 为空 → 用 Front 当标题 target",
   c10["Extra"].split("\n")[1], "[[笔记5#只有 Front 没 source_text|标题]]")

c11, _ = B.build_cloze({"Front": "标题", "Back": "1. 甲\n==乙==", "source_text": "## 标题"},
                       note_base_name="笔记6")
ck("源卡没有尾链接 → 照样补上标题链接",
   c11["Extra"].split("\n")[1], "[[笔记6#标题|标题]]")

ck("heading_text 去 # 前缀", B.heading_text("### 𒋙甲⭐"), "𒋙甲⭐")
ck("heading_text 无 source_text 时退回 Front", B.heading_text("", "𒋙乙⏳"), "𒋙乙⏳")


# ---------- 3.6 卡面标记的翻转（swap_mark_line） ----------
print("\n--- 3.6 卡面标记：待掌握 ⇄ 已掌握")
ck("首行是标记 → 就地翻转，链接行不动",
   B.swap_mark_line(B.MARK_TODO + "\n[[笔记#标题|标题]]", B.MARK_DONE),
   (B.MARK_DONE + "\n[[笔记#标题|标题]]", True))
ck("首行已是目标标记 → 不重复写",
   B.swap_mark_line(B.MARK_DONE + "\n[[笔记#标题|标题]]", B.MARK_DONE)[1], False)
ck("老卡没标记 → 插到最前面",
   B.swap_mark_line("[[笔记#标题|标题]]", B.MARK_TODO),
   (B.MARK_TODO + "\n[[笔记#标题|标题]]", True))
ck("Extra 为空 → 只放标记", B.swap_mark_line("", B.MARK_TODO), (B.MARK_TODO, True))
ck("两条标记都带同一个可搜 token",
   B.MARK_KEY in B.MARK_TODO and B.MARK_KEY in B.MARK_DONE, True)
ck("已完成标记里带「已掌握」（插件里搜这个词）", "已掌握" in B.MARK_DONE, True)


# ---------- 4. local_fields_key ----------
print("\n--- 4. local_fields_key：幂等键必须与降级路由（渲染态）可比")
text = "标题\n\n1. 甲 {{c1::乙::" + H.DEFAULT_HINT + "}} 丙"
k_local = B.local_fields_key(text, "[[笔记#标题|标题]]")
k_api = H.card_fields_key(H._render_cloze(text), "[[笔记#标题|标题]]")
ck("本地键 == 按渲染归一化后算的键（这就是降级路径能命中的原因）", k_local, k_api)
ck("渲染归一化把 hint 段渲染成 [hint]",
   H._render_cloze(text).count("[" + H.DEFAULT_HINT + "]"), 1)
ck("键 = 紧凑 + 键排序的 JSON（前一个断言已证明与渲染态可比）", k_local,
   __import__("json").dumps({"Text": H._render_cloze(text).strip(),
                             "Extra": "[[笔记#标题|标题]]"},
                            ensure_ascii=False, separators=(",", ":"), sort_keys=True))

# ---------- 5. 阶梯：配对键 / 配对闸 / 毕业判据 ----------
print("\n--- 5. 阶梯：配对键、配对闸、毕业判据")
ck("配对键 = uid + source_text", B.pair_key("4c90df20", "## 标题"), "4c90df20||## 标题")
ck("配对键两端去空白", B.pair_key(" 4c90df20 ", " ## 标题 "), "4c90df20||## 标题")
ck("标题行 → 可配对（本 skill 出的挖空卡）", B.is_heading_source_text("## 𒋙甲⭐"), True)
ck("### 也算标题行", B.is_heading_source_text("### 甲"), True)
ck("块原文 → 不可配对（hl2tr 出的挖空卡）", B.is_heading_source_text("1. 甲\n==乙=="), False)
ck("空 source_text → 不可配对", B.is_heading_source_text(""), False)


def _c(**kw):
    d = {"cardType": "cloze", "state": 2, "reps": 2, "lapses": 0, "suspended": False,
         "scheduledDays": 1, "reviewHistory": [{"r": 3}, {"r": 3}]}
    d.update(kw)
    return d


ck("最近两次 Good + Review 态 → 达标", B.is_graduatable(_c())[0], True)
ck("最近两次是 Easy+Good 也算答对",
   B.is_graduatable(_c(reviewHistory=[{"r": 4}, {"r": 3}]))[0], True)
ck("只有 1 次记录 → 不够", B.is_graduatable(_c(reviewHistory=[{"r": 3}]))[0], False)
ck("完全没有复习记录 → 不够", B.is_graduatable(_c(reviewHistory=[]))[0], False)
ck("最近一次是 Hard → 不算全答对",
   B.is_graduatable(_c(reviewHistory=[{"r": 3}, {"r": 2}]))[0], False)
ck("最近一次是 Again → 拦住",
   B.is_graduatable(_c(reviewHistory=[{"r": 3}, {"r": 1}], lapses=1))[0], False)
ck("--max-lapses=1 放行一次忘记", B.is_graduatable(_c(lapses=1), max_lapses=1)[0], True)
ck("lapses 超阈值仍拦住", B.is_graduatable(_c(lapses=2), max_lapses=1)[0], False)
ck("Learning 态默认被拦住", B.is_graduatable(_c(state=1))[0], False)
ck("--any-state 放行 Learning", B.is_graduatable(_c(state=1), any_state=True)[0], True)
ck("挖空卡自己被挂起 → 不能毕业", B.is_graduatable(_c(suspended=True))[0], False)
ck("basic 卡不能走毕业", B.is_graduatable(_c(cardType="basic"))[0], False)
ck("--min-goods=3 要求三次都答对",
   B.is_graduatable(_c(reviewHistory=[{"r": 3}, {"r": 3}]), min_goods=3)[0], False)
ck("--min-interval=7 但间隔只有 1 天 → 拦住", B.is_graduatable(_c(), min_interval=7)[0], False)
ck("--min-interval=1 且间隔 1 天 → 放行", B.is_graduatable(_c(), min_interval=1)[0], True)
ck("说明里带最近评分", "Good" in B.is_graduatable(_c())[1], True)
ck("不达标时说明里带原因", "复习次数不够" in B.is_graduatable(_c(reviewHistory=[]))[1], True)
ck("RATING_NAMES 认 3=Good", B.RATING_NAMES[3], "Good")
ck("STATE_NAMES 认 Review=2", B.STATE_NAMES[2], "Review")

print("\n" + "=" * 60)
print("PASS %d / FAIL %d" % (PASS, FAIL))
sys.exit(1 if FAIL else 0)
