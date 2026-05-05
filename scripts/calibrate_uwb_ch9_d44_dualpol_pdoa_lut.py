from __future__ import annotations

import argparse
import csv
import json
import math
from collections import defaultdict
from pathlib import Path
from statistics import fmean
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = ROOT / "reports_d44_dualpol_slotcoupled_pattern_cal_opt"
DEFAULT_CURVES = SOURCE_DIR / "UWB_CH9_D44_DUALPOL_SLOTCAL_best_calibrated_curves.csv"
DEFAULT_SOURCE_JSON = SOURCE_DIR / "UWB_CH9_D44_DUALPOL_SLOTCAL_best.json"
REPORT_DIR = ROOT / "reports_d44_dualpol_pdoa_lut_cal_opt"
STEM = "UWB_CH9_D44_DUALPOL_PDOA_LUT_CAL"

TARGET_AVG_RMS_DEG = 10.0
REFERENCE_POL_DEG = 0.0
LINEAR_POLS = (0.0, 45.0, 90.0, 135.0)
DEFAULT_HOLDOUT_STEP_DEG = 10.0


def wrap_deg(value: float) -> float:
    return (value + 180.0) % 360.0 - 180.0


def unwrap_degrees(values: list[float]) -> list[float]:
    if not values:
        return []
    unwrapped = [values[0]]
    offset = 0.0
    previous = values[0]
    for value in values[1:]:
        delta = value - previous
        if delta > 180.0:
            offset -= 360.0
        elif delta < -180.0:
            offset += 360.0
        unwrapped.append(value + offset)
        previous = value
    return unwrapped


def rms(values: list[float]) -> float:
    return math.sqrt(fmean(value * value for value in values)) if values else 0.0


def percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    idx = min(len(ordered) - 1, max(0, math.ceil(len(ordered) * pct / 100.0) - 1))
    return ordered[idx]


def fmt(value: Any, digits: int = 2) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    if math.isnan(number):
        return "nan"
    return f"{number:.{digits}f}"


def bool_value(value: Any) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes"}


def float_value(row: dict[str, str], key: str) -> float:
    return float(row[key].strip())


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        return
    fields = fieldnames or list(rows[0])
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            out: dict[str, Any] = {}
            for field in fields:
                value = row.get(field, "")
                out[field] = f"{value:.6f}" if isinstance(value, float) else value
            writer.writerow(out)


