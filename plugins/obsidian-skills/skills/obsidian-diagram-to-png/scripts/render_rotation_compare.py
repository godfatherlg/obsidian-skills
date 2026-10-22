"""Render a side-by-side comparison of rotating a point vs rotating the axes.

Usage:
    python render_rotation_compare.py [outfile]

Default outfile: <vault>\\images\\坐标旋转-转点与转轴对比.png
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

out = sys.argv[1] if len(sys.argv) > 1 else r"<vault>\images\坐标旋转-转点与转轴对比.png"

GRAY = "#B4B2A9"
BLUE = "#185FA5"
TEAL = "#0F6E56"


def axis_line(ax, angle_deg, length, color, ls, lw=1.2):
    dx, dy = np.cos(np.radians(angle_deg)), np.sin(np.radians(angle_deg))
    ax.plot([-dx * length * 0.4, dx * length], [-dy * length * 0.4, dy * length],
            color=color, ls=ls, lw=lw, zorder=1)
    ax.annotate("", xy=(dx * length, dy * length),
                xytext=(dx * length * 0.92, dy * length * 0.92),
                arrowprops=dict(arrowstyle="-|>", color=color, lw=lw))


def arc_arrow(ax, a0, a1, r, color):
    p0 = (r * np.cos(np.radians(a0)), r * np.sin(np.radians(a0)))
    p1 = (r * np.cos(np.radians(a1)), r * np.sin(np.radians(a1)))
    ax.annotate("", xy=p1, xytext=p0,
                arrowprops=dict(arrowstyle="-|>", color=color, lw=1.4,
                                connectionstyle="arc3,rad=0.55"))


def setup(ax):
    ax.set_aspect("equal")
    ax.set_xlim(-1.45, 1.5)
    ax.set_ylim(-1.65, 1.5)
    ax.axis("off")


def point(ax, angle_deg, r, face, edge):
    x, y = r * np.cos(np.radians(angle_deg)), r * np.sin(np.radians(angle_deg))
    ax.scatter([x], [y], s=70, facecolor=face, edgecolor=edge, zorder=4)
    return x, y


fig, axes = plt.subplots(1, 2, figsize=(11, 5.2), dpi=280)

# Left: rotating the point, axes fixed
ax = axes[0]
setup(ax)
axis_line(ax, 0, 1.25, GRAY, "-")
axis_line(ax, 90, 1.25, GRAY, "-")
ax.text(1.36, 0.05, "x", fontsize=12, color="#5F5E5A")
ax.text(0.07, 1.33, "y", fontsize=12, color="#5F5E5A")
px, py = 1.0 * np.cos(np.radians(20)), 1.0 * np.sin(np.radians(20))
qx, qy = 1.0 * np.cos(np.radians(70)), 1.0 * np.sin(np.radians(70))
ax.plot([0, px], [0, py], "--", color=GRAY, lw=1.1, zorder=2)
ax.plot([0, qx], [0, qy], "-", color=BLUE, lw=1.7, zorder=3)
ax.scatter([px], [py], s=80, facecolor="#B5D4F4", edgecolor=BLUE, zorder=4)
ax.scatter([qx], [qy], s=80, facecolor="#378ADD", edgecolor=BLUE, zorder=4)
ax.text(px + 0.07, py - 0.06, r"$P(x,y)$", fontsize=13, color=BLUE)
ax.text(qx - 0.62, qy + 0.06, r"$P'(x',y')$", fontsize=13, color=BLUE)
arc_arrow(ax, 20, 70, 0.45, BLUE)
ax.text(0.55 * np.cos(np.radians(52)), 0.55 * np.sin(np.radians(52)) + 0.05,
        r"$\alpha$", fontsize=14, color="#0C447C")
ax.text(0, -1.42, r"$x'=x\cos\alpha-y\sin\alpha$", ha="center", fontsize=14,
        color="#1F2933")
ax.set_title(r"转点：轴不动，点转 $+\alpha$", fontsize=15, color="#0C447C", pad=12)

# Right: rotating the axes, point fixed
ax = axes[1]
setup(ax)
axis_line(ax, 0, 1.25, GRAY, "--")
axis_line(ax, 90, 1.25, GRAY, "--")
ax.text(1.36, 0.05, "x", fontsize=12, color="#888780")
ax.text(0.07, 1.33, "y", fontsize=12, color="#888780")
axis_line(ax, 45, 1.25, TEAL, "-", 1.6)
axis_line(ax, 135, 1.25, TEAL, "-", 1.6)
ax.text(1.02, 0.96, r"$x'$", fontsize=13, color="#085041")
ax.text(-1.02, 0.96, r"$y'$", fontsize=13, color="#085041")
rx, ry = point(ax, 20, 1.0, "#9FE1CB", TEAL)
ax.plot([0, rx], [0, ry], "--", color=TEAL, lw=1.1, zorder=2)
ax.text(rx + 0.07, ry - 0.06, "点 P 不动", fontsize=13, color="#085041")
arc_arrow(ax, 0, 45, 0.62, TEAL)
ax.text(0.74 * np.cos(np.radians(30)), 0.74 * np.sin(np.radians(30)) - 0.02,
        r"$\alpha$", fontsize=14, color="#085041")
ax.text(0, -1.42, r"$x'=x\cos\alpha+y\sin\alpha$", ha="center", fontsize=14,
        color="#1F2933")
ax.set_title(r"转轴：点不动，轴转 $+\alpha$", fontsize=15, color="#085041", pad=12)

os.makedirs(os.path.dirname(out), exist_ok=True)
fig.savefig(out, bbox_inches="tight", pad_inches=0.18, facecolor="white")
print("saved", out)
