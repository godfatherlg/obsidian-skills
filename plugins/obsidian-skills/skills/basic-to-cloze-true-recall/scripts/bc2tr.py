# -*- coding: utf-8 -*-
"""bc2tr.py — True Recall 的「两级阶梯」工具。

阶梯：标题问答卡(basic) 记不住 → 挂起它 + 造一张高亮挖空卡(cloze) 当扶手
      挖空卡记住了 → 删掉挖空卡 + 取消挂起原来那张 basic 卡，重回标题卡

两个方向都在本脚本里：
  · 降级（basic → cloze）：`--list` / `--card=` / 笔记路径 / `--all`
  · 毕业（cloze → 删挖空 + 复活 basic）：`--pairs` / `--graduate`

配套 skill: basic-to-cloze-true-recall

用法
----
  python bc2tr.py --list                        列出全库 suspend 的 basic 卡（只读）
  python bc2tr.py --card=<卡id>[,<卡id>…]       预览：把这几张 basic 卡降级成 cloze
  python bc2tr.py "<md路径>"                    预览：该笔记名下所有 suspend 的 basic 卡
  python bc2tr.py --all                         预览：全库所有 suspend 的 basic 卡
  python bc2tr.py --card=<卡id> --apply         落盘：置源卡为 suspend + 建 cloze 卡
  python bc2tr.py --pairs                       列出所有「阶梯配对」与各自进度（只读）
  python bc2tr.py --graduate                    按阈值筛毕业候选（只读预览）
  python bc2tr.py --graduate --apply            执行：取消挂起源卡 + 软删挖空卡
  python bc2tr.py --graduate --card=<挖空卡id> --apply   点名毕业（不看阈值）

参数
----
  --apply                落盘（不带就只预览）
  --card=<id>[,<id>…]    点名卡：降级模式给 basic 卡 id，毕业模式给 cloze 卡 id
  --delete-source        降级时改为「软删源卡」（已废弃的旧行为，见下方"为什么源卡必须保留"）
  --no-suspend-source    降级时不动源卡的 suspended（默认会把它置为 suspend）
  --keep-tail            不把末尾链接行摘到 Extra（留在卡面里）
  --no-hint / --no-wj / --keep-cloze-bold   挖空格式开关
  --cloze-mark           给挖空内容与 hint 包 ==…==(⛔ 2026-10-12 起默认关闭,
                         加这个开关才开启;旧开关 --no-cloze-mark 已作废)
  --min-goods=N          毕业阈值：最近 N 次复习要全答对（Good/Easy），默认 2
  --max-lapses=N         毕业阈值：最多允许「忘记」次数（默认 0）
  --min-interval=N       毕业阈值：额外要求间隔 ≥ N 天（默认 0 = 不看；21 = 插件的 Mature 口径）
  --any-state            毕业时不要求进 Review 态（默认只认 state=2）
  --limit=N              单轮处理上限（默认 20）
  --token=<token>        显式给 Local API token

降级口径（卡对卡）
----------------
  Front(标题)  → 新卡 Text 的**第一行**（原样，保留 𒋙 与 ⭐⏳）
  Back(正文)   → 摘掉末尾那行跳转链接后，整段走 hl2tr.plan_cloze()：
                 `==x==` → `{{c1::x}}`（清文本格式；`$…$` 公式、`` `代码` ``、HTML 标签原样；内外 WJ、`==` 包裹、填占位符 hint）
                 一处高亮都没有 → **不建卡**，只报告
  卡型         → cloze（`builtin-cloze`，Text / Extra）；Extra **重建为两行：卡面标记行 + 标题链接行**（`--no-mark` 去标记行）
  source_text  → **继承源卡的 source_text**（= 标题行原文，含 `## `）
  源卡         → **默认保留**，并顺手置为 `suspended: true`（这就是"降级"的记号）

为什么源卡必须保留（2026-09-19 广哥定的"两级阶梯"）
------------------------------------------------
挖空卡只是**临时扶手**：记住了就把它删掉、把原来那张 basic 卡取消挂起、重回标题卡。
所以源卡一旦删掉就"没得恢复"—— 而插件的 Local API **没有任何 undelete 路由**
（71 条路由里没有；撤销删除只存在于 UI 的 Undo 通知里，且只在当次会话有效，
走的是内部方法 `cardStore.cards.restoreWithCascade()`，Python 侧够不着）。
⇒ 降级时**只挂起、不删除**。反过来说，basic 卡的卡面里本来就留着 `==`，
将来再想造挖空卡是零成本重跑，所以挖空卡可以放心删。

配对键 = （source_uid, source_text）
---------------------------------
挖空卡的 `source_text` 继承自源 basic 卡 ⇒ **两者共用同一行标题**。这既是
幂等比对里必须排除源卡 id 的原因，也正是毕业阶段识别"谁配谁"的现成钥匙。
⚠️ 只认 `source_text` 形如标题行（`^#{1,6}\\s`）的 cloze 卡，免得把
highlight-to-true-recall 建的（块原文当 source_text、标题是硬边界）误配进来。

幂等
----
降级：双键 ① `source_text`（继承的标题行）② 归一化 `{"Text","Extra"}`
      ⚠️ **比对时必须把源卡 id 排除掉** —— 源卡的 `source_text` 与新 cloze 卡完全
      相同，不排除就会把"源卡还在"误判成"新卡已存在"，一张都不建还不报错。
毕业：以「配对找得到 + 阈值达标」为准；跑完复跑必须「可毕业 0 张」。
"""
import os
import re
import sys
import json
import glob
import sqlite3

# ---------- 复用 highlight-to-true-recall 的骨架（token / Local API / 挖空格式） ----------
HL2TR_SCRIPTS = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "highlight-to-true-recall", "scripts")

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

if not os.path.isdir(HL2TR_SCRIPTS):
    raise SystemExit("找不到同族 skill 的脚本目录：%s\n"
                     "（本 skill 直接复用 hl2tr.py 的 Local API 与挖空格式，不复制骨架）"
                     % HL2TR_SCRIPTS)
sys.path.insert(0, HL2TR_SCRIPTS)
try:
    import hl2tr  # noqa: E402
except Exception as e:  # pragma: no cover
    raise SystemExit("导入 hl2tr.py 失败：%s" % e)

