from __future__ import annotations

import csv
import json
import math
import time
import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ansys.aedt.core import Hfss

import build_uwb_ch9_hfss_d44_topology as builder
import evaluate_uwb_ch9_d44_pdoa_linear_polarization as pdoa_eval
import evaluate_uwb_ch9_d44_topology as topology_eval
import optimize_uwb_ch9_d44_pdoa_polarization_stability as pdoa_stability


ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = ROOT / "reports_d44_geometry_pdoa_opt"
SPARAM_CSV = REPORT_DIR / "UWB_CH9_D44_GEOMETRY_PDOA_sparam_screening.csv"
FULL_CSV = REPORT_DIR / "UWB_CH9_D44_GEOMETRY_PDOA_full_validation.csv"
SOURCE_SWEEP_CSV = REPORT_DIR / "UWB_CH9_D44_GEOMETRY_PDOA_best_source_sweep.csv"
BEST_CURVES_CSV = REPORT_DIR / "UWB_CH9_D44_GEOMETRY_PDOA_best_curves.csv"
BEST_JSON = REPORT_DIR / "UWB_CH9_D44_GEOMETRY_PDOA_best.json"
REPORT_MD = REPORT_DIR / "UWB_CH9_D44_GEOMETRY_PDOA_optimization_report.md"

TOPOLOGY = "dualfeed"
ORIGINAL_PARAMS = dict(builder.TOPOLOGIES[TOPOLOGY]["params"])

RETURN_TARGET_DB = -10.0
ISOLATION_TARGET_DB = 15.0
GAIN_TARGET_DBI = -5.0
AR_TARGET_DB = 3.0
PDOA_RMS_TARGET_DEG = 10.0
PDOA_MAX_TARGET_DEG = 20.0


@dataclass(frozen=True)
class GeometryCandidate:
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


def candidate(name: str, rationale: str, **overrides: float) -> GeometryCandidate:
    params = dict(ORIGINAL_PARAMS)
    params.update(
        {
            "microstrip_feed_enabled": 0.0,
            "neutralization_branch_enabled": 0.0,
            "local_dgs_enabled": 0.0,
            "isolation_slot_enabled": 1.0,
        }
    )
    params.update(overrides)
    return GeometryCandidate(name=name, params=params, rationale=rationale)


