from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import optimize_uwb_ch9_d44_dualpol_rf_switch_fov_gain as fov_gain
import optimize_uwb_ch9_d44_truefed_l_s11_match as l_match


ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = ROOT / "reports_d44_dualpol_truefed_l_fov_gain_check"
STEM = "UWB_CH9_D44_DUALPOL_TRUEFED_L_FOV_GAIN"

SUMMARY_CSV = REPORT_DIR / f"{STEM}_summary.csv"
SOURCE_CSV = REPORT_DIR / f"{STEM}_source_summary.csv"
COVERAGE_CSV = REPORT_DIR / f"{STEM}_coverage_summary.csv"
METRICS_JSON = REPORT_DIR / f"{STEM}_metrics.json"
REPORT_MD = REPORT_DIR / f"{STEM}_report.md"


def fmt(value: Any, digits: int = 2) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    return f"{number:.{digits}f}"


def configure_fov_output_paths() -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    fov_gain.REPORT_DIR = REPORT_DIR
    fov_gain.STEM = STEM
    fov_gain.SUMMARY_CSV = SUMMARY_CSV
    fov_gain.SOURCE_CSV = SOURCE_CSV
    fov_gain.COVERAGE_CSV = COVERAGE_CSV
    fov_gain.METRICS_JSON = METRICS_JSON
    fov_gain.REPORT_MD = REPORT_MD


def truefed_candidate(candidate_index: int) -> fov_gain.GainCandidate:
    pool = l_match.candidates()
    if candidate_index < 1 or candidate_index > len(pool):
        raise ValueError(f"candidate_index must be between 1 and {len(pool)}")
    item = pool[candidate_index - 1]
    return fov_gain.GainCandidate(
        item.name,
        dict(item.params),
        f"True-fed L-port matching candidate {candidate_index}: {item.rationale}",
    )


