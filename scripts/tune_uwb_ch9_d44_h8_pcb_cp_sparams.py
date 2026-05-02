from __future__ import annotations

import argparse
import csv
from pathlib import Path

from ansys.aedt.core import Hfss

import build_uwb_ch9_hfss_d44_h8_pcb_cp as builder
import evaluate_uwb_ch9_d44_h8_pcb_cp as evaluator


ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = ROOT / "reports_d44_h8_pcb_cp"
TUNING_CSV_PREFIX = "UWB_CH9_D44_H8_PCB_CP_sparam_tuning"


STARTING_CANDIDATES = [
    {"substrate_h_mm": 2.0, "patch_side_mm": 9.4, "feed_offset_u_mm": 1.85, "corner_cut_mm": 0.72},
    {"substrate_h_mm": 2.0, "patch_side_mm": 9.0, "feed_offset_u_mm": 2.35, "corner_cut_mm": 0.68},
    {"substrate_h_mm": 2.0, "patch_side_mm": 8.8, "feed_offset_u_mm": 2.75, "corner_cut_mm": 0.64},
    {"substrate_h_mm": 2.0, "patch_side_mm": 8.6, "feed_offset_u_mm": 3.05, "corner_cut_mm": 0.60},
    {"substrate_h_mm": 2.0, "patch_side_mm": 8.4, "feed_offset_u_mm": 3.20, "corner_cut_mm": 0.58},
    {"substrate_h_mm": 2.0, "patch_side_mm": 8.2, "feed_offset_u_mm": 3.30, "corner_cut_mm": 0.55},
]


REFINED_CANDIDATES = [
    {"substrate_h_mm": 2.0, "patch_side_mm": 8.95, "feed_offset_u_mm": 2.55, "corner_cut_mm": 0.62},
    {"substrate_h_mm": 2.0, "patch_side_mm": 8.90, "feed_offset_u_mm": 2.70, "corner_cut_mm": 0.62},
    {"substrate_h_mm": 2.0, "patch_side_mm": 8.85, "feed_offset_u_mm": 2.85, "corner_cut_mm": 0.62},
    {"substrate_h_mm": 2.0, "patch_side_mm": 8.80, "feed_offset_u_mm": 3.00, "corner_cut_mm": 0.62},
    {"substrate_h_mm": 2.0, "patch_side_mm": 8.90, "feed_offset_u_mm": 2.80, "corner_cut_mm": 0.50},
    {"substrate_h_mm": 2.0, "patch_side_mm": 8.90, "feed_offset_u_mm": 2.80, "corner_cut_mm": 0.80},
    {"substrate_h_mm": 2.4, "patch_side_mm": 9.05, "feed_offset_u_mm": 2.80, "corner_cut_mm": 0.68},
    {"substrate_h_mm": 3.2, "patch_side_mm": 9.25, "feed_offset_u_mm": 3.00, "corner_cut_mm": 0.72},
]


FINE_CANDIDATES = [
    {"substrate_h_mm": 2.0, "patch_side_mm": 8.93, "feed_offset_u_mm": 2.62, "corner_cut_mm": 0.62},
    {"substrate_h_mm": 2.0, "patch_side_mm": 8.92, "feed_offset_u_mm": 2.66, "corner_cut_mm": 0.62},
    {"substrate_h_mm": 2.0, "patch_side_mm": 8.91, "feed_offset_u_mm": 2.68, "corner_cut_mm": 0.62},
    {"substrate_h_mm": 2.0, "patch_side_mm": 8.90, "feed_offset_u_mm": 2.72, "corner_cut_mm": 0.62},
    {"substrate_h_mm": 2.0, "patch_side_mm": 8.89, "feed_offset_u_mm": 2.74, "corner_cut_mm": 0.62},
    {"substrate_h_mm": 2.0, "patch_side_mm": 8.88, "feed_offset_u_mm": 2.70, "corner_cut_mm": 0.62},
    {"substrate_h_mm": 2.0, "patch_side_mm": 8.90, "feed_offset_u_mm": 2.66, "corner_cut_mm": 0.55},
    {"substrate_h_mm": 2.0, "patch_side_mm": 8.90, "feed_offset_u_mm": 2.66, "corner_cut_mm": 0.70},
]


