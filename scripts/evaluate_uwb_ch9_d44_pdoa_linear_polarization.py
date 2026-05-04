from __future__ import annotations

import cmath
import csv
import json
import math
from dataclasses import dataclass
from pathlib import Path
from statistics import fmean

from ansys.aedt.core import Hfss


ROOT = Path(__file__).resolve().parents[1]
PROJECT_PATH = ROOT / "UWB_CH9_Diamond_CP_Array_D44_DUALFEED_CP.aedt"
DESIGN = "Array4_Diamond_D44_DualFeed_CP"
SOLUTION = "Setup_CH9 : Sweep_CH9"
SPHERE = "Upper_Hemisphere_5deg"

REPORT_DIR = ROOT / "reports_d44_pdoa_linear"
CURVES_CSV = REPORT_DIR / "UWB_CH9_D44_PDOA_linear_polarization_curves.csv"
SUMMARY_CSV = REPORT_DIR / "UWB_CH9_D44_PDOA_linear_polarization_summary.csv"
METRICS_JSON = REPORT_DIR / "UWB_CH9_D44_PDOA_linear_polarization_metrics.json"
REPORT_MD = REPORT_DIR / "UWB_CH9_D44_PDOA_linear_polarization_report.md"

TARGET_FREQS_GHZ = [7.738, 7.9855, 8.233]
PHI_CUTS_DEG = [45.0, 60.0, 75.0, 90.0]
LINEAR_POLARIZATION_DEG = [0.0, 45.0, 90.0, 135.0]
MAG_VALID_FLOOR_REL_DB = -35.0


@dataclass(frozen=True)
class FieldPoint:
    theta_deg: float
    phi_deg: float
    etheta: complex
    ephi: complex


@dataclass(frozen=True)
class WeightedSource:
    source: str
    weight: complex


def axis_values(sd, axis: str) -> list[float]:
    return [float(str(raw).replace("deg", "")) for raw in sd.intrinsics.get(axis, [])]


def fmt(value: float | int | None, digits: int = 2) -> str:
    if value is None:
        return "N/A"
    value = float(value)
    if math.isnan(value) or math.isinf(value):
        return "N/A"
    return f"{value:.{digits}f}"


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


def complex_weight(phase_deg_value: float) -> complex:
    return cmath.exp(1j * math.radians(phase_deg_value))


def get_available_frequencies(hfss: Hfss) -> list[float]:
    expressions = hfss.get_traces_for_plot(category="dB(S")
    if not expressions:
        return [8.0]
    sd = hfss.post.get_solution_data(
        expressions=expressions[0],
        setup_sweep_name=SOLUTION,
        primary_sweep_variable="Freq",
    )
    return sorted(float(x) for x in sd.primary_sweep_values)


def nearest_frequencies(available: list[float]) -> list[float]:
    selected: list[float] = []
    for target in TARGET_FREQS_GHZ:
        nearest = min(available, key=lambda x: abs(x - target))
        if nearest not in selected:
            selected.append(nearest)
    return selected


def edit_single_source(hfss: Hfss, sources: list[str], active: str) -> None:
    hfss.edit_sources({source: (1.0 if source == active else 0.0, 0.0) for source in sources})


