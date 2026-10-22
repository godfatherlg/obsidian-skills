import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon, FancyBboxPatch, Circle, Rectangle
from matplotlib.font_manager import fontManager

fp = r"C:\Windows\Fonts\simhei.ttf"
if os.path.exists(fp):
    fontManager.addfont(fp)
plt.rcParams["font.family"] = "SimHei"
plt.rcParams["mathtext.fontset"] = "dejavusans"
plt.rcParams["axes.unicode_minus"] = False

# 参考标准: 人教版高中数学必修3《算法初步》程序框图符号; GB/T 1526-1989 信息处理流程图图形符号.
# 关键区分: 起止框=圆角矩形, 处理框=直角矩形; 连接点成对出现且标同一字母, 两点之间不画流程线.

# 配色: 起止框紫色(圆角), 输入/输出与处理框蓝色, 判断框琥珀色, 连接点灰
TERM_F, TERM_E, TERM_T = "#E9E2F7", "#6B3FA0", "#4A2270"
IO_F, IO_E, IO_T = "#E6F1FB", "#185FA5", "#0C447C"
PROC_F, PROC_E, PROC_T = "#E6F1FB", "#185FA5", "#0C447C"
DIA_F, DIA_E, DIA_T = "#FAEEDA", "#854F0B", "#633806"
GF, GE, GT = "#F1EFE8", "#888780", "#444441"
LN = "#5F5E5A"

fig, ax = plt.subplots(figsize=(9, 11), dpi=340)
ax.set_xlim(0.2, 8.8)
ax.set_ylim(2.6, 10.6)
ax.axis("off")


def term(x0, y0, w, h, fc, ec, tc):
    """起止框: 圆角矩形 (教材标准, 圆角约占框高 46%, 外形明显区别于直角矩形)."""
    ax.add_patch(FancyBboxPatch((x0, y0), w, h,
                 boxstyle="round,pad=0,rounding_size=%.3f" % (h * 0.46),
                 linewidth=1.6, edgecolor=ec, facecolor=fc))
    ax.text(x0 + w / 2, y0 + h / 2, "", color=tc)


def proc(x0, y0, w, h, fc, ec, tc):
    """处理框: 直角矩形, 绝不能给圆角 —— 否则与起止框无法区分."""
    ax.add_patch(Rectangle((x0, y0), w, h, linewidth=1.6, edgecolor=ec, facecolor=fc))


def pbox(x0, y0, w, h, fc, ec, tc, sk=0.3):
    """输入, 输出框: 平行四边形."""
    ax.add_patch(Polygon([(x0 + sk, y0), (x0 + w, y0), (x0 + w - sk, y0 + h), (x0, y0 + h)],
                         closed=True, linewidth=1.6, edgecolor=ec, facecolor=fc))


def diam(cx, cy, hw, hh, fc, ec, tc):
    """判断框: 菱形, 两个出口分别标 Y 与 N."""
    ax.add_patch(Polygon([(cx, cy + hh), (cx + hw, cy), (cx, cy - hh), (cx - hw, cy)],
                         closed=True, linewidth=1.6, edgecolor=ec, facecolor=fc))


def label(cx, cy, big, small, col):
    ax.text(cx, cy + 0.03, big, ha="center", va="center", fontsize=13, color=col)
    ax.text(cx, cy - 0.215, small, ha="center", va="center", fontsize=8.5, color=col, alpha=0.92)


def arw(x1, y1, x2, y2):
    ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle="-|>", color=LN, lw=1.6, shrinkA=0, shrinkB=0))


def line(pts):
    ax.plot([p[0] for p in pts], [p[1] for p in pts], color=LN, lw=1.6, zorder=0)


def dline(pts):
    ax.plot([p[0] for p in pts], [p[1] for p in pts], color=GE, lw=1.1,
            linestyle=(0, (4, 2)), zorder=0)


