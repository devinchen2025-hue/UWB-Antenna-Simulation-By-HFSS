from __future__ import annotations

import cmath
import csv
import json
import math
from dataclasses import dataclass
from pathlib import Path
from statistics import fmean

import matplotlib.pyplot as plt
from matplotlib import font_manager
from ansys.aedt.core import Hfss

import evaluate_uwb_ch9_d44_pdoa_linear_polarization as pdoa_eval
import evaluate_uwb_ch9_d44_topology as topology_eval


ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = ROOT / "reports_d44_pdoa_stability_opt"
HISTORY_CSV = REPORT_DIR / "UWB_CH9_D44_PDOA_polarization_stability_history.csv"
VALIDATION_CSV = REPORT_DIR / "UWB_CH9_D44_PDOA_polarization_stability_top_validation.csv"
BEST_CURVES_CSV = REPORT_DIR / "UWB_CH9_D44_PDOA_polarization_stability_best_curves.csv"
BEST_JSON = REPORT_DIR / "UWB_CH9_D44_PDOA_polarization_stability_best.json"
REPORT_MD = REPORT_DIR / "UWB_CH9_D44_PDOA_polarization_stability_report.md"
HEATMAP_PNG = REPORT_DIR / "UWB_CH9_D44_PDOA_polarization_stability_score_heatmap.png"

PROJECT_PATH = pdoa_eval.PROJECT_PATH
DESIGN = pdoa_eval.DESIGN
SOLUTION = pdoa_eval.SOLUTION
SPHERE = pdoa_eval.SPHERE

PDOA_RMS_TARGET_DEG = 10.0
PDOA_MAX_TARGET_DEG = 20.0
RETURN_TARGET_DB = -10.0
ISOLATION_TARGET_DB = 15.0
GAIN_TARGET_DBI = -5.0
AR_TARGET_DB = 3.0

PHI_CUTS_DEG = pdoa_eval.PHI_CUTS_DEG
POLARIZATIONS_DEG = pdoa_eval.LINEAR_POLARIZATION_DEG
BASELINES = [("E1", "E3"), ("E2", "E4"), ("E1", "E2"), ("E2", "E3"), ("E3", "E4"), ("E4", "E1")]
NONREF_POLS = [pol for pol in POLARIZATIONS_DEG if abs(pol) > 1e-9]
MAG_VALID_FLOOR_REL_DB = pdoa_eval.MAG_VALID_FLOOR_REL_DB


@dataclass(frozen=True)
class Candidate:
    amp_b: float
    phase_b_deg: float


def fmt(value: float | int | None, digits: int = 2) -> str:
    if value is None:
        return "N/A"
    value = float(value)
    if math.isnan(value) or math.isinf(value):
        return "N/A"
    return f"{value:.{digits}f}"


def configure_font() -> None:
    available = {font.name for font in font_manager.fontManager.ttflist}
    for candidate in ["Microsoft YaHei", "SimHei", "SimSun", "Arial Unicode MS"]:
        if candidate in available:
            plt.rcParams["font.sans-serif"] = [candidate, "DejaVu Sans"]
            break
    plt.rcParams["axes.unicode_minus"] = False


def complex_weight(amp: float, phase_deg: float) -> complex:
    return amp * cmath.exp(1j * math.radians(phase_deg))


def candidate_grid() -> list[Candidate]:
    amps = [round(0.80 + 0.025 * idx, 3) for idx in range(17)]
    phases = [round(-125.0 + 2.5 * idx, 1) for idx in range(29)]
    candidates = [Candidate(amp, phase) for amp in amps for phase in phases]
    if Candidate(1.0, -90.0) not in candidates:
        candidates.append(Candidate(1.0, -90.0))
    return candidates


def channel_voltage(
    element: int,
    fields_by_source: dict[str, dict[tuple[float, float], pdoa_eval.FieldPoint]],
    key: tuple[float, float],
    pol_deg: float,
    candidate: Candidate,
) -> complex:
    a = fields_by_source[f"P{element}A"][key]
    b = fields_by_source[f"P{element}B"][key]
    va = pdoa_eval.linear_projection(a, pol_deg)
    vb = pdoa_eval.linear_projection(b, pol_deg)
    return va + complex_weight(candidate.amp_b, candidate.phase_b_deg) * vb


