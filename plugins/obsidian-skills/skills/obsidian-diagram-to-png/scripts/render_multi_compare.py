# -*- coding: utf-8 -*-
"""render_multi_compare.py — 多张卡横向对比表（固化模板，可复用）。

用法
----
  python render_multi_compare.py                  # 用底部 DATA 默认出图
  python render_multi_compare.py --out=路径.png    # 指定输出（不覆盖已交付图时用）
  python render_multi_compare.py --out 路径.png    # 同上（两种写法都认）

适用场景
--------
  用户 suspend 了 N 张卡、想做成一张「多行对比表」横向记忆：
  一行 = 一张卡，一列 = 一个对比维度（如 原则名 / 核心定义 / 识别标志 / 基本要求）。
  典型：四大教学原则对比、几个易混概念辨析、几个公式/定理横向对照。

换内容只需改底部 DATA 区块（每个单元格直接写一整句，**不用自己换行**，脚本按列宽自动折行）：
  title       表格大标题
  headers     列标题列表（顺序 = 列顺序）
  rows        每行的单元格列表（一整个字符串即可，会自动按列宽折行）
  col_widths  各列宽度，**之和必须 = 96**（画布左边距 2、右边距 2，外边框留 2）
  col_colors  各列底色（不填默认：首列淡蓝 + 其余淡白）
  col_aligns  各列对齐（不填默认：首列居中 + 其余左对齐）
  col_red_first_line  哪些列要"红色口诀"效果（该列每格**第一行**用红色，其余正常）
  out         输出路径（默认 <vault>\\images\\多卡对比.png）

**行高内容驱动（2026-10-02 作图铁律，已是默认行为，不需要手算高度）**：
  每行高度 = 该行最大折行数 × LINE_PT + PAD_PT；纵向量全以 pt 设计再换算成 y 单位
  ⇒ 行距与画布高度解耦；figsize 高度按内容自动算（只吃宽度），短表自然扁、长表自然高。
  ⚠️ 别再传 figsize 高度来"压扁"，那会拉伸行距；也别改回"总高/行数"统一行高。
  运行时 stdout 打印 `每行行数 [...] ｜ 行高pt [...]`，先看它再回读 PNG。

字体 C:\\Windows\\Fonts\\simhei.ttf（SimHei）；无粗体属正常（matplotlib 回退 400）。
"""
import sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import matplotlib.font_manager as fm

FONT = r"C:\Windows\Fonts\simhei.ttf"
fm.fontManager.addfont(FONT)
plt.rcParams["font.family"] = "SimHei"
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["mathtext.fontset"] = "dejavusans"

C_EDGE = "#8A94A6"
C_HEAD = "#E7EDF5"
C_TEXT = "#1F2933"
C_SLOGAN = "#C0392B"

# 画布：axes 用 subplots_adjust 铺满整张 figure ⇒ 100 x 单位 = 13.6in = 979.2pt
# ⇒ 1 x 单位 = 9.792pt。一个全角字宽 ≈ 字号 F(pt)。
# 每列每行可容纳的全角字数 ≈ (列宽 - 2.6 内边距) * 9.792 / F，再乘安全系数。
PT_PER_UNIT = 9.792
FONT_PT = 10.3          # 正文/口诀的平均字号
WRAP_SAFETY = 0.97
COL_PAD = 2.6           # 每列左右内边距（x0+1.3 起排，右边留 1.3）

# 纵向尺寸全部以 pt 设计、再换算成 y 单位 ⇒ 行距与画布高度解耦（2026-10-02 作图铁律）
LINE_PT = 17.0          # 每行文字占的纵向高度
PAD_PT = 9.0            # 每格上下内边距合计
TITLE_PT = 30.0         # 画布顶部留给大标题的高度
BOTTOM_PT = 6.0         # 画布底部余量


def _visual_len(s):
    """按显示宽度估算串长：全角 1.0、半角 0.55。"""
    return sum(0.55 if ord(ch) < 128 else 1.0 for ch in s)


def _wrap_text(text, max_units):
    """把一段文字按 max_units（全角字数）折行；已有的 \\n 当作硬换行。"""
    out = []
    for raw in str(text).split("\n"):
        if _visual_len(raw) <= max_units:
            out.append(raw)
            continue
        cur, w = "", 0.0
        for ch in raw:
            cw = 0.55 if ord(ch) < 128 else 1.0
            if cur and w + cw > max_units:
                out.append(cur)
                cur, w = "", 0.0
            cur += ch
            w += cw
        if cur:
            out.append(cur)
    return "\n".join(out)


