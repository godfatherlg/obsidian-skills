# -*- coding: utf-8 -*-
"""
sync_note_lines.py —— 源笔记被编辑导致行号漂移后，重新同步下游产物里指向它的行号链接。

支持三类产物（按扩展名自动判断，也可 --mode 强制）：
  html   : <a class="jump" href="obsidianjump://jump?p=<enc>&line=N">P N</a>
           以及 href="obsidian://adv-uri?...&filepath=<enc>&line=N..."
  md     : 1. 文本内容 [标题](obsidian://adv-uri?...&filepath=<enc>&line=N...)
  pydata : 数据脚本里的条目元组  (N, "文本内容"),  路径取自同级的 append(("相对/路径.md", ...))

匹配算法（关键）：
  1. 产物里的条目文本是"整理/改写过的摘要"，与 md 原文行并不逐字相同，不能直接字符串相等匹配。
  2. 因此用 字符 bigram 召回率 + 前 6 字锚点 给 (条目, 新文件每一行) 打分；
  3. 再用 单调对齐 DP（允许跳过行 / 跳过条目）求全局最优分配——条目按原文顺序整理，
     新行号必然递增，这个约束能把大量"局部相似"的误配纠正过来。
  4. 匹配完成后补算 最长公共子串比例，给出 HIGH / MID / LOW 三档置信度；LOW 不自动改，列出来人工核对。

用法：
  python sync_note_lines.py <产物1> [产物2 ...] [选项]

选项：
  --vault-root DIR    Obsidian 仓库根目录（默认 <vault>）
  --base PREFIX       pydata 模式下路径前缀，如 "2026上数学教资/2026科三数学/粉笔课程"；
                      不传则自动读取数据脚本里的 BASE = "..." 常量
  --mode MODE         auto（默认，按扩展名）| html | md | pydata
  --apply             真正写回（默认 dry-run，只报告不落盘）
  --min-score F       接受自动匹配的最低分（默认 0.30）；低于此值列为 UNMATCHED
  --only SUBSTR       只处理路径包含该子串的源笔记（可重复传）
  --override S        人工指定映射，格式 "路径关键字|旧行=新行,旧行=新行"（可重复传）
  --quiet             只打印汇总，不列明细
  --no-backup         --apply 时不生成 .bak（默认生成）
  --check             体检模式：不改任何东西，只报告每条链接当前指向的行"像不像"该条目

退出码：0=全部处理成功；2=存在 UNMATCHED 或 ERROR（需人工介入）
"""
from __future__ import annotations

import argparse
import os
import re
import shutil
import sys
from urllib.parse import unquote

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

VAULT_DEFAULT = r"<vault>"

# 归一化时剔除的字符：加粗标记、代码符、公式符、各类标点、空白
PUNCT_RE = re.compile(
    r"[，。；：、,.;:！!？?（）()【】\[\]「」『』“”‘’\"'`~—\-_《》〈〉…·　\s]+"
)
TAG_RE = re.compile(r"<[^>]+>")
MD_STAR_RE = re.compile(r"\*\*|`|\$")


# ---------------------------------------------------------------- 工具函数
def norm(s: str) -> str:
    """归一化：去 HTML 标签、去 ** 加粗、去所有标点与空白，只留纯字符序列。"""
    s = TAG_RE.sub("", s)
    s = MD_STAR_RE.sub("", s)
    s = PUNCT_RE.sub("", s)
    return s


def bigrams(s: str) -> set:
    if len(s) < 2:
        return {s} if s else set()
    return {s[i:i + 2] for i in range(len(s) - 1)}


def lcs_len(a: str, b: str) -> int:
    """最长公共子串长度（a 截断到 80 字、b 截断到 240 字以控耗时）。"""
    a, b = a[:80], b[:240]
    if not a or not b:
        return 0
    prev = [0] * (len(b) + 1)
    best = 0
    for i in range(1, len(a) + 1):
        cur = [0] * (len(b) + 1)
        ai = a[i - 1]
        for j in range(1, len(b) + 1):
            if ai == b[j - 1]:
                cur[j] = prev[j - 1] + 1
                if cur[j] > best:
                    best = cur[j]
        prev = cur
    return best


