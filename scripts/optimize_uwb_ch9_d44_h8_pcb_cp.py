from __future__ import annotations

import argparse
import csv
import json
import math
import time
from dataclasses import dataclass
from pathlib import Path

from ansys.aedt.core import Hfss

import build_uwb_ch9_hfss_d44_h8_pcb_cp as builder
import evaluate_uwb_ch9_d44_h8_pcb_cp as evaluator


ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = ROOT / "reports_d44_h8_pcb_cp"
HISTORY_CSV = REPORT_DIR / "UWB_CH9_D44_H8_PCB_CP_optimization_history.csv"
BEST_JSON = REPORT_DIR / "UWB_CH9_D44_H8_PCB_CP_optimization_best.json"
REPORT_MD = REPORT_DIR / "UWB_CH9_D44_H8_PCB_CP_optimization_report.md"

RETURN_TARGET_DB = -10.0
ISOLATION_TARGET_DB = 15.0
GAIN_TARGET_DBI = -5.0
AR_TARGET_DB = 3.0


@dataclass
class Candidate:
    name: str
    params: dict[str, float]
    rationale: str


def baseline_params() -> dict[str, float]:
    return dict(builder.PARAMS)


def merged_params(overrides: dict[str, float]) -> dict[str, float]:
    params = baseline_params()
    params.update(overrides)
    return params