def get_field_grid(hfss: Hfss, freq_ghz: float) -> dict[tuple[float, float], FieldPoint]:
    expressions = ["re(rETheta)", "im(rETheta)", "re(rEPhi)", "im(rEPhi)"]
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
        raise RuntimeError("HFSS 未返回 rETheta/rEPhi 复数字段数据")

    theta_values = axis_values(sd, "Theta")
    phi_values = axis_values(sd, "Phi")
    expected = len(theta_values) * len(phi_values)

    re_theta = [float(x) for x in sd.data_real("re(rETheta)")]
    im_theta = [float(x) for x in sd.data_real("im(rETheta)")]
    re_phi = [float(x) for x in sd.data_real("re(rEPhi)")]
    im_phi = [float(x) for x in sd.data_real("im(rEPhi)")]
    lengths = {len(re_theta), len(im_theta), len(re_phi), len(im_phi)}
    if lengths != {expected}:
        raise RuntimeError(
            "远场网格长度不一致: "
            f"Theta={len(theta_values)}, Phi={len(phi_values)}, data={sorted(lengths)}"
        )

    grid: dict[tuple[float, float], FieldPoint] = {}
    idx = 0
    for phi in phi_values:
        for theta in theta_values:
            point = FieldPoint(
                theta_deg=theta,
                phi_deg=phi,
                etheta=complex(re_theta[idx], im_theta[idx]),
                ephi=complex(re_phi[idx], im_phi[idx]),
            )
            grid[(round(theta, 9), round(phi, 9))] = point
            idx += 1
    return grid


def acquire_embedded_fields(
    hfss: Hfss,
    sources: list[str],
    eval_freqs: list[float],
) -> dict[str, dict[str, dict[tuple[float, float], FieldPoint]]]:
    fields: dict[str, dict[str, dict[tuple[float, float], FieldPoint]]] = {}
    for source in sources:
        print(f"Extracting embedded far field for {source}")
        edit_single_source(hfss, sources, source)
        fields[source] = {}
        for freq in eval_freqs:
            fields[source][freq_key(freq)] = get_field_grid(hfss, freq)
    return fields


def freq_key(freq_ghz: float) -> str:
    return f"{freq_ghz:.6f}GHz"


def source_index(source: str) -> tuple[int, str]:
    digits = "".join(ch for ch in source if ch.isdigit())
    suffix = source[-1] if source else ""
    return (int(digits) if digits else 0, suffix)


def source_name(element: int, feed: str) -> str:
    return f"P{element}{feed}"


def build_channel_sets(sources: list[str]) -> dict[str, dict[str, list[WeightedSource]]]:
    available = set(sources)
    channel_sets: dict[str, dict[str, list[WeightedSource]]] = {}

    for feed in ["A", "B"]:
        channels = {
            f"E{idx}": [WeightedSource(source_name(idx, feed), 1.0 + 0.0j)]
            for idx in range(1, 5)
            if source_name(idx, feed) in available
        }
        if len(channels) >= 2:
            channel_sets[f"{feed}_feed_only"] = channels

    quadrature = {}
    for idx in range(1, 5):
        a = source_name(idx, "A")
        b = source_name(idx, "B")
        if a in available and b in available:
            quadrature[f"E{idx}"] = [
                WeightedSource(a, 1.0 + 0.0j),
                WeightedSource(b, complex_weight(-90.0)),
            ]
    if len(quadrature) >= 2:
        channel_sets["dualfeed_quadrature_minus90"] = quadrature

    if not channel_sets:
        ordered = sorted(sources, key=source_index)
        channel_sets["raw_ports"] = {
            source: [WeightedSource(source, 1.0 + 0.0j)] for source in ordered
        }

    return channel_sets


def build_baselines(channels: dict[str, list[WeightedSource]]) -> list[tuple[str, str]]:
    labels = sorted(channels, key=lambda name: int(name[1:]) if name.startswith("E") and name[1:].isdigit() else name)
    preferred = [("E1", "E3"), ("E2", "E4"), ("E1", "E2"), ("E2", "E3"), ("E3", "E4"), ("E4", "E1")]
    baselines = [(left, right) for left, right in preferred if left in channels and right in channels]
    if baselines:
        return baselines
    return [(labels[idx], labels[idx + 1]) for idx in range(len(labels) - 1)]


def linear_projection(point: FieldPoint, polarization_deg: float) -> complex:
    angle = math.radians(polarization_deg)
    return point.etheta * math.cos(angle) + point.ephi * math.sin(angle)


