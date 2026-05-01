from __future__ import annotations

import csv
import json
import math
from pathlib import Path

from ansys.aedt.core import Hfss


ROOT = Path(__file__).resolve().parents[1]
PROJECT_PATH = ROOT / "UWB_CH9_Diamond_CP_Array_D44_FOV.aedt"
PARAM_PATH = ROOT / "UWB_CH9_Diamond_CP_Array_D44_FOV_params.json"
REPORT_DIR = ROOT / "reports_d44_fov"
METRICS_JSON = REPORT_DIR / "UWB_CH9_D44_FOV_metrics.json"
FOV_CSV = REPORT_DIR / "UWB_CH9_D44_FOV_fov_metrics.csv"
REPORT_MD = REPORT_DIR / "UWB_CH9_D44_FOV_simulation_report.md"
DESIGN = "Array4_Diamond_D44_FOV"
SOLUTION = "Setup_CH9 : Sweep_CH9"
SPHERE = "Upper_Hemisphere_5deg"
TARGET_FREQS_GHZ = [7.738, 8.0, 8.233]


def axis_values(sd, axis: str) -> list[float]:
    values = []
    for raw in sd.intrinsics.get(axis, []):
        values.append(float(str(raw).replace("deg", "")))
    return values


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


def get_grid(hfss: Hfss, freq_ghz: float, expression: str = "dB(GainTotal)") -> dict:
    sd = hfss.post.get_solution_data(
        expressions=expression,
        setup_sweep_name=SOLUTION,
        domain="Sweep",
        variations={"Freq": [f"{freq_ghz:g}GHz"], "Theta": ["All"], "Phi": ["All"]},
        primary_sweep_variable="Phi",
        report_category="Far Fields",
        context=SPHERE,
    )
    theta_vals = axis_values(sd, "Theta")
    phi_vals = axis_values(sd, "Phi")
    values = [float(x) for x in sd.data_real(expression)]
    expected = len(theta_vals) * len(phi_vals)
    if len(values) != expected:
        raise RuntimeError(
            f"Unexpected grid length for {expression}: {len(values)} != {expected}"
        )

    rows = []
    idx = 0
    for phi in phi_vals:
        for theta in theta_vals:
            rows.append({"theta": theta, "phi": phi, "value": values[idx]})
            idx += 1
    return {
        "theta_values": theta_vals,
        "phi_values": phi_vals,
        "rows": rows,
    }


def summarize_rows(freq_ghz: float, rows: list[dict], value_key: str = "value") -> dict:
    roi = [
        r for r in rows
        if 0.0 <= r["theta"] <= 360.0 and 45.0 <= r["phi"] <= 90.0
    ]
    min_row = min(roi, key=lambda r: r[value_key])
    max_row = max(roi, key=lambda r: r[value_key])
    return {
        "freq_ghz": freq_ghz,
        "fov": "Theta 0-360 deg, Phi 45-90 deg",
        "sample_count": len(roi),
        "gain_min_dbi": min_row[value_key],
        "gain_max_dbi": max_row[value_key],
        "gain_ripple_db": max_row[value_key] - min_row[value_key],
        "gain_min_point": {
            "theta_deg": min_row["theta"],
            "phi_deg": min_row["phi"],
            "gain_dbi": min_row[value_key],
        },
        "gain_max_point": {
            "theta_deg": max_row["theta"],
            "phi_deg": max_row["phi"],
            "gain_dbi": max_row[value_key],
        },
    }


def edit_sources_safe(hfss: Hfss, assignments: dict[str, tuple[float, float]]) -> None:
    if not assignments:
        return
    hfss.edit_sources(assignments)


def get_s_parameter_snapshot(hfss: Hfss, freq_ghz: float) -> dict:
    try:
        expressions = hfss.get_traces_for_plot(category="dB(S")
        sd = hfss.post.get_solution_data(
            expressions=expressions,
            setup_sweep_name=SOLUTION,
            primary_sweep_variable="Freq",
        )
        freqs = [float(x) for x in sd.primary_sweep_values]
        idx = min(range(len(freqs)), key=lambda i: abs(freqs[i] - freq_ghz))
        data = {expr: float(sd.data_real(expr)[idx]) for expr in expressions}
        self_terms = {
            expr: value for expr, value in data.items()
            if expr.split("S(", 1)[1].split(")", 1)[0].split(",", 1)[0].strip()
            == expr.split("S(", 1)[1].split(")", 1)[0].split(",", 1)[1].strip()
        }
        coupling = {expr: value for expr, value in data.items() if expr not in self_terms}
        return {
            "freq_ghz": freqs[idx],
            "self_terms_db": self_terms,
            "coupling_terms_db": coupling,
            "worst_return_db": max(self_terms.values()) if self_terms else None,
            "worst_coupling_db": max(coupling.values()) if coupling else None,
        }
    except Exception as exc:
        return {"error": str(exc)}


