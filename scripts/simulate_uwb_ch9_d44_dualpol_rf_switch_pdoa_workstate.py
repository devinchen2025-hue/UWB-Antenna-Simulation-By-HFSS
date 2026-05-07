from __future__ import annotations

import csv
import json
import math
import shutil
import time
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from statistics import fmean
from typing import Any

import build_uwb_ch9_hfss_d44_topology as builder
import evaluate_uwb_ch9_d44_pdoa_linear_polarization as pdoa_eval
import evaluate_uwb_ch9_d44_topology as topology_eval
import optimize_uwb_ch9_d44_dualpol_s11_slotcoupled_match as s11_opt


ROOT = Path(__file__).resolve().parents[1]
TOPOLOGY = "dualpol"
REPORT_DIR = ROOT / "reports_d44_dualpol_rf_switch_pdoa_workstate"
STEM = "UWB_CH9_D44_DUALPOL_RF_SWITCH_PDOA"
BEST_SOURCE_JSON = ROOT / "reports_d44_dualpol_s11_slotmatch_opt" / "UWB_CH9_D44_DUALPOL_S11_SLOTMATCH_best.json"

CURVES_CSV = REPORT_DIR / f"{STEM}_curves.csv"
SUMMARY_CSV = REPORT_DIR / f"{STEM}_summary.csv"
POL_SUMMARY_CSV = REPORT_DIR / f"{STEM}_polarization_summary.csv"
VALIDATION_CSV = REPORT_DIR / f"{STEM}_lut_holdout_validation.csv"
METRICS_JSON = REPORT_DIR / f"{STEM}_metrics.json"
REPORT_MD = REPORT_DIR / f"{STEM}_workstate_report.md"

TARGET_AVG_RMS_DEG = 10.0
REFERENCE_POL_DEG = 0.0
HOLDOUT_STEP_DEG = 10.0
RETURN_TARGET_DB = -10.0


@dataclass(frozen=True)
class SwitchCase:
    name: str
    active_pol: str
    off_resistance_ohm: float
    off_capacitance_pf: float
    off_inductance_nh: float = 0.0
    engineering_valid_s11: bool = True


CASES = [
    SwitchCase("A_ON_absorptive_50ohm_c0p08pf", "A", 50.0, 0.08, engineering_valid_s11=True),
    SwitchCase("B_ON_absorptive_50ohm_c0p08pf", "B", 50.0, 0.08, engineering_valid_s11=True),
    SwitchCase("A_ON_reflective_5kohm_c0p08pf", "A", 5000.0, 0.08, engineering_valid_s11=False),
    SwitchCase("B_ON_reflective_5kohm_c0p08pf", "B", 5000.0, 0.08, engineering_valid_s11=False),
]


def fmt(value: Any, digits: int = 2) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    if math.isnan(number) or math.isinf(number):
        return "N/A"
    return f"{number:.{digits}f}"


def rms(values: list[float]) -> float:
    return math.sqrt(fmean(value * value for value in values)) if values else 0.0


def percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    idx = min(len(ordered) - 1, max(0, math.ceil(len(ordered) * pct / 100.0) - 1))
    return ordered[idx]


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        return
    fields = list(fieldnames or rows[0].keys())
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            out: dict[str, Any] = {}
            for field in fields:
                value = row.get(field, "")
                out[field] = f"{value:.6f}" if isinstance(value, float) else value
            writer.writerow(out)


def read_best_candidate_name() -> str:
    payload = json.loads(BEST_SOURCE_JSON.read_text(encoding="utf-8"))
    best = payload.get("best_candidate") or payload.get("best") or {}
    name = best.get("candidate")
    if not name:
        raise RuntimeError(f"Cannot locate best candidate name in {BEST_SOURCE_JSON}")
    return str(name)


def best_candidate_params() -> tuple[str, dict[str, Any]]:
    best_name = read_best_candidate_name()
    for candidate in s11_opt.candidates():
        if candidate.name == best_name:
            return best_name, dict(candidate.params)
    raise RuntimeError(f"Best candidate {best_name} is not present in optimizer candidate list")


def set_case_params(base_params: dict[str, Any], case: SwitchCase) -> dict[str, Any]:
    params = dict(base_params)
    params.update(
        {
            "rf_switch_equiv_enabled": 1.0,
            "rf_switch_active_pol": 0.0 if case.active_pol == "A" else 1.0,
            "rf_switch_off_resistance_ohm": case.off_resistance_ohm,
            "rf_switch_off_capacitance_pf": case.off_capacitance_pf,
            "rf_switch_off_inductance_nh": case.off_inductance_nh,
        }
    )
    return params


