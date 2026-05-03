from __future__ import annotations

import argparse
import csv
import json
import math
import time
from dataclasses import dataclass
from pathlib import Path

from ansys.aedt.core import Hfss

import build_uwb_ch9_hfss_d44_topology as builder
import evaluate_uwb_ch9_d44_topology as evaluator


ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = ROOT / "reports_d44_dualfeed_hybrid_opt"
HISTORY_CSV = REPORT_DIR / "UWB_CH9_D44_DUALFEED_HYBRID_optimization_history.csv"
BALANCE_CSV = REPORT_DIR / "UWB_CH9_D44_DUALFEED_HYBRID_source_balance.csv"
BEST_JSON = REPORT_DIR / "UWB_CH9_D44_DUALFEED_HYBRID_best.json"
REPORT_MD = REPORT_DIR / "UWB_CH9_D44_DUALFEED_HYBRID_optimization_report.md"

RETURN_TARGET_DB = -10.0
ISOLATION_TARGET_DB = 15.0
GAIN_TARGET_DBI = -5.0
AR_TARGET_DB = 3.0


@dataclass(frozen=True)
class Candidate:
    name: str
    topology: str
    params: dict[str, float]
    rationale: str


def base_params(topology: str) -> dict[str, float]:
    params = dict(builder.TOPOLOGIES[topology]["params"])
    return params


def make_candidate(
    topology: str,
    name: str,
    patch: float,
    feed: float,
    rationale: str,
    *,
    port_width: float = 0.70,
    pad: float = 0.42,
    feed_a: float | None = None,
    feed_b: float | None = None,
    slot_len: float = 10.0,
    slot_width: float = 0.42,
    trace_width: float | None = None,
    trace_gap: float | None = None,
) -> Candidate:
    params = base_params(topology)
    params.update(
        {
            "patch_side_mm": patch,
            "feed_offset_u_mm": feed,
            "feed_pad_radius_mm": pad,
            "port_width_mm": port_width,
            "isolation_slot_length_mm": slot_len,
            "isolation_slot_width_mm": slot_width,
        }
    )
    if feed_a is not None:
        params["feed_offset_a_mm"] = feed_a
    if feed_b is not None:
        params["feed_offset_b_mm"] = feed_b
    if trace_width is not None:
        params["hybrid_trace_width_mm"] = trace_width
    if trace_gap is not None:
        params["hybrid_trace_gap_mm"] = trace_gap
    return Candidate(name=f"{topology}_{name}", topology=topology, params=params, rationale=rationale)


def generate_candidates() -> list[Candidate]:
    candidates = [
        make_candidate("dualfeed", "baseline", 9.15, 2.45, "Previous dual-feed topology baseline."),
        make_candidate("hybrid", "baseline", 9.15, 2.45, "Previous 90-degree hybrid topology baseline."),
        make_candidate("dualfeed", "feed_1p6", 9.15, 1.60, "Move both feeds inward to test lower input resistance."),
        make_candidate("dualfeed", "feed_3p4", 9.15, 3.40, "Move both feeds outward to test higher input resistance."),
        make_candidate("dualfeed", "feed_3p2", 9.15, 3.20, "Fine sweep between baseline and the 3.4 mm best point."),
        make_candidate("dualfeed", "feed_3p3", 9.15, 3.30, "Fine sweep just inside the 3.4 mm best point."),
        make_candidate("dualfeed", "feed_3p4_wide_port", 9.15, 3.40, "Keep best feed offset and increase local feed capacitance.", port_width=1.05, pad=0.55),
        make_candidate("dualfeed", "feed_3p4_narrow_port", 9.15, 3.40, "Keep best feed offset and reduce local feed capacitance.", port_width=0.45, pad=0.35),
        make_candidate("dualfeed", "feed_3p6", 9.15, 3.60, "Fine sweep outward from the best return-loss trend."),
        make_candidate("dualfeed", "feed_3p8", 9.15, 3.80, "Continue outward feed sweep toward the patch edge for matching."),
        make_candidate("dualfeed", "patch_9p7_feed_3p4", 9.70, 3.40, "Lower resonance and move feeds outward."),
        make_candidate("dualfeed", "patch_10p0_feed_3p5", 10.00, 3.50, "Half-wave patch estimate near CH9 on RO4350B."),
        make_candidate("dualfeed", "patch_10p4_feed_3p9", 10.40, 3.90, "More aggressive resonance-lowering patch and edge feed."),
        make_candidate("dualfeed", "patch_10p8_feed_4p2", 10.80, 4.20, "Use remaining board margin for a larger resonator."),
        make_candidate("dualfeed", "wide_port", 10.00, 3.50, "Increase local feed capacitance and port width.", port_width=1.05, pad=0.55),
        make_candidate("dualfeed", "narrow_port", 10.00, 3.50, "Reduce local feed capacitance and port perturbation.", port_width=0.45, pad=0.35),
        make_candidate("dualfeed", "asym_feed_a3p7_b3p1", 10.00, 3.40, "Break A/B feed symmetry for modal and impedance balance.", feed_a=3.70, feed_b=3.10),
        make_candidate("dualfeed", "short_slots", 10.00, 3.50, "Reduce isolation-slot loading if it is hurting match.", slot_len=7.0, slot_width=0.32),
        make_candidate("dualfeed", "long_slots", 10.00, 3.50, "Increase isolation-slot length for coupling control.", slot_len=12.0, slot_width=0.42),
        make_candidate("hybrid", "patch_9p7_feed_3p4", 9.70, 3.40, "Hybrid layout with larger patch and outward feeds.", trace_width=0.36, trace_gap=0.65),
        make_candidate("hybrid", "patch_10p0_feed_3p5", 10.00, 3.50, "Hybrid layout on half-wave patch estimate.", trace_width=0.36, trace_gap=0.65),
        make_candidate("hybrid", "patch_10p4_feed_3p9", 10.40, 3.90, "Hybrid layout with larger resonator.", trace_width=0.34, trace_gap=0.70),
        make_candidate("hybrid", "wide_port", 10.00, 3.50, "Hybrid layout with wider feed/port.", port_width=1.05, pad=0.55, trace_width=0.40, trace_gap=0.70),
        make_candidate("hybrid", "asym_feed_a3p7_b3p1", 10.00, 3.40, "Hybrid layout with asymmetric output feed offsets.", feed_a=3.70, feed_b=3.10, trace_width=0.36, trace_gap=0.65),
    ]
    return [candidate for candidate in candidates if is_valid(candidate)]


