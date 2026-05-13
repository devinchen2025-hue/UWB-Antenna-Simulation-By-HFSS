from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import build_uwb_ch9_hfss_d44_topology as builder


ROOT = Path(__file__).resolve().parents[1]
TOPOLOGY = "dualpol"
REPORT_DIR = ROOT / "reports_d44_board_edge_low_angle_single_element"
STEM = "UWB_CH9_D44_BOARD_EDGE_LOW_ANGLE_SINGLE_ELEMENT"
DESIGN_NAME = "SingleElement_D44_BoardEdge_LowAngle"
SOLUTION = "Setup_CH9 : Sweep_CH9"
SPHERE = "Upper_Hemisphere_5deg"
NATIVE_REPORT_SCRIPT = ROOT / "scripts" / "aedt_export_ch9_native_reports.py"
AEDT_EXE = builder.AEDT_EXE

FREQ_GHZ = 8.0
THETA_MIN_DEG = 45.0
THETA_MAX_DEG = 90.0
AZIMUTH_WINDOW_DEG = 270.0
RETURN_TARGET_DB = -10.0
GAIN_TARGET_DBI = -5.0

SUMMARY_CSV = REPORT_DIR / f"{STEM}_summary.csv"
WINDOW_CSV = REPORT_DIR / f"{STEM}_azimuth_window_summary.csv"
METRICS_JSON = REPORT_DIR / f"{STEM}_metrics.json"
REPORT_MD = REPORT_DIR / f"{STEM}_report_zh.md"


@dataclass(frozen=True)
class BoardEdgeCandidate:
    name: str
    rationale: str
    updates: dict[str, Any]


def safe_slug(value: str, limit: int = 64) -> str:
    clean = "".join(ch if ch.isalnum() or ch in "-_." else "_" for ch in value)
    return clean[:limit].strip("._-") or "candidate"


def fmt(value: Any, digits: int = 3) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    if math.isnan(number) or math.isinf(number):
        return "N/A"
    return f"{number:.{digits}f}"


def base_params() -> dict[str, Any]:
    params = builder.topology_params(TOPOLOGY)
    params.update(
        {
            "element_spacing_mm": 17.0,
            "board_diameter_mm": 44.0,
            "ground_radius_mm": 21.4,
            "total_height_limit_mm": 8.0,
            "substrate_h_mm": 2.0,
            "patch_side_mm": 8.0,
            "feed_pad_radius_mm": 0.22,
            "port_width_mm": 0.42,
            "dualpol_parasitic_enabled": 0.0,
            "parasitic_side_mm": 0.0,
            "air_gap_mm": 0.0,
            "microstrip_feed_enabled": 0.0,
            "dualpol_slotcoupled_enabled": 1.0,
            "feed_substrate_h_mm": 0.254,
            "slot_coupled_aperture_length_a_mm": 2.8,
            "slot_coupled_aperture_length_b_mm": 2.8,
            "slot_coupled_aperture_width_mm": 0.38,
            "slot_coupled_feedline_length_mm": 7.4,
            "slot_coupled_feedline_width_mm": 0.42,
            "slot_coupled_horizon_loop_enabled": 0.0,
            "slot_coupled_edge_arm_enabled": 0.0,
            "slot_coupled_board_edge_ifa_enabled": 0.0,
            "slot_coupled_folded_edge_arm_enabled": 0.0,
            "board_edge_fed_monopole_enabled": 0.0,
            "board_edge_fed_ifa_enabled": 0.0,
            "board_edge_fed_l_match_enabled": 0.0,
            "board_edge_fed_l_match_stub_length_mm": 0.0,
            "board_edge_fed_l_match_stub_width_mm": 0.18,
            "board_edge_fed_l_match_fold_enabled": 0.0,
            "board_edge_fed_l_match_fold_length_mm": 0.0,
            "board_edge_fed_l_match_capacitance_pf": 0.0,
            "board_edge_fed_l_match_inductance_nh": 0.0,
            "board_edge_fed_l_feed_neck_enabled": 0.0,
            "board_edge_fed_l_feed_neck_length_mm": 0.0,
            "single_source_feed_enabled": 1.0,
            "single_source_feed_name": "P1L",
            "rf_switch_equiv_enabled": 1.0,
            "rf_switch_active_pol": 0.0,
            "rf_switch_off_resistance_ohm": 50.0,
            "rf_switch_off_capacitance_pf": 0.08,
            "rf_switch_off_inductance_nh": 0.0,
            "isolation_slot_enabled": 0.0,
            "local_dgs_enabled": 0.0,
            "air_frequency_ghz": 7.0,
        }
    )
    return params


def with_base(name: str, rationale: str, **updates: Any) -> BoardEdgeCandidate:
    return BoardEdgeCandidate(name=name, rationale=rationale, updates=updates)


