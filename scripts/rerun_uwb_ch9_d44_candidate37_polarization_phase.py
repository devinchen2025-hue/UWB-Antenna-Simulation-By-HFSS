from __future__ import annotations

import argparse
import cmath
import csv
import json
import math
import os
import subprocess
import time
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from statistics import fmean
from typing import Any

import matplotlib.pyplot as plt
from matplotlib import font_manager

import build_uwb_ch9_hfss_d44_topology as builder
import evaluate_uwb_ch9_d44_truefed_l_fov_gain as truefed_check
import optimize_uwb_ch9_d44_dualpol_rf_switch_fov_gain as fov_gain
import simulate_uwb_ch9_d44_dualpol_rf_switch_workstate as workstate


ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = ROOT / "reports_d44_dualpol_truefed_l_polarization_phase"
STEM = "UWB_CH9_D44_DUALPOL_TRUEFED_L_POLARIZATION_PHASE"
AEDT_EXE = Path(r"D:\Program Files\AnsysEM\v231\Win64\ansysedt.exe")
NATIVE_FIELD_SCRIPT = ROOT / "scripts" / "aedt_export_ch9_native_field_components.py"

FIELD_DIR = REPORT_DIR / "native_fields"
PLOTS_DIR = REPORT_DIR / "plots"
FIELDS_MANIFEST_CSV = REPORT_DIR / f"{STEM}_field_manifest.csv"
CURVES_CSV = REPORT_DIR / f"{STEM}_azimuth_phase_curves.csv"
SUMMARY_CSV = REPORT_DIR / f"{STEM}_polarization_error_summary.csv"
AGGREGATE_CSV = REPORT_DIR / f"{STEM}_polarization_aggregate.csv"
XPD_SUMMARY_CSV = REPORT_DIR / f"{STEM}_xpd_summary.csv"
METRICS_JSON = REPORT_DIR / f"{STEM}_metrics.json"
REPORT_MD = REPORT_DIR / f"{STEM}_report.md"

FREQ_GHZ = 8.0
THETA_MIN_DEG = 45.0
THETA_MAX_DEG = 90.0
THETA_CUTS_DEG = [45.0, 60.0, 75.0, 90.0]
PLOT_THETA_DEG = 90.0
POLARIZATIONS_DEG = [0.0, 45.0, 90.0, 135.0]
BASELINES = [("E1", "E3"), ("E2", "E4"), ("E1", "E2"), ("E2", "E3"), ("E3", "E4"), ("E4", "E1")]
PLOT_BASELINES = [("E1", "E3"), ("E2", "E4")]
MAG_VALID_FLOOR_REL_DB = -35.0
AZ_ERROR_SLOPE_FLOOR = 0.5
XPD_TARGET_DB = 25.0
XPD_CO_POL_DEG = 0.0
XPD_CROSS_POL_DEG = 90.0


@dataclass(frozen=True)
class FieldPoint:
    theta_deg: float
    phi_deg: float
    etheta: complex
    ephi: complex


def safe_slug(value: str, limit: int = 96) -> str:
    return fov_gain.safe_slug(value, limit)


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


def wrap_deg(value: float) -> float:
    return (value + 180.0) % 360.0 - 180.0


def phase_deg(value: complex) -> float:
    return math.degrees(cmath.phase(value))


def unwrap_degrees(values: list[float]) -> list[float]:
    if not values:
        return []
    unwrapped = [values[0]]
    offset = 0.0
    prev = values[0]
    for value in values[1:]:
        delta = value - prev
        if delta > 180.0:
            offset -= 360.0
        elif delta < -180.0:
            offset += 360.0
        unwrapped.append(value + offset)
        prev = value
    return unwrapped


def rms(values: list[float]) -> float:
    return math.sqrt(fmean(value * value for value in values)) if values else 0.0


def percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    idx = min(len(ordered) - 1, max(0, math.ceil(len(ordered) * pct / 100.0) - 1))
    return ordered[idx]


def configure_font() -> None:
    available = {font.name for font in font_manager.fontManager.ttflist}
    for candidate in ["Microsoft YaHei", "SimHei", "SimSun", "Arial Unicode MS"]:
        if candidate in available:
            plt.rcParams["font.sans-serif"] = [candidate, "DejaVu Sans"]
            break
    plt.rcParams["axes.unicode_minus"] = False


def selectable_sources(case: workstate.SwitchCase) -> list[str]:
    return [f"P{idx}{case.active_pol}" for idx in range(1, 5)]


