# -*- coding: utf-8 -*-
"""渲染「科二秒题技巧知识点图」(三维课程目标 + 课程实施取向) 为 PNG。"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
from matplotlib import font_manager as fm

fm.fontManager.addfont(r"C:\Windows\Fonts\simhei.ttf")
plt.rcParams["font.family"] = "SimHei"
plt.rcParams["axes.unicode_minus"] = False

OUT = r"<vault>\images\科二秒题技巧-三维目标与实施取向.png"

fig, ax = plt.subplots(figsize=(11, 8.4), dpi=280)
ax.set_xlim(0, 100)
ax.set_ylim(0, 100)
ax.axis("off")


def box(x, y, w, h, fc, ec, rs=0.08, lw=1.6, alpha=1.0):
    ax.add_patch(FancyBboxPatch(
        (x, y), w, h,
        boxstyle=f"round,pad=0.02,rounding_size={rs}",
        fc=fc, ec=ec, lw=lw, alpha=alpha, zorder=1))


def txt(x, y, s, size=10, color="#1F2933", weight="normal", zorder=3):
    ax.text(x, y, s, size=size, color=color, weight=weight,
            ha="center", va="center", zorder=zorder)


def arrow(x1, y1, x2, y2, color="#5B6470"):
    ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle="-|>", color=color, lw=1.4),
                zorder=2)


# ---- 顶部根节点 (紫色) ----
box(32, 91, 36, 6, "#7C5CBF", "#5B3E96", rs=0.12, lw=1.8)
txt(50, 94, "科二 · 第2章 中学课程", size=13, color="white", weight="bold")

# ---- 左右两大列容器 ----
box(4, 24, 45, 65, "#EEF3FB", "#3E7CB1", rs=0.06, lw=2)          # 左蓝
box(51, 24, 45, 65, "#FDF1E7", "#D98324", rs=0.06, lw=2)         # 右橙

# 列头
box(6, 81, 41, 7, "#3E7CB1", "#3E7CB1", rs=0.12)
txt(26.5, 84.5, "三维课程目标", size=12, color="white", weight="bold")
box(53, 81, 41, 7, "#D98324", "#D98324", rs=0.12)
txt(73.5, 84.5, "课程实施取向 (辛德三取向)", size=12, color="white", weight="bold")

# ---- 左列 3 子块 ----
left_subs = [
    (71, "知识与技能目标", "会读会写会说会背 · 掌握公式"),
    (61, "过程与方法目标", "参与感受经历 · 体验探究"),
    (51, "情感态度价值观目标", "精神体会之情 · 价值倾向"),
]
for y, title, hint in left_subs:
    box(8, y, 37, 7, "#DCE9F7", "#3E7CB1")
    txt(26.5, y + 4.4, title, size=11, color="#14385E", weight="bold")
    txt(26.5, y + 1.6, hint, size=9, color="#1F2933")

# ---- 右列 3 子块 ----
right_subs = [
    (71, "忠实取向", "不打折扣执行既定方案"),
    (61, "相互调适取向", "上课中按本班学情删减调整"),
    (51, "创生取向", "新课改 · 教师即课程开发者"),
]
for y, title, hint in right_subs:
    box(55, y, 37, 7, "#FBE6D2", "#D98324")
    txt(73.5, y + 4.4, title, size=11, color="#8A4B12", weight="bold")
    txt(73.5, y + 1.6, hint, size=9, color="#1F2933")

# ---- 根到列头连线 ----
arrow(50, 91, 26.5, 88)
arrow(50, 91, 73.5, 88)

# ---- 底部两框 ----
box(4, 6, 45, 15, "#E3F4E1", "#2E7D32", rs=0.06, lw=1.8)
txt(26.5, 16.5, "舒伯特四种目标价值取向", size=11, color="#1B5E20", weight="bold")
txt(26.5, 11, "普遍性目标 · 行为性目标 · 生成性目标 · 表现性目标", size=9, color="#1F2933")
arrow(26.5, 24, 26.5, 21)

box(51, 6, 45, 15, "#FBE3E3", "#C62828", rs=0.06, lw=1.8)
txt(73.5, 16.5, "同题干冲突 (删减内容加趣味)", size=11, color="#B71C1C", weight="bold")
txt(73.5, 11, "相互适应取向 / 创生取向", size=9, color="#1F2933")
arrow(73.5, 24, 73.5, 21)

fig.savefig(OUT, dpi=280, bbox_inches="tight", facecolor="white")
print("saved", OUT)