def geometry_candidates() -> list[GeometryCandidate]:
    raw = [
        candidate(
            "probe_reference_current",
            "当前双馈探针/焊盘参考结构，作为几何层优化基线。",
            patch_side_mm=9.15,
            feed_offset_u_mm=3.30,
            feed_pad_radius_mm=0.42,
            port_width_mm=0.70,
            isolation_slot_length_mm=10.0,
            isolation_slot_width_mm=0.42,
            isolation_slot_inner_mm=3.20,
        ),
        candidate(
            "small_pad_feed3p30",
            "缩小馈电焊盘和端口片，降低同贴片 A/B 端口近场耦合。",
            patch_side_mm=9.15,
            feed_offset_u_mm=3.30,
            feed_pad_radius_mm=0.34,
            port_width_mm=0.55,
            isolation_slot_length_mm=10.0,
            isolation_slot_width_mm=0.42,
            isolation_slot_inner_mm=3.20,
        ),
        candidate(
            "small_pad_feed3p55",
            "在小焊盘基础上把双馈点外移，观察匹配和正交模隔离是否改善。",
            patch_side_mm=9.15,
            feed_offset_u_mm=3.55,
            feed_pad_radius_mm=0.34,
            port_width_mm=0.55,
            isolation_slot_length_mm=10.0,
            isolation_slot_width_mm=0.42,
            isolation_slot_inner_mm=3.20,
        ),
        candidate(
            "patch9p25_feed3p65",
            "略增贴片边长并外移馈点，尝试恢复谐振同时降低双馈耦合。",
            patch_side_mm=9.25,
            feed_offset_u_mm=3.65,
            feed_pad_radius_mm=0.34,
            port_width_mm=0.55,
            isolation_slot_length_mm=10.0,
            isolation_slot_width_mm=0.42,
            isolation_slot_inner_mm=3.20,
        ),
        candidate(
            "patch9p35_feed3p65",
            "继续增大贴片边长，验证更低等效输入阻抗下的匹配/隔离折中。",
            patch_side_mm=9.35,
            feed_offset_u_mm=3.65,
            feed_pad_radius_mm=0.34,
            port_width_mm=0.55,
            isolation_slot_length_mm=10.0,
            isolation_slot_width_mm=0.42,
            isolation_slot_inner_mm=3.20,
        ),
        candidate(
            "wide_array_slot_feed3p45",
            "加宽并内移阵列隔离槽，优先切断阵元间地电流路径。",
            patch_side_mm=9.20,
            feed_offset_u_mm=3.45,
            feed_pad_radius_mm=0.34,
            port_width_mm=0.55,
            isolation_slot_length_mm=12.0,
            isolation_slot_width_mm=0.58,
            isolation_slot_inner_mm=2.55,
        ),
        candidate(
            "long_array_slot_feed3p45",
            "延长隔离槽但保持中等宽度，减少槽过宽带来的阻抗扰动。",
            patch_side_mm=9.20,
            feed_offset_u_mm=3.45,
            feed_pad_radius_mm=0.34,
            port_width_mm=0.55,
            isolation_slot_length_mm=13.0,
            isolation_slot_width_mm=0.46,
            isolation_slot_inner_mm=2.40,
        ),
        candidate(
            "mild_local_dgs_feed3p45",
            "在每个阵元附近加入温和局部 DGS，尝试改善同贴片双馈端口隔离。",
            patch_side_mm=9.20,
            feed_offset_u_mm=3.45,
            feed_pad_radius_mm=0.34,
            port_width_mm=0.55,
            local_dgs_enabled=1.0,
            local_dgs_length_mm=2.8,
            local_dgs_width_mm=0.14,
            local_dgs_offset_mm=0.55,
            isolation_slot_length_mm=10.0,
            isolation_slot_width_mm=0.42,
            isolation_slot_inner_mm=3.20,
        ),
        candidate(
            "strong_local_dgs_feed3p60",
            "增强局部 DGS 长度和偏移，验证更强地电流切断对极化一致性的影响。",
            patch_side_mm=9.30,
            feed_offset_u_mm=3.60,
            feed_pad_radius_mm=0.34,
            port_width_mm=0.55,
            local_dgs_enabled=1.0,
            local_dgs_length_mm=3.6,
            local_dgs_width_mm=0.18,
            local_dgs_offset_mm=0.75,
            isolation_slot_length_mm=10.0,
            isolation_slot_width_mm=0.42,
            isolation_slot_inner_mm=3.20,
        ),
        candidate(
            "combined_slot_dgs_feed3p55",
            "组合加长阵列隔离槽和温和局部 DGS，寻找隔离与方向图扰动之间的折中。",
            patch_side_mm=9.25,
            feed_offset_u_mm=3.55,
            feed_pad_radius_mm=0.34,
            port_width_mm=0.55,
            local_dgs_enabled=1.0,
            local_dgs_length_mm=2.8,
            local_dgs_width_mm=0.14,
            local_dgs_offset_mm=0.55,
            isolation_slot_length_mm=12.0,
            isolation_slot_width_mm=0.46,
            isolation_slot_inner_mm=2.55,
        ),
    ]
    valid = []
    for item in raw:
        merged = dict(builder.BASE_PARAMS)
        merged.update(item.params)
        try:
            builder.validate_params(merged)
            valid.append(item)
        except Exception as exc:
            print(f"Skip invalid {item.name}: {exc}", flush=True)
    return valid


def apply_candidate(item: GeometryCandidate) -> None:
    params = builder.TOPOLOGIES[TOPOLOGY]["params"]
    params.clear()
    params.update(item.params)


def get_sparams(hfss: Hfss, csv_path: Path) -> dict:
    return topology_eval.get_s_parameter_snapshot(hfss, csv_path)


