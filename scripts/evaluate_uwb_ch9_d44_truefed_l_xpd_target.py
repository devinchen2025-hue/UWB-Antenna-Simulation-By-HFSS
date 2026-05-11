from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any

import evaluate_uwb_ch9_d44_truefed_l_fov_gain as truefed_check
import rerun_uwb_ch9_d44_candidate37_polarization_phase as pol
import simulate_uwb_ch9_d44_dualpol_rf_switch_workstate as workstate


ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = ROOT / "reports_d44_dualpol_truefed_l_xpd_target"
FIELD_DIR = REPORT_DIR / "native_fields"
STEM = "UWB_CH9_D44_DUALPOL_TRUEFED_L_XPD_TARGET"

SUMMARY_CSV = REPORT_DIR / f"{STEM}_summary.csv"
METRICS_JSON = REPORT_DIR / f"{STEM}_metrics.json"
REPORT_MD = REPORT_DIR / f"{STEM}_report.md"


def fmt(value: Any, digits: int = 3) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    return f"{number:.{digits}f}"


def configure_phase_paths() -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    FIELD_DIR.mkdir(parents=True, exist_ok=True)
    pol.REPORT_DIR = REPORT_DIR
    pol.FIELD_DIR = FIELD_DIR


def sources_for_group(case: workstate.SwitchCase, source_group: str) -> list[str]:
    active_ab = pol.selectable_sources(case)
    l_sources = [f"P{idx}L" for idx in range(1, 5)]
    if source_group == "ab":
        return active_ab
    if source_group == "l":
        return l_sources
    if source_group == "all":
        return active_ab + l_sources
    raise ValueError(f"Unknown source group: {source_group}")


def native_paths(slug: str) -> dict[str, Path]:
    return {
        "field": FIELD_DIR / f"{slug}_native_field_components.csv",
        "sources": FIELD_DIR / f"{slug}_native_sources.txt",
        "log": FIELD_DIR / f"{slug}_native_field_export.log",
    }


def evaluate_candidate(candidate_index: int, source_group: str, cores: int, tasks: int, resume: bool) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    candidate = truefed_check.truefed_candidate(candidate_index)
    cases = [workstate.CASES[0], workstate.CASES[1]]
    source_rows: list[dict[str, Any]] = []
    sample_rows: list[dict[str, Any]] = []
    try:
        for case in cases:
            fields_by_source: dict[str, dict[tuple[float, float], pol.FieldPoint]] = {}
            for source in sources_for_group(case, source_group):
                slug = pol.safe_slug(f"c{candidate_index:02d}_{source_group}_{case.name}_{source}_field", 120)
                paths = native_paths(slug)
                if not (resume and paths["field"].exists() and paths["sources"].exists()):
                    print(f"=== XPD field export c{candidate_index} {source_group} {case.name} {source} ===", flush=True)
                    pol.build_single_source_project(candidate, case, source, cores, tasks)
                    original_native_paths = pol.native_paths
                    pol.native_paths = native_paths
                    try:
                        paths = pol.native_export_fields(slug)
                    finally:
                        pol.native_paths = original_native_paths
                else:
                    print(f"=== Reusing XPD field export c{candidate_index} {source_group} {case.name} {source} ===", flush=True)
                exported_sources = pol.read_sources(paths["sources"])
                if exported_sources != [source]:
                    raise RuntimeError(f"Expected only source {source} in {paths['sources']}, got {exported_sources}")
                fields_by_source[source] = pol.parse_field_csv(paths["field"])
            case_rows, case_samples = pol.evaluate_xpd_case(case, fields_by_source)
            for row in case_rows:
                row.update({"candidate_index": candidate_index, "candidate": candidate.name, "source_group": source_group})
            for row in case_samples:
                row.update({"candidate_index": candidate_index, "candidate": candidate.name, "source_group": source_group})
            source_rows.extend(case_rows)
            sample_rows.extend(case_samples)
    finally:
        print("=== Restoring full B_ON project ===", flush=True)
        pol.restore_full_project(candidate, cases[-1])
    aggregate_rows = pol.aggregate_xpd_samples(sample_rows)
    for row in aggregate_rows:
        row.update({"candidate_index": candidate_index, "candidate": candidate.name, "source_group": source_group})
    return source_rows, aggregate_rows


