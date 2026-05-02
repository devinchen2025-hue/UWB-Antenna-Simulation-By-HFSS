from __future__ import annotations

import csv
import json
import math
from pathlib import Path

from ansys.aedt.core import Hfss


ROOT = Path(__file__).resolve().parents[1]
PROJECT_PATH = ROOT / "UWB_CH9_Diamond_CP_Array_D44_H8_PCB_CP.aedt"
PARAM_PATH = ROOT / "UWB_CH9_Diamond_CP_Array_D44_H8_PCB_CP_params.json"
REPORT_DIR = ROOT / "reports_d44_h8_pcb_cp"
METRICS_JSON = REPORT_DIR / "UWB_CH9_D44_H8_PCB_CP_metrics.json"
FOV_CSV = REPORT_DIR / "UWB_CH9_D44_H8_PCB_CP_fov_cp_metrics.csv"
S_CSV = REPORT_DIR / "UWB_CH9_D44_H8_PCB_CP_s_parameters.csv"
REPORT_MD = REPORT_DIR / "UWB_CH9_D44_H8_PCB_CP_simulation_report.md"
DESIGN = "Array4_Diamond_D44_H8_PCB_CP"
SOLUTION = "Setup_CH9 : Sweep_CH9"
SPHERE = "Upper_Hemisphere_5deg"
TARGET_FREQS_GHZ = [7.738, 8.0, 8.233]
FOV_TEXT = "Theta 0-360 deg, Phi 45-90 deg"
GAIN_MIN_TARGET_DBI = -5.0
AXIAL_RATIO_TARGET_DB = 3.0


def axis_values(sd, axis: str) -> list[float]:
    values = []
    for raw in sd.intrinsics.get(axis, []):
        values.append(float(str(raw).replace("deg", "")))
    return values


def parse_s_term(expr: str) -> tuple[str, str]:
    inside = expr.split("S(", 1)[1].split(")", 1)[0]
    left, right = inside.split(",", 1)
    return left.strip(), right.strip()


def get_available_frequencies(hfss: Hfss) -> list[float]:
    expressions = hfss.get_traces_for_plot(category="dB(S")
    if not expressions:
        return [8.0]
    sd = hfss.post.get_solution_data(
        expressions=expressions[0],
        setup_sweep_name=SOLUTION,
        primary_sweep_variable="Freq",
    )
    return sorted(float(x) for x in sd.primary_sweep_values)


def nearest_frequencies(available: list[float]) -> list[float]:
    selected = []
    for target in TARGET_FREQS_GHZ:
        nearest = min(available, key=lambda x: abs(x - target))
        if nearest not in selected:
            selected.append(nearest)
    return selected


def get_grid(hfss: Hfss, freq_ghz: float) -> dict:
    gain_expr = "dB(GainTotal)"
    ar_expr = "AxialRatioValue"
    sd = hfss.post.get_solution_data(
        expressions=[gain_expr, ar_expr],
        setup_sweep_name=SOLUTION,
        domain="Sweep",
        variations={"Freq": [f"{freq_ghz:g}GHz"], "Theta": ["All"], "Phi": ["All"]},
        primary_sweep_variable="Phi",
        report_category="Far Fields",
        context=SPHERE,
    )
    theta_vals = axis_values(sd, "Theta")
    phi_vals = axis_values(sd, "Phi")
    gains = [float(x) for x in sd.data_real(gain_expr)]
    axial = [float(x) for x in sd.data_real(ar_expr)]
    expected = len(theta_vals) * len(phi_vals)
    if len(gains) != expected or len(axial) != expected:
        raise RuntimeError(
            f"Unexpected far-field grid length: gain={len(gains)}, ar={len(axial)}, expected={expected}"
        )

    rows = []
    idx = 0
    for phi in phi_vals:
        for theta in theta_vals:
            rows.append({"theta": theta, "phi": phi, "gain": gains[idx], "axial_ratio": axial[idx]})
            idx += 1
    return {
        "theta_values": theta_vals,
        "phi_values": phi_vals,
        "rows": rows,
    }


