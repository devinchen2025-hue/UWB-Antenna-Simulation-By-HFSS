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
REPORT_DIR = ROOT / "reports_d44_me_dualpol_single_element"
STEM = "UWB_CH9_D44_ME_DUALPOL_SINGLE_ELEMENT"
DESIGN_NAME = "SingleElement_D44_ME_DualPol"
SOLUTION = "Setup_CH9 : Sweep_CH9"
SPHERE = "Upper_Hemisphere_5deg"
NATIVE_REPORT_SCRIPT = ROOT / "scripts" / "aedt_export_ch9_native_reports.py"
NATIVE_FIELD_SCRIPT = ROOT / "scripts" / "aedt_export_ch9_native_field_components.py"
AEDT_EXE = Path(r"D:\Program Files\AnsysEM\v231\Win64\ansysedt.exe")

THETA_MIN_DEG = 45.0
THETA_MAX_DEG = 90.0
PHI_WINDOW_DEG = 270.0
FREQ_GHZ = 8.0
RETURN_TARGET_DB = -10.0
GAIN_TARGET_DBI = -5.0
XPD_TARGET_DB = 25.0

SUMMARY_CSV = REPORT_DIR / f"{STEM}_summary.csv"
WINDOW_CSV = REPORT_DIR / f"{STEM}_window_summary.csv"
METRICS_JSON = REPORT_DIR / f"{STEM}_metrics.json"
REPORT_MD = REPORT_DIR / f"{STEM}_report.md"


@dataclass(frozen=True)
class MeCandidate:
    name: str
    rationale: str
    b_radiator: str = "pifa"
    substrate_h_mm: float = 3.5
    pifa_length_mm: float = 8.8
    pifa_width_mm: float = 8.0
    pifa_short_wall_width_mm: float = 4.0
    pifa_side_fence_length_mm: float = 6.0
    pifa_feed_from_short_mm: float = 8.4
    pifa_pair_offset_mm: float = 0.0
    monopole_cap_radius_mm: float = 4.2
    loop_side_mm: float = 10.4
    loop_trace_width_mm: float = 0.35
    loop_gap_mm: float = 0.55
    loop_air_gap_mm: float = 0.45
    ground_radius_mm: float = 21.4
    board_diameter_mm: float = 44.0
    total_height_limit_mm: float = 8.0
    feed_pad_radius_mm: float = 0.30
    port_width_mm: float = 0.55
    epsr: float = 3.48
    tan_delta: float = 0.0037


@dataclass(frozen=True)
class FieldPoint:
    theta_deg: float
    phi_deg: float
    etheta: complex
    ephi: complex