VAULT = hl2tr.VAULT
BASIC_TYPE = "builtin-basic"
CLOZE_TYPE = "builtin-cloze"
UID_FIELD = "flashcard_uid"
STATE_NAMES = {0: "New", 1: "Learning", 2: "Review", 3: "Relearning"}
RATING_NAMES = {1: "Again", 2: "Hard", 3: "Good", 4: "Easy"}

FM_RE = re.compile(r"\A---\r?\n(.*?)\r?\n---\r?\n?", re.S)
UID_RE = re.compile(r"^flashcard_uid:\s*[\"']?([a-f0-9]+)[\"']?\s*$", re.M)
HEAD_PREFIX_RE = re.compile(r"^#{1,6}[ \t]+")
# 标题里若含这些字符，wikilink 的 target 会被拆坏 ⇒ 只能退回"源卡原来那行链接"
LINK_UNSAFE = ("#", "|", "[", "]")

# ---------- 卡面标记（2026-09-19 广哥定：转来的挖空卡要有标记、学会了也要有标记） ----------
# 为什么标记放 Extra：cloze 模板是 `{{cloze:Text}}<br>{{Extra}}` ⇒ Extra 渲染在答案面
# 下半部分；而插件的卡片列表搜索是 `question.includes(q) || answer.includes(q)`，
# 而 cloze 卡的 answer = 渲染后的 Text + `<br>` + Extra ⇒ **标记进 Extra 就能被搜到**。
# ⇒ 在插件里搜 `TR阶梯卡` 筛出全部阶梯挖空卡，搜 `已掌握` 筛出可收口的那些。
# ⚠️ 标记属卡面内容：改了它 = 改了 Extra ⇒ 幂等字段键会变（但 source_text 键不变，
#    所以不会重复建卡；既有卡用 `--sync-marks` 补齐）。
MARK_KEY = "TR阶梯卡"                    # 稳定可搜的 token（两条标记都含它）
MARK_TODO = "🪜 " + MARK_KEY + " · 待掌握"
MARK_DONE = "🪜 " + MARK_KEY + " · ✅已掌握，可收口"

# 卡面末尾那行"跳回源笔记"的链接。命中即摘出来当 Extra。
TAIL_RES = (
    re.compile(r"^\[\[[^\[\]|]+(?:\|[^\[\]]+)?\]\]$"),               # [[笔记#标题|标题]]
    re.compile(r"^\[《[^》]*》·第\s*\d+\s*块\]\(obsidian://[^\s)]*\)$"),  # hl2tr 式行链接
    re.compile(r"^《[^》]*》·第\s*\d+\s*块$"),                          # 纯文字块名
    re.compile(r"^\[[^\]]+\]\(obsidian://[^\s)]*\)$"),                # 任何 adv-uri 链接行
)


# ---------- 纯函数（离线可测） ----------

def split_tail(back):
    """Back → (正文, 末尾链接行)。没有链接行时第二项为空串。"""
    lines = (back or "").split("\n")
    end = len(lines)
    while end > 0 and not lines[end - 1].strip():
        end -= 1
    if end == 0:
        return "", ""
    last = lines[end - 1].strip()
    if any(r.match(last) for r in TAIL_RES):
        return "\n".join(lines[:end - 1]).rstrip(), last
    return "\n".join(lines[:end]).rstrip(), ""


def extra_from_answer2(ans):
    """从卡面 answer 里切出真 Extra。

    cloze 模板是 `{{cloze:Text}}<br>{{Extra}}` ⇒ **最后一个 `<br>` 之后就是 Extra**，
    无条件取（⚠️ 不要像 hl2tr._extra_from_answer() 那样只认 `[《…》·第 N 块]` 开头
    的尾段 —— 卡片标记改成 `🪜 …` 开头后那个闸会失配，导致 Extra 被切空 ⇒
    复跑永远"需要改"、降级幂等也会错判）。
    没有 `<br>` 时才退回 `split_tail()`（行首必须是链接）。
    """
    ans = (ans or "").strip()
    if "<br>" in ans:
        return ans.rsplit("<br>", 1)[1].strip()
    return split_tail(ans)[1]


def heading_text(source_text, front=""):
    """标题行原文（`## 𒋙…⭐`）→ 标题文本（`𒋙…⭐`）。没有 source_text 时退回 Front。"""
    s = (source_text or "").strip()
    if s:
        return HEAD_PREFIX_RE.sub("", s).strip()
    return (front or "").strip()


def title_link_for(base, heading):
    """构造标题链接 `[[笔记名#标题原文|标题]]`（简写形态，别名固定「标题」两字）。

    标题含 `#` `|` `[` `]` 时返回空串 —— 那种 target 会被 wikilink 语法拆坏，
    调用方应退回源卡 `Back` 里原来那行链接（hq2tr 对这种情况就是这么降级的）。
    """
    if not base or not heading:
        return ""
    if any(ch in heading for ch in LINK_UNSAFE):
        return ""
    return "[[%s#%s|标题]]" % (base, heading)


def is_heading_source_text(st):
    """配对闸：只有 source_text 形如标题行（`## ` 开头）的 cloze 卡才可能是本 skill 产的。

    highlight-to-true-recall 建的 cloze 卡 source_text = 块原文（标题是硬边界，
    块原文永不以标题行开头）⇒ 这样就不会把那些卡误配进阶梯。
    """
    return bool(HEAD_PREFIX_RE.match((st or "").lstrip()))


def pair_key(uid, source_text):
    return "%s||%s" % ((uid or "").strip(), (source_text or "").strip())