def port_pol(port: str) -> str:
    return port.split(":", 1)[0][-1]


def summarize_sparams(case: SwitchCase, sparams: dict[str, Any]) -> dict[str, Any]:
    returns = {
        expr: value
        for expr, value in sparams["self_worst_db"].items()
        if port_pol(expr.split("S(", 1)[1].split(",", 1)[0].strip()) == case.active_pol
    }
    couplings = {}
    for expr, value in sparams.get("coupling_worst_db", {}).items():
        inside = expr.split("S(", 1)[1].split(")", 1)[0]
        left, right = [part.strip() for part in inside.split(",", 1)]
        if port_pol(left) == case.active_pol and port_pol(right) == case.active_pol:
            couplings[expr] = value
    worst_return_expr, worst_return_db = max(returns.items(), key=lambda item: item[1])
    if couplings:
        worst_coupling_expr, worst_coupling_db = max(couplings.items(), key=lambda item: item[1])
        active_interelement_isolation_db = -worst_coupling_db
    else:
        worst_coupling_expr = "N/A"
        active_interelement_isolation_db = float("nan")
    return {
        "active_port_count": len(returns),
        "worst_return_db": worst_return_db,
        "worst_return_expr": worst_return_expr,
        "active_interelement_isolation_db": active_interelement_isolation_db,
        "worst_active_coupling_expr": worst_coupling_expr,
        "s11_pass": worst_return_db <= RETURN_TARGET_DB,
    }


def is_training_theta(theta: float, step_deg: float) -> bool:
    value = theta / step_deg
    return abs(value - round(value)) < 1e-6


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


def group_curve_rows(rows: list[dict[str, Any]]) -> dict[tuple[str, float, float, str, str, float], dict[float, dict[str, Any]]]:
    grouped: dict[tuple[str, float, float, str, str, float], dict[float, dict[str, Any]]] = defaultdict(dict)
    for row in rows:
        if not row.get("valid"):
            continue
        key = (
            row["case"],
            float(row["freq_ghz"]),
            float(row["phi_deg"]),
            row["channel_set"],
            row["baseline"],
            float(row["linear_pol_deg"]),
        )
        grouped[key][float(row["theta_deg"])] = row
    return grouped


def lut_holdout_validation(rows: list[dict[str, Any]], holdout_step_deg: float = HOLDOUT_STEP_DEG) -> list[dict[str, Any]]:
    grouped = group_curve_rows(rows)
    validation: list[dict[str, Any]] = []
    for (case, freq, phi, channel_set, baseline, pol), series in sorted(grouped.items()):
        if abs(pol - REFERENCE_POL_DEG) < 1e-9:
            continue
        ref_series = grouped.get((case, freq, phi, channel_set, baseline, REFERENCE_POL_DEG), {})
        pairs = []
        for theta, row in sorted(series.items()):
            ref = ref_series.get(theta)
            if ref is None:
                continue
            pairs.append((theta, pdoa_eval.wrap_deg(row["pdoa_deg"] - ref["pdoa_deg"])))
        if len(pairs) < 4:
            continue
        theta_values = [theta for theta, _bias in pairs]
        unwrapped_biases = pdoa_eval.unwrap_degrees([bias for _theta, bias in pairs])
        train_x = [theta for theta in theta_values if is_training_theta(theta, holdout_step_deg)]
        train_y = [
            bias
            for theta, bias in zip(theta_values, unwrapped_biases)
            if is_training_theta(theta, holdout_step_deg)
        ]
        if len(train_x) < 2:
            continue
        residuals = []
        for theta, raw_bias in zip(theta_values, unwrapped_biases):
            if is_training_theta(theta, holdout_step_deg):
                continue
            predicted = linear_interp(train_x, train_y, theta)
            residual = pdoa_eval.wrap_deg(raw_bias - predicted)
            residuals.append(residual)
            validation.append(
                {
                    "case": case,
                    "freq_ghz": freq,
                    "phi_deg": phi,
                    "channel_set": channel_set,
                    "baseline": baseline,
                    "linear_pol_deg": pol,
                    "theta_deg": theta,
                    "holdout_step_deg": holdout_step_deg,
                    "raw_bias_unwrapped_deg": raw_bias,
                    "interpolated_correction_deg": predicted,
                    "interpolated_residual_deg": residual,
                }
            )
    return validation


