from __future__ import annotations

import math
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.lines import Line2D
from matplotlib.patches import Circle, FancyArrowPatch, Rectangle


ROOT = Path(__file__).resolve().parents[1]
OUT = (
    ROOT
    / "reports_d44_dualpol_truefed_l_polarization_phase"
    / "plots"
    / "UWB_CH9_D44_DUALPOL_XY_polarization_anchor_plane_relationship.png"
)

COLORS = {
    "A": "#1f77b4",
    "B": "#2ca02c",
    "L": "#f28e2b",
    "look": "#545454",
    "theta": "#7f3c8d",
    "phi": "#d62728",
    "45": "#ff7f0e",
    "135": "#9467bd",
}


def configure_font() -> None:
    font_candidates = [
        Path(r"C:\Windows\Fonts\msyh.ttc"),
        Path(r"C:\Windows\Fonts\simhei.ttf"),
        Path(r"C:\Windows\Fonts\simsun.ttc"),
    ]
    for font_path in font_candidates:
        if font_path.exists():
            font_manager.fontManager.addfont(str(font_path))
            plt.rcParams["font.family"] = font_manager.FontProperties(fname=str(font_path)).get_name()
            break
    plt.rcParams["axes.unicode_minus"] = False
    plt.rcParams["figure.dpi"] = 150


def arrow(ax, start, end, color, text, text_offset=(0.0, 0.0), lw=3.0, style="-|>", fontsize=12):
    ax.add_patch(
        FancyArrowPatch(
            start,
            end,
            arrowstyle=style,
            mutation_scale=16,
            lw=lw,
            color=color,
            shrinkA=0,
            shrinkB=0,
        )
    )
    ax.text(
        end[0] + text_offset[0],
        end[1] + text_offset[1],
        text,
        color=color,
        fontsize=fontsize,
        fontweight="bold",
        ha="center",
        va="center",
    )


def draw_top_view(ax) -> None:
    board_r = 22.0
    elem_r = 17.0 / math.sqrt(2.0)
    patch_side = 6.0
    ax.add_patch(Circle((0, 0), board_r, facecolor="#f3f6f7", edgecolor="#44535c", lw=2.0, alpha=0.95))
    ax.add_patch(Circle((0, 0), 21.4, facecolor="none", edgecolor="#9aa6ac", lw=1.0, ls="--", alpha=0.8))
    ax.text(-20.8, -20.0, "锚点/PCB 平面：XY", fontsize=12, color="#34434a")
    ax.text(10.2, -20.0, "板边 L 单元", fontsize=11, color=COLORS["L"])

    for name, deg in [("E1", 0), ("E2", 90), ("E3", 180), ("E4", 270)]:
        x = elem_r * math.cos(math.radians(deg))
        y = elem_r * math.sin(math.radians(deg))
        ax.add_patch(
            Rectangle(
                (x - patch_side / 2, y - patch_side / 2),
                patch_side,
                patch_side,
                facecolor="#ffffff",
                edgecolor="#61717a",
                lw=1.4,
                zorder=4,
            )
        )
        ax.text(x, y, name, ha="center", va="center", fontsize=12, fontweight="bold", zorder=5)
        lx = (elem_r + 7.1) * math.cos(math.radians(deg))
        ly = (elem_r + 7.1) * math.sin(math.radians(deg))
        tx = -math.sin(math.radians(deg))
        ty = math.cos(math.radians(deg))
        ax.plot(
            [lx - 1.6 * tx, lx + 1.6 * tx],
            [ly - 1.6 * ty, ly + 1.6 * ty],
            color=COLORS["L"],
            lw=4.0,
            solid_capstyle="round",
            zorder=5,
        )
        ax.text(
            lx + 1.4 * math.cos(math.radians(deg)),
            ly + 1.4 * math.sin(math.radians(deg)),
            f"P{name[-1]}L",
            fontsize=9,
            color=COLORS["L"],
            ha="center",
            va="center",
        )

    arrow(ax, (-9.0, 0), (10.5, 0), COLORS["A"], "A = X 通道", (1.5, -1.5))
    arrow(ax, (0, -9.0), (0, 10.5), COLORS["B"], "B = Y 通道", (4.2, 0.4))
    ax.text(6.4, 1.4, "板固定 X 方向", color=COLORS["A"], fontsize=9)
    ax.text(1.0, 7.1, "板固定 Y 方向", color=COLORS["B"], fontsize=9)

    phi_deg = 35.0
    u = (math.cos(math.radians(phi_deg)), math.sin(math.radians(phi_deg)))
    t = (-math.sin(math.radians(phi_deg)), math.cos(math.radians(phi_deg)))
    look_len = 18.5
    arrow(ax, (0, 0), (look_len * u[0], look_len * u[1]), COLORS["look"], "入射/观测方位 φ", (1.0, 1.2), lw=2.2)
    origin = (8.5 * u[0], 8.5 * u[1])
    arrow(
        ax,
        (origin[0] - 4.2 * t[0], origin[1] - 4.2 * t[1]),
        (origin[0] + 4.2 * t[0], origin[1] + 4.2 * t[1]),
        COLORS["phi"],
        "Eφ：面内切向\n= 90°极化基",
        (2.2, 1.5),
        lw=2.4,
        style="<|-|>",
        fontsize=11,
    )
    ax.scatter([origin[0]], [origin[1]], s=92, color=COLORS["theta"], edgecolor="white", linewidth=1.2, zorder=8)
    ax.text(
        origin[0] - 2.0,
        origin[1] - 4.4,
        "Eθ：垂直图面\n≈ 板法向/Z\n= 0°极化基",
        color=COLORS["theta"],
        fontsize=10,
        ha="right",
        va="top",
    )

    arrow(ax, (-21.5, -24.5), (-14.0, -24.5), "#333333", "+X", (0.8, 0.0), lw=1.6)
    arrow(ax, (-21.5, -24.5), (-21.5, -17.0), "#333333", "+Y", (0.0, 0.8), lw=1.6)
    ax.text(-22.0, 23.7, "俯视图：A/B 是板固定 X/Y；Eφ 随方位 φ 旋转", fontsize=12, fontweight="bold", color="#222222")
    ax.set_aspect("equal")
    ax.set_xlim(-25, 25)
    ax.set_ylim(-26, 25)
    ax.axis("off")


