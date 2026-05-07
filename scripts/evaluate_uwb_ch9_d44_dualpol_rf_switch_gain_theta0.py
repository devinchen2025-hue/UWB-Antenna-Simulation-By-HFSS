from __future__ import annotations

import csv
import json
import math
import shutil
from collections import defaultdict
from pathlib import Path
from typing import Any

import build_uwb_ch9_hfss_d44_topology as builder
import evaluate_uwb_ch9_d44_pdoa_linear_polarization as pdoa_eval
import simulate_uwb_ch9_d44_dualpol_rf_switch_pdoa_workstate as pdoa_workstate


ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = ROOT / "reports_d44_dualpol_rf_switch_gain_check"
STEM = "UWB_CH9_D44_DUALPOL_RF_SWITCH_GAIN"
SOLUTION = "Setup_CH9 : Sweep_CH9"
SPHERE = "Upper_Hemisphere_5deg"
GAIN_TARGET_DBI = -5.0

CSV_PATH = REPORT_DIR / f"{STEM}_theta0_check.csv"
METRICS_JSON = REPORT_DIR / f"{STEM}_theta0_check_metrics.json"
REPORT_MD = REPORT_DIR / f"{STEM}_theta0_check_report.md"


def axis_values(sd, axis: str) -> list[float]:
    return [float(str(raw).replace("deg", "")) for raw in sd.intrinsics.get(axis, [])]


def get_gain_grid(hfss, freq_ghz: float) -> list[dict[str, float]]:
    expressions = ["dB(GainTotal)", "dB(RealizedGainTotal)"]
    sd = hfss.post.get_solution_data(
        expressions=expressions,
        setup_sweep_name=SOLUTION,
        domain="Sweep",
        variations={"Freq": [f"{freq_ghz:g}GHz"], "Theta": ["All"], "Phi": ["All"]},
        primary_sweep_variable="Phi",
        report_category="Far Fields",
        context=SPHERE,
    )
    if not sd:
        raise RuntimeError("No far-field gain data returned by HFSS")
    theta_values = axis_values(sd, "Theta")
    phi_values = axis_values(sd, "Phi")
    gain_total = [float(value) for value in sd.data_real("dB(GainTotal)")]
    realized = [float(value) for value in sd.data_real("dB(RealizedGainTotal)")]
    expected = len(theta_values) * len(phi_values)
    if len(gain_total) != expected or len(realized) != expected:
        raise RuntimeError(f"Unexpected gain grid length: expected {expected}, got {len(gain_total)}")

    rows = []
    idx = 0
    for phi in phi_values:
        for theta in theta_values:
            rows.append(
                {
                    "theta_deg": theta,
                    "phi_deg": phi,
                    "gain_total_dbi": gain_total[idx],
                    "realized_gain_total_dbi": realized[idx],
                }
            )
            idx += 1
    return rows


def summarize_source(hfss, sources: list[str], active_source: str) -> list[dict[str, Any]]:
    hfss.edit_sources({source: (1.0 if source == active_source else 0.0, 0.0) for source in sources})
    eval_freqs = pdoa_eval.nearest_frequencies(pdoa_eval.get_available_frequencies(hfss))
    rows = []
    for freq in eval_freqs:
        grid = get_gain_grid(hfss, freq)
        z_rows = [row for row in grid if abs(row["theta_deg"]) < 1e-6]
        if not z_rows:
            z_rows = [min(grid, key=lambda row: abs(row["theta_deg"]))]
        rows.append(
            {
                "source": active_source,
                "freq_ghz": freq,
                "z_theta0_gain_total_min_dbi": min(row["gain_total_dbi"] for row in z_rows),
                "z_theta0_gain_total_max_dbi": max(row["gain_total_dbi"] for row in z_rows),
                "z_theta0_realized_gain_total_min_dbi": min(row["realized_gain_total_dbi"] for row in z_rows),
                "z_theta0_realized_gain_total_max_dbi": max(row["realized_gain_total_dbi"] for row in z_rows),
                "upper_hemi_peak_gain_total_dbi": max(row["gain_total_dbi"] for row in grid),
                "upper_hemi_peak_realized_gain_total_dbi": max(row["realized_gain_total_dbi"] for row in grid),
                "upper_hemi_min_gain_total_dbi": min(row["gain_total_dbi"] for row in grid),
                "upper_hemi_min_realized_gain_total_dbi": min(row["realized_gain_total_dbi"] for row in grid),
            }
        )
    return rows


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(rows[0])
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: f"{value:.6f}" if isinstance(value, float) else value for key, value in row.items()})


