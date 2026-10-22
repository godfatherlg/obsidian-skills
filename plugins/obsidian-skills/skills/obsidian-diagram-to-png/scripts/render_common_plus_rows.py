# -*- coding: utf-8 -*-
"""render_common_plus_rows.py — 「共同带 + N 题行」横向对照图（固化模板，可复用）。

用法
----
  python render_common_plus_rows.py                 # 用底部 DATA 默认出图
  python render_common_plus_rows.py --out=路径.png   # 指定输出（不覆盖已交付图时用）

适用场景
--------
  同一个题族的 N 道题，**先共用一段内核、再各自补独有项**时的横向对照。
  典型：教资科二「影响因素类」微观族（学习迁移 / 性格·人格·品德 / 影响人身心发展的因素），
  也可用于「依据类」等任何"公共条 + 各自独有"的题族。

版式
----
  标题 / 副标题
  ┌ 共同带 ───────────────────────────────┐   列出三题共用的若干条
  ┌ 题 1 ────────────────────────────────┐   一行一题：
  │ 内部（蓝，学生自身） │ 外部（琥珀，环境与他人）│   左右两栏 = 该题独有的内 / 外部项
  ┌ 题 2 …                                 ┐
  ┌ 底部判据条 ───────────────────────────┐   记忆判据 + 视频提示（可选多行）

换内容只改底部 DATA：
  title / subtitle            大标题、副标题
  common_title                共同带的小标题
  common_lines                共同带的条目（每行一条，写短句，不自动折行）
                              条目可写 (前段, 后段) 元组：前段正文色、后段强调色
                              （用于行内标出新增/加料的共用条，如「身心发展的规律与需要」）
  common_extra                共同带最后一条（用强调色渲染，可 None）
  rows                        [dict(name=, chip=, inner=, outer=), …]
                              chip = 右上角口诀标签（"无口诀 · 现编" 之类会用灰色渲染）
                              inner / outer 自动按栏宽折行
  bar                         [(文字, 字号, 颜色), …] 底部判据条
  out                         输出路径

排版要点（改内容/字号时注意）
  - 数据坐标固定 0-100 × 0-100，`fig.subplots_adjust(0,0,1,1)` 让 axes 铺满 figure
    ⇒ 1 x 单位 = FIG_W*72/100 pt（本模板 13.6in → 9.792pt），折行容量按此换算；
    **别删那句 subplots_adjust**，否则每单位 pt 变小、折行算大一截，文字会跨栏溢出。
  - 各段高度由内容长度自动算（共同带按条数、题行按折行行数、判据条按行数），
    剩余空间平均摊进各段间隙，所以整幅总是填到底。
  - 字体 C:\\Windows\\Fonts\\simhei.ttf（SimHei）；无粗体属正常（matplotlib 回退 400）。
"""
import sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
import matplotlib.font_manager as fm

FONT = r"C:\Windows\Fonts\simhei.ttf"
fm.fontManager.addfont(FONT)
plt.rcParams["font.family"] = "SimHei"
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["mathtext.fontset"] = "dejavusans"

C_TEXT = "#1F2933"
C_EDGE = "#8A94A6"
C_NOTE = "#52606D"
C_SLOGAN = "#C0392B"
C_ACCENT = "#B45309"
C_COM_F, C_COM_E = "#F1F6FC", "#7FA8D4"    # 共同带：淡蓝
C_IN_F, C_IN_E = "#EAF3FB", "#6FA3CE"      # 内部：蓝
C_OUT_F, C_OUT_E = "#FDF4E6", "#D9A55A"    # 外部：琥珀
C_BAR_F, C_BAR_E = "#F2F4F7", "#8A94A6"    # 判据条

FIG_W, FIG_H, DPI = 13.6, 9.2, 230
PT_PER_XUNIT = FIG_W * 72.0 / 100.0        # 1 x 单位 = 9.792pt
TOP, BOTTOM = 99.0, 2.5
X0, X1 = 2.0, 98.0                         # 外框
LINE_STEP = 3.7                            # 共同带行距（y 单位）
INNER_STEP = 2.9                           # 题行内文字行距
BAR_STEP = 4.1                             # 判据条行距
BODY_PT = 11.2                             # 共同带正文字号
CELL_PT = 10.4                             # 题行内正文字号