def is_valid(candidate: Candidate) -> bool:
    params = dict(builder.BASE_PARAMS)
    params.update(candidate.params)
    try:
        builder.validate_params(params)
    except Exception as exc:
        print(f"Skipping invalid candidate {candidate.name}: {exc}", flush=True)
        return False
    return True


def apply_candidate(candidate: Candidate) -> None:
    params = builder.TOPOLOGIES[candidate.topology]["params"]
    params.clear()
    params.update(candidate.params)


def open_hfss(topology: str) -> Hfss:
    spec = builder.TOPOLOGIES[topology]
    paths = builder.topology_paths(topology)
    return Hfss(
        project=str(paths["project"]),
        design=spec["design"],
        version="2023.1",
        non_graphical=True,
        new_desktop=True,
        close_on_exit=False,
        remove_lock=True,
    )


def s_score(s: dict) -> float:
    return_miss = max(0.0, s["worst_return_db"] - RETURN_TARGET_DB)
    isolation_miss = max(0.0, ISOLATION_TARGET_DB - s["isolation_db"])
    return 16.0 * return_miss + 4.0 * isolation_miss - 0.4 * max(0.0, -RETURN_TARGET_DB + -s["worst_return_db"])


def append_csv(path: Path, row: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    exists = path.exists()
    with path.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(row))
        if not exists:
            writer.writeheader()
        writer.writerow(row)


def run_sparam_candidate(index: int, candidate: Candidate) -> dict:
    start = time.time()
    apply_candidate(candidate)
    _project, hfss = builder.build_project(
        candidate.topology,
        analyze=True,
        non_graphical=True,
        quick=True,
        band_samples=True,
        sparam_only=False,
        return_hfss=True,
    )
    try:
        s = evaluator.get_s_parameter_snapshot(hfss, REPORT_DIR / f"{candidate.topology}_candidate_s_parameters.csv")
    finally:
        hfss.release_desktop(close_projects=False, close_desktop=True)
    row = {
        "stage": "sparam",
        "index": index,
        "candidate": candidate.name,
        "topology": candidate.topology,
        "score": s_score(s),
        "elapsed_s": round(time.time() - start, 1),
        "rationale": candidate.rationale,
        "worst_return_db": s["worst_return_db"],
        "worst_return_expr": s["worst_return_expr"],
        "worst_coupling_db": s["worst_coupling_db"],
        "worst_coupling_expr": s["worst_coupling_expr"],
        "isolation_db": s["isolation_db"],
        "patch_side_mm": candidate.params.get("patch_side_mm"),
        "feed_offset_u_mm": candidate.params.get("feed_offset_u_mm"),
        "feed_offset_a_mm": candidate.params.get("feed_offset_a_mm", ""),
        "feed_offset_b_mm": candidate.params.get("feed_offset_b_mm", ""),
        "port_width_mm": candidate.params.get("port_width_mm"),
        "feed_pad_radius_mm": candidate.params.get("feed_pad_radius_mm"),
        "isolation_slot_length_mm": candidate.params.get("isolation_slot_length_mm"),
        "isolation_slot_width_mm": candidate.params.get("isolation_slot_width_mm"),
    }
    append_csv(HISTORY_CSV, row)
    print(json.dumps(row, indent=2), flush=True)
    return row


