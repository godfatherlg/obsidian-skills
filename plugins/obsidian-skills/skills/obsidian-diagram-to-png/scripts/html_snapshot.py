#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
HTML → PNG 快照工具（不重排，纯截图）。

用途：当内容已经是 HTML（例如 show_widget 生成、或用户提供的 HTML 文件，
以及任何 CSS 排版好的表格/卡片）时，用无头浏览器按原始布局截图，
得到像素级忠实于原排版的 PNG。**绝不逐块重画**（重画=重排，会越界/串列）。

用法：
    python html_snapshot.py <input.html> <output.png> [--scale 3] [--width 760] [--crop]

依赖：Windows 上的 Edge（Chromium 内核），或 CHROME 环境变量指向 chrome/msedge。
"""
import argparse, io, os, subprocess, sys, tempfile, time

BROWSERS = [
    os.environ.get("CHROME", ""),
    r"C:/Program Files/Google/Chrome/Application/chrome.exe",
    r"C:/Program Files (x86)/Google/Chrome/Application/chrome.exe",
    r"C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe",
    r"C:/Program Files/Microsoft/Edge/Application/msedge.exe",
]

def find_browser():
    for b in BROWSERS:
        if b and os.path.isfile(b):
            return b
    sys.exit("找不到 Chrome/Edge，可设 CHROME 环境变量指向浏览器 exe")

def snapshot(html_path, out_path, scale=3, width=760, crop=True, pad=24):
    browser = find_browser()
    html = io.open(html_path, encoding="utf-8").read()

    tmpdir = tempfile.gettempdir()
    tmp_html = os.path.join(tmpdir, "_snap_src.html")     # 纯 ASCII 路径，避开中文路径坑
    tmp_png  = os.path.join(tmpdir, "_snap_out.png")
    io.open(tmp_html, "w", encoding="utf-8").write(html)
    if os.path.exists(tmp_png):
        os.remove(tmp_png)

    cmd = [browser, "--headless=new", "--disable-gpu", "--no-sandbox",
           "--hide-scrollbars", f"--force-device-scale-factor={scale}",
           f"--window-size={width},1400",
           f"--screenshot={tmp_png}", "file:///" + tmp_html.replace("\\", "/")]
    subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    if not os.path.exists(tmp_png):
        sys.exit("截图失败：浏览器未产出 PNG")

    if crop:
        try:
            import numpy as np
            from PIL import Image
            im = Image.open(tmp_png).convert("RGB")
            a = np.asarray(im)
            nw = (a.sum(axis=2) < 740)
            rows, cols = nw.any(axis=1), nw.any(axis=0)
            t = int(rows.argmax()); bt = len(rows) - int(rows[::-1].argmax())
            l = int(cols.argmax()); r = len(cols) - int(cols[::-1].argmax())
            im = im.crop((max(0,l-pad), max(0,t-pad),
                          min(im.width,r+pad), min(im.height,bt+pad)))
            im.save(out_path)
        except Exception as e:
            print("裁边跳过:", e); 
            import shutil; shutil.copy(tmp_png, out_path)
    else:
        import shutil; shutil.copy(tmp_png, out_path)

    from PIL import Image
    im = Image.open(out_path)
    print(f"OK  {out_path}  {im.size}  {os.path.getsize(out_path)//1024} KB  (scale={scale})")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("html"); ap.add_argument("out")
    ap.add_argument("--scale", type=int, default=3)
    ap.add_argument("--width", type=int, default=760)
    ap.add_argument("--no-crop", action="store_true")
    a = ap.parse_args()
    snapshot(a.html, a.out, a.scale, a.width, crop=not a.no_crop)