def write_report(payload: dict[str, Any]) -> None:
    summary = payload["summary"]
    strict_ok = bool(summary["strict_gain_target_pass"]) and bool(summary["strict_realized_gain_target_pass"])
    coverage_ok = bool(summary["coverage_gain_target_pass"]) and bool(summary["coverage_realized_gain_target_pass"])
    s11_ok = bool(summary.get("all_workstate_s11_pass")) and bool(summary.get("all_low_elevation_s11_pass", True))
    lines = [
        "# D44 true-fed L 端口 FOV 增益复核报告",
        "",
        "## 目标与口径",
        "",
        f"- 增益目标：FOV 内 `GainTotal` 与 `RealizedGainTotal` 均 `>= {fov_gain.GAIN_TARGET_DBI:.1f} dBi`。",
        f"- 匹配目标：A/B 工作态与 L 端口最差 S11 均 `<= {fov_gain.RETURN_TARGET_DB:.1f} dB`。",
        f"- FOV 口径：Theta `{fov_gain.THETA_MIN_DEG:.0f}..{fov_gain.THETA_MAX_DEG:.0f} deg`，Phi `0..360 deg`。",
        "- 覆盖口径：同一工作态、频点和方向上，在全部可选端口中取最高增益。",
        "",
        "## 复核候选",
        "",
        f"- 候选编号：`{payload['candidate_index']}`",
        f"- 候选名称：`{summary['candidate']}`",
        f"- 关键结构：`1.6 mm` feed neck + `2.6 mm` open stub + `0.6 mm` folded open branch。",
        "",
        "## 核心指标",
        "",
        f"- 严格口径最小 GainTotal：`{fmt(summary['strict_fov_gain_total_min_dbi'])} dBi`。",
        f"- 严格口径最小 RealizedGainTotal：`{fmt(summary['strict_fov_realized_gain_total_min_dbi'])} dBi`。",
        f"- 覆盖口径最小 GainTotal：`{fmt(summary['coverage_fov_gain_total_min_dbi'])} dBi`。",
        f"- 覆盖口径最小 RealizedGainTotal：`{fmt(summary['coverage_fov_realized_gain_total_min_dbi'])} dBi`。",
        f"- 工作态最差 S11：`{fmt(summary['worst_active_s11_db'])} dB`。",
        f"- L 端口最差 S11：`{fmt(summary.get('worst_low_elevation_s11_db', 'N/A'))} dB`。",
        "",
        "## 达标情况",
        "",
        f"- 严格逐端口增益：`{'达标' if strict_ok else '未达标'}`。",
        f"- 覆盖口径增益：`{'达标' if coverage_ok else '未达标'}`。",
        f"- S11：`{'达标' if s11_ok else '未达标'}`。",
        f"- 综合结论：`{'达标' if coverage_ok and s11_ok else '未完全达标'}`。",
        "",
        "## 最差点",
        "",
        f"- 严格 Realized 最差点：`{summary['strict_fov_realized_gain_total_worst_case']}` / `{summary['strict_fov_realized_gain_total_worst_source']}` / "
        f"{fmt(summary['strict_fov_realized_gain_total_worst_freq_ghz'], 4)} GHz / Theta {fmt(summary['strict_fov_realized_gain_total_worst_theta_deg'], 0)} deg / Phi {fmt(summary['strict_fov_realized_gain_total_worst_phi_deg'], 0)} deg。",
        f"- 覆盖 Realized 最差点：`{summary['coverage_fov_realized_gain_total_worst_case']}` / best source `{summary['coverage_fov_realized_gain_total_worst_source']}` / "
        f"{fmt(summary['coverage_fov_realized_gain_total_worst_freq_ghz'], 4)} GHz / Theta {fmt(summary['coverage_fov_realized_gain_total_worst_theta_deg'], 0)} deg / Phi {fmt(summary['coverage_fov_realized_gain_total_worst_phi_deg'], 0)} deg。",
        "",
        "## 输出文件",
        "",
        f"- 候选汇总 CSV：`{SUMMARY_CSV}`",
        f"- 逐端口明细 CSV：`{SOURCE_CSV}`",
        f"- 覆盖口径明细 CSV：`{COVERAGE_CSV}`",
        f"- 指标 JSON：`{METRICS_JSON}`",
    ]
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run(candidate_index: int, copy_projects: bool, settle_seconds: float, cores: int, tasks: int, center_only: bool) -> dict[str, Any]:
    configure_fov_output_paths()
    candidate = truefed_candidate(candidate_index)
    original_build_project = fov_gain.builder.build_project

    def limited_build_project(*args: Any, **kwargs: Any):
        kwargs["analysis_cores"] = cores
        kwargs["analysis_tasks"] = tasks
        if center_only:
            kwargs["band_samples"] = False
        return original_build_project(*args, **kwargs)

    fov_gain.builder.build_project = limited_build_project
    try:
        summary, source_rows, coverage_rows = fov_gain.evaluate_candidate(
            candidate_index,
            candidate,
            copy_projects=copy_projects,
            settle_seconds=settle_seconds,
        )
    finally:
        fov_gain.builder.build_project = original_build_project
    fov_gain.write_csv(SUMMARY_CSV, [summary])
    fov_gain.write_csv(SOURCE_CSV, source_rows)
    fov_gain.write_csv(COVERAGE_CSV, coverage_rows)
    payload = {
        "candidate_index": candidate_index,
        "summary": summary,
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
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate-index", type=int, default=37)
    parser.add_argument("--copy-projects", action="store_true")
    parser.add_argument("--settle-seconds", type=float, default=0.0)
    parser.add_argument("--cores", type=int, default=4)
    parser.add_argument("--tasks", type=int, default=4)
    parser.add_argument("--center-only", action="store_true")
    args = parser.parse_args()
    run(args.candidate_index, args.copy_projects, args.settle_seconds, args.cores, args.tasks, args.center_only)


if __name__ == "__main__":
    main()