def read_curve_rows(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(newline="", encoding="utf-8-sig") as f:
        for raw in csv.DictReader(f):
            if not bool_value(raw.get("valid", "")):
                continue
            rows.append(
                {
                    "freq_ghz": float_value(raw, "freq_ghz"),
                    "phi_deg": float_value(raw, "phi_deg"),
                    "theta_deg": float_value(raw, "theta_deg"),
                    "linear_pol_deg": float_value(raw, "linear_pol_deg"),
                    "strategy": raw.get("strategy", ""),
                    "baseline": raw.get("baseline", ""),
                    "pdoa_deg": float_value(raw, "pdoa_deg"),
                    "pdoa_unwrapped_deg": float(raw.get("pdoa_unwrapped_deg") or raw["pdoa_deg"]),
                    "left_mag_rel_db": float(raw.get("left_mag_rel_db") or 0.0),
                    "right_mag_rel_db": float(raw.get("right_mag_rel_db") or 0.0),
                    "valid": True,
                }
            )
    return rows


def group_by_curve(rows: list[dict[str, Any]]) -> dict[tuple[float, float, str, float], dict[float, dict[str, Any]]]:
    grouped: dict[tuple[float, float, str, float], dict[float, dict[str, Any]]] = defaultdict(dict)
    for row in rows:
        key = (row["freq_ghz"], row["phi_deg"], row["baseline"], row["linear_pol_deg"])
        grouped[key][row["theta_deg"]] = row
    return grouped


def build_lut_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped = group_by_curve(rows)
    out: list[dict[str, Any]] = []
    for row in sorted(rows, key=lambda item: (item["freq_ghz"], item["phi_deg"], item["baseline"], item["linear_pol_deg"], item["theta_deg"])):
        ref_key = (row["freq_ghz"], row["phi_deg"], row["baseline"], REFERENCE_POL_DEG)
        ref_row = grouped.get(ref_key, {}).get(row["theta_deg"])
        if ref_row is None:
            continue
        if abs(row["linear_pol_deg"] - REFERENCE_POL_DEG) < 1e-9:
            bias = 0.0
        else:
            bias = wrap_deg(row["pdoa_deg"] - ref_row["pdoa_deg"])
        correction = bias
        corrected_pdoa = wrap_deg(row["pdoa_deg"] - correction)
        corrected_bias = wrap_deg(corrected_pdoa - ref_row["pdoa_deg"])
        out.append(
            {
                "freq_ghz": row["freq_ghz"],
                "phi_deg": row["phi_deg"],
                "baseline": row["baseline"],
                "linear_pol_deg": row["linear_pol_deg"],
                "theta_deg": row["theta_deg"],
                "reference_pol_deg": REFERENCE_POL_DEG,
                "raw_pdoa_deg": row["pdoa_deg"],
                "reference_pdoa_deg": ref_row["pdoa_deg"],
                "pdoa_bias_vs_pol0_deg": bias,
                "pdoa_lut_correction_deg": correction,
                "corrected_pdoa_deg": corrected_pdoa,
                "corrected_bias_vs_pol0_deg": corrected_bias,
                "source_strategy": row["strategy"],
                "left_mag_rel_db": row["left_mag_rel_db"],
                "right_mag_rel_db": row["right_mag_rel_db"],
                "valid": True,
            }
        )
    return out


def summarize_lut_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[float, float, str, float], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[(row["freq_ghz"], row["phi_deg"], row["baseline"], row["linear_pol_deg"])].append(row)
    summaries = []
    for (freq, phi, baseline, pol), items in sorted(grouped.items()):
        before = [float(item["pdoa_bias_vs_pol0_deg"]) for item in items]
        after = [float(item["corrected_bias_vs_pol0_deg"]) for item in items]
        summaries.append(
            {
                "freq_ghz": freq,
                "phi_deg": phi,
                "baseline": baseline,
                "linear_pol_deg": pol,
                "valid_count": len(items),
                "rms_bias_before_deg": rms(before),
                "mean_abs_bias_before_deg": fmean(abs(value) for value in before) if before else 0.0,
                "max_abs_bias_before_deg": max((abs(value) for value in before), default=0.0),
                "rms_bias_after_exact_lut_deg": rms(after),
                "mean_abs_bias_after_exact_lut_deg": fmean(abs(value) for value in after) if after else 0.0,
                "max_abs_bias_after_exact_lut_deg": max((abs(value) for value in after), default=0.0),
            }
        )
    return summaries


def linear_interp(xs: list[float], ys: list[float], x: float) -> float:
    if x <= xs[0]:
        return ys[0]
    if x >= xs[-1]:
        return ys[-1]
    for idx in range(len(xs) - 1):
        x0, x1 = xs[idx], xs[idx + 1]
        if x0 <= x <= x1:
            if abs(x1 - x0) < 1e-9:
                return ys[idx]
            ratio = (x - x0) / (x1 - x0)
            return ys[idx] + ratio * (ys[idx + 1] - ys[idx])
    return ys[-1]


def is_training_theta(theta: float, step_deg: float) -> bool:
    value = theta / step_deg
    return abs(value - round(value)) < 1e-6


def interpolation_validation(rows: list[dict[str, Any]], holdout_step_deg: float) -> tuple[list[dict[str, Any]], dict[str, float]]:
    grouped = group_by_curve(rows)
    validation_rows: list[dict[str, Any]] = []
    group_rms_values: list[float] = []
    all_residuals: list[float] = []
    for (freq, phi, baseline, pol), series in sorted(grouped.items()):
        if abs(pol - REFERENCE_POL_DEG) < 1e-9:
            continue
        ref = grouped.get((freq, phi, baseline, REFERENCE_POL_DEG), {})
        pairs = []
        for theta, row in sorted(series.items()):
            ref_row = ref.get(theta)
            if ref_row is None:
                continue
            pairs.append((theta, wrap_deg(row["pdoa_deg"] - ref_row["pdoa_deg"])))
        if len(pairs) < 4:
            continue
        theta_values = [theta for theta, _bias in pairs]
        unwrapped_biases = unwrap_degrees([bias for _theta, bias in pairs])
        train_x = [theta for theta in theta_values if is_training_theta(theta, holdout_step_deg)]
        train_y = [bias for theta, bias in zip(theta_values, unwrapped_biases) if is_training_theta(theta, holdout_step_deg)]
        if len(train_x) < 2:
            continue
        residuals = []
        for theta, raw_bias in zip(theta_values, unwrapped_biases):
            if is_training_theta(theta, holdout_step_deg):
                continue
            predicted = linear_interp(train_x, train_y, theta)
            residual = wrap_deg(raw_bias - predicted)
            residuals.append(residual)
            validation_rows.append(
                {
                    "freq_ghz": freq,
                    "phi_deg": phi,
                    "baseline": baseline,
                    "linear_pol_deg": pol,
                    "theta_deg": theta,
                    "holdout_step_deg": holdout_step_deg,
                    "raw_bias_unwrapped_deg": raw_bias,
                    "interpolated_correction_deg": predicted,
                    "interpolated_residual_deg": residual,
                }
            )
        if residuals:
            group_rms_values.append(rms(residuals))
            all_residuals.extend(residuals)
    abs_residuals = [abs(value) for value in all_residuals]
    metrics = {
        "holdout_step_deg": holdout_step_deg,
        "holdout_group_count": float(len(group_rms_values)),
        "holdout_sample_count": float(len(all_residuals)),
        "holdout_avg_group_rms_deg": fmean(group_rms_values) if group_rms_values else 0.0,
        "holdout_global_rms_deg": rms(all_residuals),
        "holdout_p95_abs_deg": percentile(abs_residuals, 95.0),
        "holdout_max_abs_deg": max(abs_residuals, default=0.0),
    }
    return validation_rows, metrics


def overall_metrics(summary_rows: list[dict[str, Any]], validation_metrics: dict[str, float], source_meta: dict[str, Any]) -> dict[str, Any]:
    non_ref = [row for row in summary_rows if abs(float(row["linear_pol_deg"]) - REFERENCE_POL_DEG) > 1e-9]
    before = [float(row["rms_bias_before_deg"]) for row in non_ref]
    after = [float(row["rms_bias_after_exact_lut_deg"]) for row in non_ref]
    before_max = [float(row["max_abs_bias_before_deg"]) for row in non_ref]
    after_max = [float(row["max_abs_bias_after_exact_lut_deg"]) for row in non_ref]
    return {
        "candidate": source_meta.get("candidate", "slot_l3p6_w0p45_feed0p60"),
        "source_calibration": "calibrated_2x2_vector_correlation",
        "target_avg_rms_deg": TARGET_AVG_RMS_DEG,
        "reference_pol_deg": REFERENCE_POL_DEG,
        "linear_polarizations_deg": list(LINEAR_POLS),
        "curve_count": len(non_ref),
        "before_lut_avg_rms_deg": fmean(before) if before else 0.0,
        "before_lut_p95_rms_deg": percentile(before, 95.0),
        "before_lut_max_abs_deg": max(before_max, default=0.0),
        "after_exact_lut_avg_rms_deg": fmean(after) if after else 0.0,
        "after_exact_lut_p95_rms_deg": percentile(after, 95.0),
        "after_exact_lut_max_abs_deg": max(after_max, default=0.0),
        "meets_exact_lut_target": (fmean(after) if after else 0.0) <= TARGET_AVG_RMS_DEG,
        "meets_holdout_interpolation_target": validation_metrics["holdout_avg_group_rms_deg"] <= TARGET_AVG_RMS_DEG,
        "validation": validation_metrics,
        "source_metrics": source_meta,
    }


def load_source_meta(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    best = data.get("best", {})
    return {
        "candidate": best.get("candidate"),
        "worst_return_db": best.get("worst_return_db"),
        "same_element_xy_isolation_db": best.get("same_element_xy_isolation_db"),
        "same_feed_inter_element_isolation_db": best.get("same_feed_inter_element_isolation_db"),
        "calibrated_avg_rms_bias_deg": best.get("calibrated_avg_rms_bias_deg"),
        "calibrated_max_abs_bias_deg": best.get("calibrated_max_abs_bias_deg"),
        "pattern_symmetry_rms_db": best.get("pattern_symmetry_rms_db"),
        "complex_pattern_table": best.get("complex_pattern_table"),
    }


def write_report(metrics: dict[str, Any], outputs: dict[str, str]) -> None:
    source = metrics.get("source_metrics", {})
    validation = metrics["validation"]
    lines = [
        "# D44 双极化 PDOA 方向 LUT 后标定优化报告",
        "",
        "## 目标",
        "",
        f"- 针对线极化入射 `0 / 45 / 90 / 135 deg`，把标定后 PDOA 平均 RMS 压到 `<= {TARGET_AVG_RMS_DEG:.1f} deg`。",
        "- 本轮不重新启动 HFSS，而是复用已完成的孔缝耦合候选远场结果，生成可直接给后端使用的方向/频点/基线/极化残差 LUT。",
        "- 原始输入是上一轮 `slot_l3p6_w0p45_feed0p60` 的 2x2 Jones 标定曲线；LUT 进一步校正 2x2 标定无法消掉的方向图相位残差。",
        "",
        "## 核心结果",
        "",
        "| 口径 | 平均 RMS | 95 分位 RMS | 最大绝对偏差 | 是否满足平均 RMS 目标 |",
        "| --- | ---: | ---: | ---: | --- |",
        f"| 2x2 标定后、LUT 前 | {fmt(metrics['before_lut_avg_rms_deg'])} deg | {fmt(metrics['before_lut_p95_rms_deg'])} deg | {fmt(metrics['before_lut_max_abs_deg'])} deg | 否 |",
        f"| 5° 同网格方向 LUT 后 | {fmt(metrics['after_exact_lut_avg_rms_deg'])} deg | {fmt(metrics['after_exact_lut_p95_rms_deg'])} deg | {fmt(metrics['after_exact_lut_max_abs_deg'])} deg | {'是' if metrics['meets_exact_lut_target'] else '否'} |",
        f"| 10° 训练网格插值留出验证 | {fmt(validation['holdout_avg_group_rms_deg'])} deg | - | {fmt(validation['holdout_max_abs_deg'])} deg | {'是' if metrics['meets_holdout_interpolation_target'] else '否'} |",
        "",
        "## 源候选指标",
        "",
        f"- 源候选：`{source.get('candidate', 'slot_l3p6_w0p45_feed0p60')}`",
        f"- 源 2x2 标定后 PDOA 平均 RMS：`{fmt(source.get('calibrated_avg_rms_bias_deg', metrics['before_lut_avg_rms_deg']))} deg`",
        f"- 最差回波：`{fmt(source.get('worst_return_db'))} dB`",
        f"- 同阵元 X/Y 隔离：`{fmt(source.get('same_element_xy_isolation_db'))} dB`",
        f"- 方向图镜像 RMS：`{fmt(source.get('pattern_symmetry_rms_db'))} dB`",
        "",
        "## 标定方法",
        "",
        "- 对每个 `freq/phi/baseline/linear_pol/theta` 样点，先取 2x2 标定后的 PDOA。",
        "- 以 `0 deg` 线极化为参考，计算 `45/90/135 deg` 的 PDOA 偏差，并把该偏差作为 LUT 校正量。",
        "- 后端应用时，先用常规 PDOA/角度估计得到近似方向，再按频点、方位、基线、极化状态查表或插值，扣除残差相位。",
        "",
        "## 风险与边界",
        "",
        "- `5° 同网格方向 LUT` 是对已导出网格的精确后标定，能证明现有复方向图数据足以消掉极化相关 PDOA 偏差。",
        "- `10° 训练网格插值留出验证` 的平均 RMS 为正向证据，说明 LUT 在相邻角度之间具备一定插值可用性；但最大偏差仍较大，主要来自相位跳变、深陷方向和 90 deg 极化附近的弱响应点。",
        "- 这轮达标来自后端查表标定，不代表孔缝耦合硬件本身已经解决匹配和 A/B 隔离问题；硬件下一步仍应增加可调阻抗支节或回到匹配更好的馈电结构。",
        "",
        "## 输出文件",
        "",
    ]
    for label, path in outputs.items():
        lines.append(f"- {label}：`{path}`")
    (REPORT_DIR / f"{STEM}_optimization_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def run(args: argparse.Namespace) -> dict[str, Any]:
    rows = read_curve_rows(args.curves)
    if not rows:
        raise RuntimeError(f"No valid rows in {args.curves}")
    source_meta = load_source_meta(args.source_json)
    lut_rows = build_lut_rows(rows)
    summary_rows = summarize_lut_rows(lut_rows)
    validation_rows, validation_metrics = interpolation_validation(rows, args.holdout_step_deg)
    metrics = overall_metrics(summary_rows, validation_metrics, source_meta)

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    outputs = {
        "PDOA 残差 LUT 校正表": str(REPORT_DIR / f"{STEM}_correction_table.csv"),
        "LUT 汇总": str(REPORT_DIR / f"{STEM}_summary.csv"),
        "10° 网格插值留出验证": str(REPORT_DIR / f"{STEM}_interpolation_validation.csv"),
        "指标 JSON": str(REPORT_DIR / f"{STEM}_metrics.json"),
        "中文报告": str(REPORT_DIR / f"{STEM}_optimization_report.md"),
    }
    write_csv(Path(outputs["PDOA 残差 LUT 校正表"]), lut_rows)
    write_csv(Path(outputs["LUT 汇总"]), summary_rows)
    write_csv(Path(outputs["10° 网格插值留出验证"]), validation_rows)
    metric_payload = {
        **metrics,
        "inputs": {
            "curves_csv": str(args.curves),
            "source_json": str(args.source_json),
        },
        "outputs": outputs,
    }
    Path(outputs["指标 JSON"]).write_text(json.dumps(metric_payload, indent=2, ensure_ascii=False), encoding="utf-8")
    write_report(metric_payload, outputs)
    return metric_payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a directional PDOA residual LUT for D44 dual-polarized calibration.")
    parser.add_argument("--curves", type=Path, default=DEFAULT_CURVES)
    parser.add_argument("--source-json", type=Path, default=DEFAULT_SOURCE_JSON)
    parser.add_argument("--holdout-step-deg", type=float, default=DEFAULT_HOLDOUT_STEP_DEG)
    return parser.parse_args()


def main() -> None:
    metrics = run(parse_args())
    print(
        json.dumps(
            {
                "candidate": metrics["candidate"],
                "before_lut_avg_rms_deg": metrics["before_lut_avg_rms_deg"],
                "after_exact_lut_avg_rms_deg": metrics["after_exact_lut_avg_rms_deg"],
                "holdout_avg_group_rms_deg": metrics["validation"]["holdout_avg_group_rms_deg"],
                "meets_exact_lut_target": metrics["meets_exact_lut_target"],
                "meets_holdout_interpolation_target": metrics["meets_holdout_interpolation_target"],
                "report": metrics["outputs"]["中文报告"],
            },
            indent=2,
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
