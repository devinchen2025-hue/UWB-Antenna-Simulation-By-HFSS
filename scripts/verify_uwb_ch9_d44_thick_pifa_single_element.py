from __future__ import annotations

import argparse
import csv
import json
import math
import os
import subprocess
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import build_uwb_ch9_hfss_d44_topology as builder


ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = ROOT / "reports_d44_thick_pifa_single_element"
STEM = "UWB_CH9_D44_THICK_PIFA_SINGLE_ELEMENT"
DESIGN_NAME = "SingleElement_D44_ThickPIFA_Cavity"
SOLUTION = "Setup_CH9 : Sweep_CH9"
SPHERE = "Upper_Hemisphere_5deg"
NATIVE_EXPORT_SCRIPT = ROOT / "scripts" / "aedt_export_ch9_native_reports.py"

THETA_MIN_DEG = 45.0
THETA_MAX_DEG = 90.0
AZIMUTH_WINDOW_DEG = 270.0
GAIN_TARGET_DBI = -5.0
RETURN_TARGET_DB = -10.0

SUMMARY_CSV = REPORT_DIR / f"{STEM}_summary.csv"
WINDOW_CSV = REPORT_DIR / f"{STEM}_azimuth_window_summary.csv"
METRICS_JSON = REPORT_DIR / f"{STEM}_metrics.json"
REPORT_MD = REPORT_DIR / f"{STEM}_report.md"


@dataclass(frozen=True)
class ThickPifaCandidate:
    name: str
    rationale: str
    substrate_h_mm: float = 5.0
    top_length_mm: float = 8.8
    top_width_mm: float = 8.0
    short_wall_width_mm: float = 2.4
    side_fence_length_mm: float = 4.2
    side_fence_start_from_short_mm: float = 0.0
    side_fence_enabled: bool = True
    feed_from_short_mm: float = 1.25
    feed_v_mm: float = 0.0
    feed_pad_radius_mm: float = 0.30
    port_width_mm: float = 0.55
    open_lip_height_mm: float = 0.0
    open_lip_width_mm: float = 0.0
    open_edge_coupler_length_mm: float = 0.0
    open_edge_coupler_height_mm: float = 0.0
    top_slot_start_from_short_mm: float = 0.0
    top_slot_length_mm: float = 0.0
    top_slot_width_mm: float = 0.0
    top_slot_v_offset_mm: float = 0.0
    edge_slot_start_from_short_mm: float = 0.0
    edge_slot_length_mm: float = 0.0
    edge_slot_depth_mm: float = 0.0
    match_series_cap_pf: float = 0.0
    match_series_ind_nh: float = 0.0
    match_shunt_cap_pf: float = 0.0
    match_shunt_ind_nh: float = 0.0
    match_shunt_on_load_side: bool = False
    match_gap_mm: float = 0.12
    match_island_size_mm: float = 0.70
    match_series_width_mm: float = 0.34
    ground_radius_mm: float = 21.4
    total_height_limit_mm: float = 8.0
    epsr: float = 3.48
    tan_delta: float = 0.0037


