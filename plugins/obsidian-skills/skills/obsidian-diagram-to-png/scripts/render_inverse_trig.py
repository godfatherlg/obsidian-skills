r"""渲染反三角函数两张图 -> <vault>\images\

1) 反三角函数-主值曲线与值域.png  : arcsin / arccos / arctan 三条主值曲线
2) 反三角函数-互余关系直角三角形.png: 直角三角形说明 arcsin+arccos=pi/2 与 arctan+arccot=pi/2

用法:
    python render_inverse_trig.py [输出目录]
默认输出目录 <vault>\images
"""
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.patches import Polygon
import numpy as np

FONT = r"C:\Windows\Fonts\simhei.ttf"
if os.path.exists(FONT):
    font_manager.fontManager.addfont(FONT)
plt.rcParams["font.family"] = "SimHei"
plt.rcParams["mathtext.fontset"] = "dejavusans"
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["font.size"] = 13

OUT_DIR = sys.argv[1] if len(sys.argv) > 1 else r"<vault>\images"

BLUE = "#185FA5"
AMBER = "#BA7517"
TEAL = "#0F6E56"
GRAY = "#5F5E5A"
INK = "#2C2C2A"

PI = np.pi


def style_axes(ax, xlim, ylim, xticks, xticklabels, yticks, yticklabels):
    ax.set_xlim(*xlim)
    ax.set_ylim(*ylim)
    for side in ("right", "top"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_position("zero")
        ax.spines[side].set_color(GRAY)
        ax.spines[side].set_linewidth(1.0)
    ax.set_xticks(xticks)
    ax.set_xticklabels(xticklabels)
    ax.set_yticks(yticks)
    ax.set_yticklabels(yticklabels)
    ax.tick_params(axis="both", colors=INK, labelsize=12, length=4)
    ax.set_facecolor("white")


def render_curves(path):
    fig, axes = plt.subplots(1, 3, figsize=(14.2, 4.9), facecolor="white")
    fig.subplots_adjust(bottom=0.24, top=0.86, wspace=0.32)

    ax = axes[0]
    x = np.linspace(-1, 1, 800)
    ax.plot(x, np.arcsin(x), color=BLUE, lw=2.2, solid_capstyle="round")
    ax.scatter([-1.0, 1.0], [-PI / 2, PI / 2], color=BLUE, s=28, zorder=3)
    style_axes(ax, (-1.35, 1.35), (-1.95, 1.95),
               [-1, 0, 1], ["-1", "0", "1"],
               [-PI / 2, PI / 2], [r"$-\frac{\pi}{2}$", r"$\frac{\pi}{2}$"])
    ax.set_title(r"$y=\arcsin x$", color=BLUE, fontsize=16, pad=12)

    ax = axes[1]
    x = np.linspace(-1, 1, 800)
    ax.plot(x, np.arccos(x), color=AMBER, lw=2.2, solid_capstyle="round")
    ax.scatter([-1.0, 1.0], [PI, 0.0], color=AMBER, s=28, zorder=3)
    style_axes(ax, (-1.35, 1.35), (-0.45, 3.55),
               [-1, 0, 1], ["-1", "0", "1"],
               [0, PI], ["0", r"$\pi$"])
    ax.set_title(r"$y=\arccos x$", color=AMBER, fontsize=16, pad=12)

    ax = axes[2]
    x = np.linspace(-8, 8, 4000)
    ax.plot(x, np.arctan(x), color=TEAL, lw=2.2, solid_capstyle="round")
    for sign in (-1, 1):
        ax.axhline(sign * PI / 2, color=TEAL, lw=1.0, alpha=0.75,
                   linestyle=(0, (4, 3)))
    ax.text(-7.7, PI / 2 + 0.10, r"$y=\frac{\pi}{2}$", fontsize=12, color=TEAL)
    ax.text(-7.7, -PI / 2 + 0.10, r"$y=-\frac{\pi}{2}$", fontsize=12, color=TEAL)
    style_axes(ax, (-8.0, 8.0), (-1.95, 1.95),
               [-6, -3, 0, 3, 6], ["-6", "-3", "0", "3", "6"],
               [-PI / 2, PI / 2], [r"$-\frac{\pi}{2}$", r"$\frac{\pi}{2}$"])
    ax.set_title(r"$y=\arctan x$", color=TEAL, fontsize=16, pad=12)

    fig.savefig(path, dpi=220, facecolor="white")
    plt.close(fig)


def angle_arc(ax, vertex, a0, a1, r, color):
    t = np.linspace(np.radians(a0), np.radians(a1), 80)
    ax.plot(vertex[0] + r * np.cos(t), vertex[1] + r * np.sin(t),
            color=color, lw=1.1)


def right_angle_mark(ax, P, s, color):
    ax.plot([P[0], P[0] + s, P[0] + s], [P[1] + s, P[1] + s, P[1]],
            color=color, lw=1.1)


def draw_triangle(ax, P, Q, R, fill, edge, name_a, name_b,
                  opp, adj, hyp, eq1, eq2, ylim_top):
    ax.add_patch(Polygon([P, Q, R], closed=True,
                         facecolor=fill, edgecolor=edge, lw=1.6))
    right_angle_mark(ax, P, 0.14, edge)

    ang_r_p = 180.0
    ang_r_q = np.degrees(np.arctan2(Q[1] - R[1], Q[0] - R[0]))
    ang_q_p = -90.0
    ang_q_r = np.degrees(np.arctan2(R[1] - Q[1], R[0] - Q[0]))
    angle_arc(ax, R, ang_r_q, ang_r_p, 0.30, edge)
    angle_arc(ax, Q, ang_q_p, ang_q_r, 0.30, edge)

    bis_r = np.radians((ang_r_q + ang_r_p) / 2.0)
    bis_q = np.radians((ang_q_p + ang_q_r) / 2.0)
    ax.text(R[0] + 0.42 * np.cos(bis_r), R[1] + 0.42 * np.sin(bis_r),
            name_a, ha="center", va="center", fontsize=15, color=edge)
    ax.text(Q[0] + 0.42 * np.cos(bis_q), Q[1] + 0.42 * np.sin(bis_q),
            name_b, ha="center", va="center", fontsize=15, color=edge)

    ax.text(P[0] - 0.07, (P[1] + Q[1]) / 2.0, opp,
            ha="right", va="center", fontsize=13, color=INK)
    ax.text((P[0] + R[0]) / 2.0, P[1] - 0.10, adj,
            ha="center", va="top", fontsize=13, color=INK)

    mx, my = (Q[0] + R[0]) / 2.0, (Q[1] + R[1]) / 2.0
    dx, dy = R[0] - Q[0], R[1] - Q[1]
    n = np.hypot(dx, dy)
    nx, ny = -dy / n, dx / n
    ax.text(mx + 0.20 * nx, my + 0.20 * ny, hyp,
            ha="center", va="center", fontsize=13, color=INK)

    ax.set_xlim(-0.95, 2.05)
    ax.set_ylim(-0.62, ylim_top)
    ax.set_aspect("equal")
    ax.axis("off")
    cx = (P[0] + R[0]) / 2.0
    ax.text(cx, -0.30, eq1, ha="center", va="top", fontsize=14, color=INK)
    ax.text(cx, -0.50, eq2, ha="center", va="top", fontsize=15, color=edge)


def render_triangles(path):
    fig, axes = plt.subplots(1, 2, figsize=(11.2, 4.6), facecolor="white")
    fig.subplots_adjust(left=0.02, right=0.98, top=0.95, bottom=0.04, wspace=0.10)

    draw_triangle(axes[0], (0.0, 0.0), (0.0, 0.8), (1.4, 0.0),
                  "#E6F1FB", BLUE, r"$\alpha$", r"$\beta$",
                  "对边 = $x$", "邻边 = $\\sqrt{1-x^2}$", "斜边 = $1$",
                  r"$\alpha=\arcsin x,\ \beta=\arccos x$",
                  r"$\alpha+\beta=\frac{\pi}{2}$", 1.30)

    draw_triangle(axes[1], (0.0, 0.0), (0.0, 1.05), (1.4, 0.0),
                  "#E1F5EE", TEAL, r"$\theta$", r"$\varphi$",
                  "对边 = $x$", "邻边 = $1$", "斜边 = $\\sqrt{1+x^2}$",
                  r"$\theta=\arctan x,\ \varphi=\mathrm{arccot}\,x$",
                  r"$\theta+\varphi=\frac{\pi}{2}$", 1.55)

    fig.savefig(path, dpi=220, bbox_inches="tight", facecolor="white")
    plt.close(fig)


if __name__ == "__main__":
    os.makedirs(OUT_DIR, exist_ok=True)
    p1 = os.path.join(OUT_DIR, "反三角函数-主值曲线与值域.png")
    p2 = os.path.join(OUT_DIR, "反三角函数-互余关系直角三角形.png")
    render_curves(p1)
    render_triangles(p2)
    for p in (p1, p2):
        print(p, os.path.getsize(p), "bytes")