def is_graduatable(card, min_goods=2, max_lapses=0, min_interval=0, any_state=False):
    """挖空卡「记住了」的判据 → (bool, 说明)。

    用户 2026-09-19 定：**最近两次都答对（Good 或 Easy）才算**。判据落实为：
      ① 最近 `min_goods`（默认 2）次复习的评分全部 ≥ 3（Good/Easy）；
         ⚠️ 评分来自 `GET /cards/:id` 的 `reviewHistory`，而插件是
         `getCardReviewHistory(id, 20)` —— **只给最近 20 条**（新→旧）⇒
         只能判"最近 N 次"，不能统计历史累计。
      ② `lapses == 0`（从没按过 Again）；
      ③ 未挂起；④ 进 Review 态（state=2，`--any-state` 可放开）；
      ⑤ `--min-interval=N`（默认 0=不看）时会额外要求 `scheduledDays ≥ N`。

    `--card=` 点名时**不走这个闸**（人说了算）。
    """
    if card.get("cardType") != "cloze":
        return False, "不是 cloze 卡"
    if card.get("suspended"):
        return False, "这张挖空卡自己是挂起状态"
    lapses = card.get("lapses") or 0
    ratings = [(h or {}).get("r") for h in (card.get("reviewHistory") or [])]
    recent = ratings[:min_goods]
    seen = ", ".join(RATING_NAMES.get(r, str(r)) for r in recent) if recent else "无"
    desc = "最近 %d 次：%s" % (len(recent), seen)

    if lapses > max_lapses:
        return False, "有忘记记录（lapses=%d > %d）｜%s" % (lapses, max_lapses, desc)
    if len(recent) < min_goods:
        return False, "复习次数不够（只有 %d 次记录，要 %d 次）｜%s" % (len(recent), min_goods, desc)
    if any((r or 0) < 3 for r in recent):
        return False, "最近这几次没全答对（要 Good 或 Easy）｜%s" % desc
    if not any_state and card.get("state") != 2:
        return False, "还没进 Review 态（state=%s）｜%s" % (
            STATE_NAMES.get(card.get("state"), card.get("state")), desc)
    if min_interval and (card.get("scheduledDays") or 0) < min_interval:
        return False, "间隔还不够（%s < %d 天）｜%s" % (
            card.get("scheduledDays") or 0, min_interval, desc)
    return True, "%s；state=%s；间隔 %s 天；lapses=%d" % (
        desc, STATE_NAMES.get(card.get("state"), card.get("state")),
        card.get("scheduledDays") or 0, lapses)


def build_cloze(src, strip_bold=True, use_hint=True, wj=True, mark=False, tail_to_extra=True,
                note_base_name="", mark_ladder=True):
    """一条 basic 卡的字段 → 一条 cloze 卡字段。

    入参 src 用 `Front`/`Back`/`source_text` 三个键。返回 (card, info)；
    不能转换（没高亮 / 空正文）时 card 为 None。

    `note_base_name` 非空时，Extra **重建为标题链接行**（广哥 2026-09-19 定），与下行 `mark_ladder` 的标记行合成两行结构。
    `mark_ladder`（默认开）会在 Extra **最前面**加一行卡面标记 `🪜 TR阶梯卡 · 待掌握`
    —— 用户 2026-09-19 要的"转过来的挖空卡要有标记"；`--no-mark` 可关。
    """
    title = (src.get("Front") or "").strip()
    back = src.get("Back") or ""
    info = {"title": title, "blanks": 0, "tail": "", "why": "", "tail_src": ""}

    if tail_to_extra:
        body, tail = split_tail(back)
        info["tail_src"] = tail
        link = title_link_for(note_base_name, heading_text(src.get("source_text"), title))
        if link:
            tail = link
            info["tail_src"] = ("标题链接（重建）"
                                + ("；源卡原本是：%s" % info["tail_src"][:40]
                                   if info["tail_src"] and info["tail_src"] != link else ""))
        elif tail:
            info["tail_src"] = "标题含 #|[] 或拿不到笔记名，沿用源卡原链接"
        if mark_ladder:
            tail = (MARK_TODO + "\n" + tail) if tail else MARK_TODO
    else:
        body, tail = back.rstrip(), ""
        if mark_ladder:
            tail = MARK_TODO      # --keep-tail：链接留卡面，但标记照样放 Extra
    info["tail"] = tail
    info["blanks"] = len(hl2tr.HL_RE.findall(body))

    if not body.strip():
        info["why"] = "正文为空"
        return None, info
    if info["blanks"] == 0:
        info["why"] = "卡面里没有 ==高亮==（本 skill 不猜挖空位置）"
        return None, info

    core, _pinfo = hl2tr.plan_cloze(body, strip_bold, use_hint, wj, mark)
    text = (title + "\n\n" + core) if title else core
    return {"Text": text, "Extra": tail, "blanks": info["blanks"],
            "title": title, "body": core, "tail": tail}, info


def basic_card_fields(c):
    """API 形态（question/answer）→ 字段形态（Front/Back/source_text）。

    ⚠️ basic 卡型的模板是 `{{Front}}` / `{{Back}}`，没有渲染变换 ⇒ API 给的
    question/answer 就是**存值原文**（`==` 都在）。这一点与 cloze 卡不同
    （cloze 的 question/answer 是渲染态）—— 混用会拿到被挖空的文本。
    """
    return {"Front": c.get("question") or "", "Back": c.get("answer") or "",
            "source_text": c.get("sourceText") or ""}


def local_fields_key(text, extra):
    """本地 Text/Extra → 与降级路由（渲染态）可比的那把键。"""
    return hl2tr.card_fields_key((hl2tr._render_cloze(text) or "").strip(),
                                 (extra or "").strip())


# ---------- 取卡 / 改卡 ----------

def card_info(cid):
    """GET /cards/:id（读插件内存，权威）。已软删 → None。"""
    try:
        d = hl2tr.api_call("/cards/%s" % cid)
    except RuntimeError as e:
        if "404" in str(e) or "not found" in str(e).lower():
            return None
        raise
    return d.get("data") or d


def cards_of_uid(uid):
    """GET /notes/cards?source_uid=（只返活卡，读插件内存）。"""
    d = hl2tr.api_call("/notes/cards?source_uid=%s&limit=200" % uid)
    return d.get("cards") or [], d.get("notePath") or "", d.get("noteName") or ""


def set_suspended(cid, flag):
    """POST /cards/:id/suspend —— body 是 `{suspended: boolean}`，挂起/取消挂起都走它。

    源码级核对（2026-09-19，handler G7）：body 缺 `suspended` 会 400
    "Body must contain { suspended: boolean }"；返回 `{cardId, suspended}`。
    """
    d = hl2tr.api_call("/cards/%s/suspend" % cid, {"suspended": bool(flag)})
    return bool(d.get("suspended")) if isinstance(d, dict) else None


def read_uid(path):
    try:
        text = open(path, encoding="utf-8").read()
    except Exception:
        return None
    m = FM_RE.match(text)
    if not m:
        return None
    m2 = UID_RE.search(m.group(1))
    return m2.group(1) if m2 else None


