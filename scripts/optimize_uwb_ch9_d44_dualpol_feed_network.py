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


ROOT = Path(__file__).resolve().parents[1]
TOPOLOGY = "dualpol"
REPORT_DIR = ROOT / "reports_d44_dualpol_feed_network_opt"
STEM = "UWB_CH9_D44_DUALPOL_FEED_NETWORK"
SPARAM_CSV = REPORT_DIR / f"{STEM}_sparam_screening.csv"
FULL_CSV = REPORT_DIR / f"{STEM}_full_validation.csv"
BEST_JSON = REPORT_DIR / f"{STEM}_best.json"
BEST_CURVES_CSV = REPORT_DIR / f"{STEM}_best_curves.csv"
BEST_SUMMARY_CSV = REPORT_DIR / f"{STEM}_best_summary.csv"
BEST_CAL_CURVES_CSV = REPORT_DIR / f"{STEM}_best_calibrated_curves.csv"
BEST_CAL_SUMMARY_CSV = REPORT_DIR / f"{STEM}_best_calibrated_summary.csv"
REPORT_MD = REPORT_DIR / f"{STEM}_optimization_report.md"

RETURN_TARGET_DB = -10.0
XY_ISOLATION_TARGET_DB = 15.0
SAME_FEED_ISOLATION_TARGET_DB = 16.0
RETURN_BALANCE_TARGET_DB = 0.5
XY_MAG_BALANCE_TARGET_DB = 2.0
XY_PHASE_SPREAD_TARGET_DEG = 30.0
PDOA_RMS_TARGET_DEG = 10.0
PDOA_MAX_TARGET_DEG = 20.0

LINEAR_POLS = [0.0, 45.0, 90.0, 135.0]
PHI_CUTS = [45.0, 60.0, 75.0, 90.0]
MAG_VALID_FLOOR_REL_DB = -35.0

STRUCTURE_KEYS = [
    "patch_side_mm",
    "feed_offset_u_mm",
    "feed_pad_radius_mm",
    "port_width_mm",
    "microstrip_feed_enabled",
    "microstrip_feed_offset_mm",
    "microstrip_feedline_length_mm",
    "microstrip_feedline_width_mm",
    "microstrip_match_length_mm",
    "microstrip_match_width_mm",
    "microstrip_stub_length_mm",
    "microstrip_stub_width_mm",
    "microstrip_stub_offset_mm",
    "neutralization_branch_enabled",
    "neutralization_branch_length_mm",
    "neutralization_branch_width_mm",
    "neutralization_branch_offset_mm",
    "local_dgs_enabled",
    "local_dgs_length_mm",
    "local_dgs_width_mm",
    "local_dgs_offset_mm",
    "isolation_slot_enabled",
    "isolation_slot_length_mm",
    "isolation_slot_width_mm",
    "isolation_slot_inner_mm",
]

