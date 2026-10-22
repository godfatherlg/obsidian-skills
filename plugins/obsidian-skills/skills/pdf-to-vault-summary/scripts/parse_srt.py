import os, re, sys

if len(sys.argv) < 2:
    print("usage: parse_srt.py <srt_path> [out_path]")
    sys.exit(1)

srt_path = sys.argv[1]
out_path = sys.argv[2] if len(sys.argv) >= 3 else os.path.join(
    os.path.dirname(os.path.abspath(srt_path)), "srt_sec.txt")

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
            ts_line)
        if m:
            h, mm, ss = int(m.group(1)), int(m.group(2)), int(m.group(3))
            sec = 3600 * h + 60 * mm + ss  # 绝对秒数, Obsidian 媒体时间戳需要
            i += 1
            parts = []
            while i < len(lines) and lines[i].strip():
                parts.append(lines[i].strip())
                i += 1
            entries.append("[%d] %s" % (sec, " ".join(parts)))
    i += 1

with open(out_path, "w", encoding="utf-8") as f:
    f.write("\n".join(entries))

print("entries:", len(entries), "->", out_path)