_SCRATCH = {"ax": None}


def _vlen(s):
    return sum(0.55 if ord(ch) < 128 else 1.0 for ch in s)


def _wrap(text, width_units, size):
    """按栏宽折行：全角 1.0 / 半角 0.55 折算。"""
    cap = max(6.0, width_units * PT_PER_XUNIT / size * 0.97)
    out, cur, w = [], "", 0.0
    for ch in text:
        cw = 0.55 if ord(ch) < 128 else 1.0
        if cur and w + cw > cap:
            out.append(cur)
            cur, w = "", 0.0
        cur += ch
        w += cw
    if cur:
        out.append(cur)
    return out


def _box(ax, x, y, w, h, fc, ec, lw=1.2, rs=1.0):
    ax.add_patch(FancyBboxPatch((x, y), w, h,
                                boxstyle="round,pad=0,rounding_size=%.2f" % rs,
                                facecolor=fc, edgecolor=ec, linewidth=lw))


def _txt(ax, x, y, s, size=11, color=C_TEXT, ha="left", va="top"):
    ax.text(x, y, s, fontsize=size, color=color, ha=ha, va=va, linespacing=1.55)


def render(title, subtitle, common_title, common_lines, rows, bar,
           common_extra=None, out=None, figsize=(FIG_W, FIG_H)):
    assert rows, "rows 不能为空"
    fig, ax = plt.subplots(figsize=figsize, dpi=DPI)
    fig.subplots_adjust(left=0, right=1, bottom=0, top=1)
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis("off")

    # ---- 各段高度（按内容算）----
    n_common = len(common_lines) + (1 if common_extra else 0)
    common_h = 7.0 + LINE_STEP * (n_common - 1) + 5.0
    col_w = (X1 - X0) / 2.0 - 2.8                 # 单栏可用宽度
    inner_w = col_w - 2.4
    row_texts = []
    for r in rows:
        li = _wrap(r["inner"], inner_w, CELL_PT)
        lo = _wrap(r["outer"], inner_w, CELL_PT)
        row_texts.append((li, lo))
    row_hs = [13.2 + INNER_STEP * (max(len(li), len(lo)) - 1) for li, lo in row_texts]
    bar_h = 2.5 + BAR_STEP * (len(bar) - 1) + 3.6

    blocks = [7.6, common_h] + row_hs + [bar_h]
    ngap = len(blocks) - 1
    used = sum(blocks)
    avail = TOP - BOTTOM
    gap = (avail - used) / ngap if ngap > 0 else 0
    assert gap >= 1.0, "内容太多，画布放不下：把行写短或调大 figsize"

    # ---- 标题 ----
    y = TOP
    _txt(ax, 50, y - 2.4, title, 19, C_TEXT, "center", "center")
    _txt(ax, 50, y - 5.4, subtitle, 11.5, C_NOTE, "center", "center")
    y -= blocks[0] + gap

    # ---- 共同带 ----
    ct, cb = y, y - common_h
    _box(ax, X0, cb, X1 - X0, common_h, C_COM_F, C_COM_E, 1.4)
    _txt(ax, X0 + 2.2, ct - 2.7, common_title, 13, "#1D4E89", "left", "top")
    yy = ct - 7.0
    for line in common_lines:
        if isinstance(line, tuple):
            head, tail = line
            _txt(ax, X0 + 2.2, yy, head, BODY_PT, C_TEXT, "left", "top")
            hw = _vlen(head) * BODY_PT / PT_PER_XUNIT
            _txt(ax, X0 + 2.2 + hw, yy, tail, BODY_PT, C_ACCENT, "left", "top")
        else:
            _txt(ax, X0 + 2.2, yy, line, BODY_PT, C_TEXT, "left", "top")
        yy -= LINE_STEP
    if common_extra:
        _txt(ax, X0 + 2.2, yy + 0.1, common_extra, BODY_PT, C_ACCENT, "left", "top")
    y -= common_h + gap

    # ---- 三题行 ----
    mid = (X0 + X1) / 2.0
    for i, (r, (li, lo), rh) in enumerate(zip(rows, row_texts, row_hs)):
        rt, rb = y, y - rh
        _box(ax, X0, rb, X1 - X0, rh, "#FFFFFF", C_EDGE, 1.3)
        _txt(ax, X0 + 2.2, rt - 2.0, r["name"], 12.6, C_TEXT, "left", "top")
        chip = r.get("chip", "")
        if chip:
            cc = C_SLOGAN if "无口诀" not in chip else C_NOTE
            _txt(ax, X1 - 2.2, rt - 2.2, chip, 11.6, cc, "right", "top")
        iy, ih = rb + 1.5, rh - 5.7
        _box(ax, X0 + 2.0, iy, col_w, ih, C_IN_F, C_IN_E, 1.1)
        _box(ax, mid + 1.4, iy, col_w, ih, C_OUT_F, C_OUT_E, 1.1)
        for bx, lab, labc, lines in ((X0 + 3.2, "内部", C_IN_E, li),
                                     (mid + 2.6, "外部", C_OUT_E, lo)):
            _txt(ax, bx, iy + ih - 1.0, lab, 11.0, labc, "left", "top")
            ty = iy + ih - 4.6
            for ln in lines:
                _txt(ax, bx, ty, ln, CELL_PT, C_TEXT, "left", "top")
                ty -= INNER_STEP
        y -= rh + gap

    # ---- 底部判据条 ----
    bt, bb = y, y - bar_h
    _box(ax, X0, bb, X1 - X0, bar_h, C_BAR_F, C_BAR_E, 1.3)
    yy = bt - 2.5
    for s, size, col in bar:
        _txt(ax, X0 + 2.2, yy, s, size, col, "left", "top")
        yy -= BAR_STEP

    if out is None:
        out = r"<vault>\images\共同带加N行对照.png"
    fig.savefig(out, dpi=DPI, bbox_inches="tight", facecolor="white", pad_inches=0.18)
    print("saved:", out, "| %d 题行" % len(rows))


