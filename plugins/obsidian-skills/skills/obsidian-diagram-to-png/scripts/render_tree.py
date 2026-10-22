import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import os
import sys


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
IMG_DIR = r"<vault>\images"
FONT_PATH = r"C:\Windows\Fonts\simhei.ttf"

fm.fontManager.addfont(FONT_PATH)
plt.rcParams["font.family"] = "SimHei"
plt.rcParams["axes.unicode_minus"] = False


def draw_tree(nodes, edges, outpath, title=""):
    """
    Draw a simple directed tree and save as PNG.

    nodes: list of dicts {"id": str, "label": str, "x": float, "y": float,
                          "hl": bool (optional)}
    edges: list of dicts {"s": str, "d": str, "lab": str,
                          "hl": bool (optional)}
    outpath: absolute PNG output path
    title: optional title displayed at the top
    """
    os.makedirs(os.path.dirname(outpath), exist_ok=True)
    fig, ax = plt.subplots(figsize=(7.2, 4.6), dpi=420)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    pos = {n["id"]: (n["x"], n["y"]) for n in nodes}

    for e in edges:
        s, d, lab = e["s"], e["d"], e["lab"]
        xs, ys = pos[s]
        xd, yd = pos[d]
        hl = e.get("hl", False)
        col = "#A32D2D" if hl else "#555555"
        ax.annotate(
            "", xy=(xd, yd), xytext=(xs, ys),
            arrowprops=dict(arrowstyle="-|>", color=col, lw=1.4 if hl else 1.0),
        )
        mx, my = (xs + xd) / 2, (ys + yd) / 2
        ax.text(mx, my + 0.015, lab, ha="center", va="bottom",
                fontsize=9, color=col,
                fontweight="bold" if hl else "normal")

    for n in nodes:
        x, y = n["x"], n["y"]
        hl = n.get("hl", False)
        fc = "#FCEBEB" if hl else "#EAF1FB"
        ec = "#A32D2D" if hl else "#3A6EA5"
        ax.annotate(
            n["label"], xy=(x, y), ha="center", va="center",
            fontsize=9.5, fontweight="bold" if hl else "normal",
            bbox=dict(boxstyle="round,pad=0.35", fc=fc, ec=ec, lw=1.2),
        )

    if title:
        ax.text(0.5, 0.97, title, ha="center", va="top",
                fontsize=11, fontweight="bold")

    fig.savefig(outpath, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print("saved", outpath)


if __name__ == "__main__":
    # Example: 甲乙食堂 probability tree
    nodes = [
        {"id": "S", "label": "第一天", "x": 0.08, "y": 0.5},
        {"id": "A", "label": "甲", "x": 0.40, "y": 0.78},
        {"id": "B", "label": "乙", "x": 0.40, "y": 0.22},
        {"id": "A2", "label": "第二天乙", "x": 0.86, "y": 0.92, "hl": True},
        {"id": "A1", "label": "第二天甲", "x": 0.86, "y": 0.64},
        {"id": "B1", "label": "第二天甲", "x": 0.86, "y": 0.36},
        {"id": "B2", "label": "第二天乙", "x": 0.86, "y": 0.08, "hl": True},
    ]
    edges = [
        {"s": "S", "d": "A", "lab": "0.5"},
        {"s": "S", "d": "B", "lab": "0.5"},
        {"s": "A", "d": "A2", "lab": "0.8", "hl": True},
        {"s": "A", "d": "A1", "lab": "0.2"},
        {"s": "B", "d": "B1", "lab": "0.6"},
        {"s": "B", "d": "B2", "lab": "0.4", "hl": True},
    ]
    draw_tree(nodes, edges,
              os.path.join(IMG_DIR, "概率树-甲乙食堂.png"),
              "概率树: 甲乙食堂(红框=第二天去乙)")