def render(title, headers, rows, col_widths, col_colors=None, col_aligns=None,
           col_red_first_line=(), out=None, figsize=(13.6, None), header_h_pt=26.0,
           title_fs=18):
    """figsize 只吃宽度、高度传 None = 按内容自动算（2026-10-02 作图铁律：内容驱动）。"""
    ncol = len(headers)
    nrow = len(rows)
    assert ncol >= 1 and nrow >= 1, "headers 与 rows 不能为空"
    assert abs(sum(col_widths) - 96) < 1e-6, "col_widths 之和必须 = 96（画布内边距各留 2）"
    if col_colors is None:
        col_colors = ["#D6E6F7"] + ["#F7FAFD"] * (ncol - 1)
    assert len(col_colors) == ncol, "col_colors 长度要与列数一致"
    if col_aligns is None:
        col_aligns = ["center"] + ["left"] * (ncol - 1)
    assert len(col_aligns) == ncol, "col_aligns 长度要与列数一致"
    red_set = set(col_red_first_line)

    # 列坐标（从 x=2 起，累计宽度）与各列折行容量（x 方向：figsize 宽固定 13.6in）
    cols = []
    caps = []
    x = 2.0
    for w in col_widths:
        cols.append((x, x + w))
        caps.append(max(4.0, (w - COL_PAD) * PT_PER_UNIT / FONT_PT * WRAP_SAFETY))
        x += w

    # 预先折行 + 按每行实际行数算高度（内容驱动，禁 uniform 撑满）
    wrapped = [[_wrap_text(row[j] if j < len(row) else "", caps[j]) for j in range(ncol)]
               for row in rows]
    row_lines = [max(1, max(c.count("\n") + 1 for c in wr)) for wr in wrapped]

    # 全部纵向尺寸先用 pt 设计，再一次性换算成 y 数据单位 ⇒ 行距与 figsize 高度无关，永不重叠
    body_pt = sum(n * LINE_PT + PAD_PT for n in row_lines)
    total_pt = TITLE_PT + header_h_pt + body_pt + BOTTOM_PT
    pt_per_unit = total_pt / 100.0            # 1 y 单位 = 画布高的 1% 
    fig_h = total_pt / 72.0                  # 内容刚好铺满整张图：无底部空白
    fig_w = figsize[0]
    fig, ax = plt.subplots(figsize=(fig_w, fig_h), dpi=230)
    fig.subplots_adjust(left=0, right=1, bottom=0, top=1)
    ax.set_xlim(0, 100)
    ax.axis("off")

    top = 100.0 - TITLE_PT / pt_per_unit        # 顶部标题区独占 TITLE_PT，表头不得越界
    header_h = header_h_pt / pt_per_unit
    header_bot = top - header_h
    row_heights = [(n * LINE_PT + PAD_PT) / pt_per_unit for n in row_lines]

    ax.text(50, 100 - (TITLE_PT * 0.52) / pt_per_unit, title, ha="center", va="center",
            fontsize=title_fs, color=C_TEXT)

    # 表头
    for (x0, x1), h in zip(cols, headers):
        ax.add_patch(Rectangle((x0, header_bot), x1 - x0, header_h,
                               facecolor=C_HEAD, edgecolor=C_EDGE, lw=1.1))
        ax.text((x0 + x1) / 2, header_bot + header_h / 2, h,
                ha="center", va="center", fontsize=12, color=C_TEXT)

    # 行（逐行按实际行数给高；文字纵向偏移一律把 pt 换算成 y 单位）
    y_cursor = header_bot
    pad_top = 5.0 / pt_per_unit
    line_gap = LINE_PT * 0.95 / pt_per_unit
    for i, wr in enumerate(wrapped):
        row_h = row_heights[i]
        y_top = y_cursor
        y_bot = y_top - row_h
        y_mid = (y_top + y_bot) / 2
        y_cursor = y_bot
        for j, (x0, x1) in enumerate(cols):
            ax.add_patch(Rectangle((x0, y_bot), x1 - x0, row_h,
                                   facecolor=col_colors[j], edgecolor=C_EDGE, lw=1.0))
            cell = wr[j]
            if col_aligns[j] == "center":
                ax.text((x0 + x1) / 2, y_mid, cell, ha="center", va="center",
                        fontsize=11.5, color=C_TEXT, linespacing=1.5)
            elif j in red_set:
                parts = cell.split("\n", 1)
                ax.text(x0 + 1.3, y_top - pad_top, parts[0], ha="left", va="top",
                        fontsize=10.6, color=C_SLOGAN, linespacing=1.5)
                if len(parts) > 1:
                    ax.text(x0 + 1.3, y_top - pad_top - line_gap, parts[1], ha="left",
                            va="top", fontsize=10.2, color=C_TEXT, linespacing=1.5)
            else:
                ax.text(x0 + 1.3, y_top - pad_top, cell, ha="left", va="top",
                        fontsize=10.2, color=C_TEXT, linespacing=1.5)

    bottom = y_cursor
    ax.set_ylim(bottom, 100)
    ax.add_patch(Rectangle((2, bottom), 96, top - bottom, facecolor="none",
                           edgecolor=C_EDGE, lw=1.8))
    if out is None:
        out = r"<vault>\images\多卡对比.png"
    fig.savefig(out, dpi=230, bbox_inches="tight", facecolor="white", pad_inches=0.14)
    print("saved: %s | %d 行 × %d 列 | 画布 %.1f×%.1f in" % (out, nrow, ncol, fig_w, fig_h))
    print("        每行行数 %s ｜ 行高pt %s" % (
        row_lines, [round(h * pt_per_unit, 1) for h in row_heights]))


