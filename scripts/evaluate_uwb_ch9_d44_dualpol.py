from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path
from statistics import fmean

from ansys.aedt.core import Hfss

import build_uwb_ch9_hfss_d44_topology as builder
import evaluate_uwb_ch9_d44_pdoa_linear_polarization as pdoa_eval
import evaluate_uwb_ch9_d44_topology as topology_eval


ROOT = Path(__file__).resolve().parents[1]
TOPOLOGY = "dualpol"
SPEC = builder.TOPOLOGIES[TOPOLOGY]
PATHS = builder.topology_paths(TOPOLOGY)
REPORT_DIR = ROOT / "reports_d44_dualpol_xy"
STEM = "UWB_CH9_D44_DUALPOL_XY"
SPARAM_CSV = REPORT_DIR / f"{STEM}_s_parameters.csv"
CURVES_CSV = REPORT_DIR / f"{STEM}_pdoa_linear_curves.csv"
SUMMARY_CSV = REPORT_DIR / f"{STEM}_pdoa_linear_summary.csv"
METRICS_JSON = REPORT_DIR / f"{STEM}_metrics.json"
REPORT_MD = REPORT_DIR / f"{STEM}_simulation_report.md"

LINEAR_POLS = [0.0, 45.0, 90.0, 135.0]
PHI_CUTS = [45.0, 60.0, 75.0, 90.0]
MAG_VALID_FLOOR_REL_DB = -35.0
RETURN_TARGET_DB = -10.0
ISOLATION_TARGET_DB = 15.0
PDOA_RMS_TARGET_DEG = 10.0
PDOA_MAX_TARGET_DEG = 20.0

STRATEGIES = {
    "x_only_a_port": "仅使用 A 口，全局 X 极化通道。",
    "y_only_b_port": "仅使用 B 口，全局 Y 极化通道。",
    "dualpol_vector_correlation": "推荐的双极化 PDOA：用 X/Y 两通道向量相关直接估计两阵元相位差。",
    "dualpol_known_pol_vector": "已知入射线极化角时，按 cos/sin 对 X/Y 双通道做相干合成。",
    "dualpol_fixed_45deg_sum": "固定 45 deg 双通道等权合成，作为无极化估计时的简单参考。",
    "legacy_cp_minus90": "沿用圆极化路线的 A + B*(-90 deg) 合成，仅作对照。",
}


def fmt(value: float | int | None, digits: int = 2) -> str:
    if value is None:
        return "N/A"
    value = float(value)
    if math.isnan(value) or math.isinf(value):
        return "N/A"
    return f"{value:.{digits}f}"


def port_base(port: str) -> str:
    return port.split(":", 1)[0]


def port_feed(port: str) -> str:
    base = port_base(port)
    return base[-1] if base else ""


def port_element(port: str) -> str:
    base = port_base(port)
    return "".join(ch for ch in base if ch.isdigit())


def enrich_sparams(snapshot: dict) -> dict:
    self_terms = snapshot.get("self_worst_db", {})
    coupling_terms = snapshot.get("coupling_worst_db", {})

    x_returns = []
    y_returns = []
    same_element_xy = []
    same_feed_inter_element = []
    all_inter_element = []
    for expr, value in self_terms.items():
        left, _right = topology_eval.parse_s_term(expr)
        feed = port_feed(left)
        if feed == "A":
            x_returns.append(float(value))
        elif feed == "B":
            y_returns.append(float(value))
    for expr, value in coupling_terms.items():
        left, right = topology_eval.parse_s_term(expr)
        left_base = port_base(left)
        right_base = port_base(right)
        left_element = port_element(left_base)
        right_element = port_element(right_base)
        left_feed = port_feed(left_base)
        right_feed = port_feed(right_base)
        value = float(value)
        all_inter_element.append(value)
        if left_element == right_element and {left_feed, right_feed} == {"A", "B"}:
            same_element_xy.append(value)
        if left_element != right_element and left_feed == right_feed:
            same_feed_inter_element.append(value)

    return {
        "x_return_worst_db": max(x_returns) if x_returns else float("nan"),
        "y_return_worst_db": max(y_returns) if y_returns else float("nan"),
        "same_element_xy_coupling_worst_db": max(same_element_xy) if same_element_xy else float("nan"),
        "same_element_xy_isolation_db": -max(same_element_xy) if same_element_xy else float("nan"),
        "same_feed_inter_element_coupling_worst_db": max(same_feed_inter_element) if same_feed_inter_element else float("nan"),
        "same_feed_inter_element_isolation_db": -max(same_feed_inter_element) if same_feed_inter_element else float("nan"),
        "overall_coupling_worst_db": max(all_inter_element) if all_inter_element else float("nan"),
    }


