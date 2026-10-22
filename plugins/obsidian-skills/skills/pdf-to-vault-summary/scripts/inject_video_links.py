import io, os, re, sys

if len(sys.argv) < 2:
    print("usage: inject_video_links.py <md_path> [vmap_path]")
    sys.exit(1)

md_path = sys.argv[1]
base = os.path.splitext(os.path.basename(md_path))[0]  # 去 .md 得到视频基名
vmap_path = sys.argv[2] if len(sys.argv) >= 3 else (md_path + ".vmap.txt")

# 读取映射: 每行 "文件行号<TAB或空格>秒数"
mapping = {}
with io.open(vmap_path, encoding="utf-8") as f:
    for raw in f:
        raw = raw.strip()
        if not raw:
            continue
        parts = re.split(r"\s+", raw, maxsplit=1)
        if len(parts) != 2:
            continue
        try:
            mapping[int(parts[0])] = int(parts[1])
        except ValueError:
            continue

with io.open(md_path, encoding="utf-8") as f:
    lines = f.read().split("\n")

added = 0
skipped = 0
for idx, line in enumerate(lines, start=1):
    if idx in mapping:
        sec = mapping[idx]
        if ".mp4#t=" in line:        # 已有视频链接则跳过,避免重复
            skipped += 1
            continue
        link = " [[%s.mp4#t=%d|视频]]" % (base, sec)
        lines[idx - 1] = line.rstrip() + link
        added += 1

with io.open(md_path, "w", encoding="utf-8") as f:
    f.write("\n".join(lines))

print("added=%d skipped=%d total_lines=%d" % (added, skipped, len(lines)))