def candidates() -> list[MeCandidate]:
    return [
        MeCandidate(
            name="me_h3p5_loop10p4_gap0p55",
            rationale="同相位中心电-磁双模式首版：B端口沿用已达标厚板PIFA作为垂直电偶极近似，A端口增加水平环作为z向磁偶极近似。",
        ),
        MeCandidate(
            name="me_h3p5_loop12p0_gap0p55",
            rationale="加大水平磁环周长以提高H=Ephi通道辐射电阻和低仰角增益。",
            loop_side_mm=12.0,
        ),
        MeCandidate(
            name="me_h4p0_loop10p8_gap0p55",
            rationale="略增板厚和环-贴片间距，降低磁环与PIFA的近场耦合。",
            substrate_h_mm=4.0,
            loop_side_mm=10.8,
            loop_air_gap_mm=0.60,
            pifa_feed_from_short_mm=8.2,
        ),
        MeCandidate(
            name="me_sym_h5p5_cap3p8_loop8p8_air1p4",
            rationale="将B通道改为中心顶加载单极子以提高V极化方位对称性，同时抬高并缩小A环以接近z向磁偶极。",
            b_radiator="tophat",
            substrate_h_mm=5.5,
            monopole_cap_radius_mm=3.8,
            loop_side_mm=8.8,
            loop_trace_width_mm=0.22,
            loop_gap_mm=0.35,
            loop_air_gap_mm=1.4,
        ),
        MeCandidate(
            name="me_sym_h6p5_cap4p2_loop9p4_air1p0",
            rationale="进一步提高中心顶加载单极子高度和电容帽尺寸，并把环周长调到接近8GHz一波长附近。",
            b_radiator="tophat",
            substrate_h_mm=6.5,
            monopole_cap_radius_mm=4.2,
            loop_side_mm=9.4,
            loop_trace_width_mm=0.24,
            loop_gap_mm=0.35,
            loop_air_gap_mm=1.0,
        ),
        MeCandidate(
            name="cross_pifa_h3p5_l8p8_w8p0_feed8p40",
            rationale="使用更大的中心电容帽与更高环间距，测试V通道匹配和H通道去耦的折中点。",
            b_radiator="cross_pifa",
            substrate_h_mm=3.5,
            pifa_length_mm=8.8,
            pifa_width_mm=8.0,
            pifa_short_wall_width_mm=4.0,
            pifa_side_fence_length_mm=6.0,
            pifa_feed_from_short_mm=8.4,
            monopole_cap_radius_mm=5.0,
            loop_side_mm=10.0,
            loop_trace_width_mm=0.25,
            loop_gap_mm=0.30,
            loop_air_gap_mm=2.0,
        ),
        MeCandidate(
            name="cross_pifa_h4p0_l8p8_w8p0_feed8p40",
            rationale="Slightly taller co-located orthogonal PIFA pair to trade S11 margin for stronger low-elevation current.",
            b_radiator="cross_pifa",
            substrate_h_mm=4.0,
            pifa_length_mm=8.8,
            pifa_width_mm=8.0,
            pifa_short_wall_width_mm=4.0,
            pifa_side_fence_length_mm=6.0,
            pifa_feed_from_short_mm=8.4,
        ),
        MeCandidate(
            name="cross_pifa_h3p5_l9p2_w8p4_feed8p80",
            rationale="Longer and slightly wider orthogonal PIFA pair to recover match after the second orthogonal cavity is added.",
            b_radiator="cross_pifa",
            substrate_h_mm=3.5,
            pifa_length_mm=9.2,
            pifa_width_mm=8.4,
            pifa_short_wall_width_mm=4.0,
            pifa_side_fence_length_mm=6.0,
            pifa_feed_from_short_mm=8.8,
        ),
        MeCandidate(
            name="offset_pifa_h3p5_l8p8_sep9p0_feed8p40",
            rationale="Two independent orthogonal PIFAs separated inside the cell to avoid overlapping copper while keeping a calibratable local phase-center offset.",
            b_radiator="offset_cross_pifa",
            substrate_h_mm=3.5,
            pifa_length_mm=8.8,
            pifa_width_mm=8.0,
            pifa_short_wall_width_mm=4.0,
            pifa_side_fence_length_mm=6.0,
            pifa_feed_from_short_mm=8.4,
            pifa_pair_offset_mm=4.5,
        ),
        MeCandidate(
            name="offset_pifa_h3p5_l8p8_sep10p0_feed8p40",
            rationale="Increase A/B PIFA separation to reduce mutual loading and recover the single-port S11 behavior.",
            b_radiator="offset_cross_pifa",
            substrate_h_mm=3.5,
            pifa_length_mm=8.8,
            pifa_width_mm=8.0,
            pifa_short_wall_width_mm=4.0,
            pifa_side_fence_length_mm=6.0,
            pifa_feed_from_short_mm=8.4,
            pifa_pair_offset_mm=5.0,
        ),
        MeCandidate(
            name="offset_pifa_h4p0_l8p8_sep10p0_feed8p40",
            rationale="Use the separated pair with a 4.0 mm substrate height to check the gain/S11 trade.",
            b_radiator="offset_cross_pifa",
            substrate_h_mm=4.0,
            pifa_length_mm=8.8,
            pifa_width_mm=8.0,
            pifa_short_wall_width_mm=4.0,
            pifa_side_fence_length_mm=6.0,
            pifa_feed_from_short_mm=8.4,
            pifa_pair_offset_mm=5.0,
        ),
        MeCandidate(
            name="offset_pifa_h3p5_l8p8_sep12p0_feed8p40",
            rationale="Further separate the two PIFAs to reduce mutual loading while preserving the h=3.5 mm S11 margin.",
            b_radiator="offset_cross_pifa",
            substrate_h_mm=3.5,
            pifa_length_mm=8.8,
            pifa_width_mm=8.0,
            pifa_short_wall_width_mm=4.0,
            pifa_side_fence_length_mm=6.0,
            pifa_feed_from_short_mm=8.4,
            pifa_pair_offset_mm=6.0,
        ),
        MeCandidate(
            name="offset_pifa_h4p0_l8p8_sep12p0_feed8p40",
            rationale="Use the larger separation with h=4.0 mm to recover low-elevation gain and then inspect the S11 penalty.",
            b_radiator="offset_cross_pifa",
            substrate_h_mm=4.0,
            pifa_length_mm=8.8,
            pifa_width_mm=8.0,
            pifa_short_wall_width_mm=4.0,
            pifa_side_fence_length_mm=6.0,
            pifa_feed_from_short_mm=8.4,
            pifa_pair_offset_mm=6.0,
        ),
        MeCandidate(
            name="offset_pifa_h3p5_l8p8_sep14p0_feed8p40",
            rationale="Practical upper-bound spacing check for the offset pair before it becomes too large for the array cell.",
            b_radiator="offset_cross_pifa",
            substrate_h_mm=3.5,
            pifa_length_mm=8.8,
            pifa_width_mm=8.0,
            pifa_short_wall_width_mm=4.0,
            pifa_side_fence_length_mm=6.0,
            pifa_feed_from_short_mm=8.4,
            pifa_pair_offset_mm=7.0,
        ),
        MeCandidate(
            name="offset_pifa_h5p8_l8p6_sep10p0_feed7p80",
            rationale="Separated pair using the high-gain h=5.8 mm single-port feed point as the base geometry.",
            b_radiator="offset_cross_pifa",
            substrate_h_mm=5.8,
            pifa_length_mm=8.6,
            pifa_width_mm=8.0,
            pifa_short_wall_width_mm=4.0,
            pifa_side_fence_length_mm=4.0,
            pifa_feed_from_short_mm=7.8,
            pifa_pair_offset_mm=5.0,
        ),
        MeCandidate(
            name="offset_pifa_h6p5_l8p4_sep10p0_feed7p90",
            rationale="Separated pair using the strongest single-port low-elevation gain geometry as a dual-source stress test.",
            b_radiator="offset_cross_pifa",
            substrate_h_mm=6.5,
            pifa_length_mm=8.4,
            pifa_width_mm=8.0,
            pifa_short_wall_width_mm=4.0,
            pifa_side_fence_length_mm=4.0,
            pifa_feed_from_short_mm=7.9,
            pifa_pair_offset_mm=5.0,
        ),
        MeCandidate(
            name="offset_pifa_h6p5_l8p4_sep12p0_feed7p90",
            rationale="Higher-gain h=6.5 mm pair with larger separation to reduce mutual loading.",
            b_radiator="offset_cross_pifa",
            substrate_h_mm=6.5,
            pifa_length_mm=8.4,
            pifa_width_mm=8.0,
            pifa_short_wall_width_mm=4.0,
            pifa_side_fence_length_mm=4.0,
            pifa_feed_from_short_mm=7.9,
            pifa_pair_offset_mm=6.0,
        ),
        MeCandidate(
            name="mirror_pifa_h3p5_l8p8_sep17p0_feed8p40",
            rationale="Physically separated mirror-oriented PIFA pair; the two low-elevation units are calibrated as separate phase centers instead of forced co-located dual polarization.",
            b_radiator="offset_mirror_pifa",
            substrate_h_mm=3.5,
            pifa_length_mm=8.8,
            pifa_width_mm=8.0,
            pifa_short_wall_width_mm=4.0,
            pifa_side_fence_length_mm=6.0,
            pifa_feed_from_short_mm=8.4,
            pifa_pair_offset_mm=8.5,
        ),
        MeCandidate(
            name="mirror_pifa_h3p5_l8p8_sep19p0_feed8p40",
            rationale="Increase the physical separation of the mirror pair to reduce coupling while staying on the 44 mm board.",
            b_radiator="offset_mirror_pifa",
            substrate_h_mm=3.5,
            pifa_length_mm=8.8,
            pifa_width_mm=8.0,
            pifa_short_wall_width_mm=4.0,
            pifa_side_fence_length_mm=6.0,
            pifa_feed_from_short_mm=8.4,
            pifa_pair_offset_mm=9.5,
        ),
        MeCandidate(
            name="parallel_pifa_h3p5_l8p8_sep17p0_feed8p40",
            rationale="Physically separated parallel-oriented PIFA pair for checking whether identical unit orientation preserves the single-port low-elevation pattern better than mirror orientation.",
            b_radiator="offset_parallel_pifa",
            substrate_h_mm=3.5,
            pifa_length_mm=8.8,
            pifa_width_mm=8.0,
            pifa_short_wall_width_mm=4.0,
            pifa_side_fence_length_mm=6.0,
            pifa_feed_from_short_mm=8.4,
            pifa_pair_offset_mm=8.5,
        ),
        MeCandidate(
            name="mirror_pifa_h4p0_l8p8_sep17p0_feed8p40",
            rationale="Slightly taller mirror pair to test whether extra height recovers low-elevation gain after physical separation.",
            b_radiator="offset_mirror_pifa",
            substrate_h_mm=4.0,
            pifa_length_mm=8.8,
            pifa_width_mm=8.0,
            pifa_short_wall_width_mm=4.0,
            pifa_side_fence_length_mm=6.0,
            pifa_feed_from_short_mm=8.4,
            pifa_pair_offset_mm=8.5,
        ),
        MeCandidate(
            name="parallel_pifa_h5p8_l8p6_sep17p0_feed7p80",
            rationale="High-gain thick-board PIFA pair with the same side-by-side separation as the calibrated mirror pair.",
            b_radiator="offset_parallel_pifa",
            substrate_h_mm=5.8,
            pifa_length_mm=8.6,
            pifa_width_mm=8.0,
            pifa_short_wall_width_mm=4.0,
            pifa_side_fence_length_mm=4.0,
            pifa_feed_from_short_mm=7.8,
            pifa_pair_offset_mm=8.5,
        ),
        MeCandidate(
            name="parallel_pifa_h6p5_l8p4_sep17p0_feed7p90",
            rationale="Highest-gain thick-board PIFA pair with the same physical separation for a final gain check.",
            b_radiator="offset_parallel_pifa",
            substrate_h_mm=6.5,
            pifa_length_mm=8.4,
            pifa_width_mm=8.0,
            pifa_short_wall_width_mm=4.0,
            pifa_side_fence_length_mm=4.0,
            pifa_feed_from_short_mm=7.9,
            pifa_pair_offset_mm=8.5,
        ),
        MeCandidate(
            name="mirror_pifa_h5p8_l8p6_sep17p0_feed7p80",
            rationale="Mirror-oriented thick-board separated pair using the stronger h=5.8 mm single-port base geometry.",
            b_radiator="offset_mirror_pifa",
            substrate_h_mm=5.8,
            pifa_length_mm=8.6,
            pifa_width_mm=8.0,
            pifa_short_wall_width_mm=4.0,
            pifa_side_fence_length_mm=4.0,
            pifa_feed_from_short_mm=7.8,
            pifa_pair_offset_mm=8.5,
        ),
        MeCandidate(
            name="mirror_pifa_h6p5_l8p4_sep17p0_feed7p90",
            rationale="Mirror-oriented thick-board separated pair using the strongest low-elevation single-port base geometry.",
            b_radiator="offset_mirror_pifa",
            substrate_h_mm=6.5,
            pifa_length_mm=8.4,
            pifa_width_mm=8.0,
            pifa_short_wall_width_mm=4.0,
            pifa_side_fence_length_mm=4.0,
            pifa_feed_from_short_mm=7.9,
            pifa_pair_offset_mm=8.5,
        ),
    ]


