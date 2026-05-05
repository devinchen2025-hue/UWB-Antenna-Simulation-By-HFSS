from __future__ import annotations

import argparse
import csv
import json
import math
import shutil
import time
from dataclasses import dataclass
from pathlib import Path
from statistics import fmean
from typing import Any

import numpy as np
from ansys.aedt.core import Hfss

import build_uwb_ch9_hfss_d44_topology as builder
import evaluate_uwb_ch9_d44_dualpol as dualpol_eval
import evaluate_uwb_ch9_d44_pdoa_linear_polarization as pdoa_eval
import evaluate_uwb_ch9_d44_topology as topology_eval
import optimize_uwb_ch9_d44_dualpol_feed_network as mirror_opt


ROOT = Path(__file__).resolve().parents[1]
TOPOLOGY = "dualpol"
REPORT_DIR = ROOT / "reports_d44_dualpol_slotcoupled_pattern_cal_opt"
STEM = "UWB_CH9_D44_DUALPOL_SLOTCAL"
SPARAM_CSV = REPORT_DIR / f"{STEM}_sparam_screening.csv"
FULL_CSV = REPORT_DIR / f"{STEM}_full_validation.csv"
BEST_JSON = REPORT_DIR / f"{STEM}_best.json"
BEST_CURVES_CSV = REPORT_DIR / f"{STEM}_best_curves.csv"
BEST_SUMMARY_CSV = REPORT_DIR / f"{STEM}_best_summary.csv"
BEST_CAL_CURVES_CSV = REPORT_DIR / f"{STEM}_best_calibrated_curves.csv"
BEST_CAL_SUMMARY_CSV = REPORT_DIR / f"{STEM}_best_calibrated_summary.csv"
BEST_PHASE_CENTER_CSV = REPORT_DIR / f"{STEM}_best_phase_center.csv"
BEST_PATTERN_TABLE_CSV = REPORT_DIR / f"{STEM}_best_complex_pattern_table.csv"
BEST_PATTERN_TABLE_JSON = REPORT_DIR / f"{STEM}_best_complex_pattern_table.json"
REPORT_MD = REPORT_DIR / f"{STEM}_optimization_report.md"

RETURN_TARGET_DB = -10.0
XY_ISOLATION_TARGET_DB = 15.0
SAME_FEED_ISOLATION_TARGET_DB = 16.0
RETURN_BALANCE_TARGET_DB = 0.5
XY_MAG_BALANCE_TARGET_DB = 2.0
XY_PHASE_SPREAD_TARGET_DEG = 30.0
PDOA_RMS_TARGET_DEG = 10.0
PDOA_MAX_TARGET_DEG = 20.0
PATTERN_SYMMETRY_TARGET_DB = 3.0
PHASE_CENTER_RMS_TARGET_DEG = 20.0

LINEAR_POLS = [0.0, 45.0, 90.0, 135.0]
PHI_CUTS = [45.0, 60.0, 75.0, 90.0]

STRUCTURE_KEYS = [
    "patch_side_mm",
    "feed_offset_u_mm",
    "feed_pad_radius_mm",
    "port_width_mm",
    "microstrip_feed_enabled",
    "microstrip_feedline_length_mm",
    "microstrip_feedline_width_mm",
    "microstrip_match_length_mm",
    "microstrip_match_width_mm",
    "microstrip_transform2_length_mm",
    "microstrip_transform2_width_mm",
    "microstrip_feed_mirror_enabled",
    "dualpol_parasitic_enabled",
    "parasitic_side_mm",
    "parasitic_corner_cut_mm",
    "parasitic_rotation_deg",
    "parasitic_offset_u_mm",
    "parasitic_offset_v_mm",
    "air_gap_mm",
    "dualpol_slotcoupled_enabled",
    "feed_substrate_h_mm",
    "slot_coupled_aperture_length_a_mm",
    "slot_coupled_aperture_length_b_mm",
    "slot_coupled_aperture_width_mm",
    "slot_coupled_offset_a_mm",
    "slot_coupled_offset_b_mm",
    "slot_coupled_aperture_center_a_v_mm",
    "slot_coupled_aperture_center_b_u_mm",
    "slot_coupled_feedline_length_mm",
    "slot_coupled_feedline_width_mm",
    "slot_coupled_feedline_offset_a_v_mm",
    "slot_coupled_feedline_offset_b_u_mm",
    "neutralization_branch_enabled",
    "local_dgs_enabled",
    "isolation_slot_enabled",
    "isolation_slot_length_mm",
    "isolation_slot_width_mm",
    "isolation_slot_inner_mm",
]

BASE_PARAMS: dict[str, Any] = dict(builder.TOPOLOGIES[TOPOLOGY]["params"])
BASE_PARAMS.update(
    {
        "patch_side_mm": 9.35,
        "corner_cut_mm": 0.0,
        "feed_offset_u_mm": 3.40,
        "feed_offset_v_mm": 0.0,
        "feed_pad_radius_mm": 0.28,
        "port_width_mm": 0.50,
        "microstrip_feed_enabled": 0.0,
        "microstrip_feed_offset_mm": 0.0,
        "microstrip_feedline_length_mm": 1.78,
        "microstrip_feedline_width_mm": 0.58,
        "microstrip_match_length_mm": 0.48,
        "microstrip_match_width_mm": 0.34,
        "microstrip_transform2_length_mm": 0.55,
        "microstrip_transform2_width_mm": 0.50,
        "microstrip_stub_length_mm": 0.0,
        "microstrip_stub_width_mm": 0.24,
        "microstrip_stub_offset_mm": 0.60,
        "microstrip_feed_mirror_enabled": 1.0,
        "neutralization_branch_enabled": 0.0,
        "neutralization_branch_length_mm": 0.85,
        "neutralization_branch_width_mm": 0.12,
        "neutralization_branch_offset_mm": 0.65,
        "local_dgs_enabled": 0.0,
        "local_dgs_length_mm": 3.6,
        "local_dgs_width_mm": 0.18,
        "local_dgs_offset_mm": 0.75,
        "dualpol_parasitic_enabled": 0.0,
        "parasitic_side_mm": 0.0,
        "parasitic_corner_cut_mm": 0.0,
        "parasitic_rotation_deg": 0.0,
        "parasitic_offset_u_mm": 0.0,
        "parasitic_offset_v_mm": 0.0,
        "air_gap_mm": 0.0,
        "dualpol_slotcoupled_enabled": 1.0,
        "feed_substrate_h_mm": 0.254,
        "slot_coupled_aperture_length_a_mm": 3.6,
        "slot_coupled_aperture_length_b_mm": 3.6,
        "slot_coupled_aperture_width_mm": 0.45,
        "slot_coupled_offset_a_mm": 0.0,
        "slot_coupled_offset_b_mm": 0.0,
        "slot_coupled_aperture_center_a_v_mm": 0.0,
        "slot_coupled_aperture_center_b_u_mm": 0.0,
        "slot_coupled_feedline_length_mm": 10.0,
        "slot_coupled_feedline_width_mm": 0.60,
        "slot_coupled_feedline_offset_a_v_mm": 0.0,
        "slot_coupled_feedline_offset_b_u_mm": 0.0,
        "weak_coupling_open_line_enabled": 0.0,
        "via_fence_enabled": 0.0,
        "isolation_slot_enabled": 1.0,
        "isolation_slot_length_mm": 10.0,
        "isolation_slot_width_mm": 0.42,
        "isolation_slot_inner_mm": 3.20,
    }
)


