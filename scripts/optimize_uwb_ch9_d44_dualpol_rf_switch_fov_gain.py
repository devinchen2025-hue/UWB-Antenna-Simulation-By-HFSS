from __future__ import annotations

import argparse
import ast
import csv
import json
import math
import shutil
import time
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import build_uwb_ch9_hfss_d44_topology as builder
import evaluate_uwb_ch9_d44_pdoa_linear_polarization as pdoa_eval
import evaluate_uwb_ch9_d44_topology as topology_eval
import optimize_uwb_ch9_d44_dualpol_s11_slotcoupled_match as s11_opt
import simulate_uwb_ch9_d44_dualpol_rf_switch_workstate as workstate


ROOT = Path(__file__).resolve().parents[1]
TOPOLOGY = "dualpol"
SOLUTION = "Setup_CH9 : Sweep_CH9"
SPHERE = "Upper_Hemisphere_5deg"
REPORT_DIR = ROOT / "reports_d44_dualpol_rf_switch_fov_gain_opt"
STEM = "UWB_CH9_D44_DUALPOL_RF_SWITCH_FOV_GAIN"

SUMMARY_CSV = REPORT_DIR / f"{STEM}_summary.csv"
SOURCE_CSV = REPORT_DIR / f"{STEM}_source_summary.csv"
COVERAGE_CSV = REPORT_DIR / f"{STEM}_coverage_summary.csv"
METRICS_JSON = REPORT_DIR / f"{STEM}_metrics.json"
REPORT_MD = REPORT_DIR / f"{STEM}_report.md"
BEST_SOURCE_JSON = ROOT / "reports_d44_dualpol_s11_slotmatch_opt" / "UWB_CH9_D44_DUALPOL_S11_SLOTMATCH_best.json"

THETA_MIN_DEG = 45.0
THETA_MAX_DEG = 90.0
GAIN_TARGET_DBI = -5.0
RETURN_TARGET_DB = -10.0


@dataclass(frozen=True)
class GainCandidate:
    name: str
    params: dict[str, Any]
    rationale: str


def axis_values(sd, axis: str) -> list[float]:
    return [float(str(raw).replace("deg", "")) for raw in sd.intrinsics.get(axis, [])]


def fmt(value: Any, digits: int = 2) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    if math.isnan(number) or math.isinf(number):
        return "N/A"
    return f"{number:.{digits}f}"