def sparam_score(s: dict) -> float:
    return_miss = max(0.0, s["worst_return_db"] - RETURN_TARGET_DB)
    isolation_miss = max(0.0, ISOLATION_TARGET_DB - s["isolation_db"])
    return 20.0 * return_miss + 6.0 * isolation_miss - 0.6 * max(0.0, -s["worst_return_db"] - 8.0)


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


def sparam_screen(item: GeometryCandidate, index: int) -> dict:
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
        s = get_sparams(hfss, REPORT_DIR / f"{item.name}_s_parameters.csv")
    finally:
        hfss.release_desktop(close_projects=False, close_desktop=True)
    row = {
        "index": index,
        "candidate": item.name,
        "score": sparam_score(s),
        "elapsed_s": round(time.time() - start, 1),
        "rationale": item.rationale,
        "worst_return_db": s["worst_return_db"],
        "worst_return_expr": s["worst_return_expr"],
        "isolation_db": s["isolation_db"],
        "worst_coupling_db": s["worst_coupling_db"],
        "worst_coupling_expr": s["worst_coupling_expr"],
    }
    for key in [
        "patch_side_mm",
        "feed_offset_u_mm",
        "feed_pad_radius_mm",
        "port_width_mm",
        "weak_coupling_open_line_enabled",
        "weak_coupling_open_line_length_mm",
        "weak_coupling_open_line_width_mm",
        "weak_coupling_open_line_offset_mm",
        "weak_coupling_open_line_gap_mm",
        "via_fence_enabled",
        "via_fence_count",
        "via_fence_radius_mm",
        "via_fence_pitch_mm",
        "via_fence_edge_offset_mm",
        "via_fence_center_mm",
        "isolation_slot_length_mm",
        "isolation_slot_width_mm",
        "isolation_slot_inner_mm",
        "local_dgs_enabled",
        "local_dgs_length_mm",
        "local_dgs_width_mm",
        "local_dgs_offset_mm",
    ]:
        row[key] = item.params.get(key, "")
    print(json.dumps(row, indent=2, ensure_ascii=False), flush=True)
    return row


def summarize_fov_for_assignment(hfss: Hfss, eval_freqs: list[float], amp_b: float, phase_b: float) -> dict:
    sources = hfss.get_all_sources()
    hfss.edit_sources(pdoa_stability.source_assignments(sources, pdoa_stability.Candidate(amp_b, phase_b)))
    summaries = []
    for freq in eval_freqs:
        grid = topology_eval.get_grid(hfss, freq)
        summaries.append(topology_eval.summarize_rows(freq, grid["rows"]))
    return {
        "gain_min_dbi": min(item["gain_min_dbi"] for item in summaries),
        "gain_max_dbi": max(item["gain_max_dbi"] for item in summaries),
        "axial_ratio_max_db": max(item["axial_ratio_max_db"] for item in summaries),
        "axial_ratio_min_db": min(item["axial_ratio_min_db"] for item in summaries),
        "cp_coverage_min_percent": min(item["cp_coverage_percent"] for item in summaries),
    }


def source_sweep(fields: dict, eval_freqs: list[float]) -> tuple[dict, dict, list[dict], list[dict]]:
    history = []
    for source_candidate in pdoa_stability.candidate_grid():
        result, _ = pdoa_stability.evaluate_candidate(fields, eval_freqs, source_candidate, keep_curves=False)
        history.append(result)
    history.sort(key=lambda row: row["score"])
    pure_best = history[0]
    baseline, _ = pdoa_stability.evaluate_candidate(fields, eval_freqs, pdoa_stability.Candidate(1.0, -90.0), keep_curves=False)
    best_result, curves = pdoa_stability.evaluate_candidate(
        fields,
        eval_freqs,
        pdoa_stability.Candidate(float(pure_best["amp_b"]), float(pure_best["phase_b_deg"])),
        keep_curves=True,
    )
    return baseline, pure_best, history, curves