# ============================ DATA：改这里换内容 ============================
# 默认示例 = 科二「因素题 · 与学生有关三题对照」
# 交付文件：<vault>\images\因素题-三题内部外部对照.png
def _demo_data():
    return dict(
        title="因素题 · 与学生有关三题对照",
        subtitle="内部（蓝）＝ 学生自身   外部（琥珀）＝ 环境与他人",
        common_title="三题共同（先写这两组，三题都通用）",
        common_lines=[
            "① 都按「内部（学生自身）/ 外部（环境与他人）」两角度分条作答，各写 4-5 条即可",
            ("② 内部共用条：智力水平高低 · 学生主观能动性 · 年龄大小 · ", "身心发展的规律与需要"),
            "③ 外部共用条：教师（学校）的教育教学方式 · 家庭的教养方式与家庭氛围 · 同伴影响",
        ],
        rows=[
            dict(name="学习迁移的影响因素", chip="无口诀 · 现编",
                 inner="知识经验情况 · 思维定势（心向）",
                 outer="学习材料的相似性"),
            dict(name="性格／人格／品德形成的影响因素", chip="无口诀 · 现编",
                 inner="生理遗传因素 · 自我调控能力 · 认知风格",
                 outer="外界环境影响"),
            dict(name="影响人身心发展的因素", chip="意境观学",
                 inner="遗传＝生理前提、物质基础 · 个体主观能动性＝动力与决定性因素",
                 outer="环境＝现实基础，提供多种可能 · 学校教育＝主导作用"),
        ],
        bar=[
            ("判据：三题都先按内部 / 外部两条线分条，再按题干落点挑独有条", 12.0, C_TEXT),
            ("前两题没口诀可现编 —— 公共七条先写，再补各自独有；第三题是固定四因素，必须按口诀背", 11.0, C_TEXT),
            ("视频提示：气质主要受遗传影响，写进性格题不合适；个人基础知识与技能更适合学习迁移题，写上也不扣分", 10.6, C_NOTE),
        ],
        figsize=(13.6, 8.8),
        out=r"<vault>\images\因素题-三题内部外部对照.png",
    )


if __name__ == "__main__":
    kw = _demo_data()
    argv = sys.argv[1:]
    for i, a in enumerate(argv):
        if a.startswith("--out="):
            kw["out"] = a.split("=", 1)[1]
        elif a == "--out" and i + 1 < len(argv):
            kw["out"] = argv[i + 1]
    render(**kw)