def candidates() -> list[BoardEdgeCandidate]:
    foldpar_mini_common = {
        "element_spacing_mm": 19.0,
        "substrate_h_mm": 1.6,
        "patch_side_mm": 6.2,
        "feed_pad_radius_mm": 0.16,
        "port_width_mm": 0.34,
        "slot_coupled_aperture_length_a_mm": 2.0,
        "slot_coupled_aperture_length_b_mm": 2.0,
        "slot_coupled_feedline_length_mm": 5.8,
        "slot_coupled_folded_edge_arm_enabled": 1.0,
        "slot_coupled_folded_edge_arm_radial_length_mm": 1.0,
        "slot_coupled_folded_edge_arm_tangent_length_mm": 2.7,
        "slot_coupled_folded_edge_arm_height_mm": 5.9,
        "slot_coupled_folded_edge_arm_width_mm": 0.24,
        "board_edge_fed_ifa_enabled": 1.0,
        "board_edge_fed_ifa_height_mm": 6.3,
        "board_edge_fed_ifa_length_mm": 5.0,
        "board_edge_fed_ifa_feed_offset_mm": 1.80,
        "board_edge_fed_ifa_gap_mm": 0.18,
        "board_edge_fed_ifa_width_mm": 0.28,
        "board_edge_fed_l_feed_neck_length_mm": 0.80,
        "board_edge_fed_l_feed_neck_width_mm": 0.14,
        "board_edge_fed_l_series_match_enabled": 1.0,
        "board_edge_fed_l_series_match_width_mm": 0.14,
        "board_edge_fed_l_match_enabled": 1.0,
        "board_edge_fed_l_match_stub_width_mm": 0.14,
    }
    foldpar_match_common = {
        "element_spacing_mm": 19.0,
        "substrate_h_mm": 1.6,
        "patch_side_mm": 6.2,
        "slot_coupled_aperture_length_a_mm": 2.0,
        "slot_coupled_aperture_length_b_mm": 2.0,
        "slot_coupled_feedline_length_mm": 5.8,
        "slot_coupled_folded_edge_arm_enabled": 1.0,
        "slot_coupled_folded_edge_arm_radial_length_mm": 1.0,
        "slot_coupled_folded_edge_arm_tangent_length_mm": 2.7,
        "slot_coupled_folded_edge_arm_height_mm": 5.9,
        "slot_coupled_folded_edge_arm_width_mm": 0.24,
        "board_edge_fed_ifa_enabled": 1.0,
        "board_edge_fed_ifa_height_mm": 6.3,
        "board_edge_fed_ifa_length_mm": 5.0,
        "board_edge_fed_ifa_feed_offset_mm": 1.80,
        "board_edge_fed_ifa_gap_mm": 0.18,
        "board_edge_fed_ifa_width_mm": 0.28,
        "board_edge_fed_l_feed_neck_length_mm": 0.80,
        "board_edge_fed_l_feed_neck_width_mm": 0.16,
        "board_edge_fed_l_series_match_enabled": 1.0,
        "board_edge_fed_l_series_match_width_mm": 0.16,
        "board_edge_fed_l_series_match_capacitance_pf": 0.173,
        "board_edge_fed_l_match_enabled": 1.0,
        "board_edge_fed_l_match_inductance_nh": 6.1,
    }
    sidewall_pifa_common = foldpar_match_common | {
        "substrate_h_mm": 7.60,
        "slot_coupled_folded_edge_arm_sidewall_metallized_enabled": 1.0,
        "board_edge_fed_ifa_sidewall_metallized_enabled": 1.0,
        "slot_coupled_folded_edge_arm_tangent_length_mm": 2.0,
        "slot_coupled_folded_edge_arm_offset_mm": -0.6,
        "board_edge_fed_l_series_match_capacitance_pf": 0.142,
        "board_edge_fed_l_match_inductance_nh": 2.00,
        "board_edge_fed_l_match_resistance_ohm": 680.0,
    }
    sidewall_plane_pifa_common = foldpar_match_common | {
        "board_edge_fed_ifa_sidewall_plane_enabled": 1.0,
        "slot_coupled_folded_edge_arm_tangent_length_mm": 2.0,
        "slot_coupled_folded_edge_arm_offset_mm": -0.6,
        "board_edge_fed_l_series_match_capacitance_pf": 0.142,
        "board_edge_fed_l_match_inductance_nh": 2.00,
        "board_edge_fed_l_match_resistance_ohm": 680.0,
    }
    return [
        with_base(
            "edgeifa_s17_h5p6_l4p2_f0p60_g0p25",
            "True board-edge fed IFA baseline: P1 is placed near the D44 board rim and P1L is the only active low-elevation source.",
            board_edge_fed_ifa_enabled=1.0,
            board_edge_fed_ifa_height_mm=5.6,
            board_edge_fed_ifa_length_mm=4.2,
            board_edge_fed_ifa_feed_offset_mm=0.60,
            board_edge_fed_ifa_gap_mm=0.25,
            board_edge_fed_ifa_width_mm=0.24,
        ),
        with_base(
            "edgeifa_s17_h5p8_l4p8_f0p75_g0p25",
            "Lengthen the printed IFA arm and lift it close to the 8 mm envelope to move the board-edge resonance toward 8 GHz.",
            board_edge_fed_ifa_enabled=1.0,
            board_edge_fed_ifa_height_mm=5.8,
            board_edge_fed_ifa_length_mm=4.8,
            board_edge_fed_ifa_feed_offset_mm=0.75,
            board_edge_fed_ifa_gap_mm=0.25,
            board_edge_fed_ifa_width_mm=0.24,
        ),
        with_base(
            "edgeifa_s17_h5p4_l5p4_f0p95_g0p20_patch7p4",
            "Use a slightly smaller local patch footprint so a longer IFA arm still fits inside the circular D44 outline.",
            patch_side_mm=7.4,
            slot_coupled_feedline_length_mm=6.8,
            board_edge_fed_ifa_enabled=1.0,
            board_edge_fed_ifa_height_mm=5.4,
            board_edge_fed_ifa_length_mm=5.4,
            board_edge_fed_ifa_feed_offset_mm=0.95,
            board_edge_fed_ifa_gap_mm=0.20,
            board_edge_fed_ifa_width_mm=0.24,
        ),
        with_base(
            "edgeifa_s17_h5p8_l4p8_f1p35_g0p25",
            "Move the IFA feed tap toward the open end to bracket the input resistance without adding discrete parts.",
            board_edge_fed_ifa_enabled=1.0,
            board_edge_fed_ifa_height_mm=5.8,
            board_edge_fed_ifa_length_mm=4.8,
            board_edge_fed_ifa_feed_offset_mm=1.35,
            board_edge_fed_ifa_gap_mm=0.25,
            board_edge_fed_ifa_width_mm=0.24,
        ),
        with_base(
            "edgeifa_s17_h5p8_l4p8_f0p75_g0p25_stub1p2_c0p18",
            "Add a low-cost L-port shunt capacitance and short printed stub to the gain-oriented IFA point.",
            board_edge_fed_ifa_enabled=1.0,
            board_edge_fed_ifa_height_mm=5.8,
            board_edge_fed_ifa_length_mm=4.8,
            board_edge_fed_ifa_feed_offset_mm=0.75,
            board_edge_fed_ifa_gap_mm=0.25,
            board_edge_fed_ifa_width_mm=0.24,
            board_edge_fed_l_match_enabled=1.0,
            board_edge_fed_l_match_stub_length_mm=1.2,
            board_edge_fed_l_match_stub_width_mm=0.18,
            board_edge_fed_l_match_capacitance_pf=0.18,
        ),
        with_base(
            "edgemono_s17_h5p8_g0p35_top2p2",
            "True board-edge monopole/PIFA branch with a small printed top load; this checks the cheapest vertical edge radiator.",
            board_edge_fed_monopole_enabled=1.0,
            board_edge_fed_monopole_height_mm=5.8,
            board_edge_fed_monopole_gap_mm=0.35,
            board_edge_fed_monopole_width_mm=0.24,
            board_edge_fed_monopole_topload_length_mm=2.2,
        ),
        with_base(
            "edgemono_s17_h5p9_g0p25_top1p4_neck0p6",
            "Slightly taller monopole with a short feed neck, keeping total height inside 8 mm.",
            board_edge_fed_monopole_enabled=1.0,
            board_edge_fed_monopole_height_mm=5.9,
            board_edge_fed_monopole_gap_mm=0.25,
            board_edge_fed_monopole_width_mm=0.24,
            board_edge_fed_monopole_topload_length_mm=1.4,
            board_edge_fed_l_feed_neck_enabled=1.0,
            board_edge_fed_l_feed_neck_length_mm=0.6,
            board_edge_fed_l_feed_neck_width_mm=0.14,
        ),
        with_base(
            "edgemono_s17_h5p8_g0p35_top2p2_stub1p0_l1p8",
            "Use a manufacturable shunt inductive match plus printed stub on the top-loaded monopole candidate.",
            board_edge_fed_monopole_enabled=1.0,
            board_edge_fed_monopole_height_mm=5.8,
            board_edge_fed_monopole_gap_mm=0.35,
            board_edge_fed_monopole_width_mm=0.24,
            board_edge_fed_monopole_topload_length_mm=2.2,
            board_edge_fed_l_match_enabled=1.0,
            board_edge_fed_l_match_stub_length_mm=1.0,
            board_edge_fed_l_match_stub_width_mm=0.18,
            board_edge_fed_l_match_inductance_nh=1.8,
        ),
        with_base(
            "edgeifa_s18p5_p6p2_h6p3_l4p8_f1p35_g0p18",
            "Move the true-fed IFA closer to the circular board rim, shrink the inactive A/B patch background, and use more vertical height inside the 8 mm envelope.",
            element_spacing_mm=18.5,
            substrate_h_mm=1.6,
            patch_side_mm=6.2,
            slot_coupled_aperture_length_a_mm=2.2,
            slot_coupled_aperture_length_b_mm=2.2,
            slot_coupled_feedline_length_mm=5.8,
            board_edge_fed_ifa_enabled=1.0,
            board_edge_fed_ifa_height_mm=6.3,
            board_edge_fed_ifa_length_mm=4.8,
            board_edge_fed_ifa_feed_offset_mm=1.35,
            board_edge_fed_ifa_gap_mm=0.18,
            board_edge_fed_ifa_width_mm=0.28,
        ),
        with_base(
            "edgeifa_s18p5_p6p2_h6p3_l4p8_f2p10_g0p18",
            "Same rim-pushed IFA as #9 with a farther feed tap to lower the very high input resistance.",
            element_spacing_mm=18.5,
            substrate_h_mm=1.6,
            patch_side_mm=6.2,
            slot_coupled_aperture_length_a_mm=2.2,
            slot_coupled_aperture_length_b_mm=2.2,
            slot_coupled_feedline_length_mm=5.8,
            board_edge_fed_ifa_enabled=1.0,
            board_edge_fed_ifa_height_mm=6.3,
            board_edge_fed_ifa_length_mm=4.8,
            board_edge_fed_ifa_feed_offset_mm=2.10,
            board_edge_fed_ifa_gap_mm=0.18,
            board_edge_fed_ifa_width_mm=0.28,
        ),
        with_base(
            "edgeifa_s19p5_p4p8_h6p3_l5p2_f1p80_g0p18",
            "Use a very small inactive patch footprint so the printed IFA can sit at the real board rim with a longer top arm.",
            element_spacing_mm=19.5,
            substrate_h_mm=1.6,
            patch_side_mm=4.8,
            slot_coupled_aperture_length_a_mm=1.8,
            slot_coupled_aperture_length_b_mm=1.8,
            slot_coupled_feedline_length_mm=4.6,
            board_edge_fed_ifa_enabled=1.0,
            board_edge_fed_ifa_height_mm=6.3,
            board_edge_fed_ifa_length_mm=5.2,
            board_edge_fed_ifa_feed_offset_mm=1.80,
            board_edge_fed_ifa_gap_mm=0.18,
            board_edge_fed_ifa_width_mm=0.28,
        ),
        with_base(
            "edgeifa_s19p5_p4p8_h6p3_l5p2_f2p60_g0p18",
            "Farther feed tap on the rim IFA to search for a better 50 ohm transform point before adding a discrete series element.",
            element_spacing_mm=19.5,
            substrate_h_mm=1.6,
            patch_side_mm=4.8,
            slot_coupled_aperture_length_a_mm=1.8,
            slot_coupled_aperture_length_b_mm=1.8,
            slot_coupled_feedline_length_mm=4.6,
            board_edge_fed_ifa_enabled=1.0,
            board_edge_fed_ifa_height_mm=6.3,
            board_edge_fed_ifa_length_mm=5.2,
            board_edge_fed_ifa_feed_offset_mm=2.60,
            board_edge_fed_ifa_gap_mm=0.18,
            board_edge_fed_ifa_width_mm=0.30,
        ),
        with_base(
            "edgeifa_s20p0_p4p2_h6p3_l5p4_f2p00_g0p15",
            "Push the IFA to the most aggressive board-rim placement that still fits the D44 circular outline.",
            element_spacing_mm=20.0,
            substrate_h_mm=1.6,
            patch_side_mm=4.2,
            slot_coupled_aperture_length_a_mm=1.6,
            slot_coupled_aperture_length_b_mm=1.6,
            slot_coupled_feedline_length_mm=4.0,
            board_edge_fed_ifa_enabled=1.0,
            board_edge_fed_ifa_height_mm=6.3,
            board_edge_fed_ifa_length_mm=5.4,
            board_edge_fed_ifa_feed_offset_mm=2.00,
            board_edge_fed_ifa_gap_mm=0.15,
            board_edge_fed_ifa_width_mm=0.30,
        ),
        with_base(
            "edgeifa_s20p0_p4p2_h6p3_l5p4_f2p80_g0p15",
            "High-feed-tap endpoint on the aggressive rim IFA, checking whether the resistance trend continues.",
            element_spacing_mm=20.0,
            substrate_h_mm=1.6,
            patch_side_mm=4.2,
            slot_coupled_aperture_length_a_mm=1.6,
            slot_coupled_aperture_length_b_mm=1.6,
            slot_coupled_feedline_length_mm=4.0,
            board_edge_fed_ifa_enabled=1.0,
            board_edge_fed_ifa_height_mm=6.3,
            board_edge_fed_ifa_length_mm=5.4,
            board_edge_fed_ifa_feed_offset_mm=2.80,
            board_edge_fed_ifa_gap_mm=0.15,
            board_edge_fed_ifa_width_mm=0.30,
        ),
        with_base(
            "edgeifa_s19p0_p5p4_h6p3_l5p0_f1p80_foldpar",
            "Add a passive folded edge arm beside the true-fed IFA as a low-cost parasitic aperture to strengthen low-elevation current.",
            element_spacing_mm=19.0,
            substrate_h_mm=1.6,
            patch_side_mm=6.2,
            slot_coupled_aperture_length_a_mm=2.0,
            slot_coupled_aperture_length_b_mm=2.0,
            slot_coupled_feedline_length_mm=5.8,
            slot_coupled_folded_edge_arm_enabled=1.0,
            slot_coupled_folded_edge_arm_radial_length_mm=1.0,
            slot_coupled_folded_edge_arm_tangent_length_mm=2.7,
            slot_coupled_folded_edge_arm_height_mm=5.9,
            slot_coupled_folded_edge_arm_width_mm=0.24,
            board_edge_fed_ifa_enabled=1.0,
            board_edge_fed_ifa_height_mm=6.3,
            board_edge_fed_ifa_length_mm=5.0,
            board_edge_fed_ifa_feed_offset_mm=1.80,
            board_edge_fed_ifa_gap_mm=0.18,
            board_edge_fed_ifa_width_mm=0.28,
        ),
        with_base(
            "edgeifa_s19p5_p4p8_h6p3_l5p2_f1p80_hloop",
            "Keep the real board-edge IFA and open a small horizon loop in the inactive patch background to reduce stored energy near A/B loads.",
            element_spacing_mm=19.5,
            substrate_h_mm=1.6,
            patch_side_mm=4.8,
            slot_coupled_aperture_length_a_mm=1.8,
            slot_coupled_aperture_length_b_mm=1.8,
            slot_coupled_feedline_length_mm=4.6,
            slot_coupled_horizon_loop_enabled=1.0,
            slot_coupled_horizon_loop_inner_side_mm=2.8,
            board_edge_fed_ifa_enabled=1.0,
            board_edge_fed_ifa_height_mm=6.3,
            board_edge_fed_ifa_length_mm=5.2,
            board_edge_fed_ifa_feed_offset_mm=1.80,
            board_edge_fed_ifa_gap_mm=0.18,
            board_edge_fed_ifa_width_mm=0.28,
        ),
        with_base(
            "edgeifa_s19p0_foldpar_match_c0p173_l6p1",
            "Apply the load-side L-match solved from #15 impedance: about 0.173 pF series C plus 6.1 nH shunt L.",
            element_spacing_mm=19.0,
            substrate_h_mm=1.6,
            patch_side_mm=6.2,
            slot_coupled_aperture_length_a_mm=2.0,
            slot_coupled_aperture_length_b_mm=2.0,
            slot_coupled_feedline_length_mm=5.8,
            slot_coupled_folded_edge_arm_enabled=1.0,
            slot_coupled_folded_edge_arm_radial_length_mm=1.0,
            slot_coupled_folded_edge_arm_tangent_length_mm=2.7,
            slot_coupled_folded_edge_arm_height_mm=5.9,
            slot_coupled_folded_edge_arm_width_mm=0.24,
            board_edge_fed_ifa_enabled=1.0,
            board_edge_fed_ifa_height_mm=6.3,
            board_edge_fed_ifa_length_mm=5.0,
            board_edge_fed_ifa_feed_offset_mm=1.80,
            board_edge_fed_ifa_gap_mm=0.18,
            board_edge_fed_ifa_width_mm=0.28,
            board_edge_fed_l_feed_neck_length_mm=0.80,
            board_edge_fed_l_feed_neck_width_mm=0.16,
            board_edge_fed_l_series_match_enabled=1.0,
            board_edge_fed_l_series_match_width_mm=0.16,
            board_edge_fed_l_series_match_capacitance_pf=0.173,
            board_edge_fed_l_match_enabled=1.0,
            board_edge_fed_l_match_inductance_nh=6.1,
        ),
        with_base(
            "edgeifa_s19p0_foldpar_match_c0p160_l5p6",
            "Slightly weaker series/shunt match around the #15 solution to absorb source-island and pad parasitics.",
            element_spacing_mm=19.0,
            substrate_h_mm=1.6,
            patch_side_mm=6.2,
            slot_coupled_aperture_length_a_mm=2.0,
            slot_coupled_aperture_length_b_mm=2.0,
            slot_coupled_feedline_length_mm=5.8,
            slot_coupled_folded_edge_arm_enabled=1.0,
            slot_coupled_folded_edge_arm_radial_length_mm=1.0,
            slot_coupled_folded_edge_arm_tangent_length_mm=2.7,
            slot_coupled_folded_edge_arm_height_mm=5.9,
            slot_coupled_folded_edge_arm_width_mm=0.24,
            board_edge_fed_ifa_enabled=1.0,
            board_edge_fed_ifa_height_mm=6.3,
            board_edge_fed_ifa_length_mm=5.0,
            board_edge_fed_ifa_feed_offset_mm=1.80,
            board_edge_fed_ifa_gap_mm=0.18,
            board_edge_fed_ifa_width_mm=0.28,
            board_edge_fed_l_feed_neck_length_mm=0.70,
            board_edge_fed_l_feed_neck_width_mm=0.16,
            board_edge_fed_l_series_match_enabled=1.0,
            board_edge_fed_l_series_match_width_mm=0.16,
            board_edge_fed_l_series_match_capacitance_pf=0.160,
            board_edge_fed_l_match_enabled=1.0,
            board_edge_fed_l_match_inductance_nh=5.6,
        ),
        with_base(
            "edgeifa_s19p0_foldpar_match_c0p190_l6p8",
            "Stronger matched endpoint around the #15 solution, checking whether the physical series island needs more compensation.",
            element_spacing_mm=19.0,
            substrate_h_mm=1.6,
            patch_side_mm=6.2,
            slot_coupled_aperture_length_a_mm=2.0,
            slot_coupled_aperture_length_b_mm=2.0,
            slot_coupled_feedline_length_mm=5.8,
            slot_coupled_folded_edge_arm_enabled=1.0,
            slot_coupled_folded_edge_arm_radial_length_mm=1.0,
            slot_coupled_folded_edge_arm_tangent_length_mm=2.7,
            slot_coupled_folded_edge_arm_height_mm=5.9,
            slot_coupled_folded_edge_arm_width_mm=0.24,
            board_edge_fed_ifa_enabled=1.0,
            board_edge_fed_ifa_height_mm=6.3,
            board_edge_fed_ifa_length_mm=5.0,
            board_edge_fed_ifa_feed_offset_mm=1.80,
            board_edge_fed_ifa_gap_mm=0.18,
            board_edge_fed_ifa_width_mm=0.28,
            board_edge_fed_l_feed_neck_length_mm=0.90,
            board_edge_fed_l_feed_neck_width_mm=0.16,
            board_edge_fed_l_series_match_enabled=1.0,
            board_edge_fed_l_series_match_width_mm=0.16,
            board_edge_fed_l_series_match_capacitance_pf=0.190,
            board_edge_fed_l_match_enabled=1.0,
            board_edge_fed_l_match_inductance_nh=6.8,
        ),
        with_base(
            "edgeifa_s19p0_foldpar_hiarm_raw",
            "Raise and widen the passive folded edge arm around #15 to add gain margin before applying the matching network.",
            element_spacing_mm=19.0,
            substrate_h_mm=1.6,
            patch_side_mm=6.2,
            slot_coupled_aperture_length_a_mm=2.0,
            slot_coupled_aperture_length_b_mm=2.0,
            slot_coupled_feedline_length_mm=5.8,
            slot_coupled_folded_edge_arm_enabled=1.0,
            slot_coupled_folded_edge_arm_radial_length_mm=1.2,
            slot_coupled_folded_edge_arm_tangent_length_mm=2.65,
            slot_coupled_folded_edge_arm_height_mm=6.3,
            slot_coupled_folded_edge_arm_width_mm=0.30,
            board_edge_fed_ifa_enabled=1.0,
            board_edge_fed_ifa_height_mm=6.3,
            board_edge_fed_ifa_length_mm=5.0,
            board_edge_fed_ifa_feed_offset_mm=1.80,
            board_edge_fed_ifa_gap_mm=0.18,
            board_edge_fed_ifa_width_mm=0.34,
        ),
        with_base(
            "edgeifa_s19p0_foldpar_hiarm_match_c0p173_l6p1",
            "Apply the #15 solved L-match to the higher passive-arm geometry, targeting simultaneous gain and S11 pass.",
            element_spacing_mm=19.0,
            substrate_h_mm=1.6,
            patch_side_mm=6.2,
            feed_pad_radius_mm=0.16,
            port_width_mm=0.34,
            slot_coupled_aperture_length_a_mm=2.0,
            slot_coupled_aperture_length_b_mm=2.0,
            slot_coupled_feedline_length_mm=5.8,
            slot_coupled_folded_edge_arm_enabled=1.0,
            slot_coupled_folded_edge_arm_radial_length_mm=1.2,
            slot_coupled_folded_edge_arm_tangent_length_mm=2.65,
            slot_coupled_folded_edge_arm_height_mm=6.3,
            slot_coupled_folded_edge_arm_width_mm=0.30,
            board_edge_fed_ifa_enabled=1.0,
            board_edge_fed_ifa_height_mm=6.3,
            board_edge_fed_ifa_length_mm=5.0,
            board_edge_fed_ifa_feed_offset_mm=1.80,
            board_edge_fed_ifa_gap_mm=0.18,
            board_edge_fed_ifa_width_mm=0.34,
            board_edge_fed_l_feed_neck_length_mm=0.80,
            board_edge_fed_l_feed_neck_width_mm=0.14,
            board_edge_fed_l_series_match_enabled=1.0,
            board_edge_fed_l_series_match_width_mm=0.14,
            board_edge_fed_l_series_match_capacitance_pf=0.173,
            board_edge_fed_l_match_enabled=1.0,
            board_edge_fed_l_match_inductance_nh=6.1,
        ),
        with_base(
            "edgeifa_s19p0_foldpar_hiarm_match_c0p190_l6p8",
            "Stronger matched endpoint on the higher passive-arm geometry.",
            element_spacing_mm=19.0,
            substrate_h_mm=1.6,
            patch_side_mm=6.2,
            feed_pad_radius_mm=0.16,
            port_width_mm=0.34,
            slot_coupled_aperture_length_a_mm=2.0,
            slot_coupled_aperture_length_b_mm=2.0,
            slot_coupled_feedline_length_mm=5.8,
            slot_coupled_folded_edge_arm_enabled=1.0,
            slot_coupled_folded_edge_arm_radial_length_mm=1.2,
            slot_coupled_folded_edge_arm_tangent_length_mm=2.65,
            slot_coupled_folded_edge_arm_height_mm=6.3,
            slot_coupled_folded_edge_arm_width_mm=0.30,
            board_edge_fed_ifa_enabled=1.0,
            board_edge_fed_ifa_height_mm=6.3,
            board_edge_fed_ifa_length_mm=5.0,
            board_edge_fed_ifa_feed_offset_mm=1.80,
            board_edge_fed_ifa_gap_mm=0.18,
            board_edge_fed_ifa_width_mm=0.34,
            board_edge_fed_l_feed_neck_length_mm=0.90,
            board_edge_fed_l_feed_neck_width_mm=0.14,
            board_edge_fed_l_series_match_enabled=1.0,
            board_edge_fed_l_series_match_width_mm=0.14,
            board_edge_fed_l_series_match_capacitance_pf=0.190,
            board_edge_fed_l_match_enabled=1.0,
            board_edge_fed_l_match_inductance_nh=6.8,
        ),
        with_base(
            "edgeifa_s19p0_foldpar_hiarm_neg_match_c0p173_l6p1",
            "Mirror the passive folded arm tangent direction to check whether the best-270 weak side moves out of the selected window.",
            element_spacing_mm=19.0,
            substrate_h_mm=1.6,
            patch_side_mm=6.2,
            feed_pad_radius_mm=0.16,
            port_width_mm=0.34,
            slot_coupled_aperture_length_a_mm=2.0,
            slot_coupled_aperture_length_b_mm=2.0,
            slot_coupled_feedline_length_mm=5.8,
            slot_coupled_folded_edge_arm_enabled=1.0,
            slot_coupled_folded_edge_arm_radial_length_mm=1.2,
            slot_coupled_folded_edge_arm_tangent_length_mm=2.65,
            slot_coupled_folded_edge_arm_height_mm=6.3,
            slot_coupled_folded_edge_arm_width_mm=0.30,
            slot_coupled_folded_edge_arm_turn_sign=-1.0,
            board_edge_fed_ifa_enabled=1.0,
            board_edge_fed_ifa_height_mm=6.3,
            board_edge_fed_ifa_length_mm=5.0,
            board_edge_fed_ifa_feed_offset_mm=1.80,
            board_edge_fed_ifa_gap_mm=0.18,
            board_edge_fed_ifa_width_mm=0.34,
            board_edge_fed_l_feed_neck_length_mm=0.80,
            board_edge_fed_l_feed_neck_width_mm=0.14,
            board_edge_fed_l_series_match_enabled=1.0,
            board_edge_fed_l_series_match_width_mm=0.14,
            board_edge_fed_l_series_match_capacitance_pf=0.173,
            board_edge_fed_l_match_enabled=1.0,
            board_edge_fed_l_match_inductance_nh=6.1,
        ),
        with_base(
            "edgeifa_s19p0_foldpar_mini_match_c0p173_l6p1",
            "Return to the #15 gain-oriented radiator and use a smaller source island/series strip so the externalizable L-match perturbs the low-angle current less.",
            element_spacing_mm=19.0,
            substrate_h_mm=1.6,
            patch_side_mm=6.2,
            feed_pad_radius_mm=0.16,
            port_width_mm=0.34,
            slot_coupled_aperture_length_a_mm=2.0,
            slot_coupled_aperture_length_b_mm=2.0,
            slot_coupled_feedline_length_mm=5.8,
            slot_coupled_folded_edge_arm_enabled=1.0,
            slot_coupled_folded_edge_arm_radial_length_mm=1.0,
            slot_coupled_folded_edge_arm_tangent_length_mm=2.7,
            slot_coupled_folded_edge_arm_height_mm=5.9,
            slot_coupled_folded_edge_arm_width_mm=0.24,
            board_edge_fed_ifa_enabled=1.0,
            board_edge_fed_ifa_height_mm=6.3,
            board_edge_fed_ifa_length_mm=5.0,
            board_edge_fed_ifa_feed_offset_mm=1.80,
            board_edge_fed_ifa_gap_mm=0.18,
            board_edge_fed_ifa_width_mm=0.28,
            board_edge_fed_l_feed_neck_length_mm=0.80,
            board_edge_fed_l_feed_neck_width_mm=0.14,
            board_edge_fed_l_series_match_enabled=1.0,
            board_edge_fed_l_series_match_width_mm=0.14,
            board_edge_fed_l_series_match_capacitance_pf=0.173,
            board_edge_fed_l_match_enabled=1.0,
            board_edge_fed_l_match_inductance_nh=6.1,
        ),
        with_base(
            "edgeifa_s19p0_foldpar_mini_match_c0p165_l5p8",
            "Slightly weaker mini L-match around the #15 solution to recover gain if the compact source island adds extra capacitance.",
            element_spacing_mm=19.0,
            substrate_h_mm=1.6,
            patch_side_mm=6.2,
            feed_pad_radius_mm=0.16,
            port_width_mm=0.34,
            slot_coupled_aperture_length_a_mm=2.0,
            slot_coupled_aperture_length_b_mm=2.0,
            slot_coupled_feedline_length_mm=5.8,
            slot_coupled_folded_edge_arm_enabled=1.0,
            slot_coupled_folded_edge_arm_radial_length_mm=1.0,
            slot_coupled_folded_edge_arm_tangent_length_mm=2.7,
            slot_coupled_folded_edge_arm_height_mm=5.9,
            slot_coupled_folded_edge_arm_width_mm=0.24,
            board_edge_fed_ifa_enabled=1.0,
            board_edge_fed_ifa_height_mm=6.3,
            board_edge_fed_ifa_length_mm=5.0,
            board_edge_fed_ifa_feed_offset_mm=1.80,
            board_edge_fed_ifa_gap_mm=0.18,
            board_edge_fed_ifa_width_mm=0.28,
            board_edge_fed_l_feed_neck_length_mm=0.80,
            board_edge_fed_l_feed_neck_width_mm=0.14,
            board_edge_fed_l_series_match_enabled=1.0,
            board_edge_fed_l_series_match_width_mm=0.14,
            board_edge_fed_l_series_match_capacitance_pf=0.165,
            board_edge_fed_l_match_enabled=1.0,
            board_edge_fed_l_match_inductance_nh=5.8,
        ),
        with_base(
            "edgeifa_s19p0_foldpar_mini_match_c0p185_l6p4",
            "Slightly stronger mini L-match around the #15 solution, checking the high-Q side without adding extra printed stub length.",
            element_spacing_mm=19.0,
            substrate_h_mm=1.6,
            patch_side_mm=6.2,
            feed_pad_radius_mm=0.16,
            port_width_mm=0.34,
            slot_coupled_aperture_length_a_mm=2.0,
            slot_coupled_aperture_length_b_mm=2.0,
            slot_coupled_feedline_length_mm=5.8,
            slot_coupled_folded_edge_arm_enabled=1.0,
            slot_coupled_folded_edge_arm_radial_length_mm=1.0,
            slot_coupled_folded_edge_arm_tangent_length_mm=2.7,
            slot_coupled_folded_edge_arm_height_mm=5.9,
            slot_coupled_folded_edge_arm_width_mm=0.24,
            board_edge_fed_ifa_enabled=1.0,
            board_edge_fed_ifa_height_mm=6.3,
            board_edge_fed_ifa_length_mm=5.0,
            board_edge_fed_ifa_feed_offset_mm=1.80,
            board_edge_fed_ifa_gap_mm=0.18,
            board_edge_fed_ifa_width_mm=0.28,
            board_edge_fed_l_feed_neck_length_mm=0.80,
            board_edge_fed_l_feed_neck_width_mm=0.14,
            board_edge_fed_l_series_match_enabled=1.0,
            board_edge_fed_l_series_match_width_mm=0.14,
            board_edge_fed_l_series_match_capacitance_pf=0.185,
            board_edge_fed_l_match_enabled=1.0,
            board_edge_fed_l_match_inductance_nh=6.4,
        ),
        with_base(
            "edgeifa_s19p0_foldpar_mini_match_stub0p45_c0p173_l6p1",
            "Move the shunt inductor a short distance along a printed side stub, reducing direct loading at the radiator feed while keeping a low-cost layout.",
            element_spacing_mm=19.0,
            substrate_h_mm=1.6,
            patch_side_mm=6.2,
            feed_pad_radius_mm=0.16,
            port_width_mm=0.34,
            slot_coupled_aperture_length_a_mm=2.0,
            slot_coupled_aperture_length_b_mm=2.0,
            slot_coupled_feedline_length_mm=5.8,
            slot_coupled_folded_edge_arm_enabled=1.0,
            slot_coupled_folded_edge_arm_radial_length_mm=1.0,
            slot_coupled_folded_edge_arm_tangent_length_mm=2.7,
            slot_coupled_folded_edge_arm_height_mm=5.9,
            slot_coupled_folded_edge_arm_width_mm=0.24,
            board_edge_fed_ifa_enabled=1.0,
            board_edge_fed_ifa_height_mm=6.3,
            board_edge_fed_ifa_length_mm=5.0,
            board_edge_fed_ifa_feed_offset_mm=1.80,
            board_edge_fed_ifa_gap_mm=0.18,
            board_edge_fed_ifa_width_mm=0.28,
            board_edge_fed_l_feed_neck_length_mm=0.80,
            board_edge_fed_l_feed_neck_width_mm=0.14,
            board_edge_fed_l_series_match_enabled=1.0,
            board_edge_fed_l_series_match_width_mm=0.14,
            board_edge_fed_l_series_match_capacitance_pf=0.173,
            board_edge_fed_l_match_enabled=1.0,
            board_edge_fed_l_match_stub_length_mm=0.45,
            board_edge_fed_l_match_stub_width_mm=0.14,
            board_edge_fed_l_match_inductance_nh=6.1,
        ),
        with_base(
            "edgeifa_s19p0_foldpar_tall_mini_match_c0p173_l6p1",
            "Use a modestly taller parasitic edge arm with the compact L-match, seeking a little gain margin without the wider high-arm penalty seen in #20.",
            element_spacing_mm=19.0,
            substrate_h_mm=1.6,
            patch_side_mm=6.2,
            feed_pad_radius_mm=0.16,
            port_width_mm=0.34,
            slot_coupled_aperture_length_a_mm=2.0,
            slot_coupled_aperture_length_b_mm=2.0,
            slot_coupled_feedline_length_mm=5.8,
            slot_coupled_folded_edge_arm_enabled=1.0,
            slot_coupled_folded_edge_arm_radial_length_mm=1.1,
            slot_coupled_folded_edge_arm_tangent_length_mm=2.75,
            slot_coupled_folded_edge_arm_height_mm=6.15,
            slot_coupled_folded_edge_arm_width_mm=0.26,
            board_edge_fed_ifa_enabled=1.0,
            board_edge_fed_ifa_height_mm=6.3,
            board_edge_fed_ifa_length_mm=5.0,
            board_edge_fed_ifa_feed_offset_mm=1.80,
            board_edge_fed_ifa_gap_mm=0.18,
            board_edge_fed_ifa_width_mm=0.30,
            board_edge_fed_l_feed_neck_length_mm=0.80,
            board_edge_fed_l_feed_neck_width_mm=0.14,
            board_edge_fed_l_series_match_enabled=1.0,
            board_edge_fed_l_series_match_width_mm=0.14,
            board_edge_fed_l_series_match_capacitance_pf=0.173,
            board_edge_fed_l_match_enabled=1.0,
            board_edge_fed_l_match_inductance_nh=6.1,
        ),
        with_base(
            "edgeifa_s19p0_foldpar_stub0p45_c0p150_l8p0",
            "Retune the 0.45 mm displaced shunt point with weaker inductive loading and a smaller series capacitance after #27 showed low input resistance.",
            **foldpar_mini_common,
            board_edge_fed_l_series_match_capacitance_pf=0.150,
            board_edge_fed_l_match_stub_length_mm=0.45,
            board_edge_fed_l_match_inductance_nh=8.0,
        ),
        with_base(
            "edgeifa_s19p0_foldpar_stub0p45_c0p140_l9p5",
            "Move farther toward the raw high-impedance radiator from the #27 point, aiming to recover low-elevation gain while retaining an L-match.",
            **foldpar_mini_common,
            board_edge_fed_l_series_match_capacitance_pf=0.140,
            board_edge_fed_l_match_stub_length_mm=0.45,
            board_edge_fed_l_match_inductance_nh=9.5,
        ),
        with_base(
            "edgeifa_s19p0_foldpar_stub0p45_c0p130_l11p0",
            "Weakest 0.45 mm displaced shunt endpoint, checking whether the gain can approach #15 before the match becomes too light.",
            **foldpar_mini_common,
            board_edge_fed_l_series_match_capacitance_pf=0.130,
            board_edge_fed_l_match_stub_length_mm=0.45,
            board_edge_fed_l_match_inductance_nh=11.0,
        ),
        with_base(
            "edgeifa_s19p0_foldpar_stub0p30_c0p155_l8p0",
            "Bring the shunt point slightly closer than #27 and retune with weaker loading, bracketing the electrical length of the printed stub.",
            **foldpar_mini_common,
            board_edge_fed_l_series_match_capacitance_pf=0.155,
            board_edge_fed_l_match_stub_length_mm=0.30,
            board_edge_fed_l_match_inductance_nh=8.0,
        ),
        with_base(
            "edgeifa_s19p0_foldpar_stub0p25_c0p160_l7p0",
            "Short displaced shunt variant with moderate loading, targeting S11 recovery with less gain penalty than the feed-point shunt.",
            **foldpar_mini_common,
            board_edge_fed_l_series_match_capacitance_pf=0.160,
            board_edge_fed_l_match_stub_length_mm=0.25,
            board_edge_fed_l_match_inductance_nh=7.0,
        ),
        with_base(
            "edgeifa_s19p0_foldpar_stub0p60_c0p140_l10p0",
            "Longer displaced shunt variant that reduces current loading at the radiator feed and checks whether a looser externalizable match is viable.",
            **foldpar_mini_common,
            board_edge_fed_l_series_match_capacitance_pf=0.140,
            board_edge_fed_l_match_stub_length_mm=0.60,
            board_edge_fed_l_match_inductance_nh=10.0,
        ),
        with_base(
            "edgeifa_s19p0_foldpar_match_short_offset_m0p6",
            "Shorten the passive folded edge arm so it can be shifted toward the weak azimuth side while preserving the #17 S11-passing L-match.",
            **(
                foldpar_match_common
                | {
                    "slot_coupled_folded_edge_arm_tangent_length_mm": 2.0,
                    "slot_coupled_folded_edge_arm_offset_mm": -0.6,
                }
            ),
        ),
        with_base(
            "edgeifa_s19p0_foldpar_match_short_offset_p0p6",
            "Opposite shortened folded-arm lateral offset around the #17 matched radiator to bracket the weak-azimuth current path.",
            **(
                foldpar_match_common
                | {
                    "slot_coupled_folded_edge_arm_tangent_length_mm": 2.0,
                    "slot_coupled_folded_edge_arm_offset_mm": 0.6,
                }
            ),
        ),
        with_base(
            "edgeifa_s19p0_foldpar_match_edgearm_m1p0",
            "Add a small substrate-level printed board-edge arm on one side of the #17 matched radiator as a very low-cost current-path helper.",
            **foldpar_match_common,
            slot_coupled_edge_arm_enabled=1.0,
            slot_coupled_edge_arm_length_mm=2.0,
            slot_coupled_edge_arm_width_mm=0.20,
            slot_coupled_edge_arm_offset_mm=-1.0,
            slot_coupled_edge_arm_gap_mm=0.08,
        ),
        with_base(
            "edgeifa_s19p0_foldpar_match_edgearm_p1p0",
            "Mirror the small substrate-level printed board-edge arm to see which side lifts the best270 limiting azimuth.",
            **foldpar_match_common,
            slot_coupled_edge_arm_enabled=1.0,
            slot_coupled_edge_arm_length_mm=2.0,
            slot_coupled_edge_arm_width_mm=0.20,
            slot_coupled_edge_arm_offset_mm=1.0,
            slot_coupled_edge_arm_gap_mm=0.08,
        ),
        with_base(
            "edgeifa_s19p0_foldpar_match_passiveifa_m1p0",
            "Add a short passive board-edge IFA beside the true-fed IFA, using the same low-cost plated/via-wall manufacturing family.",
            **foldpar_match_common,
            slot_coupled_board_edge_ifa_enabled=1.0,
            slot_coupled_board_edge_ifa_length_mm=3.2,
            slot_coupled_board_edge_ifa_width_mm=0.22,
            slot_coupled_board_edge_ifa_height_mm=5.2,
            slot_coupled_board_edge_ifa_gap_mm=0.12,
            slot_coupled_board_edge_ifa_offset_mm=-1.0,
        ),
        with_base(
            "edgeifa_s19p0_foldpar_match_passiveifa_p1p0",
            "Mirror the short passive board-edge IFA to bracket coupling polarity around the #17 matched radiator.",
            **foldpar_match_common,
            slot_coupled_board_edge_ifa_enabled=1.0,
            slot_coupled_board_edge_ifa_length_mm=3.2,
            slot_coupled_board_edge_ifa_width_mm=0.22,
            slot_coupled_board_edge_ifa_height_mm=5.2,
            slot_coupled_board_edge_ifa_gap_mm=0.12,
            slot_coupled_board_edge_ifa_offset_mm=1.0,
        ),
        with_base(
            "edgeifa_s19p0_short_m0p6_match_c0p142_l3p65",
            "Retune the high-gain #35 shortened/offset folded arm using the de-embedded 389+j148 ohm radiator estimate.",
            **(
                foldpar_match_common
                | {
                    "slot_coupled_folded_edge_arm_tangent_length_mm": 2.0,
                    "slot_coupled_folded_edge_arm_offset_mm": -0.6,
                    "board_edge_fed_l_series_match_capacitance_pf": 0.142,
                    "board_edge_fed_l_match_inductance_nh": 3.65,
                }
            ),
        ),
        with_base(
            "edgeifa_s19p0_short_m0p6_match_c0p140_l3p70",
            "Neighbor retune around the #35 de-embedded optimum with a slightly weaker series capacitance.",
            **(
                foldpar_match_common
                | {
                    "slot_coupled_folded_edge_arm_tangent_length_mm": 2.0,
                    "slot_coupled_folded_edge_arm_offset_mm": -0.6,
                    "board_edge_fed_l_series_match_capacitance_pf": 0.140,
                    "board_edge_fed_l_match_inductance_nh": 3.70,
                }
            ),
        ),
        with_base(
            "edgeifa_s19p0_short_m0p6_match_c0p144_l3p55",
            "Neighbor retune around the #35 de-embedded optimum with a slightly stronger series capacitance and lower shunt inductance.",
            **(
                foldpar_match_common
                | {
                    "slot_coupled_folded_edge_arm_tangent_length_mm": 2.0,
                    "slot_coupled_folded_edge_arm_offset_mm": -0.6,
                    "board_edge_fed_l_series_match_capacitance_pf": 0.144,
                    "board_edge_fed_l_match_inductance_nh": 3.55,
                }
            ),
        ),
        with_base(
            "edgeifa_s19p0_short_m0p6_match_c0p138_l3p75",
            "Lower-capacitance endpoint around the #35 de-embedded optimum to cover source-island parasitic uncertainty.",
            **(
                foldpar_match_common
                | {
                    "slot_coupled_folded_edge_arm_tangent_length_mm": 2.0,
                    "slot_coupled_folded_edge_arm_offset_mm": -0.6,
                    "board_edge_fed_l_series_match_capacitance_pf": 0.138,
                    "board_edge_fed_l_match_inductance_nh": 3.75,
                }
            ),
        ),
        with_base(
            "edgeifa_s19p0_short_m0p6_match_c0p124_l3p00",
            "Second-pass retune from #41 complex impedance, using stronger shunt loading while keeping the high-gain shortened offset arm.",
            **(
                foldpar_match_common
                | {
                    "slot_coupled_folded_edge_arm_tangent_length_mm": 2.0,
                    "slot_coupled_folded_edge_arm_offset_mm": -0.6,
                    "board_edge_fed_l_series_match_capacitance_pf": 0.124,
                    "board_edge_fed_l_match_inductance_nh": 3.00,
                }
            ),
        ),
        with_base(
            "edgeifa_s19p0_short_m0p6_match_c0p125_l2p98",
            "Neighbor around the second-pass retune point with slightly higher series capacitance and lower shunt inductance.",
            **(
                foldpar_match_common
                | {
                    "slot_coupled_folded_edge_arm_tangent_length_mm": 2.0,
                    "slot_coupled_folded_edge_arm_offset_mm": -0.6,
                    "board_edge_fed_l_series_match_capacitance_pf": 0.125,
                    "board_edge_fed_l_match_inductance_nh": 2.98,
                }
            ),
        ),
        with_base(
            "edgeifa_s19p0_short_m0p6_match_c0p122_l3p05",
            "Low-capacitance/high-inductance neighbor around the second-pass retune point.",
            **(
                foldpar_match_common
                | {
                    "slot_coupled_folded_edge_arm_tangent_length_mm": 2.0,
                    "slot_coupled_folded_edge_arm_offset_mm": -0.6,
                    "board_edge_fed_l_series_match_capacitance_pf": 0.122,
                    "board_edge_fed_l_match_inductance_nh": 3.05,
                }
            ),
        ),
        with_base(
            "edgeifa_s19p0_short_m0p6_match_c0p127_l2p95",
            "High-capacitance/low-inductance neighbor around the second-pass retune point.",
            **(
                foldpar_match_common
                | {
                    "slot_coupled_folded_edge_arm_tangent_length_mm": 2.0,
                    "slot_coupled_folded_edge_arm_offset_mm": -0.6,
                    "board_edge_fed_l_series_match_capacitance_pf": 0.127,
                    "board_edge_fed_l_match_inductance_nh": 2.95,
                }
            ),
        ),
        with_base(
            "edgeifa_s19p0_short_m0p6_match_c0p110_l2p70",
            "Third-pass retune from #45 complex impedance; stronger shunt loading targets the remaining high-resistance S11 miss.",
            **(
                foldpar_match_common
                | {
                    "slot_coupled_folded_edge_arm_tangent_length_mm": 2.0,
                    "slot_coupled_folded_edge_arm_offset_mm": -0.6,
                    "board_edge_fed_l_series_match_capacitance_pf": 0.110,
                    "board_edge_fed_l_match_inductance_nh": 2.70,
                }
            ),
        ),
        with_base(
            "edgeifa_s19p0_short_m0p6_damped_c0p156_l2p20_r820",
            "Damped low-cost discrete match for the high-gain short-offset arm; accepts some resistor loss to close the remaining S11 gap.",
            **(
                foldpar_match_common
                | {
                    "slot_coupled_folded_edge_arm_tangent_length_mm": 2.0,
                    "slot_coupled_folded_edge_arm_offset_mm": -0.6,
                    "board_edge_fed_l_series_match_capacitance_pf": 0.156,
                    "board_edge_fed_l_match_inductance_nh": 2.20,
                    "board_edge_fed_l_match_resistance_ohm": 820.0,
                }
            ),
        ),
        with_base(
            "edgeifa_s19p0_short_m0p6_damped_c0p146_l2p30_r1000",
            "Moderate-damping neighbor with a 1 kohm shunt resistor in the discrete match.",
            **(
                foldpar_match_common
                | {
                    "slot_coupled_folded_edge_arm_tangent_length_mm": 2.0,
                    "slot_coupled_folded_edge_arm_offset_mm": -0.6,
                    "board_edge_fed_l_series_match_capacitance_pf": 0.146,
                    "board_edge_fed_l_match_inductance_nh": 2.30,
                    "board_edge_fed_l_match_resistance_ohm": 1000.0,
                }
            ),
        ),
        with_base(
            "edgeifa_s19p0_short_m0p6_damped_c0p134_l2p40_r1500",
            "Light-damping neighbor with a 1.5 kohm shunt resistor, trading less loss against a shallower S11 correction.",
            **(
                foldpar_match_common
                | {
                    "slot_coupled_folded_edge_arm_tangent_length_mm": 2.0,
                    "slot_coupled_folded_edge_arm_offset_mm": -0.6,
                    "board_edge_fed_l_series_match_capacitance_pf": 0.134,
                    "board_edge_fed_l_match_inductance_nh": 2.40,
                    "board_edge_fed_l_match_resistance_ohm": 1500.0,
                }
            ),
        ),
        with_base(
            "edgeifa_s19p0_short_m0p6_damped_c0p142_l2p00_r680",
            "Post-#50 retune with moderate damping and lower shunt inductance to add S11 margin.",
            **(
                foldpar_match_common
                | {
                    "slot_coupled_folded_edge_arm_tangent_length_mm": 2.0,
                    "slot_coupled_folded_edge_arm_offset_mm": -0.6,
                    "board_edge_fed_l_series_match_capacitance_pf": 0.142,
                    "board_edge_fed_l_match_inductance_nh": 2.00,
                    "board_edge_fed_l_match_resistance_ohm": 680.0,
                }
            ),
        ),
        with_base(
            "edgeifa_s19p0_short_m0p6_damped_c0p130_l2p10_r820",
            "Post-#50 retune keeping 820 ohm damping but reducing both series capacitance and shunt inductance.",
            **(
                foldpar_match_common
                | {
                    "slot_coupled_folded_edge_arm_tangent_length_mm": 2.0,
                    "slot_coupled_folded_edge_arm_offset_mm": -0.6,
                    "board_edge_fed_l_series_match_capacitance_pf": 0.130,
                    "board_edge_fed_l_match_inductance_nh": 2.10,
                    "board_edge_fed_l_match_resistance_ohm": 820.0,
                }
            ),
        ),
        with_base(
            "edgeifa_s19p0_short_m0p6_damped_c0p178_l1p80_r390",
            "High-damping endpoint to confirm the achievable S11 floor and remaining GainTotal margin.",
            **(
                foldpar_match_common
                | {
                    "slot_coupled_folded_edge_arm_tangent_length_mm": 2.0,
                    "slot_coupled_folded_edge_arm_offset_mm": -0.6,
                    "board_edge_fed_l_series_match_capacitance_pf": 0.178,
                    "board_edge_fed_l_match_inductance_nh": 1.80,
                    "board_edge_fed_l_match_resistance_ohm": 390.0,
                }
            ),
        ),
        with_base(
            "sidewall_pifa_s19p0_short_m0p6_c0p142_l2p00_r680",
            "Manufacturing conversion of the passing #53 geometry: active IFA/PIFA and folded parasitic path are implemented as thick-PCB sidewall metallization/via-wall copper.",
            **sidewall_pifa_common,
        ),
        with_base(
            "sidewall_pifa_s19p0_short_m0p6_c0p120_l1p60_r680",
            "Lower-series-capacitance sidewall neighbor to compensate the thicker sidewall current path and stronger short-wall capacitance.",
            **(
                sidewall_pifa_common
                | {
                    "board_edge_fed_l_series_match_capacitance_pf": 0.120,
                    "board_edge_fed_l_match_inductance_nh": 1.60,
                }
            ),
        ),
        with_base(
            "sidewall_pifa_s19p0_short_m0p6_c0p165_l2p40_r820",
            "Higher-reactance sidewall neighbor with lighter damping loss, checking whether the sidewall implementation keeps enough S11 margin.",
            **(
                sidewall_pifa_common
                | {
                    "board_edge_fed_l_series_match_capacitance_pf": 0.165,
                    "board_edge_fed_l_match_inductance_nh": 2.40,
                    "board_edge_fed_l_match_resistance_ohm": 820.0,
                }
            ),
        ),
        with_base(
            "sidewall_pifa_s19p0_short_m0p6_c0p100_l1p20_r560",
            "Stronger sidewall retune with lower C/L and moderate damping for the high-permittivity thick-board environment.",
            **(
                sidewall_pifa_common
                | {
                    "board_edge_fed_l_series_match_capacitance_pf": 0.100,
                    "board_edge_fed_l_match_inductance_nh": 1.20,
                    "board_edge_fed_l_match_resistance_ohm": 560.0,
                }
            ),
        ),
        with_base(
            "sidewall_pifa_foam_s19p0_short_m0p6_c0p142_l2p00_r680",
            "Same sidewall-metallized PIFA geometry, but using a low-epsilon thick carrier/foam equivalent instead of solid RO4350B to check whether the manufacturing conversion can preserve the air-supported radiation mode.",
            **(
                sidewall_pifa_common
                | {
                    "epsr": 1.12,
                    "tan_delta": 0.0008,
                }
            ),
        ),
        with_base(
            "sidewall_pifa_foam_s19p0_short_m0p6_c0p120_l1p60_r680",
            "Low-epsilon thick carrier with the lower-C/L sidewall retune.",
            **(
                sidewall_pifa_common
                | {
                    "epsr": 1.12,
                    "tan_delta": 0.0008,
                    "board_edge_fed_l_series_match_capacitance_pf": 0.120,
                    "board_edge_fed_l_match_inductance_nh": 1.60,
                }
            ),
        ),
        with_base(
            "edgeplate_pifa_air_s19p0_short_m0p6_c0p142_l2p00_r680",
            "PCB edge-plated IFA/PIFA conversion: the active IFA trace is rotated onto the vertical board-edge sidewall plane while the low-elevation folded parasitic keeps the air-supported current path.",
            **sidewall_plane_pifa_common,
        ),
        with_base(
            "edgeplate_pifa_air_nofold_s19p0_c0p142_l2p00_r680",
            "Active sidewall-plane IFA/PIFA only, disabling the folded parasitic arm to isolate whether the manufacturable edge-plated PIFA can carry the low-elevation coverage by itself.",
            **(
                sidewall_plane_pifa_common
                | {
                    "slot_coupled_folded_edge_arm_enabled": 0.0,
                }
            ),
        ),
        with_base(
            "edgeplate_riser_pifa_s19p0_short_m0p6_c0p142_l2p00_r680",
            "Manufacturable edge-plated riser conversion of the passing #53 EM current path: keep the raised radial IFA/PIFA arm and short folded parasitic path, but implement the vertical sections as plated sidewall/castellated risers or a low-cost plated vertical carrier.",
            **(
                foldpar_match_common
                | {
                    "slot_coupled_folded_edge_arm_tangent_length_mm": 2.0,
                    "slot_coupled_folded_edge_arm_offset_mm": -0.6,
                    "board_edge_fed_l_series_match_capacitance_pf": 0.142,
                    "board_edge_fed_l_match_inductance_nh": 2.00,
                    "board_edge_fed_l_match_resistance_ohm": 680.0,
                }
            ),
        ),
    ]