def write_curves(rows: list[dict]) -> None:
    if not rows:
        return
    fields = [
        "freq_ghz",
        "phi_deg",
        "theta_deg",
        "linear_pol_deg",
        "amp_b",
        "phase_b_deg",
        "channel_set",
        "baseline",
        "pdoa_deg",
        "pdoa_unwrapped_deg",
        "left_mag_rel_db",
        "right_mag_rel_db",
        "valid",
    ]
    with BEST_CURVES_CSV.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    key: f"{row[key]:.6f}" if isinstance(row.get(key), float) else row.get(key)
                    for key in fields
                }
            )


def full_validate(item: GeometryCandidate) -> dict:
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
        s = get_sparams(hfss, REPORT_DIR / f"{item.name}_full_s_parameters.csv")
        sources = hfss.get_all_sources()
        eval_freqs = pdoa_eval.nearest_frequencies(pdoa_eval.get_available_frequencies(hfss))
        fields = pdoa_eval.acquire_embedded_fields(hfss, sources, eval_freqs)
        baseline, pure_best, source_history, curves = source_sweep(fields, eval_freqs)
        write_csv(SOURCE_SWEEP_CSV, source_history)
        write_curves(curves)
        fov_baseline = summarize_fov_for_assignment(hfss, eval_freqs, 1.0, -90.0)
        fov_best = summarize_fov_for_assignment(hfss, eval_freqs, float(pure_best["amp_b"]), float(pure_best["phase_b_deg"]))
    finally:
        hfss.release_desktop(close_projects=False, close_desktop=True)

    full_score = (
        sparam_score(s)
        + 0.85 * pure_best["avg_rms_bias_deg"]
        + 0.20 * pure_best["p95_rms_bias_deg"]
        + 0.05 * pure_best["max_abs_bias_deg"]
        + 0.04 * max(0.0, fov_best["axial_ratio_max_db"] - AR_TARGET_DB)
        + 0.7 * max(0.0, GAIN_TARGET_DBI - fov_best["gain_min_dbi"])
    )
    result = {
        "candidate": item.name,
        "project": str(project),
        "elapsed_s": round(time.time() - start, 1),
        "rationale": item.rationale,
        "full_score": full_score,
        "sparam_score": sparam_score(s),
        "worst_return_db": s["worst_return_db"],
        "isolation_db": s["isolation_db"],
        "worst_return_expr": s["worst_return_expr"],
        "worst_coupling_expr": s["worst_coupling_expr"],
        "baseline_avg_rms_bias_deg": baseline["avg_rms_bias_deg"],
        "baseline_p95_rms_bias_deg": baseline["p95_rms_bias_deg"],
        "baseline_max_abs_bias_deg": baseline["max_abs_bias_deg"],
        "best_amp_b": pure_best["amp_b"],
        "best_phase_b_deg": pure_best["phase_b_deg"],
        "best_avg_rms_bias_deg": pure_best["avg_rms_bias_deg"],
        "best_p95_rms_bias_deg": pure_best["p95_rms_bias_deg"],
        "best_max_abs_bias_deg": pure_best["max_abs_bias_deg"],
        "best_avg_valid_percent": pure_best["avg_valid_percent"],
        "fov_baseline_gain_min_dbi": fov_baseline["gain_min_dbi"],
        "fov_baseline_axial_ratio_max_db": fov_baseline["axial_ratio_max_db"],
        "fov_baseline_cp_coverage_min_percent": fov_baseline["cp_coverage_min_percent"],
        "fov_best_gain_min_dbi": fov_best["gain_min_dbi"],
        "fov_best_axial_ratio_max_db": fov_best["axial_ratio_max_db"],
        "fov_best_cp_coverage_min_percent": fov_best["cp_coverage_min_percent"],
        "meets_s": s["worst_return_db"] <= RETURN_TARGET_DB and s["isolation_db"] >= ISOLATION_TARGET_DB,
        "meets_pdoa": pure_best["avg_rms_bias_deg"] <= PDOA_RMS_TARGET_DEG and pure_best["max_abs_bias_deg"] <= PDOA_MAX_TARGET_DEG,
        "meets_fov": fov_best["gain_min_dbi"] >= GAIN_TARGET_DBI and fov_best["axial_ratio_max_db"] <= AR_TARGET_DB,
        "parameters": item.params,
    }
    result["meets_all"] = result["meets_s"] and result["meets_pdoa"] and result["meets_fov"]
    return result


