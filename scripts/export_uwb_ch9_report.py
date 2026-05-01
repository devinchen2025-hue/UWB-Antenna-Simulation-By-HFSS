from __future__ import annotations

import csv
import json
import math
from pathlib import Path

import numpy as np
from ansys.aedt.core import Hfss


ROOT = Path(__file__).resolve().parents[1]
PROJECT_PATH = ROOT / "UWB_CH9_Diamond_CP_Array.aedt"
PARAM_PATH = ROOT / "UWB_CH9_Diamond_CP_Array_params.json"
REPORT_DIR = ROOT / "reports"
S_CSV = REPORT_DIR / "UWB_CH9_s_parameters.csv"
FARFIELD_CSV = REPORT_DIR / "UWB_CH9_farfield_summary.csv"
METRICS_JSON = REPORT_DIR / "UWB_CH9_metrics.json"
REPORT_MD = REPORT_DIR / "UWB_CH9_simulation_report.md"

DESIGN = "Array4_Diamond_CP_Patch"
SOLUTION = "Setup_CH9 : Sweep_CH9"
SPHERE = "Upper_Hemisphere_5deg"
TARGET_START = 7.738
TARGET_STOP = 8.233
WIDE_START = 7.7
WIDE_STOP = 8.3


def parse_s_term(expr: str) -> tuple[str, str]:
    inside = expr.split("S(", 1)[1].split(")", 1)[0]
    left, right = inside.split(",", 1)
    return left.strip(), right.strip()


def fmt(value, digits: int = 3) -> str:
    if value is None:
        return "N/A"
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return "N/A"
    return f"{value:.{digits}f}"


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        return
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def export_s_parameters(hfss: Hfss) -> dict:
    expressions = hfss.get_traces_for_plot(category="dB(S")
    self_terms = [e for e in expressions if parse_s_term(e)[0] == parse_s_term(e)[1]]
    coupling_terms = [e for e in expressions if e not in self_terms]

    sd = hfss.post.get_solution_data(
        expressions=expressions,
        setup_sweep_name=SOLUTION,
        primary_sweep_variable="Freq",
    )
    freqs = [float(x) for x in sd.primary_sweep_values]
    data = {expr: [float(x) for x in sd.data_real(expr)] for expr in expressions}
    ch9_idx = [i for i, freq in enumerate(freqs) if TARGET_START <= freq <= TARGET_STOP]
    target_idx = [i for i, freq in enumerate(freqs) if WIDE_START <= freq <= WIDE_STOP]

    rows = []
    for i, freq in enumerate(freqs):
        row = {"Freq_GHz": f"{freq:.6f}"}
        for expr in expressions:
            row[expr] = f"{data[expr][i]:.6f}"
        rows.append(row)
    write_csv(S_CSV, rows)

    self_worst = {
        expr: max(data[expr][i] for i in target_idx)
        for expr in self_terms
    }
    ch9_self_worst = {
        expr: max(data[expr][i] for i in ch9_idx)
        for expr in self_terms
    }
    coupling_worst = {
        expr: max(data[expr][i] for i in target_idx)
        for expr in coupling_terms
    }
    worst_return_expr, worst_return_db = max(self_worst.items(), key=lambda item: item[1])
    ch9_worst_return_expr, ch9_worst_return_db = max(ch9_self_worst.items(), key=lambda item: item[1])
    worst_coupling_expr, worst_coupling_db = max(coupling_worst.items(), key=lambda item: item[1])

    return {
        "frequencies_ghz": freqs,
        "target_indices": target_idx,
        "ch9_indices": ch9_idx,
        "expressions": expressions,
        "self_terms": self_terms,
        "coupling_terms": coupling_terms,
        "s_data_db": data,
        "self_worst_db": self_worst,
        "ch9_self_worst_db": ch9_self_worst,
        "coupling_worst_db": coupling_worst,
        "worst_return_expr": worst_return_expr,
        "worst_return_db": worst_return_db,
        "ch9_worst_return_expr": ch9_worst_return_expr,
        "ch9_worst_return_db": ch9_worst_return_db,
        "worst_coupling_expr": worst_coupling_expr,
        "worst_coupling_db": worst_coupling_db,
        "isolation_db": -worst_coupling_db,
    }


