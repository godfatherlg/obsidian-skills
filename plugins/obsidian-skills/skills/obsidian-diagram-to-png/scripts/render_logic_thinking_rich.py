# -*- coding: utf-8 -*-
"""抽象逻辑思维（丰富版）：凭借物三分类对照 + 形式逻辑/辩证逻辑展开 + 判据条

在 render_logic_thinking.py 基础上扩展三层：
- 顶部：按凭借物/发展水平分类（直观动作 -> 具体形象 -> 抽象逻辑）三块横排，
  右端"抽象逻辑思维"为蓝系高亮主角，向下接主体结构；
- 中部：抽象逻辑思维向下分两支（形式逻辑思维 / 辩证逻辑思维），
  左支展开成容器 + 横排子块（概念 -> 判断（命题） -> 推理）；
- 底部：灰底判据条，写"具体与抽象的分界 = 思维的拐杖"及皮亚杰阶段映射。
坐标一律 0-100 百分数，y 轴向上。
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
GRAY_F, GRAY_E, GRAY_T, GRAY_S = "#F1EFE8", "#B4B2A9", "#2C2C2A", "#5F5E5A"

fig, ax = plt.subplots(figsize=(11, 8.2), dpi=280)
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


# ---------- 顶部：按凭借物分类（发展顺序） ----------
band = [
    (3, 26, "直观动作思维", "靠动作与操作", BLUE_F, BLUE_E, BLUE_T),
    (37, 26, "具体形象思维", "靠实物与表象", BLUE_F, BLUE_E, BLUE_T),
    (71, 26, "抽象逻辑思维", "靠概念与符号", "#D3E7F9", BLUE_E, BLUE_T),
]
for bx, bw, title, sub, fc, ec, tc in band:
    box(bx, 84, bw, 14, fc, ec, 1.2)
    txt(bx + bw / 2.0, 93.0, title, 12.5, tc, "bold")
    txt(bx + bw / 2.0, 88.4, sub, 10, ec)

arrow(29.6, 91, 36.4, 91)
arrow(63.6, 91, 70.4, 91)
txt(50, 80.4, "思维的凭借物由实物走向概念（拐杖不同）", 10, GRAY_S)

# ---------- 分叉连线：抽象逻辑思维 -> 两支 ----------
ax.plot([84, 84], [84, 78], color=BLUE_E, linewidth=1.2, zorder=1)
ax.plot([30, 84], [78, 78], color=BLUE_E, linewidth=1.2, zorder=1)
arrow(30, 78, 30, 73)
arrow(84, 78, 84, 73)

# ---------- 左支：形式逻辑思维 ----------
box(18, 61, 24, 12, BLUE_F, BLUE_E, 1.2)
txt(30, 68.6, "形式逻辑思维", 13, BLUE_T, "bold")
txt(30, 64.0, "按固定规则、公式逐步推导", 10.5, BLUE_E)

# ---------- 右支：辩证逻辑思维 ----------
box(72, 61, 24, 12, AMB_F, AMB_E, 1.2)
txt(84, 68.6, "辩证逻辑思维", 13, AMB_D, "bold")
txt(84, 64.0, "从正反两个方面思考问题", 10.5, AMB_T)

arrow(30, 61, 30, 55)
ax.plot([84, 84], [61, 55], color=AMB_E, linewidth=1.0,
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

# ---------- 底部判据条 ----------
box(2, 3, 96, 17.5, GRAY_F, GRAY_E, 1.6, lw=1.0)
txt(50, 16.4, "具体与抽象的分界 = 思维的拐杖", 11.5, GRAY_T, "bold")
txt(50, 10.6, "具体形象思维：靠实物与表象；皮亚杰具体运算 7-11 岁（能借助具体形象做简单的逻辑推理）", 9.5, GRAY_S)
txt(50, 6.2, "抽象逻辑思维：脱离具体事物；皮亚杰形式运算 11 岁以后（符号、隐喻和直喻，假设—演绎推理）", 9.5, GRAY_S)

out = r"<vault>\images\思维形式-形式逻辑与辩证逻辑.png"
os.makedirs(os.path.dirname(out), exist_ok=True)
fig.savefig(out, dpi=280, facecolor="white", bbox_inches="tight", pad_inches=0.12)
plt.close(fig)
print("saved:", out)
