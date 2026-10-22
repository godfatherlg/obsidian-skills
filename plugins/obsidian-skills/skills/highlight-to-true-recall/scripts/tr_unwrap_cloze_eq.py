# -*- coding: utf-8 -*-
"""一次性迁移：剥掉存量 cloze 卡面里脚本包的那两层 `==`（2026-10-12 彻底走官方原生）。

⚠️ 为什么**不做**「拿 source_text 重算卡面」：
   实测 156 张卡里只有 63 张满足 `plan_cloze(source_text, mark=True) == 库内 Text`；
   其余 92 张不等（库里有语义 hint `%%…%%` 生成的第三段，而源块里已没有对应 `%%`）
   ⇒ 重算会**把用户已有的语义 hint 冲掉**，不可逆。所以改成**纯文本剥离**：
   只剥包裹的 `==` 与配套的内层 WJ，**正文与 hint 文字一个字不动**。

剥离规则（每个 `{{cN::BODY::HINT}}` 单独处理）
  · BODY：`WJ==X==WJ` 或 `WJ==WJ X WJ==WJ`  → `WJ X WJ`（外层 WJ **必须保留**，
    它是给插件答案面那对 `**` 用的，与 `==` 无关）
  · HINT：`==X==` / `==WJ X WJ==` / `==WJ X==` / `==X WJ==` → `X`（裸文本）

不变式（每条都断言，不过就不写）
  ① 新 Text 里不再含 `==` 标记
  ② unwrap(旧) == unwrap(新) ⇒ 只动包裹、没动内容

用法
    python tr_unwrap_cloze_eq.py                 # dry-run，只报数 + 打样例
    python tr_unwrap_cloze_eq.py --apply         # 真正写回（保留 FSRS 调度）
    python tr_unwrap_cloze_eq.py --apply --snapshot   # 写回前先存快照到同目录

⚠️ `POST /cards/:id/update`（源码 `Wge`）只改 note 的 `fields.Text/Extra`，
   走 `updateNoteFields` + Edit card 命令，**不碰 cards 表的 due/stability/reps 等调度字段**。
"""
import json, os, re, sys, time, importlib.util, urllib.request, urllib.error

sys.stdout.reconfigure(encoding="utf-8")

SKILL = r"~/.workbuddy/skills/highlight-to-true-recall"
TOKEN = open(os.path.join(SKILL, ".local-api-token"), encoding="utf-8").read().strip()
BASE = "http://127.0.0.1:27182"

spec = importlib.util.spec_from_file_location("hl2tr", os.path.join(SKILL, "scripts", "hl2tr.py"))
H = importlib.util.module_from_spec(spec)
spec.loader.exec_module(H)

WJ = H.WJ
MARK = H.CLOZE_MARK
CLOZE_RE = re.compile(r"\{\{c(\d+)::(.*?)(?:::(.*?))?\}\}", re.S)   # 与 hl2tr 同一套正则

APPLY = "--apply" in sys.argv
SNAP = "--snapshot" in sys.argv
HERE = os.getenv("TR_SNAP_DIR") or os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "tmp")   # 默认存 <skill>/tmp/


def call(method, path, payload=None, timeout=20):
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(BASE + path, data=data,
                                 headers={"Content-Type": "application/json",
                                          "Authorization": "Bearer " + TOKEN},
                                 method=method)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def rows_of(sql):
    d = call("POST", "/query", {"sql": sql})
    return (d.get("data") or d).get("rows", [])


def unwrap(s):
    """剥掉所有 WJ 与一层首尾 `==`，回到完全裸的内容（只用于比对，不落库）。

    ⚠️ **顺序**：必须先去 WJ 再剥 `==` —— 外层形态是 `WJ==…==WJ`，
    不先去 WJ 就认不出首尾的 `==`，会残留字面 `==`。
    """
    s = (s or "").replace(WJ, "")
    if s.startswith(MARK) and s.endswith(MARK) and len(s) > 2 * len(MARK):
        s = s[2:-2]
    return s.strip()