def candidates() -> list[ThickPifaCandidate]:
    return [
        ThickPifaCandidate(
            name="h5p0_l8p8_w8p0_feed1p25",
            rationale="5.0 mm thick-board baseline PIFA: top plate, short wall, and two short side fences for a quasi-cavity low-elevation mode.",
        ),
        ThickPifaCandidate(
            name="h5p0_l9p6_w8p2_feed1p45",
            rationale="Lengthen the top arm and move the feed farther from the short wall to lower the resonant point toward CH9.",
            top_length_mm=9.6,
            top_width_mm=8.2,
            feed_from_short_mm=1.45,
            side_fence_length_mm=4.6,
        ),
        ThickPifaCandidate(
            name="h5p8_l8p6_w8p0_feed1p20",
            rationale="Spend more PCB thickness to strengthen vertical current while keeping the same compact footprint.",
            substrate_h_mm=5.8,
            top_length_mm=8.6,
            feed_from_short_mm=1.20,
            side_fence_length_mm=4.0,
        ),
        ThickPifaCandidate(
            name="h4p5_l10p4_w8p6_feed1p65",
            rationale="Use a longer, lower-profile PIFA to test whether electrical length rather than height dominates the match.",
            substrate_h_mm=4.5,
            top_length_mm=10.4,
            top_width_mm=8.6,
            feed_from_short_mm=1.65,
            side_fence_length_mm=5.0,
        ),
        ThickPifaCandidate(
            name="h5p0_l8p8_w9p6_feed1p10_wide",
            rationale="Widen the cavity aperture to improve 270-degree azimuth coverage uniformity.",
            top_width_mm=9.6,
            short_wall_width_mm=3.0,
            feed_from_short_mm=1.10,
            side_fence_length_mm=4.2,
        ),
        ThickPifaCandidate(
            name="h5p0_l8p8_w8p0_feed1p25_lip0p8",
            rationale="Add a shallow open-edge vertical lip to couple more field into the low-elevation horizon without using a separate L monopole.",
            open_lip_height_mm=0.8,
            open_lip_width_mm=1.2,
        ),
        ThickPifaCandidate(
            name="h5p0_l8p8_w8p0_feed2p20",
            rationale="Move the feed farther from the short wall to raise the PIFA input resistance while preserving the baseline horizon pattern.",
            feed_from_short_mm=2.20,
        ),
        ThickPifaCandidate(
            name="h5p0_l8p8_w8p0_feed3p00",
            rationale="Mid-arm feed location intended to bracket a 50 ohm point on the same thick-board PIFA mode.",
            feed_from_short_mm=3.00,
        ),
        ThickPifaCandidate(
            name="h5p0_l8p8_w8p0_feed3p80",
            rationale="Feed close to the open half of the top plate to test the high-impedance side of the PIFA feed sweep.",
            feed_from_short_mm=3.80,
        ),
        ThickPifaCandidate(
            name="h5p0_l9p6_w8p2_feed3p20",
            rationale="Combine the longer top arm with a mid-arm feed for a lower-resonance, higher-input-resistance point.",
            top_length_mm=9.6,
            top_width_mm=8.2,
            feed_from_short_mm=3.20,
            side_fence_length_mm=4.6,
        ),
        ThickPifaCandidate(
            name="h5p0_l8p8_w8p0_feed3p80_c0p093_l0p64",
            rationale="Add a lossless two-element L-match estimated from candidate 9 impedance: series C plus shunt L on a top-layer feed island.",
            feed_from_short_mm=3.80,
            match_series_cap_pf=0.093,
            match_shunt_ind_nh=0.64,
        ),
        ThickPifaCandidate(
            name="h5p0_l8p8_w8p0_feed3p80_c0p085_l0p70",
            rationale="Slightly lower series capacitance and higher shunt inductance around the calculated L-match point.",
            feed_from_short_mm=3.80,
            match_series_cap_pf=0.085,
            match_shunt_ind_nh=0.70,
        ),
        ThickPifaCandidate(
            name="h5p0_l8p8_w8p0_feed3p80_c0p105_l0p58",
            rationale="Slightly higher series capacitance and lower shunt inductance around the calculated L-match point.",
            feed_from_short_mm=3.80,
            match_series_cap_pf=0.105,
            match_shunt_ind_nh=0.58,
        ),
        ThickPifaCandidate(
            name="h5p0_l8p8_w8p0_feed3p80_c0p45_l0p24",
            rationale="Retune the feed-island version after measured input moved to a very low-resistance point.",
            feed_from_short_mm=3.80,
            match_series_cap_pf=0.45,
            match_shunt_ind_nh=0.24,
        ),
        ThickPifaCandidate(
            name="h5p0_l8p8_w8p0_feed3p80_c0p65_l0p20",
            rationale="Use the approximate L-match for the feed-island input of about 2+j20 ohm at 8 GHz.",
            feed_from_short_mm=3.80,
            match_series_cap_pf=0.65,
            match_shunt_ind_nh=0.20,
        ),
        ThickPifaCandidate(
            name="h5p0_l8p8_w8p0_feed3p80_c0p90_l0p16",
            rationale="Push the series capacitance higher and shunt inductance lower to bracket the strong-match side.",
            feed_from_short_mm=3.80,
            match_series_cap_pf=0.90,
            match_shunt_ind_nh=0.16,
        ),
        ThickPifaCandidate(
            name="h5p0_l8p8_w8p0_feed5p50",
            rationale="Move the direct coax-style feed well beyond the mid-arm point toward the open edge to continue the observed S11 trend.",
            feed_from_short_mm=5.50,
        ),
        ThickPifaCandidate(
            name="h5p0_l8p8_w8p0_feed7p00",
            rationale="Near-open-edge direct feed intended to raise input resistance without an external matching island.",
            feed_from_short_mm=7.00,
        ),
        ThickPifaCandidate(
            name="h5p0_l8p8_w8p0_feed8p00",
            rationale="Aggressive near-open-edge feed location to bracket the high-resistance side of the compact PIFA mode.",
            feed_from_short_mm=8.00,
        ),
        ThickPifaCandidate(
            name="h5p0_l10p4_w8p6_feed8p80",
            rationale="Longer top plate with near-open-edge feed to combine lower resonance with higher feed resistance.",
            top_length_mm=10.4,
            top_width_mm=8.6,
            feed_from_short_mm=8.80,
            side_fence_length_mm=5.0,
        ),
        ThickPifaCandidate(
            name="h5p8_l8p6_w8p0_feed7p80",
            rationale="Use extra board thickness and a near-open-edge feed to keep horizon gain while probing a higher-resistance feed point.",
            substrate_h_mm=5.8,
            top_length_mm=8.6,
            feed_from_short_mm=7.80,
            side_fence_length_mm=4.0,
        ),
        ThickPifaCandidate(
            name="h5p0_l8p8_w8p0_feed8p40",
            rationale="Move the baseline feed to the practical near-open-edge limit to test whether the S11 trend continues.",
            feed_from_short_mm=8.40,
        ),
        ThickPifaCandidate(
            name="h5p0_l8p8_w8p0_sw4p0_fence6p0_feed8p40",
            rationale="Near-open-edge feed with a wider short wall and longer side fences for stronger cavity current return.",
            short_wall_width_mm=4.0,
            side_fence_length_mm=6.0,
            feed_from_short_mm=8.40,
        ),
        ThickPifaCandidate(
            name="h5p0_l7p8_w8p0_feed7p40",
            rationale="Shorten the top plate while keeping the feed near the open edge to probe the high-frequency side of resonance.",
            top_length_mm=7.8,
            feed_from_short_mm=7.40,
            side_fence_length_mm=3.8,
        ),
        ThickPifaCandidate(
            name="h6p5_l8p4_w8p0_feed7p90",
            rationale="Spend more board thickness and keep a compact near-edge feed to increase vertical current and input resistance.",
            substrate_h_mm=6.5,
            top_length_mm=8.4,
            feed_from_short_mm=7.90,
            side_fence_length_mm=4.0,
        ),
        ThickPifaCandidate(
            name="h5p0_l8p8_w8p0_sw4p0_fence6p0_feed7p80",
            rationale="Retune the best S11 geometry by moving the near-open-edge feed back toward the short wall to reduce the high input resistance.",
            short_wall_width_mm=4.0,
            side_fence_length_mm=6.0,
            feed_from_short_mm=7.80,
        ),
        ThickPifaCandidate(
            name="h5p0_l8p8_w8p0_sw4p0_fence6p0_feed8p00",
            rationale="Fine feed sweep around the best S11 geometry to bracket the 50 ohm point.",
            short_wall_width_mm=4.0,
            side_fence_length_mm=6.0,
            feed_from_short_mm=8.00,
        ),
        ThickPifaCandidate(
            name="h5p0_l8p8_w8p0_sw4p0_fence6p0_feed8p20",
            rationale="Fine feed sweep between the 8.0 mm and 8.4 mm near-edge feed points.",
            short_wall_width_mm=4.0,
            side_fence_length_mm=6.0,
            feed_from_short_mm=8.20,
        ),
        ThickPifaCandidate(
            name="h5p0_l8p8_w8p0_sw4p0_fence6p0_feed8p48",
            rationale="Probe the practical open-edge feed limit of the best S11 geometry.",
            short_wall_width_mm=4.0,
            side_fence_length_mm=6.0,
            feed_from_short_mm=8.48,
        ),
        ThickPifaCandidate(
            name="h5p0_l9p2_w8p4_sw4p0_fence6p0_feed8p80",
            rationale="Lengthen and slightly widen the top plate to add capacitive loading while keeping the strong return wall.",
            top_length_mm=9.2,
            top_width_mm=8.4,
            short_wall_width_mm=4.0,
            side_fence_length_mm=6.0,
            feed_from_short_mm=8.80,
        ),
        ThickPifaCandidate(
            name="h5p0_l8p8_w10p0_sw4p0_fence6p0_feed8p40",
            rationale="Widen the top plate to increase edge capacitance and reduce the inductive input reactance.",
            top_width_mm=10.0,
            short_wall_width_mm=4.0,
            side_fence_length_mm=6.0,
            feed_from_short_mm=8.40,
        ),
        ThickPifaCandidate(
            name="h4p5_l8p8_w8p0_sw4p0_fence6p0_feed8p40",
            rationale="Lower the board height around the best S11 geometry to test whether reduced vertical inductance improves the match.",
            substrate_h_mm=4.5,
            short_wall_width_mm=4.0,
            side_fence_length_mm=6.0,
            feed_from_short_mm=8.40,
        ),
        ThickPifaCandidate(
            name="h5p0_l8p8_w8p0_sw5p5_fence7p0_feed8p20",
            rationale="Use a stronger short/side-wall return path with the feed pulled back slightly from the open edge.",
            short_wall_width_mm=5.5,
            side_fence_length_mm=7.0,
            feed_from_short_mm=8.20,
        ),
        ThickPifaCandidate(
            name="h5p0_l8p8_w8p0_sw4p0_fence6p0_feed8p40_lip1p0",
            rationale="Add an open-edge lip to the best S11 geometry for extra capacitive loading at the high-impedance edge.",
            short_wall_width_mm=4.0,
            side_fence_length_mm=6.0,
            feed_from_short_mm=8.40,
            open_lip_height_mm=1.0,
            open_lip_width_mm=1.6,
        ),
        ThickPifaCandidate(
            name="h4p0_l8p8_w8p0_sw4p0_fence6p0_feed8p40",
            rationale="Continue the height reduction trend from the h=4.5 mm best candidate to reduce inductive reactance.",
            substrate_h_mm=4.0,
            short_wall_width_mm=4.0,
            side_fence_length_mm=6.0,
            feed_from_short_mm=8.40,
        ),
        ThickPifaCandidate(
            name="h3p5_l8p8_w8p0_sw4p0_fence6p0_feed8p40",
            rationale="Lower-profile limit check for the same short-wall PIFA mode.",
            substrate_h_mm=3.5,
            short_wall_width_mm=4.0,
            side_fence_length_mm=6.0,
            feed_from_short_mm=8.40,
        ),
        ThickPifaCandidate(
            name="h4p5_l8p8_w8p0_sw4p0_fence6p0_feed8p00",
            rationale="Pull the h=4.5 mm best feed point back toward the short wall to reduce input resistance.",
            substrate_h_mm=4.5,
            short_wall_width_mm=4.0,
            side_fence_length_mm=6.0,
            feed_from_short_mm=8.00,
        ),
        ThickPifaCandidate(
            name="h4p5_l8p8_w8p0_sw4p0_fence6p0_feed8p20",
            rationale="Midpoint feed correction around the h=4.5 mm best candidate.",
            substrate_h_mm=4.5,
            short_wall_width_mm=4.0,
            side_fence_length_mm=6.0,
            feed_from_short_mm=8.20,
        ),
        ThickPifaCandidate(
            name="h4p5_l8p8_w8p0_sw4p0_fence6p0_feed8p48",
            rationale="Open-edge limit check around the h=4.5 mm best candidate.",
            substrate_h_mm=4.5,
            short_wall_width_mm=4.0,
            side_fence_length_mm=6.0,
            feed_from_short_mm=8.48,
        ),
        ThickPifaCandidate(
            name="h4p0_l8p8_w8p0_sw4p0_fence6p0_feed8p20",
            rationale="Combine lower height with a feed pull-back to target lower resistance and lower reactance together.",
            substrate_h_mm=4.0,
            short_wall_width_mm=4.0,
            side_fence_length_mm=6.0,
            feed_from_short_mm=8.20,
        ),
        ThickPifaCandidate(
            name="h4p0_l8p8_w10p0_sw4p0_fence6p0_feed8p40",
            rationale="Lower height plus wider top plate for extra capacitance at the open edge.",
            substrate_h_mm=4.0,
            top_width_mm=10.0,
            short_wall_width_mm=4.0,
            side_fence_length_mm=6.0,
            feed_from_short_mm=8.40,
        ),
        ThickPifaCandidate(
            name="h4p5_l8p8_w8p0_sw5p5_fence7p0_feed8p20",
            rationale="h=4.5 mm with stronger return wall and slightly pulled-back feed.",
            substrate_h_mm=4.5,
            short_wall_width_mm=5.5,
            side_fence_length_mm=7.0,
            feed_from_short_mm=8.20,
        ),
        ThickPifaCandidate(
            name="h4p5_l9p2_w8p4_sw4p0_fence6p0_feed8p80",
            rationale="h=4.5 mm with longer/wider top loading to reduce reactance while preserving the near-edge feed.",
            substrate_h_mm=4.5,
            top_length_mm=9.2,
            top_width_mm=8.4,
            short_wall_width_mm=4.0,
            side_fence_length_mm=6.0,
            feed_from_short_mm=8.80,
        ),
        ThickPifaCandidate(
            name="h6p5_l8p4_w8p0_sw4p0_fence6p0_feed7p90_lowcost",
            rationale="Low-cost PCB edge/via-wall variant: keep the high-gain h=6.5 mm PIFA height and add stronger short/side walls to pull S11 toward 50 ohm without external metal parts.",
            substrate_h_mm=6.5,
            top_length_mm=8.4,
            top_width_mm=8.0,
            short_wall_width_mm=4.0,
            side_fence_length_mm=6.0,
            feed_from_short_mm=7.90,
        ),
        ThickPifaCandidate(
            name="h6p5_l8p4_w8p0_sw4p0_fence6p0_feed8p05_lowcost",
            rationale="Feed retune around the low-cost h=6.5 mm reinforced-wall PIFA to bracket the match near the open edge.",
            substrate_h_mm=6.5,
            top_length_mm=8.4,
            top_width_mm=8.0,
            short_wall_width_mm=4.0,
            side_fence_length_mm=6.0,
            feed_from_short_mm=8.05,
        ),
        ThickPifaCandidate(
            name="h6p5_l9p2_w8p4_sw3p5_fence5p5_feed8p50_lowcost",
            rationale="Slightly longer capacitive top plate on the low-cost h=6.5 mm PIFA to improve match while preserving vertical low-elevation current.",
            substrate_h_mm=6.5,
            top_length_mm=9.2,
            top_width_mm=8.4,
            short_wall_width_mm=3.5,
            side_fence_length_mm=5.5,
            feed_from_short_mm=8.50,
        ),
        ThickPifaCandidate(
            name="h6p5_l8p4_w9p6_feed7p90_lowcost",
            rationale="Widen the h=6.5 mm high-gain PIFA aperture with standard PCB copper to reduce the corrected 270-degree gain hole.",
            substrate_h_mm=6.5,
            top_length_mm=8.4,
            top_width_mm=9.6,
            feed_from_short_mm=7.90,
            side_fence_length_mm=4.0,
        ),
        ThickPifaCandidate(
            name="h7p2_l8p2_w8p0_feed7p80_lim10_lowcost",
            rationale="Use a 7.2 mm plated-edge/via-wall PIFA inside a 10 mm envelope to test the height lever without a separate stamped metal radiator.",
            substrate_h_mm=7.2,
            top_length_mm=8.2,
            top_width_mm=8.0,
            feed_from_short_mm=7.80,
            side_fence_length_mm=4.0,
            total_height_limit_mm=10.0,
        ),
        ThickPifaCandidate(
            name="h7p2_l8p2_w8p0_sw4p0_fence6p0_feed7p75_lim10_lowcost",
            rationale="Reinforced-wall version of the 7.2 mm low-cost PIFA, keeping fabrication to copper, via wall, and edge plating.",
            substrate_h_mm=7.2,
            top_length_mm=8.2,
            top_width_mm=8.0,
            short_wall_width_mm=4.0,
            side_fence_length_mm=6.0,
            feed_from_short_mm=7.75,
            total_height_limit_mm=10.0,
        ),
        ThickPifaCandidate(
            name="h8p0_l8p0_w8p0_feed7p60_lim10_lowcost",
            rationale="Upper low-cost envelope check: 8.0 mm thick-board/edge-plated PIFA with no discrete vertical metal arm.",
            substrate_h_mm=8.0,
            top_length_mm=8.0,
            top_width_mm=8.0,
            feed_from_short_mm=7.60,
            side_fence_length_mm=4.0,
            total_height_limit_mm=10.0,
        ),
        ThickPifaCandidate(
            name="h8p0_l8p0_w8p0_sw4p0_fence6p0_feed7p55_lim10_lowcost",
            rationale="Reinforced return wall on the 8.0 mm low-cost PIFA to recover S11 while testing maximum PCB-only low-elevation gain.",
            substrate_h_mm=8.0,
            top_length_mm=8.0,
            top_width_mm=8.0,
            short_wall_width_mm=4.0,
            side_fence_length_mm=6.0,
            feed_from_short_mm=7.55,
            total_height_limit_mm=10.0,
        ),
        ThickPifaCandidate(
            name="h8p0_l8p0_w8p0_sw4p0_fence6p0_feed7p55_lim10_lowcost_c0p05",
            rationale="Add a very small series capacitor to the best low-cost 8 mm PIFA to see whether a light PCB matching island can recover S11 without hurting low-angle gain.",
            substrate_h_mm=8.0,
            top_length_mm=8.0,
            top_width_mm=8.0,
            short_wall_width_mm=4.0,
            side_fence_length_mm=6.0,
            feed_from_short_mm=7.55,
            match_series_cap_pf=0.05,
            total_height_limit_mm=10.0,
        ),
        ThickPifaCandidate(
            name="h8p0_l8p0_w8p0_sw4p0_fence6p0_feed7p55_lim10_lowcost_c0p09_l10p7",
            rationale="Derived 8 GHz L-match sweep: slightly smaller series capacitor with the shunt inductor held near the impedance-solved value.",
            substrate_h_mm=8.0,
            top_length_mm=8.0,
            top_width_mm=8.0,
            short_wall_width_mm=4.0,
            side_fence_length_mm=6.0,
            feed_from_short_mm=7.55,
            match_series_cap_pf=0.09,
            match_shunt_ind_nh=10.7,
            total_height_limit_mm=10.0,
        ),
        ThickPifaCandidate(
            name="h8p0_l8p0_w8p0_sw4p0_fence6p0_feed7p55_lim10_lowcost_c0p11_l10p7",
            rationale="Center the low-cost match on the solved 8 GHz series-C/shunt-L point from the exported port impedance.",
            substrate_h_mm=8.0,
            top_length_mm=8.0,
            top_width_mm=8.0,
            short_wall_width_mm=4.0,
            side_fence_length_mm=6.0,
            feed_from_short_mm=7.55,
            match_series_cap_pf=0.11,
            match_shunt_ind_nh=10.7,
            total_height_limit_mm=10.0,
        ),
        ThickPifaCandidate(
            name="h8p0_l8p0_w8p0_sw4p0_fence6p0_feed7p55_lim10_lowcost_c0p13_l10p7",
            rationale="Push the series capacitor slightly higher while keeping the shunt inductor fixed to see whether the 8 GHz match is under- or over-corrected.",
            substrate_h_mm=8.0,
            top_length_mm=8.0,
            top_width_mm=8.0,
            short_wall_width_mm=4.0,
            side_fence_length_mm=6.0,
            feed_from_short_mm=7.55,
            match_series_cap_pf=0.13,
            match_shunt_ind_nh=10.7,
            total_height_limit_mm=10.0,
        ),
        ThickPifaCandidate(
            name="h8p0_l8p0_w8p0_sw4p0_fence6p0_feed7p55_lim10_lowcost_c0p11_l9p0",
            rationale="Hold the series capacitor near the solved point but lower the shunt inductance to bracket the transformed resistance side.",
            substrate_h_mm=8.0,
            top_length_mm=8.0,
            top_width_mm=8.0,
            short_wall_width_mm=4.0,
            side_fence_length_mm=6.0,
            feed_from_short_mm=7.55,
            match_series_cap_pf=0.11,
            match_shunt_ind_nh=9.0,
            total_height_limit_mm=10.0,
        ),
        ThickPifaCandidate(
            name="h8p0_l8p0_w8p0_sw4p0_fence6p0_feed7p55_lim10_lowcost_c0p11_l12p5",
            rationale="Hold the series capacitor near the solved point but raise the shunt inductance to bracket the weaker-coupling side.",
            substrate_h_mm=8.0,
            top_length_mm=8.0,
            top_width_mm=8.0,
            short_wall_width_mm=4.0,
            side_fence_length_mm=6.0,
            feed_from_short_mm=7.55,
            match_series_cap_pf=0.11,
            match_shunt_ind_nh=12.5,
            total_height_limit_mm=10.0,
        ),
        ThickPifaCandidate(
            name="h4p5_l9p2_w8p4_sw4p0_fence6p0_feed8p80_c0p25_l5p6",
            rationale="Low-cost L-match sweep around the candidate-43 impedance: slightly lighter series capacitor with the shunt inductor held near the solved 5.6 nH point.",
            substrate_h_mm=4.5,
            top_length_mm=9.2,
            top_width_mm=8.4,
            short_wall_width_mm=4.0,
            side_fence_length_mm=6.0,
            feed_from_short_mm=8.80,
            match_series_cap_pf=0.25,
            match_shunt_ind_nh=5.6,
        ),
        ThickPifaCandidate(
            name="h4p5_l9p2_w8p4_sw4p0_fence6p0_feed8p80_c0p32_l5p6",
            rationale="Center the low-cost match on the solved candidate-43 8 GHz series-C/shunt-L point from the exported port impedance.",
            substrate_h_mm=4.5,
            top_length_mm=9.2,
            top_width_mm=8.4,
            short_wall_width_mm=4.0,
            side_fence_length_mm=6.0,
            feed_from_short_mm=8.80,
            match_series_cap_pf=0.32,
            match_shunt_ind_nh=5.6,
        ),
        ThickPifaCandidate(
            name="h4p5_l9p2_w8p4_sw4p0_fence6p0_feed8p80_c0p40_l5p6",
            rationale="Push the series capacitor higher while keeping the shunt inductor fixed to see whether the 8 GHz match is under- or over-corrected.",
            substrate_h_mm=4.5,
            top_length_mm=9.2,
            top_width_mm=8.4,
            short_wall_width_mm=4.0,
            side_fence_length_mm=6.0,
            feed_from_short_mm=8.80,
            match_series_cap_pf=0.40,
            match_shunt_ind_nh=5.6,
        ),
        ThickPifaCandidate(
            name="h4p5_l9p2_w8p4_sw4p0_fence6p0_feed8p80_c0p32_l4p7",
            rationale="Hold the series capacitor near the solved point but lower the shunt inductance to bracket the transformed resistance side.",
            substrate_h_mm=4.5,
            top_length_mm=9.2,
            top_width_mm=8.4,
            short_wall_width_mm=4.0,
            side_fence_length_mm=6.0,
            feed_from_short_mm=8.80,
            match_series_cap_pf=0.32,
            match_shunt_ind_nh=4.7,
        ),
        ThickPifaCandidate(
            name="h4p5_l9p2_w8p4_sw4p0_fence6p0_feed8p80_c0p32_l6p6",
            rationale="Hold the series capacitor near the solved point but raise the shunt inductance to bracket the weaker-coupling side.",
            substrate_h_mm=4.5,
            top_length_mm=9.2,
            top_width_mm=8.4,
            short_wall_width_mm=4.0,
            side_fence_length_mm=6.0,
            feed_from_short_mm=8.80,
            match_series_cap_pf=0.32,
            match_shunt_ind_nh=6.6,
        ),
        ThickPifaCandidate(
            name="h8p0_l9p6_w9p6_feed9p10_lim10_lowcost",
            rationale="Increase the 8 mm PIFA top plate in both axes for physical capacitive loading while keeping the low-cost plated-wall construction.",
            substrate_h_mm=8.0,
            top_length_mm=9.6,
            top_width_mm=9.6,
            feed_from_short_mm=9.10,
            side_fence_length_mm=4.8,
            total_height_limit_mm=10.0,
        ),
        ThickPifaCandidate(
            name="h8p0_l9p6_w9p6_sw4p0_fence6p8_feed9p05_lim10_lowcost",
            rationale="Reinforced-return version of the larger 8 mm capacitive top plate to recover S11 without adding stamped metal.",
            substrate_h_mm=8.0,
            top_length_mm=9.6,
            top_width_mm=9.6,
            short_wall_width_mm=4.0,
            side_fence_length_mm=6.8,
            feed_from_short_mm=9.05,
            total_height_limit_mm=10.0,
        ),
        ThickPifaCandidate(
            name="h8p0_l10p8_w10p0_feed10p20_lim10_lowcost",
            rationale="Longer 8 mm top plate to pull the inductive input toward resonance while preserving the vertical low-elevation current path.",
            substrate_h_mm=8.0,
            top_length_mm=10.8,
            top_width_mm=10.0,
            feed_from_short_mm=10.20,
            side_fence_length_mm=5.2,
            total_height_limit_mm=10.0,
        ),
        ThickPifaCandidate(
            name="h8p0_l10p8_w10p0_sw4p0_fence7p2_feed10p15_lim10_lowcost",
            rationale="Stronger short and side plated walls around the longer 8 mm top plate to bracket the S11/gain trade.",
            substrate_h_mm=8.0,
            top_length_mm=10.8,
            top_width_mm=10.0,
            short_wall_width_mm=4.0,
            side_fence_length_mm=7.2,
            feed_from_short_mm=10.15,
            total_height_limit_mm=10.0,
        ),
        ThickPifaCandidate(
            name="h7p2_l10p8_w10p0_sw4p0_fence7p2_feed10p20_lim10_lowcost",
            rationale="Use the same larger capacitive top at 7.2 mm height to improve match while checking whether the low-elevation gain stays above target.",
            substrate_h_mm=7.2,
            top_length_mm=10.8,
            top_width_mm=10.0,
            short_wall_width_mm=4.0,
            side_fence_length_mm=7.2,
            feed_from_short_mm=10.20,
            total_height_limit_mm=10.0,
        ),
        ThickPifaCandidate(
            name="h8p0_l10p0_w11p5_sw5p5_fence7p5_feed9p50_lip1p2_lim10_lowcost",
            rationale="Wide capacitive top plus a plated open-edge lip to reduce the large inductive input reactance with PCB-only features.",
            substrate_h_mm=8.0,
            top_length_mm=10.0,
            top_width_mm=11.5,
            short_wall_width_mm=5.5,
            side_fence_length_mm=7.5,
            feed_from_short_mm=9.50,
            open_lip_height_mm=1.2,
            open_lip_width_mm=4.0,
            total_height_limit_mm=10.0,
        ),
        ThickPifaCandidate(
            name="h8p0_l12p0_w10p0_sw4p0_fence8p0_feed11p30_lim10_lowcost",
            rationale="Upper footprint check for the low-cost thick PIFA: a 12 mm top plate tests whether physical capacitive loading can replace the failed lumped matching island.",
            substrate_h_mm=8.0,
            top_length_mm=12.0,
            top_width_mm=10.0,
            short_wall_width_mm=4.0,
            side_fence_length_mm=8.0,
            feed_from_short_mm=11.30,
            total_height_limit_mm=10.0,
        ),
        ThickPifaCandidate(
            name="h8p0_l9p6_w9p6_sw4p0_fence6p8_feed9p05_lim10_lowcost_match_c0p14_l8p0_loadside",
            rationale="Put the low-cost L-match on the antenna side of the high-gain 8 mm geometry so the shunt branch sees the transformed load instead of the source node.",
            substrate_h_mm=8.0,
            top_length_mm=9.6,
            top_width_mm=9.6,
            short_wall_width_mm=4.0,
            side_fence_length_mm=6.8,
            feed_from_short_mm=9.05,
            match_series_cap_pf=0.14,
            match_shunt_ind_nh=8.0,
            match_shunt_on_load_side=True,
            total_height_limit_mm=10.0,
        ),
        ThickPifaCandidate(
            name="h8p0_l9p6_w9p6_sw4p0_fence6p8_feed9p05_lim10_lowcost_match_l2p9_c0p19_loadside",
            rationale="Test the conjugate load-side high-pass L-match for the same 8 mm geometry, using a modest series inductor and a small shunt capacitor.",
            substrate_h_mm=8.0,
            top_length_mm=9.6,
            top_width_mm=9.6,
            short_wall_width_mm=4.0,
            side_fence_length_mm=6.8,
            feed_from_short_mm=9.05,
            match_series_ind_nh=2.9,
            match_shunt_cap_pf=0.19,
            match_shunt_on_load_side=True,
            total_height_limit_mm=10.0,
        ),
        ThickPifaCandidate(
            name="h8p0_l9p6_w9p6_sw4p0_fence6p8_feed8p40_lim10_lowcost",
            rationale="Pull the high-gain 9.6 mm top plate feed back toward the short wall to lower the input resistance while keeping the plated-wall low-elevation mode.",
            substrate_h_mm=8.0,
            top_length_mm=9.6,
            top_width_mm=9.6,
            short_wall_width_mm=4.0,
            side_fence_length_mm=6.8,
            feed_from_short_mm=8.40,
            total_height_limit_mm=10.0,
        ),
        ThickPifaCandidate(
            name="h8p0_l9p6_w9p6_sw4p0_fence6p8_feed8p60_lim10_lowcost",
            rationale="Mid-point feed sweep on the same high-gain 8 mm PIFA to bracket the 50 ohm crossing without changing the copper outline.",
            substrate_h_mm=8.0,
            top_length_mm=9.6,
            top_width_mm=9.6,
            short_wall_width_mm=4.0,
            side_fence_length_mm=6.8,
            feed_from_short_mm=8.60,
            total_height_limit_mm=10.0,
        ),
        ThickPifaCandidate(
            name="h8p0_l9p6_w9p6_sw4p0_fence6p8_feed8p80_lim10_lowcost",
            rationale="Open-edge side of the same 8 mm high-gain PIFA to see whether a slightly longer feed arm is needed for the impedance match.",
            substrate_h_mm=8.0,
            top_length_mm=9.6,
            top_width_mm=9.6,
            short_wall_width_mm=4.0,
            side_fence_length_mm=6.8,
            feed_from_short_mm=8.80,
            total_height_limit_mm=10.0,
        ),
        ThickPifaCandidate(
            name="h7p2_l9p6_w9p6_sw4p0_fence6p8_feed8p60_lim10_lowcost",
            rationale="Step down the height slightly from the best 8 mm gain geometry and pull the feed a bit back to see whether the higher input resistance can be tamed.",
            substrate_h_mm=7.2,
            top_length_mm=9.6,
            top_width_mm=9.6,
            short_wall_width_mm=4.0,
            side_fence_length_mm=6.8,
            feed_from_short_mm=8.60,
            total_height_limit_mm=10.0,
        ),
        ThickPifaCandidate(
            name="h7p2_l9p6_w9p6_sw4p0_fence6p8_feed8p80_lim10_lowcost",
            rationale="Same 7.2 mm height with a near-open feed point to bracket the trade between low-angle gain and input match.",
            substrate_h_mm=7.2,
            top_length_mm=9.6,
            top_width_mm=9.6,
            short_wall_width_mm=4.0,
            side_fence_length_mm=6.8,
            feed_from_short_mm=8.80,
            total_height_limit_mm=10.0,
        ),
        ThickPifaCandidate(
            name="h7p2_l9p6_w9p6_sw4p0_fence6p8_feed8p80_match_c0p157_l7p3_loadside",
            rationale="Load-side L-match solved from the candidate-76 impedance of about 111+j170 ohm, using series C and shunt L.",
            substrate_h_mm=7.2,
            top_length_mm=9.6,
            top_width_mm=9.6,
            short_wall_width_mm=4.0,
            side_fence_length_mm=6.8,
            feed_from_short_mm=8.80,
            match_series_cap_pf=0.157,
            match_shunt_ind_nh=7.3,
            match_shunt_on_load_side=True,
            total_height_limit_mm=10.0,
        ),
        ThickPifaCandidate(
            name="h7p2_l9p6_w9p6_sw4p0_fence6p8_feed8p80_match_l2p5_c0p22_loadside",
            rationale="Conjugate load-side L-match solved from the candidate-76 impedance, using series L and shunt C.",
            substrate_h_mm=7.2,
            top_length_mm=9.6,
            top_width_mm=9.6,
            short_wall_width_mm=4.0,
            side_fence_length_mm=6.8,
            feed_from_short_mm=8.80,
            match_series_ind_nh=2.5,
            match_shunt_cap_pf=0.22,
            match_shunt_on_load_side=True,
            total_height_limit_mm=10.0,
        ),
        ThickPifaCandidate(
            name="h8p0_l12p0_w10p0_sw4p0_fence8p0_feed11p10_lim10_lowcost",
            rationale="Nudge the 12 mm top plate feed slightly back toward the short wall to see whether the raw input moves closer to a practical match while keeping the high-gain aperture.",
            substrate_h_mm=8.0,
            top_length_mm=12.0,
            top_width_mm=10.0,
            short_wall_width_mm=4.0,
            side_fence_length_mm=8.0,
            feed_from_short_mm=11.10,
            total_height_limit_mm=10.0,
        ),
        ThickPifaCandidate(
            name="h8p0_l12p0_w10p0_sw4p0_fence8p0_feed11p30_match_l2p9_c0p24_gap0p08_loadside",
            rationale="Apply a tighter load-side L-match with a smaller parasitic gap and island to push the 12 mm high-gain geometry toward 50 ohm.",
            substrate_h_mm=8.0,
            top_length_mm=12.0,
            top_width_mm=10.0,
            short_wall_width_mm=4.0,
            side_fence_length_mm=8.0,
            feed_from_short_mm=11.30,
            match_series_ind_nh=2.9,
            match_shunt_cap_pf=0.24,
            match_shunt_on_load_side=True,
            match_gap_mm=0.08,
            match_island_size_mm=0.60,
            match_series_width_mm=0.24,
            total_height_limit_mm=10.0,
        ),
        ThickPifaCandidate(
            name="h8p0_l12p0_w10p0_sw4p0_fence8p0_feed11p30_match_l3p4_c0p28_gap0p08_loadside",
            rationale="Use a slightly stronger tight-geometry load-side match to test whether the physical implementation needs more nominal reactance than the ideal circuit estimate.",
            substrate_h_mm=8.0,
            top_length_mm=12.0,
            top_width_mm=10.0,
            short_wall_width_mm=4.0,
            side_fence_length_mm=8.0,
            feed_from_short_mm=11.30,
            match_series_ind_nh=3.4,
            match_shunt_cap_pf=0.28,
            match_shunt_on_load_side=True,
            match_gap_mm=0.08,
            match_island_size_mm=0.60,
            match_series_width_mm=0.24,
            total_height_limit_mm=10.0,
        ),
        ThickPifaCandidate(
            name="h8p0_l12p0_w10p0_sw4p0_fence8p0_feed11p30_match_l3p0_c0p26_gap0p10_loadside",
            rationale="Relax the island gap slightly while keeping the same matched 12 mm footprint to balance reactance compensation and parasitic loading.",
            substrate_h_mm=8.0,
            top_length_mm=12.0,
            top_width_mm=10.0,
            short_wall_width_mm=4.0,
            side_fence_length_mm=8.0,
            feed_from_short_mm=11.30,
            match_series_ind_nh=3.0,
            match_shunt_cap_pf=0.26,
            match_shunt_on_load_side=True,
            match_gap_mm=0.10,
            match_island_size_mm=0.65,
            match_series_width_mm=0.28,
            total_height_limit_mm=10.0,
        ),
        ThickPifaCandidate(
            name="h8p0_l12p0_w10p0_sw4p0_fence8p0_feed11p30_lip1p6_w5p0_lim10_lowcost",
            rationale="Add stronger open-edge capacitive loading to the 12 mm high-gain PIFA without discrete matching components.",
            substrate_h_mm=8.0,
            top_length_mm=12.0,
            top_width_mm=10.0,
            short_wall_width_mm=4.0,
            side_fence_length_mm=8.0,
            feed_from_short_mm=11.30,
            open_lip_height_mm=1.6,
            open_lip_width_mm=5.0,
            total_height_limit_mm=10.0,
        ),
        ThickPifaCandidate(
            name="h8p0_l12p0_w10p0_sw4p0_fence8p0_feed11p30_lip2p4_w6p0_lim10_lowcost",
            rationale="Increase the open-edge lip depth and width to pull down the strong inductive input while checking low-elevation gain margin.",
            substrate_h_mm=8.0,
            top_length_mm=12.0,
            top_width_mm=10.0,
            short_wall_width_mm=4.0,
            side_fence_length_mm=8.0,
            feed_from_short_mm=11.30,
            open_lip_height_mm=2.4,
            open_lip_width_mm=6.0,
            total_height_limit_mm=10.0,
        ),
        ThickPifaCandidate(
            name="h8p0_l12p0_w10p0_sw6p0_fence9p0_feed11p20_lip2p0_w6p0_lim10_lowcost",
            rationale="Use a stronger short/side-wall return plus open-edge lip to retune the cavity current path rather than only the lumped match.",
            substrate_h_mm=8.0,
            top_length_mm=12.0,
            top_width_mm=10.0,
            short_wall_width_mm=6.0,
            side_fence_length_mm=9.0,
            feed_from_short_mm=11.20,
            open_lip_height_mm=2.0,
            open_lip_width_mm=6.0,
            total_height_limit_mm=10.0,
        ),
        ThickPifaCandidate(
            name="h8p0_l12p0_w10p0_sw4p0_fence8p0_feed11p30_lip2p4_w6p0_match_l2p8_c0p22_gap0p08_loadside",
            rationale="Combine the best open-edge lip with a tight load-side L-match to see whether the lip can keep the gain up while the match pulls S11 down.",
            substrate_h_mm=8.0,
            top_length_mm=12.0,
            top_width_mm=10.0,
            short_wall_width_mm=4.0,
            side_fence_length_mm=8.0,
            feed_from_short_mm=11.30,
            open_lip_height_mm=2.4,
            open_lip_width_mm=6.0,
            match_series_ind_nh=2.8,
            match_shunt_cap_pf=0.22,
            match_shunt_on_load_side=True,
            match_gap_mm=0.08,
            match_island_size_mm=0.60,
            match_series_width_mm=0.24,
            total_height_limit_mm=10.0,
        ),
        ThickPifaCandidate(
            name="h8p0_l12p0_w10p0_sw4p0_fence8p0_feed11p30_lip2p4_w6p0_match_l3p2_c0p24_gap0p08_loadside",
            rationale="Use a slightly stronger matched lip variant to bracket the load-side reactance compensation on the same low-cost cavity form.",
            substrate_h_mm=8.0,
            top_length_mm=12.0,
            top_width_mm=10.0,
            short_wall_width_mm=4.0,
            side_fence_length_mm=8.0,
            feed_from_short_mm=11.30,
            open_lip_height_mm=2.4,
            open_lip_width_mm=6.0,
            match_series_ind_nh=3.2,
            match_shunt_cap_pf=0.24,
            match_shunt_on_load_side=True,
            match_gap_mm=0.08,
            match_island_size_mm=0.60,
            match_series_width_mm=0.24,
            total_height_limit_mm=10.0,
        ),
        ThickPifaCandidate(
            name="h8p0_l12p0_w10p0_sw4p0_fence6p2_start0p8_feed11p05_lip2p0_w6p0_edgec2p8_h4p8_slot7p2x2p8",
            rationale="Move the side via walls off the short wall, add open-edge side coupling, and cut a narrow top slot to lengthen the high-current path without a separate arm.",
            substrate_h_mm=8.0,
            top_length_mm=12.0,
            top_width_mm=10.0,
            short_wall_width_mm=4.0,
            side_fence_length_mm=6.2,
            side_fence_start_from_short_mm=0.8,
            feed_from_short_mm=11.05,
            open_lip_height_mm=2.0,
            open_lip_width_mm=6.0,
            open_edge_coupler_length_mm=2.8,
            open_edge_coupler_height_mm=4.8,
            top_slot_start_from_short_mm=7.2,
            top_slot_length_mm=2.8,
            top_slot_width_mm=0.42,
            edge_slot_start_from_short_mm=7.8,
            edge_slot_length_mm=2.4,
            edge_slot_depth_mm=0.65,
            total_height_limit_mm=10.0,
        ),
        ThickPifaCandidate(
            name="h8p0_l12p0_w10p0_sw4p0_fence6p2_start0p8_feed11p15_lip2p0_edgec3p2_h5p6_slot_match_l2p8_c0p22",
            rationale="Keep the same geometry-current path as the first slot/coupler case, then retune the load-side L match around the shifted feed point.",
            substrate_h_mm=8.0,
            top_length_mm=12.0,
            top_width_mm=10.0,
            short_wall_width_mm=4.0,
            side_fence_length_mm=6.2,
            side_fence_start_from_short_mm=0.8,
            feed_from_short_mm=11.15,
            open_lip_height_mm=2.0,
            open_lip_width_mm=6.0,
            open_edge_coupler_length_mm=3.2,
            open_edge_coupler_height_mm=5.6,
            top_slot_start_from_short_mm=7.0,
            top_slot_length_mm=3.2,
            top_slot_width_mm=0.46,
            edge_slot_start_from_short_mm=7.6,
            edge_slot_length_mm=2.8,
            edge_slot_depth_mm=0.75,
            match_series_ind_nh=2.8,
            match_shunt_cap_pf=0.22,
            match_shunt_on_load_side=True,
            match_gap_mm=0.08,
            match_island_size_mm=0.60,
            match_series_width_mm=0.24,
            total_height_limit_mm=10.0,
        ),
        ThickPifaCandidate(
            name="h8p0_l12p0_w10p5_sw5p2_fence5p4_start1p6_feed10p85_lip1p6_edgec3p8_h6p0_edgeslot",
            rationale="Use a stronger short wall with shorter displaced side fences and deeper edge slots to pull the cavity mode toward the feed while preserving low-elevation radiation.",
            substrate_h_mm=8.0,
            top_length_mm=12.0,
            top_width_mm=10.5,
            short_wall_width_mm=5.2,
            side_fence_length_mm=5.4,
            side_fence_start_from_short_mm=1.6,
            feed_from_short_mm=10.85,
            open_lip_height_mm=1.6,
            open_lip_width_mm=6.4,
            open_edge_coupler_length_mm=3.8,
            open_edge_coupler_height_mm=6.0,
            top_slot_start_from_short_mm=6.6,
            top_slot_length_mm=3.8,
            top_slot_width_mm=0.50,
            edge_slot_start_from_short_mm=6.8,
            edge_slot_length_mm=3.6,
            edge_slot_depth_mm=0.95,
            total_height_limit_mm=10.0,
        ),
        ThickPifaCandidate(
            name="h8p0_l12p0_w10p5_sw5p2_fence5p4_start1p6_feed10p95_lip1p6_edgec4p0_h6p2_match_l3p0_c0p24",
            rationale="Add a moderate load-side L match to the stronger short-wall/edge-slot case, testing whether the geometry path can recover return loss before gain collapses.",
            substrate_h_mm=8.0,
            top_length_mm=12.0,
            top_width_mm=10.5,
            short_wall_width_mm=5.2,
            side_fence_length_mm=5.4,
            side_fence_start_from_short_mm=1.6,
            feed_from_short_mm=10.95,
            open_lip_height_mm=1.6,
            open_lip_width_mm=6.4,
            open_edge_coupler_length_mm=4.0,
            open_edge_coupler_height_mm=6.2,
            top_slot_start_from_short_mm=6.6,
            top_slot_length_mm=3.8,
            top_slot_width_mm=0.50,
            edge_slot_start_from_short_mm=6.8,
            edge_slot_length_mm=3.6,
            edge_slot_depth_mm=0.95,
            match_series_ind_nh=3.0,
            match_shunt_cap_pf=0.24,
            match_shunt_on_load_side=True,
            match_gap_mm=0.08,
            match_island_size_mm=0.60,
            match_series_width_mm=0.24,
            total_height_limit_mm=10.0,
        ),
        ThickPifaCandidate(
            name="h8p0_l11p4_w11p2_sw5p8_fence4p8_start2p0_feed10p35_lip1p2_edgec4p2_h6p8_slot6p2x4p4",
            rationale="Compact the length but widen the cavity aperture; displaced fences and a longer central slot push the current around the side edges for a low-cost meandered PIFA.",
            substrate_h_mm=8.0,
            top_length_mm=11.4,
            top_width_mm=11.2,
            short_wall_width_mm=5.8,
            side_fence_length_mm=4.8,
            side_fence_start_from_short_mm=2.0,
            feed_from_short_mm=10.35,
            open_lip_height_mm=1.2,
            open_lip_width_mm=7.0,
            open_edge_coupler_length_mm=4.2,
            open_edge_coupler_height_mm=6.8,
            top_slot_start_from_short_mm=6.2,
            top_slot_length_mm=4.4,
            top_slot_width_mm=0.55,
            edge_slot_start_from_short_mm=6.4,
            edge_slot_length_mm=3.8,
            edge_slot_depth_mm=1.05,
            total_height_limit_mm=10.0,
        ),
        ThickPifaCandidate(
            name="h8p0_l11p4_w11p2_sw5p8_fence4p8_start2p0_feed10p45_lip1p2_edgec4p2_h6p8_match_l3p2_c0p26",
            rationale="Matched version of the widened aperture slot case, keeping all added features manufacturable as plated via-wall and etched top-copper details.",
            substrate_h_mm=8.0,
            top_length_mm=11.4,
            top_width_mm=11.2,
            short_wall_width_mm=5.8,
            side_fence_length_mm=4.8,
            side_fence_start_from_short_mm=2.0,
            feed_from_short_mm=10.45,
            open_lip_height_mm=1.2,
            open_lip_width_mm=7.0,
            open_edge_coupler_length_mm=4.2,
            open_edge_coupler_height_mm=6.8,
            top_slot_start_from_short_mm=6.2,
            top_slot_length_mm=4.4,
            top_slot_width_mm=0.55,
            edge_slot_start_from_short_mm=6.4,
            edge_slot_length_mm=3.8,
            edge_slot_depth_mm=1.05,
            match_series_ind_nh=3.2,
            match_shunt_cap_pf=0.26,
            match_shunt_on_load_side=True,
            match_gap_mm=0.08,
            match_island_size_mm=0.60,
            match_series_width_mm=0.24,
            total_height_limit_mm=10.0,
        ),
        ThickPifaCandidate(
            name="h8p0_w11p2_f1085_slot",
            rationale="Move the feed closer to the open edge on the best gain-pass wide aperture geometry to pull the impedance toward resonance without adding discrete matching loss.",
            substrate_h_mm=8.0,
            top_length_mm=11.4,
            top_width_mm=11.2,
            short_wall_width_mm=5.8,
            side_fence_length_mm=4.8,
            side_fence_start_from_short_mm=2.0,
            feed_from_short_mm=10.85,
            open_lip_height_mm=1.2,
            open_lip_width_mm=7.0,
            open_edge_coupler_length_mm=4.2,
            open_edge_coupler_height_mm=6.8,
            top_slot_start_from_short_mm=6.2,
            top_slot_length_mm=4.4,
            top_slot_width_mm=0.55,
            edge_slot_start_from_short_mm=6.4,
            edge_slot_length_mm=3.8,
            edge_slot_depth_mm=1.05,
            total_height_limit_mm=10.0,
        ),
        ThickPifaCandidate(
            name="h8p0_w11p2_f1105_slot",
            rationale="Push the feed farther toward the open edge on the same wide aperture geometry, looking for a better impedance point while keeping the low-angle coverage structure intact.",
            substrate_h_mm=8.0,
            top_length_mm=11.4,
            top_width_mm=11.2,
            short_wall_width_mm=5.8,
            side_fence_length_mm=4.8,
            side_fence_start_from_short_mm=2.0,
            feed_from_short_mm=11.05,
            open_lip_height_mm=1.2,
            open_lip_width_mm=7.0,
            open_edge_coupler_length_mm=4.2,
            open_edge_coupler_height_mm=6.8,
            top_slot_start_from_short_mm=6.2,
            top_slot_length_mm=4.4,
            top_slot_width_mm=0.55,
            edge_slot_start_from_short_mm=6.4,
            edge_slot_length_mm=3.8,
            edge_slot_depth_mm=1.05,
            total_height_limit_mm=10.0,
        ),
        ThickPifaCandidate(
            name="h8p0_w11p2_f1085_m228",
            rationale="Same feed shift as the previous case, but with a lighter load-side match to see if the impedance can be pulled down without giving away too much gain.",
            substrate_h_mm=8.0,
            top_length_mm=11.4,
            top_width_mm=11.2,
            short_wall_width_mm=5.8,
            side_fence_length_mm=4.8,
            side_fence_start_from_short_mm=2.0,
            feed_from_short_mm=10.85,
            open_lip_height_mm=1.2,
            open_lip_width_mm=7.0,
            open_edge_coupler_length_mm=4.2,
            open_edge_coupler_height_mm=6.8,
            top_slot_start_from_short_mm=6.2,
            top_slot_length_mm=4.4,
            top_slot_width_mm=0.55,
            edge_slot_start_from_short_mm=6.4,
            edge_slot_length_mm=3.8,
            edge_slot_depth_mm=1.05,
            match_series_ind_nh=2.8,
            match_shunt_cap_pf=0.22,
            match_shunt_on_load_side=True,
            match_gap_mm=0.08,
            match_island_size_mm=0.60,
            match_series_width_mm=0.24,
            total_height_limit_mm=10.0,
        ),
        ThickPifaCandidate(
            name="h8p0_w11p2_f1105_m3024",
            rationale="Load-side match on the farther-open feed point, targeting the same wide aperture geometry with a slightly stronger impedance pull.",
            substrate_h_mm=8.0,
            top_length_mm=11.4,
            top_width_mm=11.2,
            short_wall_width_mm=5.8,
            side_fence_length_mm=4.8,
            side_fence_start_from_short_mm=2.0,
            feed_from_short_mm=11.05,
            open_lip_height_mm=1.2,
            open_lip_width_mm=7.0,
            open_edge_coupler_length_mm=4.2,
            open_edge_coupler_height_mm=6.8,
            top_slot_start_from_short_mm=6.2,
            top_slot_length_mm=4.4,
            top_slot_width_mm=0.55,
            edge_slot_start_from_short_mm=6.4,
            edge_slot_length_mm=3.8,
            edge_slot_depth_mm=1.05,
            match_series_ind_nh=3.0,
            match_shunt_cap_pf=0.24,
            match_shunt_on_load_side=True,
            match_gap_mm=0.08,
            match_island_size_mm=0.60,
            match_series_width_mm=0.24,
            total_height_limit_mm=10.0,
        ),
        ThickPifaCandidate(
            name="h8p0_w11p2_f1105_m5625",
            rationale="Apply the stronger L/C pair that previously helped the lower-height geometry, but keep the best gain-pass wide aperture and the same feed point.",
            substrate_h_mm=8.0,
            top_length_mm=11.4,
            top_width_mm=11.2,
            short_wall_width_mm=5.8,
            side_fence_length_mm=4.8,
            side_fence_start_from_short_mm=2.0,
            feed_from_short_mm=11.05,
            open_lip_height_mm=1.2,
            open_lip_width_mm=7.0,
            open_edge_coupler_length_mm=4.2,
            open_edge_coupler_height_mm=6.8,
            top_slot_start_from_short_mm=6.2,
            top_slot_length_mm=4.4,
            top_slot_width_mm=0.55,
            edge_slot_start_from_short_mm=6.4,
            edge_slot_length_mm=3.8,
            edge_slot_depth_mm=1.05,
            match_series_ind_nh=5.6,
            match_shunt_cap_pf=0.25,
            match_shunt_on_load_side=True,
            match_gap_mm=0.08,
            match_island_size_mm=0.60,
            match_series_width_mm=0.24,
            total_height_limit_mm=10.0,
        ),
        ThickPifaCandidate(
            name="h8p0_w11p2_f1105_m6028",
            rationale="Bracket the stronger L/C match with a slightly heavier series inductance and shunt capacitance to see if the wide aperture can be pulled onto resonance without killing horizon gain.",
            substrate_h_mm=8.0,
            top_length_mm=11.4,
            top_width_mm=11.2,
            short_wall_width_mm=5.8,
            side_fence_length_mm=4.8,
            side_fence_start_from_short_mm=2.0,
            feed_from_short_mm=11.05,
            open_lip_height_mm=1.2,
            open_lip_width_mm=7.0,
            open_edge_coupler_length_mm=4.2,
            open_edge_coupler_height_mm=6.8,
            top_slot_start_from_short_mm=6.2,
            top_slot_length_mm=4.4,
            top_slot_width_mm=0.55,
            edge_slot_start_from_short_mm=6.4,
            edge_slot_length_mm=3.8,
            edge_slot_depth_mm=1.05,
            match_series_ind_nh=6.0,
            match_shunt_cap_pf=0.28,
            match_shunt_on_load_side=True,
            match_gap_mm=0.08,
            match_island_size_mm=0.60,
            match_series_width_mm=0.24,
            total_height_limit_mm=10.0,
        ),
        ThickPifaCandidate(
            name="h8p0_l14p0_w11p2_f1355_slot",
            rationale="Extend the current path length while keeping the same low-cost wide aperture and open-edge coupler, aiming to move the resonance down without losing the low-angle gain lift.",
            substrate_h_mm=8.0,
            top_length_mm=14.0,
            top_width_mm=11.2,
            short_wall_width_mm=5.8,
            side_fence_length_mm=6.0,
            side_fence_start_from_short_mm=2.0,
            feed_from_short_mm=13.55,
            open_lip_height_mm=1.2,
            open_lip_width_mm=7.0,
            open_edge_coupler_length_mm=4.8,
            open_edge_coupler_height_mm=6.8,
            top_slot_start_from_short_mm=7.6,
            top_slot_length_mm=5.0,
            top_slot_width_mm=0.55,
            edge_slot_start_from_short_mm=8.0,
            edge_slot_length_mm=4.2,
            edge_slot_depth_mm=1.05,
            total_height_limit_mm=10.0,
        ),
        ThickPifaCandidate(
            name="h8p0_l14p0_w11p2_f1355_m5625",
            rationale="Apply the stronger L/C pair to the extended path version, checking whether the longer arm can recover S11 while the wide aperture still keeps the horizon gain within spec.",
            substrate_h_mm=8.0,
            top_length_mm=14.0,
            top_width_mm=11.2,
            short_wall_width_mm=5.8,
            side_fence_length_mm=6.0,
            side_fence_start_from_short_mm=2.0,
            feed_from_short_mm=13.55,
            open_lip_height_mm=1.2,
            open_lip_width_mm=7.0,
            open_edge_coupler_length_mm=4.8,
            open_edge_coupler_height_mm=6.8,
            top_slot_start_from_short_mm=7.6,
            top_slot_length_mm=5.0,
            top_slot_width_mm=0.55,
            edge_slot_start_from_short_mm=8.0,
            edge_slot_length_mm=4.2,
            edge_slot_depth_mm=1.05,
            match_series_ind_nh=5.6,
            match_shunt_cap_pf=0.25,
            match_shunt_on_load_side=True,
            match_gap_mm=0.08,
            match_island_size_mm=0.60,
            match_series_width_mm=0.24,
            total_height_limit_mm=10.0,
        ),
        ThickPifaCandidate(
            name="h8p0_l16p0_w12p5_f1555_slot",
            rationale="Stretch the current path and aperture again so the impedance point moves closer to 8 GHz while the wide cavity keeps the low-angle gain from collapsing.",
            substrate_h_mm=8.0,
            top_length_mm=16.0,
            top_width_mm=12.5,
            short_wall_width_mm=5.8,
            side_fence_length_mm=6.2,
            side_fence_start_from_short_mm=2.0,
            feed_from_short_mm=15.55,
            open_lip_height_mm=1.2,
            open_lip_width_mm=7.4,
            open_edge_coupler_length_mm=5.2,
            open_edge_coupler_height_mm=6.8,
            top_slot_start_from_short_mm=8.8,
            top_slot_length_mm=5.6,
            top_slot_width_mm=0.60,
            edge_slot_start_from_short_mm=9.0,
            edge_slot_length_mm=4.8,
            edge_slot_depth_mm=1.10,
            total_height_limit_mm=10.0,
        ),
        ThickPifaCandidate(
            name="h8p0_l16p0_w12p5_f1555_m5625",
            rationale="Add the stronger load-side match to the stretched 16 mm aperture path, trying to keep the low-angle gain while finally pulling S11 toward the limit.",
            substrate_h_mm=8.0,
            top_length_mm=16.0,
            top_width_mm=12.5,
            short_wall_width_mm=5.8,
            side_fence_length_mm=6.2,
            side_fence_start_from_short_mm=2.0,
            feed_from_short_mm=15.55,
            open_lip_height_mm=1.2,
            open_lip_width_mm=7.4,
            open_edge_coupler_length_mm=5.2,
            open_edge_coupler_height_mm=6.8,
            top_slot_start_from_short_mm=8.8,
            top_slot_length_mm=5.6,
            top_slot_width_mm=0.60,
            edge_slot_start_from_short_mm=9.0,
            edge_slot_length_mm=4.8,
            edge_slot_depth_mm=1.10,
            match_series_ind_nh=5.6,
            match_shunt_cap_pf=0.25,
            match_shunt_on_load_side=True,
            match_gap_mm=0.08,
            match_island_size_mm=0.60,
            match_series_width_mm=0.24,
            total_height_limit_mm=10.0,
        ),
        ThickPifaCandidate(
            name="h3p5_l9p2_w8p6_sw4p4_fence6p4_feed8p70_lip0p8_edgec2p6_slot",
            rationale="Start from the only S11-pass low-height family, then add a manufacturable lip, side-edge coupling, and etched slots to recover low-angle current without losing the shorted-cavity match.",
            substrate_h_mm=3.5,
            top_length_mm=9.2,
            top_width_mm=8.6,
            short_wall_width_mm=4.4,
            side_fence_length_mm=6.4,
            feed_from_short_mm=8.70,
            open_lip_height_mm=0.8,
            open_lip_width_mm=5.6,
            open_edge_coupler_length_mm=2.6,
            open_edge_coupler_height_mm=3.1,
            top_slot_start_from_short_mm=4.6,
            top_slot_length_mm=2.8,
            top_slot_width_mm=0.40,
            edge_slot_start_from_short_mm=5.0,
            edge_slot_length_mm=2.4,
            edge_slot_depth_mm=0.55,
            total_height_limit_mm=10.0,
        ),
        ThickPifaCandidate(
            name="h4p0_l9p2_w8p8_sw4p4_fence6p6_start0p4_feed8p70_lip0p9_edgec2p8_slot",
            rationale="Use a slightly taller cavity than the S11-pass baseline and move the via walls off the short edge to trade a small return-loss margin for more horizon current.",
            substrate_h_mm=4.0,
            top_length_mm=9.2,
            top_width_mm=8.8,
            short_wall_width_mm=4.4,
            side_fence_length_mm=6.6,
            side_fence_start_from_short_mm=0.4,
            feed_from_short_mm=8.70,
            open_lip_height_mm=0.9,
            open_lip_width_mm=5.8,
            open_edge_coupler_length_mm=2.8,
            open_edge_coupler_height_mm=3.6,
            top_slot_start_from_short_mm=4.8,
            top_slot_length_mm=3.0,
            top_slot_width_mm=0.42,
            edge_slot_start_from_short_mm=5.0,
            edge_slot_length_mm=2.6,
            edge_slot_depth_mm=0.62,
            total_height_limit_mm=10.0,
        ),
        ThickPifaCandidate(
            name="h4p5_l9p6_w9p2_sw4p8_fence6p8_start0p8_feed8p95_lip1p0_edgec3p2_slot",
            rationale="Revisit the near-S11-pass 4.5 mm geometry with displaced side walls and open-edge capacitive coupling instead of relying on the L/C island.",
            substrate_h_mm=4.5,
            top_length_mm=9.6,
            top_width_mm=9.2,
            short_wall_width_mm=4.8,
            side_fence_length_mm=6.8,
            side_fence_start_from_short_mm=0.8,
            feed_from_short_mm=8.95,
            open_lip_height_mm=1.0,
            open_lip_width_mm=6.0,
            open_edge_coupler_length_mm=3.2,
            open_edge_coupler_height_mm=4.2,
            top_slot_start_from_short_mm=5.0,
            top_slot_length_mm=3.2,
            top_slot_width_mm=0.45,
            edge_slot_start_from_short_mm=5.2,
            edge_slot_length_mm=2.8,
            edge_slot_depth_mm=0.72,
            total_height_limit_mm=10.0,
        ),
        ThickPifaCandidate(
            name="h5p2_l9p8_w9p4_sw4p8_fence6p8_start1p0_feed9p15_lip1p2_edgec3p4_slot",
            rationale="Middle-height geometry-current candidate intended to find the crossover between the matched-but-weak 4.5 mm case and the gain-pass 7.2 mm case.",
            substrate_h_mm=5.2,
            top_length_mm=9.8,
            top_width_mm=9.4,
            short_wall_width_mm=4.8,
            side_fence_length_mm=6.8,
            side_fence_start_from_short_mm=1.0,
            feed_from_short_mm=9.15,
            open_lip_height_mm=1.2,
            open_lip_width_mm=6.2,
            open_edge_coupler_length_mm=3.4,
            open_edge_coupler_height_mm=4.8,
            top_slot_start_from_short_mm=5.2,
            top_slot_length_mm=3.4,
            top_slot_width_mm=0.48,
            edge_slot_start_from_short_mm=5.4,
            edge_slot_length_mm=3.0,
            edge_slot_depth_mm=0.80,
            total_height_limit_mm=10.0,
        ),
        ThickPifaCandidate(
            name="h6p2_l9p8_w9p4_sw4p8_fence6p8_start1p0_feed9p15_lip1p4_edgec3p6_slot",
            rationale="Raise the same crossover geometry to strengthen the vertical current path, checking whether edge slots and couplers can keep S11 from collapsing like the 8 mm family.",
            substrate_h_mm=6.2,
            top_length_mm=9.8,
            top_width_mm=9.4,
            short_wall_width_mm=4.8,
            side_fence_length_mm=6.8,
            side_fence_start_from_short_mm=1.0,
            feed_from_short_mm=9.15,
            open_lip_height_mm=1.4,
            open_lip_width_mm=6.2,
            open_edge_coupler_length_mm=3.6,
            open_edge_coupler_height_mm=5.4,
            top_slot_start_from_short_mm=5.2,
            top_slot_length_mm=3.4,
            top_slot_width_mm=0.48,
            edge_slot_start_from_short_mm=5.4,
            edge_slot_length_mm=3.0,
            edge_slot_depth_mm=0.85,
            total_height_limit_mm=10.0,
        ),
        ThickPifaCandidate(
            name="h6p8_l10p4_w10p0_sw5p2_fence7p2_start1p2_feed9p80_lip1p4_edgec3p8_slot",
            rationale="Use the best low-cost manufacturing features on a 6.8 mm cavity, aiming for gain pass with less impedance penalty than the 7.2/8.0 mm wide-aperture cases.",
            substrate_h_mm=6.8,
            top_length_mm=10.4,
            top_width_mm=10.0,
            short_wall_width_mm=5.2,
            side_fence_length_mm=7.2,
            side_fence_start_from_short_mm=1.2,
            feed_from_short_mm=9.80,
            open_lip_height_mm=1.4,
            open_lip_width_mm=6.6,
            open_edge_coupler_length_mm=3.8,
            open_edge_coupler_height_mm=6.0,
            top_slot_start_from_short_mm=5.6,
            top_slot_length_mm=3.8,
            top_slot_width_mm=0.50,
            edge_slot_start_from_short_mm=5.8,
            edge_slot_length_mm=3.4,
            edge_slot_depth_mm=0.95,
            total_height_limit_mm=10.0,
        ),
        ThickPifaCandidate(
            name="h7p2_l10p0_w10p8_sw5p6_fence6p0_start2p0_feed9p45_lip1p2_edgec4p8_slot",
            rationale="Keep the gain-pass height but shorten the current path and move the side fences farther from the short wall to lower the feed impedance without sacrificing the wide low-angle aperture.",
            substrate_h_mm=7.2,
            top_length_mm=10.0,
            top_width_mm=10.8,
            short_wall_width_mm=5.6,
            side_fence_length_mm=6.0,
            side_fence_start_from_short_mm=2.0,
            feed_from_short_mm=9.45,
            open_lip_height_mm=1.2,
            open_lip_width_mm=6.8,
            open_edge_coupler_length_mm=4.8,
            open_edge_coupler_height_mm=6.2,
            top_slot_start_from_short_mm=5.4,
            top_slot_length_mm=3.8,
            top_slot_width_mm=0.52,
            edge_slot_start_from_short_mm=5.6,
            edge_slot_length_mm=3.6,
            edge_slot_depth_mm=1.00,
            total_height_limit_mm=10.0,
        ),
    ]