def rank_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        rows,
        key=lambda row: (
            0 if str(row.get("level")) == "aggregate" and str(row.get("case")) == "ALL_CASES" else 1,
            -float(row.get("xpd_min_db", -999.0)),
        ),
    )


def write_report(payload: dict[str, Any]) -> None:
    rows = rank_rows(payload["rows"])
    best = rows[0]
    lines = [
        "# D44 true-fed L 交叉极化抑制比目标评估",
        "",
        "## 目标",
        "",
        f"- XPD 目标：Theta `{pol.THETA_MIN_DEG:.0f}..{pol.THETA_MAX_DEG:.0f} deg`，`0 deg/Etheta` 为主极化、`90 deg/Ephi` 为交叉极化，最小 XPD `>= {pol.XPD_TARGET_DB:.1f} dB`。",
        f"- 候选编号：`{payload['candidate_indices']}`；源组：`{payload['source_group']}`。",
        "",
        "## 最优汇总",
        "",
        f"- 当前排序首项：candidate `{best['candidate_index']}` / `{best['candidate']}` / `{best['case']}`。",
        f"- 最小 XPD：`{fmt(best['xpd_min_db'])} dB`，距离目标 `{fmt(best['xpd_margin_to_target_db'])} dB`。",
        f"- 结论：`{'达标' if best['xpd_target_pass'] else '未达标'}`。",
        "",
        "## 结果表",
        "",
        "| 候选 | 源组 | 范围 | 源 | 样本数 | 最小XPD | P5 XPD | 中位XPD | 平均XPD | 最差Theta | 最差Phi | 是否达标 |",
        "| ---: | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['candidate_index']} | `{row['source_group']}` | `{row['case']}` | `{row['source']}` | "
            f"{int(row['xpd_sample_count'])} | {fmt(row['xpd_min_db'])} dB | {fmt(row['xpd_p5_db'])} dB | "
            f"{fmt(row['xpd_median_db'])} dB | {fmt(row['xpd_avg_db'])} dB | "
            f"{fmt(row.get('xpd_worst_theta_deg', 0.0), 0)} deg | {fmt(row.get('xpd_worst_phi_deg', 0.0), 0)} deg | "
            f"{'是' if row['xpd_target_pass'] else '否'} |"
        )
    lines.extend(
        [
            "",
            "## 输出文件",
            "",
            f"- CSV：`{SUMMARY_CSV}`",
            f"- JSON：`{METRICS_JSON}`",
        ]
    )
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run(candidate_indices: list[int], source_group: str, cores: int, tasks: int, resume: bool) -> dict[str, Any]:
    configure_phase_paths()
    started = time.time()
    rows: list[dict[str, Any]] = []
    for candidate_index in candidate_indices:
        source_rows, aggregate_rows = evaluate_candidate(candidate_index, source_group, cores, tasks, resume)
        rows.extend(source_rows)
        rows.extend(aggregate_rows)
        pol.write_csv(SUMMARY_CSV, rows)
    payload = {
        "candidate_indices": candidate_indices,
        "source_group": source_group,
        "xpd_target_db": pol.XPD_TARGET_DB,
        "xpd_co_pol_deg": pol.XPD_CO_POL_DEG,
        "xpd_cross_pol_deg": pol.XPD_CROSS_POL_DEG,
        "elapsed_s": time.time() - started,
        "rows": rows,
        "summary_csv": str(SUMMARY_CSV),
        "report_md": str(REPORT_MD),
    }
    METRICS_JSON.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    write_report(payload)
    print(json.dumps({"report": str(REPORT_MD), "summary_csv": str(SUMMARY_CSV)}, indent=2, ensure_ascii=False), flush=True)
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate-index", action="append", type=int, default=[])
    parser.add_argument("--source-group", choices=["ab", "l", "all"], default="l")
    parser.add_argument("--cores", type=int, default=8)
    parser.add_argument("--tasks", type=int, default=8)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    run(args.candidate_index or [37], args.source_group, args.cores, args.tasks, args.resume)


if __name__ == "__main__":
    main()