def summarize_metrics(rows: list[dict[str, Any]], best_candidate: str, projects: dict[str, str]) -> dict[str, Any]:
    by_case: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_case[row["case"]].append(row)
    case_summary = {}
    for case, items in sorted(by_case.items()):
        worst_z = min(items, key=lambda row: row["z_theta0_gain_total_min_dbi"])
        case_summary[case] = {
            "z_theta0_gain_total_min_dbi": min(row["z_theta0_gain_total_min_dbi"] for row in items),
            "z_theta0_realized_gain_total_min_dbi": min(row["z_theta0_realized_gain_total_min_dbi"] for row in items),
            "upper_hemi_peak_gain_total_min_dbi": min(row["upper_hemi_peak_gain_total_dbi"] for row in items),
            "upper_hemi_peak_realized_gain_total_min_dbi": min(row["upper_hemi_peak_realized_gain_total_dbi"] for row in items),
            "worst_z_source": worst_z["source"],
            "worst_z_freq_ghz": worst_z["freq_ghz"],
            "z_gain_total_meets": min(row["z_theta0_gain_total_min_dbi"] for row in items) >= GAIN_TARGET_DBI,
            "z_realized_gain_meets": min(row["z_theta0_realized_gain_total_min_dbi"] for row in items) >= GAIN_TARGET_DBI,
            "peak_gain_total_meets": min(row["upper_hemi_peak_gain_total_dbi"] for row in items) >= GAIN_TARGET_DBI,
            "peak_realized_gain_meets": min(row["upper_hemi_peak_realized_gain_total_dbi"] for row in items) >= GAIN_TARGET_DBI,
        }
    return {
        "target_dbi": GAIN_TARGET_DBI,
        "interpretation": "Theta=0 deg, +Z boresight. Duplicate Phi samples at theta=0 are reduced by conservative minimum.",
        "best_candidate": best_candidate,
        "case_summary": case_summary,
        "min_z_theta0_gain_total_dbi": min(row["z_theta0_gain_total_min_dbi"] for row in rows),
        "min_z_theta0_realized_gain_total_dbi": min(row["z_theta0_realized_gain_total_min_dbi"] for row in rows),
        "min_upper_hemi_peak_gain_total_dbi": min(row["upper_hemi_peak_gain_total_dbi"] for row in rows),
        "min_upper_hemi_peak_realized_gain_total_dbi": min(row["upper_hemi_peak_realized_gain_total_dbi"] for row in rows),
        "all_z_gain_total_meet": all(row["z_theta0_gain_total_min_dbi"] >= GAIN_TARGET_DBI for row in rows),
        "all_z_realized_gain_meet": all(row["z_theta0_realized_gain_total_min_dbi"] >= GAIN_TARGET_DBI for row in rows),
        "all_peak_gain_total_meet": all(row["upper_hemi_peak_gain_total_dbi"] >= GAIN_TARGET_DBI for row in rows),
        "all_peak_realized_gain_meet": all(row["upper_hemi_peak_realized_gain_total_dbi"] >= GAIN_TARGET_DBI for row in rows),
        "csv": str(CSV_PATH),
        "projects": projects,
    }


def fmt(value: Any, digits: int = 2) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    if math.isnan(number) or math.isinf(number):
        return "N/A"
    return f"{number:.{digits}f}"


