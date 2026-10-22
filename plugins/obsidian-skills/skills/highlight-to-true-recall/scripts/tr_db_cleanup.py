#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""True Recall 库清理：软删除「孤儿 note」并可选 VACUUM 回收空间。

孤儿 note = notes 里 deleted_at 为空、但没有任何活跃 card 的记录。
它们来自：① 插件删卡/清空笔记时只软删 card、note 留下；② 反复重建卡片。

【为什么必须"插件已停"】
插件把 sqlite3 编译成 WASM 在内存里跑（:memory: 库 + sqlite3_deserialize），
写盘走 Obsidian 的 vault.adapter.writeBinary / rename，**没有文件句柄、没有锁**。
所以"库文件被占用"不是问题，真正的问题是：
  onunload() -> coreApp.shutdown() -> cardStore.saveNow() 会把**内存整库覆盖到磁盘**。
因此只要插件还活着（或刚被禁用、saveNow 尚未落盘），外部改动就可能被盖掉。

【怎么算"插件已停"】
不必退出整个 Obsidian（关 ob 与禁插件走的是同一条 shutdown 路径，安全性相同）。
判据 = **Local API 探不到**（插件运行时监听 127.0.0.1:<apiPort>，默认 27182；
它一被禁用，localApi.stop() 就关掉端口）。本脚本：
  1) 先探端口/接口 -> 探到就拒跑；
  2) 再等库文件 mtime+size 连续稳定 -> 说明 saveNow 已落盘；
  3) 写前自动备份；写后再复探一次，若插件又活了则强警告。

用法：
    python tr_db_cleanup.py                     # 只预演，打印将要删什么
    python tr_db_cleanup.py --apply             # 真正软删（先自动备份）
    python tr_db_cleanup.py --apply --vacuum    # 顺便 VACUUM 回收空间
    python tr_db_cleanup.py --db <path>         # 指定库文件（默认自动发现）
    python tr_db_cleanup.py --port 27183        # 指定插件 Local API 端口

安全设计：
  - 默认只预演；--apply 才写。
  - 写前自动备份到 C:\\Users\\<user>\\.workbuddy\\tmp\\。
  - 检测到插件 Local API 在线就拒绝执行（除非 --force）。
  - 库文件 mtime/size 不稳定（还在被写）也拒绝执行。
  - 只填 notes.deleted_at，绝不 DELETE 行 → 可随时用备份还原。
  - 删前做"误伤检查"：任何挂着活跃 card 的 note 都不许进清理集。
  - VACUUM 后自动 rebuild FTS（notes_fts 是 external-content 表，靠 rowid 挂接，
    虽实测 VACUUM 未改 rowid，重建一次是保险动作），并跑 integrity-check。