# 首句切分标点：注意不含 "." 和 ","，因为中文笔记里它们常作序号点与千分位，
# 保留了才能把 "1. 课程结构三类型:**必修课程...**" 的首句切成 "课程结构三类型"。
SEG_SPLIT_RE = re.compile(r"[，。；：、！？（）()【】\[\]「」『』“”‘’\"'…—｜|]")
LEAD_NUM_RE = re.compile(r"^\s*\d+\s*[.、)]\s*")


def first_seg(raw: str) -> str:
    """取"到第一个标点为止"的首句（归一化后）。六素养条目的锚点命门。"""
    s = MD_STAR_RE.sub("", raw)
    s = TAG_RE.sub("", s)
    s = LEAD_NUM_RE.sub("", s)
    parts = SEG_SPLIT_RE.split(s)
    return norm(parts[0]) if parts else ""


def prep(raw: str):
    """预处理文本 -> (归一化串, bigram 集合, 首句)。HTML 实体必须先反转义。"""
    try:
        import html as _h
        raw = _h.unescape(raw)
    except Exception:
        pass
    n = norm(raw)
    return (n, bigrams(n), first_seg(raw))


def _seg_anchor(iseg: str, lseg: str) -> float:
    """首句互含：条目首句与行首句一方包含另一方 -> 强信号（定位到小标题行的关键）。"""
    if not iseg or not lseg:
        return 0.0
    if iseg in lseg or lseg in iseg:
        return 1.0
    if len(iseg) >= 4 and len(lseg) >= 4 and (iseg[:4] in lseg or lseg[:4] in iseg):
        return 0.6
    return 0.0


def cheap_score(item, lp) -> float:
    """
    粗打分（全矩阵用）。item / lp 均为 prep() 的三元组。
    cov 用 min 归一化而非召回：产物条目是"小标题 + 子内容"的合并摘要，
    若用召回（除以条目 bigram 数），内容更长的"表现/内容"子行会压过小标题行，
    导致落点漂到子行；除以 min 让短小标题行也能拿到高覆盖分（2026-09-01 实测踩坑）。
    """
    in_, ib, iseg = item
    ln, lb, lseg = lp
    if not in_ or not ln or not ib or not lb:
        return 0.0
    mn = min(len(ib), len(lb))
    cov = len(ib & lb) / mn if mn else 0.0
    cov *= min(1.0, len(lb) / 5.0)   # 极短行惩罚，避免误配到 2~3 字的碎片行
    pf = 1.0 if len(in_) >= 6 and in_[:6] in ln else 0.0
    return 0.55 * cov + 0.30 * _seg_anchor(iseg, lseg) + 0.15 * pf


def fine_score(item, lp) -> float:
    """细打分（仅对最终配对算）：四路加权，用于置信度分级。"""
    in_, ib, iseg = item
    ln, lb, lseg = lp
    if not in_ or not ln:
        return 0.0
    mn = min(len(ib), len(lb)) if ib and lb else 0
    cov = len(ib & lb) / mn if mn else 0.0
    cov *= min(1.0, len(lb) / 5.0) if lb else 0.0
    lcsr = lcs_len(in_, ln) / max(1, len(in_))
    pf = 1.0 if len(in_) >= 6 and in_[:6] in ln else 0.0
    return 0.35 * cov + 0.20 * lcsr + 0.30 * _seg_anchor(iseg, lseg) + 0.15 * pf


def grade(score: float) -> str:
    if score >= 0.60:
        return "HIGH"
    if score >= 0.40:
        return "MID"
    return "LOW"


def strip_tags(s: str) -> str:
    return TAG_RE.sub("", s).replace("**", "").strip()


