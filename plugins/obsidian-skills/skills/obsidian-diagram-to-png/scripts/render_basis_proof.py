"""基向量法证明：转点=加法合成，转轴=内积分解，两矩阵互为转置。

Usage:
    python render_basis_proof.py [outfile]

Default outfile: <vault>\\images\\坐标旋转-基向量合成与分解.png
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

out = sys.argv[1] if len(sys.argv) > 1 else r"<vault>\images\坐标旋转-基向量合成与分解.png"

GRAY = "#B4B2A9"
LBL = "#5F5E5A"
BLUE = "#185FA5"
TEAL = "#0F6E56"

ALPHA = 40.0
E1 = np.array([np.cos(np.radians(ALPHA)), np.sin(np.radians(ALPHA))])
E2 = np.array([-np.sin(np.radians(ALPHA)), np.cos(np.radians(ALPHA))])


def full_axis(ax, vec, length, color, ls, lw=1.2):
    v = np.asarray(vec, dtype=float)
    ax.plot([-v[0] * length * 0.6, v[0] * length],
            [-v[1] * length * 0.6, v[1] * length],
            color=color, ls=ls, lw=lw, zorder=1)
    ax.annotate("", xy=(v[0] * length, v[1] * length),
                xytext=(v[0] * length * 0.92, v[1] * length * 0.92),
                arrowprops=dict(arrowstyle="-|>", color=color, lw=lw))


def arc(ax, a0, a1, r, color, lw=1.3):
    t = np.linspace(np.radians(a0), np.radians(a1), 240)
    ax.plot(r * np.cos(t), r * np.sin(t), color=color, lw=lw, zorder=2)
    ax.annotate("", xy=(r * np.cos(np.radians(a1)), r * np.sin(np.radians(a1))),
                xytext=(r * np.cos(np.radians(a1 - 2.5)), r * np.sin(np.radians(a1 - 2.5))),
                arrowprops=dict(arrowstyle="-|>", color=color, lw=lw))


def right_angle(ax, foot, u, v, size=0.10):
    u = u / np.linalg.norm(u)
    v = v / np.linalg.norm(v)
    a = foot + size * u
    b = a + size * v
    c = foot + size * v
    ax.plot([a[0], b[0], c[0]], [a[1], b[1], c[1]], color=GRAY, lw=1.0, zorder=3)


def setup(ax, title, color):
    ax.set_aspect("equal")
    ax.set_xlim(-1.5, 1.5)
    ax.set_ylim(-1.95, 1.5)
    ax.axis("off")
    ax.set_title(title, fontsize=15, color=color, pad=10)


fig, axes = plt.subplots(1, 2, figsize=(11, 5.6), dpi=280)

# ---------- 左：转点 = 合成 ----------
ax = axes[0]
setup(ax, "转点 = 合成：$P'=x\\vec{e}_1^{*}+y\\vec{e}_2^{*}$", "#0C447C")
full_axis(ax, [1, 0], 1.25, GRAY, "-")
full_axis(ax, [0, 1], 1.25, GRAY, "-")
ax.text(1.36, 0.04, "x", fontsize=12, color=LBL)
ax.text(0.06, 1.33, "y", fontsize=12, color=LBL)

cx, cy = 1.12 * E1
dx, dy = 0.72 * E2
p = np.array([cx, cy]) + np.array([dx, dy])
ax.plot([0, cx], [0, cy], "-", color=BLUE, lw=1.9, zorder=3)
ax.plot([0, dx], [0, dy], "-", color=BLUE, lw=1.9, zorder=3)
ax.plot([cx, p[0]], [cy, p[1]], "--", color=BLUE, lw=0.9, zorder=2)
ax.plot([dx, p[0]], [dy, p[1]], "--", color=BLUE, lw=0.9, zorder=2)
ax.scatter([p[0]], [p[1]], s=80, facecolor="#378ADD", edgecolor=BLUE, zorder=4)
ax.scatter([cx], [cy], s=34, facecolor=BLUE, zorder=4)
ax.scatter([dx], [dy], s=34, facecolor=BLUE, zorder=4)
ax.text(p[0] + 0.06, p[1] + 0.03, "$P'$", fontsize=14, color=BLUE)
ax.text(cx * 0.62 - 0.06, cy * 0.62 - 0.10, "$x\\vec{e}_1^{*}$", fontsize=14, color=BLUE)
ax.text(dx * 0.66 - 0.20, dy * 0.66 - 0.06, "$y\\vec{e}_2^{*}$", fontsize=14, color=BLUE)

arc(ax, 0, ALPHA, 0.44, GRAY)
ax.text(0.56 * np.cos(np.radians(ALPHA / 2)), 0.56 * np.sin(np.radians(ALPHA / 2)) + 0.02,
        "$\\alpha$", fontsize=15, color=LBL)

ax.text(0, -1.44, "系数 $x,y$ 照抄，转动的是基", ha="center", fontsize=14, color="#1F2933")
ax.text(0, -1.66, "已知系数求向量 $\\Rightarrow$ 用加法", ha="center", fontsize=13, color=LBL)

# ---------- 右：转轴 = 分解 ----------
ax = axes[1]
setup(ax, "转轴 = 分解：$x'=P\\cdot\\vec{e}_1',\\ y'=P\\cdot\\vec{e}_2'$", "#085041")
full_axis(ax, [1, 0], 1.25, GRAY, "-")
full_axis(ax, [0, 1], 1.25, GRAY, "-")
ax.text(1.36, 0.04, "x", fontsize=12, color=LBL)
ax.text(0.06, 1.33, "y", fontsize=12, color=LBL)
full_axis(ax, E1, 1.28, TEAL, "--", 1.5)
full_axis(ax, E2, 1.28, TEAL, "--", 1.5)
ax.text(1.02, 0.98, "$\\vec{e}_1'$", fontsize=14, color="#085041")
ax.text(-1.06, 0.94, "$\\vec{e}_2'$", fontsize=14, color="#085041")

P = np.array([np.cos(np.radians(75.0)), np.sin(np.radians(75.0))])
f1 = float(P @ E1) * E1
f2 = float(P @ E2) * E2
ax.plot([0, f1[0]], [0, f1[1]], "-", color=TEAL, lw=1.9, zorder=3)
ax.plot([0, f2[0]], [0, f2[1]], "-", color=TEAL, lw=1.9, zorder=3)
ax.plot([f1[0], P[0]], [f1[1], P[1]], ":", color=GRAY, lw=1.0, zorder=2)
ax.plot([f2[0], P[0]], [f2[1], P[1]], ":", color=GRAY, lw=1.0, zorder=2)
right_angle(ax, f1, -E1, P - f1)
right_angle(ax, f2, -E2, P - f2)
ax.scatter([P[0]], [P[1]], s=80, facecolor="#9FE1CB", edgecolor=TEAL, zorder=4)
ax.scatter([f1[0]], [f1[1]], s=34, facecolor=TEAL, zorder=4)
ax.scatter([f2[0]], [f2[1]], s=34, facecolor=TEAL, zorder=4)
ax.text(P[0] + 0.06, P[1] + 0.02, "$P$", fontsize=14, color="#085041")
ax.text(f1[0] * 0.60 - 0.02, f1[1] * 0.60 - 0.14, "$x'$", fontsize=14, color=TEAL)
ax.text(f2[0] * 0.62 - 0.14, f2[1] * 0.62 - 0.12, "$y'$", fontsize=14, color=TEAL)

arc(ax, 0, ALPHA, 1.02, GRAY)
ax.text(1.16 * np.cos(np.radians(ALPHA / 2)), 1.16 * np.sin(np.radians(ALPHA / 2)) - 0.02,
        "$\\alpha$", fontsize=15, color=LBL)

ax.text(0, -1.44, "点不动，换基后用内积拆分量", ha="center", fontsize=14, color="#1F2933")
ax.text(0, -1.66, "已知向量求系数 $\\Rightarrow$ 用投影", ha="center", fontsize=13, color=LBL)

os.makedirs(os.path.dirname(out), exist_ok=True)
fig.savefig(out, bbox_inches="tight", pad_inches=0.18, facecolor="white")
print("saved", out)