def export_group_delay_proxy(hfss: Hfss, s_metrics: dict) -> dict:
    terms = []
    for expr in s_metrics["coupling_terms"]:
        left, right = parse_s_term(expr)
        terms.append(f"S({left},{right})")

    re_exprs = [f"re({term})" for term in terms]
    im_exprs = [f"im({term})" for term in terms]
    sd = hfss.post.get_solution_data(
        expressions=re_exprs + im_exprs,
        setup_sweep_name=SOLUTION,
        primary_sweep_variable="Freq",
    )
    freqs = np.array([float(x) for x in sd.primary_sweep_values], dtype=float)
    omega = 2.0 * np.pi * freqs * 1e9
    target_idx = np.array(s_metrics["target_indices"], dtype=int)

    results = {}
    for term, re_expr, im_expr in zip(terms, re_exprs, im_exprs):
        real = np.array([float(x) for x in sd.data_real(re_expr)], dtype=float)
        imag = np.array([float(x) for x in sd.data_real(im_expr)], dtype=float)
        phase = np.unwrap(np.angle(real + 1j * imag))
        group_delay_s = -np.gradient(phase, omega)
        group_delay_ps = group_delay_s * 1e12
        band = group_delay_ps[target_idx]
        results[term] = {
            "min_ps": float(np.min(band)),
            "max_ps": float(np.max(band)),
            "max_abs_ps": float(np.max(np.abs(band))),
        }

    worst_term, worst = max(results.items(), key=lambda item: item[1]["max_abs_ps"])
    return {
        "note": "Proxy computed from unwrapped mutual-coupling Sij phase; not a substitute for a two-antenna time-domain fidelity setup.",
        "per_term": results,
        "worst_term": worst_term,
        "worst_max_abs_ps": worst["max_abs_ps"],
    }


def farfield_values(hfss: Hfss, expression: str, freq_ghz: float) -> list[float] | None:
    freq = f"{freq_ghz:g}GHz"
    try:
        sd = hfss.post.get_solution_data(
            expressions=expression,
            setup_sweep_name=SOLUTION,
            domain="Sweep",
            variations={"Freq": [freq], "Theta": ["All"], "Phi": ["All"]},
            primary_sweep_variable="Phi",
            report_category="Far Fields",
            context=SPHERE,
        )
        if not sd:
            return None
        return [float(x) for x in sd.data_real(expression)]
    except Exception:
        return None


def export_farfield_summary(hfss: Hfss, s_metrics: dict) -> dict:
    freqs = s_metrics["frequencies_ghz"]
    sample_freqs = [
        min(freqs, key=lambda x: abs(x - TARGET_START)),
        min(freqs, key=lambda x: abs(x - 8.0)),
        min(freqs, key=lambda x: abs(x - TARGET_STOP)),
    ]

    rows = []
    summary = {}
    for freq in sample_freqs:
        gain = farfield_values(hfss, "dB(GainTotal)", freq)
        realized = farfield_values(hfss, "dB(RealizedGainTotal)", freq)
        axial = farfield_values(hfss, "AxialRatioValue", freq)
        row = {
            "Freq_GHz": f"{freq:.6f}",
            "GainTotal_min_dBi": fmt(min(gain) if gain else None, 6),
            "GainTotal_max_dBi": fmt(max(gain) if gain else None, 6),
            "GainTotal_ripple_dB": fmt((max(gain) - min(gain)) if gain else None, 6),
            "RealizedGainTotal_min_dBi": fmt(min(realized) if realized else None, 6),
            "RealizedGainTotal_max_dBi": fmt(max(realized) if realized else None, 6),
            "AxialRatioValue_min": fmt(min(axial) if axial else None, 6),
            "AxialRatioValue_max": fmt(max(axial) if axial else None, 6),
        }
        rows.append(row)
        summary[f"{freq:.6f}GHz"] = row
    write_csv(FARFIELD_CSV, rows)
    return {
        "note": "Far-field values use the default HFSS source context on Upper_Hemisphere_5deg; dedicated per-port or phased-combined source contexts are still required for final antenna-pattern signoff.",
        "samples": summary,
    }


