from __future__ import annotations

import argparse
import csv
import json
import os
import subprocess
import time
from pathlib import Path
from typing import Any

import build_uwb_ch9_hfss_d44_topology as builder
import evaluate_uwb_ch9_d44_truefed_l_fov_gain as truefed_check
import optimize_uwb_ch9_d44_dualpol_rf_switch_fov_gain as fov_gain
import simulate_uwb_ch9_d44_dualpol_rf_switch_workstate as workstate


ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = ROOT / "reports_d44_dualpol_truefed_l_fov_gain_check"
STEM = "UWB_CH9_D44_DUALPOL_TRUEFED_L_SINGLE_SOURCE_COVERAGE"
AEDT_EXE = Path(r"D:\Program Files\AnsysEM\v231\Win64\ansysedt.exe")
NATIVE_EXPORT_SCRIPT = ROOT / "scripts" / "aedt_export_ch9_native_reports.py"
NATIVE_RERUN_SUMMARY_CSV = REPORT_DIR / "UWB_CH9_D44_DUALPOL_TRUEFED_L_NATIVE_RERUN_summary.csv"

SUMMARY_CSV = REPORT_DIR / f"{STEM}_summary.csv"
SOURCE_CSV = REPORT_DIR / f"{STEM}_source_summary.csv"
COVERAGE_CSV = REPORT_DIR / f"{STEM}_coverage_summary.csv"
COVERAGE_GRID_CSV = REPORT_DIR / f"{STEM}_coverage_grid.csv"
METRICS_JSON = REPORT_DIR / f"{STEM}_metrics.json"
REPORT_MD = REPORT_DIR / f"{STEM}_report.md"


def num(value: Any, default: float = float("nan")) -> float:
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        return default