def source_balance_cases(sources: list[str]) -> list[dict]:
    pairs = evaluator.element_pair_map(sources)
    if not pairs:
        return []
    cases = []
    for amp_b in [0.85, 1.0, 1.15]:
        for phase_b in [-105.0, -90.0, -75.0]:
            assignments = {item: (0.0, 0.0) for item in sources}
            for idx, element in enumerate(sorted(pairs, key=int)):
                base_phase = idx * -90.0
                pair = pairs[element]
                assignments[pair["A"]] = (1.0, base_phase)
                assignments[pair["B"]] = (amp_b, base_phase + phase_b)
            cases.append({"amp_b": amp_b, "phase_b_deg": phase_b, "assignments": assignments})
    return cases


def evaluate_open_hfss(topology: str, hfss: Hfss) -> dict:
    spec = builder.TOPOLOGIES[topology]
    paths = builder.topology_paths(topology)
    reports = evaluator.report_paths(topology)
    reports["dir"].mkdir(parents=True, exist_ok=True)

    sources = hfss.get_all_sources()
    available_freqs = evaluator.get_available_frequencies(hfss)
    eval_freqs = evaluator.nearest_frequencies(available_freqs)
    cases = evaluator.source_cases(sources, topology)
    summaries_by_freq = {}
    for freq in eval_freqs:
        summaries = {}
        single_grids = {}
        for name, assignments in cases.items():
            if assignments:
                hfss.edit_sources(assignments)
            grid = evaluator.get_grid(hfss, freq)
            summaries[name] = evaluator.summarize_rows(freq, grid["rows"])
            if name.endswith("_only"):
                single_grids[name] = grid
        if single_grids:
            first_grid = next(iter(single_grids.values()))
            envelope_rows = []
            cp_rows = []
            for idx, base_row in enumerate(first_grid["rows"]):
                candidates = [grid["rows"][idx] for grid in single_grids.values()]
                best_gain = max(candidates, key=lambda r: r["gain"])
                envelope_rows.append(
                    {
                        "theta": base_row["theta"],
                        "phi": base_row["phi"],
                        "gain": best_gain["gain"],
                        "axial_ratio": best_gain["axial_ratio"],
                    }
                )
                cp_candidates = [r for r in candidates if r["axial_ratio"] <= evaluator.AXIAL_RATIO_TARGET_DB]
                cp_best = max(cp_candidates, key=lambda r: r["gain"]) if cp_candidates else min(candidates, key=lambda r: r["axial_ratio"])
                cp_rows.append(
                    {
                        "theta": base_row["theta"],
                        "phi": base_row["phi"],
                        "gain": cp_best["gain"],
                        "axial_ratio": cp_best["axial_ratio"],
                    }
                )
            summaries["coverage_envelope_best_port"] = evaluator.summarize_rows(freq, envelope_rows)
            summaries["cp_qualified_envelope"] = evaluator.summarize_rows(freq, cp_rows)
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
        "s_parameters": evaluator.get_s_parameter_snapshot(hfss, reports["s_csv"]),
    }
    metrics["fov_summary"] = evaluator.summarize_fov(metrics)
    metrics["metrics_json"] = str(reports["metrics"])
    metrics["fov_csv"] = str(reports["fov_csv"])
    metrics["s_csv"] = str(reports["s_csv"])
    reports["metrics"].write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    evaluator.write_csv(reports["fov_csv"], summaries_by_freq)
    params = json.loads(paths["params"].read_text(encoding="utf-8"))
    evaluator.write_report(topology, params, metrics, reports["report"])
    return metrics


def balance_score(item: dict) -> float:
    ar_miss = max(0.0, item["axial_ratio_max_db"] - AR_TARGET_DB)
    gain_miss = max(0.0, GAIN_TARGET_DBI - item["gain_min_dbi"])
    return 2.0 * ar_miss + 0.8 * gain_miss - 0.08 * item["cp_coverage_min_percent"]


