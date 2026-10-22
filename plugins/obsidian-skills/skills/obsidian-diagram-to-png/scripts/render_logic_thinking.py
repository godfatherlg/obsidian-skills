# -*- coding: utf-8 -*-
"""中学生思维发展特点：形式逻辑思维的三种基本形式 + 与辩证逻辑思维的关系

层级结构图模板：顶层一个概念框 -> 下分左右两支（左支继续展开成容器 + 横排子块）。
改内容只需改下方"内容区"的文字与坐标；坐标一律用 0-100 x 0-100 的百分数。
"""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
from matplotlib import font_manager

FP = r"C:\Windows\Fonts\simhei.ttf"
if os.path.exists(FP):
    font_manager.fontManager.addfont(FP)
plt.rcParams["font.family"] = "SimHei"
plt.rcParams["mathtext.fontset"] = "dejavusans"

BLUE_F, BLUE_E, BLUE_T = "#E6F1FB", "#185FA5", "#0C447C"
BLUE_L = "#85B7EB"
AMB_F, AMB_E, AMB_T = "#FAEEDA", "#EF9F27", "#854F0B"
AMB_D = "#633806"

fig, ax = plt.subplots(figsize=(11, 5.6), dpi=280)
ax.set_xlim(0, 100)
ax.set_ylim(0, 100)
ax.axis("off")
fig.patch.set_facecolor("white")


def box(x, y, w, h, fc, ec, rs, lw=1.2, z=2):
    ax.add_patch(FancyBboxPatch(
        (x, y), w, h,
        boxstyle="round,pad=0.0,rounding_size=%.3f" % rs,
        linewidth=lw, edgecolor=ec, facecolor=fc, zorder=z))


def txt(x, y, s, size, color, weight="normal", z=3):
    ax.text(x, y, s, ha="center", va="center", fontsize=size,
            color=color, fontweight=weight, zorder=z)


def arrow(x1, y1, x2, y2, color=BLUE_E, lw=1.2, z=2):
    ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle="-|>", color=color, linewidth=lw,
                                shrinkA=0, shrinkB=0), zorder=z)


# ---------- 顶层 ----------
box(43, 84, 24, 12, BLUE_F, BLUE_E, 1.2)
txt(55, 91.6, "抽象逻辑思维", 13, BLUE_T, "bold")
txt(55, 87.0, "又称抽象思维", 10.5, BLUE_E)

# ---------- 分叉连线 ----------
ax.plot([55, 55], [84, 79], color=BLUE_E, linewidth=1.2, zorder=1)
ax.plot([30, 80], [79, 79], color=BLUE_E, linewidth=1.2, zorder=1)
arrow(30, 79, 30, 73)
arrow(80, 79, 80, 73)

# ---------- 左支：形式逻辑思维 ----------
box(18, 61, 24, 12, BLUE_F, BLUE_E, 1.2)
txt(30, 68.6, "形式逻辑思维", 13, BLUE_T, "bold")
txt(30, 64.0, "按固定规则、公式逐步推导", 10.5, BLUE_E)

# ---------- 右支：辩证逻辑思维 ----------
box(68, 61, 24, 12, AMB_F, AMB_E, 1.2)
txt(80, 68.6, "辩证逻辑思维", 13, AMB_D, "bold")
txt(80, 64.0, "从正反两个方面思考问题", 10.5, AMB_T)

arrow(30, 61, 30, 55)
ax.plot([80, 80], [61, 55], color=AMB_E, linewidth=1.0,
        linestyle=(0, (3, 2)), zorder=1)

# ---------- 左支展开：三种基本形式 ----------
box(2, 25, 56, 30, "none", BLUE_L, 2.0, lw=1.0)
txt(30, 50.5, "形式逻辑思维的三种基本形式", 10.5, BLUE_E)

blocks = [
    (5, 13, "概念", 13),
    (21, 18, "判断（命题）", 12.5),
    (42, 13, "推理", 13),
]
for bx, bw, label, size in blocks:
    box(bx, 28, bw, 16, BLUE_F, BLUE_E, 1.3)
    txt(bx + bw / 2.0, 36, label, size, BLUE_T, "bold")

txt(19.5, 36, "→", 12, BLUE_E)
txt(40.5, 36, "→", 12, BLUE_E)

# ---------- 右支说明框 ----------
box(62, 25, 36, 30, "none", AMB_E, 2.0, lw=1.0)
txt(80, 47.0, "两者是同一层级的一对", 12.5, AMB_D, "bold")
txt(80, 38.5, "形式逻辑按规则推演", 10.5, AMB_T)
txt(80, 30.5, "辩证逻辑看正反两面", 10.5, AMB_T)

out = r"<vault>\images\思维形式-形式逻辑与辩证逻辑.png"
os.makedirs(os.path.dirname(out), exist_ok=True)
fig.savefig(out, dpi=280, facecolor="white", bbox_inches="tight", pad_inches=0.12)
plt.close(fig)
print("saved:", out)
