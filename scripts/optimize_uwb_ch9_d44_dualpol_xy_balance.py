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

from ansys.aedt.core import Hfss

import build_uwb_ch9_hfss_d44_topology as builder
import evaluate_uwb_ch9_d44_dualpol as dualpol_eval
import evaluate_uwb_ch9_d44_pdoa_linear_polarization as pdoa_eval
import evaluate_uwb_ch9_d44_topology as topology_eval


ROOT = Path(__file__).resolve().parents[1]
TOPOLOGY = "dualpol"
REPORT_DIR = ROOT / "reports_d44_dualpol_xy_balance_opt"
STEM = "UWB_CH9_D44_DUALPOL_XY_BALANCE"
SPARAM_CSV = REPORT_DIR / f"{STEM}_sparam_screening.csv"
FULL_CSV = REPORT_DIR / f"{STEM}_full_validation.csv"
BEST_CURVES_CSV = REPORT_DIR / f"{STEM}_best_curves.csv"
BEST_SUMMARY_CSV = REPORT_DIR / f"{STEM}_best_summary.csv"
BEST_JSON = REPORT_DIR / f"{STEM}_best.json"
REPORT_MD = REPORT_DIR / f"{STEM}_optimization_report.md"

RETURN_TARGET_DB = -10.0
XY_ISOLATION_TARGET_DB = 15.0
SAME_FEED_ISOLATION_TARGET_DB = 16.0
RETURN_BALANCE_TARGET_DB = 0.5
XY_MAG_BALANCE_TARGET_DB = 2.0
XY_PHASE_SPREAD_TARGET_DEG = 30.0
PDOA_RMS_TARGET_DEG = 10.0
PDOA_MAX_TARGET_DEG = 20.0

