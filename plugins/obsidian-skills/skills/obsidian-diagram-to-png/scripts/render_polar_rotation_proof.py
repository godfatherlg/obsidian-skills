"""极坐标证明：转点公式（极角 +alpha）与转轴公式（极角 -alpha）。

Usage:
    python render_polar_rotation_proof.py [outfile]

Default outfile: <vault>\\images\\坐标旋转-极坐标证明.png
"""
import os
import sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

font_path = r"C:\Windows\Fonts\simhei.ttf"
if os.path.exists(font_path):
    font_manager.fontManager.addfont(font_path)
    plt.rcParams["font.family"] = "SimHei"
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["mathtext.fontset"] = "dejavusans"

out = sys.argv[1] if len(sys.argv) > 1 else r"<vault>\images\坐标旋转-极坐标证明.png"

GRAY = "#B4B2A9"
LBL = "#5F5E5A"
BLUE = "#185FA5"
TEAL = "#0F6E56"
PURPLE = "#534AB7"

PHI = 65.0
ALPHA = 45.0


def pol(ang, r):
    return r * np.cos(np.radians(ang)), r * np.sin(np.radians(ang))


def full_axis(ax, ang, length, color, ls, lw=1.2):
    dx, dy = np.cos(np.radians(ang)), np.sin(np.radians(ang))
    ax.plot([-dx * length * 0.75, dx * length],
            [-dy * length * 0.75, dy * length],
            color=color, ls=ls, lw=lw, zorder=1)
    ax.annotate("", xy=(dx * length, dy * length),
                xytext=(dx * length * 0.92, dy * length * 0.92),
                arrowprops=dict(arrowstyle="-|>", color=color, lw=lw))


def arc(ax, a0, a1, r, color, lw=1.3):
    t = np.linspace(np.radians(a0), np.radians(a1), 240)
    ax.plot(r * np.cos(t), r * np.sin(t), color=color, lw=lw, zorder=2)
    ax.annotate("", xy=pol(a1, r), xytext=pol(a1 - 2.5, r),
                arrowprops=dict(arrowstyle="-|>", color=color, lw=lw))


def setup(ax, title, color):
    ax.set_aspect("equal")
    ax.set_xlim(-1.4, 1.5)
    ax.set_ylim(-1.95, 1.5)
    ax.axis("off")
    ax.set_title(title, fontsize=15, color=color, pad=10)


fig, axes = plt.subplots(1, 2, figsize=(11, 5.6), dpi=280)

# ---------- 左：转点，极角 phi -> phi + alpha ----------
ax = axes[0]
setup(ax, "转点：轴不动，点转 $+\\alpha$", "#0C447C")
full_axis(ax, 0, 1.25, GRAY, "-")
full_axis(ax, 90, 1.25, GRAY, "-")
ax.text(1.36, 0.04, "x", fontsize=12, color=LBL)
ax.text(0.06, 1.33, "y", fontsize=12, color=LBL)

px, py = pol(PHI, 1.0)
qx, qy = pol(PHI + ALPHA, 1.0)
ax.plot([0, px], [0, py], "--", color=GRAY, lw=1.2, zorder=2)
ax.plot([0, qx], [0, qy], "-", color=BLUE, lw=1.8, zorder=3)
ax.scatter([px], [py], s=80, facecolor="#B5D4F4", edgecolor=BLUE, zorder=4)
ax.scatter([qx], [qy], s=80, facecolor="#378ADD", edgecolor=BLUE, zorder=4)
ax.text(px + 0.08, py + 0.02, "$P$", fontsize=14, color=BLUE)
ax.text(qx - 0.22, qy + 0.05, "$P'$", fontsize=14, color=BLUE)
ax.text(0.52 * np.cos(np.radians(PHI / 2)), 0.52 * np.sin(np.radians(PHI / 2)) - 0.02,
        "$r$", fontsize=13, color=LBL)

arc(ax, 0, PHI, 0.42, GRAY)
arc(ax, PHI, PHI + ALPHA, 0.62, PURPLE)
arc(ax, 0, PHI + ALPHA, 0.92, BLUE)
ax.text(*pol(PHI / 2, 0.55), "$\\varphi$", fontsize=15, color=LBL)
ax.text(*pol(PHI + ALPHA / 2, 0.78), "$\\alpha$", fontsize=15, color=PURPLE)
ax.text(*pol((PHI + ALPHA) / 2, 1.08), "$\\varphi+\\alpha$", fontsize=15, color="#0C447C")

ax.text(0, -1.42, "$x'=x\\cos\\alpha-y\\sin\\alpha$", ha="center", fontsize=15, color="#1F2933")
ax.text(0, -1.62, "$y'=x\\sin\\alpha+y\\cos\\alpha$", ha="center", fontsize=15, color="#1F2933")
ax.text(0, -1.86, "极角变为 $\\varphi+\\alpha$，$r$ 不变", ha="center", fontsize=13, color=LBL)

# ---------- 右：转轴，点相对新轴极角 phi - alpha ----------
ax = axes[1]
setup(ax, "转轴：点不动，轴转 $+\\alpha$", "#085041")
full_axis(ax, 0, 1.25, GRAY, "-")
full_axis(ax, 90, 1.25, GRAY, "-")
ax.text(1.36, 0.04, "x", fontsize=12, color=LBL)
ax.text(0.06, 1.33, "y", fontsize=12, color=LBL)
full_axis(ax, ALPHA, 1.28, TEAL, "--", 1.5)
full_axis(ax, 90 + ALPHA, 1.28, TEAL, "--", 1.5)
ax.text(1.02, 0.98, "$x'$", fontsize=14, color="#085041")
ax.text(-1.04, 0.96, "$y'$", fontsize=14, color="#085041")

rx, ry = pol(PHI, 1.0)
ax.plot([0, rx], [0, ry], "-", color=TEAL, lw=1.8, zorder=3)
ax.scatter([rx], [ry], s=80, facecolor="#9FE1CB", edgecolor=TEAL, zorder=4)
ax.text(rx + 0.07, ry + 0.02, "$P$ 不动", fontsize=13, color="#085041")
ax.text(0.52 * np.cos(np.radians(PHI / 2)), 0.52 * np.sin(np.radians(PHI / 2)) - 0.02,
        "$r$", fontsize=13, color=LBL)

arc(ax, 0, ALPHA, 0.95, TEAL)
arc(ax, 0, PHI, 0.42, GRAY)
arc(ax, ALPHA, PHI, 0.64, PURPLE)
ax.text(*pol(ALPHA / 2, 1.10), "$\\alpha$", fontsize=15, color=TEAL)
ax.text(*pol(PHI / 2, 0.55), "$\\varphi$", fontsize=15, color=LBL)
ax.text(*pol((ALPHA + PHI) / 2, 0.80), "$\\varphi-\\alpha$", fontsize=15, color=PURPLE)

ax.text(0, -1.42, "$x'=x\\cos\\alpha+y\\sin\\alpha$", ha="center", fontsize=15, color="#1F2933")
ax.text(0, -1.62, "$y'=-x\\sin\\alpha+y\\cos\\alpha$", ha="center", fontsize=15, color="#1F2933")
ax.text(0, -1.86, "相对新轴极角为 $\\varphi-\\alpha$", ha="center", fontsize=13, color=LBL)

os.makedirs(os.path.dirname(out), exist_ok=True)
fig.savefig(out, bbox_inches="tight", pad_inches=0.18, facecolor="white")
print("saved", out)