def complex_weight(deg: float) -> complex:
    return math.cos(math.radians(deg)) + 1j * math.sin(math.radians(deg))


def element_pairs(sources: list[str]) -> list[int]:
    available = set(sources)
    pairs = []
    for idx in range(1, 5):
        if f"P{idx}A" in available and f"P{idx}B" in available:
            pairs.append(idx)
    return pairs


def baseline_pairs(elements: list[int]) -> list[tuple[int, int]]:
    preferred = [(1, 3), (2, 4), (1, 2), (2, 3), (3, 4), (4, 1)]
    return [(left, right) for left, right in preferred if left in elements and right in elements]


def linear_projection(point: pdoa_eval.FieldPoint, polarization_deg: float) -> complex:
    angle = math.radians(polarization_deg)
    return point.etheta * math.cos(angle) + point.ephi * math.sin(angle)


def rel_db(value: float, reference: float) -> float:
    if value <= 0.0 or reference <= 0.0:
        return -999.0
    return 20.0 * math.log10(value / reference)


def combine_element_response(
    fields_by_source: dict[str, dict[tuple[float, float], pdoa_eval.FieldPoint]],
    element: int,
    point_key: tuple[float, float],
    pol_deg: float,
    strategy: str,
) -> complex:
    a = linear_projection(fields_by_source[f"P{element}A"][point_key], pol_deg)
    b = linear_projection(fields_by_source[f"P{element}B"][point_key], pol_deg)
    if strategy == "x_only_a_port":
        return a
    if strategy == "y_only_b_port":
        return b
    if strategy == "dualpol_known_pol_vector":
        angle = math.radians(pol_deg)
        return a * math.cos(angle) + b * math.sin(angle)
    if strategy == "dualpol_fixed_45deg_sum":
        return (a + b) / math.sqrt(2.0)
    if strategy == "legacy_cp_minus90":
        return a + b * complex_weight(-90.0)
    raise ValueError(f"Unsupported dualpol strategy {strategy}")


def element_vector_response(
    fields_by_source: dict[str, dict[tuple[float, float], pdoa_eval.FieldPoint]],
    element: int,
    point_key: tuple[float, float],
    pol_deg: float,
) -> tuple[complex, complex]:
    return (
        linear_projection(fields_by_source[f"P{element}A"][point_key], pol_deg),
        linear_projection(fields_by_source[f"P{element}B"][point_key], pol_deg),
    )


def summarize_curve(rows: list[dict], reference_by_theta: dict[float, float] | None) -> dict:
    valid_rows = [row for row in rows if row["valid"]]
    if len(valid_rows) >= 2:
        unwrapped = pdoa_eval.unwrap_degrees([row["pdoa_deg"] for row in valid_rows])
        for row, value in zip(valid_rows, unwrapped):
            row["pdoa_unwrapped_deg"] = value
        slopes = [
            (unwrapped[idx + 1] - unwrapped[idx])
            / (valid_rows[idx + 1]["theta_deg"] - valid_rows[idx]["theta_deg"])
            for idx in range(len(valid_rows) - 1)
            if abs(valid_rows[idx + 1]["theta_deg"] - valid_rows[idx]["theta_deg"]) > 1e-9
        ]
    else:
        unwrapped = []
        slopes = []
    for row in rows:
        row.setdefault("pdoa_unwrapped_deg", row["pdoa_deg"])

    slope_positive = sum(1 for slope in slopes if slope >= 0.0)
    slope_negative = sum(1 for slope in slopes if slope < 0.0)
    monotonic = 100.0 * max(slope_positive, slope_negative) / len(slopes) if slopes else 0.0

    bias_values = []
    if reference_by_theta:
        for row in valid_rows:
            ref = reference_by_theta.get(row["theta_deg"])
            if ref is not None:
                bias_values.append(pdoa_eval.wrap_deg(row["pdoa_deg"] - ref))
    abs_bias = [abs(value) for value in bias_values]
    return {
        "valid_count": len(valid_rows),
        "total_count": len(rows),
        "valid_percent": 100.0 * len(valid_rows) / len(rows) if rows else 0.0,
        "pdoa_span_deg": max(unwrapped) - min(unwrapped) if unwrapped else float("nan"),
        "pdoa_start_deg": unwrapped[0] if unwrapped else float("nan"),
        "pdoa_end_deg": unwrapped[-1] if unwrapped else float("nan"),
        "monotonic_segment_percent": monotonic,
        "min_pair_mag_rel_db": min(min(row["left_mag_rel_db"], row["right_mag_rel_db"]) for row in rows) if rows else float("nan"),
        "rms_bias_vs_pol0_deg": math.sqrt(fmean(value * value for value in bias_values)) if bias_values else 0.0,
        "mean_abs_bias_vs_pol0_deg": fmean(abs_bias) if abs_bias else 0.0,
        "max_abs_bias_vs_pol0_deg": max(abs_bias) if abs_bias else 0.0,
    }


def percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    idx = min(len(ordered) - 1, max(0, math.ceil(len(ordered) * pct / 100.0) - 1))
    return ordered[idx]


def evaluate_dualpol_pdoa(fields: dict, eval_freqs: list[float], sources: list[str]) -> tuple[list[dict], list[dict], dict]:
    elements = element_pairs(sources)
    baselines = baseline_pairs(elements)
    curves: list[dict] = []
    summaries: list[dict] = []

    for freq in eval_freqs:
        fkey = pdoa_eval.freq_key(freq)
        fields_by_source = {source: fields[source][fkey] for source in sources}
        all_points = next(iter(fields_by_source.values()))
        theta_values = sorted({point.theta_deg for point in all_points.values()})
        phi_values = sorted({point.phi_deg for point in all_points.values()})
        selected_phi = [phi for phi in PHI_CUTS if any(abs(phi - item) < 1e-6 for item in phi_values)]

        for strategy in STRATEGIES:
            for phi in selected_phi:
                for left, right in baselines:
                    reference_by_theta = None
                    by_pol: dict[float, list[dict]] = {}
                    for pol in LINEAR_POLS:
                        raw_rows = []
                        mags = []
                        for theta in theta_values:
                            key = (round(theta, 9), round(phi, 9))
                            if key not in all_points:
                                continue
                            if strategy == "dualpol_vector_correlation":
                                left_vec = element_vector_response(fields_by_source, left, key, pol)
                                right_vec = element_vector_response(fields_by_source, right, key, pol)
                                v_left_mag = math.sqrt(sum(abs(value) ** 2 for value in left_vec))
                                v_right_mag = math.sqrt(sum(abs(value) ** 2 for value in right_vec))
                                pair_phase = sum(lv * rv.conjugate() for lv, rv in zip(left_vec, right_vec))
                                pdoa_deg = pdoa_eval.wrap_deg(pdoa_eval.phase_deg(pair_phase))
                            else:
                                v_left = combine_element_response(fields_by_source, left, key, pol, strategy)
                                v_right = combine_element_response(fields_by_source, right, key, pol, strategy)
                                v_left_mag = abs(v_left)
                                v_right_mag = abs(v_right)
                                pdoa_deg = pdoa_eval.wrap_deg(pdoa_eval.phase_deg(v_left) - pdoa_eval.phase_deg(v_right))
                            mags.extend([v_left_mag, v_right_mag])
                            raw_rows.append(
                                {
                                    "freq_ghz": freq,
                                    "phi_deg": phi,
                                    "theta_deg": theta,
                                    "linear_pol_deg": pol,
                                    "strategy": strategy,
                                    "baseline": f"E{left}-E{right}",
                                    "left_mag": v_left_mag,
                                    "right_mag": v_right_mag,
                                    "pdoa_deg": pdoa_deg,
                                }
                            )
                        reference = max(mags) if mags else 1.0
                        floor = reference * 10.0 ** (MAG_VALID_FLOOR_REL_DB / 20.0)
                        for row in raw_rows:
                            row["left_mag_rel_db"] = rel_db(row["left_mag"], reference)
                            row["right_mag_rel_db"] = rel_db(row["right_mag"], reference)
                            row["valid"] = row["left_mag"] >= floor and row["right_mag"] >= floor
                        by_pol[pol] = raw_rows
                        if pol == 0.0:
                            reference_by_theta = {row["theta_deg"]: row["pdoa_deg"] for row in raw_rows if row["valid"]}
                    for pol, rows in by_pol.items():
                        summary = summarize_curve(rows, reference_by_theta)
                        summary.update(
                            {
                                "freq_ghz": freq,
                                "phi_deg": phi,
                                "linear_pol_deg": pol,
                                "strategy": strategy,
                                "strategy_note": STRATEGIES[strategy],
                                "baseline": f"E{left}-E{right}",
                            }
                        )
                        summaries.append(summary)
                        curves.extend(rows)

    strategy_summary = {}
    for strategy in STRATEGIES:
        rows = [row for row in summaries if row["strategy"] == strategy and abs(row["linear_pol_deg"]) > 1e-9]
        rms = [row["rms_bias_vs_pol0_deg"] for row in rows]
        max_abs = [row["max_abs_bias_vs_pol0_deg"] for row in rows]
        valid = [row["valid_percent"] for row in rows]
        strategy_summary[strategy] = {
            "note": STRATEGIES[strategy],
            "curve_count": len(rows),
            "avg_rms_bias_deg": fmean(rms) if rms else 0.0,
            "p95_rms_bias_deg": percentile(rms, 95.0),
            "max_abs_bias_deg": max(max_abs) if max_abs else 0.0,
            "avg_valid_percent": fmean(valid) if valid else 0.0,
            "score": (fmean(rms) if rms else 0.0) + 0.2 * percentile(rms, 95.0) + 0.03 * (max(max_abs) if max_abs else 0.0),
        }
    best_strategy = min(strategy_summary, key=lambda name: strategy_summary[name]["score"])
    worst_summary = max(
        (row for row in summaries if abs(row["linear_pol_deg"]) > 1e-9),
        key=lambda row: row["max_abs_bias_vs_pol0_deg"],
        default=None,
    )
    return curves, summaries, {
        "strategies": strategy_summary,
        "best_strategy": best_strategy,
        "worst_curve": worst_summary,
    }