def run_source_balance_sweep(topology: str, hfss: Hfss | None = None) -> dict:
    close_when_done = hfss is None
    if hfss is None:
        hfss = open_hfss(topology)
    try:
        sources = hfss.get_all_sources()
        freqs = evaluator.nearest_frequencies(evaluator.get_available_frequencies(hfss))
        rows = []
        for case in source_balance_cases(sources):
            summaries = []
            hfss.edit_sources(case["assignments"])
            for freq in freqs:
                grid = evaluator.get_grid(hfss, freq)
                summaries.append(evaluator.summarize_rows(freq, grid["rows"]))
            row = {
                "amp_b": case["amp_b"],
                "phase_b_deg": case["phase_b_deg"],
                "gain_min_dbi": min(item["gain_min_dbi"] for item in summaries),
                "axial_ratio_max_db": max(item["axial_ratio_max_db"] for item in summaries),
                "cp_coverage_min_percent": min(item["cp_coverage_percent"] for item in summaries),
            }
            row["score"] = balance_score(row)
            rows.append(row)
            append_csv(BALANCE_CSV, {"topology": topology, **row})
        best = min(rows, key=lambda item: item["score"]) if rows else {}
        print(json.dumps({"best_source_balance": best}, indent=2), flush=True)
        return best
    finally:
        if close_when_done:
            hfss.release_desktop(close_projects=False, close_desktop=True)


def run_full_candidate(candidate: Candidate) -> dict:
    apply_candidate(candidate)
    _project, hfss = builder.build_project(
        candidate.topology,
        analyze=True,
        non_graphical=True,
        quick=True,
        band_samples=True,
        sparam_only=False,
        return_hfss=True,
    )
    try:
        metrics = evaluate_open_hfss(candidate.topology, hfss)
        balance = run_source_balance_sweep(candidate.topology, hfss)
    finally:
        hfss.release_desktop(close_projects=False, close_desktop=True)
    s = metrics.get("s_parameters", {})
    f = metrics.get("fov_summary", {})
    best = {
        "candidate": candidate.name,
        "topology": candidate.topology,
        "rationale": candidate.rationale,
        "parameters": candidate.params,
        "s_parameters": s,
        "fov_summary": f,
        "optimized_source_balance": balance,
        "meets_s_targets": s.get("worst_return_db", math.inf) <= RETURN_TARGET_DB and s.get("isolation_db", -math.inf) >= ISOLATION_TARGET_DB,
        "meets_fov_targets": f.get("coverage_envelope_gain_min_dbi", -math.inf) >= GAIN_TARGET_DBI
        and f.get("cp_qualified_ar_max_db", math.inf) <= AR_TARGET_DB,
        "meets_balanced_cp_target": bool(balance)
        and balance.get("gain_min_dbi", -math.inf) >= GAIN_TARGET_DBI
        and balance.get("axial_ratio_max_db", math.inf) <= AR_TARGET_DB,
    }
    best["meets_all_targets"] = best["meets_s_targets"] and (best["meets_fov_targets"] or best["meets_balanced_cp_target"])
    BEST_JSON.write_text(json.dumps(best, indent=2), encoding="utf-8")
    write_report(best)
    return best


def fmt(value: float | int | None, digits: int = 2) -> str:
    if value is None:
        return "N/A"
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return "N/A"
    return f"{float(value):.{digits}f}"


def top_history_rows(limit: int = 10) -> list[dict]:
    if not HISTORY_CSV.exists():
        return []
    with HISTORY_CSV.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    return sorted(rows, key=lambda r: float(r.get("score") or 1e9))[:limit]