def _db_path():
    cands = [c for c in glob.glob(os.path.join(VAULT, ".true-recall", "*", "*.db"))
             if not c.endswith(".bak")]
    if not cands:
        return None
    cands.sort(key=os.path.getmtime, reverse=True)
    return cands[0]


def _ro_db():
    db = _db_path()
    if not db:
        raise SystemExit("找不到 True Recall 数据库(.true-recall/*/*.db)")
    con = sqlite3.connect("file:%s?mode=ro" % db.replace("\\", "/"), uri=True)
    con.row_factory = sqlite3.Row
    return con


def scan_db_suspended():
    """只读读库：全库 suspended=1 的活 basic 卡 → [card_id]。"""
    con = _ro_db()
    try:
        q = ("select c.id from cards c join notes n on n.id = c.note_id "
             "where c.suspended = 1 and c.deleted_at is null and n.deleted_at is null "
             "and n.note_type_id = ?")
        return [r[0] for r in con.execute(q, (BASIC_TYPE,))]
    finally:
        con.close()


def scan_pairs_db():
    """只读读库找出「阶梯配对」候选 → [(cloze_id, uid, source_text, basic_id)]。

    配对键 = (source_uid, source_text)；只认 source_text 是标题行的 cloze 卡。
    磁盘快照可能滞后，调用方随后逐张 GET /cards/:id 复核（那才是插件内存）。
    """
    con = _ro_db()
    try:
        basics = {}
        for r in con.execute("""select c.id cid, n.source_uid uid, n.source_text st
                                from cards c join notes n on n.id = c.note_id
                                where c.deleted_at is null and n.deleted_at is null
                                and n.note_type_id = ?""", (BASIC_TYPE,)):
            basics[pair_key(r["uid"], r["st"])] = r["cid"]
        out = []
        for r in con.execute("""select c.id cid, n.source_uid uid, n.source_text st
                                from cards c join notes n on n.id = c.note_id
                                where c.deleted_at is null and n.deleted_at is null
                                and n.note_type_id = ?
                                order by n.created_at""", (CLOZE_TYPE,)):
            if not is_heading_source_text(r["st"]):
                continue
            k = pair_key(r["uid"], r["st"])
            if k in basics:
                out.append((r["cid"], r["uid"], r["st"], basics[k]))
        return out
    finally:
        con.close()


_NOTE_BASE_CACHE = {}
_FK_CACHE = {}


def pairs_of_uid(uid):
    """API 权威：某一篇笔记里的阶梯配对 → [(cloze_id, uid, source_text, basic_id)]。

    走 `GET /notes/cards?source_uid=`（读插件内存，**没有磁盘滞后**）+ 逐张
    `GET /cards/:id` 取 `sourceText`。这是排查"全库扫描看不见刚改的卡"时的正路。
    """
    cards, _p, _n = cards_of_uid(uid)
    basics, clozes = {}, []
    for c in cards:
        one = card_info(c.get("id"))
        if not one:
            continue
        st = (one.get("sourceText") or "").strip()
        if c.get("cardType") == "basic":
            basics[pair_key(uid, st)] = c.get("id")
        elif c.get("cardType") == "cloze" and is_heading_source_text(st):
            clozes.append((c.get("id"), st))
    out = []
    for cid, st in clozes:
        k = pair_key(uid, st)
        if k in basics:
            out.append((cid, uid, st, basics[k]))
    return out


def snapshot_lag():
    """库快照滞后检测 → (api_total, db_alive, lag)。

    `GET /cards` 的 `total` 是**插件内存**里的活卡数（权威）；磁盘快照可能少几张
    （刚建/刚删的还没落盘）。差 ≥1 就说明全库扫描可能漏卡 —— 必须报出来，
    否则 `--pairs` / `--graduate` 会给出"看起来什么都没有"的假阴性。
    """
    try:
        d = hl2tr.api_call("/cards?limit=1")
        api_total = int(d.get("total") or 0)
    except Exception:
        return None, None, 0
    try:
        con = _ro_db()
        try:
            db_alive = con.execute(
                "select count(*) from cards where deleted_at is null").fetchone()[0]
        finally:
            con.close()
    except Exception:
        return api_total, None, 0
    return api_total, db_alive, max(0, api_total - db_alive)


def warn_lag():
    api_total, db_alive, lag = snapshot_lag()
    if lag:
        print("⚠️ 库快照滞后：插件内存 %s 张活卡 / 磁盘快照 %s 张（差 %d）⇒ 本次全库扫描"
              "可能漏掉刚改动的卡。等几秒重跑，或改用「点名」："
              "`--pairs <笔记路径>` / `--graduate --card=<挖空卡id>`（这两条读插件内存，无滞后）。\n"
              % (api_total, db_alive, lag))
    return lag


def scan_pairs(paths=()):
    """配对候选：给了笔记路径就走 API 精确枚举；否则读库快照（并报滞后）。"""
    if paths:
        out = []
        for p in paths:
            full = p if os.path.isabs(p) else os.path.join(VAULT, p)
            if not os.path.exists(full):
                raise SystemExit("文件不存在：%s" % full)
            uid = read_uid(full)
            if not uid:
                print("  ~ %s 没有 frontmatter %s，跳过" % (p, UID_FIELD))
                continue
            hit = pairs_of_uid(uid)
            print("  · %s（uid %s）：配对 %d 对" % (os.path.basename(full), uid, len(hit)))
            out += hit
        print()
        return out
    warn_lag()
    return scan_pairs_db()


def note_base(uid):
    """该 uid 对应笔记的 basename（取自 GET /notes/cards 的 noteName）。"""
    if uid in _NOTE_BASE_CACHE:
        return _NOTE_BASE_CACHE[uid]
    base = ""
    try:
        _cards, _p, name = cards_of_uid(uid)
        base = os.path.splitext((name or "").strip())[0]
    except Exception:
        pass
    _NOTE_BASE_CACHE[uid] = base
    return base