# ---------------------------------------------------------------- 链接解析
LINE_RE = re.compile(r"[?&]line=(\d+)")
PATH_RE = re.compile(r"(?:filepath|\bp)=([^&\"'\s]+)")


def parse_uri(uri: str):
    """从 obsidian:// / obsidianjump:// URI 里解出 (vault 内相对路径, 行号)。"""
    m = LINE_RE.search(uri)
    if not m:
        return None, None
    line = int(m.group(1))
    p = PATH_RE.search(uri)
    if not p:
        return None, line
    return unquote(p.group(1)), line


URI_RE = re.compile(r"(?:obsidian://adv-uri|obsidianjump://jump)[^\s\"'<>)\]]*")
A_TAG_RE = re.compile(r"<a\b[^>]*href=\"([^\"]*(?:obsidian://|obsidianjump://)[^\"]*)\"[^>]*>.*?</a>",
                     re.S | re.I)
LI_RE = re.compile(r"<li\b[^>]*>(.*?)</li>", re.S | re.I)
MD_LINK_RE = re.compile(
    r"^[ \t]*(?:\d+[.、]\s*)?(.*?)\s*\[([^\]]*)\]\((obsidian://[^)]*|obsidianjump://[^)]*)\)[ \t]*$",
    re.M,
)
PY_ITEM_RE = re.compile(r"^\s*\(\s*(\d+)\s*,\s*[\"'](.*?)[\"']\s*\),?\s*$")
PY_PATH_RE = re.compile(r"append\(\(\s*[\"']([^\"']+\.md)[\"']")
PY_BASE_RE = re.compile(r"^\s*BASE\s*=\s*[\"']([^\"']*)[\"']", re.M)
PY_NUM_RE = re.compile(r"^\s*\(\s*(\d+)\s*,")


def parse_html(text: str):
    """
    返回 [(path, line, item_text, (span_start, span_end))]，span 为整个 <a>...</a>。
    条目正文取自 <li> 块内"去掉 <a> 按钮后"的剩余文本——直接取 <a> 的 innerText
    只会得到 "P8" 这种按钮文字，毫无匹配价值（2026-09-01 实测踩坑）。
    """
    out = []
    covered = set()
    # 1) 优先按 <li> 块解析（正文 + 按钮同属一个 li）
    for lm in LI_RE.finditer(text):
        li = lm.group(1)
        for am in A_TAG_RE.finditer(li):
            path, line = parse_uri(am.group(1))
            if path is None or line is None:
                continue
            body = li[:am.start()] + li[am.end():]
            s, e = lm.start(1) + am.start(), lm.start(1) + am.end()
            covered.add((s, e))
            out.append((path, line, strip_tags(body), (s, e)))
    # 2) 兜底：<li> 之外的链接，取其 innerText（可能只是按钮文字，聊胜于无）
    for m in A_TAG_RE.finditer(text):
        if (m.start(), m.end()) in covered:
            continue
        path, line = parse_uri(m.group(1))
        if path is None or line is None:
            continue
        out.append((path, line, strip_tags(m.group(0)), (m.start(), m.end())))
    return out


def parse_md(text: str):
    out = []
    for m in MD_LINK_RE.finditer(text):
        body, _alias, uri = m.group(1), m.group(2), m.group(3)
        path, line = parse_uri(uri)
        if path is None or line is None:
            continue
        # span 只覆盖 URI 本体（括号内），回写时只动 line= 数值
        s = m.start(3)
        e = m.end(3)
        out.append((path, line, strip_tags(body), (s, e)))
    return out


def parse_pydata(text: str, base: str):
    """状态机解析数据脚本：跟踪 current path，收集 (line, text) 元组。"""
    out = []
    cur = None
    for raw in text.splitlines(keepends=True):
        m = PY_PATH_RE.search(raw)
        if m:
            cur = (m.group(1) if not base else f"{base}/{m.group(1)}")
            continue
        mi = PY_ITEM_RE.match(raw)
        if mi and cur:
            line = int(mi.group(1))
            item_text = mi.group(2)
            out.append((cur, line, item_text, None))  # span 用 None，回写时按行正则替换
    return out