@dataclass(frozen=True)
class Candidate:
    name: str
    params: dict[str, Any]
    rationale: str
    slotcoupled_enabled: bool


def fmt(value: float | int | None, digits: int = 2) -> str:
    return mirror_opt.fmt(value, digits)


def write_csv(path: Path, rows: list[dict], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        return
    fields = fieldnames or list(rows[0])
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    key: f"{row[key]:.6f}" if isinstance(row.get(key), float) else row.get(key, "")
                    for key in fields
                }
            )


def read_csv(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def make_candidate(name: str, rationale: str, slotcoupled_enabled: bool = True, **overrides: Any) -> Candidate:
    params = dict(BASE_PARAMS)
    params.update(overrides)
    params["dualpol_slotcoupled_enabled"] = 1.0 if slotcoupled_enabled else 0.0
    if slotcoupled_enabled:
        params["microstrip_feed_enabled"] = 0.0
    return Candidate(name=name, params=params, rationale=rationale, slotcoupled_enabled=slotcoupled_enabled)


def parasitic_extra(
    *,
    side: float,
    gap: float,
    corner: float = 0.0,
    rotation: float = 0.0,
    offset_u: float = 0.0,
    offset_v: float = 0.0,
) -> dict[str, float]:
    return {
        "dualpol_parasitic_enabled": 1.0,
        "parasitic_side_mm": side,
        "parasitic_corner_cut_mm": corner,
        "parasitic_rotation_deg": rotation,
        "parasitic_offset_u_mm": offset_u,
        "parasitic_offset_v_mm": offset_v,
        "air_gap_mm": gap,
    }


def slot_extra(
    *,
    length: float,
    width: float,
    feed_width: float,
    feed_h: float = 0.254,
    feed_length: float = 10.0,
    offset: float = 0.0,
    length_b: float | None = None,
    offset_b: float | None = None,
    center_a_v: float = 0.0,
    center_b_u: float = 0.0,
    feed_offset_a_v: float = 0.0,
    feed_offset_b_u: float = 0.0,
) -> dict[str, float]:
    return {
        "dualpol_slotcoupled_enabled": 1.0,
        "feed_substrate_h_mm": feed_h,
        "slot_coupled_aperture_length_a_mm": length,
        "slot_coupled_aperture_length_b_mm": length if length_b is None else length_b,
        "slot_coupled_aperture_width_mm": width,
        "slot_coupled_offset_a_mm": offset,
        "slot_coupled_offset_b_mm": offset if offset_b is None else offset_b,
        "slot_coupled_aperture_center_a_v_mm": center_a_v,
        "slot_coupled_aperture_center_b_u_mm": center_b_u,
        "slot_coupled_feedline_length_mm": feed_length,
        "slot_coupled_feedline_width_mm": feed_width,
        "slot_coupled_feedline_offset_a_v_mm": feed_offset_a_v,
        "slot_coupled_feedline_offset_b_u_mm": feed_offset_b_u,
    }


def candidates() -> list[Candidate]:
    network = mirror_opt.network_extra(
        line_len=1.78,
        line_width=0.58,
        match_len=0.48,
        match_width=0.34,
        transform2_len=0.55,
        transform2_width=0.50,
    )
    raw = [
        make_candidate(
            "stacked_reference_prev",
            "上一轮最优叠层寄生贴片真实网络参考，用于判断缝隙耦合窗口是否带来净收益。",
            slotcoupled_enabled=False,
            patch_side_mm=9.15,
            **network,
            **parasitic_extra(side=9.75, gap=1.20),
        ),
        make_candidate(
            "slot_sep_l4p4_w0p65_h0p18_feed0p75",
            "A/B 孔缝和下层馈线分离布置，缩短中心交叉耦合路径，并用更近的下层馈线增强孔缝耦合。",
            patch_side_mm=9.35,
            **slot_extra(length=4.4, width=0.65, feed_width=0.75, feed_h=0.18, center_a_v=-1.55, center_b_u=1.55, feed_offset_a_v=-1.55, feed_offset_b_u=1.55),
        ),
        make_candidate(
            "slot_sep_l5p0_w0p70_h0p18_feed0p80_patch9p55",
            "放大贴片并加长分离孔缝，优先提升耦合强度和回波匹配。",
            patch_side_mm=9.55,
            **slot_extra(length=5.0, width=0.70, feed_width=0.80, feed_h=0.18, center_a_v=-1.55, center_b_u=1.55, feed_offset_a_v=-1.55, feed_offset_b_u=1.55),
        ),
        make_candidate(
            "slot_sep_l4p8_w0p70_h0p10_feed0p80",
            "进一步拉近下层馈线到接地缝的距离，检查耦合不足是否来自下层介质过厚。",
            patch_side_mm=9.55,
            **slot_extra(length=4.8, width=0.70, feed_width=0.80, feed_h=0.10, center_a_v=-1.50, center_b_u=1.50, feed_offset_a_v=-1.50, feed_offset_b_u=1.50),
        ),
        make_candidate(
            "slot_sep_l4p4_w0p65_h0p18_par9p75",
            "分离孔缝上方叠加弱寄生贴片，尝试在增强耦合后恢复方向图对称性。",
            patch_side_mm=9.15,
            **slot_extra(length=4.4, width=0.65, feed_width=0.75, feed_h=0.18, center_a_v=-1.50, center_b_u=1.50, feed_offset_a_v=-1.50, feed_offset_b_u=1.50),
            **parasitic_extra(side=9.75, gap=0.80),
        ),
        make_candidate(
            "slot_sep_l5p2_w0p75_h0p18_feed0p85",
            "强耦合分离孔缝上限候选，用于判断当前结构能否把回波拉回可优化区间。",
            patch_side_mm=9.55,
            **slot_extra(length=5.2, width=0.75, feed_width=0.85, feed_h=0.18, center_a_v=-1.45, center_b_u=1.45, feed_offset_a_v=-1.45, feed_offset_b_u=1.45),
        ),
        make_candidate(
            "slot_l3p2_w0p40_feed0p55_patch9p35",
            "小缝隙窗口和窄下层馈线，优先验证弱耦合窗口是否能保住端口匹配。",
            patch_side_mm=9.35,
            **slot_extra(length=3.2, width=0.40, feed_width=0.55),
        ),
        make_candidate(
            "slot_l3p6_w0p45_feed0p60",
            "中等正交缝隙窗口和 0.60 mm 下层馈线，作为本轮主候选。",
            patch_side_mm=9.35,
            **slot_extra(length=3.6, width=0.45, feed_width=0.60),
        ),
        make_candidate(
            "slot_l4p0_w0p50_feed0p60",
            "加长缝隙窗口提高耦合强度，观察回波和同阵元隔离的平衡点。",
            patch_side_mm=9.35,
            **slot_extra(length=4.0, width=0.50, feed_width=0.60),
        ),
        make_candidate(
            "slot_l4p4_w0p55_feed0p65",
            "更强耦合窗口和较宽馈线，用于检查槽耦合匹配上限。",
            patch_side_mm=9.35,
            **slot_extra(length=4.4, width=0.55, feed_width=0.65),
        ),
        make_candidate(
            "slot_l3p6_sep0p25",
            "A/B 两个正交槽轻微错开，降低同阵元端口互耦。",
            patch_side_mm=9.35,
            **slot_extra(length=3.6, width=0.45, feed_width=0.60, offset=0.25, offset_b=-0.25),
        ),
        make_candidate(
            "slot_l4p0_sep0p35",
            "较长槽配更大错位，优先改善 A/B 隔离和相位中心一致性。",
            patch_side_mm=9.35,
            **slot_extra(length=4.0, width=0.50, feed_width=0.60, offset=0.35, offset_b=-0.35),
        ),
        make_candidate(
            "slot_l3p6_lower0p508",
            "加厚下层馈电介质，降低下层微带对接地槽的过强加载。",
            patch_side_mm=9.35,
            **slot_extra(length=3.6, width=0.45, feed_width=0.60, feed_h=0.508),
        ),
        make_candidate(
            "slot_l3p6_par9p75_gap0p80",
            "缝隙耦合窗口上方保留弱叠层寄生片，尝试用上层孔径改善方向图对称性。",
            patch_side_mm=9.15,
            **slot_extra(length=3.6, width=0.45, feed_width=0.60),
            **parasitic_extra(side=9.75, gap=0.80),
        ),
        make_candidate(
            "slot_l4p0_patch9p55",
            "放大上层辐射贴片并使用较强槽耦合，检查谐振点下移后的匹配空间。",
            patch_side_mm=9.55,
            **slot_extra(length=4.0, width=0.50, feed_width=0.65),
        ),
    ]
    valid: list[Candidate] = []
    for item in raw:
        full_params = dict(builder.BASE_PARAMS)
        full_params.update(item.params)
        try:
            builder.validate_params(full_params)
            valid.append(item)
        except Exception as exc:
            print(f"Skip invalid {item.name}: {exc}", flush=True)
    return valid


def apply_candidate(item: Candidate) -> None:
    params = builder.TOPOLOGIES[TOPOLOGY].setdefault("params", {})
    params.clear()
    params.update(item.params)


def build_and_open(sparam_only: bool) -> tuple[Path, Hfss]:
    return builder.build_project(
        TOPOLOGY,
        analyze=True,
        non_graphical=True,
        quick=True,
        band_samples=True,
        sparam_only=sparam_only,
        return_hfss=True,
    )


def bool_value(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).lower() in {"1", "true", "yes"}


def sparam_score(row: dict) -> float:
    ret = float(row["worst_return_db"])
    iso = float(row["same_element_xy_isolation_db"])
    same_feed_iso = float(row["same_feed_inter_element_isolation_db"])
    balance = float(row["xy_return_balance_db"])
    return_gap = max(0.0, ret - RETURN_TARGET_DB)
    iso_gap = max(0.0, XY_ISOLATION_TARGET_DB - iso)
    same_feed_gap = max(0.0, SAME_FEED_ISOLATION_TARGET_DB - same_feed_iso)
    balance_gap = max(0.0, balance - RETURN_BALANCE_TARGET_DB)
    slot_bonus = -1.0 if bool_value(row.get("slotcoupled_enabled")) else 0.0
    return 8.0 * return_gap + 5.0 * iso_gap + 2.0 * same_feed_gap + 4.0 * balance_gap + slot_bonus


def sparam_screen(item: Candidate, index: int) -> dict:
    started = time.time()
    apply_candidate(item)
    _project, hfss = build_and_open(sparam_only=True)
    try:
        sparams = topology_eval.get_s_parameter_snapshot(hfss, REPORT_DIR / f"{item.name}_s_parameters.csv")
        extra = dualpol_eval.enrich_sparams(sparams)
    finally:
        hfss.release_desktop(close_projects=False, close_desktop=True)

    x_return = extra["x_return_worst_db"]
    y_return = extra["y_return_worst_db"]
    row = {
        "index": index,
        "candidate": item.name,
        "slotcoupled_enabled": item.slotcoupled_enabled,
        "elapsed_s": time.time() - started,
        "rationale": item.rationale,
        "worst_return_db": sparams["worst_return_db"],
        "isolation_db": sparams["isolation_db"],
        "worst_return_expr": sparams["worst_return_expr"],
        "worst_coupling_expr": sparams["worst_coupling_expr"],
        "x_return_worst_db": x_return,
        "y_return_worst_db": y_return,
        "xy_return_balance_db": abs(x_return - y_return),
        "same_element_xy_isolation_db": extra["same_element_xy_isolation_db"],
        "same_feed_inter_element_isolation_db": extra["same_feed_inter_element_isolation_db"],
    }
    for key in STRUCTURE_KEYS:
        row[key] = item.params.get(key, "")
    row["score"] = sparam_score(row)
    print(json.dumps(row, indent=2, ensure_ascii=False), flush=True)
    return row


def direction_xy(theta_deg: float, phi_deg: float) -> tuple[float, float]:
    theta = math.radians(theta_deg)
    phi = math.radians(phi_deg)
    return math.sin(theta) * math.cos(phi), math.sin(theta) * math.sin(phi)


def nominal_positions(params: dict) -> dict[int, tuple[float, float]]:
    radius = params["element_spacing_mm"] / math.sqrt(2.0)
    return {
        1: (radius, 0.0),
        2: (0.0, radius),
        3: (-radius, 0.0),
        4: (0.0, -radius),
    }


def vector_pdoa_deg(
    fields_by_source: dict[str, dict[tuple[float, float], pdoa_eval.FieldPoint]],
    left: int,
    right: int,
    point_key: tuple[float, float],
    pol_deg: float,
) -> tuple[float, float, float]:
    left_vec = mirror_opt.measured_vector(fields_by_source, left, point_key, pol_deg)
    right_vec = mirror_opt.measured_vector(fields_by_source, right, point_key, pol_deg)
    left_mag = float(np.linalg.norm(left_vec))
    right_mag = float(np.linalg.norm(right_vec))
    pair_phase = np.vdot(right_vec, left_vec)
    return pdoa_eval.wrap_deg(pdoa_eval.phase_deg(pair_phase)), left_mag, right_mag


def phase_center_metrics(fields: dict, eval_freqs: list[float], sources: list[str], params: dict) -> tuple[list[dict], dict]:
    elements = dualpol_eval.element_pairs(sources)
    baselines = dualpol_eval.baseline_pairs(elements)
    positions = nominal_positions(params)
    rows: list[dict] = []
    raw_all: list[float] = []
    calibrated_all: list[float] = []
    correction_magnitudes: list[float] = []
    k0 = 360.0 / 299.792458

    for freq in eval_freqs:
        fkey = pdoa_eval.freq_key(freq)
        fields_by_source = {source: fields[source][fkey] for source in sources}
        all_points = next(iter(fields_by_source.values()))
        theta_values = sorted({point.theta_deg for point in all_points.values()})
        phi_values = sorted({point.phi_deg for point in all_points.values()})
        selected_phi = [phi for phi in PHI_CUTS if any(abs(phi - item) < 1e-6 for item in phi_values)]
        k_deg_per_mm = k0 * freq

        for left, right in baselines:
            left_pos = positions[left]
            right_pos = positions[right]
            sample_rows: list[dict] = []
            group_values: dict[str, list[tuple[dict, float]]] = {}

            for phi in selected_phi:
                for pol in LINEAR_POLS:
                    group_key = f"phi{phi:.1f}_pol{pol:.1f}"
                    wrapped_group: list[tuple[dict, float]] = []
                    for theta in theta_values:
                        point_key = (round(theta, 9), round(phi, 9))
                        if point_key not in all_points:
                            continue
                        measured, left_mag, right_mag = vector_pdoa_deg(fields_by_source, left, right, point_key, pol)
                        if left_mag <= 1e-12 or right_mag <= 1e-12:
                            continue
                        ux, uy = direction_xy(theta, phi)
                        nominal = k_deg_per_mm * ((left_pos[0] - right_pos[0]) * ux + (left_pos[1] - right_pos[1]) * uy)
                        residual = pdoa_eval.wrap_deg(measured - nominal)
                        row = {
                            "freq_ghz": freq,
                            "baseline": f"E{left}-E{right}",
                            "phi_deg": phi,
                            "linear_pol_deg": pol,
                            "theta_deg": theta,
                            "ux": ux,
                            "uy": uy,
                            "measured_pdoa_deg": measured,
                            "nominal_pdoa_deg": pdoa_eval.wrap_deg(nominal),
                            "raw_residual_wrapped_deg": residual,
                            "left_mag": left_mag,
                            "right_mag": right_mag,
                            "group": group_key,
                        }
                        wrapped_group.append((row, residual))
                    if len(wrapped_group) >= 2:
                        unwrapped = pdoa_eval.unwrap_degrees([value for _row, value in wrapped_group])
                        group_values[group_key] = [(row, value) for (row, _wrapped), value in zip(wrapped_group, unwrapped)]

            group_keys = sorted(group_values)
            for group_key, values in group_values.items():
                mean_residual = fmean(value for _row, value in values)
                for row, value in values:
                    row["raw_residual_unwrapped_deg"] = value
                    row["raw_residual_centered_deg"] = value - mean_residual
                    sample_rows.append(row)

            feature_count = 2 + len(group_keys)
            if len(sample_rows) < feature_count + 3:
                continue

            group_index = {group: idx for idx, group in enumerate(group_keys)}
            matrix = np.zeros((len(sample_rows), feature_count), dtype=np.float64)
            observed = np.zeros(len(sample_rows), dtype=np.float64)
            for idx, row in enumerate(sample_rows):
                matrix[idx, 0] = k_deg_per_mm * row["ux"]
                matrix[idx, 1] = k_deg_per_mm * row["uy"]
                matrix[idx, 2 + group_index[row["group"]]] = 1.0
                observed[idx] = row["raw_residual_unwrapped_deg"]

            coeffs, _residuals, _rank, _singular = np.linalg.lstsq(matrix, observed, rcond=None)
            predicted = matrix @ coeffs
            correction_magnitudes.append(float(math.hypot(coeffs[0], coeffs[1])))

            baseline_raw = []
            baseline_cal = []
            for row, predicted_value in zip(sample_rows, predicted):
                calibrated = row["raw_residual_unwrapped_deg"] - float(predicted_value)
                row["phase_center_delta_x_mm"] = float(coeffs[0])
                row["phase_center_delta_y_mm"] = float(coeffs[1])
                row["phase_center_delta_mag_mm"] = float(math.hypot(coeffs[0], coeffs[1]))
                row["calibrated_residual_deg"] = calibrated
                rows.append(row)
                baseline_raw.append(row["raw_residual_centered_deg"])
                baseline_cal.append(calibrated)

            raw_all.extend(baseline_raw)
            calibrated_all.extend(baseline_cal)

    raw_abs = [abs(value) for value in raw_all]
    cal_abs = [abs(value) for value in calibrated_all]
    metrics = {
        "phase_center_sample_count": len(calibrated_all),
        "phase_center_raw_rms_deg": math.sqrt(fmean(value * value for value in raw_all)) if raw_all else 0.0,
        "phase_center_raw_p95_deg": dualpol_eval.percentile(raw_abs, 95.0),
        "phase_center_calibrated_rms_deg": math.sqrt(fmean(value * value for value in calibrated_all)) if calibrated_all else 0.0,
        "phase_center_calibrated_p95_deg": dualpol_eval.percentile(cal_abs, 95.0),
        "phase_center_calibrated_max_abs_deg": max(cal_abs) if cal_abs else 0.0,
        "phase_center_delta_mag_mean_mm": fmean(correction_magnitudes) if correction_magnitudes else 0.0,
        "phase_center_delta_mag_max_mm": max(correction_magnitudes) if correction_magnitudes else 0.0,
    }
    return rows, metrics


def source_element_feed(source: str) -> tuple[int, str]:
    digits = "".join(ch for ch in source if ch.isdigit())
    feed = source[-1] if source else ""
    return int(digits) if digits else 0, feed


def complex_pattern_table(fields: dict, eval_freqs: list[float], sources: list[str]) -> tuple[list[dict], dict]:
    rows: list[dict] = []
    theta_values: set[float] = set()
    phi_values: set[float] = set()
    for freq in eval_freqs:
        fkey = pdoa_eval.freq_key(freq)
        for source in sorted(sources, key=lambda item: source_element_feed(item)):
            element, feed = source_element_feed(source)
            for point in fields[source][fkey].values():
                theta_values.add(point.theta_deg)
                phi_values.add(point.phi_deg)
                row = {
                    "freq_ghz": freq,
                    "source": source,
                    "element": element,
                    "feed": feed,
                    "theta_deg": point.theta_deg,
                    "phi_deg": point.phi_deg,
                    "etheta_re": point.etheta.real,
                    "etheta_im": point.etheta.imag,
                    "ephi_re": point.ephi.real,
                    "ephi_im": point.ephi.imag,
                    "gain_proxy_mag": math.sqrt(abs(point.etheta) ** 2 + abs(point.ephi) ** 2),
                }
                for pol in LINEAR_POLS:
                    projection = dualpol_eval.linear_projection(point, pol)
                    label = str(int(pol))
                    row[f"linpol{label}_re"] = projection.real
                    row[f"linpol{label}_im"] = projection.imag
                    row[f"linpol{label}_mag"] = abs(projection)
                    row[f"linpol{label}_phase_deg"] = pdoa_eval.phase_deg(projection)
                rows.append(row)
    meta = {
        "description": "Per-element embedded complex far-field calibration table. Use source/element/feed plus freq/theta/phi as lookup keys.",
        "coordinate_system": "HFSS far-field rETheta/rEPhi on Upper_Hemisphere_5deg.",
        "linear_polarizations_deg": LINEAR_POLS,
        "frequencies_ghz": eval_freqs,
        "sources": sorted(sources, key=lambda item: source_element_feed(item)),
        "theta_count": len(theta_values),
        "phi_count": len(phi_values),
        "row_count": len(rows),
        "columns": list(rows[0]) if rows else [],
    }
    return rows, meta


def full_score(row: dict) -> float:
    return (
        row["sparam_score"]
        + 0.25 * row["dualpol_vector_avg_rms_bias_deg"]
        + 0.55 * row["calibrated_avg_rms_bias_deg"]
        + 0.12 * row["calibrated_p95_rms_bias_deg"]
        + 0.02 * row["calibrated_max_abs_bias_deg"]
        + 1.75 * row["pattern_symmetry_rms_db"]
        + 1.00 * row["xy_mag_imbalance_rms_db"]
        + 0.04 * row["xy_phase_spread_rms_deg"]
        + 0.45 * row["phase_center_calibrated_rms_deg"]
        + 0.08 * row["phase_center_calibrated_p95_deg"]
    )


def full_validate(item: Candidate) -> dict:
    started = time.time()
    apply_candidate(item)
    _project, hfss = build_and_open(sparam_only=False)
    try:
        sources = hfss.get_all_sources()
        sparams = topology_eval.get_s_parameter_snapshot(hfss, REPORT_DIR / f"{item.name}_full_s_parameters.csv")
        extra = dualpol_eval.enrich_sparams(sparams)
        eval_freqs = pdoa_eval.nearest_frequencies(pdoa_eval.get_available_frequencies(hfss))
        fields = pdoa_eval.acquire_embedded_fields(hfss, sources, eval_freqs)
        curves, summaries, pdoa_metrics = dualpol_eval.evaluate_dualpol_pdoa(fields, eval_freqs, sources)
        cal_curves, cal_summaries, cal_metrics, cal_quality = mirror_opt.evaluate_calibrated_pdoa(fields, eval_freqs, sources)
        balance = mirror_opt.xy_balance_metrics(fields, eval_freqs, sources)
        symmetry = mirror_opt.pattern_symmetry_metrics(fields, eval_freqs, sources)
        full_params = dict(builder.BASE_PARAMS)
        full_params.update(item.params)
        phase_rows, phase_metrics = phase_center_metrics(fields, eval_freqs, sources, full_params)
        pattern_rows, pattern_meta = complex_pattern_table(fields, eval_freqs, sources)
    finally:
        hfss.release_desktop(close_projects=False, close_desktop=True)

    curve_fields = [
        "freq_ghz",
        "phi_deg",
        "theta_deg",
        "linear_pol_deg",
        "strategy",
        "baseline",
        "pdoa_deg",
        "pdoa_unwrapped_deg",
        "left_mag_rel_db",
        "right_mag_rel_db",
        "valid",
    ]
    summary_fields = [
        "freq_ghz",
        "phi_deg",
        "linear_pol_deg",
        "strategy",
        "baseline",
        "valid_percent",
        "pdoa_span_deg",
        "pdoa_start_deg",
        "pdoa_end_deg",
        "monotonic_segment_percent",
        "min_pair_mag_rel_db",
        "rms_bias_vs_pol0_deg",
        "mean_abs_bias_vs_pol0_deg",
        "max_abs_bias_vs_pol0_deg",
    ]
    phase_fields = [
        "freq_ghz",
        "baseline",
        "phi_deg",
        "linear_pol_deg",
        "theta_deg",
        "measured_pdoa_deg",
        "nominal_pdoa_deg",
        "raw_residual_wrapped_deg",
        "raw_residual_unwrapped_deg",
        "raw_residual_centered_deg",
        "phase_center_delta_x_mm",
        "phase_center_delta_y_mm",
        "phase_center_delta_mag_mm",
        "calibrated_residual_deg",
        "left_mag",
        "right_mag",
    ]
    write_csv(REPORT_DIR / f"{item.name}_curves.csv", curves, curve_fields)
    write_csv(REPORT_DIR / f"{item.name}_summary.csv", summaries, summary_fields)
    write_csv(REPORT_DIR / f"{item.name}_calibrated_curves.csv", cal_curves, curve_fields)
    write_csv(REPORT_DIR / f"{item.name}_calibrated_summary.csv", cal_summaries, summary_fields)
    write_csv(REPORT_DIR / f"{item.name}_phase_center.csv", phase_rows, phase_fields)
    write_csv(REPORT_DIR / f"{item.name}_complex_pattern_table.csv", pattern_rows)
    (REPORT_DIR / f"{item.name}_complex_pattern_table.json").write_text(json.dumps(pattern_meta, indent=2, ensure_ascii=False), encoding="utf-8")

    vector = pdoa_metrics["strategies"]["dualpol_vector_correlation"]
    x_return = extra["x_return_worst_db"]
    y_return = extra["y_return_worst_db"]
    row = {
        "candidate": item.name,
        "slotcoupled_enabled": item.slotcoupled_enabled,
        "elapsed_s": time.time() - started,
        "rationale": item.rationale,
        "parameters": item.params,
        "worst_return_db": sparams["worst_return_db"],
        "isolation_db": sparams["isolation_db"],
        "x_return_worst_db": x_return,
        "y_return_worst_db": y_return,
        "xy_return_balance_db": abs(x_return - y_return),
        "same_element_xy_isolation_db": extra["same_element_xy_isolation_db"],
        "same_feed_inter_element_isolation_db": extra["same_feed_inter_element_isolation_db"],
        "dualpol_vector_avg_rms_bias_deg": vector["avg_rms_bias_deg"],
        "dualpol_vector_p95_rms_bias_deg": vector["p95_rms_bias_deg"],
        "dualpol_vector_max_abs_bias_deg": vector["max_abs_bias_deg"],
        "calibrated_avg_rms_bias_deg": cal_metrics["avg_rms_bias_deg"],
        "calibrated_p95_rms_bias_deg": cal_metrics["p95_rms_bias_deg"],
        "calibrated_max_abs_bias_deg": cal_metrics["max_abs_bias_deg"],
        "calibrated_avg_valid_percent": cal_metrics["avg_valid_percent"],
        "calibration_quality": cal_quality,
        "complex_pattern_table": pattern_meta,
        **balance,
        **symmetry,
        **phase_metrics,
    }
    row["sparam_score"] = sparam_score(row)
    row["full_score"] = full_score(row)
    row["meets_s"] = (
        row["worst_return_db"] <= RETURN_TARGET_DB
        and row["same_element_xy_isolation_db"] >= XY_ISOLATION_TARGET_DB
        and row["same_feed_inter_element_isolation_db"] >= SAME_FEED_ISOLATION_TARGET_DB
    )
    row["meets_balance"] = (
        row["xy_return_balance_db"] <= RETURN_BALANCE_TARGET_DB
        and row["xy_mag_imbalance_rms_db"] <= XY_MAG_BALANCE_TARGET_DB
        and row["xy_phase_spread_rms_deg"] <= XY_PHASE_SPREAD_TARGET_DEG
    )
    row["meets_calibrated_pdoa"] = (
        row["calibrated_avg_rms_bias_deg"] <= PDOA_RMS_TARGET_DEG
        and row["calibrated_max_abs_bias_deg"] <= PDOA_MAX_TARGET_DEG
    )
    row["meets_pattern_symmetry"] = row["pattern_symmetry_rms_db"] <= PATTERN_SYMMETRY_TARGET_DB
    row["meets_phase_center"] = row["phase_center_calibrated_rms_deg"] <= PHASE_CENTER_RMS_TARGET_DEG
    row["meets_all"] = (
        row["meets_s"]
        and row["meets_balance"]
        and row["meets_calibrated_pdoa"]
        and row["meets_pattern_symmetry"]
        and row["meets_phase_center"]
    )
    print(json.dumps({k: v for k, v in row.items() if k not in {"parameters", "calibration_quality"}}, indent=2, ensure_ascii=False), flush=True)
    return row


def select_full(cands: list[Candidate], rows: list[dict], count: int) -> list[Candidate]:
    by_name = {item.name: item for item in cands}
    ranked = sorted(rows, key=lambda row: float(row["score"]))
    selected: list[Candidate] = []
    for row in ranked:
        item = by_name[row["candidate"]]
        if item.slotcoupled_enabled and item not in selected:
            selected.append(item)
        if len(selected) >= count:
            break
    reference = by_name.get("stacked_reference_prev")
    if reference and reference not in selected:
        selected.append(reference)
    if not selected and ranked:
        selected.append(by_name[ranked[0]["candidate"]])
    return selected


def copy_best_outputs(candidate: str) -> None:
    mapping = {
        REPORT_DIR / f"{candidate}_curves.csv": BEST_CURVES_CSV,
        REPORT_DIR / f"{candidate}_summary.csv": BEST_SUMMARY_CSV,
        REPORT_DIR / f"{candidate}_calibrated_curves.csv": BEST_CAL_CURVES_CSV,
        REPORT_DIR / f"{candidate}_calibrated_summary.csv": BEST_CAL_SUMMARY_CSV,
        REPORT_DIR / f"{candidate}_phase_center.csv": BEST_PHASE_CENTER_CSV,
        REPORT_DIR / f"{candidate}_complex_pattern_table.csv": BEST_PATTERN_TABLE_CSV,
        REPORT_DIR / f"{candidate}_complex_pattern_table.json": BEST_PATTERN_TABLE_JSON,
    }
    for src, dst in mapping.items():
        if src.exists():
            shutil.copy2(src, dst)


def previous_best() -> dict:
    path = ROOT / "reports_d44_dualpol_stacked_calibration_opt" / "UWB_CH9_D44_DUALPOL_STACKED_CAL_best.json"
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8")).get("best", {})
    except json.JSONDecodeError:
        return {}


def write_report(best: dict, sparam_rows: list[dict], full_rows: list[dict]) -> None:
    prev = previous_best()
    ranked_s = sorted(sparam_rows, key=lambda row: float(row["score"]))
    ranked_full = sorted(full_rows, key=lambda row: float(row["full_score"]))
    params = best["parameters"]
    pattern_meta = best.get("complex_pattern_table", {})
    lines = [
        "# D44 双极化锚点天线缝隙耦合窗口与复方向图标定报告",
        "",
        "## 本轮目标",
        "",
        "- 从叠层寄生贴片路线转向真实双层过渡：下层微带线、接地层正交缝隙窗口、上层双极化贴片。",
        "- 扫描缝隙长度/宽度、A/B 槽错位、下层馈线宽度、下层介质厚度和是否保留弱寄生贴片。",
        "- 在完整远场复核中导出每阵元、每端口的复数方向图标定表，给后端做按角度/频点查表的矢量标定。",
        f"- 仍只评估线极化入射 `0 / 45 / 90 / 135 deg`；目标为回波 `<= {RETURN_TARGET_DB:.1f} dB`、同阵元 X/Y 隔离 `>= {XY_ISOLATION_TARGET_DB:.1f} dB`、方向图镜像 RMS `<= {PATTERN_SYMMETRY_TARGET_DB:.1f} dB`、标定后 PDOA 平均 RMS `<= {PDOA_RMS_TARGET_DEG:.1f} deg`。",
        "",
        "## 方法说明",
        "",
        "- S 参数阶段优先筛选真实缝隙耦合窗口候选，`stacked_reference_prev` 只作为上一轮叠层方案对照。",
        "- 完整复核阶段提取所有端口嵌入远场，计算未标定双极化向量相关 PDOA、2x2 幅相标定 PDOA、方向图镜像误差和等效相位中心残差。",
        "- 复方向图标定表包含 `source/element/feed/freq/theta/phi` 索引，以及 `rETheta/rEPhi` 的实部/虚部和 0/45/90/135 deg 线极化投影。",
        "",
        "## S 参数筛选",
        "",
        "| 排名 | 候选 | 缝隙耦合 | 评分 | 最差回波 | X回波 | Y回波 | 回波差 | 同阵元X/Y隔离 | 同馈跨阵元隔离 |",
        "| ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for idx, row in enumerate(ranked_s[:10], start=1):
        lines.append(
            f"| {idx} | `{row['candidate']}` | {'是' if bool_value(row.get('slotcoupled_enabled')) else '否'} | "
            f"{fmt(float(row['score']))} | {fmt(float(row['worst_return_db']))} dB | "
            f"{fmt(float(row['x_return_worst_db']))} dB | {fmt(float(row['y_return_worst_db']))} dB | "
            f"{fmt(float(row['xy_return_balance_db']))} dB | {fmt(float(row['same_element_xy_isolation_db']))} dB | "
            f"{fmt(float(row['same_feed_inter_element_isolation_db']))} dB |"
        )

    lines.extend(
        [
            "",
            "## 完整复核结果",
            "",
            "| 候选 | 综合评分 | 最差回波 | 同阵元X/Y隔离 | 方向图镜像RMS | 相位中心残差RMS | 标定后PDOA均值RMS | 标定后PDOA最大漂移 |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for row in ranked_full:
        lines.append(
            f"| `{row['candidate']}` | {fmt(row['full_score'])} | {fmt(row['worst_return_db'])} dB | "
            f"{fmt(row['same_element_xy_isolation_db'])} dB | {fmt(row['pattern_symmetry_rms_db'])} dB | "
            f"{fmt(row['phase_center_calibrated_rms_deg'])} deg | {fmt(row['calibrated_avg_rms_bias_deg'])} deg | "
            f"{fmt(row['calibrated_max_abs_bias_deg'])} deg |"
        )

    lines.extend(
        [
            "",
            "## 最优候选",
            "",
            f"- 候选：`{best['candidate']}`",
            f"- 缝隙耦合窗口：`{'启用' if best.get('slotcoupled_enabled') else '未启用'}`",
            f"- 说明：{best['rationale']}",
            f"- AEDT 工程：`{builder.topology_paths(TOPOLOGY)['project']}`",
            f"- 最差回波：`{fmt(best['worst_return_db'])} dB`",
            f"- X/Y 回波差：`{fmt(best['xy_return_balance_db'])} dB`",
            f"- 同阵元 X/Y 隔离：`{fmt(best['same_element_xy_isolation_db'])} dB`",
            f"- 同馈跨阵元隔离：`{fmt(best['same_feed_inter_element_isolation_db'])} dB`",
            f"- 方向图镜像 RMS：`{fmt(best['pattern_symmetry_rms_db'])} dB`",
            f"- X/Y 幅度 RMS 差：`{fmt(best['xy_mag_imbalance_rms_db'])} dB`",
            f"- X/Y 相位离散 RMS：`{fmt(best['xy_phase_spread_rms_deg'])} deg`",
            f"- 未标定双极化向量 PDOA 平均 RMS：`{fmt(best['dualpol_vector_avg_rms_bias_deg'])} deg`",
            f"- 2x2 标定后 PDOA 平均 RMS：`{fmt(best['calibrated_avg_rms_bias_deg'])} deg`",
            f"- 2x2 标定后 PDOA 最大漂移：`{fmt(best['calibrated_max_abs_bias_deg'])} deg`",
            f"- 相位中心校正后残差 RMS：`{fmt(best['phase_center_calibrated_rms_deg'])} deg`",
            f"- 复方向图标定表行数：`{pattern_meta.get('row_count', 0)}`",
            "",
            "## 最优几何参数",
            "",
        ]
    )
    for key in STRUCTURE_KEYS:
        if key in params:
            lines.append(f"- `{key}`: `{fmt(params[key], 3)}`")

    if prev:
        lines.extend(
            [
                "",
                "## 与上一轮叠层最优对比",
                "",
                "| 指标 | 上一轮 | 本轮 | 变化 |",
                "| --- | ---: | ---: | ---: |",
            ]
        )
        for label, key, unit in [
            ("最差回波", "worst_return_db", "dB"),
            ("同阵元 X/Y 隔离", "same_element_xy_isolation_db", "dB"),
            ("X/Y 回波差", "xy_return_balance_db", "dB"),
            ("方向图镜像 RMS", "pattern_symmetry_rms_db", "dB"),
            ("标定后 PDOA 平均 RMS", "calibrated_avg_rms_bias_deg", "deg"),
            ("相位中心残差 RMS", "phase_center_calibrated_rms_deg", "deg"),
        ]:
            old = prev.get(key)
            new = best.get(key)
            delta = float(new) - float(old) if old is not None and new is not None else None
            lines.append(f"| {label} | {fmt(old)} {unit} | {fmt(new)} {unit} | {fmt(delta)} |")

    lines.extend(
        [
            "",
            "## 达标情况",
            "",
            f"- S 参数/隔离目标：`{'通过' if best['meets_s'] else '未通过'}`。",
            f"- X/Y 幅相一致性目标：`{'通过' if best['meets_balance'] else '未通过'}`。",
            f"- 标定后 PDOA 稳定性目标：`{'通过' if best['meets_calibrated_pdoa'] else '未通过'}`。",
            f"- 方向图镜像对称性目标：`{'通过' if best['meets_pattern_symmetry'] else '未通过'}`。",
            f"- 相位中心残差目标：`{'通过' if best['meets_phase_center'] else '未通过'}`。",
            f"- 全部目标：`{'通过' if best['meets_all'] else '未通过'}`。",
            "",
            "## 工程判断",
            "",
            "- 如果缝隙耦合候选优于叠层参考，说明馈线从辐射贴片主电流区退耦有效，下一轮应围绕窗口尺寸和馈线端口阻抗继续细扫。",
            "- 如果匹配不足但方向图或相位中心改善，下一轮应增加可调电容耦合窗口、下层馈线开路支节或短路过孔调谐。",
            "- 如果 PDOA 仍大幅漂移，应把复方向图表直接用于后端按角度/频点的矢量标定，而不是只依赖 2x2 幅相矩阵。",
            "",
            "## 输出文件",
            "",
            f"- S 参数筛选：`{SPARAM_CSV}`",
            f"- 完整复核：`{FULL_CSV}`",
            f"- 最优未标定曲线：`{BEST_CURVES_CSV}`",
            f"- 最优 2x2 标定后曲线：`{BEST_CAL_CURVES_CSV}`",
            f"- 最优相位中心标定明细：`{BEST_PHASE_CENTER_CSV}`",
            f"- 最优复方向图标定表 CSV：`{BEST_PATTERN_TABLE_CSV}`",
            f"- 最优复方向图标定表说明 JSON：`{BEST_PATTERN_TABLE_JSON}`",
            f"- 最优 JSON：`{BEST_JSON}`",
        ]
    )
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def rebuild_final_project(item: Candidate) -> None:
    print(f"Stage: rebuilding final best runnable project {item.name}", flush=True)
    apply_candidate(item)
    _project, hfss = build_and_open(sparam_only=False)
    hfss.release_desktop(close_projects=False, close_desktop=True)


def run(
    max_sparam_candidates: int = 10,
    full_candidate_count: int = 2,
    resume_sparam: bool = False,
    full_candidate_names: list[str] | None = None,
) -> dict:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    cands = candidates()[:max_sparam_candidates]
    by_name = {item.name: item for item in cands}
    sparam_rows = [row for row in read_csv(SPARAM_CSV) if row.get("candidate") in by_name] if resume_sparam else []
    completed = {row["candidate"] for row in sparam_rows}
    for idx, item in enumerate(cands, start=1):
        if item.name in completed:
            print(f"Stage: S-parameter screening {idx}/{len(cands)} {item.name} reused", flush=True)
            continue
        print(f"Stage: S-parameter screening {idx}/{len(cands)} {item.name}", flush=True)
        sparam_rows.append(sparam_screen(item, idx))
        write_csv(SPARAM_CSV, sparam_rows)

    if full_candidate_names:
        ranked_full = [by_name[name] for name in full_candidate_names if name in by_name]
    else:
        ranked_full = select_full(cands, sparam_rows, full_candidate_count)

    full_rows = []
    for idx, item in enumerate(ranked_full, start=1):
        print(f"Stage: full validation {idx}/{len(ranked_full)} {item.name}", flush=True)
        full_rows.append(full_validate(item))
        write_csv(FULL_CSV, [{k: v for k, v in row.items() if k not in {"parameters", "calibration_quality"}} for row in full_rows])

    slot_rows = [row for row in full_rows if row.get("slotcoupled_enabled")]
    best = min(slot_rows or full_rows, key=lambda row: row["full_score"])
    copy_best_outputs(best["candidate"])
    rebuild_final_project(by_name[best["candidate"]])

    output = {
        "targets": {
            "return_target_db": RETURN_TARGET_DB,
            "xy_isolation_target_db": XY_ISOLATION_TARGET_DB,
            "same_feed_isolation_target_db": SAME_FEED_ISOLATION_TARGET_DB,
            "return_balance_target_db": RETURN_BALANCE_TARGET_DB,
            "xy_mag_balance_target_db": XY_MAG_BALANCE_TARGET_DB,
            "xy_phase_spread_target_deg": XY_PHASE_SPREAD_TARGET_DEG,
            "pdoa_rms_target_deg": PDOA_RMS_TARGET_DEG,
            "pdoa_max_target_deg": PDOA_MAX_TARGET_DEG,
            "pattern_symmetry_target_db": PATTERN_SYMMETRY_TARGET_DB,
            "phase_center_rms_target_deg": PHASE_CENTER_RMS_TARGET_DEG,
        },
        "candidate_count": len(cands),
        "sparam_top": sorted(sparam_rows, key=lambda row: float(row["score"]))[:10],
        "full_validation": full_rows,
        "best": best,
        "files": {
            "sparam_csv": str(SPARAM_CSV),
            "full_csv": str(FULL_CSV),
            "best_curves_csv": str(BEST_CURVES_CSV),
            "best_summary_csv": str(BEST_SUMMARY_CSV),
            "best_calibrated_curves_csv": str(BEST_CAL_CURVES_CSV),
            "best_calibrated_summary_csv": str(BEST_CAL_SUMMARY_CSV),
            "best_phase_center_csv": str(BEST_PHASE_CENTER_CSV),
            "best_json": str(BEST_JSON),
            "report_md": str(REPORT_MD),
        },
    }
    BEST_JSON.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")
    write_report(best, sparam_rows, full_rows)
    print(json.dumps({k: v for k, v in best.items() if k not in {"parameters", "calibration_quality"}}, indent=2, ensure_ascii=False), flush=True)
    print(f"Wrote {REPORT_MD}", flush=True)
    return output


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-sparam-candidates", type=int, default=10)
    parser.add_argument("--full-candidate-count", type=int, default=2)
    parser.add_argument("--resume-sparam", action="store_true")
    parser.add_argument("--full-candidate-names", default="", help="Comma-separated candidate names for full validation.")
    args = parser.parse_args()
    full_names = [item.strip() for item in args.full_candidate_names.split(",") if item.strip()]
    run(
        max_sparam_candidates=args.max_sparam_candidates,
        full_candidate_count=args.full_candidate_count,
        resume_sparam=args.resume_sparam,
        full_candidate_names=full_names or None,
    )


if __name__ == "__main__":
    main()
