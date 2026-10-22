#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
verify_video_links.py — 视频时间戳链接语义审计 (pdf-to-vault-summary 配套)

问题背景 (2026-09-02 发现于 主观专项-教学技能2.md):
  md 里每条知识点的 [[mp4#t=秒|视频]] 链接, 格式验证器只查"有没有链接、别名对不对",
  不查"链接指到的秒数到底是不是在讲这条文字". 结果生成时按关键词"首次命中"字幕,
  把后半段链接指到了课间闲聊/早期举例段, 文字与视频对不上, 直到人工点开才发现.

本脚本做的事:
  读 md, 提取每条带 mp4#t=N 的行, 反查同源 .srt 在 N 秒附近的字幕内容,
  自动标出三类可疑, 输出可肉眼复核的审计表.

可疑标记 (⚠):
  [IDLE]  窗口含课间/闲聊/广告等无效段标志词 (如 卷子, 歌曲, 休息, 下课, 插播...).
  [ORDER] 同一 ## 𒋙 节内, 连续两条知识点的时间戳出现倒挂 (后一条秒数 < 前一条),
          或同一秒数重复出现 -> 几乎必然映射错位.
  [KEYMISS] 该行的加粗关键词(或首词)在字幕窗口里完全不出现 -> 大概率指错段.

用法:
  python verify_video_links.py <MD_PATH> <SRT_PATH> [--window-before 15] [--window-after 45]

退出码: 0 = 无 ⚠; 1 = 有 ⚠ (应消掉后再 present).

注意: 本脚本是"辅助肉眼复核", 不是自动修复. 它给出每条链接对应的字幕窗口,
       agent/用户读完窗口即可判断对不对, 错位就按真实秒数改 vmap 重注入.
"""
import re
import sys
import os


# 注意 (2026-09-10 修正): 单一名词(课间/休息/广告/福利/试卷/私信)在教资题干里是正当高频词
# ("课间操""课间休息""侵犯休息权""儿童福利机构""播放广告""讲试卷""回私信"), 直接入表会大面积误伤;
# 全部收窄为"只在闲聊/广告语境下才成立"的多字短语.
# ⚠️ 2026-09-10 二次收窄: 裸词 "试卷" "私信" "卷子" 仍会误伤 (t=684 讲"阅卷只看20秒"窗口含"试卷",
# t=3848 讲顾明远窗口含"私信"), 已删去裸词、只保留语境明确的形式 "这套卷子" / "这套卷啊" / "私信我发" / "私信发我".
# 新增词条前先自问: 这个字符串会不会出现在**正当讲授内容**里? 会, 就必须加限定字.
IDLE_MARKERS = [
    "这首歌", "这套卷子", "这套卷啊", "讲套卷子", "下课", "闲聊", "插播", "中场",
    "课间休息一下", "课间聊", "课间的时候我们", "大家放松", "咱们休息",
    "休息一下", "休息十分钟", "休息会儿", "私信我发", "私信发我", "加微信", "推广", "扫码",
    "发福利", "领福利", "福利课", "福利群", "插播广告", "打个广告", "广告时间",
    "没听懂没关系", "这个歌", "听首歌", "来首歌", "咱们聊", "闲话", "先歇",
]


def parse_srt(srt_path):
    """返回按 start 升序的 (start, end, text) 列表."""
    with open(srt_path, "r", encoding="utf-8-sig") as f:
        lines = f.readlines()
    entries = []
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if line.isdigit():
            i += 1
            if i >= len(lines):
                break
            ts_line = lines[i].strip()
            m = re.match(
                r"(\d{2}):(\d{2}):(\d{2}),(\d{3})\s*-->\s*(\d{2}):(\d{2}):(\d{2}),(\d{3})",
                ts_line,
            )
            if not m:
                i += 1
                continue
            sh, sm, ss, _ = (int(m.group(k)) for k in (1, 2, 3, 4))
            eh, em, es, _ = (int(m.group(k)) for k in (5, 6, 7, 8))
            start = 3600 * sh + 60 * sm + ss
            end = 3600 * eh + 60 * em + es
            i += 1
            parts = []
            while i < len(lines) and lines[i].strip():
                parts.append(lines[i].strip())
                i += 1
            entries.append((start, end, " ".join(parts)))
        i += 1
    entries.sort(key=lambda e: e[0])
    return entries


def window_around(entries, target, before=15, after=45):
    """取 target 秒附近窗口内的字幕文本 (用于关键词匹配与展示)."""
    # 找匹配条目: start<=target<=end, 否则取 start 最接近 target 且 <=target 的, 再退化为最近.
    matched = None
    for e in entries:
        if e[0] <= target <= e[1]:
            matched = e
            break
    if matched is None:
        cands = [e for e in entries if e[0] <= target]
        if cands:
            matched = max(cands, key=lambda e: e[0])
        elif entries:
            matched = min(entries, key=lambda e: abs(e[0] - target))
    if matched is None:
        return "", ""
    mi = entries.index(matched)
    lo = max(0, mi - 3)
    hi = min(len(entries), mi + 8)
    ctx = entries[lo:hi]
    full = " ".join(e[2] for e in ctx)
    return matched[2], full


STOPWORDS = set("的了吗呢吧啊在和与及或用了等从到中上下内外也都就而即将把被给个这那你我他它们是否即些其并又再很更最被让使于对为因该当每各任何哪怎啥")


def _cjk_tokens(s):
    """从一段文本切出 >=2 字的中文 token (按非中文/分隔符断开)."""
    toks = re.split(r"[^一-鿿]+", s)
    out = []
    for t in toks:
        t = t.strip()
        if len(t) >= 2:
            out.append(t)
    return out


def extract_keywords(md_line, section=""):
    """从 md 行提取用于匹配的关键词.

    优先级: 加粗词(按 / , 、 ; 等分隔符拆成多个) > 行首普通词(冒号前) > 节标题词.
    只取 >=2 字中文 token, 过滤停用词. 返回去重列表(最多 6 个).
    """
    kws = []
    for b in re.findall(r"\*\*(.+?)\*\*", md_line):
        for piece in re.split(r"[/,，、;；:：.。]+", b):
            kws.extend(_cjk_tokens(piece))
    # 行首普通词: 去掉 "N. " 前缀, 取到首个冒号/左括号前的内容
    body = re.sub(r"^\s*\d+\.\s*", "", md_line)
    head = re.split(r"[:：(\（\[]", body, 1)[0]
    kws.extend(_cjk_tokens(head))
    if section:
        kws.extend(_cjk_tokens(section))
    seen = []
    for k in kws:
        if k in STOPWORDS:
            continue
        if k not in seen:
            seen.append(k)
    return seen[:6]


def main():
    if len(sys.argv) < 3:
        print("usage: verify_video_links.py <MD_PATH> <SRT_PATH> "
              "[--window-before 15] [--window-after 45]")
        sys.exit(2)
    md_path = sys.argv[1]
    srt_path = sys.argv[2]
    before, after = 15, 45
    if "--window-before" in sys.argv:
        before = int(sys.argv[sys.argv.index("--window-before") + 1])
    if "--window-after" in sys.argv:
        after = int(sys.argv[sys.argv.index("--window-after") + 1])

    entries = parse_srt(srt_path)
    if not entries:
        print("ERROR: srt 解析为空", file=sys.stderr)
        sys.exit(2)

    with open(md_path, "r", encoding="utf-8") as f:
        md_lines = f.readlines()

    # 收集每条视频链接: (行号1基, 秒, 该行文本, 所属 ## 𒋙 节)
    links = []          # (lineno, sec, text)
    section = "(开头)"
    for idx, raw in enumerate(md_lines, 1):
        line = raw.rstrip("\n")
        h = re.match(r"^##\s*𒋙?\s*(.+)$", line)
        if h:
            section = h.group(1).strip()
            continue
        for sec in re.findall(r"mp4#t=(\d+)", line):
            links.append((idx, int(sec), line, section))

    if not links:
        print("未找到任何 mp4#t= 链接. 退出.")
        sys.exit(0)

    print("=" * 78)
    print("视频链接语义审计: %s" % os.path.basename(md_path))
    print("字幕: %s  (条目 %d, 末秒 %d)" % (os.path.basename(srt_path), len(entries), entries[-1][0]))
    print("=" * 78)

    warn = 0
    idle_n = dup_n = 0
    keymiss_hints = 0
    order_soft = 0
    prev_sec_in_section = {}
    sec_global_count = {}

    for lineno, sec, text, section in links:
        matched_text, full_window = window_around(entries, sec, before, after)
        kws = extract_keywords(text, section)
        # 关键词匹配: 任一关键词出现在窗口 (软提示用, 不计入强制门槛)
        hit = any(kw in full_window for kw in kws) if kws else True
        # 闲聊段检测 (高精度, 强制)
        idle = any(mk in full_window for mk in IDLE_MARKERS)
        # 同时间戳重复检测 (高精度, 强制): 同一秒数被两条及以上链接使用, 几乎必错
        sec_global_count[sec] = sec_global_count.get(sec, 0) + 1
        dup = sec_global_count[sec] >= 2
        # 同节倒挂 (软提示): 单次向后引用可能是合理的"前段讲解", 仅提醒不阻断
        order_jump = False
        if section in prev_sec_in_section:
            if sec < prev_sec_in_section[section]:
                order_jump = True
        prev_sec_in_section[section] = sec

        hard = []
        if idle:
            hard.append("IDLE")
        if dup:
            hard.append("DUP")

        if hard:
            mark = "⚠ " + ",".join(hard)
            warn += 1
            if "IDLE" in hard:
                idle_n += 1
            if "DUP" in hard:
                dup_n += 1
            print("L%-3d t=%-5d [%s] %s" % (lineno, sec, section[:10], mark))
            print("       md : %s" % text[:30].replace("\n", " "))
            print("       srt: %s" % matched_text[:80])
        elif order_jump:
            order_soft += 1
            print("L%-3d t=%-5d [%s] · ORDER?(软提示: 同节时间戳倒挂, 请确认是合理前引)"
                  % (lineno, sec, section[:10]))
            print("       md : %s" % text[:30].replace("\n", " "))
            print("       srt: %s" % matched_text[:80])
        else:
            if not hit and kws:
                keymiss_hints += 1
                print("L%-3d t=%-5d [%s] · KEYMISS(软提示, 请肉眼复核窗口)"
                      % (lineno, sec, section[:10]))
                print("       md : %s" % text[:30].replace("\n", " "))
                print("       srt: %s" % matched_text[:80])
            else:
                print("L%-3d t=%-5d [%s]   ✓" % (lineno, sec, section[:10]))
                print("       srt: %s" % matched_text[:80])

    print("=" * 78)
    print("强制门槛: IDLE=%d, DUP(同秒重复)=%d  (任一 >0 必须修复后再 present)"
          % (idle_n, dup_n))
    print("软提示: ORDER?=%d (同节倒挂, 合理前引可忽略), KEYMISS=%d (窗口对得上可忽略)"
          % (order_soft, keymiss_hints))
    print("链接总数: %d" % len(links))
    if warn:
        print(">>> 存在强制 ⚠ (IDLE/DUP), 消掉后再 present_files.")
        sys.exit(1)
    else:
        print(">>> 强制门槛通过, 请顺带扫一眼软提示的窗口确认无误.")
        sys.exit(0)


if __name__ == "__main__":
    main()