def summarize_rows(freq_ghz: float, rows: list[dict]) -> dict:
    roi = [r for r in rows if 0.0 <= r["theta"] <= 360.0 and 45.0 <= r["phi"] <= 90.0]
    min_gain_row = min(roi, key=lambda r: r["gain"])
    max_gain_row = max(roi, key=lambda r: r["gain"])
    min_ar_row = min(roi, key=lambda r: r["axial_ratio"])
    max_ar_row = max(roi, key=lambda r: r["axial_ratio"])
    cp_count = sum(1 for r in roi if r["axial_ratio"] <= AXIAL_RATIO_TARGET_DB)
    return {
        "freq_ghz": freq_ghz,
        "fov": FOV_TEXT,
        "sample_count": len(roi),
        "gain_min_dbi": min_gain_row["gain"],
        "gain_max_dbi": max_gain_row["gain"],
        "gain_ripple_db": max_gain_row["gain"] - min_gain_row["gain"],
        "gain_min_point": min_gain_row,
        "gain_max_point": max_gain_row,
        "axial_ratio_min_db": min_ar_row["axial_ratio"],
        "axial_ratio_max_db": max_ar_row["axial_ratio"],
        "axial_ratio_min_point": min_ar_row,
        "axial_ratio_max_point": max_ar_row,
        "cp_coverage_percent": 100.0 * cp_count / len(roi) if roi else 0.0,
        "meets_gain": min_gain_row["gain"] >= GAIN_MIN_TARGET_DBI,
        "meets_cp": max_ar_row["axial_ratio"] <= AXIAL_RATIO_TARGET_DB,
    }


def edit_sources_safe(hfss: Hfss, assignments: dict[str, tuple[float, float]]) -> None:
    if assignments:
        hfss.edit_sources(assignments)


def sequential_assignments(sources: list[str], phase_step_deg: float = -90.0) -> dict[str, tuple[float, float]]:
    assignments = {}
    for idx, source in enumerate(sources):
        assignments[source] = (1.0, idx * phase_step_deg)
    return assignments


def get_s_parameter_snapshot(hfss: Hfss) -> dict:
    expressions = hfss.get_traces_for_plot(category="dB(S")
    sd = hfss.post.get_solution_data(
        expressions=expressions,
        setup_sweep_name=SOLUTION,
        primary_sweep_variable="Freq",
    )
    freqs = [float(x) for x in sd.primary_sweep_values]
    rows = []
    s_data = {expr: [float(x) for x in sd.data_real(expr)] for expr in expressions}
    for idx, freq in enumerate(freqs):
        row = {"Freq_GHz": f"{freq:.6f}"}
        for expr in expressions:
            row[expr] = f"{s_data[expr][idx]:.6f}"
        rows.append(row)
    if rows:
        with S_CSV.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)

    target_indices = [
        i for i, freq in enumerate(freqs)
        if TARGET_FREQS_GHZ[0] - 1e-9 <= freq <= TARGET_FREQS_GHZ[-1] + 1e-9
    ] or list(range(len(freqs)))

    self_terms = {}
    coupling_terms = {}
    for expr in expressions:
        left, right = parse_s_term(expr)
        values = [s_data[expr][i] for i in target_indices]
        worst = max(values)
        if left == right:
            self_terms[expr] = worst
        else:
            coupling_terms[expr] = worst

    worst_return_expr, worst_return_db = max(self_terms.items(), key=lambda item: item[1])
    worst_coupling_expr, worst_coupling_db = max(coupling_terms.items(), key=lambda item: item[1])
    return {
        "frequencies_ghz": freqs,
        "target_band_ghz": [TARGET_FREQS_GHZ[0], TARGET_FREQS_GHZ[-1]],
        "self_worst_db": self_terms,
        "coupling_worst_db": coupling_terms,
        "worst_return_expr": worst_return_expr,
        "worst_return_db": worst_return_db,
        "worst_coupling_expr": worst_coupling_expr,
        "worst_coupling_db": worst_coupling_db,
        "isolation_db": -worst_coupling_db,
    }