def generate_candidates() -> list[Candidate]:
    """Generate theory-guided candidates around the current D44/H8 geometry.

    The ranges are intentionally conservative. The 44 mm board leaves little
    edge clearance for the four-patch diamond array, so this optimizer first
    searches low-risk dimensions before trying larger bandwidth moves.
    """

    candidates: list[Candidate] = [
        Candidate(
            "baseline_branch_best",
            merged_params({}),
            "Existing branch best quick-sweep point.",
        ),
        Candidate(
            "feed_inward_match",
            merged_params({"patch_side_mm": 8.92, "feed_offset_u_mm": 2.56, "corner_cut_mm": 0.62}),
            "Move feed inward to reduce over-coupled edge behavior while keeping resonance nearly fixed.",
        ),
        Candidate(
            "feed_outward_match",
            merged_params({"patch_side_mm": 8.88, "feed_offset_u_mm": 2.86, "corner_cut_mm": 0.62}),
            "Move feed outward and slightly shrink patch to test input-resistance matching.",
        ),
        Candidate(
            "slightly_larger_patch",
            merged_params({"patch_side_mm": 9.05, "feed_offset_u_mm": 2.78, "corner_cut_mm": 0.64}),
            "Lower the resonant point and retune feed for CH9 edge return loss.",
        ),
        Candidate(
            "slightly_smaller_patch",
            merged_params({"patch_side_mm": 8.78, "feed_offset_u_mm": 2.72, "corner_cut_mm": 0.58}),
            "Raise the resonant point and reduce corner perturbation.",
        ),
        Candidate(
            "larger_corner_split",
            merged_params({"patch_side_mm": 8.95, "feed_offset_u_mm": 2.70, "corner_cut_mm": 0.78}),
            "Increase modal split for axial-ratio tuning near the band center.",
        ),
        Candidate(
            "smaller_corner_split",
            merged_params({"patch_side_mm": 8.95, "feed_offset_u_mm": 2.70, "corner_cut_mm": 0.46}),
            "Reduce modal split in case the current AR modes are over-separated.",
        ),
        Candidate(
            "wider_port_pad",
            merged_params({"patch_side_mm": 8.91, "feed_offset_u_mm": 2.68, "corner_cut_mm": 0.62, "port_width_mm": 1.10, "feed_pad_radius_mm": 0.55}),
            "Increase local feed capacitance to improve the residual return-loss miss.",
        ),
        Candidate(
            "narrower_port_pad",
            merged_params({"patch_side_mm": 8.91, "feed_offset_u_mm": 2.68, "corner_cut_mm": 0.62, "port_width_mm": 0.45, "feed_pad_radius_mm": 0.35}),
            "Reduce local feed capacitance and port-sheet perturbation.",
        ),
        Candidate(
            "ground_slot_longer",
            merged_params({"patch_side_mm": 8.91, "feed_offset_u_mm": 2.68, "corner_cut_mm": 0.62, "isolation_slot_length_mm": 10.0, "isolation_slot_width_mm": 0.45}),
            "Increase decoupling slot length for isolation and FOV ripple control.",
        ),
        Candidate(
            "ground_slot_shorter",
            merged_params({"patch_side_mm": 8.91, "feed_offset_u_mm": 2.68, "corner_cut_mm": 0.62, "isolation_slot_length_mm": 6.0, "isolation_slot_width_mm": 0.30}),
            "Reduce slot perturbation if the slot is degrading match or CP modes.",
        ),
        Candidate(
            "thicker_substrate_2p4",
            merged_params({"substrate_h_mm": 2.4, "patch_side_mm": 9.18, "feed_offset_u_mm": 2.86, "corner_cut_mm": 0.68}),
            "Use more height for bandwidth while staying far below the 8 mm envelope.",
        ),
        Candidate(
            "thicker_substrate_3p2",
            merged_params({"substrate_h_mm": 3.2, "patch_side_mm": 9.55, "feed_offset_u_mm": 3.05, "corner_cut_mm": 0.72}),
            "More aggressive bandwidth move using available height margin.",
        ),
        Candidate(
            "large_patch_high_h",
            merged_params({"substrate_h_mm": 3.2, "patch_side_mm": 10.15, "feed_offset_u_mm": 3.35, "corner_cut_mm": 0.82}),
            "Theory-driven half-wave patch length test on thicker substrate.",
        ),
        Candidate(
            "local_corner_0p86",
            merged_params({"patch_side_mm": 8.95, "feed_offset_u_mm": 2.70, "corner_cut_mm": 0.86}),
            "Continue the first-round trend by increasing the corner perturbation.",
        ),
        Candidate(
            "local_corner_0p94",
            merged_params({"patch_side_mm": 8.95, "feed_offset_u_mm": 2.70, "corner_cut_mm": 0.94}),
            "Test whether additional modal splitting improves the lower-band return miss.",
        ),
        Candidate(
            "local_feed_2p62_corner_0p82",
            merged_params({"patch_side_mm": 8.96, "feed_offset_u_mm": 2.62, "corner_cut_mm": 0.82}),
            "Retune feed inward after increasing corner perturbation.",
        ),
        Candidate(
            "local_feed_2p78_corner_0p82",
            merged_params({"patch_side_mm": 8.96, "feed_offset_u_mm": 2.78, "corner_cut_mm": 0.82}),
            "Retune feed outward after increasing corner perturbation.",
        ),
        Candidate(
            "local_patch_9p00_corner_0p84",
            merged_params({"patch_side_mm": 9.00, "feed_offset_u_mm": 2.74, "corner_cut_mm": 0.84}),
            "Slightly lower resonance and keep the stronger CP modal split.",
        ),
        Candidate(
            "local_patch_8p90_corner_0p82",
            merged_params({"patch_side_mm": 8.90, "feed_offset_u_mm": 2.66, "corner_cut_mm": 0.82}),
            "Slightly raise resonance with the stronger CP modal split.",
        ),
        Candidate(
            "local_wide_port_corner_0p82",
            merged_params({"patch_side_mm": 8.96, "feed_offset_u_mm": 2.70, "corner_cut_mm": 0.82, "port_width_mm": 1.05, "feed_pad_radius_mm": 0.55}),
            "Combine stronger modal split with extra feed capacitance.",
        ),
        Candidate(
            "local_narrow_port_corner_0p82",
            merged_params({"patch_side_mm": 8.96, "feed_offset_u_mm": 2.70, "corner_cut_mm": 0.82, "port_width_mm": 0.45, "feed_pad_radius_mm": 0.35}),
            "Combine stronger modal split with reduced feed capacitance.",
        ),
    ]
    return [c for c in candidates if is_valid_candidate(c)]