def fmt(value: Any, digits: int = 3) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    if math.isnan(number) or math.isinf(number):
        return "N/A"
    return f"{number:.{digits}f}"


def safe_slug(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch in "-_." else "_" for ch in value).strip("._-")


def params_dict(candidate: MeCandidate) -> dict[str, float]:
    return {
        "freq_center_ghz": 8.0,
        "freq_start_ghz": 7.7,
        "freq_stop_ghz": 8.3,
        "freq_step_ghz": 0.02,
        "air_frequency_ghz": 7.0,
        "board_diameter_mm": candidate.board_diameter_mm,
        "ground_radius_mm": candidate.ground_radius_mm,
        "substrate_h_mm": candidate.substrate_h_mm,
        "copper_t_mm": 0.035,
        "total_height_limit_mm": candidate.total_height_limit_mm,
        "epsr": candidate.epsr,
        "tan_delta": candidate.tan_delta,
        "feed_pad_radius_mm": candidate.feed_pad_radius_mm,
        "port_width_mm": candidate.port_width_mm,
    }


def project_paths(candidate: MeCandidate, active_source: str) -> dict[str, Path]:
    slug = safe_slug(f"{candidate.name}_{active_source}")
    project = ROOT / f"{STEM}_{slug}.aedt"
    return {
        "project": project,
        "results": project.with_suffix(".aedtresults"),
        "pyaedt": project.with_suffix(".pyaedt"),
        "params": REPORT_DIR / f"{STEM}_{slug}_params.json",
    }


def wall_points(u0: float, u1: float, v0: float, v1: float, z0: float, z1: float, axis: str) -> list[list[float]]:
    if axis == "u":
        u = u0
        return [[u, v0, z0], [u, v1, z0], [u, v1, z1], [u, v0, z1]]
    if axis == "v":
        v = v0
        return [[u0, v, z0], [u1, v, z0], [u1, v, z1], [u0, v, z1]]
    raise ValueError(axis)


def rotated_wall_points(
    rot_deg: float,
    u0: float,
    u1: float,
    v0: float,
    v1: float,
    z0: float,
    z1: float,
    axis: str,
    center: tuple[float, float] = (0.0, 0.0),
) -> list[list[float]]:
    return [builder.local_to_global(center[0], center[1], rot_deg, u, v, z) for u, v, z in wall_points(u0, u1, v0, v1, z0, z1, axis)]


