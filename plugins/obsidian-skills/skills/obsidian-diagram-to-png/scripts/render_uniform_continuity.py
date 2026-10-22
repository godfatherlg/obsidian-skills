"""Render the 'continuity vs uniform continuity' comparison figure.

Left panel: pointwise continuity -- for the SAME epsilon, the admissible delta
shrinks where the curve is steep (delta depends on x0).
Right panel: uniform continuity -- one single delta works for every point.

Usage:
    python render_uniform_continuity.py [outfile]
Default output: <vault>\\images\\一致连续-连续与一致连续对比.png
"""
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib import font_manager

OUT = sys.argv[1] if len(sys.argv) > 1 else r"<vault>\images\一致连续-连续与一致连续对比.png"
FONT = r"C:\Windows\Fonts\simhei.ttf"

if os.path.exists(FONT):
    font_manager.fontManager.addfont(FONT)
plt.rcParams["font.family"] = "SimHei"
plt.rcParams["mathtext.fontset"] = "dejavusans"
plt.rcParams["axes.unicode_minus"] = False

f = lambda x: x ** 3
fp = lambda x: 3 * x ** 2

EPS = 0.3
XA, XB = 0.6, 1.9
DA = EPS / fp(XA)
DB = EPS / fp(XB)

C_TEXT = "#2C2C2A"
C_MUTE = "#5F5E5A"


def draw_panel(ax, deltas, title, sub, footer, c_fill, c_edge, c_curve):
    ax.set_facecolor(c_fill)
    for s in ax.spines.values():
        s.set_visible(False)
    ax.set_xlim(-0.12, 2.2)
    ax.set_ylim(-1.5, 9.6)
    ax.set_xticks([])
    ax.set_yticks([])

    ax.annotate("", xy=(2.18, 0), xytext=(-0.05, 0),
                arrowprops=dict(arrowstyle="-|>", color="#888780", lw=0.9))
    ax.annotate("", xy=(0, 9.4), xytext=(0, -1.2),
                arrowprops=dict(arrowstyle="-|>", color="#888780", lw=0.9))

    xs = np.linspace(0, 2.06, 400)
    ax.plot(xs, f(xs), color=c_curve, lw=2.0)

    for x0, d in zip((XA, XB), deltas):
        y0 = f(x0)
        lo, hi = y0 - EPS, y0 + EPS
        for y in (lo, hi):
            ax.plot([x0 - d, x0 + d], [y, y], color=c_edge, lw=1.0,
                    linestyle=(0, (4, 2)))
        for x in (x0 - d, x0 + d):
            ax.plot([x, x], [lo, hi], color=c_edge, lw=1.0,
                    linestyle=(0, (4, 2)))
        ax.plot([x0], [y0], marker="o", color=c_curve, ms=5)
        lab = "δ" if d == DB else ("δ 大" if x0 == XA else "δ 小")
        y_mark = -0.45 if x0 == XA else -1.05
        ax.annotate("", xy=(x0 + d, y_mark), xytext=(x0 - d, y_mark),
                    arrowprops=dict(arrowstyle="<|-|>", color=c_edge, lw=1.2))
        ax.text(x0, y_mark - 0.42, lab, ha="center", va="top",
                fontsize=11, color=C_TEXT)

    ax.text(XA, f(XA) + EPS + 0.75, "平缓处", ha="center", fontsize=12,
            color=C_MUTE)
    ax.text(XB, f(XB) + EPS + 0.6, "陡峭处", ha="center", fontsize=12,
            color=C_MUTE)

    ax.set_title(title, fontsize=15, color=C_TEXT, pad=14)
    ax.text(1.05, 10.35, sub, ha="center", fontsize=11, color=C_MUTE)
    ax.text(1.05, -1.95, footer, ha="center", fontsize=12, color=C_TEXT)
    for patch in ax.patches:
        pass


def main():
    fig, axes = plt.subplots(1, 2, figsize=(12, 5.6), dpi=250)
    draw_panel(axes[0], (DA, DB),
               "连续 (逐点定义)",
               r"$\delta=\delta(\varepsilon,x_0)$, 各点各不相同",
               "δ 的正下界可能为 0",
               "#FAEEDA", "#BA7517", "#993C1D")
    draw_panel(axes[1], (DB, DB),
               "一致连续",
               r"$\delta=\delta(\varepsilon)$, 全段共用一个",
               "取最窄处的 δ, 仍是正数",
               "#E1F5EE", "#1D9E75", "#0F6E56")
    fig.patch.set_facecolor("white")
    fig.tight_layout(w_pad=4.0)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    fig.savefig(OUT, facecolor="white", bbox_inches="tight")
    print("written:", OUT)
    print("delta_A=%.4f delta_B=%.4f" % (DA, DB))


if __name__ == "__main__":
    main()