def write_report(best: dict) -> None:
    s = best.get("s_parameters", {})
    f = best.get("fov_summary", {})
    b = best.get("optimized_source_balance", {})
    params = best.get("parameters", {})
    lines = [
        "# D44 dual-feed / 90-degree hybrid optimization report",
        "",
        "## Targets",
        "",
        f"- Worst Sii <= {RETURN_TARGET_DB:.1f} dB across 7.738/7.9855/8.233 GHz.",
        f"- Port isolation >= {ISOLATION_TARGET_DB:.1f} dB.",
        f"- FOV envelope minimum gain >= {GAIN_TARGET_DBI:.1f} dBi.",
        f"- AxialRatioValue <= {AR_TARGET_DB:.1f} dB in the selected FOV, or best available source-balance result recorded.",
        "",
        "## Best candidate",
        "",
        f"- Candidate: `{best.get('candidate')}`",
        f"- Topology: `{best.get('topology')}`",
        f"- Rationale: {best.get('rationale')}",
        f"- Meets all targets: `{best.get('meets_all_targets')}`",
        "",
        "## Geometry parameters",
        "",
    ]
    for key in [
        "patch_side_mm",
        "feed_offset_u_mm",
        "feed_offset_a_mm",
        "feed_offset_b_mm",
        "port_width_mm",
        "feed_pad_radius_mm",
        "hybrid_trace_width_mm",
        "hybrid_trace_gap_mm",
        "isolation_slot_length_mm",
        "isolation_slot_width_mm",
    ]:
        if key in params:
            lines.append(f"- `{key}`: `{fmt(params[key], 3)}`")
    lines.extend(
        [
            "",
            "## Core metrics",
            "",
            f"- Worst return loss: `{fmt(s.get('worst_return_db'))} dB` via `{s.get('worst_return_expr', 'N/A')}`",
            f"- Worst coupling: `{fmt(s.get('worst_coupling_db'))} dB` via `{s.get('worst_coupling_expr', 'N/A')}`",
            f"- Isolation: `{fmt(s.get('isolation_db'))} dB`",
            f"- Coverage-envelope min gain: `{fmt(f.get('coverage_envelope_gain_min_dbi'))} dBi`",
            f"- CP-qualified envelope max AR: `{fmt(f.get('cp_qualified_ar_max_db'))} dB`",
            f"- CP-qualified envelope min gain: `{fmt(f.get('cp_qualified_gain_min_dbi'))} dBi`",
            f"- CP-qualified min coverage: `{fmt(f.get('cp_qualified_coverage_min_percent'), 1)}%`",
            "",
            "## Best source phase/amplitude balance",
            "",
            f"- B-feed amplitude: `{fmt(b.get('amp_b'), 3)}` relative to A-feed.",
            f"- B-feed phase: `{fmt(b.get('phase_b_deg'), 1)} deg` relative to A-feed.",
            f"- Balanced-array min gain: `{fmt(b.get('gain_min_dbi'))} dBi`",
            f"- Balanced-array max AR: `{fmt(b.get('axial_ratio_max_db'))} dB`",
            f"- Balanced-array min CP coverage: `{fmt(b.get('cp_coverage_min_percent'), 1)}%`",
            "",
            "## S-parameter screening ranking",
            "",
            "| Rank | Candidate | Topology | Score | Worst Sii | Isolation | Notes |",
            "| ---: | --- | --- | ---: | ---: | ---: | --- |",
        ]
    )
    for idx, row in enumerate(top_history_rows(), start=1):
        lines.append(
            f"| {idx} | {row.get('candidate')} | {row.get('topology')} | {fmt(float(row.get('score', 0)))} | "
            f"{fmt(float(row.get('worst_return_db', 0)))} dB | {fmt(float(row.get('isolation_db', 0)))} dB | {row.get('rationale', '')} |"
        )
    lines.extend(
        [
            "",
            "## Output files",
            "",
            f"- Optimization history: `{HISTORY_CSV}`",
            f"- Source balance sweep: `{BALANCE_CSV}`",
            f"- Best JSON: `{BEST_JSON}`",
            f"- Final topology report directory: `{evaluator.report_paths(best['topology'])['dir']}`",
        ]
    )
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-candidates", type=int, default=12)
    parser.add_argument("--skip-candidates", type=int, default=0)
    parser.add_argument("--full-finalists", type=int, default=1)
    parser.add_argument("--reset-history", action="store_true")
    args = parser.parse_args()

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    if args.reset_history:
        for path in [HISTORY_CSV, BALANCE_CSV, BEST_JSON, REPORT_MD]:
            if path.exists():
                path.unlink()

    candidates = generate_candidates()[args.skip_candidates : args.skip_candidates + args.max_candidates]
    s_rows = []
    for idx, candidate in enumerate(candidates, start=args.skip_candidates + 1):
        s_rows.append(run_sparam_candidate(idx, candidate))
    ranked = sorted(zip(s_rows, candidates), key=lambda item: item[0]["score"])
    best_full = None
    for _, candidate in ranked[: args.full_finalists]:
        best_full = run_full_candidate(candidate)
        if best_full["meets_all_targets"]:
            break
    print(json.dumps(best_full, indent=2), flush=True)
    print(f"Wrote {REPORT_MD}", flush=True)


if __name__ == "__main__":
    main()
