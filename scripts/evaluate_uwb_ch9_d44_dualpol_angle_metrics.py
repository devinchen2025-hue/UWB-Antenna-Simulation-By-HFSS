from __future__ import annotations

import argparse
import cmath
import csv
import json
import math
import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from statistics import fmean, median
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = (
    ROOT
    / "reports_d44_dualpol_truefed_l_polarization_phase"
    / "UWB_CH9_D44_DUALPOL_TRUEFED_L_POLARIZATION_PHASE_field_manifest.csv"
)
DEFAULT_SPARAM_SUMMARY = (
    ROOT
    / "reports_d44_dualpol_truefed_l_fov_gain_check"
    / "UWB_CH9_D44_DUALPOL_TRUEFED_L_NATIVE_RERUN_summary.csv"
)
DEFAULT_GAIN_DIR = ROOT / "reports_d44_dualpol_truefed_l_fov_gain_check"
REPORT_DIR = ROOT / "reports_d44_dualpol_angle_metrics"
STEM = "UWB_CH9_D44_DUALPOL_ANGLE_METRICS"

MATRIX_SAMPLES_CSV = REPORT_DIR / f"{STEM}_matrix_samples.csv"
MATRIX_SUMMARY_CSV = REPORT_DIR / f"{STEM}_matrix_summary.csv"
PHASE_CURVES_CSV = REPORT_DIR / f"{STEM}_pdoa_phase_curves.csv"
PHASE_SUMMARY_CSV = REPORT_DIR / f"{STEM}_pdoa_phase_summary.csv"
SPARAM_SUMMARY_CSV = REPORT_DIR / f"{STEM}_sparam_summary.csv"
GAIN_SUMMARY_CSV = REPORT_DIR / f"{STEM}_gain_summary.csv"
METRICS_JSON = REPORT_DIR / f"{STEM}_metrics.json"
REPORT_MD = REPORT_DIR / f"{STEM}_report.md"
PLOTS_DIR = REPORT_DIR / "plots"

FREQ_GHZ = 8.0
THETA_MIN_DEG = 45.0
THETA_MAX_DEG = 90.0
PHI_WINDOW_DEG = 270.0
XPD_TARGET_DB = 25.0
ORTHOGONALITY_TARGET_DB = 20.0
CONDITION_MAX_TARGET_DB = 6.0
PHASE_RESIDUAL_P95_TARGET_DEG = 10.0
MAG_VALID_FLOOR_REL_DB = -35.0
GAIN_TARGET_DBI = -5.0
AZIMUTH_SLOPE_FLOOR_DEG_PER_DEG = 0.5
THETA_CUTS_DEG = [45.0, 60.0, 75.0, 90.0]
PLOT_THETA_DEG = 90.0
PLOT_BASELINES = [("E1", "E3"), ("E2", "E4")]
BASELINES = [
    ("E1", "E3"),
    ("E2", "E4"),
    ("E1", "E2"),
    ("E2", "E3"),
    ("E3", "E4"),
    ("E4", "E1"),
]
ASSIGNMENTS = {
    "A_H__B_V": {"A": "H", "B": "V"},
    "A_V__B_H": {"A": "V", "B": "H"},
}


@dataclass(frozen=True)
class FieldPoint:
    theta_deg: float
    phi_deg: float
    etheta: complex
    ephi: complex


@dataclass(frozen=True)
class FieldEntry:
    case: str
    active_pol: str
    source: str
    feed: str
    element: int
    path: Path
    grid: dict[tuple[float, float], FieldPoint]


def fmt(value: Any, digits: int = 3) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    if math.isnan(number) or math.isinf(number):
        return "N/A"
    return f"{number:.{digits}f}"


def num(value: Any, default: float = float("nan")) -> float:
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        return default


def first_header_index(header: list[str], prefix: str) -> int:
    return next(idx for idx, name in enumerate(header) if name.startswith(prefix))


def expr_index(header: list[str], expr: str) -> int:
    return next(idx for idx, name in enumerate(header) if expr in name)


def wrap_deg(value: float) -> float:
    return (value + 180.0) % 360.0 - 180.0


def phase_deg(value: complex) -> float:
    return math.degrees(cmath.phase(value))


def unwrap_degrees(values: list[float]) -> list[float]:
    if not values:
        return []
    unwrapped = [values[0]]
    offset = 0.0
    previous = values[0]
    for value in values[1:]:
        delta = value - previous
        if delta > 180.0:
            offset -= 360.0
        elif delta < -180.0:
            offset += 360.0
        unwrapped.append(value + offset)
        previous = value
    return unwrapped


def rms(values: list[float]) -> float:
    return math.sqrt(fmean(value * value for value in values)) if values else float("nan")


def percentile(values: list[float], pct: float) -> float:
    clean = sorted(value for value in values if not math.isnan(value))
    if not clean:
        return float("nan")
    idx = min(len(clean) - 1, max(0, math.ceil(len(clean) * pct / 100.0) - 1))
    return clean[idx]


def db20(value: float) -> float:
    if value <= 0.0:
        return -999.0
    return 20.0 * math.log10(value)


def ratio_db(numerator: float, denominator: float) -> float:
    if numerator <= 0.0 or denominator <= 0.0:
        return float("nan")
    return 20.0 * math.log10(numerator / denominator)


def rel_db(value: float, reference: float) -> float:
    if value <= 0.0 or reference <= 0.0:
        return -999.0
    return 20.0 * math.log10(value / reference)


def source_parts(source: str) -> tuple[int, str]:
    match = re.fullmatch(r"P(\d+)([A-Za-z]+)", source.strip())
    if not match:
        raise ValueError(f"Cannot parse source name: {source}")
    return int(match.group(1)), match.group(2).upper()


def parse_field_csv(path: Path) -> dict[tuple[float, float], FieldPoint]:
    with path.open(newline="", encoding="utf-8-sig") as f:
        rows = list(csv.reader(f))
    if len(rows) < 2:
        raise RuntimeError(f"Empty field CSV: {path}")
    header = rows[0]
    theta_idx = first_header_index(header, "Theta")
    phi_idx = first_header_index(header, "Phi")
    re_theta_idx = expr_index(header, "re(rETheta)")
    im_theta_idx = expr_index(header, "im(rETheta)")
    re_phi_idx = expr_index(header, "re(rEPhi)")
    im_phi_idx = expr_index(header, "im(rEPhi)")
    angle_rows = [
        (num(raw[theta_idx]), num(raw[phi_idx]))
        for raw in rows[1:]
        if len(raw) > max(theta_idx, phi_idx)
    ]
    swap_angle_columns = (
        bool(angle_rows)
        and max(theta for theta, _ in angle_rows) > 180.0
        and max(phi for _, phi in angle_rows) <= 180.0
    )
    grid: dict[tuple[float, float], FieldPoint] = {}
    for raw in rows[1:]:
        if len(raw) <= max(theta_idx, phi_idx, re_theta_idx, im_theta_idx, re_phi_idx, im_phi_idx):
            continue
        theta_raw = num(raw[theta_idx])
        phi_raw = num(raw[phi_idx])
        theta = phi_raw if swap_angle_columns else theta_raw
        phi = theta_raw if swap_angle_columns else phi_raw
        point = FieldPoint(
            theta_deg=theta,
            phi_deg=phi,
            etheta=complex(num(raw[re_theta_idx]), num(raw[im_theta_idx])),
            ephi=complex(num(raw[re_phi_idx]), num(raw[im_phi_idx])),
        )
        grid[(round(theta, 9), round(phi, 9))] = point
    if not grid:
        raise RuntimeError(f"No field rows parsed from {path}")
    return grid