def is_valid_candidate(candidate: Candidate) -> bool:
    try:
        original = dict(builder.PARAMS)
        builder.PARAMS.update(candidate.params)
        builder.validate_params(builder.PARAMS)
        return True
    except Exception:
        return False
    finally:
        builder.PARAMS.clear()
        builder.PARAMS.update(original)


def apply_candidate(candidate: Candidate) -> None:
    builder.PARAMS.clear()
    builder.PARAMS.update(candidate.params)


def open_hfss() -> Hfss:
    return Hfss(
        project=str(builder.PROJECT_PATH),
        design="Array4_Diamond_D44_H8_PCB_CP",
        version="2023.1",
        non_graphical=True,
        new_desktop=True,
        close_on_exit=False,
        remove_lock=True,
    )


def extract_s_metrics() -> dict:
    hfss = open_hfss()
    try:
        return evaluator.get_s_parameter_snapshot(hfss)
    finally:
        hfss.release_desktop(close_projects=False, close_desktop=True)


def s_score(row: dict) -> float:
    return_miss = max(0.0, row["worst_return_db"] - RETURN_TARGET_DB)
    isolation_miss = max(0.0, ISOLATION_TARGET_DB - row["isolation_db"])
    # Reward extra return-loss margin and isolation, but keep the score stable.
    return 10.0 * return_miss + 2.0 * isolation_miss - 0.15 * max(0.0, row["isolation_db"] - ISOLATION_TARGET_DB)


def run_sparam_candidate(index: int, candidate: Candidate) -> dict:
    start = time.time()
    apply_candidate(candidate)
    builder.build_project(
        analyze=True,
        non_graphical=True,
        quick=True,
        band_samples=True,
        sparam_only=True,
    )
    s = extract_s_metrics()
    row = {
        "stage": "sparam",
        "index": index,
        "candidate": candidate.name,
        "score": None,
        "elapsed_s": round(time.time() - start, 1),
        "rationale": candidate.rationale,
        **{k: candidate.params[k] for k in sorted(candidate.params)},
        "worst_return_db": s["worst_return_db"],
        "worst_return_expr": s["worst_return_expr"],
        "worst_coupling_db": s["worst_coupling_db"],
        "worst_coupling_expr": s["worst_coupling_expr"],
        "isolation_db": s["isolation_db"],
    }
    row["score"] = s_score(row)
    append_history(row)
    print(json.dumps(row, indent=2), flush=True)
    return row


def append_history(row: dict) -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    exists = HISTORY_CSV.exists()
    with HISTORY_CSV.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(row))
        if not exists:
            writer.writeheader()
        writer.writerow(row)


def run_full_candidate(candidate: Candidate) -> dict:
    apply_candidate(candidate)
    builder.build_project(
        analyze=True,
        non_graphical=True,
        quick=True,
        band_samples=True,
        sparam_only=False,
    )
    # The evaluator writes the detailed JSON/CSV/report artifacts.
    evaluator.main()
    metrics = json.loads(evaluator.METRICS_JSON.read_text(encoding="utf-8"))
    fov = summarize_fov(metrics)
    s = metrics.get("s_parameters", {})
    row = {
        "candidate": candidate.name,
        "parameters": candidate.params,
        "rationale": candidate.rationale,
        "s_parameters": s,
        "fov_summary": fov,
        "meets_all_targets": (
            s.get("worst_return_db", math.inf) <= RETURN_TARGET_DB
            and s.get("isolation_db", -math.inf) >= ISOLATION_TARGET_DB
            and fov["coverage_envelope_gain_min_dbi"] >= GAIN_TARGET_DBI
            and fov["cp_qualified_ar_max_db"] <= AR_TARGET_DB
        ),
    }
    BEST_JSON.write_text(json.dumps(row, indent=2), encoding="utf-8")
    write_optimization_report(row)
    return row


