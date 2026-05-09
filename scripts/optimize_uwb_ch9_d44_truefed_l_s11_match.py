from __future__ import annotations

import argparse
import csv
import json
import math
import shutil
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import build_uwb_ch9_hfss_d44_topology as builder
import evaluate_uwb_ch9_d44_topology as topology_eval
import optimize_uwb_ch9_d44_dualpol_rf_switch_fov_gain as fov_opt
import simulate_uwb_ch9_d44_dualpol_rf_switch_workstate as workstate


ROOT = Path(__file__).resolve().parents[1]
TOPOLOGY = "dualpol"
REPORT_DIR = ROOT / "reports_d44_dualpol_truefed_l_match_opt"
STEM = "UWB_CH9_D44_DUALPOL_TRUEFED_L_MATCH"
SUMMARY_CSV = REPORT_DIR / f"{STEM}_summary.csv"
METRICS_JSON = REPORT_DIR / f"{STEM}_metrics.json"
REPORT_MD = REPORT_DIR / f"{STEM}_report.md"
RETURN_TARGET_DB = -10.0


@dataclass(frozen=True)
class MatchCandidate:
    name: str
    params: dict[str, Any]
    rationale: str


def fmt(value: Any, digits: int = 2) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    if math.isnan(number) or math.isinf(number):
        return "N/A"
    return f"{number:.{digits}f}"


def safe_slug(value: str, limit: int = 72) -> str:
    clean = "".join(ch if ch.isalnum() or ch in "-_." else "_" for ch in value)
    return clean[:limit].strip("._-") or "candidate"


def base_truefed_monopole_candidate() -> MatchCandidate:
    for item in fov_opt.candidate_pool():
        if item.name.endswith("_replacewall_fedmono_h4p8_g0p80_w0p24"):
            return MatchCandidate(
                "c61_fedmono_h4p8_g0p80_w0p24",
                dict(item.params),
                "Candidate 61 baseline: true board-edge-fed monopole that passed coverage but failed L-port S11.",
            )
    raise RuntimeError("Cannot locate candidate 61 true-fed monopole baseline")


def clone_candidate(base: MatchCandidate, name: str, rationale: str, **updates: Any) -> MatchCandidate:
    params = dict(base.params)
    params.update(updates)
    return MatchCandidate(name, params, rationale)