def find_basic_of(cloze_uid, cloze_source_text):
    """按（同 uid + 同 source_text）找配对的 basic 卡 → (basic_id, suspended) 或 ("", None)。"""
    cards, _p, _n = cards_of_uid(cloze_uid)
    needle = (cloze_source_text or "").strip()
    for x in cards:
        if x.get("cardType") != "basic":
            continue
        one = card_info(x["id"])
        if one and (one.get("sourceText") or "").strip() == needle:
            return x["id"], bool(one.get("suspended"))
    return "", None


def fields_keys_cached(uid):
    """该笔记名下活卡的「字段键」集合（按渲染态归一化，1 次 API 调用就够）。

    只用于**预览**时提示"库里已有同款 cloze 卡"；落盘时的判定仍走
    existing_keys() 那条双键路线（那边还会额外比 source_text 并排除源卡 id）。
    """
    if uid in _FK_CACHE:
        return _FK_CACHE[uid]
    out = set()
    try:
        cards, _p, _n = cards_of_uid(uid)
        for c in cards:
            out.add(hl2tr.card_fields_key((c.get("question") or "").strip(),
                                          extra_from_answer2(c.get("answer") or "").strip()))
    except Exception:
        pass
    _FK_CACHE[uid] = out
    return out


def existing_keys(uid, exclude=()):
    """该笔记名下活卡的幂等键：(字段键集合, source_text 集合)。

    ⚠️ exclude 里必须放**源卡 id** —— 源 basic 卡与本 skill 建的 cloze 卡共用同一行
    标题当 source_text，不排除就会把"源卡还在"当成"新卡已存在"，一张都不建还不报错。
    """
    cards, _p, _n = cards_of_uid(uid)
    fk, sk = set(), set()
    for c in cards:
        cid = c.get("id")
        if not cid or cid in exclude:
            continue
        st = ""
        try:
            one = hl2tr.api_call("/cards/%s" % cid)
            st = ((one.get("data") or one).get("sourceText") or "")
        except Exception:
            pass
        extra = extra_from_answer2(c.get("answer") or "")
        fk.add(hl2tr.card_fields_key((c.get("question") or "").strip(), extra.strip()))
        if st:
            sk.add(st.strip())
    return fk, sk


# ---------- 模式一：降级（basic → cloze） ----------

def gather_targets(argv):
    """返回 (mode, targets)。targets = [(card_id, 来源说明)]。"""
    ids, paths = [], []
    for a in argv:
        if a.startswith("--card="):
            ids += [x.strip() for x in a.split("=", 1)[1].split(",") if x.strip()]
        elif not a.startswith("--"):
            paths.append(a)
    if ids:
        return "card", [(i, "--card") for i in ids]
    if paths:
        out = []
        for p in paths:
            full = p if os.path.isabs(p) else os.path.join(VAULT, p)
            if not os.path.exists(full):
                raise SystemExit("文件不存在：%s" % full)
            uid = read_uid(full)
            if not uid:
                print("  ~ %s 没有 frontmatter %s，跳过" % (p, UID_FIELD))
                continue
            cards, _np, _nn = cards_of_uid(uid)
            hit = [c["id"] for c in cards
                   if c.get("suspended") and c.get("cardType") == "basic"]
            print("  · %s（uid %s）：活卡 %d 张，其中 suspend 的 basic %d 张"
                  % (os.path.basename(full), uid, len(cards), len(hit)))
            out += [(i, os.path.basename(full)) for i in hit]
        return "paths", out
    return "all", [(i, "全库扫描") for i in scan_db_suspended()]


def cmd_list():
    warn_lag()
    ids = scan_db_suspended()
    print("全库 suspend 的 basic 卡：%d 张" % len(ids))
    for i in ids:
        c = card_info(i)
        if not c:
            continue
        print("  %s  %-18s %s" % (i, (c.get("sourceText") or "(无 source_text)")[:18],
                                  (c.get("question") or "")[:60]))
    print("\n降级：python bc2tr.py --card=<卡id>        （加 --apply 落盘）")
    print("⚠️ --card= 必须给上面那一整串完整 id —— 卡 id 是 36 位 UUID，"
          "只给前 8 位会 404，并被报成「已处理过·源 basic 卡已不在活跃卡里」（误导）。")