# ---------------------------------------------------------------- 对齐求解
FRONT_BONUS = 0.01  # 靠前微奖励：条目横跨多行时，同分优先落在起始行
MARGIN = 0.15       # 单条判据：新行分必须比当前行高出这么多，才判定这一条漂移了
FILE_GAIN = 0.08    # 笔记级判据：整篇平均得分须提升这么多，才认为这个笔记真的被编辑过
AVG_BEST_MIN = 0.45  # 笔记级判据：新落点整体平均得分门槛，低于此说明匹配证据不足，宁可不改


def align(items, new_preps, min_score):
    """
    items: [(idx, old_line, item_prep)]（按产物出现顺序）
    new_preps: [prep(每行)]，行号 = 下标 + 1
    返回 {idx: (new_line, score)}
    """
    if not items or not new_preps:
        return {}

    n = len(new_preps)
    m = len(items)

    # 粗打分矩阵（含靠前微奖励）
    sc = []
    for _, _, it in items:
        row = [cheap_score(it, lp) - FRONT_BONUS * (j / max(1, n - 1))
               for j, lp in enumerate(new_preps)]
        sc.append(row)

    # 原行号是否单调不减？单调才启用顺序约束（条目按原文顺序整理时的强先验）
    olds = [o for _, o, _ in items]
    monotone = all(olds[i] <= olds[i + 1] for i in range(len(olds) - 1))

    if not monotone:
        # 无顺序约束：各自取最高分
        res = {}
        for i in range(m):
            j = max(range(n), key=lambda j: sc[i][j])
            res[items[i][0]] = (j + 1, sc[i][j])
        return res

    # 单调对齐 DP：dp[i][j] = 前 i+1 个条目在 前 j+1 行内的最优总分
    NEG = -1e18
    dp = [[0.0] * n for _ in range(m)]
    bk = [[0] * n for _ in range(m)]  # 0=配对, 1=跳过行, 2=跳过条目

    for i in range(m):
        for j in range(n):
            pair = sc[i][j] + (dp[i - 1][j - 1] if i > 0 and j > 0 else 0.0)
            skip_line = dp[i][j - 1] if j > 0 else NEG
            skip_item = dp[i - 1][j] if i > 0 else NEG
            best, who = pair, 0
            if skip_line > best:
                best, who = skip_line, 1
            if skip_item > best:
                best, who = skip_item, 2
            dp[i][j] = best
            bk[i][j] = who

    # 回溯
    res = {}
    i, j = m - 1, n - 1
    while i >= 0 and j >= 0:
        who = bk[i][j]
        if who == 0:
            res[items[i][0]] = (j + 1, sc[i][j])
            i -= 1
            j -= 1
        elif who == 1:
            j -= 1
        else:
            i -= 1
    return res


# ---------------------------------------------------------------- 主流程
def read_note(vault_root: str, rel_path: str):
    p = os.path.join(vault_root, rel_path.replace("/", os.sep))
    if not os.path.isfile(p):
        return None
    with open(p, encoding="utf-8", errors="replace") as f:
        return f.read().splitlines()


def detect_mode(path: str, forced: str) -> str:
    if forced != "auto":
        return forced
    ext = os.path.splitext(path)[1].lower()
    if ext in (".html", ".htm"):
        return "html"
    if ext == ".py":
        return "pydata"
    return "md"