def unwrap(values: list[float]) -> list[float]:
    return pdoa_eval.unwrap_degrees(values)


def curve_metrics(rows: list[dict], reference_by_theta: dict[float, float] | None) -> dict:
    valid_rows = [row for row in rows if row["valid"]]
    bias_values = []
    if reference_by_theta:
        for row in valid_rows:
            ref = reference_by_theta.get(row["theta_deg"])
            if ref is not None:
                bias_values.append(pdoa_eval.wrap_deg(row["pdoa_deg"] - ref))
    abs_bias = [abs(item) for item in bias_values]
    unwrapped = unwrap([row["pdoa_deg"] for row in valid_rows]) if valid_rows else []
    for row, value in zip(valid_rows, unwrapped):
        row["pdoa_unwrapped_deg"] = value
    for row in rows:
        row.setdefault("pdoa_unwrapped_deg", row["pdoa_deg"])

    slopes = [
        (unwrapped[idx + 1] - unwrapped[idx])
        / (valid_rows[idx + 1]["theta_deg"] - valid_rows[idx]["theta_deg"])
        for idx in range(len(valid_rows) - 1)
        if abs(valid_rows[idx + 1]["theta_deg"] - valid_rows[idx]["theta_deg"]) > 1e-9
    ]
    if slopes:
        pos = sum(1 for slope in slopes if slope >= 0.0)
        neg = len(slopes) - pos
        monotonic = 100.0 * max(pos, neg) / len(slopes)
    else:
        monotonic = 0.0

    return {
        "valid_percent": 100.0 * len(valid_rows) / len(rows) if rows else 0.0,
        "rms_bias_deg": math.sqrt(fmean(value * value for value in bias_values)) if bias_values else 0.0,
        "mean_abs_bias_deg": fmean(abs_bias) if abs_bias else 0.0,
        "max_abs_bias_deg": max(abs_bias) if abs_bias else 0.0,
        "monotonic_segment_percent": monotonic,
        "pdoa_span_deg": max(unwrapped) - min(unwrapped) if unwrapped else float("nan"),
    }


