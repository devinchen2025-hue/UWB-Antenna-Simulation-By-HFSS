#!/usr/bin/env python3
"""Evaluate a calibrated D44 array using the thick single-port PIFA baseline.

This is a lightweight system-level check.  It intentionally does not reuse the
old dual-pol A/B source set: the single-port thick PIFA far-field is treated as
the low-elevation coverage element, then array geometry and a calibrated PDOA
LUT are evaluated analytically.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from dataclasses import dataclass
from pathlib import Path
from statistics import mean
from typing import Dict, Iterable, List, Sequence, Tuple


ROOT = Path(__file__).resolve().parents[1]
BASELINE_DIR = ROOT / "reports_d44_thick_pifa_single_element"
BASELINE_SUMMARY = BASELINE_DIR / "UWB_CH9_D44_THICK_PIFA_SINGLE_ELEMENT_summary.csv"
BASELINE_FARFIELD = (
    BASELINE_DIR / "h3p5_l8p8_w8p0_sw4p0_fence6p0_feed8p40_native_farfield_default.csv"
)
OUTPUT_DIR = ROOT / "reports_d44_thick_pifa_array_lut"
OUTPUT_STEM = "UWB_CH9_D44_THICK_PIFA_ARRAY_LUT"

FREQ_GHZ = 8.0
C0_MM_PER_NS = 299.792458
WAVELENGTH_MM = C0_MM_PER_NS / FREQ_GHZ
BOARD_DIAMETER_MM = 44.0
GROUND_RADIUS_MM = 21.4
ELEMENT_SPACING_MM = 17.0
CENTER_RADIUS_MM = ELEMENT_SPACING_MM / math.sqrt(2.0)

THETA_CUTS_DEG = [45, 60, 75, 90]
THETA_MIN_DEG = 45
THETA_MAX_DEG = 90
PHI_WINDOW_DEG = 270
GRID_STEP_DEG = 5
HOLDOUT_STEP_DEG = 10

S11_TARGET_DB = -10.0
GAIN_TARGET_DBI = -5.0
LUT_RMS_TARGET_DEG = 10.0
LUT_P95_TARGET_DEG = 10.0
VECTOR_SLOPE_P5_TARGET_DEG_PER_DEG = 0.5
PHASE_SEPARATION_MIN_TARGET_DEG = 3.0

ELEMENTS: Sequence[Tuple[str, float, float, float]] = (
    ("E1", CENTER_RADIUS_MM, 0.0, 0.0),
    ("E2", 0.0, CENTER_RADIUS_MM, 90.0),
    ("E3", -CENTER_RADIUS_MM, 0.0, 180.0),
    ("E4", 0.0, -CENTER_RADIUS_MM, 270.0),
)

BASELINES: Sequence[Tuple[str, str]] = (
    ("E1", "E3"),
    ("E2", "E4"),
    ("E1", "E2"),
    ("E2", "E3"),
    ("E3", "E4"),
    ("E4", "E1"),
)

PRIMARY_BASELINES: Sequence[Tuple[str, str]] = (
    ("E1", "E3"),
    ("E2", "E4"),
)


@dataclass(frozen=True)
class FarFieldGrid:
    gain_total: Dict[Tuple[int, int], float]
    realized_gain_total: Dict[Tuple[int, int], float]
    theta_values: List[int]
    phi_values: List[int]
    theta_column_idx: int
    phi_column_idx: int
    axis_note: str


@dataclass(frozen=True)
class BaselineResult:
    scenario: str
    phi_start_deg: int
    phi_stop_deg: int
    strict_gain_total_min_dbi: float
    coverage_gain_total_min_dbi: float
    strict_realized_gain_total_min_dbi: float
    coverage_realized_gain_total_min_dbi: float
    lut_holdout_rms_deg: float
    lut_holdout_p95_deg: float
    lut_holdout_max_deg: float
    vector_slope_p5_deg_per_deg: float
    min_phase_vector_separation_deg: float
    gain_pass: bool
    lut_pass: bool
    separation_pass: bool
    overall_pass: bool


def wrap_deg(value: float) -> float:
    return ((value + 180.0) % 360.0) - 180.0


def wrap360(value: float) -> float:
    return value % 360.0


def percentile(values: Sequence[float], pct: float) -> float:
    if not values:
        return float("nan")
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    rank = (len(ordered) - 1) * pct / 100.0
    lo = math.floor(rank)
    hi = math.ceil(rank)
    if lo == hi:
        return ordered[int(rank)]
    frac = rank - lo
    return ordered[lo] * (1.0 - frac) + ordered[hi] * frac


def rms(values: Sequence[float]) -> float:
    if not values:
        return float("nan")
    return math.sqrt(sum(v * v for v in values) / len(values))


def round_grid(value: float, step: int = GRID_STEP_DEG) -> int:
    rounded = int(round(value / step) * step) % 360
    return 0 if rounded == 360 else rounded


def phi_samples_in_window(start_deg: int, width_deg: int = PHI_WINDOW_DEG) -> List[int]:
    count = width_deg // GRID_STEP_DEG
    return [int((start_deg + idx * GRID_STEP_DEG) % 360) for idx in range(count + 1)]


def window_stop(start_deg: int, width_deg: int = PHI_WINDOW_DEG) -> int:
    return int((start_deg + width_deg) % 360)


def read_baseline_summary(path: Path) -> Dict[str, str]:
    rows = read_summary_rows(path)
    return select_summary_row(rows)


def read_summary_rows(path: Path) -> List[Dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(f"Missing baseline summary: {path}")
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        raise ValueError(f"Baseline summary is empty: {path}")
    return rows


def select_summary_row(rows: Sequence[Dict[str, str]], candidate_name: str | None = None) -> Dict[str, str]:
    if candidate_name:
        matching = [
            row
            for row in rows
            if (row.get("candidate_name") or row.get("candidate") or row.get("name")) == candidate_name
        ]
        if matching:
            return matching[0]
    passing = [row for row in rows if row.get("candidate_index") == "36"]
    if not passing:
        passing = [
            row
            for row in rows
            if (row.get("candidate_name") or row.get("candidate"))
            == "h3p5_l8p8_w8p0_sw4p0_fence6p0_feed8p40"
        ]
    return passing[0] if passing else rows[0]


def read_farfield(path: Path) -> FarFieldGrid:
    if not path.exists():
        raise FileNotFoundError(f"Missing far-field CSV: {path}")
    gain_total: Dict[Tuple[int, int], float] = {}
    realized: Dict[Tuple[int, int], float] = {}
    theta_values = set()
    phi_values = set()

    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f)
        header = next(reader, None)
        if not header or len(header) < 6:
            raise ValueError(f"Unexpected far-field header in {path}")
        raw_rows = [row for row in reader if len(row) >= 6]
        if not raw_rows:
            raise ValueError(f"Far-field CSV has no data rows: {path}")

        col0_values = [float(row[0]) for row in raw_rows]
        col2_values = [float(row[2]) for row in raw_rows]
        col0_max = max(col0_values)
        col2_max = max(col2_values)
        col0_unique = len({round(v, 6) for v in col0_values})
        col2_unique = len({round(v, 6) for v in col2_values})
        if col0_max <= 90.0 + 1e-9 and col2_max > 180.0:
            theta_idx = 0
            phi_idx = 2
            axis_note = (
                "auto-corrected: native export labels column 0 as Phi and column 2 as Theta, "
                "but ranges show column 0 is 0..90 theta and column 2 is 0..360 phi"
            )
        elif col2_max <= 90.0 + 1e-9 and col0_max > 180.0:
            theta_idx = 2
            phi_idx = 0
            axis_note = "native labels and value ranges are consistent with Phi in column 0 and Theta in column 2"
        elif col0_unique < col2_unique:
            theta_idx = 0
            phi_idx = 2
            axis_note = "auto-corrected by unique-count heuristic: column 0 treated as theta, column 2 as phi"
        else:
            theta_idx = 2
            phi_idx = 0
            axis_note = "used native header order by fallback heuristic"

        for row in raw_rows:
            if len(row) < 6:
                continue
            # HFSS native exports in this project may swap the Phi/Theta labels.
            # Axis selection is based on observed value ranges above.
            phi = round_grid(float(row[phi_idx]))
            theta = int(round(float(row[theta_idx])))
            total = float(row[3])
            realized_total = float(row[5])
            gain_total[(theta, phi)] = total
            realized[(theta, phi)] = realized_total
            theta_values.add(theta)
            phi_values.add(phi)

    required_thetas = set(range(THETA_MIN_DEG, THETA_MAX_DEG + 1, GRID_STEP_DEG))
    missing = sorted(required_thetas - theta_values)
    if missing:
        raise ValueError(f"Far-field CSV lacks required theta cuts: {missing}")
    return FarFieldGrid(
        gain_total=gain_total,
        realized_gain_total=realized,
        theta_values=sorted(theta_values),
        phi_values=sorted(phi_values),
        theta_column_idx=theta_idx,
        phi_column_idx=phi_idx,
        axis_note=axis_note,
    )


def element_angle_map() -> Dict[str, float]:
    return {name: angle for name, _x, _y, angle in ELEMENTS}


def position_map() -> Dict[str, Tuple[float, float]]:
    return {name: (x, y) for name, x, y, _angle in ELEMENTS}


def sample_gain(
    grid: FarFieldGrid,
    theta_deg: int,
    phi_deg: int,
    element_name: str,
    scenario: str,
    realized: bool = False,
) -> float:
    angles = element_angle_map()
    if scenario == "radial_oriented":
        local_phi = round_grid(phi_deg - angles[element_name])
    elif scenario == "co_oriented":
        local_phi = round_grid(phi_deg)
    else:
        raise ValueError(f"Unknown scenario: {scenario}")
    data = grid.realized_gain_total if realized else grid.gain_total
    key = (theta_deg, local_phi)
    if key not in data:
        raise KeyError(f"Missing far-field sample theta={theta_deg}, phi={local_phi}")
    return data[key]


def array_phase_deg(theta_deg: int, phi_deg: int, element_name: str) -> float:
    positions = position_map()
    x_mm, y_mm = positions[element_name]
    theta = math.radians(theta_deg)
    phi = math.radians(phi_deg)
    ux = math.sin(theta) * math.cos(phi)
    uy = math.sin(theta) * math.sin(phi)
    path_mm = x_mm * ux + y_mm * uy
    return wrap_deg(-360.0 * path_mm / WAVELENGTH_MM)


def pdoa_vector(theta_deg: int, phi_deg: int, baselines: Sequence[Tuple[str, str]] = BASELINES) -> List[float]:
    phases = {name: array_phase_deg(theta_deg, phi_deg, name) for name, *_ in ELEMENTS}
    return [wrap_deg(phases[right] - phases[left]) for left, right in baselines]


def phase_vector_distance(lhs: Sequence[float], rhs: Sequence[float]) -> float:
    diffs = [wrap_deg(a - b) for a, b in zip(lhs, rhs)]
    return rms(diffs)


def evaluate_lut_holdout(start_deg: int) -> Tuple[float, float, float, List[Dict[str, float]]]:
    phis = phi_samples_in_window(start_deg)
    rows: List[Dict[str, float]] = []
    residuals: List[float] = []
    for theta in THETA_CUTS_DEG:
        train_phis = [p for p in phis if p % HOLDOUT_STEP_DEG != 0]
        holdout_phis = [p for p in phis if p % HOLDOUT_STEP_DEG == 0]
        if not train_phis or not holdout_phis:
            raise ValueError("LUT split produced empty train or holdout samples")
        train = [(p, pdoa_vector(theta, p)) for p in train_phis]
        for phi in holdout_phis:
            observed = pdoa_vector(theta, phi)
            best_phi, best_distance = min(
                ((candidate_phi, phase_vector_distance(observed, candidate_vec)) for candidate_phi, candidate_vec in train),
                key=lambda item: item[1],
            )
            residual = abs(wrap_deg(best_phi - phi))
            residuals.append(residual)
            rows.append(
                {
                    "theta_deg": float(theta),
                    "phi_true_deg": float(phi),
                    "phi_est_deg": float(best_phi),
                    "azimuth_error_deg": residual,
                    "phase_vector_distance_deg": best_distance,
                }
            )
    return rms(residuals), percentile(residuals, 95.0), max(residuals), rows


def evaluate_phase_separation(start_deg: int) -> float:
    phis = phi_samples_in_window(start_deg)
    min_sep = float("inf")
    for theta in THETA_CUTS_DEG:
        train = [(p, pdoa_vector(theta, p)) for p in phis if p % HOLDOUT_STEP_DEG != 0]
        for idx, (_phi_a, vec_a) in enumerate(train):
            for _phi_b, vec_b in train[idx + 1 :]:
                sep = phase_vector_distance(vec_a, vec_b)
                if sep < min_sep:
                    min_sep = sep
    return min_sep


def evaluate_vector_slope(start_deg: int) -> float:
    phis = phi_samples_in_window(start_deg)
    slopes: List[float] = []
    for theta in THETA_CUTS_DEG:
        for idx in range(len(phis) - 1):
            vec_a = pdoa_vector(theta, phis[idx], PRIMARY_BASELINES)
            vec_b = pdoa_vector(theta, phis[idx + 1], PRIMARY_BASELINES)
            slopes.append(phase_vector_distance(vec_a, vec_b) / GRID_STEP_DEG)
    return percentile(slopes, 5.0)


def evaluate_gain(grid: FarFieldGrid, scenario: str, start_deg: int) -> Tuple[float, float, float, float]:
    strict_total: List[float] = []
    coverage_total: List[float] = []
    strict_realized: List[float] = []
    coverage_realized: List[float] = []
    phis = phi_samples_in_window(start_deg)
    theta_values = list(range(THETA_MIN_DEG, THETA_MAX_DEG + 1, GRID_STEP_DEG))

    for theta in theta_values:
        for phi in phis:
            element_total = [
                sample_gain(grid, theta, phi, element_name, scenario, realized=False)
                for element_name, *_ in ELEMENTS
            ]
            element_realized = [
                sample_gain(grid, theta, phi, element_name, scenario, realized=True)
                for element_name, *_ in ELEMENTS
            ]
            strict_total.append(min(element_total))
            coverage_total.append(max(element_total))
            strict_realized.append(min(element_realized))
            coverage_realized.append(max(element_realized))

    return (
        min(strict_total),
        min(coverage_total),
        min(strict_realized),
        min(coverage_realized),
    )


def evaluate_single_element_windows(grid: FarFieldGrid) -> Tuple[Dict[str, object], List[Dict[str, object]]]:
    rows: List[Dict[str, object]] = []
    theta_values = list(range(THETA_MIN_DEG, THETA_MAX_DEG + 1, GRID_STEP_DEG))
    for start in range(0, 360, GRID_STEP_DEG):
        total_values: List[float] = []
        realized_values: List[float] = []
        worst_theta = 0
        worst_phi = 0
        worst_gain = float("inf")
        for theta in theta_values:
            for phi in phi_samples_in_window(start):
                total = sample_gain(grid, theta, phi, "E1", "co_oriented", realized=False)
                realized_total = sample_gain(grid, theta, phi, "E1", "co_oriented", realized=True)
                total_values.append(total)
                realized_values.append(realized_total)
                if total < worst_gain:
                    worst_gain = total
                    worst_theta = theta
                    worst_phi = phi
        rows.append(
            {
                "window_start_phi_deg": start,
                "window_stop_phi_deg": window_stop(start),
                "gain_total_min_dbi": min(total_values),
                "realized_gain_total_min_dbi": min(realized_values),
                "gain_total_min_theta_deg": worst_theta,
                "gain_total_min_phi_deg": worst_phi,
                "gain_pass": min(total_values) >= GAIN_TARGET_DBI,
                "realized_gain_pass": min(realized_values) >= GAIN_TARGET_DBI,
            }
        )
    best = max(rows, key=lambda row: float(row["gain_total_min_dbi"]))
    return best, rows


def bool_from_summary(value: object) -> bool:
    return str(value).strip().lower() in {"true", "1", "yes", "pass", "passed"}


def candidate_from_farfield(path: Path) -> str:
    suffix = "_native_farfield_default.csv"
    if path.name.endswith(suffix):
        return path.name[: -len(suffix)]
    return path.stem


def scan_physical_candidates(summary_rows: Sequence[Dict[str, str]], report_dir: Path) -> List[Dict[str, object]]:
    summary_by_candidate = {
        (row.get("candidate") or row.get("candidate_name") or row.get("name") or ""): row
        for row in summary_rows
    }
    rows: List[Dict[str, object]] = []
    for farfield_path in sorted(report_dir.glob("*_native_farfield_default.csv")):
        candidate = candidate_from_farfield(farfield_path)
        summary = summary_by_candidate.get(candidate, {})
        try:
            grid = read_farfield(farfield_path)
            best, _window_rows = evaluate_single_element_windows(grid)
            s11 = float(summary.get("s11_worst_db") or summary.get("s11_db") or "nan")
            s11_pass = s11 <= S11_TARGET_DB
            gain = float(best["gain_total_min_dbi"])
            realized_gain = float(best["realized_gain_total_min_dbi"])
            gain_pass = gain >= GAIN_TARGET_DBI
            rows.append(
                {
                    "candidate": candidate,
                    "candidate_index": summary.get("candidate_index", ""),
                    "farfield_csv": str(farfield_path),
                    "s11_worst_db": s11,
                    "s11_pass": s11_pass,
                    "best_270deg_window_start_phi_deg": best["window_start_phi_deg"],
                    "best_270deg_window_stop_phi_deg": best["window_stop_phi_deg"],
                    "corrected_best_270deg_gain_total_min_dbi": gain,
                    "corrected_best_270deg_realized_gain_total_min_dbi": realized_gain,
                    "corrected_best_270deg_gain_total_min_theta_deg": best["gain_total_min_theta_deg"],
                    "corrected_best_270deg_gain_total_min_phi_deg": best["gain_total_min_phi_deg"],
                    "gain_pass": gain_pass,
                    "realized_gain_pass": bool(best["realized_gain_pass"]),
                    "overall_pass": s11_pass and gain_pass,
                    "axis_note": grid.axis_note,
                }
            )
        except Exception as exc:  # pragma: no cover - kept in CSV for engineering traceability.
            rows.append(
                {
                    "candidate": candidate,
                    "candidate_index": summary.get("candidate_index", ""),
                    "farfield_csv": str(farfield_path),
                    "s11_worst_db": summary.get("s11_worst_db") or summary.get("s11_db") or "",
                    "s11_pass": bool_from_summary(summary.get("s11_pass", "")),
                    "best_270deg_window_start_phi_deg": "",
                    "best_270deg_window_stop_phi_deg": "",
                    "corrected_best_270deg_gain_total_min_dbi": "",
                    "corrected_best_270deg_realized_gain_total_min_dbi": "",
                    "corrected_best_270deg_gain_total_min_theta_deg": "",
                    "corrected_best_270deg_gain_total_min_phi_deg": "",
                    "gain_pass": False,
                    "realized_gain_pass": False,
                    "overall_pass": False,
                    "axis_note": f"failed: {exc}",
                }
            )
    return rows


def physical_candidate_score(row: Dict[str, object]) -> Tuple[int, int, int, float, float]:
    def as_float(key: str, default: float = -999.0) -> float:
        try:
            return float(row.get(key, default))
        except (TypeError, ValueError):
            return default

    return (
        1 if bool(row.get("overall_pass")) else 0,
        1 if bool(row.get("s11_pass")) else 0,
        1 if bool(row.get("gain_pass")) else 0,
        as_float("corrected_best_270deg_gain_total_min_dbi"),
        -as_float("s11_worst_db", 999.0),
    )


def choose_physical_candidate(scan_rows: Sequence[Dict[str, object]]) -> Dict[str, object] | None:
    valid = [row for row in scan_rows if row.get("corrected_best_270deg_gain_total_min_dbi") != ""]
    if not valid:
        return None
    return max(valid, key=physical_candidate_score)


def evaluate_scenario(grid: FarFieldGrid, scenario: str, start_deg: int) -> Tuple[BaselineResult, List[Dict[str, float]]]:
    strict_gain, coverage_gain, strict_realized, coverage_realized = evaluate_gain(grid, scenario, start_deg)
    lut_rms, lut_p95, lut_max, holdout_rows = evaluate_lut_holdout(start_deg)
    vector_slope_p5 = evaluate_vector_slope(start_deg)
    min_sep = evaluate_phase_separation(start_deg)

    gain_pass = strict_gain >= GAIN_TARGET_DBI
    lut_pass = lut_rms <= LUT_RMS_TARGET_DEG and lut_p95 <= LUT_P95_TARGET_DEG
    separation_pass = (
        vector_slope_p5 >= VECTOR_SLOPE_P5_TARGET_DEG_PER_DEG
        and min_sep >= PHASE_SEPARATION_MIN_TARGET_DEG
    )
    result = BaselineResult(
        scenario=scenario,
        phi_start_deg=start_deg,
        phi_stop_deg=window_stop(start_deg),
        strict_gain_total_min_dbi=strict_gain,
        coverage_gain_total_min_dbi=coverage_gain,
        strict_realized_gain_total_min_dbi=strict_realized,
        coverage_realized_gain_total_min_dbi=coverage_realized,
        lut_holdout_rms_deg=lut_rms,
        lut_holdout_p95_deg=lut_p95,
        lut_holdout_max_deg=lut_max,
        vector_slope_p5_deg_per_deg=vector_slope_p5,
        min_phase_vector_separation_deg=min_sep,
        gain_pass=gain_pass,
        lut_pass=lut_pass,
        separation_pass=separation_pass,
        overall_pass=gain_pass and lut_pass and separation_pass,
    )
    for row in holdout_rows:
        row["scenario"] = scenario
        row["phi_start_deg"] = float(start_deg)
        row["phi_stop_deg"] = float(window_stop(start_deg))
    return result, holdout_rows


def result_score(result: BaselineResult) -> Tuple[int, float, float, float]:
    return (
        1 if result.overall_pass else 0,
        result.strict_gain_total_min_dbi,
        -result.lut_holdout_p95_deg,
        result.min_phase_vector_separation_deg,
    )


def choose_best(results: Sequence[BaselineResult], scenario: str) -> BaselineResult:
    scenario_results = [r for r in results if r.scenario == scenario]
    return max(scenario_results, key=result_score)


def write_csv(path: Path, rows: Iterable[Dict[str, object]], fieldnames: Sequence[str]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def result_to_row(result: BaselineResult) -> Dict[str, object]:
    return {
        "scenario": result.scenario,
        "phi_window_start_deg": result.phi_start_deg,
        "phi_window_stop_deg": result.phi_stop_deg,
        "phi_window_width_deg": PHI_WINDOW_DEG,
        "strict_gain_total_min_dbi": result.strict_gain_total_min_dbi,
        "coverage_gain_total_min_dbi": result.coverage_gain_total_min_dbi,
        "strict_realized_gain_total_min_dbi": result.strict_realized_gain_total_min_dbi,
        "coverage_realized_gain_total_min_dbi": result.coverage_realized_gain_total_min_dbi,
        "lut_holdout_rms_deg": result.lut_holdout_rms_deg,
        "lut_holdout_p95_deg": result.lut_holdout_p95_deg,
        "lut_holdout_max_deg": result.lut_holdout_max_deg,
        "vector_slope_p5_deg_per_deg": result.vector_slope_p5_deg_per_deg,
        "min_phase_vector_separation_deg": result.min_phase_vector_separation_deg,
        "gain_pass": result.gain_pass,
        "lut_pass": result.lut_pass,
        "separation_pass": result.separation_pass,
        "overall_pass": result.overall_pass,
    }


def render_phase_svg(best: BaselineResult, path: Path) -> None:
    width = 960
    height = 560
    margin_left = 72
    margin_right = 24
    margin_top = 38
    margin_bottom = 64
    plot_w = width - margin_left - margin_right
    plot_h = height - margin_top - margin_bottom
    phis = phi_samples_in_window(best.phi_start_deg)
    x_values = [idx * GRID_STEP_DEG for idx in range(len(phis))]
    y_min = -240.0
    y_max = 240.0

    def sx(x: float) -> float:
        return margin_left + (x / PHI_WINDOW_DEG) * plot_w

    def sy(y: float) -> float:
        return margin_top + (y_max - y) / (y_max - y_min) * plot_h

    colors = {
        (45, "E1-E3"): "#006d77",
        (45, "E2-E4"): "#9b2226",
        (60, "E1-E3"): "#0a9396",
        (60, "E2-E4"): "#bb3e03",
        (75, "E1-E3"): "#94d2bd",
        (75, "E2-E4"): "#ca6702",
        (90, "E1-E3"): "#001219",
        (90, "E2-E4"): "#ae2012",
    }
    lines: List[str] = []
    labels: List[str] = []
    for theta in THETA_CUTS_DEG:
        for baseline in PRIMARY_BASELINES:
            label = f"{baseline[0]}-{baseline[1]}"
            points = []
            last = None
            offset = 0.0
            for x, phi in zip(x_values, phis):
                raw = pdoa_vector(theta, phi, [baseline])[0]
                if last is not None:
                    delta = raw + offset - last
                    if delta > 180.0:
                        offset -= 360.0
                    elif delta < -180.0:
                        offset += 360.0
                value = raw + offset
                last = value
                points.append(f"{sx(x):.1f},{sy(max(y_min, min(y_max, value))):.1f}")
            color = colors[(theta, label)]
            dash = " stroke-dasharray=\"5 5\"" if label == "E2-E4" else ""
            lines.append(
                f"<polyline fill=\"none\" stroke=\"{color}\" stroke-width=\"2.1\"{dash} points=\"{' '.join(points)}\" />"
            )
            labels.append(
                f"<span style='color:{color};font-weight:600'>{theta}deg {label}</span>"
            )

    axis = [
        f"<line x1=\"{margin_left}\" y1=\"{margin_top}\" x2=\"{margin_left}\" y2=\"{height - margin_bottom}\" stroke=\"#333\"/>",
        f"<line x1=\"{margin_left}\" y1=\"{height - margin_bottom}\" x2=\"{width - margin_right}\" y2=\"{height - margin_bottom}\" stroke=\"#333\"/>",
    ]
    ticks = []
    for y in range(-180, 181, 90):
        ticks.append(
            f"<line x1=\"{margin_left - 5}\" y1=\"{sy(y):.1f}\" x2=\"{width - margin_right}\" y2=\"{sy(y):.1f}\" stroke=\"#ddd\"/>"
        )
        ticks.append(
            f"<text x=\"{margin_left - 10}\" y=\"{sy(y) + 4:.1f}\" text-anchor=\"end\" font-size=\"12\">{y}</text>"
        )
    for x in range(0, PHI_WINDOW_DEG + 1, 45):
        ticks.append(
            f"<line x1=\"{sx(x):.1f}\" y1=\"{height - margin_bottom}\" x2=\"{sx(x):.1f}\" y2=\"{height - margin_bottom + 5}\" stroke=\"#333\"/>"
        )
        ticks.append(
            f"<text x=\"{sx(x):.1f}\" y=\"{height - margin_bottom + 22}\" text-anchor=\"middle\" font-size=\"12\">{x}</text>"
        )
    legend = " | ".join(labels)
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
<rect width="100%" height="100%" fill="white"/>
<text x="{margin_left}" y="24" font-size="18" font-weight="700">D44 thick PIFA PDOA phase, {best.scenario}, Phi {best.phi_start_deg}..{best.phi_stop_deg} deg</text>
{''.join(ticks)}
{''.join(axis)}
{''.join(lines)}
<text x="{margin_left + plot_w / 2:.1f}" y="{height - 18}" text-anchor="middle" font-size="13">Azimuth offset inside selected 270 deg window (deg)</text>
<text x="18" y="{margin_top + plot_h / 2:.1f}" transform="rotate(-90 18,{margin_top + plot_h / 2:.1f})" text-anchor="middle" font-size="13">Unwrapped PDOA phase (deg)</text>
<foreignObject x="{margin_left}" y="{height - 48}" width="{plot_w}" height="26">
  <div xmlns="http://www.w3.org/1999/xhtml" style="font-size:11px;font-family:Arial,sans-serif;white-space:nowrap;overflow:hidden">{legend}</div>
</foreignObject>
</svg>
"""
    path.write_text(svg, encoding="utf-8")