def summarize_fov(metrics: dict) -> dict:
    coverage_gain = []
    cp_ar = []
    cp_gain = []
    cp_coverage = []
    seq_gain = []
    seq_coverage = []
    for summaries in metrics.get("fov_by_freq", {}).values():
        cov = summaries.get("coverage_envelope_best_port", {})
        cp = summaries.get("cp_qualified_envelope", {})
        seq = summaries.get("sequential_quadrature_all_ports", {})
        if cov:
            coverage_gain.append(cov.get("gain_min_dbi", -math.inf))
        if cp:
            cp_ar.append(cp.get("axial_ratio_max_db", math.inf))
            cp_gain.append(cp.get("gain_min_dbi", -math.inf))
            cp_coverage.append(cp.get("cp_coverage_percent", 0.0))
        if seq:
            seq_gain.append(seq.get("gain_min_dbi", -math.inf))
            seq_coverage.append(seq.get("cp_coverage_percent", 0.0))
    return {
        "coverage_envelope_gain_min_dbi": min(coverage_gain) if coverage_gain else -math.inf,
        "cp_qualified_ar_max_db": max(cp_ar) if cp_ar else math.inf,
        "cp_qualified_gain_min_dbi": min(cp_gain) if cp_gain else -math.inf,
        "cp_qualified_coverage_min_percent": min(cp_coverage) if cp_coverage else 0.0,
        "sequential_gain_min_dbi": min(seq_gain) if seq_gain else -math.inf,
        "sequential_cp_coverage_min_percent": min(seq_coverage) if seq_coverage else 0.0,
    }


def fmt(value: float | int | None, digits: int = 2) -> str:
    if value is None:
        return "N/A"
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return "N/A"
    return f"{float(value):.{digits}f}"