def add_oriented_pifa(
    hfss,
    candidate: MeCandidate,
    active_source: str,
    params: dict[str, float],
    port_name: str,
    rot_deg: float,
    prefix: str,
    center: tuple[float, float] = (0.0, 0.0),
) -> list[str]:
    h = candidate.substrate_h_mm
    half_l = candidate.pifa_length_mm / 2.0
    half_w = candidate.pifa_width_mm / 2.0
    metals: list[str] = []
    top = builder.polygon_sheet(
        hfss,
        f"{prefix}_top_plate",
        builder.rectangle_points(center[0], center[1], rot_deg, -half_l, half_l, -half_w, half_w, h),
        "copper",
    )
    metals.append(top.name)
    short_half = candidate.pifa_short_wall_width_mm / 2.0
    short = builder.polygon_sheet(
        hfss,
        f"{prefix}_short_wall",
        rotated_wall_points(rot_deg, -half_l, -half_l, -short_half, short_half, 0.0, h, "u", center),
        "copper",
    )
    metals.append(short.name)
    fence_u1 = min(-half_l + candidate.pifa_side_fence_length_mm, half_l - 0.2)
    for side, v in [("pos", half_w), ("neg", -half_w)]:
        fence = builder.polygon_sheet(
            hfss,
            f"{prefix}_side_fence_{side}",
            rotated_wall_points(rot_deg, -half_l, fence_u1, v, v, 0.0, h, "v", center),
            "copper",
        )
        metals.append(fence.name)
    feed_u = -half_l + candidate.pifa_feed_from_short_mm
    if active_source == port_name:
        metals.extend(builder.add_lumped_feed(hfss, port_name, center, rot_deg, feed_u, 0.0, h, 0.0, params, pad=True, port_width_axis="v"))
    else:
        load_params = dict(params)
        load_params["rf_switch_off_resistance_ohm"] = 50.0
        load_params["rf_switch_off_capacitance_pf"] = 0.0
        load_params["rf_switch_off_inductance_nh"] = 0.0
        builder.add_lumped_switch_load(hfss, f"{port_name}_load", center, rot_deg, feed_u, 0.0, h, 0.0, load_params, port_width_axis="v")
    return metals


def add_cross_pifa_pair(hfss, candidate: MeCandidate, active_source: str, params: dict[str, float]) -> list[str]:
    metals: list[str] = []
    metals.extend(add_oriented_pifa(hfss, candidate, active_source, params, "P1A", 90.0, "ME_A_cross_pifa"))
    metals.extend(add_oriented_pifa(hfss, candidate, active_source, params, "P1B", 0.0, "ME_B_cross_pifa"))
    return metals


def add_offset_cross_pifa_pair(hfss, candidate: MeCandidate, active_source: str, params: dict[str, float]) -> list[str]:
    offset = candidate.pifa_pair_offset_mm
    metals: list[str] = []
    metals.extend(add_oriented_pifa(hfss, candidate, active_source, params, "P1A", 90.0, "ME_A_offset_pifa", (-offset, 0.0)))
    metals.extend(add_oriented_pifa(hfss, candidate, active_source, params, "P1B", 0.0, "ME_B_offset_pifa", (offset, 0.0)))
    return metals


def add_offset_parallel_pifa_pair(hfss, candidate: MeCandidate, active_source: str, params: dict[str, float]) -> list[str]:
    offset = candidate.pifa_pair_offset_mm
    metals: list[str] = []
    metals.extend(add_oriented_pifa(hfss, candidate, active_source, params, "P1A", 0.0, "ME_A_parallel_pifa", (-offset, 0.0)))
    metals.extend(add_oriented_pifa(hfss, candidate, active_source, params, "P1B", 0.0, "ME_B_parallel_pifa", (offset, 0.0)))
    return metals


def add_offset_mirror_pifa_pair(hfss, candidate: MeCandidate, active_source: str, params: dict[str, float]) -> list[str]:
    offset = candidate.pifa_pair_offset_mm
    metals: list[str] = []
    metals.extend(add_oriented_pifa(hfss, candidate, active_source, params, "P1A", 180.0, "ME_A_mirror_pifa", (-offset, 0.0)))
    metals.extend(add_oriented_pifa(hfss, candidate, active_source, params, "P1B", 0.0, "ME_B_mirror_pifa", (offset, 0.0)))
    return metals


def add_pifa(hfss, candidate: MeCandidate, active_source: str, params: dict[str, float]) -> list[str]:
    h = candidate.substrate_h_mm
    half_l = candidate.pifa_length_mm / 2.0
    half_w = candidate.pifa_width_mm / 2.0
    metals: list[str] = []
    top = builder.polygon_sheet(
        hfss,
        "ME_B_pifa_top_plate",
        builder.rectangle_points(0.0, 0.0, 0.0, -half_l, half_l, -half_w, half_w, h),
        "copper",
    )
    metals.append(top.name)
    short_half = candidate.pifa_short_wall_width_mm / 2.0
    short = builder.polygon_sheet(
        hfss,
        "ME_B_pifa_short_wall",
        wall_points(-half_l, -half_l, -short_half, short_half, 0.0, h, "u"),
        "copper",
    )
    metals.append(short.name)
    fence_u1 = min(-half_l + candidate.pifa_side_fence_length_mm, half_l - 0.2)
    for side, v in [("pos", half_w), ("neg", -half_w)]:
        fence = builder.polygon_sheet(
            hfss,
            f"ME_B_pifa_side_fence_{side}",
            wall_points(-half_l, fence_u1, v, v, 0.0, h, "v"),
            "copper",
        )
        metals.append(fence.name)
    feed_u = -half_l + candidate.pifa_feed_from_short_mm
    if active_source == "P1B":
        metals.extend(builder.add_lumped_feed(hfss, "P1B", (0.0, 0.0), 0.0, feed_u, 0.0, h, 0.0, params, pad=True, port_width_axis="v"))
    else:
        load_params = dict(params)
        load_params["rf_switch_off_resistance_ohm"] = 50.0
        load_params["rf_switch_off_capacitance_pf"] = 0.0
        load_params["rf_switch_off_inductance_nh"] = 0.0
        builder.add_lumped_switch_load(hfss, "P1B_load", (0.0, 0.0), 0.0, feed_u, 0.0, h, 0.0, load_params, port_width_axis="v")
    return metals


def add_tophat_monopole(hfss, candidate: MeCandidate, active_source: str, params: dict[str, float]) -> list[str]:
    h = candidate.substrate_h_mm
    cap = hfss.modeler.create_circle(
        "XY",
        [0.0, 0.0, h],
        candidate.monopole_cap_radius_mm,
        num_sides=96,
        name="ME_B_tophat_monopole_cap",
        material="copper",
    )
    metals = [cap.name]
    if active_source == "P1B":
        metals.extend(
            builder.add_lumped_feed(
                hfss,
                "P1B",
                (0.0, 0.0),
                0.0,
                0.0,
                0.0,
                h,
                0.0,
                params,
                pad=False,
                port_width_axis="u",
            )
        )
    else:
        load_params = dict(params)
        load_params["rf_switch_off_resistance_ohm"] = 50.0
        load_params["rf_switch_off_capacitance_pf"] = 0.0
        load_params["rf_switch_off_inductance_nh"] = 0.0
        builder.add_lumped_switch_load(hfss, "P1B_load", (0.0, 0.0), 0.0, 0.0, 0.0, h, 0.0, load_params, port_width_axis="u")
    return metals