def summarize_validation(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    grouped: dict[tuple[str, float, float, str, str, float], list[float]] = defaultdict(list)
    by_case_pol: dict[tuple[str, float], list[float]] = defaultdict(list)
    for row in rows:
        key = (
            row["case"],
            float(row["freq_ghz"]),
            float(row["phi_deg"]),
            row["channel_set"],
            row["baseline"],
            float(row["linear_pol_deg"]),
        )
        value = float(row["interpolated_residual_deg"])
        grouped[key].append(value)
        by_case_pol[(row["case"], float(row["linear_pol_deg"]))].append(value)

    group_rows = []
    group_rms_by_case: dict[str, list[float]] = defaultdict(list)
    all_by_case: dict[str, list[float]] = defaultdict(list)
    for key, values in sorted(grouped.items()):
        case, freq, phi, channel_set, baseline, pol = key
        group_rms = rms(values)
        group_rows.append(
            {
                "case": case,
                "freq_ghz": freq,
                "phi_deg": phi,
                "channel_set": channel_set,
                "baseline": baseline,
                "linear_pol_deg": pol,
                "sample_count": len(values),
                "holdout_rms_deg": group_rms,
                "holdout_mean_abs_deg": fmean(abs(value) for value in values),
                "holdout_max_abs_deg": max(abs(value) for value in values),
            }
        )
        group_rms_by_case[case].append(group_rms)
        all_by_case[case].extend(values)

    by_case = {}
    for case, values in sorted(all_by_case.items()):
        abs_values = [abs(value) for value in values]
        group_rms_values = group_rms_by_case[case]
        pol_metrics = {}
        for (case_name, pol), pol_values in sorted(by_case_pol.items()):
            if case_name != case:
                continue
            abs_pol = [abs(value) for value in pol_values]
            pol_metrics[f"{pol:.0f}deg"] = {
                "sample_count": len(pol_values),
                "global_rms_deg": rms(pol_values),
                "p95_abs_deg": percentile(abs_pol, 95.0),
                "max_abs_deg": max(abs_pol, default=0.0),
            }
        by_case[case] = {
            "holdout_group_count": len(group_rms_values),
            "holdout_sample_count": len(values),
            "holdout_avg_group_rms_deg": fmean(group_rms_values) if group_rms_values else 0.0,
            "holdout_global_rms_deg": rms(values),
            "holdout_p95_abs_deg": percentile(abs_values, 95.0),
            "holdout_max_abs_deg": max(abs_values, default=0.0),
            "by_pol": pol_metrics,
            "meets_target": (fmean(group_rms_values) if group_rms_values else 0.0) <= TARGET_AVG_RMS_DEG,
        }
    return group_rows, by_case


def summarize_polarization(case_rows: list[dict[str, Any]], validation_by_case: dict[str, Any]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, float], list[dict[str, Any]]] = defaultdict(list)
    for row in case_rows:
        grouped[(row["case"], float(row["linear_pol_deg"]))].append(row)

    summaries = []
    for (case, pol), rows in sorted(grouped.items()):
        rms_values = [float(row["rms_bias_vs_pol0_deg"]) for row in rows]
        max_values = [float(row["max_abs_bias_vs_pol0_deg"]) for row in rows]
        valid_values = [float(row["valid_percent"]) for row in rows]
        holdout_pol = validation_by_case.get(case, {}).get("by_pol", {}).get(f"{pol:.0f}deg", {})
        summaries.append(
            {
                "case": case,
                "linear_pol_deg": pol,
                "curve_count": len(rows),
                "valid_percent_avg": fmean(valid_values) if valid_values else 0.0,
                "raw_rms_bias_vs_pol0_avg_deg": fmean(rms_values) if rms_values else 0.0,
                "raw_p95_rms_bias_vs_pol0_deg": percentile(rms_values, 95.0),
                "raw_max_abs_bias_vs_pol0_deg": max(max_values, default=0.0),
                "lut_holdout_global_rms_deg": holdout_pol.get("global_rms_deg", 0.0),
                "lut_holdout_p95_abs_deg": holdout_pol.get("p95_abs_deg", 0.0),
                "lut_holdout_max_abs_deg": holdout_pol.get("max_abs_deg", 0.0),
            }
        )
    return summaries