def draw_side_view(side) -> None:
    side.set_title("侧视图：线极化角相对锚点平面的关系（θ≈90°低仰角）", fontsize=13, fontweight="bold")
    side.axhline(0, color="#52616b", lw=3, alpha=0.85)
    side.text(-4.9, -0.35, "锚点平面 / XY", fontsize=12, color="#34434a", va="top")
    side.add_patch(Rectangle((-5.0, -0.18), 10.0, 0.16, facecolor="#d9e2e7", edgecolor="none", alpha=0.9))
    arrow(side, (-4.5, 0.15), (-4.5, 2.0), "#333333", "+Z 法向", (-0.1, 0.22), lw=1.8)
    arrow(side, (-4.5, 0.15), (-2.7, 0.15), "#333333", "面内切向", (0.35, -0.35), lw=1.8)
    arrow(side, (-4.8, 1.55), (-1.8, 1.55), COLORS["look"], "水平/低仰角传播方向", (1.0, 0.1), lw=2.0)
    side.text(-4.75, 1.05, "远场线极化定义：E(α)=Eθ·cosα + Eφ·sinα", fontsize=11, color="#222222")

    origin = (0.8, 0.75)
    length = 2.25
    pols = [
        (0, COLORS["theta"], "0° = Eθ\n近似板法向"),
        (45, COLORS["45"], "45°"),
        (90, COLORS["phi"], "90° = Eφ\n位于锚点平面"),
        (135, COLORS["135"], "135°"),
    ]
    for alpha, color, label in pols:
        x = math.sin(math.radians(alpha))
        z = math.cos(math.radians(alpha))
        side.plot(
            [origin[0] - length * x, origin[0] + length * x],
            [origin[1] - length * z, origin[1] + length * z],
            color=color,
            lw=3.0,
            solid_capstyle="round",
        )
        side.text(
            origin[0] + (length + 0.35) * x,
            origin[1] + (length + 0.35) * z,
            label,
            color=color,
            fontsize=11,
            fontweight="bold",
            ha="center",
            va="center",
        )
    side.scatter([origin[0]], [origin[1]], s=52, color="#222222", zorder=5)
    side.text(origin[0] - 0.15, origin[1] - 0.35, "同一观测方向的\n极化切平面", fontsize=10, ha="right", va="top")

    note = (
        "读图要点\n"
        "1. A/B 是锚点板固定坐标：A=X，B=Y。\n"
        "2. 0/45/90/135° 是入射线极化角，基于局部 Eθ/Eφ。\n"
        "3. 在水平面附近，0°更接近板法向，90°在板面内；\n"
        "   因而不同极化不会天然与 A/B 曲线重合，需要 LUT/矢量标定。\n"
        "4. L 端口是独立板边低仰角覆盖单元，不是 A/B 的另一种极化。"
    )
    side.text(
        -4.9,
        -2.35,
        note,
        fontsize=10.5,
        va="top",
        ha="left",
        bbox=dict(boxstyle="round,pad=0.55", facecolor="#ffffff", edgecolor="#b8c2c8", alpha=0.96),
    )

    legend_handles = [
        Line2D([0], [0], color=COLORS["A"], lw=3, label="A / X 板固定通道"),
        Line2D([0], [0], color=COLORS["B"], lw=3, label="B / Y 板固定通道"),
        Line2D([0], [0], color=COLORS["theta"], lw=3, label="0° 极化基 Eθ"),
        Line2D([0], [0], color=COLORS["phi"], lw=3, label="90° 极化基 Eφ"),
        Line2D([0], [0], color=COLORS["L"], lw=4, label="L 板边低仰角单元"),
    ]
    side.legend(handles=legend_handles, loc="upper right", frameon=True, fontsize=10)
    side.set_xlim(-5.2, 5.2)
    side.set_ylim(-2.75, 3.3)
    side.set_aspect("equal", adjustable="box")
    side.axis("off")


def main() -> None:
    configure_font()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    fig = plt.figure(figsize=(15.5, 8.8), constrained_layout=True)
    grid = fig.add_gridspec(1, 2, width_ratios=[1.1, 1.0])
    ax = fig.add_subplot(grid[0, 0])
    side = fig.add_subplot(grid[0, 1])
    fig.suptitle("D44 当前锚点平面与不同极化方向的相对关系", fontsize=18, fontweight="bold")
    draw_top_view(ax)
    draw_side_view(side)
    fig.savefig(OUT, dpi=220, bbox_inches="tight")
    print(OUT)


if __name__ == "__main__":
    main()