def safe_slug(value: str, limit: int = 72) -> str:
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


def candidate_paths(candidate: ThickPifaCandidate) -> dict[str, Path]:
    project = ROOT / f"{STEM}_{safe_slug(candidate.name)}.aedt"
    return {
        "project": project,
        "results": project.with_suffix(".aedtresults"),
        "pyaedt": project.with_suffix(".pyaedt"),
        "params": REPORT_DIR / f"{STEM}_{safe_slug(candidate.name)}_params.json",
    }


def params_dict(candidate: ThickPifaCandidate) -> dict[str, float]:
    return {
        "freq_center_ghz": 8.0,
        "freq_start_ghz": 7.7,
        "freq_stop_ghz": 8.3,
        "freq_step_ghz": 0.02,
        "air_frequency_ghz": 7.0,
        "board_diameter_mm": 44.0,
        "ground_radius_mm": candidate.ground_radius_mm,
        "substrate_h_mm": candidate.substrate_h_mm,
        "copper_t_mm": 0.035,
        "total_height_limit_mm": candidate.total_height_limit_mm,
        "epsr": candidate.epsr,
        "tan_delta": candidate.tan_delta,
        "feed_pad_radius_mm": candidate.feed_pad_radius_mm,
        "port_width_mm": candidate.port_width_mm,
    }