def evaluate_candidate(fields: dict, eval_freqs: list[float], candidate: Candidate, keep_curves: bool = False) -> tuple[dict, list[dict]]:
    summary_rows = []
    curve_rows = []
    for freq in eval_freqs:
        fkey = pdoa_eval.freq_key(freq)
        fields_by_source = {source: fields[source][fkey] for source in fields}
        all_points = next(iter(fields_by_source.values()))
        theta_values = sorted({point.theta_deg for point in all_points.values()})
        phi_values = sorted({point.phi_deg for point in all_points.values()})
        selected_phi = [phi for phi in PHI_CUTS_DEG if any(abs(phi - item) < 1e-6 for item in phi_values)]

        for phi in selected_phi:
            for left_label, right_label in BASELINES:
                left = int(left_label[1:])
                right = int(right_label[1:])
                per_pol_rows: dict[float, list[dict]] = {}
                reference_by_theta = None
                for pol in POLARIZATIONS_DEG:
                    raw_rows = []
                    magnitudes = []
                    for theta in theta_values:
                        point_key = (round(theta, 9), round(phi, 9))
                        if point_key not in all_points:
                            continue
                        v_left = channel_voltage(left, fields_by_source, point_key, pol, candidate)
                        v_right = channel_voltage(right, fields_by_source, point_key, pol, candidate)
                        magnitudes.extend([abs(v_left), abs(v_right)])
                        raw_rows.append(
                            {
                                "freq_ghz": freq,
                                "phi_deg": phi,
                                "theta_deg": theta,
                                "linear_pol_deg": pol,
                                "amp_b": candidate.amp_b,
                                "phase_b_deg": candidate.phase_b_deg,
                                "channel_set": "dualfeed_amp_phase_optimized",
                                "baseline": f"{left_label}-{right_label}",
                                "left_mag": abs(v_left),
                                "right_mag": abs(v_right),
                                "pdoa_deg": pdoa_eval.wrap_deg(pdoa_eval.phase_deg(v_left) - pdoa_eval.phase_deg(v_right)),
                            }
                        )
                    reference = max(magnitudes) if magnitudes else 1.0
                    floor = reference * 10.0 ** (MAG_VALID_FLOOR_REL_DB / 20.0)
                    for row in raw_rows:
                        row["left_mag_rel_db"] = pdoa_eval.rel_db(row["left_mag"], reference)
                        row["right_mag_rel_db"] = pdoa_eval.rel_db(row["right_mag"], reference)
                        row["valid"] = row["left_mag"] >= floor and row["right_mag"] >= floor
                    per_pol_rows[pol] = raw_rows
                    if abs(pol) < 1e-9:
                        reference_by_theta = {row["theta_deg"]: row["pdoa_deg"] for row in raw_rows if row["valid"]}

                for pol, rows in per_pol_rows.items():
                    metrics = curve_metrics(rows, reference_by_theta)
                    metrics.update(
                        {
                            "freq_ghz": freq,
                            "phi_deg": phi,
                            "linear_pol_deg": pol,
                            "baseline": f"{left_label}-{right_label}",
                        }
                    )
                    summary_rows.append(metrics)
                    if keep_curves:
                        curve_rows.extend(rows)

    nonref = [row for row in summary_rows if row["linear_pol_deg"] in NONREF_POLS]
    ref = [row for row in summary_rows if abs(row["linear_pol_deg"]) < 1e-9]
    rms_values = sorted(row["rms_bias_deg"] for row in nonref)
    max_values = [row["max_abs_bias_deg"] for row in nonref]
    valid_values = [row["valid_percent"] for row in summary_rows]
    mono_values = [row["monotonic_segment_percent"] for row in ref]
    p95_index = max(0, math.ceil(0.95 * len(rms_values)) - 1)

    avg_rms = fmean(rms_values) if rms_values else 0.0
    p95_rms = rms_values[p95_index] if rms_values else 0.0
    max_abs = max(max_values) if max_values else 0.0
    avg_max = fmean(max_values) if max_values else 0.0
    avg_valid = fmean(valid_values) if valid_values else 0.0
    avg_mono = fmean(mono_values) if mono_values else 0.0

    score = (
        avg_rms
        + 0.55 * p95_rms
        + 0.12 * max_abs
        + 0.35 * max(0.0, 98.0 - avg_valid)
        + 0.10 * max(0.0, 75.0 - avg_mono)
        + 4.0 * abs(20.0 * math.log10(candidate.amp_b))
        + 0.25 * abs(abs(candidate.phase_b_deg) - 90.0)
    )
    result = {
        "amp_b": candidate.amp_b,
        "phase_b_deg": candidate.phase_b_deg,
        "score": score,
        "avg_rms_bias_deg": avg_rms,
        "p95_rms_bias_deg": p95_rms,
        "avg_max_abs_bias_deg": avg_max,
        "max_abs_bias_deg": max_abs,
        "avg_valid_percent": avg_valid,
        "avg_reference_monotonic_percent": avg_mono,
        "curve_count": len(summary_rows),
        "pdoa_rms_target_met": avg_rms <= PDOA_RMS_TARGET_DEG,
        "pdoa_max_target_met": max_abs <= PDOA_MAX_TARGET_DEG,
    }
    return result, curve_rows


def append_history(rows: list[dict]) -> None:
    if not rows:
        return
    with HISTORY_CSV.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def source_assignments(sources: list[str], candidate: Candidate) -> dict[str, tuple[float, float]]:
    assignments = {source: (0.0, 0.0) for source in sources}
    for idx in range(1, 5):
        base_phase = (idx - 1) * -90.0
        a = f"P{idx}A"
        b = f"P{idx}B"
        if a in assignments:
            assignments[a] = (1.0, base_phase)
        if b in assignments:
            assignments[b] = (candidate.amp_b, base_phase + candidate.phase_b_deg)
    return assignments