def write_csv(path: Path, summaries_by_freq: dict[str, dict[str, dict]]) -> None:
    rows = []
    for _, summaries in summaries_by_freq.items():
        for name, item in summaries.items():
            gain_point = item["gain_min_point"]
            ar_point = item["axial_ratio_max_point"]
            rows.append(
                {
                    "source_case": name,
                    "freq_ghz": f"{item['freq_ghz']:.6f}",
                    "gain_min_dbi": f"{item['gain_min_dbi']:.6f}",
                    "gain_max_dbi": f"{item['gain_max_dbi']:.6f}",
                    "gain_ripple_db": f"{item['gain_ripple_db']:.6f}",
                    "axial_ratio_min_db": f"{item['axial_ratio_min_db']:.6f}",
                    "axial_ratio_max_db": f"{item['axial_ratio_max_db']:.6f}",
                    "cp_coverage_percent": f"{item['cp_coverage_percent']:.3f}",
                    "gain_min_theta_deg": f"{gain_point['theta']:.6f}",
                    "gain_min_phi_deg": f"{gain_point['phi']:.6f}",
                    "ar_max_theta_deg": f"{ar_point['theta']:.6f}",
                    "ar_max_phi_deg": f"{ar_point['phi']:.6f}",
                    "meets_gain": item["meets_gain"],
                    "meets_cp": item["meets_cp"],
                }
            )
    if not rows:
        return
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def fmt(value: float | None, digits: int = 2) -> str:
    if value is None or (isinstance(value, float) and (math.isnan(value) or math.isinf(value))):
        return "N/A"
    return f"{value:.{digits}f}"


