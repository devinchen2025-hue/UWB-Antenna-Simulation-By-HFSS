from __future__ import annotations

import csv
import math
from dataclasses import dataclass
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib import font_manager


ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = ROOT / "reports_d44_pdoa_linear"
CURVES_CSV = REPORT_DIR / "UWB_CH9_D44_PDOA_linear_polarization_curves.csv"
PLOTS_DIR = REPORT_DIR / "plots"
MANIFEST_MD = PLOTS_DIR / "UWB_CH9_D44_PDOA_linear_polarization_plot_manifest.md"

POLARIZATIONS = [0.0, 45.0, 90.0, 135.0]
COLORS = {
    0.0: "#1f77b4",
    45.0: "#d62728",
    90.0: "#2ca02c",
    135.0: "#9467bd",
}


@dataclass(frozen=True)
class PlotCase:
    key: str
    title: str
    freq_ghz: float
    phi_deg: float
    channel_set: str
    baseline: str
    note: str


PLOT_CASES = [
    PlotCase(
        key="center_best_a_feed_e1_e3_phi90",
        title="中心频点 A 馈 E1-E3 基线",
        freq_ghz=7.9855,
        phi_deg=90.0,
        channel_set="A_feed_only",
        baseline="E1-E3",
        note="上一轮汇总中单调性最好的中心频点候选之一，用于观察理想较优基线下的极化偏移。",
    ),
    PlotCase(
        key="center_dualfeed_e1_e3_phi75",
        title="中心频点 双馈合成 E1-E3 基线",
        freq_ghz=7.9855,
        phi_deg=75.0,
        channel_set="dualfeed_quadrature_minus90",
        baseline="E1-E3",
        note="采用 A+B*exp(-j90deg) 双馈合成通道，展示接近当前 CP 使用方式下的鉴角曲线变化。",
    ),
    PlotCase(
        key="worst_sensitive_b_feed_e1_e2_phi45",
        title="低频点 B 馈 E1-E2 敏感基线",
        freq_ghz=7.738,
        phi_deg=45.0,
        channel_set="B_feed_only",
        baseline="E1-E2",
        note="上一轮指标中最大偏移接近 180 deg 的敏感案例，用于展示极化方向造成的最坏相位偏置。",
    ),
]


def configure_font() -> None:
    available = {font.name for font in font_manager.fontManager.ttflist}
    for candidate in ["Microsoft YaHei", "SimHei", "SimSun", "Arial Unicode MS"]:
        if candidate in available:
            plt.rcParams["font.sans-serif"] = [candidate, "DejaVu Sans"]
            break
    plt.rcParams["axes.unicode_minus"] = False


def nearly_equal(left: float, right: float, tol: float = 1e-6) -> bool:
    return abs(left - right) <= tol


def wrap_deg(value: float) -> float:
    return (value + 180.0) % 360.0 - 180.0


def read_rows() -> list[dict]:
    rows = []
    with CURVES_CSV.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for item in reader:
            rows.append(
                {
                    "freq_ghz": float(item["freq_ghz"]),
                    "phi_deg": float(item["phi_deg"]),
                    "theta_deg": float(item["theta_deg"]),
                    "linear_pol_deg": float(item["linear_pol_deg"]),
                    "channel_set": item["channel_set"],
                    "baseline": item["baseline"],
                    "pdoa_deg": float(item["pdoa_deg"]),
                    "pdoa_unwrapped_deg": float(item["pdoa_unwrapped_deg"]),
                    "left_mag_rel_db": float(item["left_mag_rel_db"]),
                    "right_mag_rel_db": float(item["right_mag_rel_db"]),
                    "valid": item["valid"].strip().lower() == "true",
                }
            )
    return rows


def select_curve(rows: list[dict], case: PlotCase, pol: float) -> list[dict]:
    curve = [
        row
        for row in rows
        if nearly_equal(row["freq_ghz"], case.freq_ghz)
        and nearly_equal(row["phi_deg"], case.phi_deg)
        and nearly_equal(row["linear_pol_deg"], pol)
        and row["channel_set"] == case.channel_set
        and row["baseline"] == case.baseline
    ]
    return sorted(curve, key=lambda row: row["theta_deg"])


def bias_against_reference(curve: list[dict], reference: dict[float, float]) -> list[float]:
    values = []
    for row in curve:
        if not row["valid"]:
            values.append(math.nan)
            continue
        ref = reference.get(row["theta_deg"])
        values.append(wrap_deg(row["pdoa_deg"] - ref) if ref is not None else math.nan)
    return values


def valid_series(curve: list[dict], key: str) -> list[float]:
    return [row[key] if row["valid"] else math.nan for row in curve]