def run_downgrade(argv, opts):
    try:
        st = hl2tr.api_call("/status", timeout=5)
        print("Local API 在线：", json.dumps(st, ensure_ascii=False)[:100])
    except RuntimeError as e:
        raise SystemExit(str(e))

    mode, targets = gather_targets(argv)
    print("扫描范围：%s | 命中 suspend 的 basic 卡 %d 张 | 写入路线：插件 Local API(端口 %d)"
          % ({"card": "--card 点名", "paths": "点名笔记", "all": "全库"}[mode],
             len(targets), hl2tr.api_port()))
    print("挖空格式：同 highlight-to-true-recall（清文本格式 / 公式·代码·HTML 标签原样 / 内外 WJ / `==` 包裹 / %s） | 源卡：%s"
          % ("填占位符 hint" if opts["use_hint"] else "不填 hint",
             "软删（--delete-source）" if opts["delete_source"]
             else ("保留原样（--no-suspend-source）" if opts["no_suspend_source"]
                   else "保留并置为 suspend")))
    print()

    if not targets:
        print("没有命中任何 suspend 的 basic 卡。")
        return

    plans, skipped, already = [], [], []
    if len(targets) > opts["limit"]:
        print("⚠️ 命中 %d 张，本次只处理前 %d 张（用 --limit=N 调整）\n"
              % (len(targets), opts["limit"]))
    for cid, src_tag in targets[:opts["limit"]]:
        c = card_info(cid)
        if not c:
            already.append({"cid": cid, "tag": src_tag})
            continue
        if c.get("cardType") != "basic":
            skipped.append({"cid": cid, "tag": src_tag,
                            "why": "不是 basic 卡（cardType=%s）" % c.get("cardType")})
            continue
        card, info = build_cloze(basic_card_fields(c), opts["strip_bold"], opts["use_hint"],
                                 opts["wj"], opts["mark"], opts["tail_to_extra"],
                                 note_base(c.get("sourceUid") or ""), opts["mark_ladder"])
        if not card:
            skipped.append({"cid": cid, "tag": src_tag, "why": info["why"]})
            continue
        plans.append({"cid": cid, "src_tag": src_tag, "src": c, "card": card, "info": info,
                      "uid": c.get("sourceUid") or "", "suspended": bool(c.get("suspended")),
                      "dup_pre": local_fields_key(card["Text"], card["Extra"])
                      in fields_keys_cached(c.get("sourceUid") or "")})

    for r in plans:
        info = r["info"]
        print("=" * 78)
        print("源卡 %s（%s）| 卡型 basic | suspend=%s | uid=%s"
              % (r["cid"][:8], r["src_tag"], r["suspended"], r["uid"]))
        print("标题：%s" % info["title"][:80])
        print("挖空：%d 处（全部 c1，合成一张卡）" % info["blanks"])
        for m in hl2tr.CLOZE_RE.finditer(r["card"]["body"]):
            inner = m.group(1).replace(hl2tr.WJ, "").replace("==", "")
            print("   · 挖空：%s" % inner[:60])
        t = r["card"]["Text"].replace("\n", " ⏎ ")
        print("新卡 Text：%s%s" % (t[:170], "…" if len(t) > 170 else ""))
        print("新卡 Extra：%s" % (r["card"]["Extra"] or "(无)"))
        if info.get("tail_src"):
            print("           来源：%s" % info["tail_src"])
        if opts["delete_source"]:
            act = "软删源卡（不可恢复）"
        elif opts["no_suspend_source"] or r["suspended"]:
            act = "源卡保持不动"
        else:
            act = "把源卡置为 suspend（保留它）"
        print("计划：建 1 张 cloze 卡；%s%s" % (act, "" if opts["apply"] else "（落盘时）"))
        if r["dup_pre"]:
            print("⚠️ 库里已有同款 cloze 卡 → 落盘时会跳过建卡（幂等生效，不是错误）")
    for s in skipped:
        print("=" * 78)
        print("跳过 %s（%s）：%s" % (s["cid"][:8], s["tag"], s["why"]))
    for a in already:
        print("取不到 %s（%s）：卡不存在 / id 不完整（须给整串 36 位）/ 源 basic 卡已不在活跃卡里"
              % (a["cid"][:8], a["tag"]))

    print("=" * 78)
    print("合计：可转 %d 张（其中 %d 张库里已有同款、落盘会跳过）/ 已处理过 %d 张 / 跳过 %d 张"
          % (len(plans), sum(1 for r in plans if r["dup_pre"]), len(already), len(skipped)))
    if not opts["apply"]:
        print("[预览] 未做任何写入。确认无误后加 --apply。")
        return
    if not plans:
        print("本轮无需建卡（可转 0 张）—— 复跑出现这一行即幂等成立。")
        return

    done = dup = fail = sused = notsused = susfail = deleted = delfail = 0
    for r in plans:
        uid, card = r["uid"], r["card"]
        if not uid:
            print("  ✗ %s：源卡没有 sourceUid，跳过" % r["cid"][:8])
            fail += 1
            continue
        src_st = (r["src"].get("sourceText") or "").strip()
        fk, sk = existing_keys(uid, exclude=(r["cid"],))
        key = local_fields_key(card["Text"], card["Extra"])
        if (src_st and src_st in sk) or key in fk:
            dup += 1
            print("  = %s 已有同款 cloze 卡，跳过建卡" % r["cid"][:8])
        else:
            payload = {"cards": [{"question": card["Text"], "answer": card["Extra"],
                                  "card_type": "cloze", "source_uid": uid,
                                  "source_text": src_st}],
                       "source_uid": uid}
            try:
                res = hl2tr.api_call("/cards", payload)
                n = int(res.get("created") or 0)
                done += n
                if n == 0:
                    fail += 1
                    print("  ✗ %s：建卡返回 created=0" % r["cid"][:8])
                else:
                    print("  + %s 已建 cloze 卡（配对键 = 这行标题）" % r["cid"][:8])
            except RuntimeError as e:
                fail += 1
                print("  ✗ %s 建卡失败：%s" % (r["cid"][:8], e))

        if opts["delete_source"]:
            try:
                hl2tr.api_call("/cards/%s" % r["cid"], method="DELETE")
                deleted += 1
                print("  - %s 源 basic 卡已软删（⚠️ 无 undelete 路由，救不回来）" % r["cid"][:8])
            except RuntimeError as e:
                delfail += 1
                print("  ✗ %s 软删源卡失败：%s" % (r["cid"][:8], e))
            continue
        if opts["no_suspend_source"] or r["suspended"]:
            notsused += 1
            continue
        try:
            set_suspended(r["cid"], True)
            sused += 1
            print("  ~ %s 源 basic 卡已置为 suspend（留着，等挖空卡毕业再放出来）"
                  % r["cid"][:8])
        except RuntimeError as e:
            susfail += 1
            print("  ✗ %s 置 suspend 失败：%s" % (r["cid"][:8], e))

    print("建卡：新增 %d 张 / 已存在跳过 %d 张 / 失败 %d 张" % (done, dup, fail))
    if opts["delete_source"]:
        print("源卡：已软删 %d 张 / 删除失败 %d 张" % (deleted, delfail))
    else:
        print("源卡：新置 suspend %d 张 / 本来就不动 %d 张 / 失败 %d 张"
              % (sused, notsused, susfail))
    print("\n⚠️ 请立刻原地复跑同一条命令，幂等成立应看到其一：")
    print("    · 源卡保留（默认）→「可转 N 张（其中 N 张已有同款）/ 建卡：新增 0 张」")
    print("    · 源卡已软删（--delete-source）→「可转 0 张 / 已处理过 N 张」")
    print("  看到「新增 N>0」就停手查键（先查是不是没排除源卡 id）。")
    print("下一步：挖空卡记住了 → `--pairs` 看配对 → `--graduate --apply` 收口。")


# ---------- 模式二：配对总览 ----------