MATCH_CANDIDATES = [
    {"substrate_h_mm": 2.0, "patch_side_mm": 8.91, "feed_offset_u_mm": 2.68, "corner_cut_mm": 0.62, "port_width_mm": 0.35, "feed_pad_radius_mm": 0.35},
    {"substrate_h_mm": 2.0, "patch_side_mm": 8.91, "feed_offset_u_mm": 2.68, "corner_cut_mm": 0.62, "port_width_mm": 0.50, "feed_pad_radius_mm": 0.45},
    {"substrate_h_mm": 2.0, "patch_side_mm": 8.91, "feed_offset_u_mm": 2.68, "corner_cut_mm": 0.62, "port_width_mm": 1.00, "feed_pad_radius_mm": 0.45},
    {"substrate_h_mm": 2.0, "patch_side_mm": 8.91, "feed_offset_u_mm": 2.68, "corner_cut_mm": 0.62, "port_width_mm": 1.25, "feed_pad_radius_mm": 0.55},
    {"substrate_h_mm": 2.0, "patch_side_mm": 8.92, "feed_offset_u_mm": 2.66, "corner_cut_mm": 0.62, "port_width_mm": 0.50, "feed_pad_radius_mm": 0.45},
    {"substrate_h_mm": 2.0, "patch_side_mm": 8.90, "feed_offset_u_mm": 2.70, "corner_cut_mm": 0.62, "port_width_mm": 0.50, "feed_pad_radius_mm": 0.45},
]


def extract_s_metrics() -> dict:
    hfss = Hfss(
        project=str(builder.PROJECT_PATH),
        design="Array4_Diamond_D44_H8_PCB_CP",
        version="2023.1",
        non_graphical=True,
        new_desktop=True,
        close_on_exit=False,
        remove_lock=True,
    )
    try:
        s = evaluator.get_s_parameter_snapshot(hfss)
        return {
            "worst_return_db": s["worst_return_db"],
            "worst_return_expr": s["worst_return_expr"],
            "worst_coupling_db": s["worst_coupling_db"],
            "worst_coupling_expr": s["worst_coupling_expr"],
            "isolation_db": s["isolation_db"],
        }
    finally:
        hfss.release_desktop(close_projects=False, close_desktop=True)


def run_candidate(idx: int, candidate: dict) -> dict:
    for key, value in candidate.items():
        builder.PARAMS[key] = value
    builder.build_project(
        analyze=True,
        non_graphical=True,
        quick=True,
        band_samples=True,
        sparam_only=True,
    )
    metrics = extract_s_metrics()
    row = {"candidate": idx, **candidate, **metrics}
    print(row, flush=True)
    return row


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None, help="Limit number of candidates to run.")
    parser.add_argument(
        "--mode",
        choices=["starting", "refined", "fine", "match"],
        default="starting",
        help="Choose the coarse starting sweep or the local refined sweep.",
    )
    args = parser.parse_args()

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    candidate_sets = {
        "starting": STARTING_CANDIDATES,
        "refined": REFINED_CANDIDATES,
        "fine": FINE_CANDIDATES,
        "match": MATCH_CANDIDATES,
    }
    candidates = candidate_sets[args.mode]
    limit = len(candidates) if args.limit is None else args.limit
    rows = []
    for idx, candidate in enumerate(candidates[:limit], start=1):
        rows.append(run_candidate(idx, dict(candidate)))

    output_csv = REPORT_DIR / f"{TUNING_CSV_PREFIX}_{args.mode}.csv"
    if rows:
        with output_csv.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
    print(f"Wrote {output_csv}", flush=True)


if __name__ == "__main__":
    main()