def process(artifact: str, mode: str, vault_root: str, base: str, args):
    with open(artifact, encoding="utf-8", errors="replace") as f:
        raw = f.read()

    if mode == "pydata":
        auto_base = base
        if not auto_base:
            mb = PY_BASE_RE.search(raw)
            auto_base = mb.group(1) if mb else ""
        entries = parse_pydata(raw, auto_base)
    elif mode == "html":
        entries = parse_html(raw)
    else:
        entries = parse_md(raw)

    if not entries:
        print(f"[跳过] {artifact} —— 未解析到任何行号链接")
        return 0

    # 按源笔记分组；同一笔记去重读入一次
    by_path = {}
    for i, (p, ln, txt, span) in enumerate(entries):
        by_path.setdefault(p, []).append((i, ln, txt, span))

    if args.only:
        by_path = {k: v for k, v in by_path.items()
                   if any(o in k for o in args.only)}
        if not by_path:
            print(f"[跳过] {artifact} —— 没有匹配 --only 的源笔记")
            return 0

    overrides = {}
    for spec in args.override or []:
        if "|" not in spec:
            continue
        key, pairs = spec.split("|", 1)
        d = {}
        for kv in pairs.split(","):
            if "=" in kv:
                a, b = kv.split("=", 1)
                d[int(a.strip())] = int(b.strip())
        overrides[key] = d

    changes = []      # (idx, old, new, conf, grade, preview) —— 判定为漂移、建议修改
    problems = []     # (idx, old, kind, detail)
    considered = 0    # 参与比对的条目总数
    skipped = 0       # 因"笔记未被修改"而整篇跳过的条目数

    art_mtime = os.path.getmtime(artifact)
    MTIME_TOL = 2.0   # 秒级容差，避免同一秒内生成产物+保存笔记的边界情况

    def not_modified(p):
        """笔记 mtime 不晚于产物 -> 产物生成后笔记没动过，行号不可能漂移（硬证据）。"""
        if args.force:
            return False
        fp = os.path.join(vault_root, p.replace("/", os.sep))
        try:
            return os.path.getmtime(fp) <= art_mtime + MTIME_TOL
        except OSError:
            return False

    for path, group in by_path.items():
        lines = read_note(vault_root, path)
        if lines is None:
            problems += [(i, o, "ERROR", f"源笔记不存在: {path}") for i, o, _, _ in group]
            continue
        if not_modified(path):
            skipped += len(group)
            continue
        new_preps = [prep(t) for t in lines]

        ov = {}
        for key, d in overrides.items():
            if key in path:
                ov.update(d)

        considered += len(group)
        todo = []     # 需要算法匹配的
        for i, old, txt, _span in group:
            if old in ov:
                new = ov[old]
                lp = new_preps[new - 1] if 0 < new <= len(new_preps) else ("", set(), "")
                changes.append((i, old, new, fine_score(prep(txt), lp), "OVERRIDE",
                                lines[new - 1].strip()[:44] if 0 < new <= len(lines) else ""))
            else:
                todo.append((i, old, prep(txt)))

        if todo:
            res = align(todo, new_preps, args.min_score)
            cand = []          # 候选改动，需先过"笔记级判据"再决定是否采纳
            s_cur = s_best = 0.0
            for idx, old, itp in todo:
                if idx not in res:
                    problems.append((idx, old, "UNMATCHED", f"{path}"))
                    continue
                new, cs = res[idx]
                conf = fine_score(itp, new_preps[new - 1])
                # 当前行得分：产物条目是改写摘要，与原文行天然不是逐字相同，
                # 所以"新行分 > 旧行分"不能直接判定漂移，必须用相对判据：
                # 只有新行明显更好（差值 > MARGIN）或旧行已完全不像（< 0.25）才改。
                # 否则一份已经同步好的产物会被无谓改动（2026-09-01 实测误改 99 条）。
                cur_s = (fine_score(itp, new_preps[old - 1])
                         if 1 <= old <= len(new_preps) else 0.0)
                s_cur += cur_s
                s_best += conf
                if new == old:
                    if conf < args.min_score:
                        problems.append((idx, old, "WEAK",
                                         f"{path} conf={conf:.2f} 未找到更优行"))
                    continue
                if conf < args.min_score:
                    problems.append((idx, old, "UNMATCHED",
                                     f"{path} best={new} conf={conf:.2f}"))
                    continue
                if not (conf - cur_s > MARGIN or cur_s < 0.25):
                    continue      # 旧行并未明显更差 -> 保持不变
                cand.append((idx, old, new, conf, grade(conf),
                             lines[new - 1].strip()[:44]))

            # 笔记级判据：编辑一个笔记会让它的所有条目集体偏移，而不是零星几条。
            # 若整篇平均得分没有明显提升，就认为该笔记未被编辑过，一条都不动。
            gain = (s_best - s_cur) / max(1, len(res))
            avg_best = s_best / max(1, len(res))
            fname = os.path.basename(path)
            # 误改比漏改危害大：只有"整体确实漂移"且"新落点整体够像"时才动。
            # avg_best 过低说明这个笔记的条目本就难以匹配（改写幅度大），证据不足，不动。
            if cand and gain < FILE_GAIN:
                print(f"  · {fname}：整体未漂移（增益 {gain:+.3f}，新落点均分 {avg_best:.2f}），"
                      f"忽略 {len(cand)} 条候选")
            elif cand and avg_best < AVG_BEST_MIN:
                print(f"  · {fname}：新落点整体不够像（均分 {avg_best:.2f} < {AVG_BEST_MIN}"
                      f"，增益 {gain:+.3f}），证据不足，忽略 {len(cand)} 条候选")
            else:
                changes += cand
                if cand:
                    print(f"  · {fname}：判定漂移（增益 {gain:+.3f}，新落点均分 {avg_best:.2f}），"
                          f"采纳 {len(cand)} 条")

    # ---------------- 报告 ----------------
    print("=" * 72)
    print(f"产物: {artifact}")
    print(f"模式: {mode}   解析链接: {len(entries)} 条   涉及源笔记: {len(by_path)} 个")
    print(f"比对 {considered} 条（{skipped} 条所属笔记未修改已跳过）"
          f"   判定漂移(建议改): {len(changes)} 条"
          f"   保持不变: {considered - len(changes) - len(problems)} 条"
          f"   待人工: {len(problems)} 条")

    if not args.quiet and changes:
        print("-" * 72)
        print(f"{'旧行':>5} {'新行':>5}  {'置信':<9} 新行内容预览")
        for _i, old, new, conf, g, prev in sorted(changes, key=lambda x: x[1]):
            print(f"{old:>5} {new:>5}  {g:<4}{conf:.2f}  {prev}")

    if problems:
        print("-" * 72)
        print("以下条目未能自动匹配，需人工核对（可用 --override 指定）：")
        for _i, old, kind, detail in sorted(problems)[:30]:
            txt = ""
            for i2, o2, t2, _s in entries:
                if i2 == _i:
                    txt = strip_tags(t2)[:40]
                    break
            print(f"  [{kind}] 旧行 {old}  「{txt}」  {detail}")
        if len(problems) > 30:
            print(f"  ... 其余 {len(problems) - 30} 条省略")

    # ---------------- 写回 ----------------
    if not args.apply:
        print("(dry-run：未写回。确认无误后加 --apply)")
        return 2 if problems else 0

    if not changes:
        print("无需写回（没有判定为漂移的条目）")
        return 2 if problems else 0

    if mode == "pydata":
        new_text = rewrite_pydata(raw, entries, changes)
    elif mode == "html":
        new_text = rewrite_html(raw, entries, changes)
    else:
        new_text = rewrite_md(raw, entries, changes)

    if not args.no_backup:
        shutil.copy2(artifact, artifact + ".bak")
    with open(artifact, "w", encoding="utf-8", newline="") as f:
        f.write(new_text)
    print(f"已写回: {artifact}（备份 {os.path.basename(artifact)}.bak）")
    return 2 if problems else 0