def add_loop_gap(hfss, name: str, candidate: MeCandidate, active: bool, params: dict[str, float]) -> None:
    z = candidate.substrate_h_mm + candidate.loop_air_gap_mm
    half = candidate.loop_side_mm / 2.0
    gap = candidate.loop_gap_mm
    trace = candidate.loop_trace_width_mm
    pts = builder.rectangle_points(0.0, 0.0, 0.0, half - trace / 2.0, half + trace / 2.0, -gap / 2.0, gap / 2.0, z)
    sheet = builder.polygon_sheet(hfss, f"{name}_loop_gap_sheet", pts, None)
    p0 = builder.local_to_global(0.0, 0.0, 0.0, half, -gap / 2.0, z)
    p1 = builder.local_to_global(0.0, 0.0, 0.0, half, gap / 2.0, z)
    if active:
        hfss.lumped_port(
            sheet.name,
            create_port_sheet=False,
            integration_line=[p0, p1],
            impedance=50,
            name=name,
            renormalize=True,
        )
    else:
        hfss.assign_lumped_rlc_to_sheet(
            sheet.name,
            start_direction=[p0, p1],
            name=f"{name}_loop_50ohm_load",
            rlc_type="Parallel",
            resistance=50.0,
        )


def add_magnetic_loop(hfss, candidate: MeCandidate, active_source: str, params: dict[str, float]) -> list[str]:
    z = candidate.substrate_h_mm + candidate.loop_air_gap_mm
    half = candidate.loop_side_mm / 2.0
    trace = candidate.loop_trace_width_mm
    gap = candidate.loop_gap_mm
    metals: list[str] = []

    def rect(name: str, u0: float, u1: float, v0: float, v1: float) -> None:
        sheet = builder.polygon_sheet(hfss, name, builder.rectangle_points(0.0, 0.0, 0.0, u0, u1, v0, v1, z), "copper")
        metals.append(sheet.name)

    rect("ME_A_loop_top_strip", -half, half, half - trace / 2.0, half + trace / 2.0)
    rect("ME_A_loop_bottom_strip", -half, half, -half - trace / 2.0, -half + trace / 2.0)
    rect("ME_A_loop_left_strip", -half - trace / 2.0, -half + trace / 2.0, -half, half)
    rect("ME_A_loop_right_upper_strip", half - trace / 2.0, half + trace / 2.0, gap / 2.0, half)
    rect("ME_A_loop_right_lower_strip", half - trace / 2.0, half + trace / 2.0, -half, -gap / 2.0)
    add_loop_gap(hfss, "P1A", candidate, active_source == "P1A", params)
    return metals


def validate(candidate: MeCandidate) -> None:
    separated_pifa_modes = {"cross_pifa", "offset_cross_pifa", "offset_parallel_pifa", "offset_mirror_pifa"}
    total_h = candidate.substrate_h_mm + (0.0 if candidate.b_radiator in separated_pifa_modes else candidate.loop_air_gap_mm) + 0.035
    if total_h > candidate.total_height_limit_mm:
        raise ValueError(f"{candidate.name}: total height {total_h:.2f} mm exceeds limit")
    if candidate.b_radiator not in separated_pifa_modes and candidate.loop_side_mm > candidate.ground_radius_mm * 1.2:
        raise ValueError(f"{candidate.name}: loop too large")
    if candidate.b_radiator not in {"pifa", "tophat", *separated_pifa_modes}:
        raise ValueError(f"{candidate.name}: unsupported B radiator {candidate.b_radiator}")
    if candidate.b_radiator in {"pifa", *separated_pifa_modes} and candidate.pifa_feed_from_short_mm >= candidate.pifa_length_mm - 0.2:
        raise ValueError(f"{candidate.name}: PIFA feed too close to open edge")
    if candidate.b_radiator == "tophat" and candidate.monopole_cap_radius_mm >= candidate.loop_side_mm / 2.0 - 0.2:
        raise ValueError(f"{candidate.name}: top-hat cap overlaps loop footprint")