def write_report(params: dict, metrics: dict) -> None:
    s = metrics["s_parameters"]
    gd = metrics["group_delay_proxy"]
    ff = metrics["farfield_summary"]

    lines = [
        "# UWB CH9 Diamond Microstrip-Fed Array HFSS Simulation Report",
        "",
        "## Project",
        "",
        f"- AEDT project: `{PROJECT_PATH}`",
        f"- Design: `{DESIGN}`",
        "- AEDT version used by automation: 2023.1",
        "- Python/PyAEDT automation: `ansys.aedt.core`",
        "",
        "## Geometry Snapshot",
        "",
        "- Topology: four microstrip-fed planar UWB monopole elements in diamond layout.",
        f"- Nearest-neighbor spacing: `{params['nearest_neighbor_spacing_mm']} mm`",
        f"- Board: `{params['parameters']['board_side_mm']} mm x {params['parameters']['board_side_mm']} mm`",
        f"- Substrate: RO4350B-like, h=`{params['parameters']['substrate_h_mm']} mm`, epsr=`{params['parameters']['epsr']}`, tan_delta=`{params['parameters']['tan_delta']}`",
        f"- Radiator disc radius: `{params['parameters']['disc_radius_mm']} mm`",
        f"- Feed width: `{params['parameters']['feed_w_mm']} mm`",
        f"- Partial ground width/gap: `{params['parameters']['partial_ground_w_mm']} mm` / `{params['parameters']['partial_ground_gap_mm']} mm`",
        "",
        "## Requirement Check",
        "",
        "| Item | Target | Simulated Result | Status |",
        "| --- | --- | --- | --- |",
        f"| S11/S22/S33/S44 | < -10 dB @ 7.7-8.3 GHz | worst `{fmt(s['worst_return_db'])} dB` at `{s['worst_return_expr']}` | {'PASS' if s['worst_return_db'] < -10 else 'FAIL'} |",
        f"| Isolation | > 25 dB | worst coupling `{fmt(s['worst_coupling_db'])} dB`, isolation `{fmt(s['isolation_db'])} dB` at `{s['worst_coupling_expr']}` | {'PASS' if s['isolation_db'] > 25 else 'FAIL'} |",
        f"| Group delay | < 100 ps | Sij phase proxy max abs `{fmt(gd['worst_max_abs_ps'])} ps` at `{gd['worst_term']}` | {'PASS (proxy)' if gd['worst_max_abs_ps'] < 100 else 'FAIL (proxy)'} |",
        "| Circular polarization / axial ratio | AR <= 3 dB full band | default-source far-field AR is exported; this single-feed monopole topology is not a verified CP element | NOT MET / NEEDS REDESIGN |",
        "| Upper-hemisphere gain coverage | edge min >= -5 dBi, ripple <= 3 dB | default-source far-field summary exported; not final per-port/phased source signoff | NEEDS DEDICATED SOURCE SETUP |",
        "| Phase-center stability | +/-0.2 mm | not extracted in this automation pass | NOT VERIFIED |",
        "| Fidelity factor | >= 99% | not extracted; requires time-domain two-antenna/pulse correlation setup | NOT VERIFIED |",
        "",
        "## S-Parameter Details",
        "",
        f"- Full S-parameter CSV: `{S_CSV}`",
        f"- Worst in-band return loss term: `{s['worst_return_expr']}` = `{fmt(s['worst_return_db'])} dB`",
        f"- Worst CH9 nominal-band return loss term: `{s['ch9_worst_return_expr']}` = `{fmt(s['ch9_worst_return_db'])} dB`",
        f"- Worst in-band coupling term: `{s['worst_coupling_expr']}` = `{fmt(s['worst_coupling_db'])} dB`",
        "",
        "Per-port worst return loss in target band:",
        "",
    ]
    for expr, value in sorted(s["self_worst_db"].items()):
        lines.append(f"- `{expr}`: `{fmt(value)} dB`")

    lines.extend([
        "",
        "## Far-Field Summary",
        "",
        f"- Far-field CSV: `{FARFIELD_CSV}`",
        f"- Note: {ff['note']}",
        "",
        "| Freq | GainTotal min/max/ripple | RealizedGainTotal min/max | AxialRatioValue min/max |",
        "| --- | --- | --- | --- |",
    ])
    for freq, row in ff["samples"].items():
        lines.append(
            "| "
            + freq
            + " | "
            + f"{row['GainTotal_min_dBi']} / {row['GainTotal_max_dBi']} / {row['GainTotal_ripple_dB']} dB"
            + " | "
            + f"{row['RealizedGainTotal_min_dBi']} / {row['RealizedGainTotal_max_dBi']} dBi"
            + " | "
            + f"{row['AxialRatioValue_min']} / {row['AxialRatioValue_max']}"
            + " |"
        )

    lines.extend([
        "",
        "## Engineering Notes",
        "",
        "- A conventional full-ground microstrip patch was checked first and was not size-compatible with 17 mm element spacing at 8 GHz on the selected substrate.",
        "- The current solved model uses a planar microstrip-fed UWB monopole because it can meet the CH9 return-loss band in this footprint.",
        "- Attempts with central via fences and thin septum walls did not improve isolation beyond about 20 dB and degraded matching.",
        "- To reach all requested CP, isolation, phase-center, and fidelity requirements, the next design iteration should move to a true CP radiator/feed network and a dedicated decoupling structure, or relax either spacing, layer count, or available board area.",
    ])

    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    if (ROOT / "UWB_CH9_Diamond_CP_Array.aedt.lock").exists():
        (ROOT / "UWB_CH9_Diamond_CP_Array.aedt.lock").unlink()

    params = json.loads(PARAM_PATH.read_text(encoding="utf-8"))
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
        s_metrics = export_s_parameters(hfss)
        group_delay = export_group_delay_proxy(hfss, s_metrics)
        farfield = export_farfield_summary(hfss, s_metrics)
        metrics = {
            "project": str(PROJECT_PATH),
            "design": DESIGN,
            "s_parameters": {k: v for k, v in s_metrics.items() if k != "s_data_db"},
            "group_delay_proxy": group_delay,
            "farfield_summary": farfield,
        }
        METRICS_JSON.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
        write_report(params, metrics)
    finally:
        hfss.release_desktop(close_projects=False, close_desktop=True)

    print(f"Wrote {S_CSV}")
    print(f"Wrote {FARFIELD_CSV}")
    print(f"Wrote {METRICS_JSON}")
    print(f"Wrote {REPORT_MD}")


if __name__ == "__main__":
    main()