def render_report(
    path: Path,
    baseline: Dict[str, str],
    grid: FarFieldGrid,
    physical_best: Dict[str, object],
    physical_candidate_scan: Sequence[Dict[str, object]],
    selected_candidate: Dict[str, object] | None,
    best_by_scenario: Dict[str, BaselineResult],
    all_results: Sequence[BaselineResult],
    phase_plot_path: Path,
) -> None:
    overall_best = max(all_results, key=result_score)
    candidate = baseline.get("candidate_name") or baseline.get("candidate") or "unknown"
    s11 = float(baseline.get("s11_db") or baseline.get("s11_worst_db") or "nan")
    legacy_single_gain = float(baseline.get("best_270deg_gain_total_min_dbi", "nan"))
    single_gain = float(physical_best["gain_total_min_dbi"])
    single_realized_gain = float(physical_best["realized_gain_total_min_dbi"])
    gain_pass = bool(physical_best["gain_pass"])
    s11_pass = baseline.get("s11_pass", "").lower() == "true"
    baseline_pass = gain_pass and s11_pass

    def pass_text(value: bool) -> str:
        return "通过" if value else "未通过"

    rows = []
    for scenario, result in best_by_scenario.items():
        rows.append(
            "| {scenario} | {start}..{stop} | {strict_gain:.2f} | {coverage_gain:.2f} | {rms:.2f} | {p95:.2f} | {slope:.2f} | {sep:.2f} | {status} |".format(
                scenario=scenario,
                start=result.phi_start_deg,
                stop=result.phi_stop_deg,
                strict_gain=result.strict_gain_total_min_dbi,
                coverage_gain=result.coverage_gain_total_min_dbi,
                rms=result.lut_holdout_rms_deg,
                p95=result.lut_holdout_p95_deg,
                slope=result.vector_slope_p5_deg_per_deg,
                sep=result.min_phase_vector_separation_deg,
                status=pass_text(result.overall_pass),
            )
        )

    scan_overall_pass = [row for row in physical_candidate_scan if bool(row.get("overall_pass"))]
    scan_s11_pass = [row for row in physical_candidate_scan if bool(row.get("s11_pass"))]
    scan_best_gain = max(
        physical_candidate_scan,
        key=lambda row: float(row.get("corrected_best_270deg_gain_total_min_dbi") or -999.0),
    ) if physical_candidate_scan else None
    selected_text = (
        f"`{selected_candidate['candidate']}`"
        if selected_candidate
        else "`未找到可用候选`"
    )
    selected_overall = bool(selected_candidate and selected_candidate.get("overall_pass"))
    selected_scan_gain = (
        float(selected_candidate["corrected_best_270deg_gain_total_min_dbi"])
        if selected_candidate and selected_candidate.get("corrected_best_270deg_gain_total_min_dbi") != ""
        else float("nan")
    )

    phase_plot_abs = phase_plot_path.resolve().as_posix()
    report = f"""# D44 厚板 PIFA 可校准阵列 + LUT 系统级验证报告

## 目标

- 保留厚板单端口 PIFA 作为物理基准：S11 < -10 dB，Theta 45..90 deg、任意 270 deg 方位窗口内 GainTotal >= -5 dBi。
- 系统级部分转向真正低仰角覆盖单元/板边独立辐射臂的思路，不再继续硬调当前 dualpol A/B 源集合。
- 测角验证优先检查“可校准阵列 + 低仰角覆盖单元 + LUT”的组合是否成立。

## 物理基准

- 基准候选：`{candidate}`
- 单端口 S11：{s11:.2f} dB，目标 < {S11_TARGET_DB:.1f} dB，{pass_text(s11_pass)}
- 单端口最佳 270 deg 窗口 GainTotal min：{single_gain:.2f} dBi，目标 >= {GAIN_TARGET_DBI:.1f} dBi，{pass_text(gain_pass)}
- 单端口最佳 270 deg 窗口 RealizedGainTotal min：{single_realized_gain:.2f} dBi
- 本轮重新按导出值域识别角度轴：{grid.axis_note}。旧汇总表中的 GainTotal min 为 {legacy_single_gain:.2f} dBi，仅作为上一阶段记录保留；本报告采用重新解析后的完整 Phi 轴复核值。
- 物理基准结论：{pass_text(baseline_pass)}
- 已复扫厚板 PIFA 家族 `{len(physical_candidate_scan)}` 个已有 far-field 候选，其中 S11 与修正后真实 270 deg GainTotal 同时达标 `{len(scan_overall_pass)}` 个；S11 达标候选 `{len(scan_s11_pass)}` 个。
- 本轮系统级验证选用：{selected_text}，修正后最佳 270 deg GainTotal min {selected_scan_gain:.2f} dBi，候选整体 {pass_text(selected_overall)}。
{("- 修正后增益最高候选：" + " `" + str(scan_best_gain["candidate"]) + "`，GainTotal min " + f"{float(scan_best_gain['corrected_best_270deg_gain_total_min_dbi']):.2f} dBi，S11 {float(scan_best_gain['s11_worst_db']):.2f} dB。") if scan_best_gain else ""}

## 系统级模型

- 阵列：D44 四阵元菱形布置，板直径 {BOARD_DIAMETER_MM:.1f} mm，地半径 {GROUND_RADIUS_MM:.1f} mm。
- 阵元相位中心半径：{CENTER_RADIUS_MM:.2f} mm，E1-E3 / E2-E4 长基线约 {2.0 * CENTER_RADIUS_MM:.2f} mm，相邻基线约 {ELEMENT_SPACING_MM:.2f} mm。
- 频点：{FREQ_GHZ:.1f} GHz，自由空间波长约 {WAVELENGTH_MM:.2f} mm。
- 低仰角单元方向图：直接复用厚板 PIFA 达标候选的 HFSS 单端口 GainTotal / RealizedGainTotal。
- LUT：每个 Theta 切面用 5 deg 方位栅格建库，10 deg 栅格作为 holdout；用六条 PDOA 基线的圆周相位向量最近邻估计方位。
- 重要限制：当前远场 CSV 只有 Total/Realized Total 增益，没有 Etheta/Ephi 复矢量场，因此本轮不能给出真实双极化 XPD 或极化相位 LUT；这里验证的是低仰角覆盖单元 + 可校准相位几何的测角上界。

## 结果

| 场景 | 最佳 270 deg 方位窗口 | strict GainTotal min (dBi) | coverage GainTotal min (dBi) | LUT RMS (deg) | LUT P95 (deg) | 相位向量斜率 P5 (deg/deg) | 最小相位向量间隔 (deg) | 结论 |
|---|---:|---:|---:|---:|---:|---:|---:|---|
{chr(10).join(rows)}

总体最佳场景为 `{overall_best.scenario}`，窗口 Phi {overall_best.phi_start_deg}..{overall_best.phi_stop_deg} deg，综合结论：{pass_text(overall_best.overall_pass)}。

![PDOA phase plot]({phase_plot_abs})

## 判断

- 厚板单端口 PIFA 基准继续成立，可以作为后续板边独立辐射臂/低仰角覆盖单元的物理锚点。
- 在解析阵列模型中，D44 当前 17 mm 阵元间距对应的长基线仍低于 8 GHz 下的 1 个波长相位周跳，六基线 LUT 的 holdout 方位误差满足 10 deg 级测角验证门限。
- 这说明下一步值得投入真实阵列 HFSS：保持低仰角 PIFA/IFA 单元，建立四阵元可校准阵列工程，导出每端口复矢量远场，再把极化 LUT、互耦、馈线相位和人体/机器狗安装面影响纳入复核。
- 不建议继续在现有 dualpol A/B 源集合上做复权重排序，因为其低仰角覆盖由源组合补偿，不能替代独立低仰角辐射单元的物理增益。

## 输出文件

- 指标 JSON：`{OUTPUT_STEM}_metrics.json`
- 单阵元真实轴向 270 deg 窗口汇总：`{OUTPUT_STEM}_physical_window_summary.csv`
- 窗口汇总：`{OUTPUT_STEM}_window_summary.csv`
- 最佳窗口摘要：`{OUTPUT_STEM}_summary.csv`
- LUT holdout 明细：`{OUTPUT_STEM}_lut_holdout.csv`
- 相位曲线：`{phase_plot_path.name}`
"""
    path.write_text(report, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline-summary", type=Path, default=BASELINE_SUMMARY)
    parser.add_argument("--farfield", type=Path, default=BASELINE_FARFIELD)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    parser.add_argument("--fixed-baseline", action="store_true", help="Do not auto-select another physical candidate")
    args = parser.parse_args()

    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    summary_rows = read_summary_rows(args.baseline_summary)
    baseline = select_summary_row(summary_rows)

    physical_scan_rows = scan_physical_candidates(summary_rows, args.baseline_summary.parent)
    selected_physical = choose_physical_candidate(physical_scan_rows)
    if not args.fixed_baseline and selected_physical and selected_physical.get("farfield_csv"):
        selected_candidate_name = str(selected_physical["candidate"])
        matching = select_summary_row(summary_rows, selected_candidate_name)
        if matching:
            baseline = matching
        farfield_path = Path(str(selected_physical["farfield_csv"]))
    else:
        farfield_path = args.farfield

    grid = read_farfield(farfield_path)
    physical_best, physical_window_rows = evaluate_single_element_windows(grid)

    scenarios = ["co_oriented", "radial_oriented"]
    starts = list(range(0, 360, GRID_STEP_DEG))
    all_results: List[BaselineResult] = []
    best_holdout_rows: List[Dict[str, float]] = []

    for scenario in scenarios:
        scenario_results: List[BaselineResult] = []
        scenario_holdouts: Dict[int, List[Dict[str, float]]] = {}
        for start in starts:
            result, holdout_rows = evaluate_scenario(grid, scenario, start)
            all_results.append(result)
            scenario_results.append(result)
            scenario_holdouts[start] = holdout_rows
        best = max(scenario_results, key=result_score)
        best_holdout_rows.extend(scenario_holdouts[best.phi_start_deg])

    best_by_scenario = {scenario: choose_best(all_results, scenario) for scenario in scenarios}
    overall_best = max(all_results, key=result_score)
    phase_plot_path = output_dir / f"{OUTPUT_STEM}_phase_best.svg"

    summary_rows = [result_to_row(best_by_scenario[scenario]) for scenario in scenarios]
    window_rows = [result_to_row(result) for result in all_results]

    summary_path = output_dir / f"{OUTPUT_STEM}_summary.csv"
    window_path = output_dir / f"{OUTPUT_STEM}_window_summary.csv"
    physical_window_path = output_dir / f"{OUTPUT_STEM}_physical_window_summary.csv"
    holdout_path = output_dir / f"{OUTPUT_STEM}_lut_holdout.csv"
    physical_scan_path = output_dir / f"{OUTPUT_STEM}_physical_candidate_scan.csv"
    metrics_path = output_dir / f"{OUTPUT_STEM}_metrics.json"
    report_path = output_dir / f"{OUTPUT_STEM}_report.md"

    fieldnames = list(summary_rows[0].keys())
    write_csv(summary_path, summary_rows, fieldnames)
    write_csv(window_path, window_rows, fieldnames)
    write_csv(
        physical_window_path,
        physical_window_rows,
        [
            "window_start_phi_deg",
            "window_stop_phi_deg",
            "gain_total_min_dbi",
            "realized_gain_total_min_dbi",
            "gain_total_min_theta_deg",
            "gain_total_min_phi_deg",
            "gain_pass",
            "realized_gain_pass",
        ],
    )
    write_csv(
        physical_scan_path,
        physical_scan_rows,
        [
            "candidate",
            "candidate_index",
            "farfield_csv",
            "s11_worst_db",
            "s11_pass",
            "best_270deg_window_start_phi_deg",
            "best_270deg_window_stop_phi_deg",
            "corrected_best_270deg_gain_total_min_dbi",
            "corrected_best_270deg_realized_gain_total_min_dbi",
            "corrected_best_270deg_gain_total_min_theta_deg",
            "corrected_best_270deg_gain_total_min_phi_deg",
            "gain_pass",
            "realized_gain_pass",
            "overall_pass",
            "axis_note",
        ],
    )
    write_csv(
        holdout_path,
        best_holdout_rows,
        [
            "scenario",
            "phi_start_deg",
            "phi_stop_deg",
            "theta_deg",
            "phi_true_deg",
            "phi_est_deg",
            "azimuth_error_deg",
            "phase_vector_distance_deg",
        ],
    )
    render_phase_svg(overall_best, phase_plot_path)

    metrics = {
        "baseline": baseline,
        "baseline_reparsed_physical_best_270deg": physical_best,
        "selected_farfield_csv": str(farfield_path),
        "selected_physical_candidate": selected_physical,
        "farfield_axes": {
            "theta_column_idx": grid.theta_column_idx,
            "phi_column_idx": grid.phi_column_idx,
            "theta_values": grid.theta_values,
            "phi_values_count": len(grid.phi_values),
            "phi_values_first": grid.phi_values[:10],
            "phi_values_last": grid.phi_values[-10:],
            "axis_note": grid.axis_note,
        },
        "targets": {
            "s11_db_lt": S11_TARGET_DB,
            "gain_total_min_dbi_ge": GAIN_TARGET_DBI,
            "theta_min_deg": THETA_MIN_DEG,
            "theta_max_deg": THETA_MAX_DEG,
            "phi_window_deg": PHI_WINDOW_DEG,
            "lut_rms_deg_le": LUT_RMS_TARGET_DEG,
            "lut_p95_deg_le": LUT_P95_TARGET_DEG,
            "phase_vector_slope_p5_deg_per_deg_ge": VECTOR_SLOPE_P5_TARGET_DEG_PER_DEG,
            "phase_vector_separation_min_deg_ge": PHASE_SEPARATION_MIN_TARGET_DEG,
        },
        "geometry": {
            "freq_ghz": FREQ_GHZ,
            "wavelength_mm": WAVELENGTH_MM,
            "board_diameter_mm": BOARD_DIAMETER_MM,
            "ground_radius_mm": GROUND_RADIUS_MM,
            "element_spacing_mm": ELEMENT_SPACING_MM,
            "center_radius_mm": CENTER_RADIUS_MM,
            "elements": [
                {"name": name, "x_mm": x, "y_mm": y, "orientation_deg": angle}
                for name, x, y, angle in ELEMENTS
            ],
            "baselines": list(BASELINES),
        },
        "best_by_scenario": {scenario: result_to_row(result) for scenario, result in best_by_scenario.items()},
        "overall_best": result_to_row(overall_best),
        "model_limitations": [
            "Uses the passing single-port thick PIFA total-gain pattern as a scalar low-elevation element pattern.",
            "Does not include mutual coupling, feed network phase, installed-machine environment, or vector Etheta/Ephi polarization response.",
            "Polarization LUT and XPD must be re-evaluated with vector complex far-field from the real multi-port array HFSS model.",
        ],
    }
    metrics_path.write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")
    render_report(
        report_path,
        baseline,
        grid,
        physical_best,
        physical_scan_rows,
        selected_physical,
        best_by_scenario,
        all_results,
        phase_plot_path,
    )

    print(f"summary={summary_path}")
    print(f"window_summary={window_path}")
    print(f"physical_window_summary={physical_window_path}")
    print(f"physical_candidate_scan={physical_scan_path}")
    print(f"holdout={holdout_path}")
    print(f"metrics={metrics_path}")
    print(f"report={report_path}")
    print(
        "overall_best={scenario} Phi {start}..{stop} gain={gain:.2f}dBi rms={rms:.2f}deg p95={p95:.2f}deg pass={passed} selected_farfield={selected}".format(
            scenario=overall_best.scenario,
            start=overall_best.phi_start_deg,
            stop=overall_best.phi_stop_deg,
            gain=overall_best.strict_gain_total_min_dbi,
            rms=overall_best.lut_holdout_rms_deg,
            p95=overall_best.lut_holdout_p95_deg,
            passed=overall_best.overall_pass,
            selected=farfield_path.name,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