def write_optimization_report(best: dict) -> None:
    s = best.get("s_parameters", {})
    fov = best.get("fov_summary", {})
    params = best.get("parameters", {})
    history_rows = []
    if HISTORY_CSV.exists():
        with HISTORY_CSV.open(newline="", encoding="utf-8") as f:
            history_rows = list(csv.DictReader(f))
    top_rows = sorted(history_rows, key=lambda r: float(r.get("score") or 1e9))[:8]

    lines = [
        "# UWB CH9 D44 H8 PCB CP 自动优化报告",
        "",
        "## 设计目标",
        "",
        f"- PCB 直径：44 mm",
        f"- 总高度：不超过 8 mm",
        f"- 工作频段：7.738-8.233 GHz",
        f"- 回波损耗目标：三频点最差 Sii <= {RETURN_TARGET_DB:.1f} dB",
        f"- 端口隔离目标：最差耦合对应隔离度 >= {ISOLATION_TARGET_DB:.1f} dB",
        f"- FOV 增益目标：Theta 0-360 deg, Phi 45-90 deg 内最小 GainTotal >= {GAIN_TARGET_DBI:.1f} dBi",
        f"- 圆极化目标：FOV 内 AxialRatioValue <= {AR_TARGET_DB:.1f} dB",
        "",
        "## 自动优化方法",
        "",
        "- 采用微带贴片经验公式和上一轮仿真结果生成候选：贴片边长控制谐振频点，馈点偏移控制输入阻抗，截角控制正交模分裂，板厚和地槽控制带宽/耦合/FOV。",
        "- 第一阶段使用三频点快速离散扫频，只保存 S 参数，快速筛除失配候选。",
        "- 第二阶段对 S 参数最佳候选重建包含远场球面的 HFSS 工程，并导出 FOV 增益和轴比指标。",
        "- 最终 AEDT 工程保存为项目根目录下的 `UWB_CH9_Diamond_CP_Array_D44_H8_PCB_CP.aedt`，可直接用 AEDT 打开复核。",
        "",
        "## 最佳参数",
        "",
    ]
    for key in [
        "substrate_h_mm",
        "patch_side_mm",
        "corner_cut_mm",
        "feed_offset_u_mm",
        "feed_pad_radius_mm",
        "port_width_mm",
        "ground_radius_mm",
        "isolation_slot_length_mm",
        "isolation_slot_width_mm",
        "isolation_slot_inner_mm",
    ]:
        if key in params:
            lines.append(f"- `{key}`: `{fmt(params[key], 3)}`")

    lines.extend(
        [
            "",
            "## 核心仿真指标",
            "",
            f"- 最差回波损耗：`{fmt(s.get('worst_return_db'))} dB`，表达式 `{s.get('worst_return_expr', 'N/A')}`",
            f"- 最差端口耦合：`{fmt(s.get('worst_coupling_db'))} dB`，表达式 `{s.get('worst_coupling_expr', 'N/A')}`",
            f"- 对应隔离度：`{fmt(s.get('isolation_db'))} dB`",
            f"- 最佳端口覆盖包络最小增益：`{fmt(fov.get('coverage_envelope_gain_min_dbi'))} dBi`",
            f"- CP 合格包络最大轴比：`{fmt(fov.get('cp_qualified_ar_max_db'))} dB`",
            f"- CP 合格包络最小增益：`{fmt(fov.get('cp_qualified_gain_min_dbi'))} dBi`",
            f"- CP 覆盖率最小值：`{fmt(fov.get('cp_qualified_coverage_min_percent'), 1)}%`",
            f"- 顺序 90 度四端口激励 CP 覆盖率最小值：`{fmt(fov.get('sequential_cp_coverage_min_percent'), 1)}%`",
            "",
            "## 是否满足目标",
            "",
            f"- 综合结论：`{'通过' if best.get('meets_all_targets') else '未完全通过'}`",
            "",
        ]
    )
    if top_rows:
        lines.extend(["## S 参数候选排名", "", "| 排名 | 候选 | 分数 | 最差 Sii | 隔离度 | 说明 |", "| ---: | --- | ---: | ---: | ---: | --- |"])
        for idx, row in enumerate(top_rows, start=1):
            lines.append(
                f"| {idx} | {row.get('candidate')} | {fmt(float(row.get('score', 0)))} | "
                f"{fmt(float(row.get('worst_return_db', 0)))} dB | {fmt(float(row.get('isolation_db', 0)))} dB | "
                f"{row.get('rationale', '')} |"
            )

    lines.extend(
        [
            "",
            "## 工程文件",
            "",
            f"- 最终 AEDT 项目：`{builder.PROJECT_PATH}`",
            f"- 详细 FOV CSV：`{evaluator.FOV_CSV}`",
            f"- S 参数 CSV：`{evaluator.S_CSV}`",
            f"- 指标 JSON：`{evaluator.METRICS_JSON}`",
            f"- 优化历史 CSV：`{HISTORY_CSV}`",
            f"- 最佳参数 JSON：`{BEST_JSON}`",
        ]
    )
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-candidates", type=int, default=8, help="Maximum S-parameter candidates to solve.")
    parser.add_argument("--full-finalists", type=int, default=1, help="Number of S-parameter finalists to run with far fields.")
    parser.add_argument("--reset-history", action="store_true", help="Delete previous optimization history before running.")
    parser.add_argument("--skip-candidates", type=int, default=0, help="Skip this many generated candidates before solving.")
    args = parser.parse_args()

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    if args.reset_history and HISTORY_CSV.exists():
        HISTORY_CSV.unlink()

    candidates = generate_candidates()[args.skip_candidates : args.skip_candidates + args.max_candidates]
    s_rows = [
        run_sparam_candidate(i, candidate)
        for i, candidate in enumerate(candidates, start=args.skip_candidates + 1)
    ]
    ranked = sorted(zip(s_rows, candidates), key=lambda item: item[0]["score"])
    finalists = [candidate for _, candidate in ranked[: args.full_finalists]]
    best_full = None
    for candidate in finalists:
        best_full = run_full_candidate(candidate)
        if best_full["meets_all_targets"]:
            break
    print(json.dumps(best_full, indent=2), flush=True)
    print(f"Wrote {REPORT_MD}", flush=True)


if __name__ == "__main__":
    main()