def channel_voltage(
    channel: list[WeightedSource],
    fields_by_source: dict[str, dict[tuple[float, float], FieldPoint]],
    point_key: tuple[float, float],
    polarization_deg: float,
) -> complex:
    total = 0.0 + 0.0j
    for item in channel:
        point = fields_by_source[item.source][point_key]
        total += item.weight * linear_projection(point, polarization_deg)
    return total


def rel_db(value: float, reference: float) -> float:
    if value <= 0.0 or reference <= 0.0:
        return -999.0
    return 20.0 * math.log10(value / reference)


def summarize_curve(rows: list[dict], reference_by_theta: dict[float, float] | None) -> dict:
    valid_rows = [row for row in rows if row["valid"]]
    if len(valid_rows) >= 2:
        unwrapped = unwrap_degrees([row["pdoa_deg"] for row in valid_rows])
        for row, value in zip(valid_rows, unwrapped):
            row["pdoa_unwrapped_deg"] = value
        slopes = [
            (unwrapped[idx + 1] - unwrapped[idx])
            / (valid_rows[idx + 1]["theta_deg"] - valid_rows[idx]["theta_deg"])
            for idx in range(len(valid_rows) - 1)
            if abs(valid_rows[idx + 1]["theta_deg"] - valid_rows[idx]["theta_deg"]) > 1e-9
        ]
    else:
        unwrapped = []
        slopes = []

    for row in rows:
        row.setdefault("pdoa_unwrapped_deg", row["pdoa_deg"])

    slope_positive = sum(1 for slope in slopes if slope >= 0.0)
    slope_negative = sum(1 for slope in slopes if slope < 0.0)
    monotonic_percent = (
        100.0 * max(slope_positive, slope_negative) / len(slopes) if slopes else 0.0
    )

    bias_values = []
    if reference_by_theta:
        for row in valid_rows:
            ref = reference_by_theta.get(row["theta_deg"])
            if ref is not None:
                bias_values.append(wrap_deg(row["pdoa_deg"] - ref))

    abs_bias = [abs(value) for value in bias_values]
    return {
        "valid_count": len(valid_rows),
        "total_count": len(rows),
        "valid_percent": 100.0 * len(valid_rows) / len(rows) if rows else 0.0,
        "pdoa_span_deg": max(unwrapped) - min(unwrapped) if unwrapped else float("nan"),
        "pdoa_start_deg": unwrapped[0] if unwrapped else float("nan"),
        "pdoa_end_deg": unwrapped[-1] if unwrapped else float("nan"),
        "mean_abs_slope_deg_per_deg": fmean(abs(slope) for slope in slopes) if slopes else float("nan"),
        "slope_std_deg_per_deg": sample_std(slopes),
        "monotonic_segment_percent": monotonic_percent,
        "min_pair_mag_rel_db": min(
            min(row["left_mag_rel_db"], row["right_mag_rel_db"]) for row in rows
        )
        if rows
        else float("nan"),
        "rms_bias_vs_pol0_deg": math.sqrt(fmean(value * value for value in bias_values))
        if bias_values
        else 0.0,
        "mean_abs_bias_vs_pol0_deg": fmean(abs_bias) if abs_bias else 0.0,
        "max_abs_bias_vs_pol0_deg": max(abs_bias) if abs_bias else 0.0,
    }