def write_report(metrics: dict[str, Any]) -> None:
    lines = [
        "# D44 RF Switch 工作态 Theta=0 增益核查报告",
        "",
        "## 判据",
        "",
        f"- 目标：Theta=0 deg（+Z 轴/法向方向）GainTotal 与 RealizedGainTotal 均 `>= {GAIN_TARGET_DBI:.1f} dBi`。",
        "- 核查工况：仅核查工程有效的吸收式 off 端 `50 ohm // 0.08 pF`，包括 A_ON 与 B_ON。",
        "- 每个选通端口单独激励，其余选通端口关断，用所有 Phi 重复样本中的最小值作为 Theta=0 的保守值。",
        "",
        "## 结论",
        "",
        f"- Theta=0 最小 GainTotal：`{fmt(metrics['min_z_theta0_gain_total_dbi'])} dBi`。",
        f"- Theta=0 最小 RealizedGainTotal：`{fmt(metrics['min_z_theta0_realized_gain_total_dbi'])} dBi`。",
        f"- 上半球峰值 GainTotal 的跨端口/频点最小值：`{fmt(metrics['min_upper_hemi_peak_gain_total_dbi'])} dBi`。",
        f"- 上半球峰值 RealizedGainTotal 的跨端口/频点最小值：`{fmt(metrics['min_upper_hemi_peak_realized_gain_total_dbi'])} dBi`。",
        f"- 结论：`{'满足' if metrics['all_z_gain_total_meet'] and metrics['all_z_realized_gain_meet'] else '不满足'}`。",
        "",
        "## 分工况最差值",
        "",
        "| 工况 | Theta=0 GainTotal 最小值 | Theta=0 RealizedGainTotal 最小值 | 上半球峰值 GainTotal 最小值 | 最差端口/频点 | 是否满足 |",
        "| --- | ---: | ---: | ---: | --- | --- |",
    ]
    for case, item in metrics["case_summary"].items():
        ok = item["z_gain_total_meets"] and item["z_realized_gain_meets"]
        lines.append(
            f"| `{case}` | {fmt(item['z_theta0_gain_total_min_dbi'])} dBi | "
            f"{fmt(item['z_theta0_realized_gain_total_min_dbi'])} dBi | "
            f"{fmt(item['upper_hemi_peak_gain_total_min_dbi'])} dBi | "
            f"`{item['worst_z_source']}` / {fmt(item['worst_z_freq_ghz'], 4)} GHz | "
            f"{'是' if ok else '否'} |"
        )
    lines.extend(
        [
            "",
            "## 文件",
            "",
            f"- 明细 CSV: `{CSV_PATH}`",
            f"- 指标 JSON: `{METRICS_JSON}`",
        ]
    )
    for case, project in metrics["projects"].items():
        lines.append(f"- `{case}` AEDT 快照: `{project}`")
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run() -> dict[str, Any]:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    best_name, base_candidate_params = pdoa_workstate.best_candidate_params()
    cases = [pdoa_workstate.CASES[0], pdoa_workstate.CASES[1]]
    rows: list[dict[str, Any]] = []
    projects: dict[str, str] = {}
    for case in cases:
        params = pdoa_workstate.set_case_params(base_candidate_params, case)
        builder.TOPOLOGIES[pdoa_workstate.TOPOLOGY]["params"] = params
        project_path, hfss = builder.build_project(
            pdoa_workstate.TOPOLOGY,
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
            for source in sources:
                for row in summarize_source(hfss, sources, source):
                    row.update(
                        {
                            "case": case.name,
                            "active_pol": case.active_pol,
                            "off_resistance_ohm": case.off_resistance_ohm,
                            "off_capacitance_pf": case.off_capacitance_pf,
                        }
                    )
                    rows.append(row)
        finally:
            hfss.release_desktop(close_projects=False, close_desktop=True)
        copy_path = REPORT_DIR / f"{STEM}_{case.name}.aedt"
        shutil.copy2(project_path, copy_path)
        projects[case.name] = str(copy_path)
    write_csv(CSV_PATH, rows)
    metrics = summarize_metrics(rows, best_name, projects)
    METRICS_JSON.write_text(json.dumps(metrics, indent=2, ensure_ascii=False), encoding="utf-8")
    write_report(metrics)
    return metrics


def main() -> None:
    print(json.dumps(run(), indent=2, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