BASE_PARAMS: dict[str, Any] = dict(builder.TOPOLOGIES[TOPOLOGY]["params"])
BASE_PARAMS.update(
    {
        "patch_side_mm": 9.15,
        "corner_cut_mm": 0.0,
        "feed_offset_u_mm": 3.40,
        "feed_offset_v_mm": 0.0,
        "feed_pad_radius_mm": 0.28,
        "port_width_mm": 0.50,
        "microstrip_feed_enabled": 0.0,
        "microstrip_feed_offset_mm": 0.0,
        "microstrip_feedline_length_mm": 1.70,
        "microstrip_feedline_width_mm": 0.58,
        "microstrip_match_length_mm": 0.75,
        "microstrip_match_width_mm": 0.40,
        "microstrip_stub_length_mm": 0.0,
        "microstrip_stub_width_mm": 0.24,
        "microstrip_stub_offset_mm": 0.60,
        "neutralization_branch_enabled": 0.0,
        "neutralization_branch_length_mm": 0.85,
        "neutralization_branch_width_mm": 0.12,
        "neutralization_branch_offset_mm": 0.65,
        "local_dgs_enabled": 0.0,
        "local_dgs_length_mm": 3.6,
        "local_dgs_width_mm": 0.18,
        "local_dgs_offset_mm": 0.75,
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
    real_network: bool


def fmt(value: float | int | None, digits: int = 2) -> str:
    if value is None:
        return "N/A"
    try:
        value = float(value)
    except (TypeError, ValueError):
        return "N/A"
    if math.isnan(value) or math.isinf(value):
        return "N/A"
    return f"{value:.{digits}f}"


def network_extra(
    *,
    line_len: float,
    line_width: float,
    match_len: float,
    match_width: float,
    feed_offset: float = 0.0,
    stub_len: float = 0.0,
    stub_width: float = 0.24,
    stub_offset: float = 0.60,
    branch: bool = False,
    branch_len: float = 0.85,
    branch_width: float = 0.12,
    branch_offset: float = 0.65,
    dgs: bool = False,
    dgs_len: float = 3.6,
    dgs_width: float = 0.18,
    dgs_offset: float = 0.75,
) -> dict[str, float]:
    return {
        "microstrip_feed_enabled": 1.0,
        "microstrip_feed_offset_mm": feed_offset,
        "microstrip_feedline_length_mm": line_len,
        "microstrip_feedline_width_mm": line_width,
        "microstrip_match_length_mm": match_len,
        "microstrip_match_width_mm": match_width,
        "microstrip_stub_length_mm": stub_len,
        "microstrip_stub_width_mm": stub_width,
        "microstrip_stub_offset_mm": stub_offset,
        "neutralization_branch_enabled": 1.0 if branch else 0.0,
        "neutralization_branch_length_mm": branch_len,
        "neutralization_branch_width_mm": branch_width,
        "neutralization_branch_offset_mm": branch_offset,
        "local_dgs_enabled": 1.0 if dgs else 0.0,
        "local_dgs_length_mm": dgs_len,
        "local_dgs_width_mm": dgs_width,
        "local_dgs_offset_mm": dgs_offset,
    }


def make_candidate(name: str, rationale: str, real_network: bool = True, **overrides: Any) -> Candidate:
    params = dict(BASE_PARAMS)
    params.update(overrides)
    return Candidate(name=name, params=params, rationale=rationale, real_network=real_network)


def candidates() -> list[Candidate]:
    return [
        make_candidate(
            "probe_ref_pad0p28",
            "上一轮小焊盘探针/焊盘最优解，仅作为真实微带网络的对照基线。",
            real_network=False,
            microstrip_feed_enabled=0.0,
            feed_pad_radius_mm=0.28,
            port_width_mm=0.50,
        ),
        make_candidate(
            "edge_eq_l1p60_w0p50_m0p62_w0p34",
            "两路等长短微带过渡，窄匹配段降低边缘过耦合。",
            **network_extra(line_len=1.60, line_width=0.50, match_len=0.62, match_width=0.34),
        ),
        make_candidate(
            "edge_eq_l1p70_w0p58_m0p75_w0p40",
            "等长微带过渡参考解，匹配段宽度接近上一轮混合器输出段中值。",
            **network_extra(line_len=1.70, line_width=0.58, match_len=0.75, match_width=0.40),
        ),
        make_candidate(
            "edge_eq_l1p78_w0p62_m0p82_w0p44",
            "加宽并拉长等长微带过渡，测试回波改善与同阵元串扰变化。",
            **network_extra(line_len=1.78, line_width=0.62, match_len=0.82, match_width=0.44),
        ),
        make_candidate(
            "edge_offset0p20_l1p70_m0p75",
            "两路保持等长，加入 0.20 mm 横向偏移用于补偿 X/Y 边馈不对称。",
            **network_extra(line_len=1.70, line_width=0.58, match_len=0.75, match_width=0.40, feed_offset=0.20),
        ),
        make_candidate(
            "edge_stub0p85_branch0p65",
            "加入开路匹配支节和短同阵元隔离枝节，优先改善同阵元 X/Y 隔离。",
            **network_extra(
                line_len=1.70,
                line_width=0.58,
                match_len=0.75,
                match_width=0.40,
                stub_len=0.85,
                branch=True,
                branch_len=0.65,
                branch_width=0.12,
                branch_offset=0.58,
            ),
        ),
        make_candidate(
            "edge_stub1p05_branch0p85",
            "加长开路匹配支节并提高隔离枝节耦合长度，观察隔离收益上限。",
            **network_extra(
                line_len=1.75,
                line_width=0.58,
                match_len=0.78,
                match_width=0.40,
                stub_len=1.05,
                branch=True,
                branch_len=0.85,
                branch_width=0.12,
                branch_offset=0.65,
            ),
        ),
        make_candidate(
            "edge_branch1p05_dgs0p65",
            "隔离枝节叠加局部 DGS，尝试压低同阵元耦合并保持可制造尺寸。",
            **network_extra(
                line_len=1.72,
                line_width=0.58,
                match_len=0.78,
                match_width=0.40,
                stub_len=0.95,
                branch=True,
                branch_len=1.05,
                branch_width=0.12,
                branch_offset=0.72,
                dgs=True,
                dgs_len=3.4,
                dgs_width=0.18,
                dgs_offset=0.65,
            ),
        ),
        make_candidate(
            "edge_branch1p20_dgs0p85",
            "更强隔离枝节与外移 DGS 组合，验证隔离提升是否牺牲匹配。",
            **network_extra(
                line_len=1.78,
                line_width=0.58,
                match_len=0.80,
                match_width=0.40,
                stub_len=1.10,
                branch=True,
                branch_len=1.20,
                branch_width=0.12,
                branch_offset=0.78,
                dgs=True,
                dgs_len=3.6,
                dgs_width=0.18,
                dgs_offset=0.85,
            ),
        ),
        make_candidate(
            "edge_patch9p05_branch_dgs",
            "略缩小贴片边长补偿边馈电容性加载，并保留隔离枝节/DGS。",
            patch_side_mm=9.05,
            **network_extra(
                line_len=1.70,
                line_width=0.58,
                match_len=0.75,
                match_width=0.38,
                stub_len=0.95,
                branch=True,
                branch_len=0.95,
                branch_width=0.12,
                branch_offset=0.70,
                dgs=True,
                dgs_len=3.4,
                dgs_width=0.18,
                dgs_offset=0.75,
            ),
        ),
        make_candidate(
            "edge_patch9p25_branch_dgs",
            "略放大贴片边长抵消边缘馈入导致的谐振上移，同时保留真实网络。",
            patch_side_mm=9.25,
            **network_extra(
                line_len=1.70,
                line_width=0.58,
                match_len=0.75,
                match_width=0.40,
                stub_len=0.95,
                branch=True,
                branch_len=0.95,
                branch_width=0.12,
                branch_offset=0.70,
                dgs=True,
                dgs_len=3.4,
                dgs_width=0.18,
                dgs_offset=0.75,
            ),
        ),
    ]


def read_csv(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        return
    fields = fieldnames or list(rows[0])
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


def apply_candidate(item: Candidate) -> None:
    params = builder.TOPOLOGIES[TOPOLOGY].setdefault("params", {})
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


def sparam_score(row: dict) -> float:
    ret = float(row["worst_return_db"])
    iso = float(row["same_element_xy_isolation_db"])
    same_feed_iso = float(row["same_feed_inter_element_isolation_db"])
    balance = float(row["xy_return_balance_db"])
    return_gap = max(0.0, ret - RETURN_TARGET_DB)
    iso_gap = max(0.0, XY_ISOLATION_TARGET_DB - iso)
    same_feed_gap = max(0.0, SAME_FEED_ISOLATION_TARGET_DB - same_feed_iso)
    balance_gap = max(0.0, balance - RETURN_BALANCE_TARGET_DB)
    real_bonus = -2.0 if row.get("real_network") else 0.0
    return 8.0 * return_gap + 5.0 * iso_gap + 2.0 * same_feed_gap + 4.0 * balance_gap + real_bonus


def sparam_screen(item: Candidate, index: int) -> dict:
    started = time.time()
    apply_candidate(item)
    _project, hfss = build_and_open(sparam_only=True)
    try:
        sources = hfss.get_all_sources()
        s_csv = REPORT_DIR / f"{item.name}_s_parameters.csv"
        sparams = topology_eval.get_s_parameter_snapshot(hfss, s_csv)
        extra = dualpol_eval.enrich_sparams(sparams)
    finally:
        hfss.release_desktop(close_projects=False, close_desktop=True)

    x_return = extra["x_return_worst_db"]
    y_return = extra["y_return_worst_db"]
    row = {
        "index": index,
        "candidate": item.name,
        "real_network": item.real_network,
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


def circular_mean_deg(values: list[float]) -> float:
    if not values:
        return 0.0
    x = fmean(math.cos(math.radians(value)) for value in values)
    y = fmean(math.sin(math.radians(value)) for value in values)
    return math.degrees(math.atan2(y, x))


def xy_balance_metrics(fields: dict, eval_freqs: list[float], sources: list[str]) -> dict:
    elements = dualpol_eval.element_pairs(sources)
    mag_errors = []
    phase_residuals = []
    for freq in eval_freqs:
        fkey = pdoa_eval.freq_key(freq)
        fields_by_source = {source: fields[source][fkey] for source in sources}
        all_points = next(iter(fields_by_source.values()))
        for point_key in all_points:
            per_element_phases = []
            per_element_mags = []
            for element in elements:
                a_point = fields_by_source[f"P{element}A"][point_key]
                b_point = fields_by_source[f"P{element}B"][point_key]
                a = dualpol_eval.linear_projection(a_point, 0.0)
                b = dualpol_eval.linear_projection(b_point, 90.0)
                if abs(a) <= 1e-12 or abs(b) <= 1e-12:
                    continue
                per_element_mags.append(20.0 * math.log10(abs(a) / abs(b)))
                per_element_phases.append(pdoa_eval.wrap_deg(pdoa_eval.phase_deg(a) - pdoa_eval.phase_deg(b)))
            if per_element_mags:
                mag_errors.extend(per_element_mags)
            if len(per_element_phases) >= 2:
                mean_phase = circular_mean_deg(per_element_phases)
                phase_residuals.extend(abs(pdoa_eval.wrap_deg(value - mean_phase)) for value in per_element_phases)
    abs_mag = [abs(value) for value in mag_errors]
    return {
        "xy_mag_imbalance_mean_abs_db": fmean(abs_mag) if abs_mag else 0.0,
        "xy_mag_imbalance_rms_db": math.sqrt(fmean(value * value for value in mag_errors)) if mag_errors else 0.0,
        "xy_mag_imbalance_max_abs_db": max(abs_mag) if abs_mag else 0.0,
        "xy_phase_spread_mean_abs_deg": fmean(phase_residuals) if phase_residuals else 0.0,
        "xy_phase_spread_rms_deg": math.sqrt(fmean(value * value for value in phase_residuals)) if phase_residuals else 0.0,
        "xy_phase_spread_max_abs_deg": max(phase_residuals) if phase_residuals else 0.0,
    }


def measured_vector(
    fields_by_source: dict[str, dict[tuple[float, float], pdoa_eval.FieldPoint]],
    element: int,
    point_key: tuple[float, float],
    pol_deg: float,
) -> np.ndarray:
    a = dualpol_eval.linear_projection(fields_by_source[f"P{element}A"][point_key], pol_deg)
    b = dualpol_eval.linear_projection(fields_by_source[f"P{element}B"][point_key], pol_deg)
    return np.array([a, b], dtype=np.complex128)


def fit_calibration_matrices(fields: dict, eval_freqs: list[float], sources: list[str]) -> tuple[dict, dict]:
    elements = dualpol_eval.element_pairs(sources)
    matrices: dict[str, dict[int, np.ndarray]] = {}
    quality: dict[str, dict[int, dict[str, float]]] = {}
    for freq in eval_freqs:
        fkey = pdoa_eval.freq_key(freq)
        fields_by_source = {source: fields[source][fkey] for source in sources}
        all_points = next(iter(fields_by_source.values()))
        phi_values = sorted({point.phi_deg for point in all_points.values()})
        selected_phi = [phi for phi in PHI_CUTS if any(abs(phi - item) < 1e-6 for item in phi_values)]
        matrices[fkey] = {}
        quality[fkey] = {}
        for element in elements:
            x_rows = []
            y_rows = []
            for point in all_points.values():
                if selected_phi and not any(abs(point.phi_deg - phi) < 1e-6 for phi in selected_phi):
                    continue
                if point.theta_deg < 5.0 or point.theta_deg > 85.0:
                    continue
                point_key = (round(point.theta_deg, 9), round(point.phi_deg, 9))
                for pol in LINEAR_POLS:
                    vec = measured_vector(fields_by_source, element, point_key, pol)
                    norm = float(np.linalg.norm(vec))
                    if norm <= 1e-12:
                        continue
                    angle = math.radians(pol)
                    x_rows.append(vec / norm)
                    y_rows.append([math.cos(angle), math.sin(angle)])
            if len(x_rows) < 4:
                matrix = np.eye(2, dtype=np.complex128)
                residual = 0.0
                cond = 1.0
            else:
                x = np.asarray(x_rows, dtype=np.complex128)
                y = np.asarray(y_rows, dtype=np.complex128)
                matrix, residuals, _rank, _singular = np.linalg.lstsq(x, y, rcond=None)
                residual = float(np.sqrt(np.mean(np.abs(x @ matrix - y) ** 2)))
                cond = float(np.linalg.cond(matrix))
                if not math.isfinite(cond) or cond > 100.0:
                    matrix = np.eye(2, dtype=np.complex128)
                    residual = 999.0
                    cond = 999.0
            matrices[fkey][element] = matrix
            quality[fkey][element] = {
                "sample_count": float(len(x_rows)),
                "fit_rms_error": residual,
                "condition_number": cond,
            }
    return matrices, quality


def calibrated_vector(
    fields_by_source: dict[str, dict[tuple[float, float], pdoa_eval.FieldPoint]],
    matrices_by_element: dict[int, np.ndarray],
    element: int,
    point_key: tuple[float, float],
    pol_deg: float,
) -> tuple[complex, complex]:
    vec = measured_vector(fields_by_source, element, point_key, pol_deg)
    norm = float(np.linalg.norm(vec))
    if norm <= 1e-12:
        return (0.0 + 0.0j, 0.0 + 0.0j)
    matrix = matrices_by_element.get(element, np.eye(2, dtype=np.complex128))
    calibrated = (vec / norm) @ matrix
    return (complex(calibrated[0]), complex(calibrated[1]))


def rel_db(value: float, reference: float) -> float:
    if value <= 0.0 or reference <= 0.0:
        return -999.0
    return 20.0 * math.log10(value / reference)


def summarize_calibrated_metrics(summary_rows: list[dict]) -> dict:
    rows = [row for row in summary_rows if abs(row["linear_pol_deg"]) > 1e-9]
    rms = [row["rms_bias_vs_pol0_deg"] for row in rows]
    max_abs = [row["max_abs_bias_vs_pol0_deg"] for row in rows]
    valid = [row["valid_percent"] for row in rows]
    return {
        "curve_count": len(rows),
        "avg_rms_bias_deg": fmean(rms) if rms else 0.0,
        "p95_rms_bias_deg": dualpol_eval.percentile(rms, 95.0),
        "max_abs_bias_deg": max(max_abs) if max_abs else 0.0,
        "avg_valid_percent": fmean(valid) if valid else 0.0,
        "score": (fmean(rms) if rms else 0.0)
        + 0.2 * dualpol_eval.percentile(rms, 95.0)
        + 0.03 * (max(max_abs) if max_abs else 0.0),
    }


def evaluate_calibrated_pdoa(fields: dict, eval_freqs: list[float], sources: list[str]) -> tuple[list[dict], list[dict], dict, dict]:
    elements = dualpol_eval.element_pairs(sources)
    baselines = dualpol_eval.baseline_pairs(elements)
    matrices, quality = fit_calibration_matrices(fields, eval_freqs, sources)
    curves: list[dict] = []
    summaries: list[dict] = []
    for freq in eval_freqs:
        fkey = pdoa_eval.freq_key(freq)
        fields_by_source = {source: fields[source][fkey] for source in sources}
        all_points = next(iter(fields_by_source.values()))
        theta_values = sorted({point.theta_deg for point in all_points.values()})
        phi_values = sorted({point.phi_deg for point in all_points.values()})
        selected_phi = [phi for phi in PHI_CUTS if any(abs(phi - item) < 1e-6 for item in phi_values)]
        for phi in selected_phi:
            for left, right in baselines:
                reference_by_theta = None
                by_pol: dict[float, list[dict]] = {}
                for pol in LINEAR_POLS:
                    raw_rows = []
                    mags = []
                    for theta in theta_values:
                        key = (round(theta, 9), round(phi, 9))
                        if key not in all_points:
                            continue
                        left_vec = calibrated_vector(fields_by_source, matrices[fkey], left, key, pol)
                        right_vec = calibrated_vector(fields_by_source, matrices[fkey], right, key, pol)
                        left_mag = math.sqrt(sum(abs(value) ** 2 for value in left_vec))
                        right_mag = math.sqrt(sum(abs(value) ** 2 for value in right_vec))
                        pair_phase = sum(lv * rv.conjugate() for lv, rv in zip(left_vec, right_vec))
                        pdoa_deg = pdoa_eval.wrap_deg(pdoa_eval.phase_deg(pair_phase))
                        mags.extend([left_mag, right_mag])
                        raw_rows.append(
                            {
                                "freq_ghz": freq,
                                "phi_deg": phi,
                                "theta_deg": theta,
                                "linear_pol_deg": pol,
                                "strategy": "calibrated_2x2_vector_correlation",
                                "baseline": f"E{left}-E{right}",
                                "left_mag": left_mag,
                                "right_mag": right_mag,
                                "pdoa_deg": pdoa_deg,
                            }
                        )
                    reference = max(mags) if mags else 1.0
                    floor = reference * 10.0 ** (MAG_VALID_FLOOR_REL_DB / 20.0)
                    for row in raw_rows:
                        row["left_mag_rel_db"] = rel_db(row["left_mag"], reference)
                        row["right_mag_rel_db"] = rel_db(row["right_mag"], reference)
                        row["valid"] = row["left_mag"] >= floor and row["right_mag"] >= floor
                    by_pol[pol] = raw_rows
                    if pol == 0.0:
                        reference_by_theta = {row["theta_deg"]: row["pdoa_deg"] for row in raw_rows if row["valid"]}
                for pol, rows in by_pol.items():
                    summary = dualpol_eval.summarize_curve(rows, reference_by_theta)
                    summary.update(
                        {
                            "freq_ghz": freq,
                            "phi_deg": phi,
                            "linear_pol_deg": pol,
                            "strategy": "calibrated_2x2_vector_correlation",
                            "baseline": f"E{left}-E{right}",
                        }
                    )
                    summaries.append(summary)
                    curves.extend(rows)
    return curves, summaries, summarize_calibrated_metrics(summaries), calibration_to_json(quality, matrices)


def complex_matrix_to_json(matrix: np.ndarray) -> list[list[dict[str, float]]]:
    return [[{"re": float(value.real), "im": float(value.imag)} for value in row] for row in matrix.tolist()]


def calibration_to_json(quality: dict, matrices: dict | None = None) -> dict:
    output: dict[str, dict[str, Any]] = {}
    for fkey, by_element in quality.items():
        output[fkey] = {}
        for element, metrics in by_element.items():
            output[fkey][str(element)] = metrics
            if matrices and fkey in matrices and element in matrices[fkey]:
                output[fkey][str(element)]["matrix"] = complex_matrix_to_json(matrices[fkey][element])
    return output


def full_score(row: dict) -> float:
    return (
        row["sparam_score"]
        + 0.30 * row["dualpol_vector_avg_rms_bias_deg"]
        + 0.10 * row["dualpol_vector_p95_rms_bias_deg"]
        + 0.02 * row["dualpol_vector_max_abs_bias_deg"]
        + 0.55 * row["calibrated_avg_rms_bias_deg"]
        + 0.18 * row["calibrated_p95_rms_bias_deg"]
        + 0.03 * row["calibrated_max_abs_bias_deg"]
        + 1.25 * row["xy_mag_imbalance_rms_db"]
        + 0.06 * row["xy_phase_spread_rms_deg"]
    )


def full_validate(item: Candidate) -> dict:
    started = time.time()
    apply_candidate(item)
    _project, hfss = build_and_open(sparam_only=False)
    try:
        sources = hfss.get_all_sources()
        s_csv = REPORT_DIR / f"{item.name}_full_s_parameters.csv"
        sparams = topology_eval.get_s_parameter_snapshot(hfss, s_csv)
        extra = dualpol_eval.enrich_sparams(sparams)
        eval_freqs = pdoa_eval.nearest_frequencies(pdoa_eval.get_available_frequencies(hfss))
        fields = pdoa_eval.acquire_embedded_fields(hfss, sources, eval_freqs)
        curves, summaries, pdoa_metrics = dualpol_eval.evaluate_dualpol_pdoa(fields, eval_freqs, sources)
        cal_curves, cal_summaries, cal_metrics, cal_quality = evaluate_calibrated_pdoa(fields, eval_freqs, sources)
        balance = xy_balance_metrics(fields, eval_freqs, sources)
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
    write_csv(REPORT_DIR / f"{item.name}_curves.csv", curves, curve_fields)
    write_csv(REPORT_DIR / f"{item.name}_summary.csv", summaries, summary_fields)
    write_csv(REPORT_DIR / f"{item.name}_calibrated_curves.csv", cal_curves, curve_fields)
    write_csv(REPORT_DIR / f"{item.name}_calibrated_summary.csv", cal_summaries, summary_fields)

    vector = pdoa_metrics["strategies"]["dualpol_vector_correlation"]
    x_return = extra["x_return_worst_db"]
    y_return = extra["y_return_worst_db"]
    row = {
        "candidate": item.name,
        "real_network": item.real_network,
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
        **balance,
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
    row["meets_all"] = row["meets_s"] and row["meets_balance"] and row["meets_calibrated_pdoa"]
    print(json.dumps({k: v for k, v in row.items() if k not in {"parameters", "calibration_quality"}}, indent=2, ensure_ascii=False), flush=True)
    return row


def select_full(cands: list[Candidate], rows: list[dict], count: int) -> list[Candidate]:
    by_name = {item.name: item for item in cands}
    ranked = sorted(rows, key=lambda row: float(row["score"]))
    selected: list[Candidate] = []
    for row in ranked:
        item = by_name[row["candidate"]]
        if item.real_network and item not in selected:
            selected.append(item)
        if len(selected) >= count:
            break
    if not selected:
        selected = [by_name[ranked[0]["candidate"]]]
    reference = by_name.get("probe_ref_pad0p28")
    if reference and reference not in selected and len(selected) < count + 1:
        selected.append(reference)
    return selected


def copy_best_outputs(candidate: str) -> None:
    mapping = {
        REPORT_DIR / f"{candidate}_curves.csv": BEST_CURVES_CSV,
        REPORT_DIR / f"{candidate}_summary.csv": BEST_SUMMARY_CSV,
        REPORT_DIR / f"{candidate}_calibrated_curves.csv": BEST_CAL_CURVES_CSV,
        REPORT_DIR / f"{candidate}_calibrated_summary.csv": BEST_CAL_SUMMARY_CSV,
    }
    for src, dst in mapping.items():
        if src.exists():
            shutil.copy2(src, dst)


def previous_best() -> dict:
    path = ROOT / "reports_d44_dualpol_xy_balance_opt" / "UWB_CH9_D44_DUALPOL_XY_BALANCE_best.json"
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8")).get("best", {})
    except json.JSONDecodeError:
        return {}


def write_report(best: dict, sparam_rows: list[dict], full_rows: list[dict]) -> None:
    prev = previous_best()
    lines = [
        "# D44 双极化 XY 真实馈电网络与接收端标定优化报告",
        "",
        "## 本轮目标",
        "",
        "- 在保留独立 X/Y 双极化接收架构的前提下，引入真实双极化馈电网络。",
        "- 两路馈线采用等长微带过渡，避免固定 90 度混合器把 X/Y 信息提前合成为单一圆极化端口。",
        "- 扫描可调匹配段、开路匹配支节、同阵元隔离枝节与局部 DGS。",
        "- 后端评估加入每阵元 2x2 复数幅相标定矩阵，用于衡量接收端双通道可校准上限。",
        f"- 目标：最差回波 `<= {RETURN_TARGET_DB:.1f} dB`，同阵元 X/Y 隔离 `>= {XY_ISOLATION_TARGET_DB:.1f} dB`，X/Y 回波差 `<= {RETURN_BALANCE_TARGET_DB:.1f} dB`，标定后 PDOA 平均 RMS `<= {PDOA_RMS_TARGET_DEG:.1f} deg`。",
        "",
        "## 方法说明",
        "",
        "- S 参数阶段优先筛选真实微带网络候选，探针/焊盘参考解只作为对照。",
        "- 完整复核阶段提取嵌入远场，分别计算未标定双极化向量相关 PDOA 与标定后 2x2 向量相关 PDOA。",
        "- 标定矩阵来自线极化 `0 / 45 / 90 / 135 deg` 的嵌入远场样本最小二乘拟合；它代表后端接收机幅相标定能力，不等同于纯硬件指标改善。",
        "",
        "## S 参数筛选排名",
        "",
        "| 排名 | 候选 | 真实网络 | 评分 | 最差Sii | X回波 | Y回波 | 回波差 | 同阵元X/Y隔离 | 说明 |",
        "| ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    ranked_s = sorted(sparam_rows, key=lambda row: float(row["score"]))
    for idx, row in enumerate(ranked_s[:12], start=1):
        lines.append(
            f"| {idx} | `{row['candidate']}` | {'是' if str(row.get('real_network')) == 'True' else '否'} | "
            f"{fmt(float(row['score']))} | {fmt(float(row['worst_return_db']))} dB | "
            f"{fmt(float(row['x_return_worst_db']))} dB | {fmt(float(row['y_return_worst_db']))} dB | "
            f"{fmt(float(row['xy_return_balance_db']))} dB | {fmt(float(row['same_element_xy_isolation_db']))} dB | "
            f"{row['rationale']} |"
        )

    lines.extend(
        [
            "",
            "## 完整复核结果",
            "",
            "| 候选 | 综合评分 | 最差Sii | 同阵元X/Y隔离 | 回波差 | 幅差RMS | 相位离散RMS | 未标定PDOA均值RMS | 标定后PDOA均值RMS | 标定后95分位 | 标定后最大漂移 |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for row in sorted(full_rows, key=lambda item: item["full_score"]):
        lines.append(
            f"| `{row['candidate']}` | {fmt(row['full_score'])} | {fmt(row['worst_return_db'])} dB | "
            f"{fmt(row['same_element_xy_isolation_db'])} dB | {fmt(row['xy_return_balance_db'])} dB | "
            f"{fmt(row['xy_mag_imbalance_rms_db'])} dB | {fmt(row['xy_phase_spread_rms_deg'])} deg | "
            f"{fmt(row['dualpol_vector_avg_rms_bias_deg'])} deg | {fmt(row['calibrated_avg_rms_bias_deg'])} deg | "
            f"{fmt(row['calibrated_p95_rms_bias_deg'])} deg | {fmt(row['calibrated_max_abs_bias_deg'])} deg |"
        )

    params = best["parameters"]
    lines.extend(
        [
            "",
            "## 最优候选",
            "",
            f"- 候选：`{best['candidate']}`",
            f"- 是否真实馈电网络：`{'是' if best.get('real_network') else '否'}`",
            f"- 说明：{best['rationale']}",
            f"- AEDT 工程：`{builder.topology_paths(TOPOLOGY)['project']}`",
            f"- 最差回波：`{fmt(best['worst_return_db'])} dB`",
            f"- X/A 最差回波：`{fmt(best['x_return_worst_db'])} dB`",
            f"- Y/B 最差回波：`{fmt(best['y_return_worst_db'])} dB`",
            f"- X/Y 回波差：`{fmt(best['xy_return_balance_db'])} dB`",
            f"- 同阵元 X/Y 隔离：`{fmt(best['same_element_xy_isolation_db'])} dB`",
            f"- 同馈跨阵元隔离：`{fmt(best['same_feed_inter_element_isolation_db'])} dB`",
            f"- X/Y 幅度 RMS 差：`{fmt(best['xy_mag_imbalance_rms_db'])} dB`",
            f"- X/Y 相位离散 RMS：`{fmt(best['xy_phase_spread_rms_deg'])} deg`",
            f"- 未标定双极化向量 PDOA 平均 RMS：`{fmt(best['dualpol_vector_avg_rms_bias_deg'])} deg`",
            f"- 2x2 标定后 PDOA 平均 RMS：`{fmt(best['calibrated_avg_rms_bias_deg'])} deg`",
            f"- 2x2 标定后 PDOA 95 分位：`{fmt(best['calibrated_p95_rms_bias_deg'])} deg`",
            f"- 2x2 标定后 PDOA 最大漂移：`{fmt(best['calibrated_max_abs_bias_deg'])} deg`",
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
                "## 与上一轮小焊盘最优解对比",
                "",
                "| 指标 | 上一轮 | 本轮最优 | 变化 |",
                "| --- | ---: | ---: | ---: |",
            ]
        )
        compare = [
            ("最差回波", "worst_return_db", "dB"),
            ("同阵元 X/Y 隔离", "same_element_xy_isolation_db", "dB"),
            ("X/Y 回波差", "xy_return_balance_db", "dB"),
            ("X/Y 幅度 RMS 差", "xy_mag_imbalance_rms_db", "dB"),
            ("X/Y 相位离散 RMS", "xy_phase_spread_rms_deg", "deg"),
            ("未标定向量 PDOA 平均 RMS", "dualpol_vector_avg_rms_bias_deg", "deg"),
        ]
        for label, key, unit in compare:
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
            f"- 全部目标：`{'通过' if best['meets_all'] else '未通过'}`。",
            "",
            "## 工程判断",
            "",
            "- 本轮完成了从探针/焊盘到等长微带双通道馈电网络的结构升级，并保留 X/Y 独立接收端口。",
            "- 如果硬件 S 参数没有明显提升，而标定后 PDOA 明显改善，说明主要矛盾已经从天线几何转向接收链路幅相一致性与标定质量。",
            "- 如果标定后 PDOA 仍大幅漂移，下一步需要从阵元方向图对称性入手，考虑双极化贴片旋转一致化、馈线镜像布局、双层过渡或叠层寄生贴片。",
            "",
            "## 输出文件",
            "",
            f"- S 参数筛选：`{SPARAM_CSV}`",
            f"- 完整复核：`{FULL_CSV}`",
            f"- 最优未标定曲线：`{BEST_CURVES_CSV}`",
            f"- 最优未标定汇总：`{BEST_SUMMARY_CSV}`",
            f"- 最优标定后曲线：`{BEST_CAL_CURVES_CSV}`",
            f"- 最优标定后汇总：`{BEST_CAL_SUMMARY_CSV}`",
            f"- 最优 JSON（含每频点、每阵元 2x2 复数标定矩阵）：`{BEST_JSON}`",
        ]
    )
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def rebuild_final_project(item: Candidate) -> None:
    print(f"Stage: rebuilding final best runnable project {item.name}", flush=True)
    apply_candidate(item)
    _project, hfss = build_and_open(sparam_only=False)
    hfss.release_desktop(close_projects=False, close_desktop=True)


def run(
    max_sparam_candidates: int = 11,
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

    real_rows = [row for row in full_rows if row.get("real_network")]
    best = min(real_rows or full_rows, key=lambda row: row["full_score"])
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
        },
        "candidate_count": len(cands),
        "sparam_top": sorted(sparam_rows, key=lambda row: float(row["score"]))[:12],
        "full_validation": full_rows,
        "best": best,
        "files": {
            "sparam_csv": str(SPARAM_CSV),
            "full_csv": str(FULL_CSV),
            "best_curves_csv": str(BEST_CURVES_CSV),
            "best_summary_csv": str(BEST_SUMMARY_CSV),
            "best_calibrated_curves_csv": str(BEST_CAL_CURVES_CSV),
            "best_calibrated_summary_csv": str(BEST_CAL_SUMMARY_CSV),
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
    parser.add_argument("--max-sparam-candidates", type=int, default=11)
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