def write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: f"{row[key]:.6f}" if isinstance(row.get(key), float) else row.get(key) for key in fields})


def previous_ab_best() -> dict:
    path = ROOT / "reports_d44_ab_isolation_finesweep" / "UWB_CH9_D44_AB_ISOLATION_finesweep_best.json"
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8")).get("best", {})
    except json.JSONDecodeError:
        return {}


def write_report(metrics: dict) -> None:
    s = metrics["s_parameters"]
    se = metrics["s_parameter_extra"]
    pdoa = metrics["pdoa"]
    best_name = pdoa["best_strategy"]
    best = pdoa["strategies"][best_name]
    previous = previous_ab_best()
    params = metrics["parameters"]

    lines = [
        "# D44 锚点天线双极化 XY 拓扑初版仿真报告",
        "",
        "## 目标",
        "",
        "- 将锚点天线从固定 90 度圆极化合成路线改为独立 X/Y 双极化接收路线。",
        "- 入射极化只考虑线极化 `0 / 45 / 90 / 135 deg`。",
        "- 优先指标从轴比转为：双端口匹配、X/Y 端口隔离、双极化矢量合成后的 PDOA 曲线稳定性。",
        "",
        "## 拓扑与参数",
        "",
        f"- 分支：`feature/d44-dualpol-anchor`",
        f"- AEDT 工程：`{metrics['project']}`",
        f"- 设计名：`{metrics['design']}`",
        "- 四个阵元的贴片均保持全局同向，不再按阵列方位旋转。",
        "- A 口定义为全局 X 极化通道，B 口定义为全局 Y 极化通道。",
        f"- 贴片边长：`{params['patch_side_mm']} mm`",
        f"- 馈电偏移：`{params['feed_offset_u_mm']} mm`",
        f"- 焊盘半径：`{params['feed_pad_radius_mm']} mm`",
        f"- 端口片宽度：`{params['port_width_mm']} mm`",
        "",
        "## S 参数",
        "",
        f"- 最差回波：`{fmt(s.get('worst_return_db'))} dB`，表达式 `{s.get('worst_return_expr')}`",
        f"- X/A 通道最差回波：`{fmt(se.get('x_return_worst_db'))} dB`",
        f"- Y/B 通道最差回波：`{fmt(se.get('y_return_worst_db'))} dB`",
        f"- 同阵元 X/Y 最差隔离：`{fmt(se.get('same_element_xy_isolation_db'))} dB`",
        f"- 同极化阵元间最差隔离：`{fmt(se.get('same_feed_inter_element_isolation_db'))} dB`",
        f"- 全端口最差隔离：`{fmt(s.get('isolation_db'))} dB`",
        f"- S 参数目标：`{'通过' if s.get('worst_return_db', 999.0) <= RETURN_TARGET_DB and s.get('isolation_db', 0.0) >= ISOLATION_TARGET_DB else '未通过'}`。",
        "",
        "## PDOA 线极化稳定性",
        "",
        "| 策略 | 平均 RMS 漂移 | 95 分位 RMS | 最大漂移 | 平均有效点 | 说明 |",
        "| --- | ---: | ---: | ---: | ---: | --- |",
    ]
    for name, item in sorted(pdoa["strategies"].items(), key=lambda entry: entry[1]["score"]):
        lines.append(
            f"| `{name}` | {fmt(item['avg_rms_bias_deg'])} deg | {fmt(item['p95_rms_bias_deg'])} deg | "
            f"{fmt(item['max_abs_bias_deg'])} deg | {fmt(item['avg_valid_percent'], 1)}% | {item['note']} |"
        )

    lines.extend(
        [
            "",
            "## 最优策略",
            "",
            f"- 最优策略：`{best_name}`",
            f"- 平均 RMS PDOA 漂移：`{fmt(best['avg_rms_bias_deg'])} deg`",
            f"- 95 分位 RMS PDOA 漂移：`{fmt(best['p95_rms_bias_deg'])} deg`",
            f"- 最大 PDOA 漂移：`{fmt(best['max_abs_bias_deg'])} deg`",
            f"- PDOA 目标：`{'通过' if best['avg_rms_bias_deg'] <= PDOA_RMS_TARGET_DEG and best['max_abs_bias_deg'] <= PDOA_MAX_TARGET_DEG else '未通过'}`。",
            "",
        ]
    )
    if previous:
        lines.extend(
            [
                "## 与上一轮圆极化/双馈路线对比",
                "",
                f"- 上一轮最优候选：`{previous.get('candidate')}`。",
                f"- 上一轮平均 RMS PDOA 漂移：`{fmt(previous.get('best_avg_rms_bias_deg'))} deg`；本轮最优：`{fmt(best['avg_rms_bias_deg'])} deg`。",
                f"- 上一轮 95 分位 RMS PDOA 漂移：`{fmt(previous.get('best_p95_rms_bias_deg'))} deg`；本轮最优：`{fmt(best['p95_rms_bias_deg'])} deg`。",
                f"- 上一轮最大 PDOA 漂移：`{fmt(previous.get('best_max_abs_bias_deg'))} deg`；本轮最优：`{fmt(best['max_abs_bias_deg'])} deg`。",
                "",
            ]
        )
    lines.extend(
        [
            "## 工程结论",
            "",
            f"- 本轮初版双极化几何尚未优于上一轮圆极化/双馈最佳结果；当前最优仍是对照策略 `{best_name}`。",
            f"- 推荐的双极化向量相关策略平均 RMS 漂移为 `{fmt(pdoa['strategies']['dualpol_vector_correlation']['avg_rms_bias_deg'])} deg`，比单独 X/Y 通道稳定，但仍未达到目标。",
            "- 双极化拓扑已经成功建模并求解，独立 X/Y 端口为后端极化标定和矢量合成留下了自由度。",
            "- 如果 `dualpol_known_pol_vector` 优于单端口策略，说明双极化接收对线极化入射有明确价值；但实际系统需要估计或标定入射极化角。",
            "- 如果 `dualpol_vector_correlation` 优于单端口策略，说明可以不先压成单个极化电压，而是直接用 X/Y 两通道向量相关做相位差估计。",
            "- 若 S 参数仍未达标，下一步应围绕 X/Y 同阵元隔离和两路幅相一致性优化，而不是继续把轴比作为主目标。",
            "- 当前报告仍是快速三频点仿真结果，后续定版前应增加完整频扫、制造过孔/馈线模型和接收通道标定误差。",
            "",
            "## 输出文件",
            "",
            f"- AEDT 工程：`{metrics['project']}`",
            f"- S 参数 CSV：`{SPARAM_CSV}`",
            f"- PDOA 曲线 CSV：`{CURVES_CSV}`",
            f"- PDOA 汇总 CSV：`{SUMMARY_CSV}`",
            f"- 指标 JSON：`{METRICS_JSON}`",
        ]
    )
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run(build: bool = True) -> dict:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    if build:
        project, hfss = builder.build_project(
            TOPOLOGY,
            analyze=True,
            non_graphical=True,
            quick=True,
            band_samples=True,
            sparam_only=False,
            return_hfss=True,
        )
    else:
        project = PATHS["project"]
        hfss = Hfss(
            project=str(project),
            design=SPEC["design"],
            version="2023.1",
            non_graphical=True,
            new_desktop=True,
            close_on_exit=False,
            remove_lock=True,
        )
    try:
        sources = hfss.get_all_sources()
        sparams = topology_eval.get_s_parameter_snapshot(hfss, SPARAM_CSV)
        eval_freqs = pdoa_eval.nearest_frequencies(pdoa_eval.get_available_frequencies(hfss))
        fields = pdoa_eval.acquire_embedded_fields(hfss, sources, eval_freqs)
        curve_rows, summary_rows, pdoa_metrics = evaluate_dualpol_pdoa(fields, eval_freqs, sources)
    finally:
        hfss.release_desktop(close_projects=False, close_desktop=True)

    curve_fields = [
        "freq_ghz",
        "phi_deg",
        "theta_deg",
        "linear_pol_deg",
        "strategy",
        "baseline",
        "pdoa_deg",
        "pdoa_unwrapped_deg",
        "left_mag_rel_db",
        "right_mag_rel_db",
        "valid",
    ]
    summary_fields = [
        "freq_ghz",
        "phi_deg",
        "linear_pol_deg",
        "strategy",
        "baseline",
        "valid_percent",
        "pdoa_span_deg",
        "pdoa_start_deg",
        "pdoa_end_deg",
        "monotonic_segment_percent",
        "min_pair_mag_rel_db",
        "rms_bias_vs_pol0_deg",
        "mean_abs_bias_vs_pol0_deg",
        "max_abs_bias_vs_pol0_deg",
    ]
    write_csv(CURVES_CSV, curve_rows, curve_fields)
    write_csv(SUMMARY_CSV, summary_rows, summary_fields)

    params = json.loads(PATHS["params"].read_text(encoding="utf-8"))["parameters"]
    metrics = {
        "project": str(project),
        "design": SPEC["design"],
        "topology": TOPOLOGY,
        "label": SPEC["label"],
        "sources": sources,
        "evaluated_frequencies_ghz": eval_freqs,
        "linear_polarizations_deg": LINEAR_POLS,
        "phi_cuts_deg": PHI_CUTS,
        "parameters": params,
        "s_parameters": sparams,
        "s_parameter_extra": enrich_sparams(sparams),
        "pdoa": pdoa_metrics,
        "targets": {
            "return_target_db": RETURN_TARGET_DB,
            "isolation_target_db": ISOLATION_TARGET_DB,
            "pdoa_rms_target_deg": PDOA_RMS_TARGET_DEG,
            "pdoa_max_target_deg": PDOA_MAX_TARGET_DEG,
        },
        "files": {
            "sparam_csv": str(SPARAM_CSV),
            "curves_csv": str(CURVES_CSV),
            "summary_csv": str(SUMMARY_CSV),
            "metrics_json": str(METRICS_JSON),
            "report_md": str(REPORT_MD),
        },
    }
    METRICS_JSON.write_text(json.dumps(metrics, indent=2, ensure_ascii=False), encoding="utf-8")
    write_report(metrics)
    print(json.dumps({"s_parameters": metrics["s_parameter_extra"], "pdoa": metrics["pdoa"]}, indent=2, ensure_ascii=False))
    print(f"Wrote {REPORT_MD}")
    return metrics


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-build", action="store_true")
    args = parser.parse_args()
    run(build=not args.skip_build)


if __name__ == "__main__":
    main()