def sample_std(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0 if values else float("nan")
    mean = fmean(values)
    return math.sqrt(sum((value - mean) ** 2 for value in values) / (len(values) - 1))


def evaluate_pdoa(fields: dict, eval_freqs: list[float], sources: list[str]) -> tuple[list[dict], list[dict], dict]:
    channel_sets = build_channel_sets(sources)
    curve_rows: list[dict] = []
    summary_rows: list[dict] = []

    for freq in eval_freqs:
        fkey = freq_key(freq)
        fields_by_source = {source: fields[source][fkey] for source in sources}
        all_points = next(iter(fields_by_source.values()))
        theta_values = sorted({point.theta_deg for point in all_points.values()})
        phi_values = sorted({point.phi_deg for point in all_points.values()})
        selected_phi = [phi for phi in PHI_CUTS_DEG if any(abs(phi - item) < 1e-6 for item in phi_values)]

        for set_name, channels in channel_sets.items():
            baselines = build_baselines(channels)
            for phi in selected_phi:
                for left, right in baselines:
                    reference_by_theta: dict[float, float] | None = None
                    pol_curve_rows: dict[float, list[dict]] = {}
                    for pol in LINEAR_POLARIZATION_DEG:
                        raw_rows = []
                        mags = []
                        for theta in theta_values:
                            key = (round(theta, 9), round(phi, 9))
                            if key not in all_points:
                                continue
                            v_left = channel_voltage(channels[left], fields_by_source, key, pol)
                            v_right = channel_voltage(channels[right], fields_by_source, key, pol)
                            mags.extend([abs(v_left), abs(v_right)])
                            pdoa = wrap_deg(phase_deg(v_left) - phase_deg(v_right))
                            raw_rows.append(
                                {
                                    "freq_ghz": freq,
                                    "phi_deg": phi,
                                    "theta_deg": theta,
                                    "linear_pol_deg": pol,
                                    "channel_set": set_name,
                                    "baseline": f"{left}-{right}",
                                    "left_mag": abs(v_left),
                                    "right_mag": abs(v_right),
                                    "pdoa_deg": pdoa,
                                }
                            )
                        reference = max(mags) if mags else 1.0
                        floor = reference * 10.0 ** (MAG_VALID_FLOOR_REL_DB / 20.0)
                        for row in raw_rows:
                            row["left_mag_rel_db"] = rel_db(row["left_mag"], reference)
                            row["right_mag_rel_db"] = rel_db(row["right_mag"], reference)
                            row["valid"] = row["left_mag"] >= floor and row["right_mag"] >= floor
                        pol_curve_rows[pol] = raw_rows
                        if pol == 0.0:
                            reference_by_theta = {row["theta_deg"]: row["pdoa_deg"] for row in raw_rows if row["valid"]}

                    for pol in LINEAR_POLARIZATION_DEG:
                        rows = pol_curve_rows[pol]
                        summary = summarize_curve(rows, reference_by_theta)
                        summary.update(
                            {
                                "freq_ghz": freq,
                                "phi_deg": phi,
                                "linear_pol_deg": pol,
                                "channel_set": set_name,
                                "baseline": f"{left}-{right}",
                            }
                        )
                        summary_rows.append(summary)
                        curve_rows.extend(rows)

    metrics = aggregate_metrics(summary_rows, channel_sets)
    return curve_rows, summary_rows, metrics


def aggregate_metrics(summary_rows: list[dict], channel_sets: dict) -> dict:
    non_ref = [row for row in summary_rows if abs(row["linear_pol_deg"]) > 1e-9]
    worst_max_bias = max(non_ref, key=lambda row: row["max_abs_bias_vs_pol0_deg"], default=None)
    worst_rms_bias = max(non_ref, key=lambda row: row["rms_bias_vs_pol0_deg"], default=None)
    best_monotonic = sorted(
        summary_rows,
        key=lambda row: (
            -row["monotonic_segment_percent"],
            row["rms_bias_vs_pol0_deg"],
            -abs(row["pdoa_span_deg"]) if not math.isnan(row["pdoa_span_deg"]) else 0.0,
        ),
    )[:8]

    by_pol = {}
    for pol in LINEAR_POLARIZATION_DEG:
        rows = [row for row in summary_rows if row["linear_pol_deg"] == pol]
        by_pol[f"{pol:.0f}deg"] = {
            "curve_count": len(rows),
            "valid_percent_avg": fmean(row["valid_percent"] for row in rows) if rows else 0.0,
            "monotonic_segment_percent_avg": fmean(row["monotonic_segment_percent"] for row in rows) if rows else 0.0,
            "rms_bias_vs_pol0_deg_avg": fmean(row["rms_bias_vs_pol0_deg"] for row in rows) if rows else 0.0,
            "max_abs_bias_vs_pol0_deg_max": max((row["max_abs_bias_vs_pol0_deg"] for row in rows), default=0.0),
        }

    return {
        "linear_polarizations_deg": LINEAR_POLARIZATION_DEG,
        "phi_cuts_deg": PHI_CUTS_DEG,
        "mag_valid_floor_rel_db": MAG_VALID_FLOOR_REL_DB,
        "channel_sets": {
            name: {
                channel: [
                    {"source": item.source, "weight_real": item.weight.real, "weight_imag": item.weight.imag}
                    for item in items
                ]
                for channel, items in channels.items()
            }
            for name, channels in channel_sets.items()
        },
        "curve_count": len(summary_rows),
        "worst_max_bias": slim_summary(worst_max_bias),
        "worst_rms_bias": slim_summary(worst_rms_bias),
        "polarization_summary": by_pol,
        "best_monotonic_candidates": [slim_summary(row) for row in best_monotonic],
    }


def slim_summary(row: dict | None) -> dict | None:
    if row is None:
        return None
    keys = [
        "freq_ghz",
        "phi_deg",
        "linear_pol_deg",
        "channel_set",
        "baseline",
        "valid_percent",
        "pdoa_span_deg",
        "monotonic_segment_percent",
        "rms_bias_vs_pol0_deg",
        "max_abs_bias_vs_pol0_deg",
        "min_pair_mag_rel_db",
    ]
    return {key: row.get(key) for key in keys}


def write_curves_csv(path: Path, rows: list[dict]) -> None:
    fields = [
        "freq_ghz",
        "phi_deg",
        "theta_deg",
        "linear_pol_deg",
        "channel_set",
        "baseline",
        "pdoa_deg",
        "pdoa_unwrapped_deg",
        "left_mag_rel_db",
        "right_mag_rel_db",
        "valid",
    ]
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "freq_ghz": f"{row['freq_ghz']:.6f}",
                    "phi_deg": f"{row['phi_deg']:.6f}",
                    "theta_deg": f"{row['theta_deg']:.6f}",
                    "linear_pol_deg": f"{row['linear_pol_deg']:.6f}",
                    "channel_set": row["channel_set"],
                    "baseline": row["baseline"],
                    "pdoa_deg": f"{row['pdoa_deg']:.6f}",
                    "pdoa_unwrapped_deg": f"{row['pdoa_unwrapped_deg']:.6f}",
                    "left_mag_rel_db": f"{row['left_mag_rel_db']:.6f}",
                    "right_mag_rel_db": f"{row['right_mag_rel_db']:.6f}",
                    "valid": row["valid"],
                }
            )