def native_paths(case_slug: str) -> dict[str, Path]:
    return {
        "field": FIELD_DIR / f"{case_slug}_native_field_components.csv",
        "sources": FIELD_DIR / f"{case_slug}_native_sources.txt",
        "log": FIELD_DIR / f"{case_slug}_native_field_export.log",
    }


def build_single_source_project(candidate: fov_gain.GainCandidate, case: workstate.SwitchCase, source: str, cores: int, tasks: int) -> Path:
    params = workstate.set_case_params(candidate.params, case)
    params.update(
        {
            "single_source_feed_enabled": 1.0,
            "single_source_feed_name": source,
        }
    )
    builder.TOPOLOGIES[fov_gain.TOPOLOGY]["params"] = params
    return builder.build_project(
        fov_gain.TOPOLOGY,
        analyze=True,
        non_graphical=True,
        quick=True,
        band_samples=False,
        sparam_only=False,
        return_hfss=False,
        analysis_cores=cores,
        analysis_tasks=tasks,
    )


def restore_full_project(candidate: fov_gain.GainCandidate, case: workstate.SwitchCase) -> None:
    params = workstate.set_case_params(candidate.params, case)
    builder.TOPOLOGIES[fov_gain.TOPOLOGY]["params"] = params
    builder.build_project(
        fov_gain.TOPOLOGY,
        analyze=False,
        non_graphical=True,
        quick=True,
        band_samples=False,
        sparam_only=False,
        return_hfss=False,
    )


def native_export_fields(case_slug: str) -> dict[str, Path]:
    FIELD_DIR.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env.update(
        {
            "D44_AEDT_CASE": case_slug,
            "D44_AEDT_OUT_DIR": str(FIELD_DIR),
            "D44_AEDT_FREQ_GHZ": f"{FREQ_GHZ:g}",
        }
    )
    paths = native_paths(case_slug)
    cmd = [str(AEDT_EXE), "-ng", "-LogFile", str(paths["log"]), "-RunScriptAndExit", str(NATIVE_FIELD_SCRIPT)]
    subprocess.run(cmd, cwd=str(ROOT), env=env, check=True, timeout=420)
    return paths


def first_header_index(header: list[str], prefix: str) -> int:
    return next(idx for idx, name in enumerate(header) if name.startswith(prefix))


def expr_index(header: list[str], expr: str) -> int:
    return next(idx for idx, name in enumerate(header) if expr in name)


def parse_field_csv(path: Path) -> dict[tuple[float, float], FieldPoint]:
    with path.open(newline="", encoding="utf-8-sig") as f:
        rows = list(csv.reader(f))
    if len(rows) < 2:
        raise RuntimeError(f"Empty field CSV: {path}")
    header = rows[0]
    phi_idx = first_header_index(header, "Phi")
    theta_idx = first_header_index(header, "Theta")
    re_theta_idx = expr_index(header, "re(rETheta)")
    im_theta_idx = expr_index(header, "im(rETheta)")
    re_phi_idx = expr_index(header, "re(rEPhi)")
    im_phi_idx = expr_index(header, "im(rEPhi)")
    angle_rows = [
        (num(raw[theta_idx]), num(raw[phi_idx]))
        for raw in rows[1:]
        if len(raw) > max(phi_idx, theta_idx)
    ]
    swap_angle_columns = bool(angle_rows) and max(theta for theta, _ in angle_rows) > 180.0 and max(phi for _, phi in angle_rows) <= 180.0
    grid: dict[tuple[float, float], FieldPoint] = {}
    for raw in rows[1:]:
        if len(raw) <= max(phi_idx, theta_idx, re_theta_idx, im_theta_idx, re_phi_idx, im_phi_idx):
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