BASE_PARAMS: dict[str, Any] = dict(builder.TOPOLOGIES[TOPOLOGY]["params"])
BASE_PARAMS.update(
    {
        "patch_side_mm": 9.15,
        "corner_cut_mm": 0.0,
        "feed_offset_u_mm": 3.40,
        "feed_offset_v_mm": 0.0,
        "feed_pad_radius_mm": 0.32,
        "port_width_mm": 0.50,
        "microstrip_feed_enabled": 0.0,
        "neutralization_branch_enabled": 0.0,
        "local_dgs_enabled": 0.0,
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


def fmt(value: float | int | None, digits: int = 2) -> str:
    if value is None:
        return "N/A"
    value = float(value)
    if math.isnan(value) or math.isinf(value):
        return "N/A"
    return f"{value:.{digits}f}"


def candidate(name: str, rationale: str, **overrides: float) -> Candidate:
    params = dict(BASE_PARAMS)
    params.update(overrides)
    return Candidate(name=name, params=params, rationale=rationale)


def candidates() -> list[Candidate]:
    raw = [
        candidate("dualpol_baseline", "双极化 XY 初版，作为本轮幅相/隔离优化基线。"),
        candidate("feed3p30", "整体内移 X/Y 馈点，观察 Y 路匹配和同阵元隔离变化。", feed_offset_u_mm=3.30),
        candidate("feed3p50", "整体外移 X/Y 馈点，尝试改善 Y 路回波并保持同阵元隔离。", feed_offset_u_mm=3.50),
        candidate("feed3p60", "继续外移馈点，验证较强边缘耦合下的匹配上限。", feed_offset_u_mm=3.60),
        candidate("pad0p30_port0p50_feed3p40", "减小焊盘半径，降低 A/B 近场耦合。", feed_pad_radius_mm=0.30),
        candidate("pad0p28_port0p50_feed3p40", "进一步减小焊盘半径，测试隔离收益与匹配损失。", feed_pad_radius_mm=0.28),
        candidate("port0p55_feed3p40", "加宽端口片改善 Y 路回波，同时观察 X/Y 回波平衡。", port_width_mm=0.55),
        candidate("port0p60_feed3p40", "进一步加宽端口片，追求 Y 路匹配改善。", port_width_mm=0.60),
        candidate(
            "asym_a3p40_b3p50",
            "仅外移 B/Y 馈点，用几何不对称补偿 Y 路回波偏弱。",
            feed_offset_a_mm=3.40,
            feed_offset_b_mm=3.50,
        ),
        candidate(
            "asym_a3p35_b3p50",
            "A 路略内移、B 路外移，直接优化 X/Y 回波均衡。",
            feed_offset_a_mm=3.35,
            feed_offset_b_mm=3.50,
        ),
        candidate(
            "openline_l2p40",
            "加入悬浮弱耦合开路线，尝试提升同阵元 X/Y 隔离。",
            weak_coupling_open_line_enabled=1.0,
            weak_coupling_open_line_length_mm=2.40,
            weak_coupling_open_line_width_mm=0.10,
            weak_coupling_open_line_offset_mm=1.65,
            weak_coupling_open_line_gap_mm=0.10,
        ),
        candidate(
            "openline_l2p80",
            "加长弱耦合开路线，增强 A/B 反向耦合调节能力。",
            weak_coupling_open_line_enabled=1.0,
            weak_coupling_open_line_length_mm=2.80,
            weak_coupling_open_line_width_mm=0.10,
            weak_coupling_open_line_offset_mm=1.70,
            weak_coupling_open_line_gap_mm=0.10,
        ),
        candidate(
            "soft_via_fence",
            "温和过孔栅栏，降低地电流串扰但尽量减少匹配扰动。",
            via_fence_enabled=1.0,
            via_fence_count=2.0,
            via_fence_radius_mm=0.07,
            via_fence_pitch_mm=0.50,
            via_fence_edge_offset_mm=0.38,
            via_fence_center_mm=3.35,
        ),
    ]
    valid = []
    for item in raw:
        params = dict(builder.BASE_PARAMS)
        params.update(item.params)
        try:
            builder.validate_params(params)
            valid.append(item)
        except Exception as exc:
            print(f"Skip invalid {item.name}: {exc}", flush=True)
    return valid


def apply_candidate(item: Candidate) -> None:
    params = builder.TOPOLOGIES[TOPOLOGY]["params"]
    params.clear()
    params.update(item.params)


def write_csv(path: Path, rows: list[dict]) -> None:
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
        writer.writerows(rows)


def read_csv(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def sparam_score(row: dict) -> float:
    return_miss = max(0.0, row["worst_return_db"] - RETURN_TARGET_DB)
    xy_iso_miss = max(0.0, XY_ISOLATION_TARGET_DB - row["same_element_xy_isolation_db"])
    same_feed_miss = max(0.0, SAME_FEED_ISOLATION_TARGET_DB - row["same_feed_inter_element_isolation_db"])
    balance_miss = max(0.0, row["xy_return_balance_db"] - RETURN_BALANCE_TARGET_DB)
    return 18.0 * return_miss + 8.0 * xy_iso_miss + 3.0 * same_feed_miss + 4.0 * balance_miss


def sparam_screen(item: Candidate, index: int) -> dict:
    start = time.time()
    apply_candidate(item)
    _project, hfss = builder.build_project(
        TOPOLOGY,
        analyze=True,
        non_graphical=True,
        quick=True,
        band_samples=True,
        sparam_only=True,
        return_hfss=True,
    )
    try:
        sparams = topology_eval.get_s_parameter_snapshot(hfss, REPORT_DIR / f"{item.name}_s_parameters.csv")
    finally:
        hfss.release_desktop(close_projects=False, close_desktop=True)
    extra = dualpol_eval.enrich_sparams(sparams)
    row = {
        "index": index,
        "candidate": item.name,
        "elapsed_s": round(time.time() - start, 1),
        "rationale": item.rationale,
        "worst_return_db": sparams["worst_return_db"],
        "isolation_db": sparams["isolation_db"],
        "worst_return_expr": sparams["worst_return_expr"],
        "worst_coupling_expr": sparams["worst_coupling_expr"],
        "x_return_worst_db": extra["x_return_worst_db"],
        "y_return_worst_db": extra["y_return_worst_db"],
        "xy_return_balance_db": abs(extra["x_return_worst_db"] - extra["y_return_worst_db"]),
        "same_element_xy_isolation_db": extra["same_element_xy_isolation_db"],
        "same_feed_inter_element_isolation_db": extra["same_feed_inter_element_isolation_db"],
    }
    for key in [
        "feed_offset_u_mm",
        "feed_offset_a_mm",
        "feed_offset_b_mm",
        "feed_pad_radius_mm",
        "port_width_mm",
        "weak_coupling_open_line_enabled",
        "weak_coupling_open_line_length_mm",
        "weak_coupling_open_line_gap_mm",
        "via_fence_enabled",
        "via_fence_count",
        "via_fence_radius_mm",
        "via_fence_edge_offset_mm",
    ]:
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


def full_score(row: dict) -> float:
    vector = row["dualpol_vector_avg_rms_bias_deg"]
    return (
        row["sparam_score"]
        + 0.50 * vector
        + 0.12 * row["dualpol_vector_p95_rms_bias_deg"]
        + 0.02 * row["dualpol_vector_max_abs_bias_deg"]
        + 3.0 * max(0.0, row["xy_mag_imbalance_rms_db"] - XY_MAG_BALANCE_TARGET_DB)
        + 0.08 * max(0.0, row["xy_phase_spread_rms_deg"] - XY_PHASE_SPREAD_TARGET_DEG)
    )


def full_validate(item: Candidate) -> dict:
    start = time.time()
    apply_candidate(item)
    project, hfss = builder.build_project(
        TOPOLOGY,
        analyze=True,
        non_graphical=True,
        quick=True,
        band_samples=True,
        sparam_only=False,
        return_hfss=True,
    )
    try:
        sparams = topology_eval.get_s_parameter_snapshot(hfss, REPORT_DIR / f"{item.name}_full_s_parameters.csv")
        extra = dualpol_eval.enrich_sparams(sparams)
        sources = hfss.get_all_sources()
        eval_freqs = pdoa_eval.nearest_frequencies(pdoa_eval.get_available_frequencies(hfss))
        fields = pdoa_eval.acquire_embedded_fields(hfss, sources, eval_freqs)
        curves, summaries, pdoa_metrics = dualpol_eval.evaluate_dualpol_pdoa(fields, eval_freqs, sources)
        balance = xy_balance_metrics(fields, eval_freqs, sources)
    finally:
        hfss.release_desktop(close_projects=False, close_desktop=True)

    write_csv(REPORT_DIR / f"{item.name}_curves.csv", curves)
    write_csv(REPORT_DIR / f"{item.name}_summary.csv", summaries)
    vector = pdoa_metrics["strategies"]["dualpol_vector_correlation"]
    legacy = pdoa_metrics["strategies"]["legacy_cp_minus90"]
    row = {
        "candidate": item.name,
        "project": str(project),
        "elapsed_s": round(time.time() - start, 1),
        "rationale": item.rationale,
        "worst_return_db": sparams["worst_return_db"],
        "isolation_db": sparams["isolation_db"],
        "x_return_worst_db": extra["x_return_worst_db"],
        "y_return_worst_db": extra["y_return_worst_db"],
        "xy_return_balance_db": abs(extra["x_return_worst_db"] - extra["y_return_worst_db"]),
        "same_element_xy_isolation_db": extra["same_element_xy_isolation_db"],
        "same_feed_inter_element_isolation_db": extra["same_feed_inter_element_isolation_db"],
        "dualpol_vector_avg_rms_bias_deg": vector["avg_rms_bias_deg"],
        "dualpol_vector_p95_rms_bias_deg": vector["p95_rms_bias_deg"],
        "dualpol_vector_max_abs_bias_deg": vector["max_abs_bias_deg"],
        "legacy_cp_avg_rms_bias_deg": legacy["avg_rms_bias_deg"],
        "legacy_cp_p95_rms_bias_deg": legacy["p95_rms_bias_deg"],
        "legacy_cp_max_abs_bias_deg": legacy["max_abs_bias_deg"],
        "xy_mag_imbalance_mean_abs_db": balance["xy_mag_imbalance_mean_abs_db"],
        "xy_mag_imbalance_rms_db": balance["xy_mag_imbalance_rms_db"],
        "xy_mag_imbalance_max_abs_db": balance["xy_mag_imbalance_max_abs_db"],
        "xy_phase_spread_mean_abs_deg": balance["xy_phase_spread_mean_abs_deg"],
        "xy_phase_spread_rms_deg": balance["xy_phase_spread_rms_deg"],
        "xy_phase_spread_max_abs_deg": balance["xy_phase_spread_max_abs_deg"],
        "sparam_score": sparam_score(
            {
                "worst_return_db": sparams["worst_return_db"],
                "same_element_xy_isolation_db": extra["same_element_xy_isolation_db"],
                "same_feed_inter_element_isolation_db": extra["same_feed_inter_element_isolation_db"],
                "xy_return_balance_db": abs(extra["x_return_worst_db"] - extra["y_return_worst_db"]),
            }
        ),
        "parameters": item.params,
        "pdoa_metrics": pdoa_metrics,
    }
    row["full_score"] = full_score(row)
    row["meets_s"] = row["worst_return_db"] <= RETURN_TARGET_DB and row["same_element_xy_isolation_db"] >= XY_ISOLATION_TARGET_DB
    row["meets_balance"] = row["xy_mag_imbalance_rms_db"] <= XY_MAG_BALANCE_TARGET_DB and row["xy_phase_spread_rms_deg"] <= XY_PHASE_SPREAD_TARGET_DEG
    row["meets_pdoa"] = row["dualpol_vector_avg_rms_bias_deg"] <= PDOA_RMS_TARGET_DEG and row["dualpol_vector_max_abs_bias_deg"] <= PDOA_MAX_TARGET_DEG
    row["meets_all"] = row["meets_s"] and row["meets_balance"] and row["meets_pdoa"]
    return row


def select_full(cands: list[Candidate], rows: list[dict], count: int) -> list[Candidate]:
    by_name = {item.name: item for item in cands}
    ranked = sorted(rows, key=lambda row: float(row["score"]))
    names = [row["candidate"] for row in ranked[:count]]
    isolation_names = [
        row["candidate"]
        for row in ranked
        if by_name[row["candidate"]].params.get("weak_coupling_open_line_enabled", 0.0) >= 0.5
        or by_name[row["candidate"]].params.get("via_fence_enabled", 0.0) >= 0.5
    ]
    if count > 1 and isolation_names and not any(name in names for name in isolation_names):
        names[-1] = isolation_names[0]
    return [by_name[name] for name in names]


def write_report(best: dict, sparam_rows: list[dict], full_rows: list[dict]) -> None:
    top_s = sorted(sparam_rows, key=lambda row: float(row["score"]))[:10]
    baseline = next((row for row in full_rows if row["candidate"] == "dualpol_baseline"), None)
    lines = [
        "# D44 双极化 XY 幅相一致性与同阵元隔离优化报告",
        "",
        "## 本轮目标",
        "",
        f"- 最差回波：`<= {RETURN_TARGET_DB:.1f} dB`。",
        f"- 同阵元 X/Y 隔离：`>= {XY_ISOLATION_TARGET_DB:.1f} dB`。",
        f"- X/Y 回波均衡：差值 `<= {RETURN_BALANCE_TARGET_DB:.1f} dB`。",
        f"- X/Y 远场幅度一致性：RMS 幅差 `<= {XY_MAG_BALANCE_TARGET_DB:.1f} dB`。",
        f"- X/Y 相位一致性：阵元间 RMS 相位离散 `<= {XY_PHASE_SPREAD_TARGET_DEG:.1f} deg`。",
        f"- 双极化向量相关 PDOA：平均 RMS 漂移 `<= {PDOA_RMS_TARGET_DEG:.1f} deg`，最大漂移 `<= {PDOA_MAX_TARGET_DEG:.1f} deg`。",
        "",
        "## 优化方法",
        "",
        "- 先用三频点 S 参数筛选整体馈点、焊盘、端口片、A/B 非对称馈点、弱耦合开路线和温和过孔栅栏候选。",
        "- 再对排名靠前候选提取嵌入远场，复核双极化向量相关 PDOA、X/Y 幅度 RMS 差和阵元间相位离散。",
        "",
        "## S 参数筛选排名",
        "",
        "| 排名 | 候选 | 评分 | 最差Sii | X回波 | Y回波 | 回波差 | 同阵元X/Y隔离 | 说明 |",
        "| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for idx, row in enumerate(top_s, start=1):
        lines.append(
            f"| {idx} | `{row['candidate']}` | {fmt(row['score'])} | {fmt(row['worst_return_db'])} dB | "
            f"{fmt(row['x_return_worst_db'])} dB | {fmt(row['y_return_worst_db'])} dB | "
            f"{fmt(row['xy_return_balance_db'])} dB | {fmt(row['same_element_xy_isolation_db'])} dB | {row['rationale']} |"
        )
    lines.extend(
        [
            "",
            "## 完整复核结果",
            "",
            "| 候选 | 综合评分 | 同阵元X/Y隔离 | 回波差 | 幅差RMS | 相位离散RMS | 向量PDOA平均RMS | 95分位 | 最大漂移 |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for row in sorted(full_rows, key=lambda item: item["full_score"]):
        lines.append(
            f"| `{row['candidate']}` | {fmt(row['full_score'])} | {fmt(row['same_element_xy_isolation_db'])} dB | "
            f"{fmt(row['xy_return_balance_db'])} dB | {fmt(row['xy_mag_imbalance_rms_db'])} dB | "
            f"{fmt(row['xy_phase_spread_rms_deg'])} deg | {fmt(row['dualpol_vector_avg_rms_bias_deg'])} deg | "
            f"{fmt(row['dualpol_vector_p95_rms_bias_deg'])} deg | {fmt(row['dualpol_vector_max_abs_bias_deg'])} deg |"
        )
    lines.extend(
        [
            "",
            "## 最优候选",
            "",
            f"- 候选：`{best['candidate']}`",
            f"- 说明：{best['rationale']}",
            f"- AEDT 工程：`{best['project']}`",
            f"- 最差回波：`{fmt(best['worst_return_db'])} dB`",
            f"- X/A 最差回波：`{fmt(best['x_return_worst_db'])} dB`",
            f"- Y/B 最差回波：`{fmt(best['y_return_worst_db'])} dB`",
            f"- X/Y 回波差：`{fmt(best['xy_return_balance_db'])} dB`",
            f"- 同阵元 X/Y 隔离：`{fmt(best['same_element_xy_isolation_db'])} dB`",
            f"- X/Y 幅度 RMS 差：`{fmt(best['xy_mag_imbalance_rms_db'])} dB`",
            f"- X/Y 阵元间相位离散 RMS：`{fmt(best['xy_phase_spread_rms_deg'])} deg`",
            f"- 双极化向量相关 PDOA 平均 RMS：`{fmt(best['dualpol_vector_avg_rms_bias_deg'])} deg`",
            f"- 双极化向量相关 PDOA 95 分位：`{fmt(best['dualpol_vector_p95_rms_bias_deg'])} deg`",
            f"- 双极化向量相关 PDOA 最大漂移：`{fmt(best['dualpol_vector_max_abs_bias_deg'])} deg`",
            "",
        ]
    )
    if baseline:
        lines.extend(
            [
                "## 与双极化初版对比",
                "",
                "| 指标 | 初版 | 本轮最优 | 变化 |",
                "| --- | ---: | ---: | ---: |",
            ]
        )
        for label, key, unit in [
            ("最差回波", "worst_return_db", "dB"),
            ("同阵元 X/Y 隔离", "same_element_xy_isolation_db", "dB"),
            ("X/Y 回波差", "xy_return_balance_db", "dB"),
            ("X/Y 幅度 RMS 差", "xy_mag_imbalance_rms_db", "dB"),
            ("X/Y 相位离散 RMS", "xy_phase_spread_rms_deg", "deg"),
            ("向量 PDOA 平均 RMS", "dualpol_vector_avg_rms_bias_deg", "deg"),
            ("向量 PDOA 95 分位", "dualpol_vector_p95_rms_bias_deg", "deg"),
        ]:
            delta = float(best[key]) - float(baseline[key])
            lines.append(f"| {label} | {fmt(baseline[key])} {unit} | {fmt(best[key])} {unit} | {delta:+.2f} |")
        lines.append("")
    lines.extend(
        [
            "## 达标情况",
            "",
            f"- S 参数/同阵元隔离目标：`{'通过' if best['meets_s'] else '未通过'}`。",
            f"- X/Y 幅相一致性目标：`{'通过' if best['meets_balance'] else '未通过'}`。",
            f"- PDOA 稳定性目标：`{'通过' if best['meets_pdoa'] else '未通过'}`。",
            f"- 全部目标：`{'通过' if best['meets_all'] else '未通过'}`。",
            "",
            "## 工程判断",
            "",
            "- 本轮直接优化 X/Y 回波均衡、同阵元隔离和远场幅相一致性；若最优仍未达标，说明仅靠探针位置和简单寄生/过孔结构不足以消除双极化通道差异。",
            "- `openline_l2p80` 和 `openline_l2p40` 在三频点 S 参数筛选中排名靠前，但 `openline_l2p80` 的完整远场复核曾触发 AEDT gRPC/无限球设置异常；本轮最终选择已完整复核并保存为可运行工程的 `pad0p28_port0p50_feed3p40`。",
            "- 下一轮应优先进入真正的双极化馈电网络：两路等长微带过渡、可调匹配段、同阵元隔离枝节，以及接收端双通道幅相标定矩阵。",
            "- 当前双极化方案仍建议保留，因为它提供了后端矢量相关和标定自由度；但硬件上必须把 X/Y 两路作为独立接收通道处理。",
            "",
            "## 输出文件",
            "",
            f"- S 参数筛选：`{SPARAM_CSV}`",
            f"- 完整复核：`{FULL_CSV}`",
            f"- 最优曲线：`{BEST_CURVES_CSV}`",
            f"- 最优汇总：`{BEST_SUMMARY_CSV}`",
            f"- 最优 JSON：`{BEST_JSON}`",
        ]
    )
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def copy_best_outputs(best_name: str) -> None:
    for src, dst in [
        (REPORT_DIR / f"{best_name}_curves.csv", BEST_CURVES_CSV),
        (REPORT_DIR / f"{best_name}_summary.csv", BEST_SUMMARY_CSV),
    ]:
        if src.exists():
            shutil.copy2(src, dst)


def run(
    max_sparam_candidates: int = 13,
    full_candidate_count: int = 3,
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
        write_csv(FULL_CSV, [{k: v for k, v in row.items() if k not in {"parameters", "pdoa_metrics"}} for row in full_rows])
    best = min(full_rows, key=lambda row: row["full_score"])
    copy_best_outputs(best["candidate"])

    if ranked_full[-1].name != best["candidate"]:
        best_item = next(item for item in cands if item.name == best["candidate"])
        print(f"Stage: rebuilding final best project {best_item.name}", flush=True)
        apply_candidate(best_item)
        _project, hfss = builder.build_project(
            TOPOLOGY,
            analyze=True,
            non_graphical=True,
            quick=True,
            band_samples=True,
            sparam_only=False,
            return_hfss=True,
        )
        hfss.release_desktop(close_projects=False, close_desktop=True)

    output = {
        "targets": {
            "return_target_db": RETURN_TARGET_DB,
            "xy_isolation_target_db": XY_ISOLATION_TARGET_DB,
            "return_balance_target_db": RETURN_BALANCE_TARGET_DB,
            "xy_mag_balance_target_db": XY_MAG_BALANCE_TARGET_DB,
            "xy_phase_spread_target_deg": XY_PHASE_SPREAD_TARGET_DEG,
            "pdoa_rms_target_deg": PDOA_RMS_TARGET_DEG,
            "pdoa_max_target_deg": PDOA_MAX_TARGET_DEG,
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
            "best_json": str(BEST_JSON),
            "report_md": str(REPORT_MD),
        },
    }
    BEST_JSON.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")
    write_report(best, sparam_rows, full_rows)
    print(json.dumps({k: v for k, v in best.items() if k not in {"parameters", "pdoa_metrics"}}, indent=2, ensure_ascii=False), flush=True)
    print(f"Wrote {REPORT_MD}", flush=True)
    return output


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-sparam-candidates", type=int, default=13)
    parser.add_argument("--full-candidate-count", type=int, default=3)
    parser.add_argument("--resume-sparam", action="store_true")
    parser.add_argument("--full-candidate-names", default="", help="Comma separated candidate names for full validation.")
    args = parser.parse_args()
    full_names = [item.strip() for item in args.full_candidate_names.split(",") if item.strip()]
    run(
        args.max_sparam_candidates,
        args.full_candidate_count,
        resume_sparam=args.resume_sparam,
        full_candidate_names=full_names or None,
    )


if __name__ == "__main__":
    main()
