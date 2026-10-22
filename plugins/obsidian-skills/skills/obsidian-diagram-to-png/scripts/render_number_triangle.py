"""Render a Yang Hui / Pascal number triangle to a PNG for Obsidian notes.

Usage:
    python render_number_triangle.py [rows] [outfile]

Defaults: rows=7, outfile=<vault>\\images\\杨辉三角-前七行.png

Styling follows the user's preference: white background, light blue internal
cells, grey edge cells, SimHei for CJK, mathtext for the (a+b)^n row labels.
"""
import os
import sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
from matplotlib import font_manager

font_path = r"C:\Windows\Fonts\simhei.ttf"
if os.path.exists(font_path):
    font_manager.fontManager.addfont(font_path)
    plt.rcParams["font.family"] = "SimHei"
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["mathtext.fontset"] = "dejavusans"

rows = int(sys.argv[1]) if len(sys.argv) > 1 else 7
out = sys.argv[2] if len(sys.argv) > 2 else r"<vault>\images\杨辉三角-前七行.png"

tri = [[1]]
for n in range(1, rows):
    prev = tri[-1]
    tri.append([1] + [prev[k - 1] + prev[k] for k in range(1, n)] + [1])

dx, dy = 1.0, 0.82
fig, ax = plt.subplots(figsize=(9.2, 5.6), dpi=330)
ax.set_xlim(-4.0, 4.6)
ax.set_ylim(-rows * dy - 0.4, 0.7)
ax.axis("off")
ax.set_aspect("equal")

for n in range(rows):
    for k, v in enumerate(tri[n]):
        x = (k - n / 2.0) * dx
        y = -n * dy
        edge = (n == 0) or (k == 0) or (k == n)
        face = "#F2F4F7" if edge else "#DCE9F7"
        ec = "#8A94A6" if edge else "#3E7CB1"
        ax.add_patch(FancyBboxPatch(
            (x - 0.36, y - 0.28), 0.72, 0.56,
            boxstyle="round,pad=0.02,rounding_size=0.10",
            linewidth=1.2, edgecolor=ec, facecolor=face, zorder=2))
        ax.text(x, y, str(v), ha="center", va="center", fontsize=13,
                color="#1F2933", zorder=3)
    ax.text(n / 2.0 * dx + 1.15, -n * dy, r"$(a+b)^{%d}$" % n,
            ha="left", va="center", fontsize=12, color="#3E7CB1")

ax.text(0, 0.45, "杨辉三角（二项式系数三角）", ha="center", va="center",
        fontsize=14, color="#1F2933")

os.makedirs(os.path.dirname(out), exist_ok=True)
fig.savefig(out, bbox_inches="tight", pad_inches=0.18, facecolor="white")
print("saved", out)