def rewrite_html(raw, entries, moved):
    """按 <a>...</a> 的 span 从后往前替换块内 line=/Pn/第 n 行。"""
    # entries 元素是 (path, line, txt, span) 四元组，index 是位置；changes 里的 i 即此位置。
    span_of = {i: s for i, (_p, _ln, _t, s) in enumerate(entries) if s}
    edits = []
    for i, old, new, _c, _g, _p in moved:
        s, e = span_of[i]
        blk = raw[s:e]
        nb = blk
        nb = nb.replace(f"line={old}", f"line={new}")
        nb = nb.replace(f">P{old}<", f">P{new}<")
        nb = nb.replace(f"第 {old} 行", f"第 {new} 行")
        if nb != blk:
            edits.append((s, e, nb))
    for s, e, nb in sorted(edits, reverse=True):
        raw = raw[:s] + nb + raw[e:]
    return raw


def rewrite_md(raw, entries, moved):
    span_of = {i: s for i, (_p, _ln, _t, s) in enumerate(entries) if s}
    edits = []
    for i, old, new, _c, _g, _p in moved:
        s, e = span_of[i]
        blk = raw[s:e]
        nb = re.sub(rf"(line=){old}\b", rf"\g<1>{new}", blk)
        if nb != blk:
            edits.append((s, e, nb))
    for s, e, nb in sorted(edits, reverse=True):
        raw = raw[:s] + nb + raw[e:]
    return raw