def parse_gain_csv(path: Path) -> list[dict[str, float]]:
    with path.open(newline="", encoding="utf-8-sig") as f:
        rows = list(csv.reader(f))
    if len(rows) < 2:
        return []
    header = rows[0]
    theta_idx = first_header_index(header, "Theta")
    phi_idx = first_header_index(header, "Phi")
    gain_idx = expr_index(header, "dB(GainTotal)")
    realized_idx = expr_index(header, "dB(RealizedGainTotal)")
    angle_rows = [
        (num(raw[theta_idx]), num(raw[phi_idx]))
        for raw in rows[1:]
        if len(raw) > max(theta_idx, phi_idx)
    ]
    swap_angle_columns = (
        bool(angle_rows)
        and max(theta for theta, _ in angle_rows) > 180.0
        and max(phi for _, phi in angle_rows) <= 180.0
    )
    out: list[dict[str, float]] = []
    for raw in rows[1:]:
        if len(raw) <= max(theta_idx, phi_idx, gain_idx, realized_idx):
            continue
        theta_raw = num(raw[theta_idx])
        phi_raw = num(raw[phi_idx])
        theta = phi_raw if swap_angle_columns else theta_raw
        phi = theta_raw if swap_angle_columns else phi_raw
        if THETA_MIN_DEG <= theta <= THETA_MAX_DEG:
            out.append(
                {
                    "theta_deg": theta,
                    "phi_deg": phi,
                    "gain_total_dbi": num(raw[gain_idx]),
                    "realized_gain_total_dbi": num(raw[realized_idx]),
                }
            )
    return out


def read_manifest(path: Path) -> dict[str, dict[int, FieldEntry]]:
    entries: dict[str, dict[int, FieldEntry]] = {"A": {}, "B": {}}
    with path.open(newline="", encoding="utf-8-sig") as f:
        for raw in csv.DictReader(f):
            source = str(raw.get("source", "")).strip()
            if not source:
                continue
            element, feed = source_parts(source)
            if feed not in entries:
                continue
            field_path = Path(str(raw.get("field_csv", "")).strip())
            if not field_path.is_absolute():
                field_path = (path.parent / field_path).resolve()
            if not field_path.exists():
                raise FileNotFoundError(field_path)
            entries[feed][element] = FieldEntry(
                case=str(raw.get("case", "")).strip(),
                active_pol=str(raw.get("active_pol", feed)).strip(),
                source=source,
                feed=feed,
                element=element,
                path=field_path,
                grid=parse_field_csv(field_path),
            )
    missing = [feed for feed, by_element in entries.items() if not by_element]
    if missing:
        raise RuntimeError(f"Manifest lacks required feed(s): {missing}")
    return entries


def local_hv(point: FieldPoint) -> dict[str, complex]:
    # HFSS basis: local vertical (+Z projected transverse) is -Etheta, local horizontal is Ephi.
    return {"H": point.ephi, "V": -point.etheta}


def component(entries: dict[str, dict[int, FieldEntry]], feed: str, element: int, key: tuple[float, float], basis: str) -> complex:
    return local_hv(entries[feed][element].grid[key])[basis]


def common_elements(entries: dict[str, dict[int, FieldEntry]]) -> list[int]:
    return sorted(set(entries["A"]) & set(entries["B"]))


def common_keys(entries: dict[str, dict[int, FieldEntry]], elements: list[int]) -> list[tuple[float, float]]:
    key_sets = []
    for feed in ["A", "B"]:
        for element in elements:
            key_sets.append(set(entries[feed][element].grid))
    keys = set.intersection(*key_sets)
    theta_values = {theta for theta, _ in keys}
    phi_values = {phi for _, phi in keys}
    has_zero_phi = any(abs(phi) < 1e-9 for phi in phi_values)
    filtered = [
        key
        for key in keys
        if THETA_MIN_DEG <= key[0] <= THETA_MAX_DEG
        and not (has_zero_phi and abs(key[1] - 360.0) < 1e-9)
    ]
    return sorted(filtered)


def normalize_phi(phi: float) -> float:
    value = phi % 360.0
    if abs(value - 360.0) < 1e-9:
        return 0.0
    return value


def in_phi_window(phi: float, start: float, width: float) -> bool:
    if width >= 359.999:
        return True
    delta = (normalize_phi(phi) - normalize_phi(start)) % 360.0
    return -1e-9 <= delta <= width + 1e-9


def scoped_keys(keys: list[tuple[float, float]], scope: str, start: float, width: float) -> list[tuple[float, float]]:
    if scope == "full360":
        return keys
    return [key for key in keys if in_phi_window(key[1], start, width)]


def matrix_condition_db(a_h: complex, a_v: complex, b_h: complex, b_v: complex) -> float:
    h11 = abs(a_h) ** 2 + abs(a_v) ** 2
    h22 = abs(b_h) ** 2 + abs(b_v) ** 2
    h12 = a_h * b_h.conjugate() + a_v * b_v.conjugate()
    trace = h11 + h22
    determinant = max(0.0, h11 * h22 - abs(h12) ** 2)
    if trace <= 0.0:
        return float("inf")
    disc = max(0.0, trace * trace - 4.0 * determinant)
    lambda_max = 0.5 * (trace + math.sqrt(disc))
    lambda_min = 0.5 * (trace - math.sqrt(disc))
    if lambda_min <= 1e-30:
        return float("inf")
    return 10.0 * math.log10(lambda_max / lambda_min)


def polarization_correlation(a_h: complex, a_v: complex, b_h: complex, b_v: complex) -> float:
    norm_a = math.sqrt(abs(a_h) ** 2 + abs(a_v) ** 2)
    norm_b = math.sqrt(abs(b_h) ** 2 + abs(b_v) ** 2)
    if norm_a <= 0.0 or norm_b <= 0.0:
        return float("nan")
    dot = a_h.conjugate() * b_h + a_v.conjugate() * b_v
    return min(1.0, abs(dot) / (norm_a * norm_b))