def validate_candidate(candidate: ThickPifaCandidate) -> None:
    if candidate.substrate_h_mm + 0.035 > candidate.total_height_limit_mm:
        raise ValueError(f"{candidate.name}: total height exceeds limit")
    if candidate.top_length_mm <= 1.0 or candidate.top_width_mm <= 1.0:
        raise ValueError(f"{candidate.name}: top plate dimensions are too small")
    if candidate.short_wall_width_mm <= 0.20:
        raise ValueError(f"{candidate.name}: short wall width is not manufacturable")
    if candidate.side_fence_start_from_short_mm < 0.0:
        raise ValueError(f"{candidate.name}: side fence start must not be negative")
    if candidate.port_width_mm <= 0.10:
        raise ValueError(f"{candidate.name}: port width is too small")
    feed_u = -candidate.top_length_mm / 2.0 + candidate.feed_from_short_mm
    if feed_u <= -candidate.top_length_mm / 2.0 + 0.20 or feed_u >= candidate.top_length_mm / 2.0 - 0.30:
        raise ValueError(f"{candidate.name}: feed must sit between the short wall and open end")
    max_extent = math.hypot(candidate.top_length_mm / 2.0, candidate.top_width_mm / 2.0)
    if max_extent > candidate.ground_radius_mm - 1.0:
        raise ValueError(f"{candidate.name}: element footprint is too close to board edge")
    for label, value in [
        ("open edge coupler length", candidate.open_edge_coupler_length_mm),
        ("open edge coupler height", candidate.open_edge_coupler_height_mm),
        ("top slot start", candidate.top_slot_start_from_short_mm),
        ("top slot length", candidate.top_slot_length_mm),
        ("top slot width", candidate.top_slot_width_mm),
        ("edge slot start", candidate.edge_slot_start_from_short_mm),
        ("edge slot length", candidate.edge_slot_length_mm),
        ("edge slot depth", candidate.edge_slot_depth_mm),
    ]:
        if value < 0.0:
            raise ValueError(f"{candidate.name}: {label} must not be negative")
    if candidate.top_slot_length_mm > 0.0 and candidate.top_slot_width_mm > candidate.top_width_mm - 0.8:
        raise ValueError(f"{candidate.name}: top slot would over-cut the plate width")
    if candidate.edge_slot_depth_mm > candidate.top_width_mm / 2.0 - 0.4:
        raise ValueError(f"{candidate.name}: edge slot depth would over-cut the plate")


