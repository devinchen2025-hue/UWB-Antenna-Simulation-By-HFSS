from __future__ import annotations

import argparse
import csv
import json
import math
import re
from pathlib import Path

from ansys.aedt.core import Hfss

import build_uwb_ch9_hfss_d44_topology as builder


ROOT = Path(__file__).resolve().parents[1]
SOLUTION = "Setup_CH9 : Sweep_CH9"
SPHERE = "Upper_Hemisphere_5deg"
TARGET_FREQS_GHZ = [7.738, 8.0, 8.233]
FOV_TEXT = "Theta 0-360 deg, Phi 45-90 deg"
GAIN_MIN_TARGET_DBI = -5.0
AXIAL_RATIO_TARGET_DB = 3.0


def report_paths(topology: str) -> dict[str, Path]:
    label = builder.TOPOLOGIES[topology]["label"].lower()
    report_dir = ROOT / f"reports_d44_{label.lower()}"
    stem = f"UWB_CH9_D44_{builder.TOPOLOGIES[topology]['label']}"
    return {
        "dir": report_dir,
        "metrics": report_dir / f"{stem}_metrics.json",
        "fov_csv": report_dir / f"{stem}_fov_cp_metrics.csv",
        "s_csv": report_dir / f"{stem}_s_parameters.csv",
        "report": report_dir / f"{stem}_simulation_report.md",
    }


def axis_values(sd, axis: str) -> list[float]:
    return [float(str(raw).replace("deg", "")) for raw in sd.intrinsics.get(axis, [])]


def parse_s_term(expr: str) -> tuple[str, str]:
    inside = expr.split("S(", 1)[1].split(")", 1)[0]
    left, right = inside.split(",", 1)
    return left.strip(), right.strip()


def get_available_frequencies(hfss: Hfss) -> list[float]:
    expressions = hfss.get_traces_for_plot(category="dB(S")
    if not expressions:
        return [8.0]
    sd = hfss.post.get_solution_data(expressions=expressions[0], setup_sweep_name=SOLUTION, primary_sweep_variable="Freq")
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
        raise RuntimeError(f"Unexpected far-field grid length: gain={len(gains)}, ar={len(axial)}, expected={expected}")

    rows = []
    idx = 0
    for phi in phi_vals:
        for theta in theta_vals:
            rows.append({"theta": theta, "phi": phi, "gain": gains[idx], "axial_ratio": axial[idx]})
            idx += 1
    return {"theta_values": theta_vals, "phi_values": phi_vals, "rows": rows}


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


def sequential_assignments(sources: list[str], phase_step_deg: float = -90.0) -> dict[str, tuple[float, float]]:
    return {source: (1.0, idx * phase_step_deg) for idx, source in enumerate(sources)}


def element_pair_map(sources: list[str]) -> dict[str, dict[str, str]]:
    pairs: dict[str, dict[str, str]] = {}
    for source in sources:
        match = re.fullmatch(r"P(\d+)([AB])", source)
        if match:
            pairs.setdefault(match.group(1), {})[match.group(2)] = source
    return {key: value for key, value in pairs.items() if {"A", "B"} <= set(value)}


def source_cases(sources: list[str], topology: str) -> dict[str, dict[str, tuple[float, float]]]:
    cases: dict[str, dict[str, tuple[float, float]]] = {}
    for src in sources:
        cases[f"{src}_only"] = {item: (1.0 if item == src else 0.0, 0.0) for item in sources}

    if len(sources) > 1:
        cases["sequential_quadrature_all_ports"] = sequential_assignments(sources)

    pairs = element_pair_map(sources)
    if pairs:
        for element, pair in pairs.items():
            assignments = {item: (0.0, 0.0) for item in sources}
            assignments[pair["A"]] = (1.0, 0.0)
            assignments[pair["B"]] = (1.0, -90.0)
            cases[f"E{element}_dualfeed_quadrature"] = assignments

        assignments = {item: (0.0, 0.0) for item in sources}
        for idx, element in enumerate(sorted(pairs, key=int)):
            pair = pairs[element]
            base_phase = idx * -90.0
            assignments[pair["A"]] = (1.0, base_phase)
            assignments[pair["B"]] = (1.0, base_phase - 90.0)
        case_name = "ideal_hybrid_array_quadrature" if topology == "hybrid" else "dualfeed_array_quadrature"
        cases[case_name] = assignments
    return cases