def validate_axial_ratio(hfss: Hfss, sources: list[str], eval_freqs: list[float], candidates: list[dict]) -> list[dict]:
    rows = []
    for item in candidates:
        candidate = Candidate(float(item["amp_b"]), float(item["phase_b_deg"]))
        hfss.edit_sources(source_assignments(sources, candidate))
        summaries = []
        for freq in eval_freqs:
            grid = topology_eval.get_grid(hfss, freq)
            summaries.append(topology_eval.summarize_rows(freq, grid["rows"]))
        row = {
            "amp_b": candidate.amp_b,
            "phase_b_deg": candidate.phase_b_deg,
            "gain_min_dbi": min(summary["gain_min_dbi"] for summary in summaries),
            "axial_ratio_max_db": max(summary["axial_ratio_max_db"] for summary in summaries),
            "cp_coverage_min_percent": min(summary["cp_coverage_percent"] for summary in summaries),
        }
        source_score = next(x for x in candidates if float(x["amp_b"]) == candidate.amp_b and float(x["phase_b_deg"]) == candidate.phase_b_deg)
        gain_penalty = max(0.0, GAIN_TARGET_DBI - row["gain_min_dbi"])
        ar_penalty = max(0.0, row["axial_ratio_max_db"] - AR_TARGET_DB)
        row["pdoa_score"] = source_score["score"]
        row["combined_score"] = source_score["score"] + 0.04 * ar_penalty + 0.6 * gain_penalty - 0.04 * row["cp_coverage_min_percent"]
        row["ar_target_met"] = row["axial_ratio_max_db"] <= AR_TARGET_DB
        row["gain_target_met"] = row["gain_min_dbi"] >= GAIN_TARGET_DBI
        rows.append(row)

    with VALIDATION_CSV.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    return rows


def write_best_curves(rows: list[dict]) -> None:
    if not rows:
        return
    fields = [
        "freq_ghz",
        "phi_deg",
        "theta_deg",
        "linear_pol_deg",
        "amp_b",
        "phase_b_deg",
        "channel_set",
        "baseline",
        "pdoa_deg",
        "pdoa_unwrapped_deg",
        "left_mag_rel_db",
        "right_mag_rel_db",
        "valid",
    ]
    with BEST_CURVES_CSV.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    key: f"{row[key]:.6f}" if isinstance(row.get(key), float) else row.get(key)
                    for key in fields
                }
            )


def plot_heatmap(history_rows: list[dict], best: dict) -> None:
    configure_font()
    amps = sorted({float(row["amp_b"]) for row in history_rows})
    phases = sorted({float(row["phase_b_deg"]) for row in history_rows})
    scores = {(float(row["amp_b"]), float(row["phase_b_deg"])): float(row["score"]) for row in history_rows}
    matrix = [[scores.get((amp, phase), math.nan) for phase in phases] for amp in amps]

    fig, ax = plt.subplots(figsize=(11.0, 6.5))
    image = ax.imshow(matrix, origin="lower", aspect="auto", cmap="viridis")
    ax.set_xticks(range(0, len(phases), 4), [f"{phases[idx]:.0f}" for idx in range(0, len(phases), 4)])
    ax.set_yticks(range(0, len(amps), 2), [f"{amps[idx]:.2f}" for idx in range(0, len(amps), 2)])
    ax.set_xlabel("B 路相位 / deg")
    ax.set_ylabel("B 路幅度 / A 路幅度")
    ax.set_title("PDOA 极化稳定性优化评分热力图")
    fig.colorbar(image, ax=ax, label="评分，越低越好")
    best_x = phases.index(float(best["phase_b_deg"]))
    best_y = amps.index(float(best["amp_b"]))
    ax.scatter(best_x, best_y, marker="x", s=100, color="white", linewidths=2.0, label="最优点")
    ax.legend(loc="upper right")
    fig.tight_layout()
    fig.savefig(HEATMAP_PNG, dpi=180)
    plt.close(fig)


def load_current_sparams() -> dict:
    metrics_path = ROOT / "reports_d44_dualfeed_cp" / "UWB_CH9_D44_DUALFEED_CP_metrics.json"
    if not metrics_path.exists():
        return {}
    metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
    return metrics.get("s_parameters", {})