def vertical_wall_points(u0: float, u1: float, v0: float, v1: float, z0: float, z1: float, axis: str) -> list[list[float]]:
    if axis == "u":
        u = u0
        return [[u, v0, z0], [u, v1, z0], [u, v1, z1], [u, v0, z1]]
    if axis == "v":
        v = v0
        return [[u0, v, z0], [u1, v, z0], [u1, v, z1], [u0, v, z1]]
    raise ValueError(f"Unsupported wall axis {axis}")


def add_thick_pifa_geometry(hfss, candidate: ThickPifaCandidate) -> list[str]:
    h = candidate.substrate_h_mm
    half_l = candidate.top_length_mm / 2.0
    half_w = candidate.top_width_mm / 2.0
    short_u = -half_l
    open_u = half_l
    metals: list[str] = []

    top = builder.polygon_sheet(
        hfss,
        "E1_thick_pifa_top_plate",
        builder.rectangle_points(0.0, 0.0, 0.0, -half_l, half_l, -half_w, half_w, h),
        "copper",
    )
    metals.append(top.name)

    slot_names: list[str] = []
    if candidate.top_slot_length_mm > 0.0 and candidate.top_slot_width_mm > 0.0:
        slot_u0 = max(short_u + candidate.top_slot_start_from_short_mm, short_u + 0.25)
        slot_u1 = min(slot_u0 + candidate.top_slot_length_mm, open_u - 0.25)
        slot_half_w = min(candidate.top_slot_width_mm / 2.0, half_w - 0.35)
        slot_v0 = max(candidate.top_slot_v_offset_mm - slot_half_w, -half_w + 0.25)
        slot_v1 = min(candidate.top_slot_v_offset_mm + slot_half_w, half_w - 0.25)
        if slot_u1 > slot_u0 + 0.20 and slot_v1 > slot_v0 + 0.10:
            top_slot = builder.polygon_sheet(
                hfss,
                "E1_thick_pifa_top_current_path_slot",
                builder.rectangle_points(0.0, 0.0, 0.0, slot_u0, slot_u1, slot_v0, slot_v1, h),
                "vacuum",
            )
            slot_names.append(top_slot.name)

    if candidate.edge_slot_length_mm > 0.0 and candidate.edge_slot_depth_mm > 0.0:
        edge_u0 = max(short_u + candidate.edge_slot_start_from_short_mm, short_u + 0.25)
        edge_u1 = min(edge_u0 + candidate.edge_slot_length_mm, open_u - 0.20)
        depth = min(candidate.edge_slot_depth_mm, half_w - 0.35)
        if edge_u1 > edge_u0 + 0.20 and depth > 0.10:
            for side, v0, v1 in [
                ("pos", half_w - depth, half_w),
                ("neg", -half_w, -half_w + depth),
            ]:
                edge_slot = builder.polygon_sheet(
                    hfss,
                    f"E1_thick_pifa_edge_current_path_slot_{side}",
                    builder.rectangle_points(0.0, 0.0, 0.0, edge_u0, edge_u1, v0, v1, h),
                    "vacuum",
                )
                slot_names.append(edge_slot.name)

    if slot_names:
        hfss.modeler.subtract(top.name, slot_names, keep_originals=False)

    short_half = candidate.short_wall_width_mm / 2.0
    short = builder.polygon_sheet(
        hfss,
        "E1_thick_pifa_short_wall",
        vertical_wall_points(short_u, short_u, -short_half, short_half, 0.0, h, "u"),
        "copper",
    )
    metals.append(short.name)

    if candidate.side_fence_enabled and candidate.side_fence_length_mm > 0.2:
        fence_u0 = min(short_u + candidate.side_fence_start_from_short_mm, open_u - 0.45)
        fence_u1 = min(fence_u0 + candidate.side_fence_length_mm, open_u - 0.20)
        for side, v in [("pos", half_w), ("neg", -half_w)]:
            if fence_u1 > fence_u0 + 0.20:
                fence = builder.polygon_sheet(
                    hfss,
                    f"E1_thick_pifa_side_fence_{side}",
                    vertical_wall_points(fence_u0, fence_u1, v, v, 0.0, h, "v"),
                    "copper",
                )
                metals.append(fence.name)

    if candidate.open_lip_height_mm > 0.0 and candidate.open_lip_width_mm > 0.0:
        lip_half = min(candidate.open_lip_width_mm / 2.0, half_w)
        lip = builder.polygon_sheet(
            hfss,
            "E1_thick_pifa_open_edge_lip",
            vertical_wall_points(open_u, open_u, -lip_half, lip_half, h - candidate.open_lip_height_mm, h, "u"),
            "copper",
        )
        metals.append(lip.name)

    if candidate.open_edge_coupler_length_mm > 0.2 and candidate.open_edge_coupler_height_mm > 0.2:
        coupler_u0 = max(open_u - candidate.open_edge_coupler_length_mm, short_u + 0.30)
        coupler_z0 = max(0.0, h - candidate.open_edge_coupler_height_mm)
        for side, v in [("pos", half_w), ("neg", -half_w)]:
            coupler = builder.polygon_sheet(
                hfss,
                f"E1_thick_pifa_open_edge_coupler_{side}",
                vertical_wall_points(coupler_u0, open_u, v, v, coupler_z0, h, "v"),
                "copper",
            )
            metals.append(coupler.name)

    feed_u = -half_l + candidate.feed_from_short_mm
    feed_v = candidate.feed_v_mm
    matched_feed = (
        candidate.match_series_cap_pf > 0.0
        or candidate.match_series_ind_nh > 0.0
        or candidate.match_shunt_cap_pf > 0.0
        or candidate.match_shunt_ind_nh > 0.0
    )
    if matched_feed:
        gap = candidate.match_gap_mm
        island = candidate.match_island_size_mm
        island_v0 = half_w + gap
        island_v1 = island_v0 + island
        island_u0 = feed_u - island / 2.0
        island_u1 = feed_u + island / 2.0
        island_sheet = builder.polygon_sheet(
            hfss,
            "E1_thick_pifa_match_feed_island",
            builder.rectangle_points(0.0, 0.0, 0.0, island_u0, island_u1, island_v0, island_v1, h),
            "copper",
        )
        metals.append(island_sheet.name)
        feed_v = (island_v0 + island_v1) / 2.0
        metals.extend(
            builder.add_lumped_feed(
                hfss,
                "P1",
                (0.0, 0.0),
                0.0,
                feed_u,
                feed_v,
                h,
                0.0,
                params_dict(candidate),
                pad=False,
                port_width_axis="u",
            )
        )
        series_half = candidate.match_series_width_mm / 2.0
        series_sheet = builder.polygon_sheet(
            hfss,
            "E1_thick_pifa_series_match_sheet",
            builder.rectangle_points(0.0, 0.0, 0.0, feed_u - series_half, feed_u + series_half, half_w, island_v0, h),
            None,
        )
        hfss.assign_lumped_rlc_to_sheet(
            series_sheet.name,
            start_direction=[[feed_u, island_v0, h], [feed_u, half_w, h]],
            name="E1_thick_pifa_series_match",
            rlc_type="Serial",
            capacitance=candidate.match_series_cap_pf * 1e-12 if candidate.match_series_cap_pf > 0.0 else None,
            inductance=candidate.match_series_ind_nh * 1e-9 if candidate.match_series_ind_nh > 0.0 else None,
        )
        if candidate.match_shunt_cap_pf > 0.0 or candidate.match_shunt_ind_nh > 0.0:
            match_params = params_dict(candidate)
            match_params["rf_switch_off_resistance_ohm"] = 0.0
            match_params["rf_switch_off_capacitance_pf"] = candidate.match_shunt_cap_pf
            match_params["rf_switch_off_inductance_nh"] = candidate.match_shunt_ind_nh
            shunt_v = half_w if candidate.match_shunt_on_load_side else feed_v
            builder.add_lumped_switch_load(
                hfss,
                "E1_thick_pifa_shunt_match",
                (0.0, 0.0),
                0.0,
                feed_u,
                shunt_v,
                h,
                0.0,
                match_params,
                port_width_axis="u",
            )
    else:
        metals.extend(
            builder.add_lumped_feed(
                hfss,
                "P1",
                (0.0, 0.0),
                0.0,
                feed_u,
                feed_v,
                h,
                0.0,
                params_dict(candidate),
                pad=True,
                port_width_axis="v",
            )
        )
    return metals