def write_report(best: dict, sparam_rows: list[dict], full_rows: list[dict]) -> None:
    top_s = sorted(sparam_rows, key=lambda row: row["score"])[:8]
    lines = [
        "# D44 锚点天线几何/隔离结构 PDOA 稳定性优化报告",
        "",
        "## 本轮目标",
        "",
        f"- S 参数：最差 `Sii <= {RETURN_TARGET_DB:.1f} dB`，端口隔离 `>= {ISOLATION_TARGET_DB:.1f} dB`。",
        f"- FOV：最小增益 `>= {GAIN_TARGET_DBI:.1f} dBi`，轴比 `<= {AR_TARGET_DB:.1f} dB`。",
        f"- PDOA：不同线极化下平均 RMS 漂移 `<= {PDOA_RMS_TARGET_DEG:.1f} deg`，最大漂移 `<= {PDOA_MAX_TARGET_DEG:.1f} deg`。",
        "",
        "## 优化路径",
        "",
        "- 从上一轮结论出发，不再只调整 90 度混合器输出幅相，而是进入阵元几何和隔离结构层。",
        "- 本轮稳定完成的候选覆盖：馈电焊盘/端口片缩小、馈点外移、贴片边长联动。",
        "- 脚本中保留了阵列隔离槽加宽/加长和局部 DGS 候选，但这批候选在 AEDT 阶段曾出现异常中断，未纳入本次默认排名，后续需要单独排查。",
        "- 先使用三频点 S 参数快速筛选，再对排名最优候选重新带远场求解，并提取复数远场做 PDOA 极化稳定性评估。",
        "",
        "## S 参数筛选排名",
        "",
        "| 排名 | 候选 | 评分 | 最差 Sii | 隔离度 | 说明 |",
        "| ---: | --- | ---: | ---: | ---: | --- |",
    ]
    for idx, row in enumerate(top_s, start=1):
        lines.append(
            f"| {idx} | `{row['candidate']}` | {fmt(row['score'])} | {fmt(row['worst_return_db'])} dB | {fmt(row['isolation_db'])} dB | {row['rationale']} |"
        )
    lines.extend(
        [
            "",
            "## 最优完整复核候选",
            "",
            f"- 候选：`{best.get('candidate')}`",
            f"- 说明：{best.get('rationale')}",
            f"- AEDT 工程：`{best.get('project')}`",
            f"- 最差 Sii：`{fmt(best.get('worst_return_db'))} dB`",
            f"- 隔离度：`{fmt(best.get('isolation_db'))} dB`",
            f"- PDOA 最优 B 路幅度：`{fmt(best.get('best_amp_b'), 3)}`",
            f"- PDOA 最优 B 路相位：`{fmt(best.get('best_phase_b_deg'), 1)} deg`",
            f"- 平均 RMS PDOA 漂移：`{fmt(best.get('best_avg_rms_bias_deg'))} deg`",
            f"- 95 分位 RMS PDOA 漂移：`{fmt(best.get('best_p95_rms_bias_deg'))} deg`",
            f"- 最大 PDOA 漂移：`{fmt(best.get('best_max_abs_bias_deg'))} deg`",
            f"- FOV 最小增益：`{fmt(best.get('fov_best_gain_min_dbi'))} dBi`",
            f"- FOV 最大轴比：`{fmt(best.get('fov_best_axial_ratio_max_db'))} dB`",
            f"- CP 覆盖率下限：`{fmt(best.get('fov_best_cp_coverage_min_percent'), 1)}%`",
            "",
            "## 达标情况",
            "",
            f"- S 参数目标：`{'通过' if best.get('meets_s') else '未通过'}`。",
            f"- PDOA 极化稳定性目标：`{'通过' if best.get('meets_pdoa') else '未通过'}`。",
            f"- FOV/轴比目标：`{'通过' if best.get('meets_fov') else '未通过'}`。",
            f"- 全部目标：`{'通过' if best.get('meets_all') else '未通过'}`。",
            "",
            "## 工程结论",
            "",
            "- 缩小焊盘和端口片对同贴片 A/B 隔离有正向作用，是本轮最可靠的几何趋势。",
            "- 馈点外移会改变匹配和隔离折中，但本轮没有改善 PDOA 对线极化的根本敏感性。",
            "- 本轮最优完整候选仍未把 PDOA 最大漂移压低到目标内，说明需要引入真正的双极化接收/标定融合，或进一步做阵元级矢量有效长度一致性优化。",
            "- 下一轮建议在当前小焊盘趋势上继续细扫 `feed_pad_radius=0.28-0.36 mm`、`port_width=0.45-0.60 mm`、`feed_offset=3.20-3.60 mm`，并增加可调的 A/B 间弱耦合隔离开路线或过孔栅栏模型。",
            "",
            "## 输出文件",
            "",
            f"- S 参数筛选：`{SPARAM_CSV}`",
            f"- 完整复核：`{FULL_CSV}`",
            f"- 最优源幅相扫：`{SOURCE_SWEEP_CSV}`",
            f"- 最优曲线：`{BEST_CURVES_CSV}`",
            f"- 最优结果 JSON：`{BEST_JSON}`",
        ]
    )
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run(max_sparam_candidates: int = 4, full_candidate_count: int = 2) -> dict:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    candidates = geometry_candidates()[:max_sparam_candidates]
    sparam_rows = []
    for idx, item in enumerate(candidates, start=1):
        print(f"Stage: S-parameter screening {idx}/{len(candidates)} {item.name}", flush=True)
        sparam_rows.append(sparam_screen(item, idx))
        write_csv(SPARAM_CSV, sparam_rows)
    ranked_candidates = [
        next(item for item in candidates if item.name == row["candidate"])
        for row in sorted(sparam_rows, key=lambda row: row["score"])[:full_candidate_count]
    ]

    full_rows = []
    for idx, item in enumerate(ranked_candidates, start=1):
        print(f"Stage: full validation {idx}/{len(ranked_candidates)} {item.name}", flush=True)
        full_rows.append(full_validate(item))
        write_csv(FULL_CSV, [{k: v for k, v in row.items() if k != "parameters"} for row in full_rows])
    best = min(full_rows, key=lambda row: row["full_score"])

    # Keep the best geometry as the final runnable AEDT project.
    if ranked_candidates[-1].name != best["candidate"]:
        best_item = next(item for item in candidates if item.name == best["candidate"])
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
            "isolation_target_db": ISOLATION_TARGET_DB,
            "gain_target_dbi": GAIN_TARGET_DBI,
            "axial_ratio_target_db": AR_TARGET_DB,
            "pdoa_rms_target_deg": PDOA_RMS_TARGET_DEG,
            "pdoa_max_target_deg": PDOA_MAX_TARGET_DEG,
        },
        "candidate_count": len(candidates),
        "note": "默认只运行已验证稳定的前 4 个几何候选；DGS/更大贴片候选在 AEDT 阶段曾出现异常中断，保留在脚本中供后续单独排查。",
        "sparam_top": sorted(sparam_rows, key=lambda row: row["score"])[:8],
        "full_validation": full_rows,
        "best": best,
        "files": {
            "sparam_csv": str(SPARAM_CSV),
            "full_csv": str(FULL_CSV),
            "source_sweep_csv": str(SOURCE_SWEEP_CSV),
            "best_curves_csv": str(BEST_CURVES_CSV),
            "best_json": str(BEST_JSON),
            "report_md": str(REPORT_MD),
        },
    }
    BEST_JSON.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")
    write_report(best, sparam_rows, full_rows)
    print(json.dumps(best, indent=2, ensure_ascii=False), flush=True)
    print(f"Wrote {REPORT_MD}", flush=True)
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-sparam-candidates", type=int, default=4)
    parser.add_argument("--full-candidate-count", type=int, default=2)
    args = parser.parse_args()
    run(max_sparam_candidates=args.max_sparam_candidates, full_candidate_count=args.full_candidate_count)