# ---- 各框 ----
term(2.3, 9.55, 1.4, 0.55, TERM_F, TERM_E, TERM_T)        # 开始
label(3.0, 9.825, "开始", "起止框 (圆角矩形)", TERM_T)
pbox(1.8, 8.6, 2.4, 0.6, IO_F, IO_E, IO_T)                 # 输入 n
label(3.0, 8.9, "输入 $n$", "输入, 输出框 (平行四边形)", IO_T)
proc(1.8, 7.5, 2.4, 0.6, PROC_F, PROC_E, PROC_T)           # S=0,i=1
label(3.0, 7.8, "$S=0,\\;i=1$", "处理框 (直角矩形)", PROC_T)
diam(3.0, 6.6, 1.2, 0.55, DIA_F, DIA_E, DIA_T)             # 判断 i<=n
label(3.0, 6.6, "$i\\leq n$ ?", "判断框 (菱形)", DIA_T)
proc(1.8, 4.8, 2.4, 0.6, PROC_F, PROC_E, PROC_T)           # S=S+i, i=i+1
label(3.0, 5.1, "$S=S+i,\\;i=i+1$", "处理框 (直角矩形)", PROC_T)
pbox(5.6, 6.3, 2.4, 0.6, IO_F, IO_E, IO_T)                 # 输出 S
label(6.8, 6.6, "输出 $S$", "输入, 输出框 (平行四边形)", IO_T)
term(6.0, 5.2, 1.6, 0.6, TERM_F, TERM_E, TERM_T)           # 结束
label(6.8, 5.5, "结束", "起止框 (圆角矩形)", TERM_T)

# 注释框 (虚线矩形)
ax.add_patch(Rectangle((0.5, 3.0), 3.2, 0.6, linewidth=1.2, edgecolor=GE,
                       facecolor=GF, linestyle=(0, (4, 2))))
ax.text(2.1, 3.415, "本图算法: 累加求 $S=1+2+\\cdots+n$", ha="center", va="center",
        fontsize=10, color=GT)
ax.text(2.1, 3.17, "注释框 (虚线矩形)", ha="center", va="center", fontsize=8.5, color=GT)

# ---- 顺序流程线 ----
arw(3.0, 9.55, 3.0, 9.20)    # 开始 -> 输入
arw(3.0, 8.60, 3.0, 8.10)    # 输入 -> S=0,i=1
arw(3.0, 7.50, 3.0, 7.15)    # S=0,i=1 -> 判断顶
arw(3.0, 6.05, 3.0, 5.40)    # 判断底(Y) -> 循环体
arw(4.20, 6.60, 5.60, 6.60)  # 判断右(N) -> 输出
arw(6.8, 6.30, 6.8, 5.83)    # 输出 -> 结束

# ---- 连接点 (成对, 标同一字母 A) ----
# 出口 A: 承接循环体底部的回边
ax.add_patch(Circle((1.55, 4.60), 0.16, facecolor="white", edgecolor=LN, lw=1.6, zorder=3))
ax.text(1.55, 4.60, "A", ha="center", va="center", fontsize=10.5, color=LN, zorder=4)
arw(3.0, 4.80, 1.62, 4.64)   # 循环体底 -> A(出口), 箭头指向圆圈
# 入口 A: 在判断框左侧把流程接回
ax.add_patch(Circle((1.55, 6.60), 0.16, facecolor="white", edgecolor=LN, lw=1.6, zorder=3))
ax.text(1.55, 6.60, "A", ha="center", va="center", fontsize=10.5, color=LN, zorder=4)
arw(1.62, 6.60, 1.80, 6.60)  # A(入口) -> 判断框左顶点, 箭头流出圆圈
# 两个 A 之间不画流程线 (靠相同字母表示相接)

ax.text(1.55, 4.22, "连接点 A (出口)", ha="center", va="top", fontsize=8.8, color=LN)
ax.text(1.55, 6.98, "连接点 A (入口)", ha="center", va="bottom", fontsize=8.8, color=LN)

# 注释框虚线箭头指向循环体
dline([(2.1, 3.60), (2.1, 4.70)])
ax.annotate("", xy=(2.1, 4.72), xytext=(2.1, 3.62),
            arrowprops=dict(arrowstyle="-|>", color=GE, lw=1.1,
                            linestyle=(0, (4, 2)), shrinkA=0, shrinkB=0))

ax.text(3.25, 5.30, "Y", ha="left", va="center", fontsize=11, color=LN)
ax.text(4.28, 6.82, "N", ha="left", va="bottom", fontsize=11, color=LN)

ax.text(4.5, 3.05, "注1: 起止框=圆角矩形(紫色), 处理框=直角矩形(蓝色); 判断框=菱形, 输入/输出框=平行四边形",
        ha="center", va="center", fontsize=9, color=GT)
ax.text(4.5, 2.78, "注2: 连接点成对出现且标同一字母 (此处 A—A), 表示两段流程在此相接, 中间不画流程线",
        ha="center", va="center", fontsize=9, color=GT)

ax.text(4.5, 10.30, "程序框图的七种图形符号 (示例: 累加求和)",
        ha="center", va="center", fontsize=14, color="#2C2C2A")

out = r"<vault>\images\程序框图七种符号示例_v2.png"
fig.savefig(out, bbox_inches="tight", facecolor="white")
plt.close(fig)
print("saved", out)