def build_candidate(candidate: ThickPifaCandidate, analyze: bool, cores: int, tasks: int) -> dict[str, Path]:
    validate_candidate(candidate)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    paths = candidate_paths(candidate)
    builder.clean_outputs(paths)
    params = params_dict(candidate)
    builder.patch_pyaedt_empty_variable_lists()

    print(f"Stage: building {candidate.name}", flush=True)
    hfss = builder.Hfss(
        project=str(paths["project"]),
        design=DESIGN_NAME,
        solution_type="DrivenModal",
        version="2023.1",
        non_graphical=True,
        new_desktop=True,
        close_on_exit=False,
        remove_lock=True,
    )
    hfss.modeler.model_units = "mm"
    hfss.design_solutions._solution_type = builder.SolutionsHfss.DrivenModal

    substrate_material = builder.add_ro4350b(hfss, params)
    substrate = hfss.modeler.create_cylinder(
        "Z",
        [0, 0, 0],
        params["board_diameter_mm"] / 2.0,
        candidate.substrate_h_mm,
        num_sides=128,
        name="D44_THICK_PIFA_single_substrate",
        material=substrate_material,
    )
    substrate.transparency = 0.65
    ground = hfss.modeler.create_circle(
        "XY",
        [0, 0, 0],
        params["ground_radius_mm"],
        num_sides=128,
        name="D44_THICK_PIFA_bottom_ground",
        material="copper",
    )
    metal_names = [ground.name]
    metal_names.extend(add_thick_pifa_geometry(hfss, candidate))

    hfss.assign_perfecte_to_sheets(metal_names, name="D44_THICK_PIFA_PEC_metallization", is_infinite_ground=False)
    hfss.create_open_region(frequency=f"{params['air_frequency_ghz']}GHz", boundary="Radiation", apply_infinite_ground=False)
    hfss.insert_infinite_sphere(theta_start=0, theta_stop=90, theta_step=5, phi_start=0, phi_stop=360, phi_step=5, name=SPHERE)

    setup = hfss.create_setup(
        name="Setup_CH9",
        setup_type="HFSSDriven",
        Frequency=f"{params['freq_center_ghz']}GHz",
        MaximumPasses=5,
        MinimumPasses=2,
        MaxDeltaS=0.03,
        BasisOrder=1,
        PercentRefinement=30,
    )
    sweep = hfss.create_single_point_sweep(
        setup=setup.name,
        unit="GHz",
        freq=params["freq_center_ghz"],
        name="Sweep_CH9",
        save_single_field=True,
        save_fields=True,
        save_rad_fields=True,
    )
    builder.create_reports(hfss, setup.name, sweep.name, "D44_THICK_PIFA_SINGLE")

    total_height = candidate.substrate_h_mm + params["copper_t_mm"]
    notes = {
        "project": str(paths["project"]),
        "design": DESIGN_NAME,
        "candidate": asdict(candidate),
        "model": "Single-port thick-PCB shorted PIFA/quasi-cavity element at the original array phase-center reference.",
        "target": {
            "s11_db_max": RETURN_TARGET_DB,
            "theta_deg": [THETA_MIN_DEG, THETA_MAX_DEG],
            "azimuth_window_deg": AZIMUTH_WINDOW_DEG,
            "gain_total_min_dbi": GAIN_TARGET_DBI,
        },
        "height_constraint": f"PCB/topology height {total_height:.3f} mm <= {candidate.total_height_limit_mm:.3f} mm.",
        "manufacturing_note": "Uses top copper, etched current-path slots, and PCB short/side/open-edge walls that can be implemented with plated via walls or edge-plated slots; no separate L monopole arm is used.",
    }
    paths["params"].write_text(json.dumps(notes, indent=2, ensure_ascii=False), encoding="utf-8")
    builder.save_project_best_effort(hfss, "thick PIFA setup creation")
    hfss.release_desktop(close_projects=True, close_desktop=True)

    if analyze:
        print(f"Stage: solving {candidate.name}", flush=True)
        time.sleep(8.0)
        builder.remove_project_lock(paths["project"])
        ok = builder.pyaedt_solve_project(paths["project"], DESIGN_NAME, setup.name, paths["results"], cores, tasks)
        if not ok:
            ok = builder.batch_solve_project(paths["project"], DESIGN_NAME, setup.name, paths["results"])
        if not ok:
            raise RuntimeError(f"HFSS solve did not complete for {candidate.name}")
        time.sleep(5.0)
        builder.remove_project_lock(paths["project"])
    return paths


