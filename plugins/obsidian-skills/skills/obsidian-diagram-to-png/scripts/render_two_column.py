# -*- coding: utf-8 -*-
"""布鲁纳双维度辨析图：学科中心（课程内容维度） vs 发现学习（课程实施维度）"""
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
TEAL_F, TEAL_E, TEAL_T = "#E1F5EE", "#0F6E56", "#085041"
AMB_F, AMB_E, AMB_T = "#FAEEDA", "#BA7517", "#854F0B"
GRAY_F, GRAY_E, GRAY_T = "#F1EFE8", "#B4B2A9", "#5F5E5A"
WHITE, DARK = "#FFFFFF", "#1F2933"

fig, ax = plt.subplots(figsize=(11, 6.2), dpi=190)
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


# 左容器：课程内容维度
box(2, 26, 46, 70, BLUE_F, BLUE_E, 3.0)
txt(25, 90.5, "课程内容维度（学什么）", 13.5, BLUE_T, "bold")

items = [
    ("要素主义 · 巴格莱", "人类文化的共同要素", 68, WHITE, BLUE_E, DARK),
    ("永恒主义 · 赫钦斯", "永恒学科与经典名著", 51, WHITE, BLUE_E, DARK),
    ("结构主义 · 布鲁纳", "学科的基本结构", 34, AMB_F, AMB_E, AMB_T),
]
for title, sub, y, fc, ec, tc in items:
    box(5, y, 40, 13, fc, ec, 1.3)
    txt(25, y + 8.4, title, 12.5, tc, "bold")
    txt(25, y + 4.2, sub, 10.5, tc)

# 右容器：课程实施维度
box(52, 26, 46, 70, TEAL_F, TEAL_E, 3.0)
txt(75, 90.5, "课程实施维度（怎么学）", 13.5, TEAL_T, "bold")

box(55, 52, 40, 16, WHITE, TEAL_E, 1.5)
txt(75, 63.2, "发现学习（布鲁纳）", 12.5, DARK, "bold")
txt(75, 57.0, "学生像科学家那样自己发现", 10.5, DARK)
txt(75, 40, "不参与流派归属的判断", 10.5, GRAY_T)

# 虚线：同一人物跨两维度
ax.plot([48.5, 55], [40.5, 59.5], color="#888780", linewidth=1.0,
        linestyle=(0, (4, 2)), zorder=2)

# 底部判据条
box(2, 4, 96, 16, GRAY_F, GRAY_E, 1.6, lw=1.0)
txt(50, 15.0, "判据：看课程内容的组织中心，不看是否让学生活动", 12.5, DARK, "bold")
txt(50, 8.0, "布鲁纳的内容中心是学科基本结构，所以归学科中心；发现学习只是他主张的获取方式", 10.5, GRAY_T)

out = r"<vault>\images\布鲁纳-学科中心与发现学习.png"
os.makedirs(os.path.dirname(out), exist_ok=True)
fig.savefig(out, dpi=190, facecolor="white", bbox_inches="tight", pad_inches=0.12)
plt.close(fig)
print("saved:", out)