def write_report(params: dict, metrics: dict) -> None:
    p = params["parameters"]
    s = metrics.get("s_parameters", {})
    lines = [
        "# UWB CH9 D44 H8 PCB圆极化结构仿真报告",
        "",
        "## 模型",
        "",
        f"- AEDT项目: `{PROJECT_PATH}`",
        f"- 设计名: `{DESIGN}`",
        "- 结构: 四阵元菱形布阵，低剖面PCB印刷单馈角截短方形圆极化贴片。",
        f"- PCB直径: `{p['board_diameter_mm']} mm`",
        f"- 总高度约束: `<= {p['total_height_limit_mm']} mm`",
        f"- 当前板厚/总高: `{p['substrate_h_mm']} mm` / `{p['substrate_h_mm'] + 2.0 * p['copper_t_mm']:.3f} mm`",
        f"- 阵元间距: `{params['nearest_neighbor_spacing_mm']} mm`",
        f"- 贴片边长/截角: `{p['patch_side_mm']} mm` / `{p['corner_cut_mm']} mm`",
        "",
        "## 验收指标",
        "",
        f"- 频点: `{ ' / '.join(metrics['fov_by_freq'].keys()) }`",
        f"- FOV区域: `{FOV_TEXT}`",
        f"- 增益判据: `GainTotal`最小值 >= `{GAIN_MIN_TARGET_DBI} dBi`",
        f"- 圆极化判据: `AxialRatioValue`最大值 <= `{AXIAL_RATIO_TARGET_DB} dB`",
        "",
        "## FOV与圆极化结果",
        "",
        "| 频点 | 源设置 | 最小增益 | 最大轴比 | CP覆盖率 | 结论 |",
        "| ---: | --- | ---: | ---: | ---: | --- |",
    ]
    for freq_key, summaries in metrics["fov_by_freq"].items():
        for name, item in summaries.items():
            status = "通过" if item["meets_gain"] and item["meets_cp"] else "未通过"
            lines.append(
                f"| {freq_key} | {name} | {fmt(item['gain_min_dbi'])} dBi | "
                f"{fmt(item['axial_ratio_max_db'])} dB | {fmt(item['cp_coverage_percent'], 1)}% | {status} |"
            )

    if s:
        lines.extend(
            [
                "",
                "## S参数快照",
                "",
                f"- CH9内最差回波损耗: `{fmt(s.get('worst_return_db'), 2)} dB`，项 `{s.get('worst_return_expr', 'N/A')}`",
                f"- CH9内最差耦合: `{fmt(s.get('worst_coupling_db'), 2)} dB`，项 `{s.get('worst_coupling_expr', 'N/A')}`",
                f"- 对应最差隔离度: `{fmt(s.get('isolation_db'), 2)} dB`",
            ]
        )

    lines.extend(
        [
            "",
            "## 本轮优化结论",
            "",
            "- 初始单馈角截短贴片候选的三频点最差回波约 `-1.51 dB`。",
            "- 粗扫、局部细扫和馈电等效参数扫后，最佳候选为 `patch_side=8.91 mm / feed_offset=2.68 mm / corner_cut=0.62 mm`。",
            "- 最终三频点最差回波为 `-9.27 dB`，已接近但尚未完全满足 `Sii < -10 dB`。",
            "- 当前单馈贴片能提供局部低轴比区域，但全FOV圆极化覆盖仍不达标；下一步应引入印刷匹配支节、双馈正交合成、缝隙耦合或小型90度混合网络。",
            "",
            "## 工程说明",
            "",
            "- 本版本用于替代超高的顶加载垂直单极子，满足PCB+天线整体高度小于等于8 mm的加工约束。",
            "- 单馈角截短贴片是圆极化的加工友好起点；若全FOV AR<=3 dB不足，需要继续引入双馈正交合成、顺序旋转馈电网络或多层/缝隙耦合结构。",
            "- `coverage_envelope_best_port`仍是PDOA接收覆盖的主要视角；`sequential_quadrature_all_ports`仅用于阵列圆极化趋势检查。",
            f"- 详细CSV: `{FOV_CSV}`",
            f"- S参数CSV: `{S_CSV}`",
        ]
    )
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
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
        available_freqs = get_available_frequencies(hfss)
        eval_freqs = nearest_frequencies(available_freqs)
        source_cases: dict[str, dict[str, tuple[float, float]]] = {}
        for src in sources:
            source_cases[f"{src}_only"] = {
                item: (1.0 if item == src else 0.0, 0.0) for item in sources
            }
        source_cases["sequential_quadrature_all_ports"] = sequential_assignments(sources)

        summaries_by_freq = {}
        for freq in eval_freqs:
            summaries = {}
            per_port_grids = {}
            for name, assignments in source_cases.items():
                edit_sources_safe(hfss, assignments)
                grid = get_grid(hfss, freq)
                summaries[name] = summarize_rows(freq, grid["rows"])
                if name.endswith("_only"):
                    per_port_grids[name] = grid

            if per_port_grids:
                first_grid = next(iter(per_port_grids.values()))
                envelope_rows = []
                cp_envelope_rows = []
                for idx, base_row in enumerate(first_grid["rows"]):
                    candidates = [grid["rows"][idx] for grid in per_port_grids.values()]
                    best = max(candidates, key=lambda r: r["gain"])
                    envelope_rows.append(
                        {
                            "theta": base_row["theta"],
                            "phi": base_row["phi"],
                            "gain": best["gain"],
                            "axial_ratio": best["axial_ratio"],
                        }
                    )
                    cp_candidates = [r for r in candidates if r["axial_ratio"] <= AXIAL_RATIO_TARGET_DB]
                    cp_best = max(cp_candidates, key=lambda r: r["gain"]) if cp_candidates else min(candidates, key=lambda r: r["axial_ratio"])
                    cp_envelope_rows.append(
                        {
                            "theta": base_row["theta"],
                            "phi": base_row["phi"],
                            "gain": cp_best["gain"],
                            "axial_ratio": cp_best["axial_ratio"],
                        }
                    )
                summaries["coverage_envelope_best_port"] = summarize_rows(freq, envelope_rows)
                summaries["cp_qualified_envelope"] = summarize_rows(freq, cp_envelope_rows)
            summaries_by_freq[f"{freq:.6f}GHz"] = summaries

        metrics = {
            "project": str(PROJECT_PATH),
            "design": DESIGN,
            "sources": sources,
            "available_frequencies_ghz": available_freqs,
            "evaluated_frequencies_ghz": eval_freqs,
            "fov_by_freq": summaries_by_freq,
            "s_parameters": get_s_parameter_snapshot(hfss),
        }
        METRICS_JSON.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
        write_csv(FOV_CSV, summaries_by_freq)
        params = json.loads(PARAM_PATH.read_text(encoding="utf-8"))
        write_report(params, metrics)
        print(json.dumps(metrics, indent=2))
        print(f"Wrote {METRICS_JSON}")
        print(f"Wrote {FOV_CSV}")
        print(f"Wrote {S_CSV}")
        print(f"Wrote {REPORT_MD}")
    finally:
        hfss.release_desktop(close_projects=False, close_desktop=True)


if __name__ == "__main__":
    main()
