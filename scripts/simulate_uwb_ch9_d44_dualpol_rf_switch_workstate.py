from __future__ import annotations

import csv
import json
import shutil
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import build_uwb_ch9_hfss_d44_topology as builder
import evaluate_uwb_ch9_d44_topology as topology_eval
import optimize_uwb_ch9_d44_dualpol_s11_slotcoupled_match as s11_opt


ROOT = Path(__file__).resolve().parents[1]
TOPOLOGY = "dualpol"
SOLUTION = "Setup_CH9 : Sweep_CH9"
REPORT_DIR = ROOT / "reports_d44_dualpol_rf_switch_workstate"
STEM = "UWB_CH9_D44_DUALPOL_RF_SWITCH"
BEST_SOURCE_JSON = ROOT / "reports_d44_dualpol_s11_slotmatch_opt" / "UWB_CH9_D44_DUALPOL_S11_SLOTMATCH_best.json"
METRICS_JSON = REPORT_DIR / f"{STEM}_workstate_metrics.json"
SUMMARY_CSV = REPORT_DIR / f"{STEM}_workstate_summary.csv"
REPORT_MD = REPORT_DIR / f"{STEM}_workstate_report.md"

RETURN_TARGET_DB = -10.0


@dataclass(frozen=True)
class SwitchCase:
    name: str
    active_pol: str
    off_resistance_ohm: float
    off_capacitance_pf: float
    off_inductance_nh: float = 0.0


CASES = [
    SwitchCase("A_ON_absorptive_50ohm_c0p08pf", "A", 50.0, 0.08),
    SwitchCase("B_ON_absorptive_50ohm_c0p08pf", "B", 50.0, 0.08),
    SwitchCase("A_ON_reflective_5kohm_c0p08pf", "A", 5000.0, 0.08),
    SwitchCase("B_ON_reflective_5kohm_c0p08pf", "B", 5000.0, 0.08),
]


def read_best_candidate_name() -> str:
    payload = json.loads(BEST_SOURCE_JSON.read_text(encoding="utf-8"))
    best = payload.get("best_candidate") or payload.get("best") or {}
    name = best.get("candidate")
    if not name:
        raise RuntimeError(f"Cannot locate best candidate name in {BEST_SOURCE_JSON}")
    return str(name)


def best_candidate_params() -> tuple[str, dict[str, Any]]:
    best_name = read_best_candidate_name()
    for candidate in s11_opt.candidates():
        if candidate.name == best_name:
            params = dict(candidate.params)
            return best_name, params
    raise RuntimeError(f"Best candidate {best_name} is not present in optimizer candidate list")


def set_case_params(base_params: dict[str, Any], case: SwitchCase) -> dict[str, Any]:
    params = dict(base_params)
    params.update(
        {
            "rf_switch_equiv_enabled": 1.0,
            "rf_switch_active_pol": 0.0 if case.active_pol == "A" else 1.0,
            "rf_switch_off_resistance_ohm": case.off_resistance_ohm,
            "rf_switch_off_capacitance_pf": case.off_capacitance_pf,
            "rf_switch_off_inductance_nh": case.off_inductance_nh,
        }
    )
    return params


def active_port_prefix(case: SwitchCase) -> str:
    return case.active_pol


def port_pol(port: str) -> str:
    return port.split(":", 1)[0][-1]


def summarize_case(case: SwitchCase, sparams: dict[str, Any], elapsed_s: float) -> dict[str, Any]:
    active = active_port_prefix(case)
    returns = {
        expr: value
        for expr, value in sparams["self_worst_db"].items()
        if port_pol(expr.split("S(", 1)[1].split(",", 1)[0].strip()) == active
    }
    couplings = {}
    for expr, value in sparams.get("coupling_worst_db", {}).items():
        inside = expr.split("S(", 1)[1].split(")", 1)[0]
        left, right = [part.strip() for part in inside.split(",", 1)]
        if port_pol(left) == active and port_pol(right) == active:
            couplings[expr] = value
    worst_return_expr, worst_return_db = max(returns.items(), key=lambda item: item[1])
    if couplings:
        worst_coupling_expr, worst_coupling_db = max(couplings.items(), key=lambda item: item[1])
        active_interelement_isolation_db = -worst_coupling_db
    else:
        worst_coupling_expr = "N/A"
        active_interelement_isolation_db = float("nan")
    return {
        "case": case.name,
        "active_pol": case.active_pol,
        "off_resistance_ohm": case.off_resistance_ohm,
        "off_capacitance_pf": case.off_capacitance_pf,
        "off_inductance_nh": case.off_inductance_nh,
        "elapsed_s": elapsed_s,
        "active_port_count": len(returns),
        "worst_return_db": worst_return_db,
        "worst_return_expr": worst_return_expr,
        "active_interelement_isolation_db": active_interelement_isolation_db,
        "worst_active_coupling_expr": worst_coupling_expr,
        "s11_pass": worst_return_db <= RETURN_TARGET_DB,
    }