def safe_slug(value: str, limit: int = 78) -> str:
    clean = "".join(ch if ch.isalnum() or ch in "-_." else "_" for ch in value)
    return clean[:limit].strip("._-") or "candidate"


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def bool_field(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y"}
    return bool(value)


def coerce_project_map(projects: Any) -> dict[str, str]:
    if isinstance(projects, dict):
        return {str(case): str(path) for case, path in projects.items()}
    if isinstance(projects, str) and projects.strip():
        try:
            parsed = ast.literal_eval(projects)
        except (SyntaxError, ValueError):
            return {}
        if isinstance(parsed, dict):
            return {str(case): str(path) for case, path in parsed.items()}
    return {}


def current_best_candidate() -> GainCandidate:
    best_name, params = workstate.best_candidate_params()
    return GainCandidate(best_name, params, "当前 RF switch / PDOA 工作态基线候选。")


def candidate_by_name(name: str) -> GainCandidate | None:
    for item in s11_opt.candidates():
        if item.name == name:
            return GainCandidate(item.name, dict(item.params), item.rationale)
    return None


def clone_candidate(base: GainCandidate, name: str, rationale: str, **updates: Any) -> GainCandidate:
    params = dict(base.params)
    params.update(updates)
    return GainCandidate(name, params, rationale)


GAIN_NAME_UPDATES: list[tuple[str, dict[str, Any]]] = [
    ("no_ab_cancel", {"slot_coupled_ab_cancel_enabled": 0.0}),
    ("no_isolation_slot", {"isolation_slot_enabled": 0.0}),
    ("ground21p9", {"ground_radius_mm": 21.9}),
    (
        "patch_slit3p0",
        {
            "slot_coupled_patch_slit_enabled": 1.0,
            "slot_coupled_patch_slit_length_mm": 3.0,
            "slot_coupled_patch_slit_width_mm": 0.10,
            "slot_coupled_patch_slit_angle_deg": 45.0,
        },
    ),
    ("feedh0p36", {"feed_substrate_h_mm": 0.36}),
    (
        "stack_p9p55_gap0p80",
        {
            "dualpol_parasitic_enabled": 1.0,
            "parasitic_side_mm": 9.55,
            "parasitic_corner_cut_mm": 0.0,
            "parasitic_rotation_deg": 0.0,
            "parasitic_offset_u_mm": 0.0,
            "parasitic_offset_v_mm": 0.0,
            "air_gap_mm": 0.80,
        },
    ),
    (
        "stack_p9p75_gap1p20",
        {
            "dualpol_parasitic_enabled": 1.0,
            "parasitic_side_mm": 9.75,
            "parasitic_corner_cut_mm": 0.0,
            "parasitic_rotation_deg": 0.0,
            "parasitic_offset_u_mm": 0.0,
            "parasitic_offset_v_mm": 0.0,
            "air_gap_mm": 1.20,
        },
    ),
    (
        "stack_p9p95_gap1p60",
        {
            "dualpol_parasitic_enabled": 1.0,
            "parasitic_side_mm": 9.95,
            "parasitic_corner_cut_mm": 0.0,
            "parasitic_rotation_deg": 0.0,
            "parasitic_offset_u_mm": 0.0,
            "parasitic_offset_v_mm": 0.0,
            "air_gap_mm": 1.60,
        },
    ),
    (
        "slit4p0_off0p45",
        {
            "slot_coupled_patch_slit_enabled": 1.0,
            "slot_coupled_patch_slit_length_mm": 4.0,
            "slot_coupled_patch_slit_width_mm": 0.12,
            "slot_coupled_patch_slit_angle_deg": 45.0,
            "slot_coupled_patch_slit_offset_u_mm": 0.45,
            "slot_coupled_patch_slit_offset_v_mm": 0.45,
        },
    ),
    (
        "weakline2p4_gap0p12",
        {
            "weak_coupling_open_line_enabled": 1.0,
            "weak_coupling_open_line_length_mm": 2.40,
            "weak_coupling_open_line_width_mm": 0.12,
            "weak_coupling_open_line_offset_mm": 1.65,
            "weak_coupling_open_line_gap_mm": 0.12,
        },
    ),
    (
        "slit5p0_offu0p80_v0p00",
        {
            "slot_coupled_patch_slit_enabled": 1.0,
            "slot_coupled_patch_slit_length_mm": 5.0,
            "slot_coupled_patch_slit_width_mm": 0.12,
            "slot_coupled_patch_slit_angle_deg": 45.0,
            "slot_coupled_patch_slit_offset_u_mm": 0.80,
            "slot_coupled_patch_slit_offset_v_mm": 0.00,
        },
    ),
    (
        "slit5p0_offu0p00_v0p80",
        {
            "slot_coupled_patch_slit_enabled": 1.0,
            "slot_coupled_patch_slit_length_mm": 5.0,
            "slot_coupled_patch_slit_width_mm": 0.12,
            "slot_coupled_patch_slit_angle_deg": 45.0,
            "slot_coupled_patch_slit_offset_u_mm": 0.00,
            "slot_coupled_patch_slit_offset_v_mm": 0.80,
        },
    ),
    (
        "slit5p5_offu0p60_v0p00",
        {
            "slot_coupled_patch_slit_enabled": 1.0,
            "slot_coupled_patch_slit_length_mm": 5.5,
            "slot_coupled_patch_slit_width_mm": 0.12,
            "slot_coupled_patch_slit_angle_deg": 45.0,
            "slot_coupled_patch_slit_offset_u_mm": 0.60,
            "slot_coupled_patch_slit_offset_v_mm": 0.00,
        },
    ),
    (
        "slit5p5_offu0p00_v0p60",
        {
            "slot_coupled_patch_slit_enabled": 1.0,
            "slot_coupled_patch_slit_length_mm": 5.5,
            "slot_coupled_patch_slit_width_mm": 0.12,
            "slot_coupled_patch_slit_angle_deg": 45.0,
            "slot_coupled_patch_slit_offset_u_mm": 0.00,
            "slot_coupled_patch_slit_offset_v_mm": 0.60,
        },
    ),
    (
        "slit3p6_off0p35",
        {
            "slot_coupled_patch_slit_enabled": 1.0,
            "slot_coupled_patch_slit_length_mm": 3.6,
            "slot_coupled_patch_slit_width_mm": 0.12,
            "slot_coupled_patch_slit_angle_deg": 45.0,
            "slot_coupled_patch_slit_offset_u_mm": 0.35,
            "slot_coupled_patch_slit_offset_v_mm": 0.35,
        },
    ),
    (
        "slit3p8_off0p45",
        {
            "slot_coupled_patch_slit_enabled": 1.0,
            "slot_coupled_patch_slit_length_mm": 3.8,
            "slot_coupled_patch_slit_width_mm": 0.12,
            "slot_coupled_patch_slit_angle_deg": 45.0,
            "slot_coupled_patch_slit_offset_u_mm": 0.45,
            "slot_coupled_patch_slit_offset_v_mm": 0.45,
        },
    ),
    (
        "slit4p0_w0p16_off0p45",
        {
            "slot_coupled_patch_slit_enabled": 1.0,
            "slot_coupled_patch_slit_length_mm": 4.0,
            "slot_coupled_patch_slit_width_mm": 0.16,
            "slot_coupled_patch_slit_angle_deg": 45.0,
            "slot_coupled_patch_slit_offset_u_mm": 0.45,
            "slot_coupled_patch_slit_offset_v_mm": 0.45,
        },
    ),
    (
        "slit4p0_ang30_off0p45",
        {
            "slot_coupled_patch_slit_enabled": 1.0,
            "slot_coupled_patch_slit_length_mm": 4.0,
            "slot_coupled_patch_slit_width_mm": 0.12,
            "slot_coupled_patch_slit_angle_deg": 30.0,
            "slot_coupled_patch_slit_offset_u_mm": 0.45,
            "slot_coupled_patch_slit_offset_v_mm": 0.45,
        },
    ),
    (
        "neutralizer2p2",
        {
            "slot_coupled_underfeed_neutralizer_enabled": 1.0,
            "slot_coupled_underfeed_neutralizer_length_mm": 2.20,
            "slot_coupled_underfeed_neutralizer_width_mm": 0.12,
            "slot_coupled_underfeed_neutralizer_offset_mm": 1.20,
            "slot_coupled_underfeed_neutralizer_z_offset_mm": 0.06,
        },
    ),
    (
        "neutralizer2p2_z0p10",
        {
            "slot_coupled_underfeed_neutralizer_enabled": 1.0,
            "slot_coupled_underfeed_neutralizer_length_mm": 2.20,
            "slot_coupled_underfeed_neutralizer_width_mm": 0.12,
            "slot_coupled_underfeed_neutralizer_offset_mm": 1.20,
            "slot_coupled_underfeed_neutralizer_z_offset_mm": 0.10,
        },
    ),
    (
        "neutralizer2p6",
        {
            "slot_coupled_underfeed_neutralizer_enabled": 1.0,
            "slot_coupled_underfeed_neutralizer_length_mm": 2.60,
            "slot_coupled_underfeed_neutralizer_width_mm": 0.12,
            "slot_coupled_underfeed_neutralizer_offset_mm": 1.20,
            "slot_coupled_underfeed_neutralizer_z_offset_mm": 0.06,
        },
    ),
    (
        "neutralizer2p2_abc",
        {
            "slot_coupled_underfeed_neutralizer_enabled": 1.0,
            "slot_coupled_underfeed_neutralizer_length_mm": 2.20,
            "slot_coupled_underfeed_neutralizer_width_mm": 0.12,
            "slot_coupled_underfeed_neutralizer_offset_mm": 1.20,
            "slot_coupled_underfeed_neutralizer_z_offset_mm": 0.06,
            "slot_coupled_ab_cancel_enabled": 1.0,
            "slot_coupled_ab_cancel_coupling_length_mm": 1.80,
            "slot_coupled_ab_cancel_trace_width_mm": 0.12,
            "slot_coupled_ab_cancel_gap_mm": 0.12,
            "slot_coupled_ab_cancel_phase_offset_mm": 2.10,
            "slot_coupled_ab_cancel_side_sign": 1.0,
            "slot_coupled_ab_cancel_z_offset_mm": 0.06,
        },
    ),
    (
        "edgearm2p4_w0p30",
        {
            "slot_coupled_edge_arm_enabled": 1.0,
            "slot_coupled_edge_arm_length_mm": 2.40,
            "slot_coupled_edge_arm_width_mm": 0.30,
            "slot_coupled_edge_arm_offset_mm": 0.0,
            "slot_coupled_edge_arm_gap_mm": 0.0,
        },
    ),
    (
        "edgearm3p2_w0p30",
        {
            "slot_coupled_edge_arm_enabled": 1.0,
            "slot_coupled_edge_arm_length_mm": 3.20,
            "slot_coupled_edge_arm_width_mm": 0.30,
            "slot_coupled_edge_arm_offset_mm": 0.0,
            "slot_coupled_edge_arm_gap_mm": 0.0,
        },
    ),
    (
        "edgewall2p0_w0p50",
        {
            "slot_coupled_edge_wall_enabled": 1.0,
            "slot_coupled_edge_wall_height_mm": 2.00,
            "slot_coupled_edge_wall_width_mm": 0.50,
            "slot_coupled_edge_wall_offset_mm": 0.0,
        },
    ),
    (
        "edgewall3p0_w0p45",
        {
            "slot_coupled_edge_wall_enabled": 1.0,
            "slot_coupled_edge_wall_height_mm": 3.00,
            "slot_coupled_edge_wall_width_mm": 0.45,
            "slot_coupled_edge_wall_offset_mm": 0.0,
        },
    ),
]


def apply_gain_name_updates(candidate_name: str, params: dict[str, Any]) -> None:
    for suffix, updates in GAIN_NAME_UPDATES:
        if f"_{suffix}" in candidate_name:
            params.update(updates)


def previous_gain_best_candidate() -> GainCandidate | None:
    if not SUMMARY_CSV.exists():
        return None
    rows = read_csv(SUMMARY_CSV)
    if not rows:
        return None
    best_name = str(rank_summary(rows)[0].get("candidate", ""))
    if not best_name:
        return None
    direct = candidate_by_name(best_name)
    if direct:
        return direct
    for item in sorted(s11_opt.candidates(), key=lambda candidate: len(candidate.name), reverse=True):
        if best_name.startswith(f"{item.name}_"):
            params = dict(item.params)
            apply_gain_name_updates(best_name, params)
            return GainCandidate(best_name, params, "Previous FOV gain best reconstructed from candidate suffixes.")
    return None


def historical_top_s11_names(limit: int = 8) -> list[str]:
    if not BEST_SOURCE_JSON.exists():
        return []
    payload = read_json(BEST_SOURCE_JSON)
    rows = payload.get("sparam_rows", [])

    def num(row: dict[str, Any], key: str, default: float = 0.0) -> float:
        try:
            return float(row.get(key, default))
        except (TypeError, ValueError):
            return default

    ranked = sorted(
        rows,
        key=lambda row: (
            num(row, "worst_return_db") > RETURN_TARGET_DB,
            num(row, "score", 1e9),
            num(row, "worst_return_db", 0.0),
        ),
    )
    names: list[str] = []
    for row in ranked:
        name = str(row.get("candidate", ""))
        if name and name not in names:
            names.append(name)
        if len(names) >= limit:
            break
    return names


def candidate_pool() -> list[GainCandidate]:
    base = current_best_candidate()
    gain_base = previous_gain_best_candidate() or base
    pool: list[GainCandidate] = [base]
    seen = {base.name}
    for name in historical_top_s11_names(limit=8):
        item = candidate_by_name(name)
        if item and item.name not in seen:
            pool.append(item)
            seen.add(item.name)

    custom = [
        clone_candidate(
            base,
            f"{base.name}_no_ab_cancel",
            "移除浮置 A/B 抵消支路，检查该支路是否造成边缘方向辐射谷。",
            slot_coupled_ab_cancel_enabled=0.0,
        ),
        clone_candidate(
            base,
            f"{base.name}_no_isolation_slot",
            "移除中心隔离缝，检查地板开槽对 Theta=45..90 边缘覆盖的影响。",
            isolation_slot_enabled=0.0,
        ),
        clone_candidate(
            base,
            f"{base.name}_ground21p9",
            "把接地半径推近 44 mm 圆板边界，观察边缘绕射和水平面覆盖是否改善。",
            ground_radius_mm=21.9,
        ),
        clone_candidate(
            base,
            f"{base.name}_patch_slit3p0",
            "启用 45 度贴片细缝，尝试扰动贴片电流以填补斜向/水平面低谷。",
            slot_coupled_patch_slit_enabled=1.0,
            slot_coupled_patch_slit_length_mm=3.0,
            slot_coupled_patch_slit_width_mm=0.10,
            slot_coupled_patch_slit_angle_deg=45.0,
        ),
        clone_candidate(
            base,
            f"{base.name}_feedh0p36",
            "略增下层馈电介质厚度，减弱贴片和馈线强加载，观察边缘方向增益。",
            feed_substrate_h_mm=0.36,
        ),
        clone_candidate(
            gain_base,
            f"{gain_base.name}_stack_p9p55_gap0p80",
            "Enable a compact stacked parasitic patch borrowed from the dual-pol stacked calibration sweep.",
            dualpol_parasitic_enabled=1.0,
            parasitic_side_mm=9.55,
            parasitic_corner_cut_mm=0.0,
            parasitic_rotation_deg=0.0,
            parasitic_offset_u_mm=0.0,
            parasitic_offset_v_mm=0.0,
            air_gap_mm=0.80,
        ),
        clone_candidate(
            gain_base,
            f"{gain_base.name}_stack_p9p75_gap1p20",
            "Enable the stacked parasitic geometry that previously gave the best dual-pol calibration tradeoff.",
            dualpol_parasitic_enabled=1.0,
            parasitic_side_mm=9.75,
            parasitic_corner_cut_mm=0.0,
            parasitic_rotation_deg=0.0,
            parasitic_offset_u_mm=0.0,
            parasitic_offset_v_mm=0.0,
            air_gap_mm=1.20,
        ),
        clone_candidate(
            gain_base,
            f"{gain_base.name}_stack_p9p95_gap1p60",
            "Use a larger and higher parasitic patch to check whether horizon gain improves through aperture enlargement.",
            dualpol_parasitic_enabled=1.0,
            parasitic_side_mm=9.95,
            parasitic_corner_cut_mm=0.0,
            parasitic_rotation_deg=0.0,
            parasitic_offset_u_mm=0.0,
            parasitic_offset_v_mm=0.0,
            air_gap_mm=1.60,
        ),
        clone_candidate(
            gain_base,
            f"{gain_base.name}_slit4p0_off0p45",
            "Add an off-center 45 degree patch slit to disturb the current null near the low-elevation FOV edge.",
            slot_coupled_patch_slit_enabled=1.0,
            slot_coupled_patch_slit_length_mm=4.0,
            slot_coupled_patch_slit_width_mm=0.12,
            slot_coupled_patch_slit_angle_deg=45.0,
            slot_coupled_patch_slit_offset_u_mm=0.45,
            slot_coupled_patch_slit_offset_v_mm=0.45,
        ),
        clone_candidate(
            gain_base,
            f"{gain_base.name}_weakline2p4_gap0p12",
            "Add a weak floating line above the patch to test whether a parasitic current path fills the horizon null.",
            weak_coupling_open_line_enabled=1.0,
            weak_coupling_open_line_length_mm=2.40,
            weak_coupling_open_line_width_mm=0.12,
            weak_coupling_open_line_offset_mm=1.65,
            weak_coupling_open_line_gap_mm=0.12,
        ),
        clone_candidate(
            gain_base,
            f"{gain_base.name}_slit5p0_offu0p80_v0p00",
            "Shift the slit toward the u-edge and lengthen it slightly to target the remaining low-elevation null.",
            slot_coupled_patch_slit_enabled=1.0,
            slot_coupled_patch_slit_length_mm=5.0,
            slot_coupled_patch_slit_width_mm=0.12,
            slot_coupled_patch_slit_angle_deg=45.0,
            slot_coupled_patch_slit_offset_u_mm=0.80,
            slot_coupled_patch_slit_offset_v_mm=0.00,
        ),
        clone_candidate(
            gain_base,
            f"{gain_base.name}_slit5p0_offu0p00_v0p80",
            "Shift the slit toward the v-edge and lengthen it slightly to target the remaining low-elevation null.",
            slot_coupled_patch_slit_enabled=1.0,
            slot_coupled_patch_slit_length_mm=5.0,
            slot_coupled_patch_slit_width_mm=0.12,
            slot_coupled_patch_slit_angle_deg=45.0,
            slot_coupled_patch_slit_offset_u_mm=0.00,
            slot_coupled_patch_slit_offset_v_mm=0.80,
        ),
        clone_candidate(
            gain_base,
            f"{gain_base.name}_slit5p5_offu0p60_v0p00",
            "Use a longer u-offset slit to see whether a stronger asymmetry fills the phi=45 deg dip.",
            slot_coupled_patch_slit_enabled=1.0,
            slot_coupled_patch_slit_length_mm=5.5,
            slot_coupled_patch_slit_width_mm=0.12,
            slot_coupled_patch_slit_angle_deg=45.0,
            slot_coupled_patch_slit_offset_u_mm=0.60,
            slot_coupled_patch_slit_offset_v_mm=0.00,
        ),
        clone_candidate(
            gain_base,
            f"{gain_base.name}_slit5p5_offu0p00_v0p60",
            "Use a longer v-offset slit to see whether a stronger asymmetry fills the phi=45 deg dip.",
            slot_coupled_patch_slit_enabled=1.0,
            slot_coupled_patch_slit_length_mm=5.5,
            slot_coupled_patch_slit_width_mm=0.12,
            slot_coupled_patch_slit_angle_deg=45.0,
            slot_coupled_patch_slit_offset_u_mm=0.00,
            slot_coupled_patch_slit_offset_v_mm=0.60,
        ),
        clone_candidate(
            gain_base,
            f"{gain_base.name}_slit3p6_off0p35",
            "Use a shorter, less-offset diagonal slit to bracket the current 4.0 mm best point.",
            slot_coupled_patch_slit_enabled=1.0,
            slot_coupled_patch_slit_length_mm=3.6,
            slot_coupled_patch_slit_width_mm=0.12,
            slot_coupled_patch_slit_angle_deg=45.0,
            slot_coupled_patch_slit_offset_u_mm=0.35,
            slot_coupled_patch_slit_offset_v_mm=0.35,
        ),
        clone_candidate(
            gain_base,
            f"{gain_base.name}_slit3p8_off0p45",
            "Trim the winning diagonal slit slightly while keeping the same offset to test a local optimum.",
            slot_coupled_patch_slit_enabled=1.0,
            slot_coupled_patch_slit_length_mm=3.8,
            slot_coupled_patch_slit_width_mm=0.12,
            slot_coupled_patch_slit_angle_deg=45.0,
            slot_coupled_patch_slit_offset_u_mm=0.45,
            slot_coupled_patch_slit_offset_v_mm=0.45,
        ),
        clone_candidate(
            gain_base,
            f"{gain_base.name}_slit4p0_w0p16_off0p45",
            "Widen the current best diagonal slit to see whether a stronger but still symmetric perturbation helps.",
            slot_coupled_patch_slit_enabled=1.0,
            slot_coupled_patch_slit_length_mm=4.0,
            slot_coupled_patch_slit_width_mm=0.16,
            slot_coupled_patch_slit_angle_deg=45.0,
            slot_coupled_patch_slit_offset_u_mm=0.45,
            slot_coupled_patch_slit_offset_v_mm=0.45,
        ),
        clone_candidate(
            gain_base,
            f"{gain_base.name}_slit4p0_ang30_off0p45",
            "Rotate the current best slit to 30 degrees to check angular sensitivity around the horizon dip.",
            slot_coupled_patch_slit_enabled=1.0,
            slot_coupled_patch_slit_length_mm=4.0,
            slot_coupled_patch_slit_width_mm=0.12,
            slot_coupled_patch_slit_angle_deg=30.0,
            slot_coupled_patch_slit_offset_u_mm=0.45,
            slot_coupled_patch_slit_offset_v_mm=0.45,
        ),
        clone_candidate(
            gain_base,
            f"{gain_base.name}_neutralizer2p2",
            "Enable the underfeed neutralizer to test whether it lifts the theta=90 deg horizon dip.",
            slot_coupled_underfeed_neutralizer_enabled=1.0,
            slot_coupled_underfeed_neutralizer_length_mm=2.20,
            slot_coupled_underfeed_neutralizer_width_mm=0.12,
            slot_coupled_underfeed_neutralizer_offset_mm=1.20,
            slot_coupled_underfeed_neutralizer_z_offset_mm=0.06,
        ),
        clone_candidate(
            gain_base,
            f"{gain_base.name}_neutralizer2p2_z0p10",
            "Raise the neutralizer above the feed a little to see if the horizon field becomes stronger.",
            slot_coupled_underfeed_neutralizer_enabled=1.0,
            slot_coupled_underfeed_neutralizer_length_mm=2.20,
            slot_coupled_underfeed_neutralizer_width_mm=0.12,
            slot_coupled_underfeed_neutralizer_offset_mm=1.20,
            slot_coupled_underfeed_neutralizer_z_offset_mm=0.10,
        ),
        clone_candidate(
            gain_base,
            f"{gain_base.name}_neutralizer2p6",
            "Lengthen the neutralizer to see whether a stronger parasitic line fills the remaining low-elevation null.",
            slot_coupled_underfeed_neutralizer_enabled=1.0,
            slot_coupled_underfeed_neutralizer_length_mm=2.60,
            slot_coupled_underfeed_neutralizer_width_mm=0.12,
            slot_coupled_underfeed_neutralizer_offset_mm=1.20,
            slot_coupled_underfeed_neutralizer_z_offset_mm=0.06,
        ),
        clone_candidate(
            gain_base,
            f"{gain_base.name}_neutralizer2p2_abc",
            "Combine the neutralizer with the A/B cancellation network to check whether the edge dip can be lifted without killing match.",
            slot_coupled_underfeed_neutralizer_enabled=1.0,
            slot_coupled_underfeed_neutralizer_length_mm=2.20,
            slot_coupled_underfeed_neutralizer_width_mm=0.12,
            slot_coupled_underfeed_neutralizer_offset_mm=1.20,
            slot_coupled_underfeed_neutralizer_z_offset_mm=0.06,
            slot_coupled_ab_cancel_enabled=1.0,
            slot_coupled_ab_cancel_coupling_length_mm=1.80,
            slot_coupled_ab_cancel_trace_width_mm=0.12,
            slot_coupled_ab_cancel_gap_mm=0.12,
            slot_coupled_ab_cancel_phase_offset_mm=2.10,
            slot_coupled_ab_cancel_side_sign=1.0,
            slot_coupled_ab_cancel_z_offset_mm=0.06,
        ),
        clone_candidate(
            gain_base,
            f"{gain_base.name}_horizonloop5p8_clean",
            "Switch the radiator to a square horizon loop and remove the earlier slit / neutralizer / match tweaks.",
            dualpol_parasitic_enabled=0.0,
            slot_coupled_a_neck_enabled=0.0,
            slot_coupled_underfeed_neutralizer_enabled=0.0,
            slot_coupled_patch_slit_enabled=0.0,
            slot_coupled_ab_cancel_enabled=0.0,
            slot_coupled_stub_enabled=0.0,
            slot_coupled_stub2_enabled=0.0,
            slot_coupled_step_enabled=0.0,
            slot_coupled_shield_via_enabled=0.0,
            slot_coupled_horizon_loop_enabled=1.0,
            slot_coupled_horizon_loop_inner_side_mm=5.8,
            slot_coupled_horizon_loop_offset_u_mm=0.0,
            slot_coupled_horizon_loop_offset_v_mm=0.0,
        ),
        clone_candidate(
            gain_base,
            f"{gain_base.name}_horizonloop6p2_clean",
            "Switch the radiator to a square horizon loop and remove the earlier slit / neutralizer / match tweaks.",
            dualpol_parasitic_enabled=0.0,
            slot_coupled_a_neck_enabled=0.0,
            slot_coupled_underfeed_neutralizer_enabled=0.0,
            slot_coupled_patch_slit_enabled=0.0,
            slot_coupled_ab_cancel_enabled=0.0,
            slot_coupled_stub_enabled=0.0,
            slot_coupled_stub2_enabled=0.0,
            slot_coupled_step_enabled=0.0,
            slot_coupled_shield_via_enabled=0.0,
            slot_coupled_horizon_loop_enabled=1.0,
            slot_coupled_horizon_loop_inner_side_mm=6.2,
            slot_coupled_horizon_loop_offset_u_mm=0.0,
            slot_coupled_horizon_loop_offset_v_mm=0.0,
        ),
        clone_candidate(
            gain_base,
            f"{gain_base.name}_horizonloop6p6_clean",
            "Switch the radiator to a square horizon loop and remove the earlier slit / neutralizer / match tweaks.",
            dualpol_parasitic_enabled=0.0,
            slot_coupled_a_neck_enabled=0.0,
            slot_coupled_underfeed_neutralizer_enabled=0.0,
            slot_coupled_patch_slit_enabled=0.0,
            slot_coupled_ab_cancel_enabled=0.0,
            slot_coupled_stub_enabled=0.0,
            slot_coupled_stub2_enabled=0.0,
            slot_coupled_step_enabled=0.0,
            slot_coupled_shield_via_enabled=0.0,
            slot_coupled_horizon_loop_enabled=1.0,
            slot_coupled_horizon_loop_inner_side_mm=6.6,
            slot_coupled_horizon_loop_offset_u_mm=0.0,
            slot_coupled_horizon_loop_offset_v_mm=0.0,
        ),
        clone_candidate(
            gain_base,
            f"{gain_base.name}_edgearm2p4_w0p30",
            "Add a connected radial edge arm to inject a stronger horizontal-plane current path while keeping the best slit baseline.",
            slot_coupled_edge_arm_enabled=1.0,
            slot_coupled_edge_arm_length_mm=2.40,
            slot_coupled_edge_arm_width_mm=0.30,
            slot_coupled_edge_arm_offset_mm=0.0,
            slot_coupled_edge_arm_gap_mm=0.0,
        ),
        clone_candidate(
            gain_base,
            f"{gain_base.name}_edgearm3p2_w0p30",
            "Lengthen the radial edge arm to see whether stronger board-edge current lifts the theta=90 deg FOV null.",
            slot_coupled_edge_arm_enabled=1.0,
            slot_coupled_edge_arm_length_mm=3.20,
            slot_coupled_edge_arm_width_mm=0.30,
            slot_coupled_edge_arm_offset_mm=0.0,
            slot_coupled_edge_arm_gap_mm=0.0,
        ),
        clone_candidate(
            gain_base,
            f"{gain_base.name}_edgewall2p0_w0p50",
            "Add a low vertical edge wall as a compact current branch aimed at horizontal-plane radiation.",
            slot_coupled_edge_wall_enabled=1.0,
            slot_coupled_edge_wall_height_mm=2.00,
            slot_coupled_edge_wall_width_mm=0.50,
            slot_coupled_edge_wall_offset_mm=0.0,
        ),
        clone_candidate(
            gain_base,
            f"{gain_base.name}_edgewall3p0_w0p45",
            "Use a taller narrow vertical edge wall to test whether a stronger monopole-like branch improves FOV floor.",
            slot_coupled_edge_wall_enabled=1.0,
            slot_coupled_edge_wall_height_mm=3.00,
            slot_coupled_edge_wall_width_mm=0.45,
            slot_coupled_edge_wall_offset_mm=0.0,
        ),
    ]
    for item in custom:
        if item.name not in seen:
            pool.append(item)
            seen.add(item.name)
    return pool


def get_gain_grid(hfss, freq_ghz: float) -> list[dict[str, float]]:
    expressions = ["dB(GainTotal)", "dB(RealizedGainTotal)"]
    sd = hfss.post.get_solution_data(
        expressions=expressions,
        setup_sweep_name=SOLUTION,
        domain="Sweep",
        variations={"Freq": [f"{freq_ghz:g}GHz"], "Theta": ["All"], "Phi": ["All"]},
        primary_sweep_variable="Phi",
        report_category="Far Fields",
        context=SPHERE,
    )
    if not sd:
        raise RuntimeError("No far-field gain data returned by HFSS")
    theta_values = axis_values(sd, "Theta")
    phi_values = axis_values(sd, "Phi")
    gain_total = [float(value) for value in sd.data_real("dB(GainTotal)")]
    realized = [float(value) for value in sd.data_real("dB(RealizedGainTotal)")]
    expected = len(theta_values) * len(phi_values)
    if len(gain_total) != expected or len(realized) != expected:
        raise RuntimeError(f"Unexpected gain grid length: expected {expected}, got {len(gain_total)}")

    rows = []
    idx = 0
    for phi in phi_values:
        for theta in theta_values:
            if THETA_MIN_DEG - 1e-9 <= theta <= THETA_MAX_DEG + 1e-9:
                rows.append(
                    {
                        "theta_deg": theta,
                        "phi_deg": phi,
                        "gain_total_dbi": gain_total[idx],
                        "realized_gain_total_dbi": realized[idx],
                    }
                )
            idx += 1
    if not rows:
        raise RuntimeError(f"No FOV rows found for Theta {THETA_MIN_DEG}-{THETA_MAX_DEG} deg")
    return rows


def summarize_source_rows(fov_rows: list[dict[str, float]]) -> dict[str, Any]:
    min_gain = min(fov_rows, key=lambda row: row["gain_total_dbi"])
    min_realized = min(fov_rows, key=lambda row: row["realized_gain_total_dbi"])
    max_gain = max(fov_rows, key=lambda row: row["gain_total_dbi"])
    max_realized = max(fov_rows, key=lambda row: row["realized_gain_total_dbi"])
    return {
        "fov_sample_count": len(fov_rows),
        "fov_gain_total_min_dbi": min_gain["gain_total_dbi"],
        "fov_gain_total_min_theta_deg": min_gain["theta_deg"],
        "fov_gain_total_min_phi_deg": min_gain["phi_deg"],
        "fov_realized_gain_total_min_dbi": min_realized["realized_gain_total_dbi"],
        "fov_realized_gain_total_min_theta_deg": min_realized["theta_deg"],
        "fov_realized_gain_total_min_phi_deg": min_realized["phi_deg"],
        "fov_gain_total_max_dbi": max_gain["gain_total_dbi"],
        "fov_gain_total_max_theta_deg": max_gain["theta_deg"],
        "fov_gain_total_max_phi_deg": max_gain["phi_deg"],
        "fov_realized_gain_total_max_dbi": max_realized["realized_gain_total_dbi"],
        "fov_realized_gain_total_max_theta_deg": max_realized["theta_deg"],
        "fov_realized_gain_total_max_phi_deg": max_realized["phi_deg"],
    }


def summarize_coverage(coverage: dict[tuple[float, float, float], dict[str, Any]]) -> dict[str, Any]:
    points = list(coverage.values())
    min_gain = min(points, key=lambda row: row["coverage_gain_total_dbi"])
    min_realized = min(points, key=lambda row: row["coverage_realized_gain_total_dbi"])
    return {
        "coverage_sample_count": len(points),
        "coverage_gain_total_min_dbi": min_gain["coverage_gain_total_dbi"],
        "coverage_gain_total_min_source": min_gain["coverage_gain_total_source"],
        "coverage_gain_total_min_freq_ghz": min_gain["freq_ghz"],
        "coverage_gain_total_min_theta_deg": min_gain["theta_deg"],
        "coverage_gain_total_min_phi_deg": min_gain["phi_deg"],
        "coverage_realized_gain_total_min_dbi": min_realized["coverage_realized_gain_total_dbi"],
        "coverage_realized_gain_total_min_source": min_realized["coverage_realized_gain_total_source"],
        "coverage_realized_gain_total_min_freq_ghz": min_realized["freq_ghz"],
        "coverage_realized_gain_total_min_theta_deg": min_realized["theta_deg"],
        "coverage_realized_gain_total_min_phi_deg": min_realized["phi_deg"],
    }


def update_coverage(
    coverage: dict[tuple[float, float, float], dict[str, Any]],
    freq: float,
    source: str,
    fov_rows: list[dict[str, float]],
) -> None:
    for row in fov_rows:
        key = (freq, row["theta_deg"], row["phi_deg"])
        item = coverage.setdefault(
            key,
            {
                "freq_ghz": freq,
                "theta_deg": row["theta_deg"],
                "phi_deg": row["phi_deg"],
                "coverage_gain_total_dbi": -1e9,
                "coverage_gain_total_source": "",
                "coverage_realized_gain_total_dbi": -1e9,
                "coverage_realized_gain_total_source": "",
            },
        )
        if row["gain_total_dbi"] > item["coverage_gain_total_dbi"]:
            item["coverage_gain_total_dbi"] = row["gain_total_dbi"]
            item["coverage_gain_total_source"] = source
        if row["realized_gain_total_dbi"] > item["coverage_realized_gain_total_dbi"]:
            item["coverage_realized_gain_total_dbi"] = row["realized_gain_total_dbi"]
            item["coverage_realized_gain_total_source"] = source


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(rows[0])
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: f"{row[key]:.6f}" if isinstance(row.get(key), float) else row.get(key, "") for key in fields})