def read_sources(path: Path) -> list[str]:
    return [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def linear_projection(point: FieldPoint, polarization_deg: float) -> complex:
    angle = math.radians(polarization_deg)
    return point.etheta * math.cos(angle) + point.ephi * math.sin(angle)


def rel_db(value: float, reference: float) -> float:
    if value <= 0.0 or reference <= 0.0:
        return -999.0
    return 20.0 * math.log10(value / reference)


def xpd_db(point: FieldPoint, co_pol_deg: float = XPD_CO_POL_DEG) -> float:
    co = abs(linear_projection(point, co_pol_deg))
    cross = abs(linear_projection(point, co_pol_deg + 90.0))
    if co <= 0.0 or cross <= 0.0:
        return float("nan")
    return 20.0 * math.log10(co / cross)


def summarize_xpd_values(values: list[dict[str, Any]], prefix: str = "xpd") -> dict[str, Any]:
    valid = [row for row in values if not math.isnan(float(row["xpd_db"]))]
    ordered = sorted(float(row["xpd_db"]) for row in valid)
    if not ordered:
        return {
            f"{prefix}_sample_count": 0,
            f"{prefix}_min_db": float("nan"),
            f"{prefix}_p5_db": float("nan"),
            f"{prefix}_median_db": float("nan"),
            f"{prefix}_avg_db": float("nan"),
            f"{prefix}_max_db": float("nan"),
            f"{prefix}_target_db": XPD_TARGET_DB,
            f"{prefix}_margin_to_target_db": float("nan"),
            f"{prefix}_target_pass": False,
        }
    worst = min(valid, key=lambda row: float(row["xpd_db"]))
    min_db = ordered[0]
    return {
        f"{prefix}_sample_count": len(ordered),
        f"{prefix}_min_db": min_db,
        f"{prefix}_p5_db": percentile(ordered, 5.0),
        f"{prefix}_median_db": ordered[len(ordered) // 2],
        f"{prefix}_avg_db": fmean(ordered),
        f"{prefix}_max_db": ordered[-1],
        f"{prefix}_target_db": XPD_TARGET_DB,
        f"{prefix}_margin_to_target_db": min_db - XPD_TARGET_DB,
        f"{prefix}_target_pass": min_db >= XPD_TARGET_DB,
        f"{prefix}_worst_theta_deg": worst["theta_deg"],
        f"{prefix}_worst_phi_deg": worst["phi_deg"],
    }


def local_slopes(phi_values: list[float], y_values: list[float]) -> dict[float, float]:
    slopes: dict[float, float] = {}
    for idx, phi in enumerate(phi_values):
        if len(phi_values) < 2:
            slopes[phi] = float("nan")
        elif idx == 0:
            slopes[phi] = (y_values[1] - y_values[0]) / (phi_values[1] - phi_values[0])
        elif idx == len(phi_values) - 1:
            slopes[phi] = (y_values[-1] - y_values[-2]) / (phi_values[-1] - phi_values[-2])
        else:
            slopes[phi] = (y_values[idx + 1] - y_values[idx - 1]) / (phi_values[idx + 1] - phi_values[idx - 1])
    return slopes


def channel_map(case: workstate.SwitchCase) -> dict[str, str]:
    return {f"E{idx}": f"P{idx}{case.active_pol}" for idx in range(1, 5)}


def evaluate_case(case: workstate.SwitchCase, fields_by_source: dict[str, dict[tuple[float, float], FieldPoint]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    channels = channel_map(case)
    all_points = next(iter(fields_by_source.values()))
    available_theta = sorted({point.theta_deg for point in all_points.values()})
    available_phi = sorted({point.phi_deg for point in all_points.values()})
    theta_cuts = [theta for theta in THETA_CUTS_DEG if any(abs(theta - item) < 1e-6 for item in available_theta)]
    curve_rows: list[dict[str, Any]] = []
    summary_rows: list[dict[str, Any]] = []

    for theta in theta_cuts:
        for left, right in BASELINES:
            left_source = channels[left]
            right_source = channels[right]
            raw_by_pol: dict[float, list[dict[str, Any]]] = {}
            mags: list[float] = []
            for pol in POLARIZATIONS_DEG:
                rows: list[dict[str, Any]] = []
                for phi in available_phi:
                    key = (round(theta, 9), round(phi, 9))
                    if key not in all_points:
                        continue
                    v_left = linear_projection(fields_by_source[left_source][key], pol)
                    v_right = linear_projection(fields_by_source[right_source][key], pol)
                    mags.extend([abs(v_left), abs(v_right)])
                    rows.append(
                        {
                            "case": case.name,
                            "active_pol": case.active_pol,
                            "freq_ghz": FREQ_GHZ,
                            "theta_deg": theta,
                            "phi_deg": phi,
                            "linear_pol_deg": pol,
                            "baseline": f"{left}-{right}",
                            "left_source": left_source,
                            "right_source": right_source,
                            "left_mag": abs(v_left),
                            "right_mag": abs(v_right),
                            "pdoa_deg": wrap_deg(phase_deg(v_left) - phase_deg(v_right)),
                        }
                    )
                raw_by_pol[pol] = rows

            reference = max(mags) if mags else 1.0
            floor = reference * 10.0 ** (MAG_VALID_FLOOR_REL_DB / 20.0)
            ref_rows = raw_by_pol.get(0.0, [])
            ref_valid = [row for row in ref_rows if row["left_mag"] >= floor and row["right_mag"] >= floor]
            ref_unwrapped = unwrap_degrees([row["pdoa_deg"] for row in ref_valid])
            ref_by_phi = {row["phi_deg"]: row for row in ref_valid}
            ref_unwrapped_by_phi = {row["phi_deg"]: value for row, value in zip(ref_valid, ref_unwrapped)}
            slopes = local_slopes([row["phi_deg"] for row in ref_valid], ref_unwrapped)

            for pol, rows in raw_by_pol.items():
                valid_rows: list[dict[str, Any]] = []
                for row in rows:
                    row["left_mag_rel_db"] = rel_db(row["left_mag"], reference)
                    row["right_mag_rel_db"] = rel_db(row["right_mag"], reference)
                    row["valid"] = row["left_mag"] >= floor and row["right_mag"] >= floor
                    ref = ref_by_phi.get(row["phi_deg"])
                    if ref is not None and row["valid"]:
                        row["phase_error_vs_pol0_deg"] = wrap_deg(row["pdoa_deg"] - ref["pdoa_deg"])
                        slope = slopes.get(row["phi_deg"], float("nan"))
                        row["reference_phase_slope_deg_per_az_deg"] = slope
                        if abs(slope) >= AZ_ERROR_SLOPE_FLOOR:
                            row["azimuth_error_equiv_deg"] = row["phase_error_vs_pol0_deg"] / slope
                        else:
                            row["azimuth_error_equiv_deg"] = float("nan")
                        valid_rows.append(row)
                    else:
                        row["phase_error_vs_pol0_deg"] = 0.0 if pol == 0.0 and row["valid"] else float("nan")
                        row["reference_phase_slope_deg_per_az_deg"] = float("nan")
                        row["azimuth_error_equiv_deg"] = float("nan")
                    curve_rows.append(row)

                unwrapped_rows = [row for row in rows if row["valid"]]
                unwrapped = unwrap_degrees([row["pdoa_deg"] for row in unwrapped_rows])
                for row, value in zip(unwrapped_rows, unwrapped):
                    row["pdoa_unwrapped_deg"] = value
                for row in rows:
                    row.setdefault("pdoa_unwrapped_deg", row["pdoa_deg"])

                phase_errors = [row["phase_error_vs_pol0_deg"] for row in valid_rows if not math.isnan(row["phase_error_vs_pol0_deg"])]
                az_errors = [row["azimuth_error_equiv_deg"] for row in valid_rows if not math.isnan(row["azimuth_error_equiv_deg"])]
                summary_rows.append(
                    {
                        "case": case.name,
                        "active_pol": case.active_pol,
                        "freq_ghz": FREQ_GHZ,
                        "theta_deg": theta,
                        "linear_pol_deg": pol,
                        "baseline": f"{left}-{right}",
                        "valid_count": len(unwrapped_rows),
                        "total_count": len(rows),
                        "valid_percent": 100.0 * len(unwrapped_rows) / len(rows) if rows else 0.0,
                        "pdoa_span_unwrapped_deg": max(unwrapped) - min(unwrapped) if unwrapped else float("nan"),
                        "phase_error_rms_deg": rms(phase_errors),
                        "phase_error_mean_abs_deg": fmean(abs(value) for value in phase_errors) if phase_errors else 0.0,
                        "phase_error_p95_abs_deg": percentile([abs(value) for value in phase_errors], 95.0),
                        "phase_error_max_abs_deg": max([abs(value) for value in phase_errors], default=0.0),
                        "azimuth_error_rms_equiv_deg": rms(az_errors),
                        "azimuth_error_p95_abs_equiv_deg": percentile([abs(value) for value in az_errors], 95.0),
                        "azimuth_error_max_abs_equiv_deg": max([abs(value) for value in az_errors], default=0.0),
                        "azimuth_error_sample_count": len(az_errors),
                    }
                )
    return curve_rows, summary_rows


def aggregate_summary(summary_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, float], list[dict[str, Any]]] = defaultdict(list)
    for row in summary_rows:
        grouped[(row["case"], float(row["linear_pol_deg"]))].append(row)
    rows: list[dict[str, Any]] = []
    for (case, pol), items in sorted(grouped.items()):
        phase_rms_values = [float(item["phase_error_rms_deg"]) for item in items]
        phase_max_values = [float(item["phase_error_max_abs_deg"]) for item in items]
        az_rms_values = [float(item["azimuth_error_rms_equiv_deg"]) for item in items if int(item["azimuth_error_sample_count"]) > 0]
        az_max_values = [float(item["azimuth_error_max_abs_equiv_deg"]) for item in items if int(item["azimuth_error_sample_count"]) > 0]
        rows.append(
            {
                "case": case,
                "linear_pol_deg": pol,
                "curve_count": len(items),
                "phase_error_rms_avg_deg": fmean(phase_rms_values) if phase_rms_values else 0.0,
                "phase_error_rms_p95_deg": percentile(phase_rms_values, 95.0),
                "phase_error_max_abs_deg": max(phase_max_values, default=0.0),
                "azimuth_error_rms_avg_equiv_deg": fmean(az_rms_values) if az_rms_values else 0.0,
                "azimuth_error_rms_p95_equiv_deg": percentile(az_rms_values, 95.0),
                "azimuth_error_max_abs_equiv_deg": max(az_max_values, default=0.0),
            }
        )
    return rows


def evaluate_xpd_case(case: workstate.SwitchCase, fields_by_source: dict[str, dict[tuple[float, float], FieldPoint]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    summary_rows: list[dict[str, Any]] = []
    sample_rows: list[dict[str, Any]] = []
    for source, field_points in sorted(fields_by_source.items()):
        source_samples: list[dict[str, Any]] = []
        for point in field_points.values():
            if point.theta_deg < THETA_MIN_DEG or point.theta_deg > THETA_MAX_DEG:
                continue
            value = xpd_db(point)
            sample = {
                "case": case.name,
                "active_pol": case.active_pol,
                "source": source,
                "freq_ghz": FREQ_GHZ,
                "theta_deg": point.theta_deg,
                "phi_deg": point.phi_deg,
                "co_pol_deg": XPD_CO_POL_DEG,
                "cross_pol_deg": XPD_CROSS_POL_DEG,
                "xpd_db": value,
            }
            source_samples.append(sample)
            sample_rows.append(sample)
        row = {
            "level": "source",
            "case": case.name,
            "active_pol": case.active_pol,
            "source": source,
            "freq_ghz": FREQ_GHZ,
            "theta_min_deg": THETA_MIN_DEG,
            "theta_max_deg": THETA_MAX_DEG,
            "co_pol_deg": XPD_CO_POL_DEG,
            "cross_pol_deg": XPD_CROSS_POL_DEG,
        }
        row.update(summarize_xpd_values(source_samples))
        summary_rows.append(row)
    return summary_rows, sample_rows


def aggregate_xpd_samples(sample_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in sample_rows:
        grouped[row["case"]].append(row)
        grouped["ALL_CASES"].append(row)
    rows: list[dict[str, Any]] = []
    for case, samples in sorted(grouped.items()):
        active_pols = sorted({str(row["active_pol"]) for row in samples})
        row = {
            "level": "aggregate",
            "case": case,
            "active_pol": "/".join(active_pols),
            "source": "ALL",
            "freq_ghz": FREQ_GHZ,
            "theta_min_deg": THETA_MIN_DEG,
            "theta_max_deg": THETA_MAX_DEG,
            "co_pol_deg": XPD_CO_POL_DEG,
            "cross_pol_deg": XPD_CROSS_POL_DEG,
        }
        row.update(summarize_xpd_values(samples))
        rows.append(row)
    return rows


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: f"{row[key]:.6f}" if isinstance(row.get(key), float) else row.get(key, "") for key in fields})


COLORS = {
    0.0: "#1f77b4",
    45.0: "#d62728",
    90.0: "#2ca02c",
    135.0: "#9467bd",
}


def select_curve(rows: list[dict[str, Any]], case: str, theta: float, baseline: str, pol: float) -> list[dict[str, Any]]:
    selected = [
        row
        for row in rows
        if row["case"] == case
        and abs(float(row["theta_deg"]) - theta) < 1e-6
        and row["baseline"] == baseline
        and abs(float(row["linear_pol_deg"]) - pol) < 1e-6
        and row["valid"]
    ]
    return sorted(selected, key=lambda row: float(row["phi_deg"]))


def plot_phase_panel(curve_rows: list[dict[str, Any]], cases: list[workstate.SwitchCase]) -> Path:
    configure_font()
    PLOTS_DIR.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(len(cases), len(PLOT_BASELINES), figsize=(14.0, 8.0), sharex=True)
    fig.suptitle(f"D44 当前天线方位-PDOA相位对比，Theta={PLOT_THETA_DEG:.0f} deg，Freq={FREQ_GHZ:.1f} GHz", fontsize=15, fontweight="bold")
    for r, case in enumerate(cases):
        for c, (left, right) in enumerate(PLOT_BASELINES):
            ax = axes[r][c] if len(cases) > 1 else axes[c]
            baseline = f"{left}-{right}"
            for pol in POLARIZATIONS_DEG:
                curve = select_curve(curve_rows, case.name, PLOT_THETA_DEG, baseline, pol)
                phi = [row["phi_deg"] for row in curve]
                ax.plot(phi, [row["pdoa_unwrapped_deg"] for row in curve], color=COLORS[pol], linewidth=1.6, label=f"{pol:.0f}deg")
            ax.set_title(f"{case.name} / {baseline}")
            ax.set_ylabel("展开PDOA相位 / deg")
            ax.grid(True, alpha=0.28)
            if r == len(cases) - 1:
                ax.set_xlabel("方位 Phi / deg")
            if r == 0 and c == 0:
                ax.legend(title="入射线极化", ncol=2)
    fig.tight_layout(rect=[0, 0.02, 1, 0.94])
    out = PLOTS_DIR / f"{STEM}_azimuth_phase_comparison_panel.png"
    fig.savefig(out, dpi=180)
    plt.close(fig)
    return out


def plot_error_panel(curve_rows: list[dict[str, Any]], cases: list[workstate.SwitchCase]) -> Path:
    configure_font()
    PLOTS_DIR.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(len(cases), len(PLOT_BASELINES), figsize=(14.0, 8.0), sharex=True, sharey=True)
    fig.suptitle(f"D44 当前天线极化相位误差，相对0deg极化，Theta={PLOT_THETA_DEG:.0f} deg，Freq={FREQ_GHZ:.1f} GHz", fontsize=15, fontweight="bold")
    for r, case in enumerate(cases):
        for c, (left, right) in enumerate(PLOT_BASELINES):
            ax = axes[r][c] if len(cases) > 1 else axes[c]
            baseline = f"{left}-{right}"
            for pol in POLARIZATIONS_DEG:
                curve = select_curve(curve_rows, case.name, PLOT_THETA_DEG, baseline, pol)
                phi = [row["phi_deg"] for row in curve]
                ax.plot(phi, [row["phase_error_vs_pol0_deg"] for row in curve], color=COLORS[pol], linewidth=1.5, label=f"{pol:.0f}deg")
            ax.axhline(0.0, color="#333333", linewidth=0.8, alpha=0.7)
            ax.set_title(f"{case.name} / {baseline}")
            ax.set_ylabel("相对0deg相位误差 / deg")
            ax.set_ylim(-185.0, 185.0)
            ax.grid(True, alpha=0.28)
            if r == len(cases) - 1:
                ax.set_xlabel("方位 Phi / deg")
            if r == 0 and c == 0:
                ax.legend(title="入射线极化", ncol=2)
    fig.tight_layout(rect=[0, 0.02, 1, 0.94])
    out = PLOTS_DIR / f"{STEM}_azimuth_phase_error_panel.png"
    fig.savefig(out, dpi=180)
    plt.close(fig)
    return out


def write_report(metrics: dict[str, Any], phase_plot: Path, error_plot: Path) -> None:
    aggregate_rows = metrics["polarization_aggregate"]
    lines = [
        "# D44 当前天线不同极化角度相位误差复核",
        "",
        "## 口径",
        "",
        "- 当前天线：candidate 37 `fold0p6_neck1p6_stub2p6`，true-fed L 低仰角覆盖单元已保留；相位复核使用 A_ON/B_ON 两个 absorptive 50 ohm 工作态的 A/B 四阵元通道。",
        "- 避开 AEDT/PyAEDT 源切换接口：每个 A/B 端口单独重建工程，只保留一个真实端口，其余 A/B/L 源同位置端接，再导出复数远场。",
        "- 极化角：入射线极化 `0 / 45 / 90 / 135 deg`；误差定义为同一工作态、Theta、基线、方位下，相对 `0 deg` 极化的 PDOA 相位偏差。",
        f"- 方位-相位曲线图固定 `Theta={PLOT_THETA_DEG:.0f} deg`、`Freq={FREQ_GHZ:.1f} GHz`，横轴为方位 `Phi 0..360 deg`。",
        "- AEDT native Rectangular Plot 导出中角度列按球面采样自动校正：本次远场球面为 `Theta 0..90 deg / Phi 0..360 deg`。",
        "",
        "## 按极化角汇总",
        "",
        "| 工作态 | 极化角 | 曲线数 | 平均RMS相位误差 | P95 RMS相位误差 | 最大相位误差 | 平均折算方位RMS | P95折算方位RMS | 最大折算方位误差 |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in aggregate_rows:
        lines.append(
            f"| `{row['case']}` | {fmt(row['linear_pol_deg'], 0)} deg | {int(row['curve_count'])} | "
            f"{fmt(row['phase_error_rms_avg_deg'])} deg | {fmt(row['phase_error_rms_p95_deg'])} deg | "
            f"{fmt(row['phase_error_max_abs_deg'])} deg | {fmt(row['azimuth_error_rms_avg_equiv_deg'])} deg | "
            f"{fmt(row['azimuth_error_rms_p95_equiv_deg'])} deg | {fmt(row['azimuth_error_max_abs_equiv_deg'])} deg |"
        )
    xpd_aggregate_rows = metrics.get("xpd_aggregate", [])
    if xpd_aggregate_rows:
        lines.extend(
            [
                "",
                "## 交叉极化抑制比目标",
                "",
                f"- 目标：Theta `{THETA_MIN_DEG:.0f}..{THETA_MAX_DEG:.0f} deg` 内，按 `{XPD_CO_POL_DEG:.0f} deg/Etheta` 为主极化、`{XPD_CROSS_POL_DEG:.0f} deg/Ephi` 为交叉极化，最小 XPD 需 `>= {XPD_TARGET_DB:.1f} dB`。",
                "- 定义：`XPD = 20log10(|Eco|/|Ecross|)`；当前统计按逐源复数远场计算。",
                "",
                "| 范围 | 样本数 | 最小XPD | P5 XPD | 中位XPD | 平均XPD | 最差Theta | 最差Phi | 是否达标 |",
                "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
            ]
        )
        for row in xpd_aggregate_rows:
            lines.append(
                f"| `{row['case']}` | {int(row['xpd_sample_count'])} | {fmt(row['xpd_min_db'])} dB | "
                f"{fmt(row['xpd_p5_db'])} dB | {fmt(row['xpd_median_db'])} dB | {fmt(row['xpd_avg_db'])} dB | "
                f"{fmt(row.get('xpd_worst_theta_deg', float('nan')), 0)} deg | "
                f"{fmt(row.get('xpd_worst_phi_deg', float('nan')), 0)} deg | "
                f"{'是' if row['xpd_target_pass'] else '否'} |"
            )
    worst_phase = max(aggregate_rows, key=lambda row: row["phase_error_max_abs_deg"])
    worst_az = max(aggregate_rows, key=lambda row: row["azimuth_error_max_abs_equiv_deg"])
    lines.extend(
        [
            "",
            "## 结论",
            "",
            f"- 相对 `0 deg` 极化，最大相位偏差来自 `{worst_phase['case']}` / `{fmt(worst_phase['linear_pol_deg'], 0)} deg` 极化，最大绝对相位误差 `{fmt(worst_phase['phase_error_max_abs_deg'])} deg`。",
            f"- 按局部参考曲线斜率折算，最大方位误差来自 `{worst_az['case']}` / `{fmt(worst_az['linear_pol_deg'], 0)} deg` 极化，最大折算方位误差 `{fmt(worst_az['azimuth_error_max_abs_equiv_deg'])} deg`。斜率接近零的方位点不参与折算方位误差统计。",
            "- `90 deg` 极化在 A_ON/B_ON 中最敏感，说明当前 A/B 单极化通道仍需要按极化角做相位 LUT 标定；增益覆盖达标不等同于任意极化下相位曲线天然重合。",
            "",
            "## 输出图",
            "",
            f"- 方位-PDOA相位对比图：`{phase_plot}`",
            f"- 方位-相位误差图：`{error_plot}`",
            "",
            "## 输出数据",
            "",
            f"- 曲线 CSV：`{CURVES_CSV}`",
            f"- 极化误差汇总 CSV：`{SUMMARY_CSV}`",
            f"- 极化误差聚合 CSV：`{AGGREGATE_CSV}`",
            f"- XPD 目标统计 CSV：`{XPD_SUMMARY_CSV}`",
            f"- 指标 JSON：`{METRICS_JSON}`",
            f"- 字段导出清单：`{FIELDS_MANIFEST_CSV}`",
        ]
    )
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run(cores: int, tasks: int, resume: bool, restore_project: bool) -> dict[str, Any]:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    FIELD_DIR.mkdir(parents=True, exist_ok=True)
    candidate = truefed_check.truefed_candidate(37)
    cases = [workstate.CASES[0], workstate.CASES[1]]
    manifest_rows: list[dict[str, Any]] = []
    all_curve_rows: list[dict[str, Any]] = []
    all_summary_rows: list[dict[str, Any]] = []
    all_xpd_summary_rows: list[dict[str, Any]] = []
    all_xpd_sample_rows: list[dict[str, Any]] = []
    started = time.time()

    try:
        for case in cases:
            fields_by_source: dict[str, dict[tuple[float, float], FieldPoint]] = {}
            for source in selectable_sources(case):
                slug = safe_slug(f"{case.name}_{source}_field")
                paths = native_paths(slug)
                source_started = time.time()
                if not (resume and paths["field"].exists() and paths["sources"].exists()):
                    print(f"=== Field export {case.name} {source} ===", flush=True)
                    build_single_source_project(candidate, case, source, cores, tasks)
                    paths = native_export_fields(slug)
                else:
                    print(f"=== Reusing field export {case.name} {source} ===", flush=True)
                exported_sources = read_sources(paths["sources"])
                if exported_sources != [source]:
                    raise RuntimeError(f"Expected only source {source} in {paths['sources']}, got {exported_sources}")
                fields_by_source[source] = parse_field_csv(paths["field"])
                manifest_rows.append(
                    {
                        "case": case.name,
                        "active_pol": case.active_pol,
                        "source": source,
                        "field_csv": str(paths["field"]),
                        "sources_txt": str(paths["sources"]),
                        "export_log": str(paths["log"]),
                        "elapsed_s": time.time() - source_started,
                    }
                )
                write_csv(FIELDS_MANIFEST_CSV, manifest_rows)
            curve_rows, summary_rows = evaluate_case(case, fields_by_source)
            xpd_summary_rows, xpd_sample_rows = evaluate_xpd_case(case, fields_by_source)
            all_curve_rows.extend(curve_rows)
            all_summary_rows.extend(summary_rows)
            all_xpd_summary_rows.extend(xpd_summary_rows)
            all_xpd_sample_rows.extend(xpd_sample_rows)
            write_csv(CURVES_CSV, all_curve_rows)
            write_csv(SUMMARY_CSV, all_summary_rows)
            write_csv(XPD_SUMMARY_CSV, all_xpd_summary_rows)
    finally:
        if restore_project:
            print("=== Restoring full B_ON project ===", flush=True)
            restore_full_project(candidate, cases[1])

    aggregate_rows = aggregate_summary(all_summary_rows)
    xpd_aggregate_rows = aggregate_xpd_samples(all_xpd_sample_rows)
    write_csv(SUMMARY_CSV, all_summary_rows)
    write_csv(AGGREGATE_CSV, aggregate_rows)
    write_csv(XPD_SUMMARY_CSV, all_xpd_summary_rows + xpd_aggregate_rows)
    phase_plot = plot_phase_panel(all_curve_rows, cases)
    error_plot = plot_error_panel(all_curve_rows, cases)
    metrics = {
        "candidate_index": 37,
        "candidate": candidate.name,
        "freq_ghz": FREQ_GHZ,
        "theta_cuts_deg": THETA_CUTS_DEG,
        "plot_theta_deg": PLOT_THETA_DEG,
        "polarizations_deg": POLARIZATIONS_DEG,
        "phase_error_reference_pol_deg": 0.0,
        "azimuth_error_slope_floor_deg_per_deg": AZ_ERROR_SLOPE_FLOOR,
        "xpd_target_db": XPD_TARGET_DB,
        "xpd_co_pol_deg": XPD_CO_POL_DEG,
        "xpd_cross_pol_deg": XPD_CROSS_POL_DEG,
        "elapsed_s": time.time() - started,
        "polarization_aggregate": aggregate_rows,
        "xpd_summary": all_xpd_summary_rows,
        "xpd_aggregate": xpd_aggregate_rows,
        "phase_plot": str(phase_plot),
        "error_plot": str(error_plot),
        "curves_csv": str(CURVES_CSV),
        "summary_csv": str(SUMMARY_CSV),
        "aggregate_csv": str(AGGREGATE_CSV),
        "xpd_summary_csv": str(XPD_SUMMARY_CSV),
        "manifest_csv": str(FIELDS_MANIFEST_CSV),
        "report_md": str(REPORT_MD),
    }
    METRICS_JSON.write_text(json.dumps(metrics, indent=2, ensure_ascii=False), encoding="utf-8")
    write_report(metrics, phase_plot, error_plot)
    print(json.dumps({"report": str(REPORT_MD), "phase_plot": str(phase_plot), "error_plot": str(error_plot)}, indent=2, ensure_ascii=False), flush=True)
    return metrics


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cores", type=int, default=8)
    parser.add_argument("--tasks", type=int, default=8)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--no-restore-project", action="store_true")
    args = parser.parse_args()
    run(args.cores, args.tasks, args.resume, not args.no_restore_project)


if __name__ == "__main__":
    main()