def native_export(candidate: ThickPifaCandidate, paths: dict[str, Path]) -> dict[str, Path]:
    safe_case = safe_slug(candidate.name)
    env = os.environ.copy()
    env.update(
        {
            "D44_AEDT_PROJECT": str(paths["project"]),
            "D44_AEDT_PROJECT_NAME": paths["project"].stem,
            "D44_AEDT_DESIGN": DESIGN_NAME,
            "D44_AEDT_SOLUTION": SOLUTION,
            "D44_AEDT_SPHERE": SPHERE,
            "D44_AEDT_CASE": safe_case,
            "D44_AEDT_OUT_DIR": str(REPORT_DIR),
            "D44_AEDT_FREQ_GHZ": "8",
        }
    )
    log_path = REPORT_DIR / f"{safe_case}_native_export.log"
    cmd = [str(builder.AEDT_EXE), "-ng", "-LogFile", str(log_path), "-RunScriptAndExit", str(NATIVE_EXPORT_SCRIPT)]
    subprocess.run(cmd, cwd=str(ROOT), env=env, check=True, timeout=360)
    return {
        "s": REPORT_DIR / f"{safe_case}_native_s_parameters.csv",
        "ff": REPORT_DIR / f"{safe_case}_native_farfield_default.csv",
        "sources": REPORT_DIR / f"{safe_case}_native_sources.txt",
        "log": log_path,
    }