def orthogonality_db(corr: float) -> float:
    if math.isnan(corr):
        return float("nan")
    if corr <= 1e-15:
        return 300.0
    return -20.0 * math.log10(corr)


def summarize_values(values: list[float], prefix: str, higher_is_better: bool = True, target: float | None = None) -> dict[str, Any]:
    clean = [value for value in values if not math.isnan(value) and not math.isinf(value)]
    if not clean:
        return {
            f"{prefix}_count": 0,
            f"{prefix}_min": float("nan"),
            f"{prefix}_p5": float("nan"),
            f"{prefix}_median": float("nan"),
            f"{prefix}_avg": float("nan"),
            f"{prefix}_p95": float("nan"),
            f"{prefix}_max": float("nan"),
        }
    out = {
        f"{prefix}_count": len(clean),
        f"{prefix}_min": min(clean),
        f"{prefix}_p5": percentile(clean, 5.0),
        f"{prefix}_median": median(clean),
        f"{prefix}_avg": fmean(clean),
        f"{prefix}_p95": percentile(clean, 95.0),
        f"{prefix}_max": max(clean),
    }
    if target is not None:
        out[f"{prefix}_target"] = target
        out[f"{prefix}_target_pass"] = (min(clean) >= target) if higher_is_better else (max(clean) <= target)
    return out