def candidates() -> list[MatchCandidate]:
    base = base_truefed_monopole_candidate()
    return [
        base,
        clone_candidate(
            base,
            "stub0p8_open",
            "Add a short open shunt stub at the L-port feed point to test purely distributed capacitive tuning.",
            board_edge_fed_l_match_enabled=1.0,
            board_edge_fed_l_match_stub_length_mm=0.80,
            board_edge_fed_l_match_stub_width_mm=0.18,
            board_edge_fed_l_match_capacitance_pf=0.0,
            board_edge_fed_l_match_inductance_nh=0.0,
        ),
        clone_candidate(
            base,
            "stub1p6_open",
            "Lengthen the open shunt stub to see whether the high-band mismatch is stub-length sensitive.",
            board_edge_fed_l_match_enabled=1.0,
            board_edge_fed_l_match_stub_length_mm=1.60,
            board_edge_fed_l_match_stub_width_mm=0.18,
            board_edge_fed_l_match_capacitance_pf=0.0,
            board_edge_fed_l_match_inductance_nh=0.0,
        ),
        clone_candidate(
            base,
            "stub0p8_c0p08",
            "Add a very small shunt capacitance at the end of a short L-port matching stub.",
            board_edge_fed_l_match_enabled=1.0,
            board_edge_fed_l_match_stub_length_mm=0.80,
            board_edge_fed_l_match_stub_width_mm=0.18,
            board_edge_fed_l_match_capacitance_pf=0.08,
            board_edge_fed_l_match_inductance_nh=0.0,
        ),
        clone_candidate(
            base,
            "stub0p8_c0p16",
            "Double the shunt capacitance to bracket the reactive direction around the L-port mismatch.",
            board_edge_fed_l_match_enabled=1.0,
            board_edge_fed_l_match_stub_length_mm=0.80,
            board_edge_fed_l_match_stub_width_mm=0.18,
            board_edge_fed_l_match_capacitance_pf=0.16,
            board_edge_fed_l_match_inductance_nh=0.0,
        ),
        clone_candidate(
            base,
            "stub1p2_c0p12",
            "Use a slightly longer stub with middle capacitance as the first compact L-match point.",
            board_edge_fed_l_match_enabled=1.0,
            board_edge_fed_l_match_stub_length_mm=1.20,
            board_edge_fed_l_match_stub_width_mm=0.18,
            board_edge_fed_l_match_capacitance_pf=0.12,
            board_edge_fed_l_match_inductance_nh=0.0,
        ),
        clone_candidate(
            base,
            "stub0p8_l0p6",
            "Test a shunt inductive compensation direction at the L-port feed.",
            board_edge_fed_l_match_enabled=1.0,
            board_edge_fed_l_match_stub_length_mm=0.80,
            board_edge_fed_l_match_stub_width_mm=0.18,
            board_edge_fed_l_match_capacitance_pf=0.0,
            board_edge_fed_l_match_inductance_nh=0.60,
        ),
        clone_candidate(
            base,
            "stub0p8_l1p0",
            "Increase the shunt inductance to bracket the inductive L-match direction.",
            board_edge_fed_l_match_enabled=1.0,
            board_edge_fed_l_match_stub_length_mm=0.80,
            board_edge_fed_l_match_stub_width_mm=0.18,
            board_edge_fed_l_match_capacitance_pf=0.0,
            board_edge_fed_l_match_inductance_nh=1.00,
        ),
        clone_candidate(
            base,
            "top2p4_stub0p8_c0p12",
            "Combine a longer monopole top load with the compact shunt-capacitive L-match point.",
            board_edge_fed_monopole_offset_mm=-1.20,
            board_edge_fed_monopole_topload_length_mm=2.40,
            board_edge_fed_l_match_enabled=1.0,
            board_edge_fed_l_match_stub_length_mm=0.80,
            board_edge_fed_l_match_stub_width_mm=0.18,
            board_edge_fed_l_match_capacitance_pf=0.12,
            board_edge_fed_l_match_inductance_nh=0.0,
        ),
    ]


def low_elevation_return_terms(sparams: dict[str, Any]) -> dict[str, float]:
    returns: dict[str, float] = {}
    for expr, value in sparams.get("self_worst_db", {}).items():
        try:
            left, _ = topology_eval.parse_s_term(expr)
        except (IndexError, ValueError):
            continue
        if workstate.port_pol(left) == "L":
            returns[expr] = float(value)
    return returns


def summarize_case(
    candidate_index: int,
    candidate: MatchCandidate,
    case: workstate.SwitchCase,
    sparams: dict[str, Any],
    elapsed_s: float,
) -> dict[str, Any]:
    selected = workstate.summarize_case(case, sparams, elapsed_s)
    l_returns = low_elevation_return_terms(sparams)
    worst_l_expr, worst_l_db = max(l_returns.items(), key=lambda item: item[1])
    worst_return_db = max(float(selected["worst_return_db"]), worst_l_db)
    worst_return_expr = worst_l_expr if worst_l_db >= float(selected["worst_return_db"]) else selected["worst_return_expr"]
    return {
        "candidate_index": candidate_index,
        "candidate": candidate.name,
        "rationale": candidate.rationale,
        "case": case.name,
        "active_pol": case.active_pol,
        "elapsed_s": elapsed_s,
        "selected_path_worst_return_db": selected["worst_return_db"],
        "selected_path_worst_return_expr": selected["worst_return_expr"],
        "low_elevation_port_count": len(l_returns),
        "worst_low_elevation_s11_db": worst_l_db,
        "worst_low_elevation_s11_expr": worst_l_expr,
        "worst_return_db": worst_return_db,
        "worst_return_expr": worst_return_expr,
        "s11_pass": worst_return_db <= RETURN_TARGET_DB,
    }


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
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
        for row in rows:
            writer.writerow({key: f"{row[key]:.6f}" if isinstance(row.get(key), float) else row.get(key, "") for key in fields})