def parse_s_csv(path: Path) -> dict[str, Any]:
    with path.open(newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        raise RuntimeError(f"Empty S-parameter CSV: {path}")
    values: list[tuple[float, float]] = []
    for row in rows:
        freq = float(row.get("Freq [GHz]", row.get("Freq", "8")))
        for key, value in row.items():
            if key and key.startswith("dB(S(") and value not in (None, ""):
                values.append((freq, float(value)))
    if not values:
        raise RuntimeError(f"No S11 data found in {path}")
    worst_freq, worst_db = max(values, key=lambda item: item[1])
    return {
        "s_csv": str(path),
        "s11_worst_db": worst_db,
        "s11_worst_freq_ghz": worst_freq,
        "s11_pass": worst_db <= RETURN_TARGET_DB,
    }


def parse_ff_rows(path: Path) -> list[dict[str, float]]:
    with path.open(newline="", encoding="utf-8-sig") as f:
        rows = list(csv.reader(f))
    if len(rows) < 2:
        raise RuntimeError(f"Empty far-field CSV: {path}")
    header = rows[0]
    phi_header_idx = next(idx for idx, name in enumerate(header) if name.startswith("Phi"))
    theta_header_idx = next(idx for idx, name in enumerate(header) if name.startswith("Theta"))
    gain_idx = next(idx for idx, name in enumerate(header) if "dB(GainTotal)" in name)
    data_rows = [row for row in rows[1:] if len(row) > max(phi_header_idx, theta_header_idx, gain_idx)]
    if not data_rows:
        raise RuntimeError(f"Empty far-field CSV: {path}")
    phi_values = [float(row[phi_header_idx]) for row in data_rows]
    theta_values = [float(row[theta_header_idx]) for row in data_rows]
    # Some AEDT native exports in this project swap the Phi/Theta labels.  Use
    # the value ranges so future optimization rows use the physical axes.
    if max(phi_values) <= 90.0 + 1e-9 and max(theta_values) > 180.0:
        theta_idx = phi_header_idx
        phi_idx = theta_header_idx
    else:
        phi_idx = phi_header_idx
        theta_idx = theta_header_idx
    parsed: list[dict[str, float]] = []
    for raw in data_rows:
        if len(raw) <= max(phi_idx, theta_idx, gain_idx):
            continue
        theta = float(raw[theta_idx])
        phi = float(raw[phi_idx]) % 360.0
        if abs(phi - 360.0) < 1e-9:
            phi = 0.0
        if THETA_MIN_DEG - 1e-9 <= theta <= THETA_MAX_DEG + 1e-9:
            parsed.append({"theta_deg": theta, "phi_deg": phi, "gain_total_dbi": float(raw[gain_idx])})
    if not parsed:
        raise RuntimeError(f"No Theta {THETA_MIN_DEG}..{THETA_MAX_DEG} rows found in {path}")
    return parsed


def window_metrics(rows: list[dict[str, float]]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    starts = sorted({row["phi_deg"] for row in rows if 0.0 <= row["phi_deg"] < 360.0})
    window_rows: list[dict[str, Any]] = []
    for start in starts:
        selected = []
        for row in rows:
            delta = (row["phi_deg"] - start) % 360.0
            if delta <= AZIMUTH_WINDOW_DEG + 1e-9:
                selected.append(row)
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
    default_window = min(window_rows, key=lambda item: abs(item["window_start_phi_deg"] - 0.0))
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
        "default_0_270deg_gain_total_min_dbi": default_window["gain_total_min_dbi"],
        "default_0_270deg_gain_total_min_theta_deg": default_window["gain_total_min_theta_deg"],
        "default_0_270deg_gain_total_min_phi_deg": default_window["gain_total_min_phi_deg"],
        "gain_pass": best_window["gain_total_min_dbi"] >= GAIN_TARGET_DBI,
    }
    return metrics, window_rows


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def read_csv(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def row_candidate_index(row: dict[str, Any]) -> int:
    try:
        return int(float(row.get("candidate_index", 999999)))
    except (TypeError, ValueError):
        return 999999


def sort_summary_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(rows, key=row_candidate_index)


def sort_window_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    def key(row: dict[str, Any]) -> tuple[int, float]:
        try:
            start_phi = float(row.get("window_start_phi_deg", 0.0))
        except (TypeError, ValueError):
            start_phi = 0.0
        return row_candidate_index(row), start_phi

    return sorted(rows, key=key)


def bool_value(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y", "达标"}
    return bool(value)


def complex_diag_path(candidate_name: str) -> Path:
    return REPORT_DIR / f"{safe_slug(candidate_name)}_complex_native_s_parameters.csv"


def read_complex_impedance(path: Path) -> dict[str, float] | None:
    if not path.exists():
        return None
    with path.open(newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        return None
    row = rows[0]
    re_key = next((key for key in row if key and key.startswith("re(Z(")), "")
    im_key = next((key for key in row if key and key.startswith("im(Z(")), "")
    if not re_key or not im_key:
        return None
    return {"re_z_ohm": float(row[re_key]), "im_z_ohm": float(row[im_key])}


def write_report_legacy(summary_rows: list[dict[str, Any]], best: dict[str, Any]) -> None:
    summary_rows = sort_summary_rows(summary_rows)
    best_s11_ok = bool_value(best["s11_pass"])
    best_gain_ok = bool_value(best["gain_pass"])
    s11_best = min(summary_rows, key=lambda row: float(row["s11_worst_db"]))
    gain_best = max(summary_rows, key=lambda row: float(row["best_270deg_gain_total_min_dbi"]))
    s11_margin_db = RETURN_TARGET_DB - float(s11_best["s11_worst_db"])
    s11_status_text = (
        f"已优于 `-10 dB` 目标约 `{s11_margin_db:.2f} dB`"
        if bool_value(s11_best["s11_pass"])
        else f"距离 `-10 dB` 目标仍差约 `{abs(s11_margin_db):.2f} dB`"
    )
    anchor_row = next((row for row in summary_rows if str(row.get("candidate_index", "")) == "23"), None)
    best_complex_diag = complex_diag_path(str(best["candidate"]))
    best_impedance = read_complex_impedance(best_complex_diag)
    lines = [
        "# D44 厚板短路 PIFA/腔体化单阵元验证报告",
        "",
        "## 目标与口径",
        "",
        f"- 验证对象：去除 A/B/L 后的单端口厚板短路 PIFA/准腔体阵元，单阵元相位中心放在阵元中心参考点。",
        f"- 匹配目标：`S11 <= {RETURN_TARGET_DB:.1f} dB`。",
        f"- 增益目标：Theta `{THETA_MIN_DEG:.0f}..{THETA_MAX_DEG:.0f} deg`，在最佳连续 `{AZIMUTH_WINDOW_DEG:.0f} deg` 方位窗口内 `GainTotal >= {GAIN_TARGET_DBI:.1f} dBi`。",
        "- 说明：本阶段只做单阵元可行性验证，不评估 4 阵元互耦、PDOA 单调性或整机遮挡。",
        "",
        "## 最佳候选",
        "",
        "- 选择口径：若没有候选同时满足 S11 和增益，则在增益达标候选中优先选择 S11 最接近目标的候选。",
        f"- 候选序号：`{best.get('candidate_index', 'N/A')}`。",
        f"- 候选：`{best['candidate']}`。",
        f"- S11 最差值：`{fmt(best['s11_worst_db'])} dB`。",
        f"- 最佳 270° 窗口：Phi `{fmt(best['best_270deg_window_start_phi_deg'], 0)}..{fmt(best['best_270deg_window_stop_phi_deg'], 0)} deg`。",
        f"- 最佳 270° 窗口最小 GainTotal：`{fmt(best['best_270deg_gain_total_min_dbi'])} dBi`，最差点 Theta `{fmt(best['best_270deg_gain_total_min_theta_deg'], 0)} deg` / Phi `{fmt(best['best_270deg_gain_total_min_phi_deg'], 0)} deg`。",
        f"- 全 360° 方位最小 GainTotal：`{fmt(best['all_phi_gain_total_min_dbi'])} dBi`。",
        "",
        "## 达标情况",
        "",
        f"- S11：`{'达标' if best_s11_ok else '未达标'}`。",
        f"- 270° 方位增益：`{'达标' if best_gain_ok else '未达标'}`。",
        f"- 综合结论：`{'达标' if best_s11_ok and best_gain_ok else '未完全达标'}`。",
        "",
        "## 复核结论",
        "",
        f"- 已完成候选数：`{len(summary_rows)}` 个，所有候选在 Theta `{THETA_MIN_DEG:.0f}..{THETA_MAX_DEG:.0f} deg`、最佳连续 `{AZIMUTH_WINDOW_DEG:.0f} deg` 方位窗口内均满足 `GainTotal >= {GAIN_TARGET_DBI:.1f} dBi`。",
        f"- S11 最优候选：`#{s11_best.get('candidate_index', 'N/A')} {s11_best['candidate']}`，S11 `{fmt(s11_best['s11_worst_db'])} dB`，{s11_status_text}。",
        f"- 增益最优候选：`#{gain_best.get('candidate_index', 'N/A')} {gain_best['candidate']}`，最佳 270° 窗口最小 GainTotal `{fmt(gain_best['best_270deg_gain_total_min_dbi'])} dBi`，但 S11 `{fmt(gain_best['s11_worst_db'])} dB`。",
        f"- 本轮有效路径是保持靠近开路端的真实几何馈电，同时把厚板高度从 `5.0 mm` 收敛到 `3.5 mm` 并保留 `4.0 mm` 短路墙、`6.0 mm` 侧墙；S11 从上一轮最佳 `{fmt(anchor_row['s11_worst_db']) if anchor_row else '-4.786'} dB` 推进到 `{fmt(best['s11_worst_db'])} dB`。",
        "- 外接匹配岛候选 11..16 已修正为 AEDT `Serial` 串联 RLC 写法，但 S11 对 L/C 数值不敏感，当前 lumped matching 拓扑不能作为达标签核依据。",
    ]
    if best_impedance:
        lines.append(
            f"- 最佳候选复阻抗诊断：`{best_complex_diag}`；8 GHz 端口约为 `{fmt(best_impedance['re_z_ohm'])} + j{fmt(best_impedance['im_z_ohm'])} ohm`。"
        )
    else:
        lines.append(f"- 最佳候选复阻抗诊断文件尚未导出：`{best_complex_diag}`。")
    lines.extend(
        [
            "",
            "## 候选汇总",
            "",
            "| # | 候选 | S11 worst dB | Best 270° min Gain dBi | All-phi min Gain dBi | 结果 |",
            "|---:|---|---:|---:|---:|---|",
        ]
    )
    for row in summary_rows:
        ok = bool_value(row["s11_pass"]) and bool_value(row["gain_pass"])
        lines.append(
            f"| {row.get('candidate_index', '')} | `{row['candidate']}` | {fmt(row['s11_worst_db'])} | {fmt(row['best_270deg_gain_total_min_dbi'])} | {fmt(row['all_phi_gain_total_min_dbi'])} | {'达标' if ok else '未达标'} |"
        )
    lines.extend(
        [
            "",
            "## 工程判断",
            "",
            "- 该方案避免了独立 4.8 mm L 单极子金属臂，制造上可转化为厚 PCB 顶层铜箔、短路 via wall/边镀墙和局部开口腔体。",
            "- 单阵元口径下，S11 和低仰角 270° 覆盖增益已经同时达标；低高度强短路墙 PIFA 是当前可继续推进的结构方向。",
            "- 下一步应把该单阵元扩展到 4 阵元，保持约 17 mm 相位中心间距并复核互耦、相位单调性、PDOA 模糊和人体/外壳遮挡。",
            "- 量产结构上仍建议优先使用 via wall/边镀墙和清晰 50 ohm 馈电过渡，避免回退到 A/B 贴片低仰角硬覆盖。",
            "",
            "## 输出文件",
            "",
            f"- 最佳 AEDT 工程：`{best.get('project', '')}`",
            f"- 候选汇总 CSV：`{SUMMARY_CSV}`",
            f"- 方位窗口 CSV：`{WINDOW_CSV}`",
            f"- 指标 JSON：`{METRICS_JSON}`",
        ]
    )
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def float_value(row: dict[str, Any], key: str, default: float = float("nan")) -> float:
    try:
        return float(row.get(key, default))
    except (TypeError, ValueError):
        return default


def pass_label(row: dict[str, Any]) -> str:
    return "达标" if bool_value(row.get("s11_pass")) and bool_value(row.get("gain_pass")) else "未达标"


def write_report(summary_rows: list[dict[str, Any]], best: dict[str, Any]) -> None:
    summary_rows = sort_summary_rows(summary_rows)
    s11_pass_count = sum(1 for row in summary_rows if bool_value(row.get("s11_pass")))
    gain_pass_count = sum(1 for row in summary_rows if bool_value(row.get("gain_pass")))
    both_pass_rows = [
        row for row in summary_rows if bool_value(row.get("s11_pass")) and bool_value(row.get("gain_pass"))
    ]
    s11_best = min(summary_rows, key=lambda row: float_value(row, "s11_worst_db", 999.0))
    gain_best = max(summary_rows, key=lambda row: float_value(row, "best_270deg_gain_total_min_dbi", -999.0))
    ranked_rows = sorted(summary_rows, key=rank_key, reverse=True)
    highlight_rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in [best, s11_best, gain_best] + ranked_rows[:10]:
        key = str(row.get("candidate_index", row.get("candidate", "")))
        if key not in seen:
            seen.add(key)
            highlight_rows.append(row)
    refreshed_count = sum(1 for row in summary_rows if row.get("refresh_status") == "refreshed")
    best_s11_gap = float_value(best, "s11_worst_db") - RETURN_TARGET_DB
    s11_best_gain_gap = GAIN_TARGET_DBI - float_value(s11_best, "best_270deg_gain_total_min_dbi")
    gain_best_s11_gap = float_value(gain_best, "s11_worst_db") - RETURN_TARGET_DB
    conclusion = (
        "本轮已找到双指标同时达标候选。"
        if both_pass_rows
        else "本轮低成本厚板 PIFA/边镀腔体电流路径扫描尚未找到 S11 与低仰角覆盖增益同时达标点。"
    )
    lines = [
        "# D44 厚板短路 PIFA 低成本优化复核报告",
        "",
        "## 目标口径",
        "",
        f"- 结构方向：厚 PCB 顶层铜、短路 via wall/边镀墙、开口槽、腔体边缘耦合与馈点联动；不使用独立 L 单极子金属臂。",
        f"- S11 目标：`S11 <= {RETURN_TARGET_DB:.1f} dB`。",
        f"- 增益目标：Theta `{THETA_MIN_DEG:.0f}..{THETA_MAX_DEG:.0f} deg`，最佳连续 `{AZIMUTH_WINDOW_DEG:.0f} deg` 方位窗口内 `GainTotal >= {GAIN_TARGET_DBI:.1f} dBi`。",
        "",
        "## 结论",
        "",
        f"- 综合结论：{conclusion}",
        f"- 已复核候选：`{len(summary_rows)}` 个；S11 达标 `{s11_pass_count}` 个，增益达标 `{gain_pass_count}` 个，双指标同时达标 `{len(both_pass_rows)}` 个。",
        f"- 当前排序候选：`#{best.get('candidate_index', 'N/A')} {best['candidate']}`，S11 `{fmt(best['s11_worst_db'])} dB`，最佳 270° 窗口最小 GainTotal `{fmt(best['best_270deg_gain_total_min_dbi'])} dBi`，结果 `{pass_label(best)}`。",
        f"- 当前排序候选距离 S11 目标仍差约 `{fmt(best_s11_gap)} dB`；说明高低仰角覆盖增益可以达标，但端口匹配仍是主瓶颈。",
        f"- S11 最优候选：`#{s11_best.get('candidate_index', 'N/A')} {s11_best['candidate']}`，S11 `{fmt(s11_best['s11_worst_db'])} dB`，最佳 270° 窗口最小 GainTotal `{fmt(s11_best['best_270deg_gain_total_min_dbi'])} dBi`。",
        f"- S11 最优候选距离增益目标仍差约 `{fmt(s11_best_gain_gap)} dB`；说明低高度强短路腔体容易匹配，但低仰角辐射不足。",
        f"- 增益最优候选：`#{gain_best.get('candidate_index', 'N/A')} {gain_best['candidate']}`，最佳 270° 窗口最小 GainTotal `{fmt(gain_best['best_270deg_gain_total_min_dbi'])} dBi`，S11 `{fmt(gain_best['s11_worst_db'])} dB`。",
        f"- 增益最优候选距离 S11 目标仍差约 `{fmt(gain_best_s11_gap)} dB`；说明继续单纯抬高/放宽口径会迅速牺牲匹配。",
        "",
        "## 数据复核",
        "",
        f"- 已从现有 native CSV 重新解析 `{refreshed_count}` 行，统一使用修正后的 Phi/Theta 轴判断。",
        "- 旧阶段部分行曾按 AEDT 导出标签直接读取，可能把 Phi/Theta 互换后的数据误判为低仰角覆盖；本报告以重新解析后的 CSV 为准。",
        "- 新增几何自由度覆盖：侧向 via wall/边镀墙起点、开路端耦合壁高度与长度、顶层中心槽、板边开口槽、开路端下翻 lip、馈点到短路墙距离。",
        "",
        "## 关键候选",
        "",
        "| # | 候选 | S11 worst dB | Best 270° min Gain dBi | All-phi min Gain dBi | 结果 |",
        "|---:|---|---:|---:|---:|---|",
    ]
    for row in highlight_rows:
        lines.append(
            f"| {row.get('candidate_index', '')} | `{row['candidate']}` | {fmt(row['s11_worst_db'])} | {fmt(row['best_270deg_gain_total_min_dbi'])} | {fmt(row['all_phi_gain_total_min_dbi'])} | {pass_label(row)} |"
        )
    lines.extend(
        [
            "",
            "## 工程判断",
            "",
            "- 8 mm PCB-only PIFA 能把最佳 270° 低仰角增益推到门限附近，但端口阻抗过高且强感性，L/C 匹配岛未能把 S11 拉进目标。",
            "- 3.5..4.5 mm 低高度族更容易满足或接近 S11，但最佳 270° 窗口增益明显低于目标，说明低仰角覆盖需要更强竖向/边缘电流。",
            "- 7.2..8.0 mm 高度族能满足低仰角 270° 覆盖增益，但 S11 远离 `-10 dB`，说明当前同相位中心厚板 PIFA 存在明确的匹配/覆盖折中。",
            "- 本轮新增几何路径仍保持低成本加工方式：顶层蚀刻槽、侧向 via wall 或边镀墙、开口端局部耦合壁，不引入独立折弯金属臂。",
            "",
            "## 输出文件",
            "",
            f"- 当前候选 AEDT 工程：`{best.get('project', '')}`",
            f"- 候选汇总 CSV：`{SUMMARY_CSV}`",
            f"- 方位窗口 CSV：`{WINDOW_CSV}`",
            f"- 指标 JSON：`{METRICS_JSON}`",
        ]
    )
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def evaluate_candidate(candidate: ThickPifaCandidate, cores: int, tasks: int) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    start = time.time()
    paths = build_candidate(candidate, analyze=True, cores=cores, tasks=tasks)
    exported = native_export(candidate, paths)
    s_metrics = parse_s_csv(exported["s"])
    ff_rows = parse_ff_rows(exported["ff"])
    gain_metrics, windows = window_metrics(ff_rows)
    row = {
        "candidate": candidate.name,
        "rationale": candidate.rationale,
        "elapsed_s": time.time() - start,
        "project": str(paths["project"]),
        "params_json": str(paths["params"]),
        "native_export_log": str(exported["log"]),
        **asdict(candidate),
        **s_metrics,
        **gain_metrics,
    }
    for item in windows:
        item["candidate"] = candidate.name
    return row, windows


def rank_key(row: dict[str, Any]) -> tuple[int, float, float]:
    s11_ok = bool_value(row["s11_pass"])
    gain_ok = bool_value(row["gain_pass"])
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


def run(candidate_indices: list[int], cores: int, tasks: int) -> dict[str, Any]:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    pool = candidates()
    if not candidate_indices:
        candidate_indices = list(range(1, len(pool) + 1))
    rerun_set = {str(index) for index in candidate_indices}
    summary_rows: list[dict[str, Any]] = [
        row for row in read_csv(SUMMARY_CSV) if str(row.get("candidate_index", "")) not in rerun_set
    ]
    window_rows: list[dict[str, Any]] = [
        row for row in read_csv(WINDOW_CSV) if str(row.get("candidate_index", "")) not in rerun_set
    ]
    for index in candidate_indices:
        if index < 1 or index > len(pool):
            raise ValueError(f"candidate index must be 1..{len(pool)}")
        candidate = pool[index - 1]
        print(f"=== Candidate {index}: {candidate.name} ===", flush=True)
        row, windows = evaluate_candidate(candidate, cores=cores, tasks=tasks)
        row["candidate_index"] = index
        for item in windows:
            item["candidate_index"] = index
        summary_rows.append(row)
        window_rows.extend(windows)
        write_csv(SUMMARY_CSV, sort_summary_rows(summary_rows))
        write_csv(WINDOW_CSV, sort_window_rows(window_rows))
    summary_rows = sort_summary_rows(summary_rows)
    window_rows = sort_window_rows(window_rows)
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
    print(f"Wrote {REPORT_MD}", flush=True)
    return payload


def refresh_existing_results() -> None:
    summary_rows = sort_summary_rows(read_csv(SUMMARY_CSV))
    existing_windows = sort_window_rows(read_csv(WINDOW_CSV))
    if not summary_rows:
        raise RuntimeError(f"No existing summary rows found in {SUMMARY_CSV}")
    windows_by_index: dict[str, list[dict[str, Any]]] = {}
    for item in existing_windows:
        windows_by_index.setdefault(str(item.get("candidate_index", "")), []).append(item)
    refreshed_rows: list[dict[str, Any]] = []
    refreshed_windows: list[dict[str, Any]] = []
    for row in summary_rows:
        name = str(row.get("candidate", "") or row.get("name", ""))
        index = str(row.get("candidate_index", ""))
        safe_case = safe_slug(name)
        s_path = REPORT_DIR / f"{safe_case}_native_s_parameters.csv"
        ff_path = REPORT_DIR / f"{safe_case}_native_farfield_default.csv"
        if s_path.exists() and ff_path.exists():
            try:
                row.update(parse_s_csv(s_path))
                gain_metrics, windows = window_metrics(parse_ff_rows(ff_path))
                row.update(gain_metrics)
                row["refresh_status"] = "refreshed"
                for item in windows:
                    item["candidate"] = name
                    item["candidate_index"] = index
                refreshed_windows.extend(windows)
            except Exception as exc:
                row["refresh_status"] = f"refresh_failed:{exc}"
                refreshed_windows.extend(windows_by_index.get(index, []))
        else:
            row["refresh_status"] = "missing_native_csv"
            refreshed_windows.extend(windows_by_index.get(index, []))
        refreshed_rows.append(row)
    refreshed_rows = sort_summary_rows(refreshed_rows)
    refreshed_windows = sort_window_rows(refreshed_windows)
    best = max(refreshed_rows, key=rank_key)
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
        "rows": refreshed_rows,
    }
    write_csv(SUMMARY_CSV, refreshed_rows)
    write_csv(WINDOW_CSV, refreshed_windows)
    METRICS_JSON.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    write_report(refreshed_rows, best)
    print(f"Wrote refreshed {REPORT_MD}", flush=True)


def regenerate_from_existing_results() -> None:
    summary_rows = sort_summary_rows(read_csv(SUMMARY_CSV))
    window_rows = sort_window_rows(read_csv(WINDOW_CSV))
    if not summary_rows:
        raise RuntimeError(f"No existing summary rows found in {SUMMARY_CSV}")
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
    print(f"Wrote {REPORT_MD}", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate-index", action="append", type=int, default=[], help="1-based candidate index. Repeat to run several; default runs all.")
    parser.add_argument("--cores", type=int, default=4)
    parser.add_argument("--tasks", type=int, default=4)
    parser.add_argument("--report-only", action="store_true", help="Regenerate JSON/Markdown reports from existing CSV files without running HFSS.")
    parser.add_argument("--refresh-existing", action="store_true", help="Reparse existing native S-parameter and far-field CSV files with the current metric logic.")
    args = parser.parse_args()
    if args.refresh_existing:
        refresh_existing_results()
        return
    if args.report_only:
        regenerate_from_existing_results()
        return
    run(args.candidate_index, args.cores, args.tasks)


if __name__ == "__main__":
    main()