def bool_field(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y"}
    return bool(value)


def fmt(value: Any, digits: int = 3) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    return f"{number:.{digits}f}"


def read_sources(path: Path) -> list[str]:
    if not path.exists():
        return []
    return [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def selectable_sources(case: workstate.SwitchCase) -> list[str]:
    sources: list[str] = []
    for idx in range(1, 5):
        sources.append(f"P{idx}{case.active_pol}")
        sources.append(f"P{idx}L")
    return sources


def parse_ff_rows(path: Path) -> tuple[float, list[dict[str, float]]]:
    with path.open(newline="", encoding="utf-8-sig") as f:
        rows = list(csv.reader(f))
    if len(rows) < 2:
        raise RuntimeError(f"Empty far-field CSV: {path}")
    header = rows[0]
    phi_idx = next(idx for idx, name in enumerate(header) if name.startswith("Phi"))
    theta_idx = next(idx for idx, name in enumerate(header) if name.startswith("Theta"))
    freq_idx = next((idx for idx, name in enumerate(header) if name.startswith("Freq")), None)
    gain_idx = next(idx for idx, name in enumerate(header) if "dB(GainTotal)" in name)
    realized_idx = next(idx for idx, name in enumerate(header) if "dB(RealizedGainTotal)" in name)
    freq = num(rows[1][freq_idx], 8.0) if freq_idx is not None else 8.0
    fov_rows: list[dict[str, float]] = []
    for raw in rows[1:]:
        if len(raw) <= max(phi_idx, theta_idx, gain_idx, realized_idx):
            continue
        theta = num(raw[theta_idx])
        if fov_gain.THETA_MIN_DEG - 1e-9 <= theta <= fov_gain.THETA_MAX_DEG + 1e-9:
            fov_rows.append(
                {
                    "theta_deg": theta,
                    "phi_deg": num(raw[phi_idx]),
                    "gain_total_dbi": num(raw[gain_idx]),
                    "realized_gain_total_dbi": num(raw[realized_idx]),
                }
            )
    if not fov_rows:
        raise RuntimeError(f"No FOV rows found in {path}")
    return freq, fov_rows


def parse_selected_return(path: Path, source: str) -> tuple[str, float]:
    with path.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    if not rows:
        return "N/A", float("nan")
    wanted = f"dB(S({source},{source}))"
    row = rows[0]
    for key, value in row.items():
        if key and key.startswith(wanted):
            return key.rsplit(" ", 1)[0], num(value)
    return "N/A", float("nan")


def native_export(case_slug: str) -> dict[str, Path]:
    env = os.environ.copy()
    env.update(
        {
            "D44_AEDT_CASE": case_slug,
            "D44_AEDT_OUT_DIR": str(REPORT_DIR),
            "D44_AEDT_FREQ_GHZ": "8",
        }
    )
    log_path = REPORT_DIR / f"{case_slug}_native_export.log"
    cmd = [str(AEDT_EXE), "-ng", "-LogFile", str(log_path), "-RunScriptAndExit", str(NATIVE_EXPORT_SCRIPT)]
    subprocess.run(cmd, cwd=str(ROOT), env=env, check=True, timeout=420)
    return native_paths(case_slug)


def native_paths(case_slug: str) -> dict[str, Path]:
    return {
        "s": REPORT_DIR / f"{case_slug}_native_s_parameters.csv",
        "ff": REPORT_DIR / f"{case_slug}_native_farfield_default.csv",
        "sources": REPORT_DIR / f"{case_slug}_native_sources.txt",
        "log": REPORT_DIR / f"{case_slug}_native_export.log",
    }


def build_single_source_project(
    candidate: fov_gain.GainCandidate,
    case: workstate.SwitchCase,
    source: str,
    cores: int,
    tasks: int,
) -> Path:
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


def load_full_s11_rows() -> list[dict[str, Any]]:
    if not NATIVE_RERUN_SUMMARY_CSV.exists():
        return []
    with NATIVE_RERUN_SUMMARY_CSV.open(newline="", encoding="utf-8-sig") as f:
        native_rows = list(csv.DictReader(f))
    rows: list[dict[str, Any]] = []
    for row in native_rows:
        active_pass = bool_field(row.get("active_s11_pass"))
        low_pass = bool_field(row.get("low_s11_pass"))
        rows.append(
            {
                "case": row.get("case", ""),
                "worst_return_db": num(row.get("worst_active_s11_db")),
                "worst_return_expr": row.get("worst_active_s11_expr", ""),
                "s11_pass": active_pass and low_pass,
                "worst_low_elevation_s11_db": num(row.get("worst_low_s11_db")),
                "worst_low_elevation_s11_expr": row.get("worst_low_s11_expr", ""),
                "low_elevation_s11_pass": low_pass,
                "low_elevation_port_count": 4,
            }
        )
    return rows


def coverage_grid_rows(candidate_index: int, candidate: fov_gain.GainCandidate, case: workstate.SwitchCase, coverage: dict[tuple[float, float, float], dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for key in sorted(coverage):
        item = coverage[key]
        rows.append(
            {
                "candidate_index": candidate_index,
                "candidate": candidate.name,
                "case": case.name,
                "active_pol": case.active_pol,
                **item,
            }
        )
    return rows


def write_report(payload: dict[str, Any]) -> None:
    summary = payload["summary"]
    expected = payload["expected_source_count"]
    completed = payload["completed_source_count"]
    full = completed == expected
    coverage_ok = bool(summary.get("coverage_gain_target_pass")) and bool(summary.get("coverage_realized_gain_target_pass"))
    s11_ok = bool(summary.get("all_workstate_s11_pass")) and bool(summary.get("all_low_elevation_s11_pass", True))
    strict_ok = bool(summary.get("strict_gain_target_pass")) and bool(summary.get("strict_realized_gain_target_pass"))
    lines = [
        "# D44 candidate 37 逐源覆盖增益复核报告",
        "",
        "## 复核口径",
        "",
        "- 复核对象：`fold0p6_neck1p6_stub2p6`，A_ON/B_ON 两个 absorptive 50 ohm 工作态。",
        "- 复核方法：每个可选源单独重建 HFSS 工程，仅保留该源为 lumped port，其余 A/B/L 源在同位置变为 50 ohm/RLC 端接；随后用 AEDT 原生命令导出默认远场。",
        "- 复核原因：AEDT 2023.1 的 `EditSources`/PyAEDT 后处理在源切换路径仍会挂起或中断；本方法不依赖源切换接口。",
        f"- FOV：Theta `{fov_gain.THETA_MIN_DEG:.0f}..{fov_gain.THETA_MAX_DEG:.0f} deg`，Phi `0..360 deg`，频点 `8 GHz`。",
        f"- 完成源数：`{completed}/{expected}`。",
        "",
        "## 核心指标",
        "",
        f"- 严格逐源最小 GainTotal：`{fmt(summary['strict_fov_gain_total_min_dbi'])} dBi`。",
        f"- 严格逐源最小 RealizedGainTotal：`{fmt(summary['strict_fov_realized_gain_total_min_dbi'])} dBi`。",
        f"- 覆盖口径最小 GainTotal：`{fmt(summary['coverage_fov_gain_total_min_dbi'])} dBi`。",
        f"- 覆盖口径最小 RealizedGainTotal：`{fmt(summary['coverage_fov_realized_gain_total_min_dbi'])} dBi`。",
        f"- 全端口 native 复跑最差工作源 S11：`{fmt(summary['worst_active_s11_db'])} dB`。",
        f"- 全端口 native 复跑最差 L 源 S11：`{fmt(summary.get('worst_low_elevation_s11_db', 'N/A'))} dB`。",
        "",
        "## 达标判断",
        "",
        f"- 严格逐源增益：`{'达标' if strict_ok else '未达标'}`。",
        f"- 端口选择覆盖增益：`{'达标' if coverage_ok else '未达标'}`。",
        f"- S11：`{'达标' if s11_ok else '未达标'}`。",
        f"- 综合结论：`{'达标' if full and coverage_ok and s11_ok else '未完全达标'}`。",
        "",
        "## 最差点",
        "",
        f"- 严格 Realized 最差：`{summary['strict_fov_realized_gain_total_worst_case']}` / `{summary['strict_fov_realized_gain_total_worst_source']}` / "
        f"{fmt(summary['strict_fov_realized_gain_total_worst_freq_ghz'], 4)} GHz / Theta {fmt(summary['strict_fov_realized_gain_total_worst_theta_deg'], 0)} deg / Phi {fmt(summary['strict_fov_realized_gain_total_worst_phi_deg'], 0)} deg。",
        f"- 覆盖 Realized 最差：`{summary['coverage_fov_realized_gain_total_worst_case']}` / best source `{summary['coverage_fov_realized_gain_total_worst_source']}` / "
        f"{fmt(summary['coverage_fov_realized_gain_total_worst_freq_ghz'], 4)} GHz / Theta {fmt(summary['coverage_fov_realized_gain_total_worst_theta_deg'], 0)} deg / Phi {fmt(summary['coverage_fov_realized_gain_total_worst_phi_deg'], 0)} deg。",
        "",
        "## 工程判断",
        "",
    ]
    if not full:
        lines.append("- 本报告为部分复核结果，需补齐剩余单源工程后再作最终达标签核。")
    elif coverage_ok and s11_ok:
        lines.append("- 逐源覆盖和全端口 S11 同时达标；当前结构可进入端口选择策略、开关链路损耗和标定误差预算验证。")
    else:
        lines.append("- 本轮尚未完全达标；若覆盖增益仍不足，下一轮应继续加强真实板边馈电单极子/IFA 的水平面电流，或进一步放宽外形高度给折叠辐射臂。")
    lines.extend(
        [
            "- 当前电脑内存不是本次挂起主因：此前 4 核/4 任务求解完成时内存余量仍约 11 GB，卡点集中在源切换后的后处理接口。",
            "",
            "## 输出文件",
            "",
            f"- 汇总 CSV：`{SUMMARY_CSV}`",
            f"- 逐源 CSV：`{SOURCE_CSV}`",
            f"- 覆盖汇总 CSV：`{COVERAGE_CSV}`",
            f"- 覆盖方向点 CSV：`{COVERAGE_GRID_CSV}`",
            f"- 指标 JSON：`{METRICS_JSON}`",
        ]
    )
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run(candidate_index: int, cores: int, tasks: int, resume: bool, only_sources: set[str] | None) -> dict[str, Any]:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    candidate = truefed_check.truefed_candidate(candidate_index)
    cases = [workstate.CASES[0], workstate.CASES[1]]
    expected_sources = [(case, source) for case in cases for source in selectable_sources(case)]
    if only_sources:
        expected_sources = [(case, source) for case, source in expected_sources if source in only_sources]
    total_expected = len(expected_sources)

    source_rows: list[dict[str, Any]] = []
    coverage_rows: list[dict[str, Any]] = []
    grid_rows: list[dict[str, Any]] = []
    coverage_by_case: dict[str, dict[tuple[float, float, float], dict[str, Any]]] = {case.name: {} for case in cases}
    started = time.time()

    for offset, (case, source) in enumerate(expected_sources, start=1):
        slug = fov_gain.safe_slug(f"{case.name}_{source}_single_source", 96)
        paths = native_paths(slug)
        source_started = time.time()
        if not (resume and paths["ff"].exists() and paths["s"].exists() and paths["sources"].exists()):
            print(f"=== Single-source coverage {offset}/{total_expected}: {case.name} {source} ===", flush=True)
            build_single_source_project(candidate, case, source, cores, tasks)
            paths = native_export(slug)
        else:
            print(f"=== Reusing single-source export {offset}/{total_expected}: {case.name} {source} ===", flush=True)

        exported_sources = read_sources(paths["sources"])
        if exported_sources != [source]:
            raise RuntimeError(f"Expected only source {source} in {paths['sources']}, got {exported_sources}")
        freq, fov_rows = parse_ff_rows(paths["ff"])
        fov_gain.update_coverage(coverage_by_case[case.name], freq, source, fov_rows)
        selected_expr, selected_return_db = parse_selected_return(paths["s"], source)
        source_summary = fov_gain.summarize_source_rows(fov_rows)
        source_summary.update(
            {
                "candidate_index": candidate_index,
                "candidate": candidate.name,
                "case": case.name,
                "active_pol": case.active_pol,
                "source": source,
                "freq_ghz": freq,
                "selected_return_expr": selected_expr,
                "selected_return_db": selected_return_db,
                "elapsed_s": time.time() - source_started,
                "single_source_s_csv": str(paths["s"]),
                "single_source_ff_csv": str(paths["ff"]),
                "single_source_export_log": str(paths["log"]),
            }
        )
        source_rows.append(source_summary)

        coverage_rows = []
        grid_rows = []
        for item_case in cases:
            case_coverage = coverage_by_case[item_case.name]
            if not case_coverage:
                continue
            coverage_summary = fov_gain.summarize_coverage(case_coverage)
            coverage_summary.update(
                {
                    "candidate_index": candidate_index,
                    "candidate": candidate.name,
                    "case": item_case.name,
                    "active_pol": item_case.active_pol,
                }
            )
            coverage_rows.append(coverage_summary)
            grid_rows.extend(coverage_grid_rows(candidate_index, candidate, item_case, case_coverage))
        write_csv(SOURCE_CSV, source_rows)
        write_csv(COVERAGE_CSV, coverage_rows)
        write_csv(COVERAGE_GRID_CSV, grid_rows)

    s11_rows = load_full_s11_rows()
    if not s11_rows:
        raise RuntimeError(f"Missing full-port native S11 summary: {NATIVE_RERUN_SUMMARY_CSV}")
    summary = fov_gain.summarize_candidate(candidate_index, candidate, source_rows, coverage_rows, s11_rows, {}, time.time() - started)
    summary["completed_single_source_count"] = len(source_rows)
    summary["expected_single_source_count"] = total_expected

    write_csv(SUMMARY_CSV, [summary])
    payload = {
        "candidate_index": candidate_index,
        "candidate": candidate.name,
        "summary": summary,
        "completed_source_count": len(source_rows),
        "expected_source_count": total_expected,
        "summary_csv": str(SUMMARY_CSV),
        "source_csv": str(SOURCE_CSV),
        "coverage_csv": str(COVERAGE_CSV),
        "coverage_grid_csv": str(COVERAGE_GRID_CSV),
        "report_md": str(REPORT_MD),
    }
    METRICS_JSON.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    write_report(payload)
    print(json.dumps({"report": str(REPORT_MD), "summary": summary}, indent=2, ensure_ascii=False), flush=True)
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate-index", type=int, default=37)
    parser.add_argument("--cores", type=int, default=4)
    parser.add_argument("--tasks", type=int, default=4)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--sources", default="", help="Comma-separated source subset for a probe run, e.g. P1A,P1L.")
    args = parser.parse_args()
    only_sources = {item.strip() for item in args.sources.split(",") if item.strip()} or None
    run(args.candidate_index, args.cores, args.tasks, args.resume, only_sources)


if __name__ == "__main__":
    main()
