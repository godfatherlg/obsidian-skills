#!/usr/bin/env python
"""gaicuo 链接生成 + 自检（唯一入口，禁用脑内拼串）

用途：批改回复里所有 obsidian:// 行链接，一律用本脚本生成，顺便跑自检。
不用本脚本、直接手写串 = 违规（2026-10-05 漏字事故根因）。

用法：
  # 生成（可多组，重复 -f/-l/-a 即可）
  python gaicuo_link.py -f "冲刺班/科二/科目二冲刺带背5.md" -l 156 -a 标题

  # 自检（把已经写好的链接串贴回来验）
  python gaicuo_link.py --check "obsidian://adv-uri?vault=...&filepath=...&line=156&..."

  # 自检（老串 + 真路径成对验，适合发现了可疑链接）
  python gaicuo_link.py --verify "<可疑串>" -f "<真路径>"

输出：
  MARKDOWN= <可直接贴进聊天回复的 markdown 链接>
  URL=      <裸 URL>
  CHECK:    OK / 报警（含长度差、逐字 diff 的首个差异位）
"""
import argparse
import os
import sys
import urllib.parse

VAULT = "<vault-id>"
VAULT_ROOT = r"<vault>"
TEMPLATE = ("obsidian://adv-uri?vault={vault}&filepath={filepath}"
            "&line={line}&column=1&openmode=true&view-mode=source")
# 走查时跳过的目录（点开头的工作区/缓存目录，不可能是链接对象）
SKIP_DIRS = {".obsidian", ".git", ".workbuddy", ".trash", ".true-recall",
             "backups.nosync", "local.nosync", "modify_backup", "file-history"}


def resolve(rel):
    """把用户给的路径校准成「vault 根起完整相对路径」。

    返回 (rel, status)。status:
      "ok"       —— 已是完整相对路径且文件存在
      "fixed"    —— 漏了工作区前缀，已自动补全（唯一定位）
      "missing"  —— vault 里找不到，或后缀命中多篇无法确定
    2026-10-21 事故根因：调用方给的是「当前工作区起」的相对路径
    （冲刺班/科二/xxx.md），漏了 2026上数学教资/ 这一层 ⇒ 编码自检照样
    OK，但 FakeLink 找不到文件、链接静默不跳。故生成前必做存在性校验。
    """
    rel = rel.replace("\\", "/").strip()
    # 允许直接传绝对路径（<vault>\... 或 <vault>/...），自动剥掉 vault 根前缀
    root = VAULT_ROOT.replace("\\", "/")
    if rel.lower().startswith(root.lower() + "/"):
        rel = rel[len(root) + 1:]
    elif rel.lower() == root.lower():
        return rel, "missing"
    rel = rel.lstrip("/")
    if os.path.exists(os.path.join(VAULT_ROOT, *rel.split("/"))):
        return rel, "ok"
    tail = os.sep + rel.replace("/", os.sep)
    hits = []
    for root, dirs, files in os.walk(VAULT_ROOT):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for fn in files:
            full = os.path.join(root, fn)
            if full.endswith(tail):
                hits.append(os.path.relpath(full, VAULT_ROOT).replace("\\", "/"))
    if len(hits) == 1:
        return hits[0], "fixed"
    return rel, "missing" if not hits else "\n".join(["ambiguous"] + hits)


def build(rel, line, alias):
    """生成一条链接。rel = vault 根起完整相对路径（含全部嵌套前缀）。"""
    enc = urllib.parse.quote(rel, safe="")
    url = TEMPLATE.format(vault=VAULT, filepath=enc, line=line)
    text = alias if alias else str(line)
    return url, "[{}]({})".format(text, url)


def _raw_filepath(url):
    """取 filepath 的**原始未解码**串（parse_qs 会预先解码，必须手工截取）。"""
    q = urllib.parse.urlparse(url).query
    for kv in q.split("&"):
        if kv.startswith("filepath="):
            return kv[len("filepath="):]
    return ""