def params_for(candidate: BoardEdgeCandidate) -> dict[str, Any]:
    params = base_params()
    params.update(candidate.updates)
    return params


def project_paths(candidate: BoardEdgeCandidate) -> dict[str, Path | str]:
    raw_slug = safe_slug(candidate.name)
    if len(raw_slug) > 36:
        digest = hashlib.sha1(candidate.name.encode("utf-8")).hexdigest()[:7]
        slug = f"{raw_slug[:28].rstrip('_-')}_{digest}"
    else:
        slug = raw_slug
    label = f"BEDGE_{slug}"
    project = ROOT / f"UWB_CH9_Diamond_CP_Array_D44_{label}.aedt"
    return {
        "label": label,
        "project": project,
        "results": project.with_suffix(".aedtresults"),
        "pyaedt": project.with_suffix(".pyaedt"),
        "params": REPORT_DIR / f"{STEM}_{slug}_params.json",
    }


def build_project(candidate: BoardEdgeCandidate, analyze: bool, cores: int, tasks: int) -> dict[str, Path | str]:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    paths = project_paths(candidate)
    params = params_for(candidate)
    original_spec = dict(builder.TOPOLOGIES[TOPOLOGY])
    original_elements = list(builder.ELEMENTS)
    try:
        builder.ELEMENTS = [("P1", 0.0)]
        builder.TOPOLOGIES[TOPOLOGY]["label"] = str(paths["label"])
        builder.TOPOLOGIES[TOPOLOGY]["design"] = DESIGN_NAME
        builder.TOPOLOGIES[TOPOLOGY]["description"] = (
            "Single true board-edge low-elevation P1L unit. "
            "The element center is intentionally offset toward the D44 rim so the L port is physically calibratable."
        )
        builder.TOPOLOGIES[TOPOLOGY]["params"] = params
        print(f"Stage: building {candidate.name}", flush=True)
        builder.build_project(
            TOPOLOGY,
            analyze=analyze,
            non_graphical=True,
            quick=True,
            band_samples=False,
            sparam_only=False,
            analysis_cores=cores,
            analysis_tasks=tasks,
        )
    finally:
        builder.ELEMENTS = original_elements
        builder.TOPOLOGIES[TOPOLOGY]["label"] = original_spec["label"]
        builder.TOPOLOGIES[TOPOLOGY]["design"] = original_spec["design"]
        builder.TOPOLOGIES[TOPOLOGY]["description"] = original_spec["description"]
        builder.TOPOLOGIES[TOPOLOGY]["params"] = original_spec["params"]
    Path(paths["params"]).write_text(
        json.dumps(
            {
                "project": str(paths["project"]),
                "design": DESIGN_NAME,
                "candidate": {"name": candidate.name, "rationale": candidate.rationale, "params": params},
                "model": "P1 element is placed near the D44 board edge; only P1L is an active port. A/B slot-coupled feeds are terminated as switch-off loads.",
                "target": {
                    "s11_db_max": RETURN_TARGET_DB,
                    "theta_deg": [THETA_MIN_DEG, THETA_MAX_DEG],
                    "azimuth_window_deg": AZIMUTH_WINDOW_DEG,
                    "gain_total_min_dbi": GAIN_TARGET_DBI,
                },
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return paths


def native_export(candidate: BoardEdgeCandidate, paths: dict[str, Path | str]) -> dict[str, Path]:
    case = safe_slug(candidate.name)
    env = os.environ.copy()
    env.update(
        {
            "D44_AEDT_PROJECT": str(paths["project"]),
            "D44_AEDT_PROJECT_NAME": Path(paths["project"]).stem,
            "D44_AEDT_DESIGN": DESIGN_NAME,
            "D44_AEDT_SOLUTION": SOLUTION,
            "D44_AEDT_SPHERE": SPHERE,
            "D44_AEDT_OUT_DIR": str(REPORT_DIR),
            "D44_AEDT_CASE": case,
            "D44_AEDT_FREQ_GHZ": f"{FREQ_GHZ:g}",
        }
    )
    report_log = REPORT_DIR / f"{case}_native_report_export.log"
    subprocess.run(
        [str(AEDT_EXE), "-ng", "-LogFile", str(report_log), "-RunScriptAndExit", str(NATIVE_REPORT_SCRIPT)],
        cwd=str(ROOT),
        env=env,
        check=True,
        timeout=420,
    )
    return {
        "s": REPORT_DIR / f"{case}_native_s_parameters.csv",
        "ff": REPORT_DIR / f"{case}_native_farfield_default.csv",
        "sources": REPORT_DIR / f"{case}_native_sources.txt",
        "log": report_log,
    }


def existing_exports(candidate: BoardEdgeCandidate) -> dict[str, Path]:
    case = safe_slug(candidate.name)
    return {
        "s": REPORT_DIR / f"{case}_native_s_parameters.csv",
        "ff": REPORT_DIR / f"{case}_native_farfield_default.csv",
        "sources": REPORT_DIR / f"{case}_native_sources.txt",
        "log": REPORT_DIR / f"{case}_native_report_export.log",
    }


def parse_s_csv(path: Path) -> dict[str, Any]:
    with path.open(newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    values: list[tuple[str, float, float]] = []
    for row in rows:
        freq = float(row.get("Freq [GHz]", row.get("Freq", FREQ_GHZ)))
        for key, value in row.items():
            if key.startswith("dB(S(") and value not in (None, ""):
                values.append((key, freq, float(value)))
    if not values:
        raise RuntimeError(f"No S-parameter data in {path}")
    expr, freq, worst = max(values, key=lambda item: item[2])
    return {
        "s_csv": str(path),
        "s11_expr": expr,
        "s11_worst_freq_ghz": freq,
        "s11_worst_db": worst,
        "s11_pass": worst <= RETURN_TARGET_DB,
    }


def angle_columns(header: list[str]) -> tuple[int, int]:
    theta_idx = next(idx for idx, name in enumerate(header) if name.startswith("Theta"))
    phi_idx = next(idx for idx, name in enumerate(header) if name.startswith("Phi"))
    return theta_idx, phi_idx


def parse_ff_csv(path: Path) -> list[dict[str, float]]:
    with path.open(newline="", encoding="utf-8-sig") as f:
        rows = list(csv.reader(f))
    if len(rows) < 2:
        raise RuntimeError(f"Empty far-field CSV: {path}")
    header = rows[0]
    theta_idx, phi_idx = angle_columns(header)
    gain_idx = next(idx for idx, name in enumerate(header) if "dB(GainTotal)" in name)
    raw_angles = [(float(row[theta_idx]), float(row[phi_idx])) for row in rows[1:] if len(row) > max(theta_idx, phi_idx)]
    swapped = bool(raw_angles) and max(theta for theta, _ in raw_angles) > 180.0 and max(phi for _, phi in raw_angles) <= 180.0
    parsed = []
    for raw in rows[1:]:
        if len(raw) <= max(theta_idx, phi_idx, gain_idx):
            continue
        raw_theta = float(raw[theta_idx])
        raw_phi = float(raw[phi_idx])
        theta = raw_phi if swapped else raw_theta
        phi_raw = raw_theta if swapped else raw_phi
        if abs(phi_raw - 360.0) < 1e-9:
            continue
        phi = phi_raw % 360.0
        if THETA_MIN_DEG <= theta <= THETA_MAX_DEG:
            parsed.append({"theta_deg": theta, "phi_deg": phi, "gain_total_dbi": float(raw[gain_idx])})
    if not parsed:
        raise RuntimeError(f"No low-elevation far-field rows in {path}")
    return parsed


def in_window(phi: float, start: float) -> bool:
    return ((phi - start) % 360.0) <= AZIMUTH_WINDOW_DEG + 1e-9


def window_metrics(rows: list[dict[str, float]]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    window_rows = []
    for start in sorted({row["phi_deg"] for row in rows}):
        selected = [row for row in rows if in_window(row["phi_deg"], start)]
        if not selected:
            continue
        worst = min(selected, key=lambda item: item["gain_total_dbi"])
        best = max(selected, key=lambda item: item["gain_total_dbi"])
        window_rows.append(
            {
                "window_start_phi_deg": start,
                "window_stop_phi_deg": (start + AZIMUTH_WINDOW_DEG) % 360.0,
                "sample_count": len(selected),
                "gain_total_min_dbi": worst["gain_total_dbi"],
                "gain_total_min_theta_deg": worst["theta_deg"],
                "gain_total_min_phi_deg": worst["phi_deg"],
                "gain_total_max_dbi": best["gain_total_dbi"],
                "gain_total_max_theta_deg": best["theta_deg"],
                "gain_total_max_phi_deg": best["phi_deg"],
            }
        )
    if not window_rows:
        raise RuntimeError("No azimuth windows could be evaluated")
    best_window = max(window_rows, key=lambda item: item["gain_total_min_dbi"])
    all_worst = min(rows, key=lambda item: item["gain_total_dbi"])
    metrics = {
        "ff_sample_count": len(rows),
        "all_phi_gain_total_min_dbi": all_worst["gain_total_dbi"],
        "all_phi_gain_total_min_theta_deg": all_worst["theta_deg"],
        "all_phi_gain_total_min_phi_deg": all_worst["phi_deg"],
        "best_270deg_window_start_phi_deg": best_window["window_start_phi_deg"],
        "best_270deg_window_stop_phi_deg": best_window["window_stop_phi_deg"],
        "best_270deg_gain_total_min_dbi": best_window["gain_total_min_dbi"],
        "best_270deg_gain_total_min_theta_deg": best_window["gain_total_min_theta_deg"],
        "best_270deg_gain_total_min_phi_deg": best_window["gain_total_min_phi_deg"],
        "gain_pass": best_window["gain_total_min_dbi"] >= GAIN_TARGET_DBI,
    }
    return metrics, window_rows


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def read_csv(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def row_index(row: dict[str, Any]) -> int:
    try:
        return int(float(row.get("candidate_index", 999999)))
    except (TypeError, ValueError):
        return 999999


def bool_value(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y", "达标"}
    return bool(value)


def rank_key(row: dict[str, Any]) -> tuple[int, float, float]:
    s11_ok = bool_value(row.get("s11_pass"))
    gain_ok = bool_value(row.get("gain_pass"))
    s11_worst = float(row["s11_worst_db"])
    gain_min = float(row["best_270deg_gain_total_min_dbi"])
    if s11_ok and gain_ok:
        tier = 3
    elif gain_ok:
        tier = 2
    elif s11_ok:
        tier = 1
    else:
        tier = 0
    return (tier, -s11_worst, gain_min)


def evaluate(candidate: BoardEdgeCandidate, cores: int, tasks: int, reuse_existing: bool) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    start = time.time()
    paths = project_paths(candidate)
    exported = existing_exports(candidate)
    required = [Path(paths["project"]), Path(paths["params"]), exported["s"], exported["ff"]]
    if not reuse_existing or not all(path.exists() for path in required):
        paths = build_project(candidate, analyze=True, cores=cores, tasks=tasks)
        exported = native_export(candidate, paths)
    s_metrics = parse_s_csv(exported["s"])
    gain_metrics, windows = window_metrics(parse_ff_csv(exported["ff"]))
    row = {
        "candidate": candidate.name,
        "rationale": candidate.rationale,
        "elapsed_s": time.time() - start,
        "project": str(paths["project"]),
        "params_json": str(paths["params"]),
        "native_export_log": str(exported["log"]),
        **params_for(candidate),
        **s_metrics,
        **gain_metrics,
    }
    row["pass"] = row["s11_pass"] and row["gain_pass"]
    for item in windows:
        item["candidate"] = candidate.name
    return row, windows


def write_report(summary_rows: list[dict[str, Any]], best: dict[str, Any]) -> None:
    sorted_rows = sorted(summary_rows, key=row_index)
    s11_best = min(sorted_rows, key=lambda row: float(row["s11_worst_db"]))
    gain_best = max(sorted_rows, key=lambda row: float(row["best_270deg_gain_total_min_dbi"]))
    both_pass = [row for row in sorted_rows if bool_value(row.get("pass"))]
    lines = [
        "# D44 真正板边低仰角单元验证报告",
        "",
        "## 目标",
        "",
        f"- 结构方向：真实板边馈电 IFA/PIFA/单极子低仰角覆盖单元，P1L 为唯一激励源，A/B 馈点作为 50 ohm // 0.08 pF 终端负载背景。",
        f"- 阵元位置：P1 元素中心按 `element_spacing_mm=17.0` 放到 D44 圆板边缘附近，属于后续可校准的物理分离低仰角单元。",
        f"- S11 目标：`S11 <= {RETURN_TARGET_DB:.1f} dB`。",
        f"- 增益目标：Theta `{THETA_MIN_DEG:.0f}..{THETA_MAX_DEG:.0f} deg`，最佳连续 `{AZIMUTH_WINDOW_DEG:.0f} deg` 方位窗口内 `GainTotal >= {GAIN_TARGET_DBI:.1f} dBi`。",
        "",
        "## 当前结果",
        "",
        f"- 综合最佳：`#{best.get('candidate_index', 'N/A')} {best['candidate']}`。",
        f"- S11：`{fmt(best['s11_worst_db'])} dB`，{'达标' if bool_value(best.get('s11_pass')) else '未达标'}。",
        f"- 最佳 270 度窗口 GainTotal 最小值：`{fmt(best['best_270deg_gain_total_min_dbi'])} dBi`，{'达标' if bool_value(best.get('gain_pass')) else '未达标'}。",
        f"- 最差点：Theta `{fmt(best['best_270deg_gain_total_min_theta_deg'], 0)} deg` / Phi `{fmt(best['best_270deg_gain_total_min_phi_deg'], 0)} deg`。",
        f"- 双指标同时达标候选数：`{len(both_pass)}` / `{len(sorted_rows)}`。",
        "",
        "## 关键对比",
        "",
        f"- S11 最优：`#{s11_best.get('candidate_index', 'N/A')} {s11_best['candidate']}`，S11 `{fmt(s11_best['s11_worst_db'])} dB`，GainTotal min `{fmt(s11_best['best_270deg_gain_total_min_dbi'])} dBi`。",
        f"- 增益最优：`#{gain_best.get('candidate_index', 'N/A')} {gain_best['candidate']}`，GainTotal min `{fmt(gain_best['best_270deg_gain_total_min_dbi'])} dBi`，S11 `{fmt(gain_best['s11_worst_db'])} dB`。",
        "",
        "| # | 候选 | S11 worst dB | Best270 min Gain dBi | All-phi min Gain dBi | 结果 |",
        "|---:|---|---:|---:|---:|---|",
    ]
    for row in sorted_rows:
        ok = bool_value(row.get("pass"))
        lines.append(
            f"| {row.get('candidate_index', '')} | `{row['candidate']}` | {fmt(row['s11_worst_db'])} | "
            f"{fmt(row['best_270deg_gain_total_min_dbi'])} | {fmt(row['all_phi_gain_total_min_dbi'])} | "
            f"{'达标' if ok else '未达标'} |"
        )
    lines.extend(
        [
            "",
            "## 工程判断",
            "",
            "- 本轮从同相位中心厚板 PIFA 切到真实板边 L 端口，验证的是可校准低仰角覆盖单元，而不是继续提高 A/B 贴片低仰角权重。",
            "- 匹配网络候选使用印刷短 stub 或低值离散 L/C 的等效 RLC，属于低成本量产可接受路径；若候选达标，后续需把理想 RLC 替换为 0201/0402 器件或可制造微带 stub 后复核。",
            "- 若仍未达标，下一轮优先围绕板边馈电 IFA 的馈点抽头、顶臂长度、单极子顶加载和 shunt/series 匹配组合继续细扫。",
            "",
            "## 输出文件",
            "",
            f"- 汇总 CSV：`{SUMMARY_CSV}`",
            f"- 方位窗口 CSV：`{WINDOW_CSV}`",
            f"- 指标 JSON：`{METRICS_JSON}`",
            f"- 当前最佳 AEDT：`{best.get('project', '')}`",
        ]
    )
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_report(summary_rows: list[dict[str, Any]], best: dict[str, Any]) -> None:
    sorted_rows = sorted(summary_rows, key=row_index)
    s11_best = min(sorted_rows, key=lambda row: float(row["s11_worst_db"]))
    gain_best = max(sorted_rows, key=lambda row: float(row["best_270deg_gain_total_min_dbi"]))
    both_pass = [row for row in sorted_rows if bool_value(row.get("pass"))]
    lines = [
        "# D44 真正板边低仰角单元验证报告",
        "",
        "## 目标",
        "",
        "- 结构方向: 真正板边馈电 IFA/PIFA 低仰角覆盖单元, P1L 为唯一激励源, A/B 馈点作为 50 ohm // 0.08 pF 终端负载背景。",
        "- 阵元位置: P1 单元中心向 D44 圆板边缘推进, 属于后续可校准的物理分离低仰角单元。",
        f"- S11 目标: `S11 <= {RETURN_TARGET_DB:.1f} dB`。",
        f"- 增益目标: Theta `{THETA_MIN_DEG:.0f}..{THETA_MAX_DEG:.0f} deg`, 最佳连续 `{AZIMUTH_WINDOW_DEG:.0f} deg` 方位窗口内 `GainTotal >= {GAIN_TARGET_DBI:.1f} dBi`。",
        "",
        "## 当前结果",
        "",
        f"- 综合最佳: `#{best.get('candidate_index', 'N/A')} {best['candidate']}`。",
        f"- S11: `{fmt(best['s11_worst_db'])} dB`, {'达标' if bool_value(best.get('s11_pass')) else '未达标'}。",
        f"- 最佳 270 deg 窗口 GainTotal 最小值: `{fmt(best['best_270deg_gain_total_min_dbi'])} dBi`, {'达标' if bool_value(best.get('gain_pass')) else '未达标'}。",
        f"- 最差点: Theta `{fmt(best['best_270deg_gain_total_min_theta_deg'], 0)} deg` / Phi `{fmt(best['best_270deg_gain_total_min_phi_deg'], 0)} deg`。",
        f"- 双指标同时达标候选数: `{len(both_pass)}` / `{len(sorted_rows)}`。",
        "",
        "## 关键对比",
        "",
        f"- S11 最优: `#{s11_best.get('candidate_index', 'N/A')} {s11_best['candidate']}`, S11 `{fmt(s11_best['s11_worst_db'])} dB`, GainTotal min `{fmt(s11_best['best_270deg_gain_total_min_dbi'])} dBi`。",
        f"- 增益最优: `#{gain_best.get('candidate_index', 'N/A')} {gain_best['candidate']}`, GainTotal min `{fmt(gain_best['best_270deg_gain_total_min_dbi'])} dBi`, S11 `{fmt(gain_best['s11_worst_db'])} dB`。",
        "- 无耗 L/C 匹配在当前 3D 近场模型中停在约 -8 dB S11, 但短折臂偏置几何给出了足够大的低仰角增益余量。",
        "- 达标方案使用高阻值 shunt R 与 L/C 组成离散阻尼匹配, 属于低成本 0201/0402 器件可实现路径, 后续量产版需要把 R/L/C 的封装寄生纳入 EM-circuit 联合复核。",
        "",
        "| # | 候选 | S11 worst dB | Best270 min Gain dBi | All-phi min Gain dBi | 结果 |",
        "|---:|---|---:|---:|---:|---|",
    ]
    for row in sorted_rows:
        ok = bool_value(row.get("pass"))
        lines.append(
            f"| {row.get('candidate_index', '')} | `{row['candidate']}` | {fmt(row['s11_worst_db'])} | "
            f"{fmt(row['best_270deg_gain_total_min_dbi'])} | {fmt(row['all_phi_gain_total_min_dbi'])} | "
            f"{'达标' if ok else '未达标'} |"
        )
    lines.extend(
        [
            "",
            "## 工程判断",
            "",
            "- 本轮从同相位中心厚板 PIFA 切到真实板边 L 端口, 验证对象是可校准的低仰角覆盖单元, 不是继续硬拧 A/B 贴片低仰角权重。",
            "- 最关键的几何收益来自短折叠板边寄生臂的负向偏置: 它把 Best270 增益从原始 #15 的 -4.802 dBi 提升到 #35 的 -2.286 dBi。",
            "- 纯无耗 L/C 匹配未完全闭合 S11, 最终采用高阻值阻尼匹配后, #53/#54/#55 均同时满足 S11 与低仰角增益目标。",
            "- 当前可作为单阵元达标基准; 下一步若进入量产验证, 建议对 680 ohm shunt R、2.0 nH shunt L、0.142 pF series C 的器件 Q 值、焊盘、过孔和封装寄生做 EM-circuit 联合复核。",
            "",
            "## 输出文件",
            "",
            f"- 汇总 CSV: `{SUMMARY_CSV}`",
            f"- 方位窗口 CSV: `{WINDOW_CSV}`",
            f"- 指标 JSON: `{METRICS_JSON}`",
            f"- 当前最佳 AEDT: `{best.get('project', '')}`",
        ]
    )
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_report(summary_rows: list[dict[str, Any]], best: dict[str, Any]) -> None:
    sorted_rows = sorted(summary_rows, key=row_index)
    s11_best = min(sorted_rows, key=lambda row: float(row["s11_worst_db"]))
    gain_best = max(sorted_rows, key=lambda row: float(row["best_270deg_gain_total_min_dbi"]))
    both_pass = [row for row in sorted_rows if bool_value(row.get("pass"))]
    by_index = {str(row.get("candidate_index", "")): row for row in sorted_rows}

    def row_line(index: str, label: str) -> str:
        row = by_index.get(index)
        if not row:
            return f"- {label}: 未运行。"
        status = "达标" if bool_value(row.get("pass")) else "未达标"
        return (
            f"- {label}: `#{index} {row['candidate']}`, S11 `{fmt(row['s11_worst_db'])} dB`, "
            f"Best270 GainTotal min `{fmt(row['best_270deg_gain_total_min_dbi'])} dBi`, {status}。"
        )

    lines = [
        "# D44 真正板边低仰角单元验证报告",
        "",
        "## 目标",
        "",
        "- 结构方向: 真正板边馈电 IFA/PIFA 低仰角覆盖单元, P1L 为唯一激励源, A/B 馈点作为 50 ohm // 0.08 pF 终端负载背景。",
        "- 加工转换: 对比实心厚板侧壁、低介电厚载体、侧壁平面 IFA, 以及保留原空气支撑电流路径的边镀立墙/立式载体方案。",
        f"- S11 目标: `S11 <= {RETURN_TARGET_DB:.1f} dB`。",
        f"- 增益目标: Theta `{THETA_MIN_DEG:.0f}..{THETA_MAX_DEG:.0f} deg`, 最佳连续 `{AZIMUTH_WINDOW_DEG:.0f} deg` 方位窗口内 `GainTotal >= {GAIN_TARGET_DBI:.1f} dBi`。",
        "",
        "## 当前结果",
        "",
        f"- 综合最佳: `#{best.get('candidate_index', 'N/A')} {best['candidate']}`。",
        f"- S11: `{fmt(best['s11_worst_db'])} dB`, {'达标' if bool_value(best.get('s11_pass')) else '未达标'}。",
        f"- 最佳 270 deg 窗口 GainTotal 最小值: `{fmt(best['best_270deg_gain_total_min_dbi'])} dBi`, {'达标' if bool_value(best.get('gain_pass')) else '未达标'}。",
        f"- 最差点: Theta `{fmt(best['best_270deg_gain_total_min_theta_deg'], 0)} deg` / Phi `{fmt(best['best_270deg_gain_total_min_phi_deg'], 0)} deg`。",
        f"- 双指标同时达标候选数: `{len(both_pass)}` / `{len(sorted_rows)}`。",
        "",
        "## 板边侧壁金属化转换结论",
        "",
        row_line("56", "实心 7.6 mm RO4350B 厚板侧壁 PIFA"),
        row_line("60", "低介电厚载体/泡棉等效侧壁 PIFA"),
        row_line("62", "主动 IFA 完全旋到侧壁平面并保留折叠寄生臂"),
        row_line("63", "只保留主动侧壁平面 IFA, 去掉折叠寄生臂"),
        row_line("64", "边镀立墙/立式载体实现原达标电流路径"),
        "",
        "- 工程判断: 不能把当前达标结构简单改成实心厚板顶层 PIFA 或完全侧壁平面 IFA; 这些版本低仰角增益明显不足。",
        "- 可制造达标路径是 #64: 保留 #53 的空气支撑竖向/折叠电流路径, 将竖直段做成板边镀铜、castellated 立墙、过孔墙加侧边铜, 或低成本金属化立式载体。",
        "- 这不是普通平面微带贴片; 量产图纸需要把 6.3 mm 主 IFA 高度、5.9 mm 短折叠寄生臂高度、0.142 pF 串联 C、2.0 nH // 680 ohm 并联阻尼匹配一起定义。",
        "",
        "## 关键对比",
        "",
        f"- S11 最优: `#{s11_best.get('candidate_index', 'N/A')} {s11_best['candidate']}`, S11 `{fmt(s11_best['s11_worst_db'])} dB`, GainTotal min `{fmt(s11_best['best_270deg_gain_total_min_dbi'])} dBi`。",
        f"- 增益最优: `#{gain_best.get('candidate_index', 'N/A')} {gain_best['candidate']}`, GainTotal min `{fmt(gain_best['best_270deg_gain_total_min_dbi'])} dBi`, S11 `{fmt(gain_best['s11_worst_db'])} dB`。",
        "- 纯无耗 L/C 匹配在当前 3D 近场模型中停在约 -8 dB S11; 最终达标方案使用高阻值 shunt R 与 L/C 组成离散阻尼匹配。",
        "",
        "| # | 候选 | S11 worst dB | Best270 min Gain dBi | All-phi min Gain dBi | 结果 |",
        "|---:|---|---:|---:|---:|---|",
    ]
    for row in sorted_rows:
        ok = bool_value(row.get("pass"))
        lines.append(
            f"| {row.get('candidate_index', '')} | `{row['candidate']}` | {fmt(row['s11_worst_db'])} | "
            f"{fmt(row['best_270deg_gain_total_min_dbi'])} | {fmt(row['all_phi_gain_total_min_dbi'])} | "
            f"{'达标' if ok else '未达标'} |"
        )
    lines.extend(
        [
            "",
            "## 输出文件",
            "",
            f"- 汇总 CSV: `{SUMMARY_CSV}`",
            f"- 方位窗口 CSV: `{WINDOW_CSV}`",
            f"- 指标 JSON: `{METRICS_JSON}`",
            f"- 当前最佳 AEDT: `{best.get('project', '')}`",
        ]
    )
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run(candidate_indices: list[int], cores: int, tasks: int, reuse_existing: bool, resume: bool) -> dict[str, Any]:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    pool = candidates()
    selected = candidate_indices or list(range(1, len(pool) + 1))
    selected_set = {str(index) for index in selected}
    if resume:
        summary_rows = read_csv(SUMMARY_CSV)
        window_rows = read_csv(WINDOW_CSV)
    else:
        summary_rows = [row for row in read_csv(SUMMARY_CSV) if str(row.get("candidate_index", "")) not in selected_set]
        window_rows = [row for row in read_csv(WINDOW_CSV) if str(row.get("candidate_index", "")) not in selected_set]
    completed = {str(row.get("candidate_index", "")) for row in summary_rows} if resume else set()
    for index in selected:
        if index < 1 or index > len(pool):
            raise ValueError(f"candidate index must be 1..{len(pool)}")
        if resume and str(index) in completed:
            print(f"Stage: reuse completed candidate {index}", flush=True)
            continue
        candidate = pool[index - 1]
        print(f"=== Board-edge candidate {index}: {candidate.name} ===", flush=True)
        row, windows = evaluate(candidate, cores=cores, tasks=tasks, reuse_existing=reuse_existing)
        row["candidate_index"] = index
        for item in windows:
            item["candidate_index"] = index
        summary_rows.append(row)
        window_rows.extend(windows)
        write_csv(SUMMARY_CSV, sorted(summary_rows, key=row_index))
        write_csv(WINDOW_CSV, sorted(window_rows, key=lambda row: (row_index(row), float(row.get("window_start_phi_deg", 0.0)))))
    summary_rows = sorted(summary_rows, key=row_index)
    window_rows = sorted(window_rows, key=lambda row: (row_index(row), float(row.get("window_start_phi_deg", 0.0))))
    best = max(summary_rows, key=rank_key)
    payload = {
        "target": {
            "s11_db_max": RETURN_TARGET_DB,
            "theta_deg": [THETA_MIN_DEG, THETA_MAX_DEG],
            "azimuth_window_deg": AZIMUTH_WINDOW_DEG,
            "gain_total_min_dbi": GAIN_TARGET_DBI,
        },
        "best_candidate": best,
        "summary_csv": str(SUMMARY_CSV),
        "window_csv": str(WINDOW_CSV),
        "report_md": str(REPORT_MD),
        "rows": summary_rows,
    }
    write_csv(SUMMARY_CSV, summary_rows)
    write_csv(WINDOW_CSV, window_rows)
    METRICS_JSON.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    write_report(summary_rows, best)
    print(json.dumps({"report": str(REPORT_MD), "rows": len(summary_rows), "best": best["candidate"]}, indent=2, ensure_ascii=False), flush=True)
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate-index", action="append", type=int, default=[])
    parser.add_argument("--cores", type=int, default=8)
    parser.add_argument("--tasks", type=int, default=8)
    parser.add_argument("--reuse-existing", action="store_true")
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    run(args.candidate_index, cores=args.cores, tasks=args.tasks, reuse_existing=args.reuse_existing, resume=args.resume)


if __name__ == "__main__":
    main()