def strip_mark(s):
    """剥掉一层 `==…==`（含其内侧的 WJ），不带 `==` 的原样返回。"""
    s = s or ""
    if s.startswith(MARK) and s.endswith(MARK) and len(s) > 2 * len(MARK):
        return s[2:-2].strip(WJ)
    return s


def parts(s):
    """取出 Text 里每个 cloze 的 **(裸 body, 裸 hint)**：只用于「只动包裹、没动内容」比对。"""
    return [(unwrap(m.group(2)), unwrap(m.group(3) or ""))
            for m in CLOZE_RE.finditer(s or "")]


def clean_text(text):
    """卡面 Text → 剥掉脚本包的两层 `==`（内容侧 + hint 侧）。"""
    def rep(m):
        idx, body, hint = m.group(1), m.group(2), m.group(3)
        b = strip_mark(body.strip(WJ))       # 先剥外层 WJ，再剥 == 与内层 WJ
        nb = (WJ + b + WJ) if b else b
        if hint is None:
            return "{{c%s::%s}}" % (idx, nb)
        return "{{c%s::%s::%s}}" % (idx, nb, strip_mark(hint.strip(WJ)))
    return CLOZE_RE.sub(rep, text or "")


SQL = ("select n.id as nid, n.fields_json as fj, n.source_text as st, c.id as cid "
       "from notes n join cards c on c.note_id = n.id "
       "where n.deleted_at is null and c.deleted_at is null "
       "and n.note_type_id = 'builtin-cloze'")

rows = rows_of(SQL)
print("待检 cloze 卡数 =", len(rows))

plans, same, nost, broken = [], 0, 0, []
for r in rows:
    try:
        fields = json.loads(r["fj"])
    except Exception:
        continue
    old = fields.get("Text") or ""
    new = clean_text(old)
    if new == old:
        same += 1
        if MARK in old:                       # 含 == 却没被剥掉 ⇒ 形态没覆盖到
            broken.append((r["cid"], old))
        continue
    # 不变式 ①：不再含 ==
    if MARK in new:
        broken.append((r["cid"], new))
        continue
    # 不变式 ②：只动包裹，没动内容（逐个 cloze 比对裸 body / 裸 hint）
    if parts(old) != parts(new):
        broken.append((r["cid"], "unwrap 不一致\n旧=%r\n新=%r" % (old, new)))
        continue
    plans.append((r["cid"], r["nid"], old, new))

print("  无 `==`（本来就干净/非本脚本建的）= ", same)
print("  待写回                          = ", len(plans))
print("  异常（形态没覆盖到）             = ", len(broken))
for cid, info in broken[:5]:
    print("   [!]", cid, repr(info)[:260])

print()
for cid, nid, old, new in plans[:6]:
    print("card", cid)
    print("   旧:", repr(old[:130]))
    print("   新:", repr(new[:130]))
if len(plans) > 6:
    print("   ...（共 %d 条）" % len(plans))

if not APPLY:
    print("\n（dry-run，未写库。加 --apply 才真正写回）")
    sys.exit(0)
if broken:
    print("\n[×] 存在异常条目，先处理再写回")
    sys.exit(1)

if SNAP:
    p = os.path.join(HERE, "tr_cloze_eq_snapshot_%s.jsonl" % time.strftime("%Y%m%d-%H%M%S"))
    with open(p, "w", encoding="utf-8") as f:
        for cid, nid, old, new in plans:
            f.write(json.dumps({"card_id": cid, "note_id": nid, "old_Text": old,
                                "new_Text": new}, ensure_ascii=False) + "\n")
    print("\n快照已存:", p)

ok = bad = 0
for cid, nid, old, new in plans:
    try:
        call("POST", "/cards/%s/update" % cid, {"question": new})
        ok += 1
    except urllib.error.HTTPError as e:
        bad += 1
        print("  [×] %s -> %s %s" % (cid, e.code, e.read().decode("utf-8", "replace")[:160]))
    except Exception as e:
        bad += 1
        print("  [×] %s -> %s" % (cid, e))
print("\n写回完成: 成功 %d / 失败 %d" % (ok, bad))