def check(url):
    """自检已写好的串：解回 filepath，与规范编码逐字比。"""
    raw = _raw_filepath(url)
    if not raw:
        return False, "串里没有 filepath 参数"
    dec = urllib.parse.unquote(raw)
    re_enc = urllib.parse.quote(dec, safe="")
    if re_enc != raw:
        i = next((k for k in range(min(len(raw), len(re_enc)))
                  if raw[k] != re_enc[k]), min(len(raw), len(re_enc)))
        return False, ("编码不规范：第 {} 位起不同（原串 …{}… / 规范 …{}…）；"
                       "原串可能被手工改过或漏字".format(
                           i, raw[max(0, i - 12):i + 12],
                           re_enc[max(0, i - 12):i + 12]))
    if "&offset=" in url:
        return False, "带 offset= 会忽略 line（本机 FakeLink 规则），必须删掉"
    return True, "OK（{} 字符）".format(len(raw))


def verify(url, rel):
    """老串 + 真路径成对验：比长度、比逐字。"""
    raw = _raw_filepath(url)
    good = urllib.parse.quote(rel, safe="")
    if raw == good:
        return True, "OK（逐字一致，{} 字符）".format(len(good))
    msgs = ["编码长度 {} vs 正确 {}".format(len(raw), len(good))]
    dec = urllib.parse.unquote(raw)
    if dec != rel:
        i = next((k for k in range(min(len(dec), len(rel)))
                  if dec[k] != rel[k]), min(len(dec), len(rel)))
        msgs.append("解码后第 {} 位起不同：得到 «{}» / 应为 «{}»".format(
            i, dec[max(0, i - 10):i + 10], rel[max(0, i - 10):i + 10]))
    return False, "；".join(msgs)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-f", "--file", action="append", default=[],
                    help="vault 根起完整相对路径（可重复）")
    ap.add_argument("-l", "--line", action="append", default=[],
                    help="行号（可重复，与 -f 一一对应）")
    ap.add_argument("-a", "--alias", action="append", default=[],
                    help="显示文字（可重复；缺省用行号；标题链接写 标题；整篇写 文章）")
    ap.add_argument("--check", metavar="URL", help="自检一条已写好的链接串")
    ap.add_argument("--verify", metavar="URL", help="与 -f 的真路径成对校验")
    args = ap.parse_args()

    if args.check:
        ok, msg = check(args.check)
        print("CHECK:", msg)
        return 0 if ok else 1

    if args.verify:
        if not args.file:
            print("--verify 需要同时给 -f <真路径>")
            return 2
        ok, msg = verify(args.verify, args.file[0])
        print("VERIFY:", msg)
        return 0 if ok else 1

    if not args.file:
        ap.print_help()
        return 2
    if len(args.line) != len(args.file):
        print("ERROR: -f 与 -l 数量必须一致")
        return 2

    rc = 0
    for idx, rel_in in enumerate(args.file):
        line = args.line[idx]
        alias = args.alias[idx] if idx < len(args.alias) else ""
        rel, status = resolve(rel_in)
        note = ""
        if status == "fixed":
            note = "   <-- 漏了工作区前缀，已自动补全"
        elif status.startswith("ambiguous"):
            cands = status.split("\n")[1:]
            print("ERROR: 后缀命中多篇，无法确定，请给完整相对路径：")
            for c in cands:
                print("  " + c)
            return 2
        elif status == "missing":
            print("ERROR: vault 里找不到 {}（filepath 必须是 vault 根起完整相对路径）"
                  .format(rel_in))
            rc = 1
            continue
        url, md = build(rel, line, alias)
        ok, msg = check(url)
        if not ok:
            rc = 1
        print("FILE=  {}{}{}".format(rel, note, "" if ok else "   <-- 生成即异常：" + msg))
        print("MARKDOWN= {}".format(md))
        print("URL=      {}".format(url))
        if idx != len(args.file) - 1:
            print()
    return rc


if __name__ == "__main__":
    sys.exit(main())