def write_csv(path: Path, summaries_by_freq: dict[str, dict[str, dict]]) -> None:
    rows = []
    for _, summaries in summaries_by_freq.items():
        for name, item in summaries.items():
            rows.append(
                {
                    "source_case": name,
                    "freq_ghz": f"{item['freq_ghz']:.6f}",
                    "gain_min_dbi": f"{item['gain_min_dbi']:.6f}",
                    "gain_max_dbi": f"{item['gain_max_dbi']:.6f}",
                    "gain_ripple_db": f"{item['gain_ripple_db']:.6f}",
                    "min_theta_deg": f"{item['gain_min_point']['theta_deg']:.6f}",
                    "min_phi_deg": f"{item['gain_min_point']['phi_deg']:.6f}",
                    "max_theta_deg": f"{item['gain_max_point']['theta_deg']:.6f}",
                    "max_phi_deg": f"{item['gain_max_point']['phi_deg']:.6f}",
                    "meets_min_gain_ge_minus5": item["gain_min_dbi"] >= -5.0,
                }
            )
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def fmt(value: float | None, digits: int = 2) -> str:
    if value is None or (isinstance(value, float) and (math.isnan(value) or math.isinf(value))):
        return "N/A"
    return f"{value:.{digits}f}"


def write_report(params: dict, metrics: dict) -> None:
    freq_list = " / ".join(metrics["fov_by_freq"].keys())
    lines = [
        "# UWB CH9 D44 FOV结构仿真报告",
        "",
        "## 模型",
        "",
        f"- AEDT项目: `{PROJECT_PATH}`",
        f"- 设计名: `{DESIGN}`",
        "- 结构: 四阵元菱形布阵，每个阵元改为顶加载垂直单极子，用于获得近似甜甜圈方向图。",
        f"- PCB直径: `{params['parameters']['board_diameter_mm']} mm`",
        f"- 阵元间距: `{params['nearest_neighbor_spacing_mm']} mm`",
        f"- 单极子高度: `{params['parameters']['monopole_height_mm']} mm`",
        f"- 电容帽半径: `{params['parameters']['top_hat_radius_mm']} mm`",
        "",
        "## FOV指标",
        "",
        f"- 评估频点: `{freq_list}`，若工程只有单点解则自动使用已有频点。",
        "- FOV区域: `Theta=0-360 deg, Phi=45-90 deg`",
        "- 判据: `GainTotal`最小值 >= `-5 dBi`",
        "",
        "| 频点 | 源设置 | 最小增益 | 最大增益 | 起伏 | 最小值位置 | 结论 |",
        "| ---: | --- | ---: | ---: | ---: | --- | --- |",
    ]
    for freq_key, summaries in metrics["fov_by_freq"].items():
        for name, item in summaries.items():
            status = "通过" if item["gain_min_dbi"] >= -5.0 else "未通过"
            min_point = item["gain_min_point"]
            lines.append(
                f"| {freq_key} | {name} | {fmt(item['gain_min_dbi'])} dBi | "
                f"{fmt(item['gain_max_dbi'])} dBi | {fmt(item['gain_ripple_db'])} dB | "
                f"Theta={fmt(min_point['theta_deg'], 0)} deg, Phi={fmt(min_point['phi_deg'], 0)} deg | {status} |"
            )

    s = metrics.get("s_parameters", [{}])[0] if metrics.get("s_parameters") else {}
    lines.extend(
        [
            "",
            "## S参数快照",
            "",
            f"- 最差回波损耗: `{fmt(s.get('worst_return_db'), 2)} dB`",
            f"- 最差耦合: `{fmt(s.get('worst_coupling_db'), 2)} dB`",
            "",
            "## 工程说明",
            "",
            "- `equal_phase_all_ports`是四端口等幅同相激励，会包含阵因子零陷；这不是PDOA接收阵列的常规单通道方向图判据。",
            "- `coverage_envelope_best_port`表示四个阵元中每个方向取最强端口，是评估360度覆盖可用性的更合理视角。",
            "- 当前版本优先解决FOV最小增益和甜甜圈形方向图；圆极化、隔离度和群时延仍需要后续结构细化。",
            f"- 详细数据CSV: `{FOV_CSV}`",
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
        source_cases["equal_phase_all_ports"] = {item: (1.0, 0.0) for item in sources}

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
                for idx, base_row in enumerate(first_grid["rows"]):
                    best = max(grid["rows"][idx]["value"] for grid in per_port_grids.values())
                    envelope_rows.append(
                        {"theta": base_row["theta"], "phi": base_row["phi"], "value": best}
                    )
                summaries["coverage_envelope_best_port"] = summarize_rows(freq, envelope_rows)
            summaries_by_freq[f"{freq:.6f}GHz"] = summaries

        metrics = {
            "project": str(PROJECT_PATH),
            "design": DESIGN,
            "sources": sources,
            "available_frequencies_ghz": available_freqs,
            "evaluated_frequencies_ghz": eval_freqs,
            "fov_by_freq": summaries_by_freq,
            "s_parameters": [get_s_parameter_snapshot(hfss, freq) for freq in eval_freqs],
        }
        METRICS_JSON.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
        write_csv(FOV_CSV, summaries_by_freq)
        params = json.loads(PARAM_PATH.read_text(encoding="utf-8"))
        write_report(params, metrics)
        print(json.dumps(metrics, indent=2))
        print(f"Wrote {METRICS_JSON}")
        print(f"Wrote {FOV_CSV}")
        print(f"Wrote {REPORT_MD}")
    finally:
        hfss.release_desktop(close_projects=False, close_desktop=True)


if __name__ == "__main__":
    main()