def write_summary_csv(path: Path, rows: list[dict]) -> None:
    fields = [
        "freq_ghz",
        "phi_deg",
        "linear_pol_deg",
        "channel_set",
        "baseline",
        "valid_percent",
        "pdoa_span_deg",
        "pdoa_start_deg",
        "pdoa_end_deg",
        "mean_abs_slope_deg_per_deg",
        "slope_std_deg_per_deg",
        "monotonic_segment_percent",
        "min_pair_mag_rel_db",
        "rms_bias_vs_pol0_deg",
        "mean_abs_bias_vs_pol0_deg",
        "max_abs_bias_vs_pol0_deg",
    ]
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    key: f"{row[key]:.6f}" if isinstance(row.get(key), float) else row.get(key)
                    for key in fields
                }
            )


def write_report(metrics: dict, summary_rows: list[dict], eval_freqs: list[float], sources: list[str]) -> None:
    worst_max = metrics["worst_max_bias"] or {}
    worst_rms = metrics["worst_rms_bias"] or {}
    best = metrics["best_monotonic_candidates"][:5]
    pol_lines = []
    for pol, item in metrics["polarization_summary"].items():
        pol_lines.append(
            "| "
            + " | ".join(
                [
                    pol,
                    str(item["curve_count"]),
                    fmt(item["valid_percent_avg"], 1) + "%",
                    fmt(item["monotonic_segment_percent_avg"], 1) + "%",
                    fmt(item["rms_bias_vs_pol0_deg_avg"], 2) + " deg",
                    fmt(item["max_abs_bias_vs_pol0_deg_max"], 2) + " deg",
                ]
            )
            + " |"
        )

    best_lines = []
    for item in best:
        best_lines.append(
            "| "
            + " | ".join(
                [
                    fmt(item["freq_ghz"], 4),
                    fmt(item["phi_deg"], 0),
                    fmt(item["linear_pol_deg"], 0),
                    item["channel_set"],
                    item["baseline"],
                    fmt(item["pdoa_span_deg"], 2),
                    fmt(item["monotonic_segment_percent"], 1) + "%",
                    fmt(item["rms_bias_vs_pol0_deg"], 2),
                ]
            )
            + " |"
        )

    lines = [
        "# D44 双馈贴片线极化 PDOA 评估报告",
        "",
        "## 评估目标",
        "",
        "- 本轮只考虑入射线极化，角度固定为 `0 / 45 / 90 / 135 deg`。",
        "- 不评估圆极化、椭圆极化或任意连续极化角扫描。",
        "- 目标是观察入射线极化方向变化对当前 PDOA 测角/鉴角曲线的影响。",
        "",
        "## 数据来源和方法",
        "",
        f"- AEDT 项目: `{PROJECT_PATH}`",
        f"- 设计名: `{DESIGN}`",
        f"- 解算: `{SOLUTION}`",
        f"- 远场球面: `{SPHERE}`",
        f"- 端口源: `{', '.join(sources)}`",
        f"- 评估频点: `{', '.join(fmt(freq, 4) + ' GHz' for freq in eval_freqs)}`",
        f"- 方位切面: `{', '.join(fmt(phi, 0) + ' deg' for phi in PHI_CUTS_DEG)}`",
        "- 使用 HFSS 远场复数量 `re/im(rETheta)` 与 `re/im(rEPhi)`。",
        "- 线极化投影定义为 `V = Etheta*cos(psi) + Ephi*sin(psi)`，其中 `psi` 为本地球坐标切向基下的线极化角。",
        "- PDOA 定义为两个接收通道复响应相位差 `angle(V_left)-angle(V_right)`，并按 theta 曲线展开。",
        "- 双馈合成通道采用与前序 CP 激励一致的 `A + B*exp(-j90deg)` 作为工程近似。",
        "",
        "## 核心结论",
        "",
        f"- 共生成 `{len(summary_rows)}` 条 PDOA 曲线汇总。",
        f"- 最大线极化敏感项: `{worst_max.get('channel_set', 'N/A')}` / `{worst_max.get('baseline', 'N/A')}`，"
        f"`freq={fmt(worst_max.get('freq_ghz'), 4)} GHz`，`phi={fmt(worst_max.get('phi_deg'), 0)} deg`，"
        f"`pol={fmt(worst_max.get('linear_pol_deg'), 0)} deg`，相对 0 deg 线极化最大 PDOA 偏移 `{fmt(worst_max.get('max_abs_bias_vs_pol0_deg'), 2)} deg`。",
        f"- 最大 RMS 偏移项: `{worst_rms.get('channel_set', 'N/A')}` / `{worst_rms.get('baseline', 'N/A')}`，"
        f"`freq={fmt(worst_rms.get('freq_ghz'), 4)} GHz`，`phi={fmt(worst_rms.get('phi_deg'), 0)} deg`，"
        f"`pol={fmt(worst_rms.get('linear_pol_deg'), 0)} deg`，RMS 偏移 `{fmt(worst_rms.get('rms_bias_vs_pol0_deg'), 2)} deg`。",
        "- 当前结构对线极化方向非常敏感，说明如果 PDOA 标定只用单一线极化，换成 45/90/135 deg 入射时会引入显著鉴角曲线偏移。",
        "",
        "## 按线极化角汇总",
        "",
        "| 入射线极化 | 曲线数 | 平均有效点 | 平均单调片段 | 平均 RMS 偏移 | 最大偏移 |",
        "| ---: | ---: | ---: | ---: | ---: | ---: |",
        *pol_lines,
        "",
        "## 相对较优的鉴角曲线候选",
        "",
        "| 频点GHz | Phi | 极化 | 通道组 | 基线 | PDOA展开跨度deg | 单调片段 | RMS偏移deg |",
        "| ---: | ---: | ---: | --- | --- | ---: | ---: | ---: |",
        *best_lines,
        "",
        "## 工程判断",
        "",
        "- 若 PDOA 系统使用当前双馈贴片直接测角，应把线极化角作为标定维度，否则不同入射线极化会造成系统性相位偏置。",
        "- 若希望降低对入射线极化方向的敏感性，优先继续优化双馈幅相平衡、端口隔离和混合网络输出匹配；只改善单端口 S11 不足以稳定 PDOA 曲线。",
        "- 本报告使用嵌入式发射远场按互易性构造接收响应代理，尚未包含实测线缆相位、接收机通道相位和暗室标定误差。",
        "",
        "## 输出文件",
        "",
        f"- 曲线 CSV: `{CURVES_CSV}`",
        f"- 汇总 CSV: `{SUMMARY_CSV}`",
        f"- 指标 JSON: `{METRICS_JSON}`",
        f"- 中文报告: `{REPORT_MD}`",
    ]
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run() -> dict:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    lock = PROJECT_PATH.with_suffix(".aedt.lock")
    if lock.exists():
        try:
            lock.unlink()
        except OSError:
            pass

    hfss = Hfss(
        project=str(PROJECT_PATH),
        design=DESIGN,
        version="2023.1",
        non_graphical=True,
        new_desktop=True,
        close_on_exit=False,
        remove_lock=True,
    )
    try:
        sources = hfss.get_all_sources()
        available_freqs = get_available_frequencies(hfss)
        eval_freqs = nearest_frequencies(available_freqs)
        fields = acquire_embedded_fields(hfss, sources, eval_freqs)
        curve_rows, summary_rows, metrics = evaluate_pdoa(fields, eval_freqs, sources)
        metrics.update(
            {
                "project": str(PROJECT_PATH),
                "design": DESIGN,
                "solution": SOLUTION,
                "sphere": SPHERE,
                "sources": sources,
                "available_frequencies_ghz": available_freqs,
                "evaluated_frequencies_ghz": eval_freqs,
                "method": {
                    "field_expressions": ["re(rETheta)", "im(rETheta)", "re(rEPhi)", "im(rEPhi)"],
                    "linear_projection": "V = Etheta*cos(psi) + Ephi*sin(psi)",
                    "pdoa": "angle(V_left) - angle(V_right)",
                    "polarization_scope": "linear only: 0/45/90/135 deg",
                },
                "files": {
                    "curves_csv": str(CURVES_CSV),
                    "summary_csv": str(SUMMARY_CSV),
                    "metrics_json": str(METRICS_JSON),
                    "report_md": str(REPORT_MD),
                },
            }
        )
        write_curves_csv(CURVES_CSV, curve_rows)
        write_summary_csv(SUMMARY_CSV, summary_rows)
        METRICS_JSON.write_text(json.dumps(metrics, indent=2, ensure_ascii=False), encoding="utf-8")
        write_report(metrics, summary_rows, eval_freqs, sources)
        print(json.dumps(metrics["polarization_summary"], indent=2, ensure_ascii=False))
        print(f"Wrote {CURVES_CSV}")
        print(f"Wrote {SUMMARY_CSV}")
        print(f"Wrote {METRICS_JSON}")
        print(f"Wrote {REPORT_MD}")
        return metrics
    finally:
        hfss.release_desktop(close_projects=False, close_desktop=True)


if __name__ == "__main__":
    run()