def get_s_parameter_snapshot(hfss: Hfss, s_csv: Path) -> dict:
    expressions = hfss.get_traces_for_plot(category="dB(S")
    sd = hfss.post.get_solution_data(expressions=expressions, setup_sweep_name=SOLUTION, primary_sweep_variable="Freq")
    freqs = [float(x) for x in sd.primary_sweep_values]
    s_data = {expr: [float(x) for x in sd.data_real(expr)] for expr in expressions}
    rows = []
    for idx, freq in enumerate(freqs):
        row = {"Freq_GHz": f"{freq:.6f}"}
        for expr in expressions:
            row[expr] = f"{s_data[expr][idx]:.6f}"
        rows.append(row)
    if rows:
        with s_csv.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)

    target_indices = [i for i, freq in enumerate(freqs) if TARGET_FREQS_GHZ[0] - 1e-9 <= freq <= TARGET_FREQS_GHZ[-1] + 1e-9] or list(range(len(freqs)))
    self_terms = {}
    coupling_terms = {}
    for expr in expressions:
        left, right = parse_s_term(expr)
        worst = max(s_data[expr][i] for i in target_indices)
        if left == right:
            self_terms[expr] = worst
        else:
            coupling_terms[expr] = worst
    worst_return_expr, worst_return_db = max(self_terms.items(), key=lambda item: item[1])
    if coupling_terms:
        worst_coupling_expr, worst_coupling_db = max(coupling_terms.items(), key=lambda item: item[1])
    else:
        worst_coupling_expr, worst_coupling_db = "N/A", float("nan")
    return {
        "frequencies_ghz": freqs,
        "target_band_ghz": [TARGET_FREQS_GHZ[0], TARGET_FREQS_GHZ[-1]],
        "self_worst_db": self_terms,
        "coupling_worst_db": coupling_terms,
        "worst_return_expr": worst_return_expr,
        "worst_return_db": worst_return_db,
        "worst_coupling_expr": worst_coupling_expr,
        "worst_coupling_db": worst_coupling_db,
        "isolation_db": -worst_coupling_db if not math.isnan(worst_coupling_db) else float("nan"),
    }


def write_csv(path: Path, summaries_by_freq: dict[str, dict[str, dict]]) -> None:
    rows = []
    for summaries in summaries_by_freq.values():
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
    if rows:
        with path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)


def summarize_fov(metrics: dict) -> dict:
    envelope_gain = []
    cp_ar = []
    cp_gain = []
    cp_coverage = []
    key_cases = {}
    for summaries in metrics.get("fov_by_freq", {}).values():
        cov = summaries.get("coverage_envelope_best_port")
        cp = summaries.get("cp_qualified_envelope")
        if cov:
            envelope_gain.append(cov["gain_min_dbi"])
        if cp:
            cp_ar.append(cp["axial_ratio_max_db"])
            cp_gain.append(cp["gain_min_dbi"])
            cp_coverage.append(cp["cp_coverage_percent"])
        for name, item in summaries.items():
            if "quadrature" in name:
                key_cases.setdefault(name, []).append(item)
    quadrature = {}
    for name, items in key_cases.items():
        quadrature[name] = {
            "gain_min_dbi": min(item["gain_min_dbi"] for item in items),
            "axial_ratio_max_db": max(item["axial_ratio_max_db"] for item in items),
            "cp_coverage_min_percent": min(item["cp_coverage_percent"] for item in items),
        }
    return {
        "coverage_envelope_gain_min_dbi": min(envelope_gain) if envelope_gain else float("nan"),
        "cp_qualified_ar_max_db": max(cp_ar) if cp_ar else float("nan"),
        "cp_qualified_gain_min_dbi": min(cp_gain) if cp_gain else float("nan"),
        "cp_qualified_coverage_min_percent": min(cp_coverage) if cp_coverage else 0.0,
        "quadrature_cases": quadrature,
    }


def fmt(value: float | int | None, digits: int = 2) -> str:
    if value is None:
        return "N/A"
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return "N/A"
    return f"{float(value):.{digits}f}"


def write_report(topology: str, params: dict, metrics: dict, report_md: Path) -> None:
    spec = builder.TOPOLOGIES[topology]
    s = metrics.get("s_parameters", {})
    summary = metrics.get("fov_summary", {})
    p = params["parameters"]
    lines = [
        f"# UWB CH9 D44 {spec['label']} 仿真报告",
        "",
        "## 模型",
        "",
        f"- AEDT 项目：`{metrics['project']}`",
        f"- 设计名：`{metrics['design']}`",
        f"- 拓扑：{spec['description']}",
        f"- PCB 直径：`{p['board_diameter_mm']} mm`",
        f"- 总高度约束：`<= {p['total_height_limit_mm']} mm`",
        f"- 板厚：`{p['substrate_h_mm']} mm`",
        f"- 贴片边长：`{p['patch_side_mm']} mm`",
        f"- 截角：`{p.get('corner_cut_mm', 0.0)} mm`",
        "",
        "## 核心指标",
        "",
        f"- 最差回波损耗：`{fmt(s.get('worst_return_db'))} dB`，表达式 `{s.get('worst_return_expr', 'N/A')}`",
        f"- 最差耦合：`{fmt(s.get('worst_coupling_db'))} dB`，表达式 `{s.get('worst_coupling_expr', 'N/A')}`",
        f"- 对应隔离度：`{fmt(s.get('isolation_db'))} dB`",
        f"- 最佳端口覆盖包络最小增益：`{fmt(summary.get('coverage_envelope_gain_min_dbi'))} dBi`",
        f"- CP 合格包络最大轴比：`{fmt(summary.get('cp_qualified_ar_max_db'))} dB`",
        f"- CP 合格包络最小增益：`{fmt(summary.get('cp_qualified_gain_min_dbi'))} dBi`",
        f"- CP 覆盖率最小值：`{fmt(summary.get('cp_qualified_coverage_min_percent'), 1)}%`",
        "",
        "## 关键激励场景",
        "",
        "| 场景 | 最小增益 | 最大轴比 | CP 覆盖率最小值 |",
        "| --- | ---: | ---: | ---: |",
    ]
    for name, item in summary.get("quadrature_cases", {}).items():
        lines.append(
            f"| {name} | {fmt(item['gain_min_dbi'])} dBi | {fmt(item['axial_ratio_max_db'])} dB | {fmt(item['cp_coverage_min_percent'], 1)}% |"
        )

    lines.extend(
        [
            "",
            "## 结论",
            "",
            "- 该版本已完成 HFSS 建模、三频点快速求解、S 参数导出和 FOV/轴比后处理。",
            "- 是否最终达标需要同时查看 S 参数、FOV 最小增益和全 FOV 轴比；详细数据见同目录 CSV/JSON。",
            "",
            "## 文件",
            "",
            f"- 指标 JSON：`{metrics['metrics_json']}`",
            f"- FOV CSV：`{metrics['fov_csv']}`",
            f"- S 参数 CSV：`{metrics['s_csv']}`",
        ]
    )
    report_md.write_text("\n".join(lines) + "\n", encoding="utf-8")