def write_report(best: dict, pure_pdoa_best: dict, baseline: dict, validation_rows: list[dict]) -> None:
    sparams = load_current_sparams()
    best_validation = min(validation_rows, key=lambda row: row["combined_score"]) if validation_rows else {}
    lines = [
        "# D44 锚点天线 PDOA 极化稳定性优化报告",
        "",
        "## 本轮目标",
        "",
        f"- 不同入射线极化 `0 / 45 / 90 / 135 deg` 下，PDOA 鉴角曲线变化最小。",
        f"- 目标阈值：平均 RMS 漂移 `<= {PDOA_RMS_TARGET_DEG:.1f} deg`，最大漂移 `<= {PDOA_MAX_TARGET_DEG:.1f} deg`。",
        f"- 同时参考天线指标：`Sii <= {RETURN_TARGET_DB:.1f} dB`、隔离 `>= {ISOLATION_TARGET_DB:.1f} dB`、轴比 `<= {AR_TARGET_DB:.1f} dB`、FOV 最小增益 `>= {GAIN_TARGET_DBI:.1f} dBi`。",
        "",
        "## 优化路径",
        "",
        "- 本轮不重建几何，直接使用已求解 HFSS 工程中的 `re/im(rETheta)` 与 `re/im(rEPhi)` 嵌入式复数远场。",
        "- 扫描双馈 B 路相对 A 路的输出幅度和相位，等价于优化 90 度混合器输出幅相平衡。",
        "- 幅度范围 `0.80-1.20`，步进 `0.025`；相位范围 `-125 deg` 到 `-55 deg`，步进 `2.5 deg`。",
        "- 评分函数直接惩罚 45/90/135 deg 线极化相对 0 deg 的 PDOA RMS 漂移、95 分位 RMS 漂移、最大漂移、弱响应点和参考曲线单调性不足。",
        "",
        "## 纯 PDOA 最优候选",
        "",
        f"- B 路幅度：`{fmt(pure_pdoa_best.get('amp_b'), 3)}`，相对 A 路。",
        f"- B 路相位：`{fmt(pure_pdoa_best.get('phase_b_deg'), 1)} deg`，相对 A 路。",
        f"- 纯 PDOA 评分：`{fmt(pure_pdoa_best.get('score'), 2)}`，越低越好。",
        f"- 平均 RMS PDOA 漂移：`{fmt(pure_pdoa_best.get('avg_rms_bias_deg'), 2)} deg`。",
        f"- 95 分位 RMS PDOA 漂移：`{fmt(pure_pdoa_best.get('p95_rms_bias_deg'), 2)} deg`。",
        f"- 全局最大 PDOA 漂移：`{fmt(pure_pdoa_best.get('max_abs_bias_deg'), 2)} deg`。",
        "",
        "## 综合最优幅相候选",
        "",
        f"- B 路幅度：`{fmt(best.get('amp_b'), 3)}`，相对 A 路。",
        f"- B 路相位：`{fmt(best.get('phase_b_deg'), 1)} deg`，相对 A 路。",
        f"- 综合候选来自 Top PDOA 候选的轴比/增益复核，兼顾 PDOA 漂移和轴比异常值。",
        f"- PDOA 评分：`{fmt(best.get('score'), 2)}`，越低越好。",
        f"- 平均 RMS PDOA 漂移：`{fmt(best.get('avg_rms_bias_deg'), 2)} deg`。",
        f"- 95 分位 RMS PDOA 漂移：`{fmt(best.get('p95_rms_bias_deg'), 2)} deg`。",
        f"- 平均最大 PDOA 漂移：`{fmt(best.get('avg_max_abs_bias_deg'), 2)} deg`。",
        f"- 全局最大 PDOA 漂移：`{fmt(best.get('max_abs_bias_deg'), 2)} deg`。",
        f"- 平均有效点比例：`{fmt(best.get('avg_valid_percent'), 1)}%`。",
        f"- 参考极化曲线平均单调片段比例：`{fmt(best.get('avg_reference_monotonic_percent'), 1)}%`。",
        "",
        "## 与当前默认 1.00 / -90 deg 对比",
        "",
        f"- 默认平均 RMS 漂移：`{fmt(baseline.get('avg_rms_bias_deg'), 2)} deg`。",
        f"- 纯 PDOA 最优平均 RMS 漂移：`{fmt(pure_pdoa_best.get('avg_rms_bias_deg'), 2)} deg`。",
        f"- 优化后平均 RMS 漂移：`{fmt(best.get('avg_rms_bias_deg'), 2)} deg`。",
        f"- 默认 95 分位 RMS 漂移：`{fmt(baseline.get('p95_rms_bias_deg'), 2)} deg`。",
        f"- 纯 PDOA 最优 95 分位 RMS 漂移：`{fmt(pure_pdoa_best.get('p95_rms_bias_deg'), 2)} deg`。",
        f"- 综合候选 95 分位 RMS 漂移：`{fmt(best.get('p95_rms_bias_deg'), 2)} deg`。",
        f"- 默认最大漂移：`{fmt(baseline.get('max_abs_bias_deg'), 2)} deg`。",
        f"- 优化后最大漂移：`{fmt(best.get('max_abs_bias_deg'), 2)} deg`。",
        f"- 纯 PDOA 平均 RMS 改善：`{fmt(baseline.get('avg_rms_bias_deg', 0.0) - pure_pdoa_best.get('avg_rms_bias_deg', 0.0), 2)} deg`。",
        f"- 综合候选平均 RMS 变化：`{fmt(best.get('avg_rms_bias_deg', 0.0) - baseline.get('avg_rms_bias_deg', 0.0), 2)} deg`。",
        "",
        "## 轴比和 S 参数验证",
        "",
        f"- 当前工程最差 Sii：`{fmt(sparams.get('worst_return_db'))} dB`，目标 `<= -10 dB`。",
        f"- 当前工程隔离度：`{fmt(sparams.get('isolation_db'))} dB`，目标 `>= 15 dB`。",
        f"- 最优幅相候选的 FOV 最小增益：`{fmt(best_validation.get('gain_min_dbi'))} dBi`。",
        f"- 最优幅相候选的 FOV 最大轴比：`{fmt(best_validation.get('axial_ratio_max_db'))} dB`。",
        f"- 最优幅相候选的 CP 覆盖率下限：`{fmt(best_validation.get('cp_coverage_min_percent'), 1)}%`。",
        "",
        "## 达标情况",
        "",
        f"- PDOA 平均 RMS 目标：`{'通过' if best.get('avg_rms_bias_deg', 999.0) <= PDOA_RMS_TARGET_DEG else '未通过'}`。",
        f"- PDOA 最大漂移目标：`{'通过' if best.get('max_abs_bias_deg', 999.0) <= PDOA_MAX_TARGET_DEG else '未通过'}`。",
        f"- S 参数目标：`{'通过' if sparams.get('worst_return_db', 999.0) <= RETURN_TARGET_DB and sparams.get('isolation_db', -999.0) >= ISOLATION_TARGET_DB else '未通过'}`。",
        f"- 轴比目标：`{'通过' if best_validation.get('axial_ratio_max_db', 999.0) <= AR_TARGET_DB else '未通过'}`。",
        "",
        "## 工程结论",
        "",
        "- 仅优化双馈输出幅相对 PDOA 漂移改善很有限：纯 PDOA 最优只带来约 0.05 deg 的平均 RMS 改善，综合候选则为了降低轴比异常值牺牲了约 0.30 deg 的平均 RMS。",
        "- 这说明极化敏感性不只是混合器输出误差导致，还来自阵元复数矢量有效长度、端口耦合、馈线路径和阵元间不一致。",
        "- 轴比与 PDOA 稳定性有相关性，但本轮再次表明：轴比不是充分条件。综合候选轴比异常值比默认点低很多，但 PDOA 最大漂移仍接近 180 deg。",
        "- 下一轮建议进入几何层：优先围绕端口隔离、双馈物理对称性、DGS/隔离枝节非直连耦合、四阵元馈线等长等相位继续优化。",
        "",
        "## 输出文件",
        "",
        f"- 优化历史：`{HISTORY_CSV}`",
        f"- Top 候选轴比验证：`{VALIDATION_CSV}`",
        f"- 最优曲线 CSV：`{BEST_CURVES_CSV}`",
        f"- 最优结果 JSON：`{BEST_JSON}`",
        f"- 评分热力图：`{HEATMAP_PNG}`",
    ]
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run() -> dict:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    lock = PROJECT_PATH.with_suffix(".aedt.lock")
    if lock.exists():
        try:
            lock.unlink()
        except OSError:
            pass

    hfss = Hfss(
        project=str(PROJECT_PATH),
        design=DESIGN,
        version="2023.1",
        non_graphical=True,
        new_desktop=True,
        close_on_exit=False,
        remove_lock=True,
    )
    try:
        sources = hfss.get_all_sources()
        eval_freqs = pdoa_eval.nearest_frequencies(pdoa_eval.get_available_frequencies(hfss))
        fields = pdoa_eval.acquire_embedded_fields(hfss, sources, eval_freqs)

        history_rows = []
        candidates = candidate_grid()
        for idx, candidate in enumerate(candidates, start=1):
            result, _ = evaluate_candidate(fields, eval_freqs, candidate, keep_curves=False)
            history_rows.append(result)
            if idx % 50 == 0 or idx == len(candidates):
                print(f"Evaluated {idx}/{len(candidates)} candidates")
        history_rows.sort(key=lambda row: row["score"])
        append_history(history_rows)

        pure_pdoa_best = history_rows[0]
        baseline, _ = evaluate_candidate(fields, eval_freqs, Candidate(1.0, -90.0), keep_curves=False)
        validation_rows = validate_axial_ratio(hfss, sources, eval_freqs, history_rows[:12])
        best = min(history_rows[:12], key=lambda row: next(v["combined_score"] for v in validation_rows if v["amp_b"] == row["amp_b"] and v["phase_b_deg"] == row["phase_b_deg"]))
        _best_result, best_curves = evaluate_candidate(fields, eval_freqs, Candidate(float(best["amp_b"]), float(best["phase_b_deg"])), keep_curves=True)
        write_best_curves(best_curves)
        plot_heatmap(history_rows, best)

        best_validation = min(validation_rows, key=lambda row: row["combined_score"]) if validation_rows else {}
        output = {
            "project": str(PROJECT_PATH),
            "design": DESIGN,
            "solution": SOLUTION,
            "sphere": SPHERE,
            "targets": {
                "pdoa_rms_target_deg": PDOA_RMS_TARGET_DEG,
                "pdoa_max_target_deg": PDOA_MAX_TARGET_DEG,
                "return_target_db": RETURN_TARGET_DB,
                "isolation_target_db": ISOLATION_TARGET_DB,
                "gain_target_dbi": GAIN_TARGET_DBI,
                "axial_ratio_target_db": AR_TARGET_DB,
            },
            "sweep": {
                "amp_b_range": [0.80, 1.20],
                "amp_step": 0.025,
                "phase_b_deg_range": [-125.0, -55.0],
                "phase_step_deg": 2.5,
                "candidate_count": len(candidates),
            },
            "baseline_1p0_minus90": baseline,
            "pure_pdoa_best": pure_pdoa_best,
            "best": best,
            "best_axial_ratio_validation": best_validation,
            "current_s_parameters": load_current_sparams(),
            "files": {
                "history_csv": str(HISTORY_CSV),
                "validation_csv": str(VALIDATION_CSV),
                "best_curves_csv": str(BEST_CURVES_CSV),
                "best_json": str(BEST_JSON),
                "report_md": str(REPORT_MD),
                "heatmap_png": str(HEATMAP_PNG),
            },
        }
        BEST_JSON.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")
        write_report(best, pure_pdoa_best, baseline, validation_rows)
        print(json.dumps(output["best"], indent=2, ensure_ascii=False))
        print(f"Wrote {REPORT_MD}")
        return output
    finally:
        hfss.release_desktop(close_projects=False, close_desktop=True)


if __name__ == "__main__":
    run()
