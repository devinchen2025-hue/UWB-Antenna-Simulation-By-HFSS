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
REPORT_DIR = ROOT / "reports_d44_dualpol_rf_switch_gain_xy_plane"
STEM = "UWB_CH9_D44_DUALPOL_RF_SWITCH_GAIN_XY_PLANE"
SOLUTION = "Setup_CH9 : Sweep_CH9"
SPHERE = "Upper_Hemisphere_5deg"
GAIN_TARGET_DBI = -5.0
PLANE_THETA_DEG = 90.0

CSV_PATH = REPORT_DIR / f"{STEM}_check.csv"
METRICS_JSON = REPORT_DIR / f"{STEM}_metrics.json"
REPORT_MD = REPORT_DIR / f"{STEM}_report.md"


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


def plane_rows(grid: list[dict[str, float]]) -> list[dict[str, float]]:
    rows = [row for row in grid if abs(row["theta_deg"] - PLANE_THETA_DEG) < 1e-6]
    if rows:
        return rows
    nearest_theta = min({row["theta_deg"] for row in grid}, key=lambda value: abs(value - PLANE_THETA_DEG))
    return [row for row in grid if abs(row["theta_deg"] - nearest_theta) < 1e-6]


def summarize_source(hfss, sources: list[str], active_source: str) -> list[dict[str, Any]]:
    hfss.edit_sources({source: (1.0 if source == active_source else 0.0, 0.0) for source in sources})
    eval_freqs = pdoa_eval.nearest_frequencies(pdoa_eval.get_available_frequencies(hfss))
    rows = []
    for freq in eval_freqs:
        grid = get_gain_grid(hfss, freq)
        xy_rows = plane_rows(grid)
        min_gain_row = min(xy_rows, key=lambda row: row["gain_total_dbi"])
        min_realized_row = min(xy_rows, key=lambda row: row["realized_gain_total_dbi"])
        max_gain_row = max(xy_rows, key=lambda row: row["gain_total_dbi"])
        max_realized_row = max(xy_rows, key=lambda row: row["realized_gain_total_dbi"])
        rows.append(
            {
                "source": active_source,
                "freq_ghz": freq,
                "plane_theta_deg": min_gain_row["theta_deg"],
                "xy_plane_gain_total_min_dbi": min_gain_row["gain_total_dbi"],
                "xy_plane_gain_total_min_phi_deg": min_gain_row["phi_deg"],
                "xy_plane_realized_gain_total_min_dbi": min_realized_row["realized_gain_total_dbi"],
                "xy_plane_realized_gain_total_min_phi_deg": min_realized_row["phi_deg"],
                "xy_plane_gain_total_max_dbi": max_gain_row["gain_total_dbi"],
                "xy_plane_gain_total_max_phi_deg": max_gain_row["phi_deg"],
                "xy_plane_realized_gain_total_max_dbi": max_realized_row["realized_gain_total_dbi"],
                "xy_plane_realized_gain_total_max_phi_deg": max_realized_row["phi_deg"],
                "xy_plane_phi_sample_count": len(xy_rows),
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
        worst_gain = min(items, key=lambda row: row["xy_plane_gain_total_min_dbi"])
        worst_realized = min(items, key=lambda row: row["xy_plane_realized_gain_total_min_dbi"])
        case_summary[case] = {
            "xy_plane_gain_total_min_dbi": worst_gain["xy_plane_gain_total_min_dbi"],
            "xy_plane_gain_total_min_source": worst_gain["source"],
            "xy_plane_gain_total_min_freq_ghz": worst_gain["freq_ghz"],
            "xy_plane_gain_total_min_phi_deg": worst_gain["xy_plane_gain_total_min_phi_deg"],
            "xy_plane_realized_gain_total_min_dbi": worst_realized["xy_plane_realized_gain_total_min_dbi"],
            "xy_plane_realized_gain_total_min_source": worst_realized["source"],
            "xy_plane_realized_gain_total_min_freq_ghz": worst_realized["freq_ghz"],
            "xy_plane_realized_gain_total_min_phi_deg": worst_realized["xy_plane_realized_gain_total_min_phi_deg"],
            "xy_plane_gain_total_max_min_dbi": min(row["xy_plane_gain_total_max_dbi"] for row in items),
            "xy_plane_realized_gain_total_max_min_dbi": min(row["xy_plane_realized_gain_total_max_dbi"] for row in items),
            "xy_plane_gain_total_meets": worst_gain["xy_plane_gain_total_min_dbi"] >= GAIN_TARGET_DBI,
            "xy_plane_realized_gain_meets": worst_realized["xy_plane_realized_gain_total_min_dbi"] >= GAIN_TARGET_DBI,
        }

    return {
        "target_dbi": GAIN_TARGET_DBI,
        "interpretation": "Z=0 plane is interpreted as the XY plane, i.e. Theta=90 deg and Phi=0..360 deg in HFSS spherical coordinates.",
        "best_candidate": best_candidate,
        "case_summary": case_summary,
        "min_xy_plane_gain_total_dbi": min(row["xy_plane_gain_total_min_dbi"] for row in rows),
        "min_xy_plane_realized_gain_total_dbi": min(row["xy_plane_realized_gain_total_min_dbi"] for row in rows),
        "min_xy_plane_peak_gain_total_dbi": min(row["xy_plane_gain_total_max_dbi"] for row in rows),
        "min_xy_plane_peak_realized_gain_total_dbi": min(row["xy_plane_realized_gain_total_max_dbi"] for row in rows),
        "all_xy_plane_gain_total_meet": all(row["xy_plane_gain_total_min_dbi"] >= GAIN_TARGET_DBI for row in rows),
        "all_xy_plane_realized_gain_meet": all(row["xy_plane_realized_gain_total_min_dbi"] >= GAIN_TARGET_DBI for row in rows),
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
        "# D44 RF Switch 工作态 XY 平面增益核查报告",
        "",
        "## 判据",
        "",
        f"- 目标：Z=0 即 XY 平面方向图，按 HFSS 球坐标 `Theta=90 deg, Phi=0..360 deg` 抽取，GainTotal 与 RealizedGainTotal 均 `>= {GAIN_TARGET_DBI:.1f} dBi`。",
        "- 核查工况：工程有效的吸收式 off 端 `50 ohm // 0.08 pF`，包括 A_ON 与 B_ON。",
        "- 每个选通端口单独激励，其余选通端口关断；对每个频点取 XY 平面整圈 Phi 的最小值作为保守判据。",
        "",
        "## 结论",
        "",
        f"- XY 平面最小 GainTotal：`{fmt(metrics['min_xy_plane_gain_total_dbi'])} dBi`。",
        f"- XY 平面最小 RealizedGainTotal：`{fmt(metrics['min_xy_plane_realized_gain_total_dbi'])} dBi`。",
        f"- XY 平面峰值 GainTotal 的跨端口/频点最小值：`{fmt(metrics['min_xy_plane_peak_gain_total_dbi'])} dBi`。",
        f"- XY 平面峰值 RealizedGainTotal 的跨端口/频点最小值：`{fmt(metrics['min_xy_plane_peak_realized_gain_total_dbi'])} dBi`。",
        f"- 结论：`{'满足' if metrics['all_xy_plane_gain_total_meet'] and metrics['all_xy_plane_realized_gain_meet'] else '不满足'}`。",
        "",
        "## 分工况最差值",
        "",
        "| 工况 | XY平面 GainTotal 最小值 | XY平面 RealizedGainTotal 最小值 | 最差 Gain 点 | 最差 Realized 点 | 是否满足 |",
        "| --- | ---: | ---: | --- | --- | --- |",
    ]
    for case, item in metrics["case_summary"].items():
        ok = item["xy_plane_gain_total_meets"] and item["xy_plane_realized_gain_meets"]
        lines.append(
            f"| `{case}` | {fmt(item['xy_plane_gain_total_min_dbi'])} dBi | "
            f"{fmt(item['xy_plane_realized_gain_total_min_dbi'])} dBi | "
            f"`{item['xy_plane_gain_total_min_source']}` / {fmt(item['xy_plane_gain_total_min_freq_ghz'], 4)} GHz / Phi {fmt(item['xy_plane_gain_total_min_phi_deg'], 0)} deg | "
            f"`{item['xy_plane_realized_gain_total_min_source']}` / {fmt(item['xy_plane_realized_gain_total_min_freq_ghz'], 4)} GHz / Phi {fmt(item['xy_plane_realized_gain_total_min_phi_deg'], 0)} deg | "
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
        print(f"=== XY-plane gain check {case.name} ===", flush=True)
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