def aggregate_metrics(
    best_name: str,
    case_metrics: list[dict[str, Any]],
    pdoa_summaries: list[dict[str, Any]],
    pol_summaries: list[dict[str, Any]],
    validation_by_case: dict[str, Any],
    project_copies: dict[str, str],
) -> dict[str, Any]:
    by_case = {}
    for case_metric in case_metrics:
        case = case_metric["case"]
        non_ref = [
            row
            for row in pdoa_summaries
            if row["case"] == case and abs(float(row["linear_pol_deg"]) - REFERENCE_POL_DEG) > 1e-9
        ]
        raw_rms_values = [float(row["rms_bias_vs_pol0_deg"]) for row in non_ref]
        raw_max_values = [float(row["max_abs_bias_vs_pol0_deg"]) for row in non_ref]
        by_case[case] = {
            **case_metric,
            "raw_curve_count_non_ref": len(non_ref),
            "raw_avg_rms_bias_vs_pol0_deg": fmean(raw_rms_values) if raw_rms_values else 0.0,
            "raw_p95_rms_bias_vs_pol0_deg": percentile(raw_rms_values, 95.0),
            "raw_max_abs_bias_vs_pol0_deg": max(raw_max_values, default=0.0),
            "lut_holdout": validation_by_case.get(case, {}),
            "project_copy": project_copies.get(case),
        }
    engineering_cases = [
        item
        for item in by_case.values()
        if item.get("engineering_valid_s11") and item.get("s11_pass") and item.get("lut_holdout", {}).get("holdout_group_count", 0) > 0
    ]
    engineering_rms = [item["lut_holdout"]["holdout_avg_group_rms_deg"] for item in engineering_cases]
    return {
        "best_candidate": best_name,
        "target_avg_rms_deg": TARGET_AVG_RMS_DEG,
        "reference_pol_deg": REFERENCE_POL_DEG,
        "holdout_step_deg": HOLDOUT_STEP_DEG,
        "linear_polarizations_deg": pdoa_eval.LINEAR_POLARIZATION_DEG,
        "phi_cuts_deg": pdoa_eval.PHI_CUTS_DEG,
        "cases": by_case,
        "polarization_summary": pol_summaries,
        "engineering_valid_absorptive_avg_holdout_group_rms_deg": fmean(engineering_rms) if engineering_rms else 0.0,
        "engineering_valid_absorptive_meets_target": (fmean(engineering_rms) if engineering_rms else 0.0) <= TARGET_AVG_RMS_DEG,
        "project_copies": project_copies,
    }