def build_matrix_samples(
    entries: dict[str, dict[int, FieldEntry]],
    elements: list[int],
    keys: list[tuple[float, float]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for theta, phi in keys:
        key = (theta, phi)
        for element in elements:
            a_h = component(entries, "A", element, key, "H")
            a_v = component(entries, "A", element, key, "V")
            b_h = component(entries, "B", element, key, "H")
            b_v = component(entries, "B", element, key, "V")
            corr = polarization_correlation(a_h, a_v, b_h, b_v)
            rows.append(
                {
                    "theta_deg": theta,
                    "phi_deg": phi,
                    "element": f"E{element}",
                    "source_a": entries["A"][element].source,
                    "source_b": entries["B"][element].source,
                    "a_h_mag": abs(a_h),
                    "a_v_mag": abs(a_v),
                    "b_h_mag": abs(b_h),
                    "b_v_mag": abs(b_v),
                    "a_h_phase_deg": phase_deg(a_h),
                    "a_v_phase_deg": phase_deg(a_v),
                    "b_h_phase_deg": phase_deg(b_h),
                    "b_v_phase_deg": phase_deg(b_v),
                    "xpd_a_as_h_db": ratio_db(abs(a_h), abs(a_v)),
                    "xpd_a_as_v_db": ratio_db(abs(a_v), abs(a_h)),
                    "xpd_b_as_h_db": ratio_db(abs(b_h), abs(b_v)),
                    "xpd_b_as_v_db": ratio_db(abs(b_v), abs(b_h)),
                    "ab_pol_corr_mag": corr,
                    "ab_pol_orthogonality_db": orthogonality_db(corr),
                    "response_condition_db": matrix_condition_db(a_h, a_v, b_h, b_v),
                }
            )
    return rows


def assignment_values(row: dict[str, Any], assignment: str) -> tuple[float, float, float, float]:
    mapping = ASSIGNMENTS[assignment]
    a_basis = mapping["A"]
    b_basis = mapping["B"]
    a_co = float(row[f"a_{a_basis.lower()}_mag"])
    a_cross = float(row[f"a_{'v' if a_basis == 'H' else 'h'}_mag"])
    b_co = float(row[f"b_{b_basis.lower()}_mag"])
    b_cross = float(row[f"b_{'v' if b_basis == 'H' else 'h'}_mag"])
    return a_co, a_cross, b_co, b_cross


def matrix_summary_for_scope(
    rows: list[dict[str, Any]],
    scope: str,
    phi_start: float,
    phi_width: float,
) -> list[dict[str, Any]]:
    scoped = [row for row in rows if scope == "full360" or in_phi_window(float(row["phi_deg"]), phi_start, phi_width)]
    out: list[dict[str, Any]] = []
    for assignment in ASSIGNMENTS:
        xpd_values: list[float] = []
        pair_min_xpd: list[float] = []
        co_mags: list[float] = []
        co_balance_abs: list[float] = []
        for row in scoped:
            a_co, a_cross, b_co, b_cross = assignment_values(row, assignment)
            xpd_a = ratio_db(a_co, a_cross)
            xpd_b = ratio_db(b_co, b_cross)
            xpd_values.extend([xpd_a, xpd_b])
            pair_min_xpd.append(min(xpd_a, xpd_b))
            co_mags.extend([a_co, b_co])
            balance = abs(ratio_db(a_co, b_co))
            if not math.isnan(balance):
                co_balance_abs.append(balance)
        co_reference = max(co_mags) if co_mags else 0.0
        co_rel = [rel_db(value, co_reference) for value in co_mags]
        row_out: dict[str, Any] = {
            "scope": scope,
            "phi_start_deg": phi_start,
            "phi_width_deg": phi_width,
            "phi_end_deg": (phi_start + phi_width) % 360.0,
            "assignment": assignment,
            "direction_element_samples": len(scoped),
            "hv_basis": "H=Ephi, V=-Etheta(board +Z projected transverse)",
        }
        row_out.update(summarize_values(xpd_values, "assigned_xpd_db", True, XPD_TARGET_DB))
        row_out.update(summarize_values(pair_min_xpd, "pair_min_xpd_db", True, XPD_TARGET_DB))
        row_out.update(summarize_values([float(row["ab_pol_orthogonality_db"]) for row in scoped], "ab_orthogonality_db", True, ORTHOGONALITY_TARGET_DB))
        row_out.update(summarize_values([float(row["response_condition_db"]) for row in scoped], "condition_db", False, CONDITION_MAX_TARGET_DB))
        row_out.update(summarize_values(co_rel, "assigned_co_rel_db", True, MAG_VALID_FLOOR_REL_DB))
        row_out.update(summarize_values(co_balance_abs, "assigned_co_balance_abs_db", False, None))
        row_out["assigned_co_floor_rel_db"] = MAG_VALID_FLOOR_REL_DB
        row_out["assigned_co_floor_pass_percent"] = (
            100.0 * sum(1 for value in co_rel if value >= MAG_VALID_FLOOR_REL_DB) / len(co_rel)
            if co_rel
            else 0.0
        )
        out.append(row_out)
    return out


def choose_best_270_window(rows: list[dict[str, Any]], available_phi: list[float]) -> tuple[float, list[dict[str, Any]]]:
    best_start = available_phi[0] if available_phi else 0.0
    best_rows: list[dict[str, Any]] = []
    best_key: tuple[float, float, float] | None = None
    for start in available_phi:
        summaries = matrix_summary_for_scope(rows, "best270", start, PHI_WINDOW_DEG)
        best_assignment = max(
            summaries,
            key=lambda row: (
                float(row.get("pair_min_xpd_db_p5", -999.0)),
                float(row.get("ab_orthogonality_db_p5", -999.0)),
                -float(row.get("condition_db_p95", 999.0)),
            ),
        )
        key = (
            float(best_assignment.get("pair_min_xpd_db_p5", -999.0)),
            float(best_assignment.get("ab_orthogonality_db_p5", -999.0)),
            -float(best_assignment.get("condition_db_p95", 999.0)),
        )
        if best_key is None or key > best_key:
            best_key = key
            best_start = start
            best_rows = summaries
    return best_start, best_rows


def available_theta_phi(keys: list[tuple[float, float]]) -> tuple[list[float], list[float]]:
    theta = sorted({key[0] for key in keys})
    phi = sorted({key[1] for key in keys})
    return theta, phi


def valid_baselines(elements: list[int]) -> list[tuple[str, str]]:
    labels = {f"E{element}" for element in elements}
    return [(left, right) for left, right in BASELINES if left in labels and right in labels]


def element_from_label(label: str) -> int:
    return int(label[1:])


def assignment_feed_for_basis(assignment: str, basis: str) -> str:
    mapping = ASSIGNMENTS[assignment]
    for feed, assigned_basis in mapping.items():
        if assigned_basis == basis:
            return feed
    raise RuntimeError(f"No feed for basis {basis} in {assignment}")


def local_slopes(phi_values: list[float], y_values: list[float]) -> dict[float, float]:
    slopes: dict[float, float] = {}
    if len(phi_values) < 2:
        return {phi: float("nan") for phi in phi_values}
    for idx, phi in enumerate(phi_values):
        if idx == 0:
            denom = phi_values[1] - phi_values[0]
            slopes[phi] = (y_values[1] - y_values[0]) / denom if abs(denom) > 1e-9 else float("nan")
        elif idx == len(phi_values) - 1:
            denom = phi_values[-1] - phi_values[-2]
            slopes[phi] = (y_values[-1] - y_values[-2]) / denom if abs(denom) > 1e-9 else float("nan")
        else:
            denom = phi_values[idx + 1] - phi_values[idx - 1]
            slopes[phi] = (y_values[idx + 1] - y_values[idx - 1]) / denom if abs(denom) > 1e-9 else float("nan")
    return slopes


def curvature_values(phi_values: list[float], y_values: list[float]) -> list[float]:
    if len(phi_values) < 3:
        return []
    slopes = []
    mid_phis = []
    for idx in range(len(phi_values) - 1):
        denom = phi_values[idx + 1] - phi_values[idx]
        if abs(denom) <= 1e-9:
            continue
        slopes.append((y_values[idx + 1] - y_values[idx]) / denom)
        mid_phis.append(0.5 * (phi_values[idx + 1] + phi_values[idx]))
    curvatures = []
    for idx in range(len(slopes) - 1):
        denom = mid_phis[idx + 1] - mid_phis[idx]
        if abs(denom) > 1e-9:
            curvatures.append((slopes[idx + 1] - slopes[idx]) / denom)
    return curvatures


def build_phase_metrics(
    entries: dict[str, dict[int, FieldEntry]],
    elements: list[int],
    keys: list[tuple[float, float]],
    matrix_summaries: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    theta_values, phi_values = available_theta_phi(keys)
    theta_cuts = [theta for theta in THETA_CUTS_DEG if any(abs(theta - item) < 1e-9 for item in theta_values)]
    baselines = valid_baselines(elements)
    scopes = {
        "full360": (0.0, 360.0),
    }
    best270_rows = [row for row in matrix_summaries if row["scope"] == "best270"]
    if best270_rows:
        scopes["best270"] = (float(best270_rows[0]["phi_start_deg"]), PHI_WINDOW_DEG)

    curve_rows: list[dict[str, Any]] = []
    summary_rows: list[dict[str, Any]] = []

    for assignment in ASSIGNMENTS:
        for scope, (phi_start, phi_width) in scopes.items():
            scoped_phi_values = [phi for phi in phi_values if scope == "full360" or in_phi_window(phi, phi_start, phi_width)]
            scoped_keys_set = {(theta, phi) for theta in theta_values for phi in scoped_phi_values if (theta, phi) in keys}
            channel_mags = []
            for basis in ["H", "V"]:
                feed = assignment_feed_for_basis(assignment, basis)
                for theta, phi in scoped_keys_set:
                    for element in elements:
                        channel_mags.append(abs(component(entries, feed, element, (theta, phi), basis)))
            reference = max(channel_mags) if channel_mags else 0.0
            floor = reference * 10.0 ** (MAG_VALID_FLOOR_REL_DB / 20.0) if reference > 0.0 else 0.0

            for theta in theta_cuts:
                for left, right in baselines:
                    left_element = element_from_label(left)
                    right_element = element_from_label(right)
                    curves_by_basis: dict[str, list[dict[str, Any]]] = {}
                    for basis in ["H", "V"]:
                        feed = assignment_feed_for_basis(assignment, basis)
                        rows: list[dict[str, Any]] = []
                        for phi in scoped_phi_values:
                            key = (theta, phi)
                            if key not in scoped_keys_set:
                                continue
                            left_value = component(entries, feed, left_element, key, basis)
                            right_value = component(entries, feed, right_element, key, basis)
                            valid = abs(left_value) >= floor and abs(right_value) >= floor
                            rows.append(
                                {
                                    "assignment": assignment,
                                    "scope": scope,
                                    "phi_start_deg": phi_start,
                                    "phi_width_deg": phi_width,
                                    "theta_deg": theta,
                                    "phi_deg": phi,
                                    "basis": basis,
                                    "feed": feed,
                                    "baseline": f"{left}-{right}",
                                    "left_source": entries[feed][left_element].source,
                                    "right_source": entries[feed][right_element].source,
                                    "left_mag": abs(left_value),
                                    "right_mag": abs(right_value),
                                    "left_mag_rel_db": rel_db(abs(left_value), reference),
                                    "right_mag_rel_db": rel_db(abs(right_value), reference),
                                    "pdoa_deg": wrap_deg(phase_deg(left_value) - phase_deg(right_value)),
                                    "valid": valid,
                                }
                            )
                        valid_rows = [row for row in rows if row["valid"]]
                        unwrapped = unwrap_degrees([row["pdoa_deg"] for row in valid_rows])
                        for row, value in zip(valid_rows, unwrapped):
                            row["pdoa_unwrapped_deg"] = value
                        for row in rows:
                            row.setdefault("pdoa_unwrapped_deg", row["pdoa_deg"])
                            curve_rows.append(row)
                        curves_by_basis[basis] = rows

                        valid_phi = [row["phi_deg"] for row in valid_rows]
                        valid_pdoa = [row["pdoa_unwrapped_deg"] for row in valid_rows]
                        slopes = []
                        if len(valid_phi) >= 2:
                            for idx in range(len(valid_phi) - 1):
                                denom = valid_phi[idx + 1] - valid_phi[idx]
                                if abs(denom) > 1e-9:
                                    slopes.append((valid_pdoa[idx + 1] - valid_pdoa[idx]) / denom)
                        curvatures = curvature_values(valid_phi, valid_pdoa)
                        summary_rows.append(
                            {
                                "summary_type": "smoothness",
                                "assignment": assignment,
                                "scope": scope,
                                "phi_start_deg": phi_start,
                                "phi_width_deg": phi_width,
                                "theta_deg": theta,
                                "basis": basis,
                                "feed": feed,
                                "baseline": f"{left}-{right}",
                                "valid_count": len(valid_rows),
                                "slope_abs_p95_deg_per_deg": percentile([abs(value) for value in slopes], 95.0),
                                "slope_abs_max_deg_per_deg": max([abs(value) for value in slopes], default=float("nan")),
                                "curvature_rms_deg_per_deg2": rms(curvatures),
                                "curvature_abs_max_deg_per_deg2": max([abs(value) for value in curvatures], default=float("nan")),
                            }
                        )

                    h_rows = {row["phi_deg"]: row for row in curves_by_basis.get("H", []) if row["valid"]}
                    v_rows = {row["phi_deg"]: row for row in curves_by_basis.get("V", []) if row["valid"]}
                    common_phi = sorted(set(h_rows) & set(v_rows))
                    deltas = [wrap_deg(h_rows[phi]["pdoa_deg"] - v_rows[phi]["pdoa_deg"]) for phi in common_phi]
                    unwrapped_deltas = unwrap_degrees(deltas)
                    bias = median(unwrapped_deltas) if unwrapped_deltas else float("nan")
                    residuals = [wrap_deg(delta - bias) for delta in unwrapped_deltas]
                    h_unwrapped = [h_rows[phi]["pdoa_unwrapped_deg"] for phi in common_phi]
                    slopes_by_phi = local_slopes(common_phi, h_unwrapped)
                    az_errors = []
                    for phi, residual in zip(common_phi, residuals):
                        slope = slopes_by_phi.get(phi, float("nan"))
                        if not math.isnan(slope) and abs(slope) >= AZIMUTH_SLOPE_FLOOR_DEG_PER_DEG:
                            az_errors.append(residual / slope)
                    summary_rows.append(
                        {
                            "summary_type": "hv_pdoa_consistency",
                            "assignment": assignment,
                            "scope": scope,
                            "phi_start_deg": phi_start,
                            "phi_width_deg": phi_width,
                            "theta_deg": theta,
                            "basis": "H_vs_V",
                            "feed": f"{assignment_feed_for_basis(assignment, 'H')}/{assignment_feed_for_basis(assignment, 'V')}",
                            "baseline": f"{left}-{right}",
                            "valid_count": len(common_phi),
                            "hv_pdoa_delta_bias_median_deg": bias,
                            "hv_pdoa_delta_rms_deg": rms(deltas),
                            "hv_pdoa_delta_p95_abs_deg": percentile([abs(value) for value in deltas], 95.0),
                            "hv_pdoa_delta_max_abs_deg": max([abs(value) for value in deltas], default=float("nan")),
                            "hv_pdoa_residual_rms_after_bias_deg": rms(residuals),
                            "hv_pdoa_residual_p95_abs_after_bias_deg": percentile([abs(value) for value in residuals], 95.0),
                            "hv_pdoa_residual_max_abs_after_bias_deg": max([abs(value) for value in residuals], default=float("nan")),
                            "azimuth_error_rms_equiv_deg": rms(az_errors),
                            "azimuth_error_p95_abs_equiv_deg": percentile([abs(value) for value in az_errors], 95.0),
                            "azimuth_error_max_abs_equiv_deg": max([abs(value) for value in az_errors], default=float("nan")),
                            "azimuth_error_sample_count": len(az_errors),
                            "phase_residual_p95_target_deg": PHASE_RESIDUAL_P95_TARGET_DEG,
                            "phase_residual_target_pass": (
                                percentile([abs(value) for value in residuals], 95.0) <= PHASE_RESIDUAL_P95_TARGET_DEG
                                if residuals
                                else False
                            ),
                        }
                    )
    return curve_rows, summary_rows


def aggregate_phase_summary(phase_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in phase_rows:
        if row.get("summary_type") == "hv_pdoa_consistency":
            grouped[(str(row["assignment"]), str(row["scope"]), str(row["summary_type"]))].append(row)
    out: list[dict[str, Any]] = []
    for (assignment, scope, summary_type), items in sorted(grouped.items()):
        residual_p95 = [float(item["hv_pdoa_residual_p95_abs_after_bias_deg"]) for item in items if not math.isnan(float(item["hv_pdoa_residual_p95_abs_after_bias_deg"]))]
        az_p95 = [float(item["azimuth_error_p95_abs_equiv_deg"]) for item in items if not math.isnan(float(item["azimuth_error_p95_abs_equiv_deg"]))]
        out.append(
            {
                "summary_type": "hv_pdoa_consistency_aggregate",
                "assignment": assignment,
                "scope": scope,
                "curve_count": len(items),
                "hv_residual_p95_abs_avg_deg": fmean(residual_p95) if residual_p95 else float("nan"),
                "hv_residual_p95_abs_max_deg": max(residual_p95, default=float("nan")),
                "azimuth_error_p95_abs_avg_equiv_deg": fmean(az_p95) if az_p95 else float("nan"),
                "azimuth_error_p95_abs_max_equiv_deg": max(az_p95, default=float("nan")),
                "phase_residual_p95_target_deg": PHASE_RESIDUAL_P95_TARGET_DEG,
                "phase_residual_target_pass": bool(residual_p95) and max(residual_p95) <= PHASE_RESIDUAL_P95_TARGET_DEG,
            }
        )
    return out


def read_sparam_summary(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    with path.open(newline="", encoding="utf-8-sig") as f:
        for raw in csv.DictReader(f):
            rows.append(
                {
                    "candidate_index": raw.get("candidate_index", ""),
                    "candidate": raw.get("candidate", ""),
                    "case": raw.get("case", ""),
                    "active_pol": raw.get("active_pol", ""),
                    "worst_active_s11_expr": raw.get("worst_active_s11_expr", ""),
                    "worst_active_s11_db": num(raw.get("worst_active_s11_db")),
                    "worst_low_s11_expr": raw.get("worst_low_s11_expr", ""),
                    "worst_low_s11_db": num(raw.get("worst_low_s11_db")),
                    "coupling_worst_db": max_dict_value(raw.get("coupling_worst_db", "")),
                    "active_s11_pass": str(raw.get("active_s11_pass", "")).strip().lower() == "true",
                    "low_s11_pass": str(raw.get("low_s11_pass", "")).strip().lower() == "true",
                }
            )
    return rows


def read_gain_rows(entries: dict[str, dict[int, FieldEntry]], gain_dir: Path) -> list[dict[str, Any]]:
    if not gain_dir.exists():
        return []
    rows: list[dict[str, Any]] = []
    for feed in ["A", "B"]:
        for element, entry in sorted(entries[feed].items()):
            path = gain_dir / f"{entry.case}_{entry.source}_single_source_native_farfield_default.csv"
            if not path.exists():
                continue
            has_zero_phi = False
            parsed = parse_gain_csv(path)
            has_zero_phi = any(abs(row["phi_deg"]) < 1e-9 for row in parsed)
            for row in parsed:
                if has_zero_phi and abs(row["phi_deg"] - 360.0) < 1e-9:
                    continue
                item: dict[str, Any] = {
                    "case": entry.case,
                    "feed": feed,
                    "element": f"E{element}",
                    "source": entry.source,
                    "gain_csv": str(path),
                }
                item.update(row)
                rows.append(item)
    return rows


def summarize_gain_rows(gain_rows: list[dict[str, Any]], matrix_summary: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not gain_rows:
        return []
    out: list[dict[str, Any]] = []
    for matrix_row in matrix_summary:
        scope = str(matrix_row["scope"])
        assignment = str(matrix_row["assignment"])
        phi_start = float(matrix_row["phi_start_deg"])
        phi_width = float(matrix_row["phi_width_deg"])
        scoped = [
            row
            for row in gain_rows
            if scope == "full360" or in_phi_window(float(row["phi_deg"]), phi_start, phi_width)
        ]
        gain_values = [float(row["gain_total_dbi"]) for row in scoped if not math.isnan(float(row["gain_total_dbi"]))]
        realized_values = [float(row["realized_gain_total_dbi"]) for row in scoped if not math.isnan(float(row["realized_gain_total_dbi"]))]
        worst_gain = min(scoped, key=lambda row: float(row["gain_total_dbi"])) if scoped else {}
        worst_realized = min(scoped, key=lambda row: float(row["realized_gain_total_dbi"])) if scoped else {}
        row_out: dict[str, Any] = {
            "scope": scope,
            "assignment": assignment,
            "phi_start_deg": phi_start,
            "phi_width_deg": phi_width,
            "sample_count": len(scoped),
            "gain_target_dbi": GAIN_TARGET_DBI,
            "gain_total_min_dbi": min(gain_values, default=float("nan")),
            "gain_total_p5_dbi": percentile(gain_values, 5.0),
            "gain_total_median_dbi": median(gain_values) if gain_values else float("nan"),
            "realized_gain_total_min_dbi": min(realized_values, default=float("nan")),
            "realized_gain_total_p5_dbi": percentile(realized_values, 5.0),
            "realized_gain_total_median_dbi": median(realized_values) if realized_values else float("nan"),
            "gain_total_target_pass": bool(gain_values) and min(gain_values) >= GAIN_TARGET_DBI,
            "realized_gain_total_target_pass": bool(realized_values) and min(realized_values) >= GAIN_TARGET_DBI,
            "worst_gain_source": worst_gain.get("source", ""),
            "worst_gain_theta_deg": worst_gain.get("theta_deg", float("nan")),
            "worst_gain_phi_deg": worst_gain.get("phi_deg", float("nan")),
            "worst_realized_source": worst_realized.get("source", ""),
            "worst_realized_theta_deg": worst_realized.get("theta_deg", float("nan")),
            "worst_realized_phi_deg": worst_realized.get("phi_deg", float("nan")),
        }
        out.append(row_out)
    return out


def max_dict_value(text: str) -> float:
    values = [num(match) for match in re.findall(r":\s*(-?\d+(?:\.\d+)?)", text or "")]
    clean = [value for value in values if not math.isnan(value)]
    return max(clean) if clean else float("nan")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        return
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            out: dict[str, Any] = {}
            for field in fields:
                value = row.get(field, "")
                if isinstance(value, float):
                    out[field] = f"{value:.6f}" if not math.isinf(value) else "inf"
                else:
                    out[field] = value
            writer.writerow(out)


def best_matrix_row(rows: list[dict[str, Any]], scope: str = "best270") -> dict[str, Any]:
    candidates = [row for row in rows if row["scope"] == scope] or rows
    return max(
        candidates,
        key=lambda row: (
            float(row.get("pair_min_xpd_db_p5", -999.0)),
            float(row.get("ab_orthogonality_db_p5", -999.0)),
            -float(row.get("condition_db_p95", 999.0)),
        ),
    )


def phase_aggregate_row(rows: list[dict[str, Any]], assignment: str, scope: str) -> dict[str, Any] | None:
    for row in rows:
        if (
            row.get("summary_type") == "hv_pdoa_consistency_aggregate"
            and row.get("assignment") == assignment
            and row.get("scope") == scope
        ):
            return row
    return None


def gain_summary_row(rows: list[dict[str, Any]], assignment: str, scope: str) -> dict[str, Any] | None:
    for row in rows:
        if row.get("assignment") == assignment and row.get("scope") == scope:
            return row
    return None


def plot_phase_curves(curve_rows: list[dict[str, Any]], assignment: str, scope: str) -> Path | None:
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from matplotlib import font_manager
    except Exception:
        return None

    available_fonts = {font.name for font in font_manager.fontManager.ttflist}
    for candidate in ["Microsoft YaHei", "SimHei", "SimSun", "Arial Unicode MS"]:
        if candidate in available_fonts:
            plt.rcParams["font.sans-serif"] = [candidate, "DejaVu Sans"]
            break
    plt.rcParams["axes.unicode_minus"] = False

    selected = [
        row
        for row in curve_rows
        if row["assignment"] == assignment
        and row["scope"] == scope
        and abs(float(row["theta_deg"]) - PLOT_THETA_DEG) < 1e-9
        and row["baseline"] in {f"{left}-{right}" for left, right in PLOT_BASELINES}
        and row["valid"]
    ]
    if not selected:
        return None
    phi_start = float(selected[0].get("phi_start_deg", 0.0))
    use_window_axis = scope != "full360"
    PLOTS_DIR.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(1, len(PLOT_BASELINES), figsize=(13.0, 4.8), sharex=True)
    if len(PLOT_BASELINES) == 1:
        axes = [axes]
    for ax, (left, right) in zip(axes, PLOT_BASELINES):
        baseline = f"{left}-{right}"
        for basis, color in [("H", "#1f77b4"), ("V", "#d62728")]:
            curve = [row for row in selected if row["baseline"] == baseline and row["basis"] == basis]
            if use_window_axis:
                curve = sorted(curve, key=lambda item: (float(item["phi_deg"]) - phi_start) % 360.0)
                x_values = [(float(row["phi_deg"]) - phi_start) % 360.0 for row in curve]
                x_label = f"Phi offset from {phi_start:.0f} deg (deg)"
            else:
                curve = sorted(curve, key=lambda item: float(item["phi_deg"]))
                x_values = [float(row["phi_deg"]) for row in curve]
                x_label = "Phi (deg)"
            ax.plot(
                x_values,
                [float(row["pdoa_unwrapped_deg"]) for row in curve],
                label=basis,
                color=color,
                linewidth=1.7,
            )
        ax.set_title(f"{baseline} / Theta={PLOT_THETA_DEG:.0f} deg")
        ax.set_xlabel(x_label)
        ax.set_ylabel("Unwrapped PDOA (deg)")
        ax.grid(True, alpha=0.25)
        ax.legend()
    fig.suptitle(f"D44 双极化测角 H/V PDOA 对比 - {assignment} / {scope}", fontsize=14, fontweight="bold")
    fig.tight_layout(rect=[0.0, 0.0, 1.0, 0.92])
    out = PLOTS_DIR / f"{STEM}_{assignment}_{scope}_theta{PLOT_THETA_DEG:.0f}_pdoa_hv.png"
    fig.savefig(out, dpi=180)
    plt.close(fig)
    return out


def write_report(payload: dict[str, Any]) -> None:
    matrix_rows = payload["matrix_summary"]
    phase_rows = payload["phase_aggregate_summary"]
    gain_rows = payload["gain_summary"]
    best = best_matrix_row(matrix_rows)
    best_phase = phase_aggregate_row(phase_rows, best["assignment"], best["scope"])
    best_gain = gain_summary_row(gain_rows, best["assignment"], best["scope"])
    sparam_rows = payload["sparam_summary"]
    worst_s11 = max((float(row["worst_active_s11_db"]) for row in sparam_rows if not math.isnan(float(row["worst_active_s11_db"]))), default=float("nan"))
    worst_coupling = max((float(row["coupling_worst_db"]) for row in sparam_rows if not math.isnan(float(row["coupling_worst_db"]))), default=float("nan"))
    s11_pass = bool(sparam_rows) and all(bool(row["active_s11_pass"]) for row in sparam_rows)

    lines = [
        "# D44 双极化测角评估指标报告",
        "",
        "## 指标定义",
        "",
        "- 局部极化基准：`H = Ephi`，`V = -Etheta`，即水平切向与板法向/世界垂直投影后的局部正交基。",
        "- 响应矩阵：每个阵元、每个方向构建 `[[A_H, A_V], [B_H, B_V]]`。",
        f"- XPD 目标：A/B 按某一 H/V 分配后，端口共极化/交叉极化比值最小值建议 `>= {XPD_TARGET_DB:.1f} dB`。",
        f"- 极化正交目标：A/B 复矢量相关系数换算的正交度建议 `>= {ORTHOGONALITY_TARGET_DB:.1f} dB`。",
        f"- 矩阵条件数目标：2x2 极化响应矩阵条件数建议 `<= {CONDITION_MAX_TARGET_DB:.1f} dB`。",
        f"- 测角相位目标：H/V 同基线 PDOA 去除中值偏置后的 P95 残差建议 `<= {PHASE_RESIDUAL_P95_TARGET_DEG:.1f} deg`。",
        "",
        "## 当前最佳分配",
        "",
        f"- 评估窗口：`{best['scope']}`，Phi `{fmt(best['phi_start_deg'], 0)}..{fmt((float(best['phi_start_deg']) + float(best['phi_width_deg'])) % 360.0, 0)} deg`，宽度 `{fmt(best['phi_width_deg'], 0)} deg`。",
        f"- 端口分配：`{best['assignment']}`。",
        f"- 成对最小 XPD：min `{fmt(best['pair_min_xpd_db_min'])} dB`，P5 `{fmt(best['pair_min_xpd_db_p5'])} dB`，median `{fmt(best['pair_min_xpd_db_median'])} dB`。",
        f"- A/B 极化正交度：min `{fmt(best['ab_orthogonality_db_min'])} dB`，P5 `{fmt(best['ab_orthogonality_db_p5'])} dB`，median `{fmt(best['ab_orthogonality_db_median'])} dB`。",
        f"- 2x2 条件数：P95 `{fmt(best['condition_db_p95'])} dB`，max `{fmt(best['condition_db_max'])} dB`。",
        f"- 共极化相对幅度覆盖：min `{fmt(best['assigned_co_rel_db_min'])} dB`，P5 `{fmt(best['assigned_co_rel_db_p5'])} dB`，`>-35 dB` 样本占比 `{fmt(best['assigned_co_floor_pass_percent'], 1)}%`。",
    ]
    if best_gain:
        lines.extend(
            [
                f"- GainTotal 覆盖：min `{fmt(best_gain['gain_total_min_dbi'])} dBi`，P5 `{fmt(best_gain['gain_total_p5_dbi'])} dBi`，目标 `>= {GAIN_TARGET_DBI:.1f} dBi`。",
                f"- RealizedGainTotal 覆盖：min `{fmt(best_gain['realized_gain_total_min_dbi'])} dBi`，P5 `{fmt(best_gain['realized_gain_total_p5_dbi'])} dBi`。",
            ]
        )
    if best_phase:
        lines.extend(
            [
                f"- H/V PDOA 去偏置后残差：P95 avg `{fmt(best_phase['hv_residual_p95_abs_avg_deg'])} deg`，P95 max `{fmt(best_phase['hv_residual_p95_abs_max_deg'])} deg`。",
                f"- 等效方位误差：P95 avg `{fmt(best_phase['azimuth_error_p95_abs_avg_equiv_deg'])} deg`，P95 max `{fmt(best_phase['azimuth_error_p95_abs_max_equiv_deg'])} deg`。",
            ]
        )
    lines.extend(
        [
            "",
            "## S 参数复核引用",
            "",
            f"- A/B 当前工作态 S11：`{'达标' if s11_pass else '未确认/未达标'}`；最差 active S11 `{fmt(worst_s11)} dB`。",
            f"- A/B 同极化阵元间耦合最差值：`{fmt(worst_coupling)} dB`。",
            "- 说明：这里引用已有中心频点 native S 参数摘要；完整频带 S11/S21 仍需按最终几何重新扫频确认。",
            "",
            "## 全部分配摘要",
            "",
            "| 范围 | 分配 | Phi窗口 | Pair XPD min | Pair XPD P5 | 正交度 P5 | 条件数 P95 | 共极化P5 | XPD达标 | 条件数达标 |",
            "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- | --- |",
        ]
    )
    for row in sorted(matrix_rows, key=lambda item: (item["scope"], item["assignment"])):
        phi_label = f"{fmt(row['phi_start_deg'], 0)}..{fmt((float(row['phi_start_deg']) + float(row['phi_width_deg'])) % 360.0, 0)}"
        lines.append(
            f"| `{row['scope']}` | `{row['assignment']}` | {phi_label} | "
            f"{fmt(row['pair_min_xpd_db_min'])} | {fmt(row['pair_min_xpd_db_p5'])} | "
            f"{fmt(row['ab_orthogonality_db_p5'])} | {fmt(row['condition_db_p95'])} | "
            f"{fmt(row['assigned_co_rel_db_p5'])} | "
            f"{'是' if row['pair_min_xpd_db_target_pass'] else '否'} | "
            f"{'是' if row['condition_db_target_pass'] else '否'} |"
        )
    if gain_rows:
        lines.extend(
            [
                "",
                "## 增益覆盖摘要",
                "",
                "| 范围 | 分配 | GainTotal min | Realized min | 最差 Realized 点 | 增益达标 |",
                "| --- | --- | ---: | ---: | --- | --- |",
            ]
        )
        for row in sorted(gain_rows, key=lambda item: (item["scope"], item["assignment"])):
            lines.append(
                f"| `{row['scope']}` | `{row['assignment']}` | {fmt(row['gain_total_min_dbi'])} dBi | "
                f"{fmt(row['realized_gain_total_min_dbi'])} dBi | "
                f"`{row['worst_realized_source']}` / Theta {fmt(row['worst_realized_theta_deg'], 0)} / Phi {fmt(row['worst_realized_phi_deg'], 0)} | "
                f"{'是' if row['gain_total_target_pass'] and row['realized_gain_total_target_pass'] else '否'} |"
            )
    lines.extend(
        [
            "",
            "## 工程结论",
            "",
            "- 该指标框架已把双极化测角拆成端口极化分离、2x2 极化矩阵可逆性、H/V PDOA 一致性、相对覆盖幅度和 S 参数五类指标。",
            "- 当前数据若 XPD/条件数未达标，说明问题不是单纯的 `Etheta/Ephi` 坐标口径，而是 A/B 两端口在局部 H/V 基准下仍存在明显混合或矩阵病态。",
            "- 后续优化应优先让每个阵元的 A/B 两个端口形成同相位中心、低相关、低条件数的局部 H/V 响应矩阵，再把 GainTotal 与完整频带 S11/S21 并入最终门限。",
            "",
            "## 输出文件",
            "",
            f"- 矩阵样本 CSV：`{MATRIX_SAMPLES_CSV}`",
            f"- 矩阵摘要 CSV：`{MATRIX_SUMMARY_CSV}`",
            f"- PDOA 曲线 CSV：`{PHASE_CURVES_CSV}`",
            f"- PDOA 摘要 CSV：`{PHASE_SUMMARY_CSV}`",
            f"- S 参数摘要 CSV：`{SPARAM_SUMMARY_CSV}`",
            f"- 增益覆盖摘要 CSV：`{GAIN_SUMMARY_CSV}`",
            f"- 指标 JSON：`{METRICS_JSON}`",
        ]
    )
    if payload.get("plot_path"):
        lines.append(f"- H/V PDOA 对比图：`{payload['plot_path']}`")
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run(manifest: Path, sparam_summary: Path, gain_dir: Path) -> dict[str, Any]:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    entries = read_manifest(manifest)
    elements = common_elements(entries)
    keys = common_keys(entries, elements)
    if not elements:
        raise RuntimeError("No paired A/B elements found")
    if not keys:
        raise RuntimeError("No common FOV field samples found")

    matrix_samples = build_matrix_samples(entries, elements, keys)
    _, phi_values = available_theta_phi(keys)
    full360_summary = matrix_summary_for_scope(matrix_samples, "full360", 0.0, 360.0)
    best_start, best270_summary = choose_best_270_window(matrix_samples, phi_values)
    matrix_summary = full360_summary + best270_summary
    phase_curves, phase_summary = build_phase_metrics(entries, elements, keys, matrix_summary)
    phase_aggregate = aggregate_phase_summary(phase_summary)
    sparam_rows = read_sparam_summary(sparam_summary)
    gain_rows = read_gain_rows(entries, gain_dir)
    gain_summary = summarize_gain_rows(gain_rows, matrix_summary)

    write_csv(MATRIX_SAMPLES_CSV, matrix_samples)
    write_csv(MATRIX_SUMMARY_CSV, matrix_summary)
    write_csv(PHASE_CURVES_CSV, phase_curves)
    write_csv(PHASE_SUMMARY_CSV, phase_summary + phase_aggregate)
    write_csv(SPARAM_SUMMARY_CSV, sparam_rows)
    write_csv(GAIN_SUMMARY_CSV, gain_summary)

    best = best_matrix_row(matrix_summary)
    plot_path = plot_phase_curves(phase_curves, str(best["assignment"]), str(best["scope"]))
    payload = {
        "manifest": str(manifest),
        "sparam_summary_source": str(sparam_summary),
        "gain_dir": str(gain_dir),
        "freq_ghz": FREQ_GHZ,
        "theta_min_deg": THETA_MIN_DEG,
        "theta_max_deg": THETA_MAX_DEG,
        "phi_window_deg": PHI_WINDOW_DEG,
        "best270_phi_start_deg": best_start,
        "elements": elements,
        "matrix_summary": matrix_summary,
        "phase_aggregate_summary": phase_aggregate,
        "sparam_summary": sparam_rows,
        "gain_summary": gain_summary,
        "matrix_samples_csv": str(MATRIX_SAMPLES_CSV),
        "matrix_summary_csv": str(MATRIX_SUMMARY_CSV),
        "phase_curves_csv": str(PHASE_CURVES_CSV),
        "phase_summary_csv": str(PHASE_SUMMARY_CSV),
        "sparam_summary_csv": str(SPARAM_SUMMARY_CSV),
        "gain_summary_csv": str(GAIN_SUMMARY_CSV),
        "plot_path": str(plot_path) if plot_path else "",
        "report_md": str(REPORT_MD),
    }
    METRICS_JSON.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    write_report(payload)
    print(json.dumps({"report": str(REPORT_MD), "best_assignment": best["assignment"], "best_scope": best["scope"]}, indent=2, ensure_ascii=False), flush=True)
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--sparam-summary", type=Path, default=DEFAULT_SPARAM_SUMMARY)
    parser.add_argument("--gain-dir", type=Path, default=DEFAULT_GAIN_DIR)
    args = parser.parse_args()
    run(args.manifest, args.sparam_summary, args.gain_dir)


if __name__ == "__main__":
    main()