def read_csv(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def numeric(row: dict[str, Any], key: str, default: float = 0.0) -> float:
    try:
        return float(row.get(key, default))
    except (TypeError, ValueError):
        return default


def rank_summary(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        rows,
        key=lambda row: (
            -numeric(row, "strict_fov_realized_gain_total_min_dbi", -1e9),
            -numeric(row, "strict_fov_gain_total_min_dbi", -1e9),
            -numeric(row, "coverage_fov_realized_gain_total_min_dbi", -1e9),
            numeric(row, "worst_active_s11_db", 0.0),
        ),
    )


def summarize_candidate(
    candidate_index: int,
    candidate: GainCandidate,
    source_rows: list[dict[str, Any]],
    coverage_rows: list[dict[str, Any]],
    s11_rows: list[dict[str, Any]],
    projects: dict[str, str],
    elapsed_s: float,
) -> dict[str, Any]:
    strict_worst_gain = min(source_rows, key=lambda row: row["fov_gain_total_min_dbi"])
    strict_worst_realized = min(source_rows, key=lambda row: row["fov_realized_gain_total_min_dbi"])
    coverage_worst_gain = min(coverage_rows, key=lambda row: row["coverage_gain_total_min_dbi"])
    coverage_worst_realized = min(coverage_rows, key=lambda row: row["coverage_realized_gain_total_min_dbi"])
    worst_s11 = max(s11_rows, key=lambda row: row["worst_return_db"])
    return {
        "candidate_index": candidate_index,
        "candidate": candidate.name,
        "rationale": candidate.rationale,
        "elapsed_s": elapsed_s,
        "strict_fov_gain_total_min_dbi": strict_worst_gain["fov_gain_total_min_dbi"],
        "strict_fov_gain_total_worst_case": strict_worst_gain["case"],
        "strict_fov_gain_total_worst_source": strict_worst_gain["source"],
        "strict_fov_gain_total_worst_freq_ghz": strict_worst_gain["freq_ghz"],
        "strict_fov_gain_total_worst_theta_deg": strict_worst_gain["fov_gain_total_min_theta_deg"],
        "strict_fov_gain_total_worst_phi_deg": strict_worst_gain["fov_gain_total_min_phi_deg"],
        "strict_fov_realized_gain_total_min_dbi": strict_worst_realized["fov_realized_gain_total_min_dbi"],
        "strict_fov_realized_gain_total_worst_case": strict_worst_realized["case"],
        "strict_fov_realized_gain_total_worst_source": strict_worst_realized["source"],
        "strict_fov_realized_gain_total_worst_freq_ghz": strict_worst_realized["freq_ghz"],
        "strict_fov_realized_gain_total_worst_theta_deg": strict_worst_realized["fov_realized_gain_total_min_theta_deg"],
        "strict_fov_realized_gain_total_worst_phi_deg": strict_worst_realized["fov_realized_gain_total_min_phi_deg"],
        "coverage_fov_gain_total_min_dbi": coverage_worst_gain["coverage_gain_total_min_dbi"],
        "coverage_fov_gain_total_worst_case": coverage_worst_gain["case"],
        "coverage_fov_gain_total_worst_source": coverage_worst_gain["coverage_gain_total_min_source"],
        "coverage_fov_gain_total_worst_freq_ghz": coverage_worst_gain["coverage_gain_total_min_freq_ghz"],
        "coverage_fov_gain_total_worst_theta_deg": coverage_worst_gain["coverage_gain_total_min_theta_deg"],
        "coverage_fov_gain_total_worst_phi_deg": coverage_worst_gain["coverage_gain_total_min_phi_deg"],
        "coverage_fov_realized_gain_total_min_dbi": coverage_worst_realized["coverage_realized_gain_total_min_dbi"],
        "coverage_fov_realized_gain_total_worst_case": coverage_worst_realized["case"],
        "coverage_fov_realized_gain_total_worst_source": coverage_worst_realized["coverage_realized_gain_total_min_source"],
        "coverage_fov_realized_gain_total_worst_freq_ghz": coverage_worst_realized["coverage_realized_gain_total_min_freq_ghz"],
        "coverage_fov_realized_gain_total_worst_theta_deg": coverage_worst_realized["coverage_realized_gain_total_min_theta_deg"],
        "coverage_fov_realized_gain_total_worst_phi_deg": coverage_worst_realized["coverage_realized_gain_total_min_phi_deg"],
        "strict_gain_target_pass": strict_worst_gain["fov_gain_total_min_dbi"] >= GAIN_TARGET_DBI,
        "strict_realized_gain_target_pass": strict_worst_realized["fov_realized_gain_total_min_dbi"] >= GAIN_TARGET_DBI,
        "coverage_gain_target_pass": coverage_worst_gain["coverage_gain_total_min_dbi"] >= GAIN_TARGET_DBI,
        "coverage_realized_gain_target_pass": coverage_worst_realized["coverage_realized_gain_total_min_dbi"] >= GAIN_TARGET_DBI,
        "worst_active_s11_db": worst_s11["worst_return_db"],
        "worst_active_s11_case": worst_s11["case"],
        "all_workstate_s11_pass": all(row["s11_pass"] for row in s11_rows),
        "projects": projects,
    }


def evaluate_candidate(
    candidate_index: int,
    candidate: GainCandidate,
    copy_projects: bool,
    settle_seconds: float,
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    started = time.time()
    print(f"=== FOV gain candidate {candidate_index}: {candidate.name} ===", flush=True)
    all_source_rows: list[dict[str, Any]] = []
    all_coverage_rows: list[dict[str, Any]] = []
    s11_rows: list[dict[str, Any]] = []
    projects: dict[str, str] = {}
    cases = [workstate.CASES[0], workstate.CASES[1]]

    for case in cases:
        case_started = time.time()
        params = workstate.set_case_params(candidate.params, case)
        builder.TOPOLOGIES[TOPOLOGY]["params"] = params
        project_path, hfss = builder.build_project(
            TOPOLOGY,
            analyze=True,
            non_graphical=True,
            quick=True,
            band_samples=True,
            sparam_only=False,
            return_hfss=True,
            analysis_cores=8,
            analysis_tasks=8,
        )
        try:
            sparams = topology_eval.get_s_parameter_snapshot(
                hfss,
                REPORT_DIR / f"{STEM}_{candidate_index:02d}_{safe_slug(candidate.name, 48)}_{case.name}_s_parameters.csv",
            )
            s11_row = workstate.summarize_case(case, sparams, time.time() - case_started)
            s11_row.update({"candidate_index": candidate_index, "candidate": candidate.name})
            s11_rows.append(s11_row)

            sources = hfss.get_all_sources()
            eval_freqs = pdoa_eval.nearest_frequencies(pdoa_eval.get_available_frequencies(hfss))
            coverage_by_point: dict[tuple[float, float, float], dict[str, Any]] = {}
            for source in sources:
                hfss.edit_sources({item: (1.0 if item == source else 0.0, 0.0) for item in sources})
                for freq in eval_freqs:
                    fov_rows = get_gain_grid(hfss, freq)
                    update_coverage(coverage_by_point, freq, source, fov_rows)
                    row = summarize_source_rows(fov_rows)
                    row.update(
                        {
                            "candidate_index": candidate_index,
                            "candidate": candidate.name,
                            "case": case.name,
                            "active_pol": case.active_pol,
                            "source": source,
                            "freq_ghz": freq,
                        }
                    )
                    all_source_rows.append(row)

            coverage_summary = summarize_coverage(coverage_by_point)
            coverage_summary.update(
                {
                    "candidate_index": candidate_index,
                    "candidate": candidate.name,
                    "case": case.name,
                    "active_pol": case.active_pol,
                }
            )
            all_coverage_rows.append(coverage_summary)
        finally:
            hfss.release_desktop(close_projects=False, close_desktop=True)

        if copy_projects:
            copy_path = REPORT_DIR / f"{STEM}_{candidate_index:02d}_{safe_slug(candidate.name)}_{case.name}.aedt"
            shutil.copy2(project_path, copy_path)
            projects[case.name] = str(copy_path)
        if settle_seconds > 0:
            print(f"Stage: AEDT settle wait {settle_seconds:.1f}s", flush=True)
            time.sleep(settle_seconds)
    summary = summarize_candidate(candidate_index, candidate, all_source_rows, all_coverage_rows, s11_rows, projects, time.time() - started)
    print(
        json.dumps(
            {
                "candidate": summary["candidate"],
                "strict_realized_min_dbi": summary["strict_fov_realized_gain_total_min_dbi"],
                "coverage_realized_min_dbi": summary["coverage_fov_realized_gain_total_min_dbi"],
                "worst_active_s11_db": summary["worst_active_s11_db"],
            },
            indent=2,
            ensure_ascii=False,
        ),
        flush=True,
    )
    return summary, all_source_rows, all_coverage_rows


def write_report(payload: dict[str, Any]) -> None:
    ranked = rank_summary(payload["summary_rows"])
    best = ranked[0]
    strict_ok = bool_field(best["strict_gain_target_pass"]) and bool_field(best["strict_realized_gain_target_pass"])
    coverage_ok = bool_field(best["coverage_gain_target_pass"]) and bool_field(best["coverage_realized_gain_target_pass"])
    lines = [
        "# D44 RF Switch 工作态 FOV 增益优化报告",
        "",
        "## 目标与坐标口径",
        "",
        f"- HFSS 球坐标口径：`Theta={THETA_MIN_DEG:.0f}..{THETA_MAX_DEG:.0f} deg`，`Phi=0..360 deg`；对应从水平面到上仰 45 deg 的完整 360 deg 方位覆盖。",
        f"- 目标：FOV 内 `GainTotal` 与 `RealizedGainTotal` 均 `>= {GAIN_TARGET_DBI:.1f} dBi`。",
        "- 工作态：只评估工程有效的吸收式 off 端 `50 ohm // 0.08 pF`，分别为 A_ON 与 B_ON。",
        "- 严格口径：每个选通端口单独激励，其余选通端口关断，逐端口/逐频点/逐方向都必须满足。",
        "- 覆盖口径：同一工作态、同一频点和方向上，在四个选通端口里取最高增益，反映阵列端口选择后的覆盖上限。",
        "",
        "## 当前最佳",
        "",
        f"- 候选：`{best['candidate']}`",
        f"- 严格口径最小 GainTotal：`{fmt(best['strict_fov_gain_total_min_dbi'])} dBi`。",
        f"- 严格口径最小 RealizedGainTotal：`{fmt(best['strict_fov_realized_gain_total_min_dbi'])} dBi`。",
        f"- 覆盖口径最小 GainTotal：`{fmt(best['coverage_fov_gain_total_min_dbi'])} dBi`。",
        f"- 覆盖口径最小 RealizedGainTotal：`{fmt(best['coverage_fov_realized_gain_total_min_dbi'])} dBi`。",
        f"- 工作态最差 S11：`{fmt(best['worst_active_s11_db'])} dB`。",
        f"- 结论：严格口径 `{'达标' if strict_ok else '未达标'}`，覆盖口径 `{'达标' if coverage_ok else '未达标'}`。",
        "",
        "## 候选排名",
        "",
        "| 排名 | 候选 | 严格 Realized 最小值 | 严格 Gain 最小值 | 覆盖 Realized 最小值 | 覆盖 Gain 最小值 | 最差 S11 |",
        "| ---: | --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for idx, row in enumerate(ranked, start=1):
        lines.append(
            f"| {idx} | `{row['candidate']}` | {fmt(row['strict_fov_realized_gain_total_min_dbi'])} dBi | "
            f"{fmt(row['strict_fov_gain_total_min_dbi'])} dBi | {fmt(row['coverage_fov_realized_gain_total_min_dbi'])} dBi | "
            f"{fmt(row['coverage_fov_gain_total_min_dbi'])} dBi | {fmt(row['worst_active_s11_db'])} dB |"
        )
    lines.extend(
        [
            "",
            "## 最差点",
            "",
            f"- 严格口径最差 Realized：`{best['strict_fov_realized_gain_total_worst_case']}` / `{best['strict_fov_realized_gain_total_worst_source']}` / "
            f"{fmt(best['strict_fov_realized_gain_total_worst_freq_ghz'], 4)} GHz / Theta {fmt(best['strict_fov_realized_gain_total_worst_theta_deg'], 0)} deg / Phi {fmt(best['strict_fov_realized_gain_total_worst_phi_deg'], 0)} deg。",
            f"- 覆盖口径最差 Realized：`{best['coverage_fov_realized_gain_total_worst_case']}` / best source `{best['coverage_fov_realized_gain_total_worst_source']}` / "
            f"{fmt(best['coverage_fov_realized_gain_total_worst_freq_ghz'], 4)} GHz / Theta {fmt(best['coverage_fov_realized_gain_total_worst_theta_deg'], 0)} deg / Phi {fmt(best['coverage_fov_realized_gain_total_worst_phi_deg'], 0)} deg。",
            "",
            "## 工程判断",
            "",
        ]
    )
    if strict_ok:
        lines.append("- 本轮已在最保守逐端口口径下达到目标，可进入更细频点、更细角度和制造容差复核。")
    elif coverage_ok:
        lines.append("- 单端口嵌入方向图仍有深谷，但端口选择覆盖已达到目标；如果系统允许按方位选择阵元/端口，可继续转入切换策略和标定验证。")
    else:
        lines.append("- 本轮尚未达到 -5 dBi FOV 目标。最差点仍落在 Theta=90 deg 附近，说明当前低剖面贴片/孔缝结构在水平面方向存在结构性辐射低谷。")
        lines.append("- 继续只调 S11 匹配网络收益有限；下一轮应加入面向水平面辐射的结构，例如边缘寄生/折叠单极子、垂直电流支路、或独立的低仰角覆盖单元。")
    lines.extend(
        [
            "",
            "## 输出文件",
            "",
            f"- 候选汇总 CSV：`{SUMMARY_CSV}`",
            f"- 逐端口明细 CSV：`{SOURCE_CSV}`",
            f"- 覆盖口径明细 CSV：`{COVERAGE_CSV}`",
            f"- 指标 JSON：`{METRICS_JSON}`",
        ]
    )
    for case, path in coerce_project_map(best.get("projects")).items():
        lines.append(f"- 最佳 `{case}` AEDT 快照：`{path}`")
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_report(payload: dict[str, Any]) -> None:
    ranked = rank_summary(payload["summary_rows"])
    best = ranked[0]
    strict_ok = bool_field(best["strict_gain_target_pass"]) and bool_field(best["strict_realized_gain_target_pass"])
    coverage_ok = bool_field(best["coverage_gain_target_pass"]) and bool_field(best["coverage_realized_gain_target_pass"])
    lines = [
        "# D44 RF Switch 工作态 FOV 增益优化报告",
        "",
        "## 目标与坐标口径",
        "",
        f"- HFSS 球坐标口径：`Theta={THETA_MIN_DEG:.0f}..{THETA_MAX_DEG:.0f} deg`，`Phi=0..360 deg`；对应从水平面到上仰 45 deg 的完整 360 deg 方位覆盖。",
        f"- 增益目标：FOV 内 `GainTotal` 与 `RealizedGainTotal` 均 `>= {GAIN_TARGET_DBI:.1f} dBi`。",
        "- 工作态：只评估工程有效的吸收式 off 端 `50 ohm // 0.08 pF`，分别为 A_ON 与 B_ON。",
        f"- 匹配约束：选通工作态最差 S11 需不高于 `{RETURN_TARGET_DB:.1f} dB`。",
        "- 严格口径：每个选通端口单独激励，其他选通端口关闭，逐端口、逐频点、逐方向均需满足。",
        "- 覆盖口径：同一工作态、同一频点和方向上，在四个选通端口里取最高增益，反映阵列端口选择后的覆盖上限。",
        f"- 本轮报告包含 `{len(ranked)}` 条候选记录；本次运行入口为 `{payload.get('evaluated_start_index', 'N/A')}`，计划评估 `{payload.get('evaluated_count', 'N/A')}` 条，总候选池 `{payload.get('candidate_count', len(ranked))}` 条。",
        "",
        "## 当前最佳",
        "",
        f"- 候选：`{best['candidate']}`",
        f"- 严格口径最小 GainTotal：`{fmt(best['strict_fov_gain_total_min_dbi'])} dBi`。",
        f"- 严格口径最小 RealizedGainTotal：`{fmt(best['strict_fov_realized_gain_total_min_dbi'])} dBi`。",
        f"- 覆盖口径最小 GainTotal：`{fmt(best['coverage_fov_gain_total_min_dbi'])} dBi`。",
        f"- 覆盖口径最小 RealizedGainTotal：`{fmt(best['coverage_fov_realized_gain_total_min_dbi'])} dBi`。",
        f"- 工作态最差 S11：`{fmt(best['worst_active_s11_db'])} dB`。",
        f"- 结论：严格口径 `{'达标' if strict_ok else '未达标'}`，覆盖口径 `{'达标' if coverage_ok else '未达标'}`。",
        "",
        "## 候选排名",
        "",
        "| 排名 | 候选 | 严格 Realized 最小值 | 严格 Gain 最小值 | 覆盖 Realized 最小值 | 覆盖 Gain 最小值 | 最差 S11 |",
        "| ---: | --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for idx, row in enumerate(ranked, start=1):
        lines.append(
            f"| {idx} | `{row['candidate']}` | {fmt(row['strict_fov_realized_gain_total_min_dbi'])} dBi | "
            f"{fmt(row['strict_fov_gain_total_min_dbi'])} dBi | {fmt(row['coverage_fov_realized_gain_total_min_dbi'])} dBi | "
            f"{fmt(row['coverage_fov_gain_total_min_dbi'])} dBi | {fmt(row['worst_active_s11_db'])} dB |"
        )
    lines.extend(
        [
            "",
            "## 最差点",
            "",
            f"- 严格口径最差 Realized：`{best['strict_fov_realized_gain_total_worst_case']}` / `{best['strict_fov_realized_gain_total_worst_source']}` / "
            f"{fmt(best['strict_fov_realized_gain_total_worst_freq_ghz'], 4)} GHz / Theta {fmt(best['strict_fov_realized_gain_total_worst_theta_deg'], 0)} deg / Phi {fmt(best['strict_fov_realized_gain_total_worst_phi_deg'], 0)} deg。",
            f"- 覆盖口径最差 Realized：`{best['coverage_fov_realized_gain_total_worst_case']}` / best source `{best['coverage_fov_realized_gain_total_worst_source']}` / "
            f"{fmt(best['coverage_fov_realized_gain_total_worst_freq_ghz'], 4)} GHz / Theta {fmt(best['coverage_fov_realized_gain_total_worst_theta_deg'], 0)} deg / Phi {fmt(best['coverage_fov_realized_gain_total_worst_phi_deg'], 0)} deg。",
            "",
            "## 工程判断",
            "",
        ]
    )
    if strict_ok:
        lines.append("- 本轮已在最保守逐端口口径下达到目标，可进入更细频点、更细角度和制造容差复核。")
    elif coverage_ok:
        lines.append("- 单端口嵌入方向图仍有深谷，但端口选择覆盖已达到目标；如果系统允许按方位选择阵元/端口，可继续转入切换策略和标定验证。")
    else:
        lines.append("- 本轮尚未达到 -5 dBi FOV 目标。最差点仍落在 Theta=90 deg 附近，说明当前低剖面贴片/孔缝结构在水平面方向存在结构性辐射低谷。")
        lines.append("- 继续只调 S11 匹配网络收益有限；下一轮应优先评估面向水平面辐射的结构，例如边缘寄生辐射臂、折叠单极子、垂直电流支路，或独立低仰角覆盖单元。")
    lines.extend(
        [
            "",
            "## 输出文件",
            "",
            f"- 候选汇总 CSV：`{SUMMARY_CSV}`",
            f"- 逐端口明细 CSV：`{SOURCE_CSV}`",
            f"- 覆盖口径明细 CSV：`{COVERAGE_CSV}`",
            f"- 指标 JSON：`{METRICS_JSON}`",
        ]
    )
    for case, path in coerce_project_map(best.get("projects")).items():
        lines.append(f"- 最佳 `{case}` AEDT 快照：`{path}`")
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run(max_candidates: int, copy_projects: bool, settle_seconds: float, start_index: int, resume: bool) -> dict[str, Any]:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    full_pool = candidate_pool()[:max_candidates]
    pool = full_pool[max(0, start_index - 1) :]
    summary_rows: list[dict[str, Any]] = read_csv(SUMMARY_CSV) if resume else []
    source_rows: list[dict[str, Any]] = read_csv(SOURCE_CSV) if resume else []
    coverage_rows: list[dict[str, Any]] = read_csv(COVERAGE_CSV) if resume else []
    completed = {int(float(row["candidate_index"])) for row in summary_rows if row.get("candidate_index")}
    for idx, candidate in enumerate(pool, start=start_index):
        if idx in completed:
            print(f"Stage: FOV gain candidate {idx} {candidate.name} reused", flush=True)
            continue
        summary, candidate_source_rows, candidate_coverage_rows = evaluate_candidate(idx, candidate, copy_projects, settle_seconds)
        summary_rows.append(summary)
        source_rows.extend(candidate_source_rows)
        coverage_rows.extend(candidate_coverage_rows)
        write_csv(SUMMARY_CSV, summary_rows)
        write_csv(SOURCE_CSV, source_rows)
        write_csv(COVERAGE_CSV, coverage_rows)

    payload = {
        "target": {
            "theta_min_deg": THETA_MIN_DEG,
            "theta_max_deg": THETA_MAX_DEG,
            "phi_min_deg": 0.0,
            "phi_max_deg": 360.0,
            "gain_target_dbi": GAIN_TARGET_DBI,
            "return_target_db": RETURN_TARGET_DB,
        },
        "candidate_count": len(full_pool),
        "evaluated_start_index": start_index,
        "evaluated_count": len(pool),
        "summary_rows": summary_rows,
        "source_csv": str(SOURCE_CSV),
        "coverage_csv": str(COVERAGE_CSV),
        "summary_csv": str(SUMMARY_CSV),
        "report_md": str(REPORT_MD),
    }
    METRICS_JSON.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    write_report(payload)
    print(f"Wrote {REPORT_MD}", flush=True)
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-candidates", type=int, default=6)
    parser.add_argument("--start-index", type=int, default=1)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--copy-projects", action="store_true")
    parser.add_argument("--settle-seconds", type=float, default=15.0, help="Delay after closing each AEDT desktop session")
    args = parser.parse_args()
    run(args.max_candidates, args.copy_projects, args.settle_seconds, args.start_index, args.resume)


if __name__ == "__main__":
    main()