def evaluate(topology: str) -> dict:
    spec = builder.TOPOLOGIES[topology]
    paths = builder.topology_paths(topology)
    reports = report_paths(topology)
    reports["dir"].mkdir(parents=True, exist_ok=True)
    if paths["project"].with_suffix(".aedt.lock").exists():
        try:
            paths["project"].with_suffix(".aedt.lock").unlink()
        except OSError:
            pass

    hfss = Hfss(
        project=str(paths["project"]),
        design=spec["design"],
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
        cases = source_cases(sources, topology)
        summaries_by_freq = {}
        for freq in eval_freqs:
            summaries = {}
            single_grids = {}
            for name, assignments in cases.items():
                if assignments:
                    hfss.edit_sources(assignments)
                grid = get_grid(hfss, freq)
                summaries[name] = summarize_rows(freq, grid["rows"])
                if name.endswith("_only"):
                    single_grids[name] = grid
            if single_grids:
                first_grid = next(iter(single_grids.values()))
                envelope_rows = []
                cp_rows = []
                for idx, base_row in enumerate(first_grid["rows"]):
                    candidates = [grid["rows"][idx] for grid in single_grids.values()]
                    best = max(candidates, key=lambda r: r["gain"])
                    envelope_rows.append({"theta": base_row["theta"], "phi": base_row["phi"], "gain": best["gain"], "axial_ratio": best["axial_ratio"]})
                    cp_candidates = [r for r in candidates if r["axial_ratio"] <= AXIAL_RATIO_TARGET_DB]
                    cp_best = max(cp_candidates, key=lambda r: r["gain"]) if cp_candidates else min(candidates, key=lambda r: r["axial_ratio"])
                    cp_rows.append({"theta": base_row["theta"], "phi": base_row["phi"], "gain": cp_best["gain"], "axial_ratio": cp_best["axial_ratio"]})
                summaries["coverage_envelope_best_port"] = summarize_rows(freq, envelope_rows)
                summaries["cp_qualified_envelope"] = summarize_rows(freq, cp_rows)
            summaries_by_freq[f"{freq:.6f}GHz"] = summaries

        metrics = {
            "project": str(paths["project"]),
            "design": spec["design"],
            "topology": topology,
            "label": spec["label"],
            "sources": sources,
            "available_frequencies_ghz": available_freqs,
            "evaluated_frequencies_ghz": eval_freqs,
            "fov_by_freq": summaries_by_freq,
            "s_parameters": get_s_parameter_snapshot(hfss, reports["s_csv"]),
        }
        metrics["fov_summary"] = summarize_fov(metrics)
        metrics["metrics_json"] = str(reports["metrics"])
        metrics["fov_csv"] = str(reports["fov_csv"])
        metrics["s_csv"] = str(reports["s_csv"])
        reports["metrics"].write_text(json.dumps(metrics, indent=2), encoding="utf-8")
        write_csv(reports["fov_csv"], summaries_by_freq)
        params = json.loads(paths["params"].read_text(encoding="utf-8"))
        write_report(topology, params, metrics, reports["report"])
        print(json.dumps(metrics["fov_summary"], indent=2))
        print(json.dumps(metrics["s_parameters"], indent=2))
        print(f"Wrote {reports['metrics']}")
        print(f"Wrote {reports['fov_csv']}")
        print(f"Wrote {reports['s_csv']}")
        print(f"Wrote {reports['report']}")
        return metrics
    finally:
        hfss.release_desktop(close_projects=False, close_desktop=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--topology", choices=sorted(builder.TOPOLOGIES), required=True)
    args = parser.parse_args()
    evaluate(args.topology)


if __name__ == "__main__":
    main()