def read_csv(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def numeric(row: dict[str, Any], key: str, default: float = 0.0) -> float:
    try:
        return float(row.get(key, default))
    except (TypeError, ValueError):
        return default


def summarize_candidate_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault(str(row["candidate"]), []).append(row)
    summaries = []
    for candidate, items in grouped.items():
        worst = max(items, key=lambda row: numeric(row, "worst_return_db", 1e9))
        worst_l = max(items, key=lambda row: numeric(row, "worst_low_elevation_s11_db", 1e9))
        summaries.append(
            {
                "candidate_index": items[0]["candidate_index"],
                "candidate": candidate,
                "rationale": items[0].get("rationale", ""),
                "worst_return_db": numeric(worst, "worst_return_db"),
                "worst_return_expr": worst.get("worst_return_expr", ""),
                "worst_return_case": worst.get("case", ""),
                "worst_low_elevation_s11_db": numeric(worst_l, "worst_low_elevation_s11_db"),
                "worst_low_elevation_s11_expr": worst_l.get("worst_low_elevation_s11_expr", ""),
                "worst_low_elevation_s11_case": worst_l.get("case", ""),
                "all_s11_pass": all(str(row.get("s11_pass", "")).lower() == "true" or row.get("s11_pass") is True for row in items),
            }
        )
    return sorted(summaries, key=lambda row: (row["worst_return_db"] > RETURN_TARGET_DB, row["worst_return_db"]))


def existing_project_copies(candidate_summary: dict[str, Any]) -> dict[str, str]:
    projects: dict[str, str] = {}
    candidate_index = int(float(candidate_summary["candidate_index"]))
    slug = safe_slug(str(candidate_summary["candidate"]))
    for case in workstate.CASES[:2]:
        path = REPORT_DIR / f"{STEM}_{candidate_index:02d}_{slug}_{case.name}.aedt"
        if path.exists():
            projects[case.name] = str(path)
    return projects


def evaluate_candidate(
    candidate_index: int,
    candidate: MatchCandidate,
    copy_projects: bool,
    settle_seconds: float,
) -> tuple[list[dict[str, Any]], dict[str, str]]:
    print(f"=== L-match candidate {candidate_index}: {candidate.name} ===", flush=True)
    rows: list[dict[str, Any]] = []
    projects: dict[str, str] = {}
    for case in workstate.CASES[:2]:
        started = time.time()
        params = workstate.set_case_params(candidate.params, case)
        builder.TOPOLOGIES[TOPOLOGY]["params"] = params
        project_path, hfss = builder.build_project(
            TOPOLOGY,
            analyze=True,
            non_graphical=True,
            quick=True,
            band_samples=True,
            sparam_only=True,
            return_hfss=True,
            analysis_cores=8,
            analysis_tasks=8,
        )
        try:
            sparams = topology_eval.get_s_parameter_snapshot(
                hfss,
                REPORT_DIR / f"{STEM}_{candidate_index:02d}_{safe_slug(candidate.name)}_{case.name}_s_parameters.csv",
            )
        finally:
            hfss.release_desktop(close_projects=False, close_desktop=True)
        row = summarize_case(candidate_index, candidate, case, sparams, time.time() - started)
        rows.append(row)
        if copy_projects:
            copy_path = REPORT_DIR / f"{STEM}_{candidate_index:02d}_{safe_slug(candidate.name)}_{case.name}.aedt"
            shutil.copy2(project_path, copy_path)
            projects[case.name] = str(copy_path)
        if settle_seconds > 0:
            print(f"Stage: AEDT settle wait {settle_seconds:.1f}s", flush=True)
            time.sleep(settle_seconds)
    candidate_summary = summarize_candidate_rows(rows)[0]
    print(
        json.dumps(
            {
                "candidate": candidate.name,
                "worst_return_db": candidate_summary["worst_return_db"],
                "worst_low_elevation_s11_db": candidate_summary["worst_low_elevation_s11_db"],
                "all_s11_pass": candidate_summary["all_s11_pass"],
            },
            indent=2,
            ensure_ascii=False,
        ),
        flush=True,
    )
    return rows, projects


def write_report(payload: dict[str, Any]) -> None:
    ranked = payload["candidate_summaries"]
    best = ranked[0]
    lines = [
        "# D44 真实馈电 L 端口匹配小扫报告",
        "",
        "## 目标",
        "",
        f"- 基线：候选 61 真实板边馈电单极子，覆盖口径 RealizedGainTotal 最差值已达到 -0.58 dBi，但 L 端口最差 S11 仅约 -4.14 dB。",
        f"- 本轮只做 s-parameter-only 小扫，目标是把 `P1L..P4L` 与选通 A/B 路径的最差回波推向 `{RETURN_TARGET_DB:.1f} dB`。",
        "- 新增结构：每个 L 端口馈点附近可选短 shunt stub，并可在 stub 端加入无损并联 C/L 作为一阶匹配网络模型。",
        "",
        "## 排名",
        "",
        "| 排名 | 候选 | 最差总回波 | 最差 L 端口回波 | 最差项 | 达标 |",
        "| ---: | --- | ---: | ---: | --- | --- |",
    ]
    for idx, row in enumerate(ranked, start=1):
        lines.append(
            f"| {idx} | `{row['candidate']}` | {fmt(row['worst_return_db'])} dB | "
            f"{fmt(row['worst_low_elevation_s11_db'])} dB | `{row['worst_return_expr']}` / `{row['worst_return_case']}` | "
            f"{'是' if row['all_s11_pass'] else '否'} |"
        )
    lines.extend(
        [
            "",
            "## 当前结论",
            "",
            f"- 本轮最佳候选：`{best['candidate']}`，最差总回波 `{fmt(best['worst_return_db'])} dB`，最差 L 端口回波 `{fmt(best['worst_low_elevation_s11_db'])} dB`。",
        ]
    )
    if best["all_s11_pass"]:
        lines.append("- 匹配目标已达成，下一步应回到完整 FOV 远场，确认 L-match 没有明显牺牲覆盖口径 RealizedGainTotal。")
    else:
        lines.append("- 匹配目标仍未达成；如果无损 shunt C/L 方向不能改善，下一轮应改为串联 feed neck/微带 L-match，或通过端口位置/单极子电长度重构输入阻抗。")
    lines.extend(
        [
            "",
            "## 输出文件",
            "",
            f"- 汇总 CSV：`{SUMMARY_CSV}`",
            f"- 指标 JSON：`{METRICS_JSON}`",
        ]
    )
    for case, path in payload.get("best_projects", {}).items():
        lines.append(f"- 最佳 `{case}` AEDT 快照：`{path}`")
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run(max_candidates: int, start_index: int, resume: bool, copy_projects: bool, settle_seconds: float) -> dict[str, Any]:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    pool = candidates()[:max_candidates]
    rows = read_csv(SUMMARY_CSV) if resume else []
    projects_by_candidate: dict[str, dict[str, str]] = {}
    completed = {int(float(row["candidate_index"])) for row in rows if row.get("candidate_index")}
    for idx, candidate in enumerate(pool, start=1):
        if idx < start_index:
            continue
        if idx in completed:
            print(f"Stage: L-match candidate {idx} {candidate.name} reused", flush=True)
            continue
        candidate_rows, projects = evaluate_candidate(idx, candidate, copy_projects, settle_seconds)
        rows.extend(candidate_rows)
        projects_by_candidate[candidate.name] = projects
        write_csv(SUMMARY_CSV, rows)
    candidate_summaries = summarize_candidate_rows(rows)
    best_projects = projects_by_candidate.get(candidate_summaries[0]["candidate"], {}) or existing_project_copies(candidate_summaries[0])
    payload = {
        "return_target_db": RETURN_TARGET_DB,
        "candidate_count": len(pool),
        "summary_rows": rows,
        "candidate_summaries": candidate_summaries,
        "best_projects": best_projects,
        "summary_csv": str(SUMMARY_CSV),
        "report_md": str(REPORT_MD),
    }
    METRICS_JSON.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    write_report(payload)
    print(f"Wrote {REPORT_MD}", flush=True)
    return payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-candidates", type=int, default=6)
    parser.add_argument("--start-index", type=int, default=1)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--copy-projects", action="store_true")
    parser.add_argument("--settle-seconds", type=float, default=5.0)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run(args.max_candidates, args.start_index, args.resume, args.copy_projects, args.settle_seconds)


if __name__ == "__main__":
    main()