def build_project(candidate: MeCandidate, active_source: str, analyze: bool, cores: int, tasks: int) -> dict[str, Path]:
    validate(candidate)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    paths = project_paths(candidate, active_source)
    builder.clean_outputs(paths)
    params = params_dict(candidate)
    builder.patch_pyaedt_empty_variable_lists()
    print(f"Stage: building {candidate.name} {active_source}", flush=True)
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
        candidate.board_diameter_mm / 2.0,
        candidate.substrate_h_mm,
        num_sides=128,
        name="D44_ME_single_substrate",
        material=substrate_material,
    )
    substrate.transparency = 0.65
    ground = hfss.modeler.create_circle(
        "XY",
        [0, 0, 0],
        candidate.ground_radius_mm,
        num_sides=128,
        name="D44_ME_bottom_ground",
        material="copper",
    )
    metals = [ground.name]
    if candidate.b_radiator == "cross_pifa":
        metals.extend(add_cross_pifa_pair(hfss, candidate, active_source, params))
    elif candidate.b_radiator == "offset_cross_pifa":
        metals.extend(add_offset_cross_pifa_pair(hfss, candidate, active_source, params))
    elif candidate.b_radiator == "offset_parallel_pifa":
        metals.extend(add_offset_parallel_pifa_pair(hfss, candidate, active_source, params))
    elif candidate.b_radiator == "offset_mirror_pifa":
        metals.extend(add_offset_mirror_pifa_pair(hfss, candidate, active_source, params))
    elif candidate.b_radiator == "pifa":
        metals.extend(add_pifa(hfss, candidate, active_source, params))
        metals.extend(add_magnetic_loop(hfss, candidate, active_source, params))
    else:
        metals.extend(add_tophat_monopole(hfss, candidate, active_source, params))
        metals.extend(add_magnetic_loop(hfss, candidate, active_source, params))
    hfss.assign_perfecte_to_sheets(metals, name="D44_ME_PEC_metallization", is_infinite_ground=False)
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
    builder.create_reports(hfss, setup.name, sweep.name, "D44_ME_DUALPOL_SINGLE")
    paths["params"].write_text(
        json.dumps(
            {
                "project": str(paths["project"]),
                "design": DESIGN_NAME,
                "active_source": active_source,
                "candidate": asdict(candidate),
                "model": "Single-element co-located electric/magnetic dual-mode radiator. P1A is a horizontal loop magnetic-dipole approximation; P1B is a shorted thick-PIFA or symmetric top-loaded electric-dipole approximation.",
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    builder.save_project_best_effort(hfss, "ME dualpol setup creation")
    hfss.release_desktop(close_projects=True, close_desktop=True)
    if analyze:
        print(f"Stage: solving {candidate.name} {active_source}", flush=True)
        time.sleep(8.0)
        builder.remove_project_lock(paths["project"])
        ok = builder.pyaedt_solve_project(paths["project"], DESIGN_NAME, setup.name, paths["results"], cores, tasks)
        if not ok:
            ok = builder.batch_solve_project(paths["project"], DESIGN_NAME, setup.name, paths["results"])
        if not ok:
            raise RuntimeError(f"HFSS solve did not complete for {candidate.name} {active_source}")
        time.sleep(5.0)
        builder.remove_project_lock(paths["project"])
    return paths


def native_export(candidate: MeCandidate, active_source: str, paths: dict[str, Path]) -> dict[str, Path]:
    case = safe_slug(f"{candidate.name}_{active_source}")
    env = os.environ.copy()
    env.update(
        {
            "D44_AEDT_PROJECT": str(paths["project"]),
            "D44_AEDT_PROJECT_NAME": paths["project"].stem,
            "D44_AEDT_DESIGN": DESIGN_NAME,
            "D44_AEDT_SOLUTION": SOLUTION,
            "D44_AEDT_SPHERE": SPHERE,
            "D44_AEDT_OUT_DIR": str(REPORT_DIR),
            "D44_AEDT_CASE": case,
            "D44_AEDT_FREQ_GHZ": f"{FREQ_GHZ:g}",
        }
    )
    report_log = REPORT_DIR / f"{case}_native_report_export.log"
    field_log = REPORT_DIR / f"{case}_native_field_export.log"
    subprocess.run([str(AEDT_EXE), "-ng", "-LogFile", str(report_log), "-RunScriptAndExit", str(NATIVE_REPORT_SCRIPT)], cwd=str(ROOT), env=env, check=True, timeout=420)
    subprocess.run([str(AEDT_EXE), "-ng", "-LogFile", str(field_log), "-RunScriptAndExit", str(NATIVE_FIELD_SCRIPT)], cwd=str(ROOT), env=env, check=True, timeout=420)
    return {
        "s": REPORT_DIR / f"{case}_native_s_parameters.csv",
        "ff": REPORT_DIR / f"{case}_native_farfield_default.csv",
        "field": REPORT_DIR / f"{case}_native_field_components.csv",
        "sources": REPORT_DIR / f"{case}_native_sources.txt",
        "report_log": report_log,
        "field_log": field_log,
    }


def parse_s_csv(path: Path) -> dict[str, Any]:
    with path.open(newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    values = []
    for row in rows:
        freq = float(next(iter(row.values())))
        for key, value in row.items():
            if key.startswith("dB(S("):
                values.append((key, freq, float(value)))
    if not values:
        raise RuntimeError(f"No S data in {path}")
    expr, freq, worst = max(values, key=lambda item: item[2])
    return {"s_csv": str(path), "s11_expr": expr, "s11_worst_freq_ghz": freq, "s11_worst_db": worst, "s11_pass": worst <= RETURN_TARGET_DB}


def parse_ff_csv(path: Path) -> list[dict[str, float]]:
    with path.open(newline="", encoding="utf-8-sig") as f:
        rows = list(csv.reader(f))
    header = rows[0]
    theta_idx = next(idx for idx, name in enumerate(header) if name.startswith("Theta"))
    phi_idx = next(idx for idx, name in enumerate(header) if name.startswith("Phi"))
    gain_idx = next(idx for idx, name in enumerate(header) if "dB(GainTotal)" in name)
    raw_angles = [(float(row[theta_idx]), float(row[phi_idx])) for row in rows[1:]]
    swapped = bool(raw_angles) and max(theta for theta, _ in raw_angles) > 180.0 and max(phi for _, phi in raw_angles) <= 180.0
    out = []
    for raw in rows[1:]:
        raw_theta = float(raw[theta_idx])
        raw_phi = float(raw[phi_idx])
        theta = raw_phi if swapped else raw_theta
        phi_raw = raw_theta if swapped else raw_phi
        if abs(phi_raw - 360.0) < 1e-9:
            continue
        phi = phi_raw % 360.0
        if THETA_MIN_DEG <= theta <= THETA_MAX_DEG:
            out.append({"theta_deg": theta, "phi_deg": phi, "gain_total_dbi": float(raw[gain_idx])})
    return out


def parse_field_csv(path: Path) -> list[dict[str, Any]]:
    with path.open(newline="", encoding="utf-8-sig") as f:
        rows = list(csv.reader(f))
    header = rows[0]
    theta_idx = next(idx for idx, name in enumerate(header) if name.startswith("Theta"))
    phi_idx = next(idx for idx, name in enumerate(header) if name.startswith("Phi"))
    re_t_idx = next(idx for idx, name in enumerate(header) if "re(rETheta)" in name)
    im_t_idx = next(idx for idx, name in enumerate(header) if "im(rETheta)" in name)
    re_p_idx = next(idx for idx, name in enumerate(header) if "re(rEPhi)" in name)
    im_p_idx = next(idx for idx, name in enumerate(header) if "im(rEPhi)" in name)
    raw_angles = [(float(row[theta_idx]), float(row[phi_idx])) for row in rows[1:]]
    swapped = bool(raw_angles) and max(theta for theta, _ in raw_angles) > 180.0 and max(phi for _, phi in raw_angles) <= 180.0
    out = []
    for raw in rows[1:]:
        raw_theta = float(raw[theta_idx])
        raw_phi = float(raw[phi_idx])
        theta = raw_phi if swapped else raw_theta
        phi_raw = raw_theta if swapped else raw_phi
        if abs(phi_raw - 360.0) < 1e-9:
            continue
        phi = phi_raw % 360.0
        if THETA_MIN_DEG <= theta <= THETA_MAX_DEG:
            etheta = complex(float(raw[re_t_idx]), float(raw[im_t_idx]))
            ephi = complex(float(raw[re_p_idx]), float(raw[im_p_idx]))
            h = ephi
            v = -etheta
            out.append({"theta_deg": theta, "phi_deg": phi, "h_mag": abs(h), "v_mag": abs(v)})
    return out


def existing_exports(candidate: MeCandidate, active_source: str) -> dict[str, Path]:
    case = safe_slug(f"{candidate.name}_{active_source}")
    return {
        "s": REPORT_DIR / f"{case}_native_s_parameters.csv",
        "ff": REPORT_DIR / f"{case}_native_farfield_default.csv",
        "field": REPORT_DIR / f"{case}_native_field_components.csv",
        "sources": REPORT_DIR / f"{case}_native_sources.txt",
        "report_log": REPORT_DIR / f"{case}_native_report_export.log",
        "field_log": REPORT_DIR / f"{case}_native_field_export.log",
    }


def in_window(phi: float, start: float) -> bool:
    return ((phi - start) % 360.0) <= PHI_WINDOW_DEG + 1e-9


def window_metrics(ff_rows: list[dict[str, float]], field_rows: list[dict[str, Any]], expected_basis: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    field_by_key = {(row["theta_deg"], row["phi_deg"]): row for row in field_rows}
    rows = []
    starts = sorted({row["phi_deg"] for row in ff_rows})
    for start in starts:
        selected_ff = [row for row in ff_rows if in_window(row["phi_deg"], start)]
        selected_field = [field_by_key[(row["theta_deg"], row["phi_deg"])] for row in selected_ff if (row["theta_deg"], row["phi_deg"]) in field_by_key]
        if not selected_ff or not selected_field:
            continue
        gain_worst = min(selected_ff, key=lambda row: row["gain_total_dbi"])
        if expected_basis == "H":
            xpd_values = [20.0 * math.log10(max(row["h_mag"], 1e-30) / max(row["v_mag"], 1e-30)) for row in selected_field]
        else:
            xpd_values = [20.0 * math.log10(max(row["v_mag"], 1e-30) / max(row["h_mag"], 1e-30)) for row in selected_field]
        rows.append(
            {
                "window_start_phi_deg": start,
                "window_stop_phi_deg": (start + PHI_WINDOW_DEG) % 360.0,
                "sample_count": len(selected_ff),
                "gain_total_min_dbi": gain_worst["gain_total_dbi"],
                "gain_total_min_theta_deg": gain_worst["theta_deg"],
                "gain_total_min_phi_deg": gain_worst["phi_deg"],
                "xpd_min_db": min(xpd_values),
                "xpd_p5_db": sorted(xpd_values)[max(0, math.ceil(len(xpd_values) * 0.05) - 1)],
                "xpd_median_db": sorted(xpd_values)[len(xpd_values) // 2],
            }
        )
    if not rows:
        raise RuntimeError("No window rows")
    best = max(rows, key=lambda row: (row["xpd_p5_db"], row["gain_total_min_dbi"]))
    return best, rows


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    fields = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def evaluate(candidate: MeCandidate, active_source: str, cores: int, tasks: int, reuse_existing: bool = False) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    paths = project_paths(candidate, active_source)
    exported = existing_exports(candidate, active_source)
    required = [paths["project"], paths["params"], exported["s"], exported["ff"], exported["field"]]
    if not reuse_existing or not all(path.exists() for path in required):
        paths = build_project(candidate, active_source, analyze=True, cores=cores, tasks=tasks)
        exported = native_export(candidate, active_source, paths)
    s_metrics = parse_s_csv(exported["s"])
    ff_rows = parse_ff_csv(exported["ff"])
    field_rows = parse_field_csv(exported["field"])
    expected = "H" if active_source.endswith("A") else "V"
    best_window, windows = window_metrics(ff_rows, field_rows, expected)
    row = {
        "candidate": candidate.name,
        "active_source": active_source,
        "expected_basis": expected,
        "project": str(paths["project"]),
        "params_json": str(paths["params"]),
        "field_csv": str(exported["field"]),
        "ff_csv": str(exported["ff"]),
        **asdict(candidate),
        **s_metrics,
        **{f"best_{key}": value for key, value in best_window.items()},
    }
    row["source_pass"] = row["s11_pass"] and row["best_gain_total_min_dbi"] >= GAIN_TARGET_DBI and row["best_xpd_min_db"] >= XPD_TARGET_DB
    for item in windows:
        item["candidate"] = candidate.name
        item["active_source"] = active_source
    return row, windows


def write_report(summary_rows: list[dict[str, Any]]) -> None:
    best = max(summary_rows, key=lambda row: (float(row["best_xpd_p5_db"]), float(row["best_gain_total_min_dbi"]), -float(row["s11_worst_db"])))
    all_pass = summary_rows and all(bool(row["source_pass"]) for row in summary_rows)
    lines = [
        "# D44 电-磁双模式单阵元验证报告",
        "",
        "## 目标与结构",
        "",
        "- 目标：把双极化测角从现有 A/B/L 混合源转向同相位中心的物理正交双模式单元。",
        "- A端口：水平环，近似 z 向磁偶极，目标局部 `H = Ephi`。",
        "- B端口：厚板短路 PIFA 或中心顶加载单极子，近似 z 向电偶极，目标局部 `V = -Etheta`。",
        f"- 单源门限：S11 `<= {RETURN_TARGET_DB:.1f} dB`，最佳 `{PHI_WINDOW_DEG:.0f}°` 低仰角窗口 GainTotal `>= {GAIN_TARGET_DBI:.1f} dBi`，局部 XPD min `>= {XPD_TARGET_DB:.1f} dB`。",
        "",
        "## 当前最佳源",
        "",
        f"- 候选：`{best['candidate']}` / `{best['active_source']}`，目标极化 `{best['expected_basis']}`。",
        f"- S11：`{fmt(best['s11_worst_db'])} dB`。",
        f"- 最佳窗口：Phi `{fmt(best['best_window_start_phi_deg'], 0)}..{fmt(best['best_window_stop_phi_deg'], 0)} deg`。",
        f"- GainTotal min：`{fmt(best['best_gain_total_min_dbi'])} dBi`。",
        f"- XPD：min `{fmt(best['best_xpd_min_db'])} dB`，P5 `{fmt(best['best_xpd_p5_db'])} dB`。",
        f"- 综合结论：`{'达标' if all_pass else '未达标'}`。",
        "",
        "## 源级结果",
        "",
        "| 候选 | 源 | 目标极化 | S11 | Gain min | XPD min | XPD P5 | 结论 |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: | --- |",
    ]
    for row in summary_rows:
        lines.append(
            f"| `{row['candidate']}` | `{row['active_source']}` | `{row['expected_basis']}` | {fmt(row['s11_worst_db'])} | "
            f"{fmt(row['best_gain_total_min_dbi'])} | {fmt(row['best_xpd_min_db'])} | {fmt(row['best_xpd_p5_db'])} | "
            f"{'达标' if row['source_pass'] else '未达标'} |"
        )
    lines.extend(
        [
            "",
            "## 工程判断",
            "",
            "- 这是结构级首版验证，不再依赖 A/B/L 现有贴片源的线性组合。",
            "- 若 A 环或 B 电偶极任一源未达标，下一步优先分别调环周长/间隙/高度与 B 通道馈点/顶加载/短路结构，再扩展到四阵元并计算完整 2x2 条件数和 PDOA。",
            "",
            "## 输出文件",
            "",
            f"- 汇总 CSV：`{SUMMARY_CSV}`",
            f"- 窗口 CSV：`{WINDOW_CSV}`",
            f"- 指标 JSON：`{METRICS_JSON}`",
        ]
    )
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def bool_value(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y", "达标"}
    return bool(value)


def decode_gbk_mojibake(value: str) -> str:
    try:
        return value.encode("latin1").decode("gbk")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return value


def write_report_cn(summary_rows: list[dict[str, Any]]) -> None:
    if not summary_rows:
        return
    best = max(
        summary_rows,
        key=lambda row: (
            float(row["best_xpd_p5_db"]),
            float(row["best_gain_total_min_dbi"]),
            -float(row["s11_worst_db"]),
        ),
    )
    all_pass = all(bool_value(row["source_pass"]) for row in summary_rows)
    lines = [
        "# D44 电-磁双模式单阵元验证报告",
        "",
        "## 目标与结构",
        "",
        "- 目标：把双极化测角从现有 A/B/L 混合源转向同相位中心的物理正交双模式单元。",
        "- A 端口：水平环，近似 z 向磁偶极，目标局部极化为 `H = Ephi`。",
        "- B 端口：厚板短路 PIFA 或中心顶加载单极子，近似 z 向电偶极，目标局部极化为 `V = -Etheta`。",
        f"- 单源门限：S11 `<= {RETURN_TARGET_DB:.1f} dB`，最佳连续 `{PHI_WINDOW_DEG:.0f} deg` 低仰角窗口 GainTotal `>= {GAIN_TARGET_DBI:.1f} dBi`，局部 XPD min `>= {XPD_TARGET_DB:.1f} dB`。",
        "",
        "## 当前最佳源",
        "",
        f"- 候选：`{best['candidate']}` / `{best['active_source']}`，目标极化 `{best['expected_basis']}`。",
        f"- S11：`{fmt(best['s11_worst_db'])} dB`。",
        f"- 最佳窗口：Phi `{fmt(best['best_window_start_phi_deg'], 0)}..{fmt(best['best_window_stop_phi_deg'], 0)} deg`。",
        f"- GainTotal min：`{fmt(best['best_gain_total_min_dbi'])} dBi`。",
        f"- XPD：min `{fmt(best['best_xpd_min_db'])} dB`，P5 `{fmt(best['best_xpd_p5_db'])} dB`。",
        f"- 综合结论：`{'达标' if all_pass else '未达标'}`。",
        "",
        "## 源级结果",
        "",
        "| 候选 | 源 | 目标极化 | S11 | Gain min | XPD min | XPD P5 | 结论 |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: | --- |",
    ]
    for row in summary_rows:
        lines.append(
            f"| `{row['candidate']}` | `{row['active_source']}` | `{row['expected_basis']}` | {fmt(row['s11_worst_db'])} | "
            f"{fmt(row['best_gain_total_min_dbi'])} | {fmt(row['best_xpd_min_db'])} | {fmt(row['best_xpd_p5_db'])} | "
            f"{'达标' if bool_value(row['source_pass']) else '未达标'} |"
        )
    lines.extend(
        [
            "",
            "## 工程判断",
            "",
            "- 这是结构级验证，不再依赖 A/B/L 现有贴片源的线性组合。",
            "- 若 A 环或 B 电偶极任一源未达标，下一步优先分别调环周长/间隙/高度，以及 B 通道馈点/顶加载/短路结构，再扩展到四阵元并计算完整 2x2 条件数和 PDOA。",
            "",
            "## 输出文件",
            "",
            f"- 汇总 CSV：`{SUMMARY_CSV}`",
            f"- 窗口 CSV：`{WINDOW_CSV}`",
            f"- 指标 JSON：`{METRICS_JSON}`",
        ]
    )
    REPORT_MD.write_text("\n".join(decode_gbk_mojibake(line) for line in lines) + "\n", encoding="utf-8")


def run(candidate_indices: list[int], sources: list[str], cores: int, tasks: int, reuse_existing: bool = False) -> dict[str, Any]:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    pool = candidates()
    summary_rows: list[dict[str, Any]] = []
    window_rows: list[dict[str, Any]] = []
    for index in candidate_indices or [1]:
        candidate = pool[index - 1]
        for source in sources:
            print(f"=== ME candidate {index} {candidate.name} {source} ===", flush=True)
            row, windows = evaluate(candidate, source, cores, tasks, reuse_existing=reuse_existing)
            row["candidate_index"] = index
            for item in windows:
                item["candidate_index"] = index
            summary_rows.append(row)
            window_rows.extend(windows)
            write_csv(SUMMARY_CSV, summary_rows)
            write_csv(WINDOW_CSV, window_rows)
    payload = {
        "target": {
            "s11_db_max": RETURN_TARGET_DB,
            "theta_deg": [THETA_MIN_DEG, THETA_MAX_DEG],
            "azimuth_window_deg": PHI_WINDOW_DEG,
            "gain_total_min_dbi": GAIN_TARGET_DBI,
            "xpd_min_db": XPD_TARGET_DB,
        },
        "summary_rows": summary_rows,
        "summary_csv": str(SUMMARY_CSV),
        "window_csv": str(WINDOW_CSV),
        "report_md": str(REPORT_MD),
    }
    METRICS_JSON.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    write_report_cn(summary_rows)
    print(json.dumps({"report": str(REPORT_MD), "rows": len(summary_rows)}, indent=2, ensure_ascii=False), flush=True)
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate-index", action="append", type=int, default=[])
    parser.add_argument("--source", action="append", choices=["P1A", "P1B"], default=[])
    parser.add_argument("--cores", type=int, default=8)
    parser.add_argument("--tasks", type=int, default=8)
    parser.add_argument("--reuse-existing", action="store_true", help="Reuse existing project and exported CSV files when available.")
    args = parser.parse_args()
    run(args.candidate_index, args.source or ["P1A", "P1B"], args.cores, args.tasks, reuse_existing=args.reuse_existing)


if __name__ == "__main__":
    main()