# ============================ DATA：改这里换内容 ============================
# 示例 = 四大教学原则对比（实际交付文件：<vault>\images\四大教学原则-对比记忆.png）
def _demo_data():
    headers = ["原则", "核心定义", "识别标志", "基本要求 (口诀 + 要点)"]
    col_widths = [15, 31, 20, 30]          # 之和 = 96
    col_colors = ["#D6E6F7", "#F7FAFD", "#FBF7EF", "#F5FAF2"]
    col_aligns = ["center", "left", "left", "left"]
    col_red_first_line = (3,)             # 第 4 列第一行当红色口诀
    rows = [
        ["启发性\n原则",
         "依据学习过程的客观规律, 运用各种教学手段充分调动学生的主动性、积极性",
         "课堂上有问有答, 引导学生思考回答; 方法上对应谈话法",
         "口诀: 事实民主\n① 调动学生的主动性\n② 启发学生独立思考\n③ 让学生动手实践\n④ 发扬教学民主"],
        ["系统性\n(循序渐进)\n原则",
         "严格按科学知识的内在逻辑体系 + 学生认识能力发展的顺序教学, 系统掌握双基(基础知识与基本技能)",
         "「循序」的序含两方面: ① 知识的逻辑顺序 ② 学生身心发展的顺序",
         "口诀: 按照系统的矛盾顺序教学\n① 教师的教学要有系统性\n② 抓主要矛盾, 解决重点与难点\n③ 按认识顺序: 由浅入深、由易到难、由简到繁"],
        ["巩固性\n原则",
         "在理解的基础上, 牢固地掌握基础知识与基本技能",
         "讲完新知识让学生复习巩固、布置作业; 讲新课前复习旧知识",
         "口诀: 全程复习, 练习记忆\n① 教学全过程中加强知识巩固\n② 组织学生的复习工作\n③ 教会学生记忆的方法\n④ 通过练习、运用来巩固"],
        ["理论联系\n实际原则",
         "以学习基础知识为主导, 引导学生从理论与实际的联系上理解知识, 学会运用知识分析和解决问题, 达到学以致用",
         "讲新知识时联系生活实际例子帮助理解; 把学过的方法运用到实际生活中解决问题",
         "口诀: 补充运用实际知识和技能\n① 书本知识教学注重联系实际\n② 因地制宜补充乡土教材、开发校本课程\n③ 重视培养学生运用知识的能力\n④ 正确处理知识教学与技能训练的关系"],
    ]
    return dict(title="四大教学原则 · 对比记忆", headers=headers, rows=rows,
                col_widths=col_widths, col_colors=col_colors,
                col_aligns=col_aligns, col_red_first_line=col_red_first_line,
                out=r"<vault>\images\四大教学原则-对比记忆.png")


if __name__ == "__main__":
    kw = _demo_data()
    argv = sys.argv[1:]
    for i, a in enumerate(argv):
        if a.startswith("--out="):
            kw["out"] = a.split("=", 1)[1]
        elif a == "--out" and i + 1 < len(argv):
            kw["out"] = argv[i + 1]
    render(**kw)