def rewrite_pydata(raw, entries, moved):
    """数据脚本：把第 old 行号改成 new。按 (old, 文本) 定位，逐行精确替换。"""
    lines = raw.splitlines(keepends=True)
    # 建立 (old, norm_text) -> new 的映射
    want = {}
    for i, old, new, _c, _g, _p in moved:
        txt = ""
        for i2, o2, t2, _s in entries:
            if i2 == i:
                txt = norm(strip_tags(t2))
                break
        want.setdefault((old, txt), new)

    done = 0
    for k, raw_line in enumerate(lines):
        m = PY_NUM_RE.match(raw_line)
        if not m:
            continue
        old = int(m.group(1))
        body = raw_line[m.end(1):]
        ntxt = norm(body)
        for (o, t), new in want.items():
            if o == old and t and t in ntxt:
                lines[k] = raw_line[:m.start(1)] + str(new) + raw_line[m.end(1):]
                done += 1
                break
    print(f"  数据脚本替换 {done} 处 / 目标 {len(moved)} 处")
    return "".join(lines)


def check(artifact, mode, vault_root, base, args):
    """
    体检：判断每条链接当前指向的行"像不像"该条目。
    判定用**相对**标准（不能用绝对阈值）：只有当源笔记里存在另一行明显更匹配时才算错位。
    原因：产物里的条目是改写过的摘要（还夹 LaTeX），与原文行天然不是逐字相同，
    绝对阈值会把大量正确链接误报成失效（2026-09-01 实测 0.25 阈值误报 143 条）。
    """
    with open(artifact, encoding="utf-8", errors="replace") as f:
        raw = f.read()
    if mode == "pydata":
        mb = PY_BASE_RE.search(raw)
        entries = parse_pydata(raw, base or (mb.group(1) if mb else ""))
    elif mode == "html":
        entries = parse_html(raw)
    else:
        entries = parse_md(raw)

    by_path = {}
    for i, (p, ln, txt, span) in enumerate(entries):
        by_path.setdefault(p, []).append((i, ln, txt))

    if args.only:
        by_path = {k: v for k, v in by_path.items() if any(o in k for o in args.only)}
        if not by_path:
            print(f"[跳过] {artifact} —— 没有匹配 --only 的源笔记")
            return 0

    art_mtime = os.path.getmtime(artifact)

    def not_modified(p):
        if args.force:
            return False
        fp = os.path.join(vault_root, p.replace("/", os.sep))
        try:
            return os.path.getmtime(fp) <= art_mtime + 2.0
        except OSError:
            return False

    bad = 0
    total = 0
    skipped = 0
    for path, group in by_path.items():
        if not_modified(path):
            skipped += len(group)
            continue
        lines = read_note(vault_root, path)
        if lines is None:
            bad += len(group)
            print(f"  [缺文件] {path}（{len(group)} 条）")
            continue
        new_preps = [prep(t) for t in lines]

        # 先逐条算 现得分 / 最佳得分 / 最佳行，收集候选
        cand = []          # (i, line, bj, cur_s, best_s, txt)
        s_cur = s_best = 0.0
        for _i, line, txt in group:
            total += 1
            if not (1 <= line <= len(lines)):
                bad += 1
                print(f"  [越界] {path}:{line}（文件共 {len(lines)} 行）"
                      f"「{strip_tags(txt)[:34]}」")
                continue
            itp = prep(txt)
            scores = [cheap_score(itp, lp) for lp in new_preps]
            bj = max(range(len(scores)), key=lambda j: scores[j])
            cur_s = fine_score(itp, new_preps[line - 1])
            best_s = fine_score(itp, new_preps[bj])
            s_cur += cur_s
            s_best += best_s
            cand.append((_i, line, bj, cur_s, best_s, txt))

        # 笔记级判据（与 process 同）：编辑一个笔记会让它的所有条目集体偏移，
        # 单条"别处更相似"往往是改写幅度大造成的误报。只有整篇平均增益够大、
        # 且新落点整体够像，才认为这个笔记真的漂移了，逐条报错才有意义。
        gain = (s_best - s_cur) / max(1, len(cand))
        avg_best = s_best / max(1, len(cand))
        fname = os.path.basename(path)
        if cand and (gain < FILE_GAIN or avg_best < AVG_BEST_MIN):
            print(f"  · {fname}：笔记级判据未触发（增益 {gain:+.3f}，新落点均分 {avg_best:.2f}），"
                  f"其下 {len(cand)} 条单条疑似均视为误报，跳过")
            continue

        for _i, line, bj, cur_s, best_s, txt in cand:
            if bj + 1 == line:
                continue
            if best_s - cur_s > MARGIN and best_s >= args.min_score:
                bad += 1
                print(f"  [疑似错位] {path}:{line} → 建议 {bj + 1}"
                      f"（现 {cur_s:.2f} / 佳 {best_s:.2f}）"
                      f"「{strip_tags(txt)[:30]}」")
                print(f"       现指向: {lines[line-1].strip()[:50]}")
                print(f"       建议行: {lines[bj].strip()[:50]}")

    print("=" * 72)
    print(f"体检 {os.path.basename(artifact)}：检查 {total} 条，疑似失效 {bad} 条"
          f"（另有 {skipped} 条所属笔记在产物之后未修改，已跳过；--force 可强制全查）")
    return 2 if bad else 0


def main():
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("artifacts", nargs="+")
    ap.add_argument("--vault-root", default=VAULT_DEFAULT)
    ap.add_argument("--base", default="")
    ap.add_argument("--mode", default="auto", choices=["auto", "html", "md", "pydata"])
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--min-score", type=float, default=0.30)
    ap.add_argument("--only", action="append", default=[])
    ap.add_argument("--override", action="append", default=[])
    ap.add_argument("--quiet", action="store_true")
    ap.add_argument("--no-backup", action="store_true")
    ap.add_argument("--force", action="store_true",
                    help="忽略 mtime 过滤，强制比对所有笔记（产物是复制来的、或 mtime 不可靠时用）")
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()

    rc = 0
    for a in args.artifacts:
        if not os.path.isfile(a):
            print(f"[错误] 文件不存在: {a}")
            rc = 2
            continue
        mode = detect_mode(a, args.mode)
        if args.check:
            rc |= check(a, mode, args.vault_root, args.base, args)
        else:
            rc |= process(a, mode, args.vault_root, args.base, args)
    sys.exit(1 if rc == 2 else 0)


if __name__ == "__main__":
    main()