def plot_case(rows: list[dict], case: PlotCase) -> Path:
    curves = {pol: select_curve(rows, case, pol) for pol in POLARIZATIONS}
    if not curves[0.0]:
        raise RuntimeError(f"未找到 0 deg 参考曲线: {case}")
    ref = {row["theta_deg"]: row["pdoa_deg"] for row in curves[0.0] if row["valid"]}

    fig, axes = plt.subplots(2, 1, figsize=(11.5, 8.0), sharex=True)
    fig.suptitle(
        f"{case.title}\n"
        f"{case.freq_ghz:.4f} GHz, Phi={case.phi_deg:.0f} deg, {case.channel_set}, {case.baseline}",
        fontsize=14,
        fontweight="bold",
    )

    for pol, curve in curves.items():
        theta = [row["theta_deg"] for row in curve]
        axes[0].plot(
            theta,
            valid_series(curve, "pdoa_unwrapped_deg"),
            color=COLORS[pol],
            linewidth=1.8,
            label=f"{pol:.0f} deg",
        )
        axes[1].plot(
            theta,
            bias_against_reference(curve, ref),
            color=COLORS[pol],
            linewidth=1.6,
            label=f"{pol:.0f} deg",
        )

    axes[0].set_ylabel("展开 PDOA / deg")
    axes[0].grid(True, alpha=0.28)
    axes[0].legend(title="入射线极化", ncol=4, loc="best")

    axes[1].axhline(0.0, color="#333333", linewidth=0.8, alpha=0.7)
    axes[1].set_xlabel("Theta / deg")
    axes[1].set_ylabel("相对 0 deg 偏移 / deg")
    axes[1].set_ylim(-185.0, 185.0)
    axes[1].grid(True, alpha=0.28)

    fig.text(0.01, 0.01, case.note, fontsize=9, color="#444444")
    fig.tight_layout(rect=[0, 0.04, 1, 0.94])

    out = PLOTS_DIR / f"{case.key}.png"
    fig.savefig(out, dpi=180)
    plt.close(fig)
    return out


def plot_panel(rows: list[dict], paths: list[Path]) -> Path:
    fig, axes = plt.subplots(len(PLOT_CASES), 2, figsize=(14.5, 12.0), sharex="col")
    fig.suptitle("不同入射线极化下的 PDOA 鉴角曲线对比", fontsize=16, fontweight="bold")

    for row_idx, case in enumerate(PLOT_CASES):
        curves = {pol: select_curve(rows, case, pol) for pol in POLARIZATIONS}
        ref = {row["theta_deg"]: row["pdoa_deg"] for row in curves[0.0] if row["valid"]}
        ax_curve = axes[row_idx][0]
        ax_bias = axes[row_idx][1]
        for pol, curve in curves.items():
            theta = [row["theta_deg"] for row in curve]
            ax_curve.plot(theta, valid_series(curve, "pdoa_unwrapped_deg"), color=COLORS[pol], linewidth=1.3, label=f"{pol:.0f} deg")
            ax_bias.plot(theta, bias_against_reference(curve, ref), color=COLORS[pol], linewidth=1.3, label=f"{pol:.0f} deg")
        ax_curve.set_title(f"{case.title}: PDOA")
        ax_bias.set_title(f"{case.title}: 相对 0 deg 偏移")
        ax_curve.set_ylabel("deg")
        ax_bias.set_ylabel("deg")
        ax_bias.set_ylim(-185.0, 185.0)
        ax_curve.grid(True, alpha=0.25)
        ax_bias.grid(True, alpha=0.25)
        ax_bias.axhline(0.0, color="#333333", linewidth=0.7, alpha=0.6)
        if row_idx == 0:
            ax_curve.legend(title="入射线极化", ncol=4, fontsize=8)
            ax_bias.legend(title="入射线极化", ncol=4, fontsize=8)
        if row_idx == len(PLOT_CASES) - 1:
            ax_curve.set_xlabel("Theta / deg")
            ax_bias.set_xlabel("Theta / deg")

    fig.tight_layout(rect=[0, 0.02, 1, 0.96])
    out = PLOTS_DIR / "pdoa_linear_polarization_comparison_panel.png"
    fig.savefig(out, dpi=180)
    plt.close(fig)
    return out


def write_manifest(paths: list[Path], panel: Path) -> None:
    lines = [
        "# D44 PDOA 线极化鉴角曲线对比图",
        "",
        "## 图表范围",
        "",
        "- 入射极化仅包含线极化 `0 / 45 / 90 / 135 deg`。",
        "- 图中上半部分为展开后的 PDOA 鉴角曲线，下半部分为相对 `0 deg` 线极化的相位偏移。",
        "- 无效点按空缺处理，避免弱响应点把曲线误连。",
        "",
        "## 输出图片",
        "",
        f"- 总览拼图: `{panel}`",
    ]
    for case, path in zip(PLOT_CASES, paths):
        lines.append(f"- {case.title}: `{path}`")
        lines.append(f"  - {case.note}")
    lines.extend(
        [
            "",
            "## 数据来源",
            "",
            f"- 曲线 CSV: `{CURVES_CSV}`",
            "- PDOA 线极化评估脚本输出的 `pdoa_unwrapped_deg` 用于鉴角曲线，`pdoa_deg` 用于计算相对 0 deg 偏移。",
        ]
    )
    MANIFEST_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    configure_font()
    PLOTS_DIR.mkdir(parents=True, exist_ok=True)
    rows = read_rows()
    paths = [plot_case(rows, case) for case in PLOT_CASES]
    panel = plot_panel(rows, paths)
    write_manifest(paths, panel)
    print(f"Wrote {panel}")
    for path in paths:
        print(f"Wrote {path}")
    print(f"Wrote {MANIFEST_MD}")


if __name__ == "__main__":
    main()