"""

import argparse
import glob
import json
import os
import shutil
import socket
import sqlite3
import subprocess
import sys
import time

TMP = r"~\.workbuddy\tmp"
PLUGIN_DIR = r"<vault>\.obsidian\plugins\true-recall"
DEFAULT_PORT = 27182

ORPHAN_SQL = (
    "select n.id from notes n where n.deleted_at is null and not exists "
    "(select 1 from cards c where c.note_id = n.id and c.deleted_at is null)"
)
ACTIVE_NOTE_SQL = "select distinct note_id from cards where deleted_at is null"


def find_db(explicit=None):
    if explicit:
        return explicit
    cands = []
    for pat in (r"<vault>\.true-recall\local.nosync\*.db",
                r"<vault>\.true-recall\*.db"):
        cands += [p for p in glob.glob(pat) if not p.lower().endswith(".bak")]
    if not cands:
        raise SystemExit("找不到 True Recall 库文件，请用 --db 指定")
    return max(cands, key=os.path.getmtime)


def configured_port():
    """从插件设置 data.json 读 apiPort（读不到就用默认值）。"""
    try:
        d = json.load(open(os.path.join(PLUGIN_DIR, "data.json"), encoding="utf-8"))
        p = int(d.get("apiPort") or 0)
        return p if 1024 <= p <= 65535 else DEFAULT_PORT
    except Exception:
        return DEFAULT_PORT


def port_open(port, host="127.0.0.1", timeout=1.5):
    """True = 有人在监听（= 插件 Local API 活着）。不受系统代理影响。"""
    s = socket.socket()
    s.settimeout(timeout)
    try:
        return s.connect_ex((host, port)) == 0
    except Exception:
        return False
    finally:
        s.close()


def obsidian_running():
    """仅作提示用：Obsidian 在跑但端口关着 = 插件已被禁用，属于可清理状态。"""
    try:
        out = subprocess.run(["tasklist", "/FO", "CSV", "/NH"],
                             capture_output=True, text=True,
                             encoding="gbk", errors="replace", timeout=30).stdout
    except Exception:
        return None
    return [l.strip() for l in out.splitlines() if "bsidian" in l.lower()]


def wait_settle(path, samples=4, gap=1.5):
    """等库文件 mtime+size 连续两次一致 → 说明插件最后一次 saveNow 已写完。"""
    prev = None
    for i in range(samples):
        try:
            st = os.stat(path)
            cur = (st.st_mtime_ns, st.st_size)
        except OSError:
            cur = None
        if prev is not None and cur == prev:
            return True, cur, i
        prev = cur
        if i < samples - 1:
            time.sleep(gap)
    return False, prev, samples


def counts(cur):
    q = lambda s: cur.execute(s).fetchone()[0]
    return {
        "cards_active": q("select count(*) from cards where deleted_at is null"),
        "notes_active": q("select count(*) from notes where deleted_at is null"),
        "orphans": q("select count(*) from notes n where n.deleted_at is null and not exists "
                     "(select 1 from cards c where c.note_id=n.id and c.deleted_at is null)"),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="真正写入（默认只预演）")
    ap.add_argument("--vacuum", action="store_true", help="清理后 VACUUM 回收空间")
    ap.add_argument("--force", action="store_true", help="插件在线也强行执行（危险）")
    ap.add_argument("--db", default=None)
    ap.add_argument("--port", type=int, default=None, help="插件 Local API 端口")
    a = ap.parse_args()

    port = a.port or configured_port()
    db = find_db(a.db)
    print("库文件 :", db)
    print("大小   :", os.path.getsize(db), "bytes")
    print("API端口:", port)

    # ---- 前置判据 1：插件是不是还活着 ----
    online = port_open(port)
    procs = obsidian_running()
    if procs is None:
        print("进程   : 无法判定（tasklist 不可用）")
    elif procs:
        print("进程   : Obsidian 在运行（%d 个进程）" % len(procs))
    else:
        print("进程   : 未检测到 Obsidian")
    print("插件   :", "**Local API 在线 —— 插件还活着**" if online else "Local API 离线 ✓")

    if online and not a.force:
        raise SystemExit(
            "拒绝执行：插件仍在运行（Local API %d 端口在监听）。\n"
            "  处理办法(二选一，不必退出整个 Obsidian)：\n"
            "    A) 设置 → 第三方插件 → 关掉 True Recall（等约 2 秒让它 saveNow 落盘）\n"
            "    B) 直接完全退出 Obsidian\n"
            "  然后重跑本脚本。确要强写加 --force。" % port)

    # ---- 前置判据 2：最后一次落盘是否已完成 ----
    print("等待落盘: 采样库文件 mtime/size ...")
    ok, fp, n = wait_settle(db)
    if not ok and not a.force:
        raise SystemExit("拒绝执行：库文件仍在被写入（mtime/size 不稳定）。"
                         "请确认插件已停，稍候重试；确要强写加 --force。")
    print("         : %s（第 %d 次采样起稳定）" % ("已稳定 ✓" if ok else "仍不稳定 ⚠", n + 1))

    con = sqlite3.connect(db)
    cur = con.cursor()
    before = counts(cur)
    print("清理前 : cards 活跃 %(cards_active)d | notes 活跃 %(notes_active)d | 孤儿 %(orphans)d" % before)

    targets = [r[0] for r in cur.execute(ORPHAN_SQL)]
    guard = {r[0] for r in cur.execute(ACTIVE_NOTE_SQL)}
    bad = guard & set(targets)
    print("待清理 : %d 条 note" % len(targets))
    print("误伤检查: %d（必须为 0）" % len(bad))
    if bad:
        con.close()
        raise SystemExit("有活跃卡挂在待清理 note 上，终止。")

    if not targets:
        print("没有孤儿 note，收工。")
        con.close()
        return
    if not a.apply:
        for nid in targets[:5]:
            row = cur.execute("select created_via, substr(fields_json,1,60) from notes where id=?",
                              (nid,)).fetchone()
            print("   样例 %s  %s  %s" % (nid[:8], row[0], row[1].replace("\n", " ")[:60]))
        if len(targets) > 5:
            print("   ... 其余 %d 条" % (len(targets) - 5))
        print("\n[预演] 未写入任何东西。确认后加 --apply。")
        con.close()
        return

    os.makedirs(TMP, exist_ok=True)
    bak = os.path.join(TMP, "true-recall-before-cleanup-%s.db" % time.strftime("%Y%m%d-%H%M%S"))
    shutil.copy2(db, bak)
    print("备份   :", bak)

    now = int(time.time() * 1000)
    try:
        cur.execute("begin")
        n = 0
        for nid in targets:
            cur.execute("update notes set deleted_at=?, updated_at=? where id=? and deleted_at is null",
                        (now, now, nid))
            n += cur.rowcount
        con.commit()
        print("已软删 : %d 条 note（rows 保留，可还原）" % n)
    except Exception as e:
        con.rollback()
        print("已回滚：", e)
        raise

    after = counts(cur)
    print("清理后 : cards 活跃 %(cards_active)d | notes 活跃 %(notes_active)d | 孤儿 %(orphans)d" % after)
    if after["cards_active"] != before["cards_active"]:
        print("! 活跃卡数发生变化，请检查！")
    con.close()

    if a.vacuum:
        bcon = sqlite3.connect("file:%s?mode=ro" % bak.replace("\\", "/"), uri=True)
        old_map = {r[0]: r[1] for r in bcon.execute("select rowid, id from notes")}
        bcon.close()

        con = sqlite3.connect(db)
        cur = con.cursor()
        cur.execute("vacuum")
        con.commit()
        new_map = {r[0]: r[1] for r in cur.execute("select rowid, id from notes")}
        print("VACUUM : rowid 映射%s变化" % ("有" if new_map != old_map else "无"))
        cur.execute("insert into notes_fts(notes_fts) values('rebuild')")
        con.commit()
        cur.execute("insert into notes_fts(notes_fts) values('integrity-check')")
        print("FTS    : rebuild + integrity-check 通过")
        print("文件   :", os.path.getsize(db), "bytes")
        con.close()
    else:
        print("（未 VACUUM；要回收空间加 --vacuum）")

    # ---- 收尾：确认外部没有又把库覆盖回去 ----
    if port_open(port):
        print("!! 警告：写完后 Local API 又在线了 —— 说明插件被重新启用，"
              "它内存里的旧库可能覆盖本次改动。请立刻禁用插件，或用备份 %s 核查。" % bak)
    else:
        print("收尾   : 插件仍处于停止状态 ✓（改动不会被覆盖）")


if __name__ == "__main__":
    main()