def run_pairs(argv=()):
    paths = [a for a in argv if not a.startswith("--")]
    cands = scan_pairs(paths)
    print("阶梯配对（同 uid + 同标题行）：%d 对\n" % len(cands))
    if not cands:
        print("（没有配对。配对要求：同一篇笔记里，basic 卡与 cloze 卡的 source_text 是同一行标题）")
        return
    for cloze_id, uid, st, basic_id in cands:
        c, b = card_info(cloze_id), card_info(basic_id)
        print("=" * 78)
        print("标题：%s" % heading_text(st)[:70])
        print("  笔记 uid：%s（%s）" % (uid, note_base(uid) or "?"))
        if c:
            hist = ", ".join(RATING_NAMES.get((h or {}).get("r"), "?")
                             for h in (c.get("reviewHistory") or [])[:5]) or "还没复习过"
            print("  挖空卡 %s：state=%s reps=%s lapses=%s suspended=%s 间隔=%s 天"
                  % (cloze_id[:8], STATE_NAMES.get(c.get("state"), c.get("state")),
                     c.get("reps"), c.get("lapses"), c.get("suspended"),
                     c.get("scheduledDays") or 0))
            print("           最近复习（新→旧）：%s" % hist)
            ok, why = is_graduatable(c)
            print("           毕业判据：%s" % ("✅ 达标 —— %s" % why if ok else "⏳ 还没到 —— " + why))
        else:
            print("  挖空卡 %s：已不在活跃卡里" % cloze_id[:8])
        if b:
            print("  原 basic 卡 %s：suspended=%s（%s）"
                  % (basic_id[:8], b.get("suspended"),
                     "等毕业" if b.get("suspended") else "⚠️ 已放出来，不是阶梯状态"))
        else:
            print("  原 basic 卡 %s：已不在活跃卡里（⚠️ 阶梯断了，没得恢复）" % basic_id[:8])
    print("\n收口：python bc2tr.py --graduate [--card=<挖空卡id>] --apply")


def swap_mark_line(extra, target):
    """把 Extra **首行**的标记换成 target（首行没有标记就插到最前面）。

    返回 (新 Extra, 是否发生变化)。首行以外的内容一字不动（标题链接那行保住）。
    """
    extra = extra or ""
    lines = extra.split("\n")
    if lines and MARK_KEY in lines[0]:
        if lines[0].strip() == target:
            return extra, False
        lines[0] = target
        return "\n".join(lines), True
    if extra.strip():
        return target + "\n" + extra, True
    return target, True


def run_sync_marks(argv, opts):
    """把阶梯挖空卡 Extra 首行的标记刷成当前状态（待掌握 / ✅已掌握可收口）。

    只走 `POST /cards/:id/update {answer}` —— cloze 分支只写 `fields.Extra`，
    不动 Text、不动 FSRS 调度。用途：① 老卡补标记；② 达标后翻成 ✅ 让用户在
    插件里一搜就看见（搜 `TR阶梯卡` = 全部阶梯卡，搜 `已掌握` = 可收口的）。
    """
    try:
        st = hl2tr.api_call("/status", timeout=5)
        print("Local API 在线：", json.dumps(st, ensure_ascii=False)[:100])
    except RuntimeError as e:
        raise SystemExit(str(e))

    paths = [a for a in argv if not a.startswith("--")]
    print("判据（决定打哪个标记）：最近 %d 次全答对 + lapses ≤ %d%s\n"
          % (opts["min_goods"], opts["max_lapses"],
             "" if opts["any_state"] else " + 进 Review 态"))
    todo, ok, bad = [], [], []
    for cloze_id, uid, stx, basic_id in scan_pairs(paths):
        c = card_info(cloze_id)
        if not c:
            bad.append({"cid": cloze_id, "why": "挖空卡不在活跃卡里"})
            continue
        ready, why = is_graduatable(c, opts["min_goods"], opts["max_lapses"],
                                    opts["min_interval"], opts["any_state"])
        cur_extra = extra_from_answer2(c.get("answer") or "")
        target = MARK_DONE if ready else MARK_TODO
        new_extra, changed = swap_mark_line(cur_extra, target)
        row = {"cid": cloze_id, "st": stx, "ready": ready, "why": why,
               "old": cur_extra.split("\n")[0] if cur_extra else "(无)",
               "new": new_extra.split("\n")[0], "extra": new_extra, "changed": changed}
        (ok if ready else todo).append(row)

    for r in ok + todo:
        print("=" * 78)
        print("%s %s：%s" % ("✅" if r["ready"] else "⏳", r["cid"][:8], heading_text(r["st"])[:56]))
        print("   判据：%s" % r["why"])
        print("   Extra 首行：%s  →  %s%s"
              % (r["old"], r["new"], "（要改）" if r["changed"] else "（本来就是）"))
    for r in bad:
        print("-" * 78)
        print("跳过 %s：%s" % (r["cid"][:8], r["why"]))

    need = [r for r in ok + todo if r["changed"]]
    print("=" * 78)
    print("合计：阶梯卡 %d 张（已掌握 %d / 待掌握 %d）｜需要改标记 %d 张"
          % (len(ok) + len(todo), len(ok), len(todo), len(need)))
    if not opts["apply"]:
        print("[预览] 未做任何写入。确认无误后加 --apply。")
        return
    if not need:
        print("本轮无需改标记（需要改 0 张）—— 复跑出现这一行即幂等成立。")
        return
    done = fail = 0
    for r in need:
        try:
            hl2tr.api_call("/cards/%s/update" % r["cid"], {"answer": r["extra"]})
            done += 1
            print("  ~ %s 标记已刷成「%s」" % (r["cid"][:8], r["new"]))
        except RuntimeError as e:
            fail += 1
            print("  ✗ %s 改标记失败：%s" % (r["cid"][:8], e))
    print("改标记：成功 %d 张 / 失败 %d 张" % (done, fail))
    print("\n⚠️ 请立刻复跑 `--sync-marks`：必须看到「需要改标记 0 张」。")
    print("插件里怎么看：卡片列表搜索框输入 `%s` 或 `已掌握`。" % MARK_KEY)


# ---------- 模式三：毕业（cloze → 删挖空 + 复活 basic） ----------

