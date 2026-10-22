# -*- coding: utf-8 -*-
"""gaicuo_tr_find.py — 按复制的题目文本, 在 True Recall 库里定位那道题的卡, 取答案面当参考答案。

配套 skill: gaicuo(手写简答批改)。改错场景里, 用户给的"题目位置线索"有两种:
  a. obsidian:// 链接 → 题目在 vault 笔记里(走 skill 第 2 节读 md);
  b. 一段复制的纯文本(没有链接、不是图片路径) → 这段文本是 True Recall 里某张卡的
     题目(正面 basic=Front / cloze=Text), 答案在卡背面 basic=Back / cloze=Extra。

本脚本走插件 Local API 的 /query(本机 apiEnableSqlQuery=true, 端口 27182) 拉全部活卡,
在 fields_json 的 Front / Text 里按文本匹配, 打印命中卡的题目+答案+出处, 供批改当参考答案。

用法:
  python gaicuo_tr_find.py "<复制的题目文本>"
  python gaicuo_tr_find.py "<复制的题目文本>" --dump <输出文件>
      # 另把最强命中卡的答案面写到文件(供 gaicuo_ocr.py 的 --ref 当词表)
  python gaicuo_tr_find.py "<复制的题目文本>" --answer-only [--dump <输出文件>]
      # 只把最强命中卡的答案面打印到 stdout(供管道喂 OCR);
      # 同时给了 --dump 就一并落盘(--answer-only 自己从不写文件, 别指望它落盘)

匹配: 归一化(去空白 + 去 𒋙⭐⏳==** 等标记)后, 先精确相等、再子串包含; 命中多张全部打印。
"""
import json
import os
import sys
import urllib.request

API_PORT = 27182
TOKEN_FILE = r"~\.workbuddy\skills\highlight-to-true-recall\.local-api-token"

# 本机有系统代理, 必须显式绕开, 否则 127.0.0.1 被拦成 502
_NO_PROXY = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def _token():
    for a in sys.argv[1:]:
        if a.startswith("--token="):
            return a.split("=", 1)[1].strip()
    v = (os.environ.get("TRUE_RECALL_TOKEN") or "").strip()
    if v:
        return v
    try:
        v = open(TOKEN_FILE, encoding="utf-8").read().strip()
        if v:
            return v
    except Exception:
        pass
    return ""


def _api(path, payload=None):
    url = "http://127.0.0.1:%d%s" % (API_PORT, path)
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(url, data=body, method="POST" if body else "GET")
    if body:
        req.add_header("Content-Type", "application/json")
    tok = _token()
    if tok:
        req.add_header("x-true-recall-token", tok)
    with _NO_PROXY.open(req, timeout=25) as r:
        res = json.loads(r.read().decode("utf-8"))
    if not res.get("ok"):
        raise RuntimeError(res.get("error") or "unknown")
    return res.get("data")


def _norm(s):
    s = s or ""
    for ch in ["\u2611", "\u2b50", "\u23f3", "==", "**", "__", "\\boxed", " ", "\t", "\n", "\r"]:
        s = s.replace(ch, "")
    return s


def _fields(note_type, fj):
    if note_type == "builtin-cloze":
        return fj.get("Text", ""), fj.get("Extra", "")
    return fj.get("Front", ""), fj.get("Back", "")


def _match_score(user_norm, q_norm):
    if not user_norm or not q_norm:
        return -1
    if user_norm == q_norm:
        return 2  # 精确相等, 最强
    if user_norm in q_norm or q_norm in user_norm:
        return 1  # 子串包含
    return -1


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    text = sys.argv[1]
    user_norm = _norm(text)

    sql = ("select n.note_type_id as ntype, n.fields_json as fj, "
           "n.source_uid as suid, n.source_text as stext "
           "from notes n join cards c on c.note_id = n.id "
           "where n.deleted_at is null and c.deleted_at is null")
    try:
        d = _api("/query", {"sql": sql})
        rows = d.get("rows", [])
    except Exception as e:
        print("ERR: 查 True Recall 卡失败: %s" % e)
        print("  (Obsidian 在跑吗? Local API 开了吗? 端口 %d)" % API_PORT)
        sys.exit(1)

    hits = []
    for r in rows:
        try:
            fj = json.loads(r["fj"])
        except Exception:
            continue
        q, a = _fields(r["ntype"], fj)
        sc = _match_score(user_norm, _norm(q))
        if sc < 0:
            continue
        hits.append({
            "score": sc,
            "type": "cloze" if r["ntype"] == "builtin-cloze" else "basic",
            "q": q,
            "a": a,
            "suid": r.get("suid") or "",
            "stext": r.get("stext") or "",
        })

    if not hits:
        print("未命中: 库里没有题目文本匹配这道题的卡。")
        print("  请确认文本是照卡面(正面)原样复制的; 或改贴 obsidian:// 链接定位。")
        sys.exit(1)

    hits.sort(key=lambda h: -h["score"])

    # --dump 先处理: 与 --answer-only 可同时用(一个落盘 + 一个只打印, 不冲突)
    out = ""
    if "--dump" in sys.argv:
        out = sys.argv[sys.argv.index("--dump") + 1]
        with open(out, "w", encoding="utf-8") as f:
            f.write(hits[0]["a"])

    if "--answer-only" in sys.argv:
        print(hits[0]["a"])
        if out:
            print("已把最强命中卡的答案面写到: %s" % out, file=sys.stderr)
        return

    if out:
        print("已把最强命中卡的答案面写到: %s" % out)

    print("命中 %d 张, 按匹配强度降序:\n" % len(hits))
    for i, h in enumerate(hits, 1):
        print("=" * 50)
        print("[%d] 卡型=%s 强度=%s" % (i, h["type"], "精确" if h["score"] == 2 else "子串"))
        print("题目(Front/Text): %s" % h["q"])
        print("答案(Back/Extra): %s" % h["a"])
        print("source_uid=%s" % h["suid"])
        print("source_text=%s" % h["stext"])


if __name__ == "__main__":
    main()
