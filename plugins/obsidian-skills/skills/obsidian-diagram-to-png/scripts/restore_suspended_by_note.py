# -*- coding: utf-8 -*-
"""restore_suspended_by_note.py — True Recall「对比图扶手」的达标恢复脚本。

两套用法（都对应"一组卡 ⇄ 一张/多张对比图"的扶手路线，没有 cloze 卡）：

  · 一图对多卡（单篇笔记）：
      为一篇笔记做了一张对比图当扶手，记住了就恢复那篇笔记里所有 suspend 的卡。
      只需该图处理完即可恢复 —— 跑本脚本（单笔记）即恢复。

  · 多图对多卡（多篇笔记一批）：
      为多篇笔记各做了一张对比图，要等【所有图片都处理完】才一起恢复。
      脚本会检查每篇笔记里嵌的 ![[images/...png]] 是否都已落在磁盘上；
      任一张图还没生成 → 只打印"等待中"并退出（不恢复）。
      全部到位 → 一次性恢复这批笔记里所有 suspend 的卡。

底层都是 POST /cards/:id/suspend {suspended:false}。

用法
----
  python restore_suspended_by_note.py <md路径> [--apply]            # 一图：恢复该笔记的卡
  python restore_suspended_by_note.py <md1> <md2> ... [--apply]     # 多图：等全部图就绪后恢复
  python restore_suspended_by_note.py --uid=<uid> [--uid=<uid> ...] [--apply]   # 直接给 uid（不做图检查）

依赖：同族 skill 的 hl2tr（Local API + token）。Obsidian 必须在跑、Local API 已开。
"""
import os
import re
import sys

# ---------- 复用 highlight-to-true-recall 的骨架（token / Local API），与 bc2tr.py 同源 ----------
HL2TR_SCRIPTS = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "highlight-to-true-recall", "scripts")
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass
if not os.path.isdir(HL2TR_SCRIPTS):
    raise SystemExit("找不到同族 skill 的脚本目录：%s" % HL2TR_SCRIPTS)
sys.path.insert(0, HL2TR_SCRIPTS)
try:
    import hl2tr  # noqa: E402
except Exception as e:  # pragma: no cover
    raise SystemExit("导入 hl2tr.py 失败：%s" % e)

VAULT = hl2tr.VAULT
UID_FIELD = "flashcard_uid"
FM_RE = re.compile(r"\A---\r?\n(.*?)\r?\n---\r?\n?", re.S)
UID_RE = re.compile(r"^flashcard_uid:\s*[\"']?([a-f0-9]+)[\"']?\s*$", re.M)
IMG_RE = re.compile(r"!\[\[images/([^\]]+\.png)\]\]", re.I)


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


def images_of(path):
    """这篇笔记里嵌的对比图（磁盘绝对路径）。"""
    try:
        text = open(path, encoding="utf-8").read()
    except Exception:
        return []
    return [os.path.join(VAULT, "images", fn) for fn in IMG_RE.findall(text)]


def cards_of_uid(uid):
    d = hl2tr.api_call("/notes/cards?source_uid=%s&limit=200" % uid)
    return d.get("cards") or [], d.get("noteName") or "", d.get("notePath") or ""


def set_suspended(cid, flag):
    d = hl2tr.api_call("/cards/%s/suspend" % cid, {"suspended": bool(flag)})
    return bool(d.get("suspended")) if isinstance(d, dict) else None


def collect_notes(args):
    """返回 [(uid, md_path_or_None, label)]。"""
    notes = []
    for a in args:
        if a.startswith("--uid="):
            uid = a.split("=", 1)[1].strip()
            if uid:
                notes.append((uid, None, uid))
        elif not a.startswith("--"):
            full = a if os.path.isabs(a) else os.path.join(VAULT, a)
            if not os.path.exists(full):
                raise SystemExit("文件不存在：%s" % full)
            uid = read_uid(full)
            if not uid:
                raise SystemExit("%s 没有 frontmatter %s" % (a, UID_FIELD))
            notes.append((uid, full, a))
    return notes


def main():
    argv = sys.argv[1:]
    apply = "--apply" in argv
    notes = collect_notes(argv)
    if not notes:
        raise SystemExit(
            "用法：python restore_suspended_by_note.py <md路径|多个> [--apply]\n"
            "   或：python restore_suspended_by_note.py --uid=<flashcard_uid> [--apply]")

    multi = len(notes) > 1

    # 多图模式：所有嵌图必须都已生成，否则等待。一图模式不做图检查（图处理完即可）。
    if multi:
        pending = []
        for uid, path, label in notes:
            if not path:
                continue  # 只给 uid 的笔记无法查图，跳过图检查
            for img in images_of(path):
                if not os.path.exists(img):
                    pending.append((label, os.path.basename(img)))
        if pending:
            print("多图模式：等待所有图片处理完毕才恢复。当前缺失：")
            for label, fn in pending:
                print("  · %s → %s" % (label, fn))
            print("\n[等待] 未恢复任何卡。把上面这些图都生成后重跑本命令即可。")
            return

    try:
        hl2tr.api_call("/status", timeout=5)
    except RuntimeError as e:
        raise SystemExit(str(e))

    total_ok = total_fail = 0
    for uid, path, label in notes:
        cards, name, _p = cards_of_uid(uid)
        suspended = [c for c in cards if c.get("suspended")]
        tag = "一图" if not multi else "多图"
        print("\n[%s] 笔记：%s（uid %s）| 活卡 %d | 挂起 %d"
              % (tag, name or label, uid, len(cards), len(suspended)))
        for c in suspended:
            t = (c.get("sourceText") or c.get("question") or "")
            print("  ~ %s  %s  (%s)" % (c.get("id", "")[:8], t[:50], c.get("cardType")))
        if not apply:
            print("  [预览] 未改动。确认后加 --apply 取消挂起以上 %d 张卡。" % len(suspended))
            continue
        if not suspended:
            print("  没有挂起的卡，跳过。")
            continue
        ok = fail = 0
        for c in suspended:
            try:
                set_suspended(c.get("id"), False)
                ok += 1
                print("  ^ %s 已取消挂起" % c.get("id")[:8])
            except RuntimeError as e:
                fail += 1
                print("  ✗ %s 失败：%s" % (c.get("id")[:8], e))
        total_ok += ok
        total_fail += fail

    if not apply:
        return
    print("\n恢复汇总：成功 %d 张 / 失败 %d 张（跨 %d 篇笔记）" % (total_ok, total_fail, len(notes)))
    print("⚠️ 取消挂起的卡 due 早就在过去，会立刻进复习队列（当天就能验证是否真记住）。")


if __name__ == "__main__":
    main()