def write_summary_csv(rows: list[dict[str, Any]]) -> None:
    SUMMARY_CSV.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "case",
        "active_pol",
        "off_resistance_ohm",
        "off_capacitance_pf",
        "off_inductance_nh",
        "elapsed_s",
        "active_port_count",
        "worst_return_db",
        "worst_return_expr",
        "active_interelement_isolation_db",
        "worst_active_coupling_expr",
        "s11_pass",
    ]
    with SUMMARY_CSV.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: f"{row[key]:.6f}" if isinstance(row.get(key), float) else row.get(key, "") for key in fields})


def write_report(best_name: str, rows: list[dict[str, Any]], project_copies: dict[str, str]) -> None:
    sorted_rows = sorted(rows, key=lambda row: (not row["s11_pass"], row["worst_return_db"]))
    lines = [
        "# UWB CH9 D44 双极化 RF Switch 工作态仿真报告",
        "",
        "## 仿真目标",
        "",
        "- 将同阵元 A/B 双极化改为 RF switch 分时单通道工作态：选通极化保留为 HFSS lumped port，未选中极化替换为 RF switch off 状态等效 RLC 负载。",
        f"- 基线结构来自当前最佳 S11 候选：`{best_name}`。",
        f"- 工作态 S11 目标：选通极化端口在 7.738-8.233 GHz 内最差 S11 <= {RETURN_TARGET_DB:.1f} dB。",
        "- 本轮不再把裸 A/B 同时端口隔离作为主指标，而是观察选通态 S11 与同极化跨阵元耦合。",
        "",
        "## RF Switch 等效模型",
        "",
        "- 吸收式 off 端：未选中端口用 `50 ohm // 0.08 pF` 并联负载近似，代表开关或外部终端能把未选端稳定吸收。",
        "- 反射式 off 端：未选中端口用 `5 kohm // 0.08 pF` 并联负载近似，代表未选端接近高阻但存在 off 电容。",
        "- 选通路径未单独加入插损；HFSS 端口仍按 50 ohm 归一化，开关 on 插损应在链路预算中另加。",
        "",
        "## 结果汇总",
        "",
        "| 排名 | 工作态 | Off 等效 | 最差 S11 | S11 达标 | 同极化跨阵元隔离 | 最差回波项 |",
        "| ---: | --- | --- | ---: | --- | ---: | --- |",
    ]
    for rank, row in enumerate(sorted_rows, start=1):
        off_model = f"{row['off_resistance_ohm']:.0f} ohm // {row['off_capacitance_pf']:.2f} pF"
        lines.append(
            f"| {rank} | `{row['case']}` | {off_model} | {row['worst_return_db']:.2f} dB | "
            f"{'是' if row['s11_pass'] else '否'} | {row['active_interelement_isolation_db']:.2f} dB | `{row['worst_return_expr']}` |"
        )
    worst_pass = all(row["s11_pass"] for row in rows)
    lines.extend(
        [
            "",
            "## 结论",
            "",
            f"- 工作态整体 S11 {'全部达标' if worst_pass else '未全部达标'}。",
            "- 如果实际 RF switch 是吸收式或外部给未选端提供稳定 50 ohm 终端，则应优先采用吸收式结果作为工程判断。",
            "- 如果实际 RF switch 是反射式高阻 off 端，则未选极化会作为寄生加载参与辐射，应以反射式结果作为更保守判断。",
            "- 后续若拿到具体开关型号，应把 datasheet 的 off capacitance、off resistance/termination、on resistance 和封装寄生更新到本脚本后重跑。",
            "",
            "## 输出文件",
            "",
            f"- 汇总 CSV: `{SUMMARY_CSV}`",
            f"- 指标 JSON: `{METRICS_JSON}`",
        ]
    )
    for case_name, path in project_copies.items():
        lines.append(f"- `{case_name}` AEDT 快照: `{path}`")
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run() -> dict[str, Any]:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    best_name, base_candidate_params = best_candidate_params()
    rows: list[dict[str, Any]] = []
    project_copies: dict[str, str] = {}
    for case in CASES:
        started = time.time()
        params = set_case_params(base_candidate_params, case)
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
            sparams = topology_eval.get_s_parameter_snapshot(hfss, REPORT_DIR / f"{STEM}_{case.name}_s_parameters.csv")
        finally:
            hfss.release_desktop(close_projects=False, close_desktop=True)
        elapsed_s = time.time() - started
        row = summarize_case(case, sparams, elapsed_s)
        rows.append(row)
        copy_path = REPORT_DIR / f"{STEM}_{case.name}.aedt"
        shutil.copy2(project_path, copy_path)
        project_copies[case.name] = str(copy_path)
        print(json.dumps(row, indent=2, ensure_ascii=False), flush=True)

    payload = {
        "best_candidate": best_name,
        "return_target_db": RETURN_TARGET_DB,
        "cases": rows,
        "project_copies": project_copies,
        "assumptions": {
            "selected_path": "Selected polarization remains a 50 ohm normalized HFSS lumped port; switch on insertion loss is not embedded.",
            "inactive_path": "Inactive polarization is replaced by a parallel RLC sheet at the former feed port location.",
        },
    }
    METRICS_JSON.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    write_summary_csv(rows)
    write_report(best_name, rows, project_copies)
    print(f"Wrote {REPORT_MD}", flush=True)
    return payload


def main() -> None:
    run()


if __name__ == "__main__":
    main()