def run_graduate(argv, opts):
    try:
        st = hl2tr.api_call("/status", timeout=5)
        print("Local API 在线：", json.dumps(st, ensure_ascii=False)[:100])
    except RuntimeError as e:
        raise SystemExit(str(e))

    forced = []
    for a in argv:
        if a.startswith("--card="):
            forced += [x.strip() for x in a.split("=", 1)[1].split(",") if x.strip()]
    forced_set = set(forced)

    if forced:
        items = []
        for cid in forced:
            c = card_info(cid)
            if not c:
                print("  ✗ %s 不在活跃卡里，跳过" % cid[:8])
                continue
            items.append((cid, c.get("sourceUid") or "", c.get("sourceText") or "", c))
        print("== 点名毕业（不看阈值）%d 张 ==" % len(items))
    else:
        items = []
        paths = [a for a in argv if not a.startswith("--")]
        for cloze_id, uid, stx, _basic in scan_pairs(paths):
            c = card_info(cloze_id)
            if c:
                items.append((cloze_id, uid, stx, c))
        print("== 按阈值筛毕业候选 ==")
        print("判据：最近 %d 次复习全答对（Good/Easy）+ lapses ≤ %d%s%s（`--card=` 点名可绕过）"
              % (opts["min_goods"], opts["max_lapses"],
                 "" if opts["any_state"] else " + 进 Review 态",
                 (" + 间隔 ≥ %d 天" % opts["min_interval"]) if opts["min_interval"] else ""))
    print()

    todo, wait, broken = [], [], []
    for cloze_id, uid, stx, c in items:
        try:
            basic_id, b_sus = find_basic_of(uid, stx)
        except RuntimeError as e:
            broken.append({"cid": cloze_id, "c": c, "why": "查配对失败：%s" % e})
            continue
        if not basic_id:
            broken.append({"cid": cloze_id, "c": c,
                           "why": "找不到配对的 basic 卡（同 uid + 同 source_text）"})
            continue
        ok, why = is_graduatable(c, opts["min_goods"], opts["max_lapses"],
                                 opts["min_interval"], opts["any_state"])
        if cloze_id in forced_set:
            ok, why = True, why + "（点名，不看阈值）"
        row = {"cid": cloze_id, "uid": uid, "st": stx, "basic": basic_id,
               "b_sus": b_sus, "c": c, "why": why}
        (todo if ok else wait).append(row)

    for r in todo:
        c = r["c"]
        print("=" * 78)
        print("毕业 %s：%s" % (r["cid"][:8], heading_text(r["st"])[:60]))
        print("  挖空卡 state=%s reps=%s lapses=%s ← %s"
              % (STATE_NAMES.get(c.get("state"), c.get("state")), c.get("reps"),
                 c.get("lapses"), r["why"]))
        print("  原卡 %s suspended=%s" % (r["basic"][:8], r["b_sus"]))
        print("  计划：取消挂起原卡（复习进度保留）→ 软删挖空卡%s"
              % ("" if opts["apply"] else "（落盘时执行）"))
        print("        收口后原卡会立刻变 due（它的 due 早就在过去），下一次复习就会遇到它")
    for r in wait:
        print("-" * 78)
        print("还不到时候 %s：%s" % (r["cid"][:8], r["why"]))
    for r in broken:
        print("-" * 78)
        print("配不上 %s：%s" % (r["cid"][:8], r["why"]))

    print("=" * 78)
    print("合计：可毕业 %d 张 / 还没到 %d 张 / 配不上 %d 张"
          % (len(todo), len(wait), len(broken)))
    if not opts["apply"]:
        print("[预览] 未做任何写入。确认无误后加 --apply。"
              "（只想放其中几张就 --graduate --card=<挖空卡id> --apply）")
        return
    if not todo:
        print("本轮无需收口（可毕业 0 张）—— 复跑出现这一行即幂等成立。")
        return

    okn = failn = 0
    for r in todo:
        try:
            set_suspended(r["basic"], False)
            print("  ^ %s 原卡已取消挂起（复习进度保留）" % r["basic"][:8])
        except RuntimeError as e:
            failn += 1
            print("  ✗ %s 取消挂起失败；为避免两头都活跃，跳过删挖空卡：%s"
                  % (r["basic"][:8], e))
            continue
        try:
            hl2tr.api_call("/cards/%s" % r["cid"], method="DELETE")
            okn += 1
            print("  - %s 挖空卡已软删（内容还在原卡的 == 里，随时能重造）" % r["cid"][:8])
        except RuntimeError as e:
            failn += 1
            print("  ✗ %s 删挖空卡失败（原卡已放出，现在两张都在）：%s" % (r["cid"][:8], e))
    print("毕业：成功 %d 张 / 失败 %d 张" % (okn, failn))
    print("\n⚠️ 请立刻原地复跑 `--graduate`：必须看到「可毕业 0 张」。")
    print("⚠️ 挖空卡留了空壳 note（预期）；要清在 Obsidian 命令面板跑 QuickAdd 宏 TR清理。")


# ---------- 主 ----------

def main():
    argv = sys.argv[1:]
    opts = {
        "apply": "--apply" in argv,
        "delete_source": "--delete-source" in argv,
        "no_suspend_source": "--no-suspend-source" in argv,
        "strip_bold": "--keep-cloze-bold" not in argv,
        "use_hint": "--no-hint" not in argv,
        "wj": "--no-wj" not in argv,
        # ⛔ 2026-10-12 广哥定：彻底走官方原生 ⇒ `==` 包裹默认关闭，
        #    开关语义翻转：`--cloze-mark` 才是开启（旧开关 `--no-cloze-mark` 已作废）。
        "mark": "--cloze-mark" in argv,
        "tail_to_extra": "--keep-tail" not in argv,
        "mark_ladder": "--no-mark" not in argv,
        "any_state": "--any-state" in argv,
        "min_goods": 2,
        "max_lapses": 0,
        "min_interval": 0,
        "limit": 20,
    }
    for a in argv:
        if a.startswith("--limit="):
            opts["limit"] = int(a.split("=", 1)[1])
        elif a.startswith("--min-goods="):
            opts["min_goods"] = int(a.split("=", 1)[1])
        elif a.startswith("--min-interval="):
            opts["min_interval"] = int(a.split("=", 1)[1])
        elif a.startswith("--max-lapses="):
            opts["max_lapses"] = int(a.split("=", 1)[1])
    if not opts["wj"] and opts["mark"]:
        opts["mark"] = False
        print("⚠️ --no-wj 会连带关掉挖空的 `==` 包裹（只包 `==` 不插 WJ，加粗会整体失效）")

    if "--list" in argv:
        cmd_list()
        return
    if "--pairs" in argv:
        run_pairs(argv)
        return
    if "--sync-marks" in argv:
        run_sync_marks(argv, opts)
        return
    if "--graduate" in argv:
        run_graduate(argv, opts)
        return
    run_downgrade(argv, opts)


if __name__ == "__main__":
    main()