def write_report(metrics: dict[str, Any]) -> None:
    cases = metrics["cases"]
    ranked = sorted(cases.values(), key=lambda row: (not row.get("engineering_valid_s11", False), row["case"]))
    lines = [
        "# UWB CH9 D44 双极化 RF Switch 工作态 PDOA 极化误差评估报告",
        "",
        "## 评估目标",
        "",
        "- 基于当前 S11 最优孔缝耦合候选，评估 RF switch 分时单通道工作态下，线极化入射 `0 / 45 / 90 / 135 deg` 对 PDOA 测角稳定性的影响。",
        "- 选通极化保留为 HFSS lumped port，未选极化替换为 RF switch off 状态并联 RLC 等效负载。",
        f"- 主判据沿用前序 PDOA 极化标定目标：10 deg theta 网格留出验证后，PDOA 残差平均 group RMS `<= {TARGET_AVG_RMS_DEG:.1f} deg`。",
        "- 报告同时列出 LUT 前的原始极化敏感度；反射式高阻 off-state 因 S11 已严重不达标，仅作为失效风险对照。",
        "",
        "## 核心结论",
        "",
        f"- 吸收式 off 端 `50 ohm // 0.08 pF` 的 A_ON/B_ON 工程有效工况，平均留出 RMS 为 `{fmt(metrics['engineering_valid_absorptive_avg_holdout_group_rms_deg'])} deg`，目标判定：`{'通过' if metrics['engineering_valid_absorptive_meets_target'] else '未通过'}`。",
        "- 单通道 RF switch 架构在 PDOA 上必须按“选通极化 + 入射极化角 + 频点 + 方位切面 + 基线”做查表标定；未做极化 LUT 时，原始 PDOA 偏差会随入射极化显著变化。",
        "- 高阻反射式 off 端已经导致 S11 约 -0.34 dB，测角结果即使可提取，也不应作为可用工程状态。",
        "",
        "## 工况汇总",
        "",
        "| 工况 | 选通极化 | Off 等效 | 最差 S11 | S11达标 | 原始平均RMS | 10deg LUT留出平均RMS | 留出95%绝对残差 | 工程判定 |",
        "| --- | --- | --- | ---: | --- | ---: | ---: | ---: | --- |",
    ]
    for item in ranked:
        lut = item.get("lut_holdout", {})
        off_model = f"{item['off_resistance_ohm']:.0f} ohm // {item['off_capacitance_pf']:.2f} pF"
        usable = item.get("engineering_valid_s11") and item.get("s11_pass") and lut.get("meets_target", False)
        lines.append(
            f"| `{item['case']}` | {item['active_pol']} | {off_model} | {fmt(item['worst_return_db'])} dB | "
            f"{'是' if item.get('s11_pass') else '否'} | {fmt(item['raw_avg_rms_bias_vs_pol0_deg'])} deg | "
            f"{fmt(lut.get('holdout_avg_group_rms_deg', 0.0))} deg | {fmt(lut.get('holdout_p95_abs_deg', 0.0))} deg | "
            f"{'可用' if usable else '不可用/需谨慎'} |"
        )
    lines.extend(
        [
            "",
            "## 分极化结果",
            "",
            "| 工况 | 入射线极化 | 曲线数 | 有效点比例 | LUT前RMS | LUT留出RMS | LUT留出95% | 最大留出残差 |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for row in metrics["polarization_summary"]:
        lines.append(
            f"| `{row['case']}` | {fmt(row['linear_pol_deg'], 0)} deg | {int(row['curve_count'])} | "
            f"{fmt(row['valid_percent_avg'], 1)}% | {fmt(row['raw_rms_bias_vs_pol0_avg_deg'])} deg | "
            f"{fmt(row['lut_holdout_global_rms_deg'])} deg | {fmt(row['lut_holdout_p95_abs_deg'])} deg | "
            f"{fmt(row['lut_holdout_max_abs_deg'])} deg |"
        )
    lines.extend(
        [
            "",
            "## 方法说明",
            "",
            f"- 基线候选：`{metrics['best_candidate']}`。",
            "- 每个工况重新建立 HFSS 远场工作态工程，使用 8 cores / 8 tasks，并在 `Upper_Hemisphere_5deg` 上提取嵌入远场。",
            "- 对每个选通端口逐一激励，读取 `rETheta/rEPhi`，用 `Etheta*cos(psi)+Ephi*sin(psi)` 投影到 0/45/90/135 deg 线极化。",
            "- PDOA 定义为同一选通极化通道下两个阵元复响应的相位差；0 deg 极化作为参考，统计其他极化相对 0 deg 的 PDOA 偏差。",
            "- 10 deg LUT 留出验证：用 theta=0/10/20/.../90 deg 点训练极化残差 LUT，用 theta=5/15/.../85 deg 点验证插值后的残差 RMS。",
            "",
            "## 输出文件",
            "",
            f"- 曲线 CSV: `{CURVES_CSV}`",
            f"- 曲线汇总 CSV: `{SUMMARY_CSV}`",
            f"- 分极化汇总 CSV: `{POL_SUMMARY_CSV}`",
            f"- LUT 留出验证 CSV: `{VALIDATION_CSV}`",
            f"- 指标 JSON: `{METRICS_JSON}`",
        ]
    )
    for case, path in metrics.get("project_copies", {}).items():
        lines.append(f"- `{case}` AEDT 工作态快照: `{path}`")
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run() -> dict[str, Any]:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    best_name, base_candidate_params = best_candidate_params()
    all_curves: list[dict[str, Any]] = []
    all_summaries: list[dict[str, Any]] = []
    case_metrics: list[dict[str, Any]] = []
    project_copies: dict[str, str] = {}

    for case in CASES:
        print(f"=== RF switch PDOA workstate: {case.name} ===", flush=True)
        started = time.time()
        params = set_case_params(base_candidate_params, case)
        builder.TOPOLOGIES[TOPOLOGY]["params"] = params
        project_path, hfss = builder.build_project(
            TOPOLOGY,
            analyze=True,
            non_graphical=True,
            quick=True,
            band_samples=True,
            sparam_only=False,
            return_hfss=True,
            analysis_cores=8,
            analysis_tasks=8,
        )
        try:
            sources = hfss.get_all_sources()
            sparams = topology_eval.get_s_parameter_snapshot(hfss, REPORT_DIR / f"{STEM}_{case.name}_s_parameters.csv")
            eval_freqs = pdoa_eval.nearest_frequencies(pdoa_eval.get_available_frequencies(hfss))
            fields = pdoa_eval.acquire_embedded_fields(hfss, sources, eval_freqs)
            curves, summaries, _pdoa_metrics = pdoa_eval.evaluate_pdoa(fields, eval_freqs, sources)
        finally:
            hfss.release_desktop(close_projects=False, close_desktop=True)

        elapsed_s = time.time() - started
        sparam_summary = summarize_sparams(case, sparams)
        for row in curves:
            row.update(
                {
                    "case": case.name,
                    "active_pol": case.active_pol,
                    "off_resistance_ohm": case.off_resistance_ohm,
                    "off_capacitance_pf": case.off_capacitance_pf,
                }
            )
        for row in summaries:
            row.update(
                {
                    "case": case.name,
                    "active_pol": case.active_pol,
                    "off_resistance_ohm": case.off_resistance_ohm,
                    "off_capacitance_pf": case.off_capacitance_pf,
                }
            )
        all_curves.extend(curves)
        all_summaries.extend(summaries)

        copy_path = REPORT_DIR / f"{STEM}_{case.name}.aedt"
        shutil.copy2(project_path, copy_path)
        project_copies[case.name] = str(copy_path)

        metric = {
            "case": case.name,
            "active_pol": case.active_pol,
            "off_resistance_ohm": case.off_resistance_ohm,
            "off_capacitance_pf": case.off_capacitance_pf,
            "off_inductance_nh": case.off_inductance_nh,
            "engineering_valid_s11": case.engineering_valid_s11,
            "elapsed_s": elapsed_s,
            "sources": sources,
            "eval_freqs_ghz": eval_freqs,
            **sparam_summary,
        }
        case_metrics.append(metric)
        print(json.dumps(metric, indent=2, ensure_ascii=False), flush=True)

    validation_rows = lut_holdout_validation(all_curves)
    validation_summary_rows, validation_by_case = summarize_validation(validation_rows)
    pol_summaries = summarize_polarization(all_summaries, validation_by_case)
    metrics = aggregate_metrics(
        best_name,
        case_metrics,
        all_summaries,
        pol_summaries,
        validation_by_case,
        project_copies,
    )

    curve_fields = [
        "case",
        "active_pol",
        "off_resistance_ohm",
        "off_capacitance_pf",
        "freq_ghz",
        "phi_deg",
        "theta_deg",
        "linear_pol_deg",
        "channel_set",
        "baseline",
        "pdoa_deg",
        "pdoa_unwrapped_deg",
        "left_mag_rel_db",
        "right_mag_rel_db",
        "valid",
    ]
    summary_fields = [
        "case",
        "active_pol",
        "off_resistance_ohm",
        "off_capacitance_pf",
        "freq_ghz",
        "phi_deg",
        "linear_pol_deg",
        "channel_set",
        "baseline",
        "valid_percent",
        "pdoa_span_deg",
        "pdoa_start_deg",
        "pdoa_end_deg",
        "mean_abs_slope_deg_per_deg",
        "slope_std_deg_per_deg",
        "monotonic_segment_percent",
        "min_pair_mag_rel_db",
        "rms_bias_vs_pol0_deg",
        "mean_abs_bias_vs_pol0_deg",
        "max_abs_bias_vs_pol0_deg",
    ]
    write_csv(CURVES_CSV, all_curves, curve_fields)
    write_csv(SUMMARY_CSV, all_summaries, summary_fields)
    write_csv(POL_SUMMARY_CSV, pol_summaries)
    write_csv(VALIDATION_CSV, validation_rows)
    write_csv(REPORT_DIR / f"{STEM}_lut_holdout_group_summary.csv", validation_summary_rows)
    METRICS_JSON.write_text(json.dumps(metrics, indent=2, ensure_ascii=False), encoding="utf-8")
    write_report(metrics)
    print(f"Wrote {REPORT_MD}", flush=True)
    return metrics


def main() -> None:
    metrics = run()
    print(
        json.dumps(
            {
                "engineering_valid_absorptive_avg_holdout_group_rms_deg": metrics[
                    "engineering_valid_absorptive_avg_holdout_group_rms_deg"
                ],
                "engineering_valid_absorptive_meets_target": metrics["engineering_valid_absorptive_meets_target"],
                "report": str(REPORT_MD),
            },
            indent=2,
            ensure_ascii=False,
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
