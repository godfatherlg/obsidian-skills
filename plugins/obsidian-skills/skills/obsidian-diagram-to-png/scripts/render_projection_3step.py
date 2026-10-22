"""投影变换：投影到倾角 alpha 的直线的「旋转三步法」流程图。

四面板：初始 -> 乘 R(-alpha) 转平 -> 投 x 轴 -> 乘 R(alpha) 转回。

Usage:
    python render_projection_3step.py [outfile]

Default outfile: <vault>\\images\\投影变换-旋转三步法.png
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

out = sys.argv[1] if len(sys.argv) > 1 else r"<vault>\images\投影变换-旋转三步法.png"

GRAY = "#B4B2A9"
DARK = "#26215C"
PURPLE = "#534AB7"
RED = "#A32D2D"
LBL = "#5F5E5A"

ALPHA = 35.0
a = np.radians(ALPHA)


def rot(v, ang):
    c, s = np.cos(ang), np.sin(ang)
    return np.array([c * v[0] - s * v[1], s * v[0] + c * v[1]])


r, th = 0.95, np.radians(8.0)
P = np.array([r * np.cos(th), r * np.sin(th)])
P1 = rot(P, -a)
P2 = np.array([P1[0], 0.0])
Pp = rot(P2, a)


def axis(ax, length=1.30):
    ax.plot([-0.35, length], [0, 0], color=GRAY, lw=1.1, zorder=1)
    ax.plot([0, 0], [-0.80, 1.15], color=GRAY, lw=1.1, zorder=1)
    ax.annotate("", xy=(length, 0), xytext=(length - 0.10, 0),
                arrowprops=dict(arrowstyle="-|>", color=GRAY, lw=1.1))
    ax.annotate("", xy=(0, 1.15), xytext=(0, 1.05),
                arrowprops=dict(arrowstyle="-|>", color=GRAY, lw=1.1))
    ax.text(length + 0.06, 0.02, "x", fontsize=11, color=LBL)
    ax.text(0.07, 1.19, "y", fontsize=11, color=LBL)


def draw_l(ax, ang, color, lw=2.0, ls="-", lo=-0.45, hi=1.20):
    c, s = np.cos(ang), np.sin(ang)
    ax.plot([lo * c, hi * c], [lo * s, hi * s], color=color, lw=lw, ls=ls, zorder=2)


def setup(ax, title, tcolor):
    ax.set_aspect("equal")
    ax.set_xlim(-0.72, 1.50)
    ax.set_ylim(-1.66, 1.36)
    ax.axis("off")
    ax.set_title(title, fontsize=13, color=tcolor, pad=8)


def arc(ax, a0, a1, rad, color, lw=1.2):
    t = np.linspace(np.radians(a0), np.radians(a1), 240)
    ax.plot(rad * np.cos(t), rad * np.sin(t), color=color, lw=lw, zorder=2)
    tip = np.radians(a1)
    prev = tip - np.radians(3) if a1 >= a0 else tip + np.radians(3)
    ax.annotate("", xy=(rad * np.cos(tip), rad * np.sin(tip)),
                xytext=(rad * np.cos(prev), rad * np.sin(prev)),
                arrowprops=dict(arrowstyle="-|>", color=color, lw=lw))


def right_angle(ax, foot, u, v, size=0.11):
    u = u / np.linalg.norm(u)
    v = v / np.linalg.norm(v)
    A = foot + size * u
    B = A + size * v
    C = foot + size * v
    ax.plot([A[0], B[0], C[0]], [A[1], B[1], C[1]], color=GRAY, lw=1.0, zorder=3)


def foot_notes(ax, L1, L2):
    ax.text(0.39, -1.10, L1, ha="center", fontsize=12, color="#1F2933")
    ax.text(0.39, -1.40, L2, ha="center", fontsize=11, color=LBL)


fig, axes = plt.subplots(1, 4, figsize=(15.5, 4.7), dpi=200)
fig.suptitle("投影到倾角 $\\alpha$ 的直线：旋转三步法", fontsize=16, color=DARK)

# ---------- 面板 1：初始 ----------
ax = axes[0]
setup(ax, "初始：l 是斜的", DARK)
axis(ax)
draw_l(ax, a, DARK, 2.2)
ax.text(1.26 * np.cos(a), 1.26 * np.sin(a), "l", fontsize=13, color=DARK)
arc(ax, 0, ALPHA, 0.42, GRAY)
ax.text(0.60 * np.cos(np.radians(ALPHA / 2)),
        0.60 * np.sin(np.radians(ALPHA / 2)) + 0.03,
        "$\\alpha$", fontsize=13, color=LBL)
ax.scatter([P[0]], [P[1]], s=70, facecolor="#CECBF6", edgecolor=PURPLE, zorder=4)
ax.text(P[0] + 0.06, P[1] - 0.02, "$P$", fontsize=14, color=DARK)
foot_notes(ax, "l 倾角 $\\alpha$，点 P 在旁边", "前提：l 必须过原点")

# ---------- 面板 2：转 -alpha ----------
ax = axes[1]
setup(ax, "第 1 步：乘 $R(-\\alpha)$", PURPLE)
axis(ax)
draw_l(ax, a, GRAY, 1.2, ls=(0, (4, 2)), hi=1.00)
draw_l(ax, 0.0, DARK, 2.4)
ax.text(1.28, 0.07, "l", fontsize=13, color=DARK)
arc(ax, ALPHA, 0, 0.55, PURPLE)
ax.text(0.76 * np.cos(np.radians(ALPHA / 2)),
        0.76 * np.sin(np.radians(ALPHA / 2)) + 0.03,
        "$-\\alpha$", fontsize=13, color=PURPLE)
ax.scatter([P1[0]], [P1[1]], s=70, facecolor="#CECBF6", edgecolor=PURPLE, zorder=4)
ax.text(P1[0] + 0.06, P1[1] - 0.02, "$P_1$", fontsize=14, color=DARK)
foot_notes(ax, "整图转 $-\\alpha$，l 躺到 x 轴", "点跟着转到 $P_1$")

# ---------- 面板 3：投 x 轴 ----------
ax = axes[2]
setup(ax, "第 2 步：投 x 轴", PURPLE)
axis(ax)
draw_l(ax, 0.0, DARK, 2.4)
ax.text(1.28, 0.07, "l", fontsize=13, color=DARK)
ax.plot([P1[0], P2[0]], [P1[1], P2[1]], ls=(0, (4, 2)), color=PURPLE, lw=1.2, zorder=2)
right_angle(ax, P2, np.array([1.0, 0.0]), P1 - P2)
ax.scatter([P1[0]], [P1[1]], s=40, facecolor="#AFA9EC", edgecolor=PURPLE, zorder=3)
ax.scatter([P2[0]], [P2[1]], s=70, facecolor="#CECBF6", edgecolor=PURPLE, zorder=4)
ax.text(P1[0] + 0.06, P1[1] - 0.05, "$P_1$", fontsize=13, color=PURPLE)
ax.text(P2[0] + 0.07, 0.07, "$P_2$", fontsize=14, color=DARK)
foot_notes(ax, "左乘 x 轴投影矩阵", "纵坐标压成 0，$P_1\\to P_2$")

# ---------- 面板 4：转回 +alpha ----------
ax = axes[3]
setup(ax, "第 3 步：乘 $R(\\alpha)$", RED)
axis(ax)
draw_l(ax, 0.0, GRAY, 1.2, ls=(0, (4, 2)), hi=1.00)
draw_l(ax, a, DARK, 2.2)
ax.text(1.26 * np.cos(a), 1.26 * np.sin(a), "l", fontsize=13, color=DARK)
arc(ax, 0, ALPHA, 0.55, RED)
ax.text(0.76 * np.cos(np.radians(ALPHA / 2)),
        0.76 * np.sin(np.radians(ALPHA / 2)) + 0.03,
        "$+\\alpha$", fontsize=13, color=RED)
ax.scatter([Pp[0]], [Pp[1]], s=95, facecolor="#F7C1C1", edgecolor=RED, zorder=4)
ax.text(Pp[0] + 0.06, Pp[1] - 0.02, "$P'$", fontsize=15, color=RED)
foot_notes(ax, "整图转回 $+\\alpha$", "$P'$ 落在 l 上，投影完成")

fig.subplots_adjust(left=0.02, right=0.98, top=0.86, bottom=0.02, wspace=0.22)
os.makedirs(os.path.dirname(out), exist_ok=True)
fig.savefig(out, bbox_inches="tight", pad_inches=0.14, facecolor="white")
print("saved", out)
