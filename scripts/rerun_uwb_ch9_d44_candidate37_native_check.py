from __future__ import annotations

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
STEM = "UWB_CH9_D44_DUALPOL_TRUEFED_L_NATIVE_RERUN"
AEDT_EXE = Path(r"D:\Program Files\AnsysEM\v231\Win64\ansysedt.exe")
NATIVE_EXPORT_SCRIPT = ROOT / "scripts" / "aedt_export_ch9_native_reports.py"
SUMMARY_CSV = REPORT_DIR / f"{STEM}_summary.csv"
METRICS_JSON = REPORT_DIR / f"{STEM}_metrics.json"
REPORT_MD = REPORT_DIR / f"{STEM}_report.md"


def num(value: str) -> float:
    return float(str(value).strip())


def parse_s_term(expr: str) -> tuple[str, str]:
    inside = expr.split("S(", 1)[1].split(")", 1)[0]
    left, right = inside.split(",", 1)
    return left.strip(), right.strip()


def read_sources(path: Path) -> list[str]:
    return [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def parse_s_csv(path: Path, case: workstate.SwitchCase) -> dict[str, Any]:
    with path.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    if not rows:
        raise RuntimeError(f"Empty S-parameter CSV: {path}")
    row = rows[0]
    self_terms: dict[str, float] = {}
    coupling_terms: dict[str, float] = {}
    for key, value in row.items():
        if not key or not key.startswith("dB(S("):
            continue
        expr = key.rsplit(" ", 1)[0] if key.endswith(" []") else key
        left, right = parse_s_term(expr)
        target = self_terms if left == right else coupling_terms
        target[expr] = num(value)
    active_returns = {
        expr: value for expr, value in self_terms.items() if workstate.port_pol(parse_s_term(expr)[0]) == case.active_pol
    }
    low_returns = {expr: value for expr, value in self_terms.items() if workstate.port_pol(parse_s_term(expr)[0]) == "L"}
    worst_active_expr, worst_active_db = max(active_returns.items(), key=lambda item: item[1])
    worst_low_expr, worst_low_db = max(low_returns.items(), key=lambda item: item[1])
    return {
        "s_csv": str(path),
        "self_worst_db": self_terms,
        "coupling_worst_db": coupling_terms,
        "worst_active_s11_expr": worst_active_expr,
        "worst_active_s11_db": worst_active_db,
        "worst_low_s11_expr": worst_low_expr,
        "worst_low_s11_db": worst_low_db,
        "active_s11_pass": worst_active_db <= fov_gain.RETURN_TARGET_DB,
        "low_s11_pass": worst_low_db <= fov_gain.RETURN_TARGET_DB,
    }


def parse_ff_csv(path: Path) -> dict[str, Any]:
    with path.open(newline="", encoding="utf-8-sig") as f:
        rows = list(csv.reader(f))
    if len(rows) < 2:
        raise RuntimeError(f"Empty far-field CSV: {path}")
    header = rows[0]
    phi_idx = next(idx for idx, name in enumerate(header) if name.startswith("Phi"))
    theta_idx = next(idx for idx, name in enumerate(header) if name.startswith("Theta"))
    gain_idx = next(idx for idx, name in enumerate(header) if "dB(GainTotal)" in name)
    realized_idx = next(idx for idx, name in enumerate(header) if "dB(RealizedGainTotal)" in name)
    fov_rows = []
    for raw in rows[1:]:
        if len(raw) <= max(phi_idx, theta_idx, gain_idx, realized_idx):
            continue
        theta = num(raw[theta_idx])
        if fov_gain.THETA_MIN_DEG - 1e-9 <= theta <= fov_gain.THETA_MAX_DEG + 1e-9:
            fov_rows.append(
                {
                    "phi_deg": num(raw[phi_idx]),
                    "theta_deg": theta,
                    "gain_total_dbi": num(raw[gain_idx]),
                    "realized_gain_total_dbi": num(raw[realized_idx]),
                }
            )
    if not fov_rows:
        raise RuntimeError(f"No FOV rows found in {path}")
    min_gain = min(fov_rows, key=lambda row: row["gain_total_dbi"])
    min_realized = min(fov_rows, key=lambda row: row["realized_gain_total_dbi"])
    return {
        "ff_csv": str(path),
        "sample_count": len(fov_rows),
        "default_gain_total_min_dbi": min_gain["gain_total_dbi"],
        "default_gain_total_min_theta_deg": min_gain["theta_deg"],
        "default_gain_total_min_phi_deg": min_gain["phi_deg"],
        "default_realized_gain_total_min_dbi": min_realized["realized_gain_total_dbi"],
        "default_realized_gain_total_min_theta_deg": min_realized["theta_deg"],
        "default_realized_gain_total_min_phi_deg": min_realized["phi_deg"],
        "default_gain_pass": min_gain["gain_total_dbi"] >= fov_gain.GAIN_TARGET_DBI,
        "default_realized_gain_pass": min_realized["realized_gain_total_dbi"] >= fov_gain.GAIN_TARGET_DBI,
    }


def native_export(case: workstate.SwitchCase) -> dict[str, Path]:
    safe_case = fov_gain.safe_slug(case.name)
    env = os.environ.copy()
    env.update(
        {
            "D44_AEDT_CASE": safe_case,
            "D44_AEDT_OUT_DIR": str(REPORT_DIR),
            "D44_AEDT_FREQ_GHZ": "8",
        }
    )
    log_path = REPORT_DIR / f"{safe_case}_native_export.log"
    cmd = [str(AEDT_EXE), "-ng", "-LogFile", str(log_path), "-RunScriptAndExit", str(NATIVE_EXPORT_SCRIPT)]
    subprocess.run(cmd, cwd=str(ROOT), env=env, check=True, timeout=300)
    return {
        "s": REPORT_DIR / f"{safe_case}_native_s_parameters.csv",
        "ff": REPORT_DIR / f"{safe_case}_native_farfield_default.csv",
        "sources": REPORT_DIR / f"{safe_case}_native_sources.txt",
        "log": log_path,
    }


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def write_report(rows: list[dict[str, Any]]) -> None:
    worst_active = max(rows, key=lambda row: row["worst_active_s11_db"])
    worst_low = max(rows, key=lambda row: row["worst_low_s11_db"])
    worst_realized = min(rows, key=lambda row: row["default_realized_gain_total_min_dbi"])
    s11_pass = all(row["active_s11_pass"] and row["low_s11_pass"] for row in rows)
    default_gain_pass = all(row["default_gain_pass"] and row["default_realized_gain_pass"] for row in rows)
    lines = [
        "# D44 candidate 37 原生导出复跑报告",
        "",
        "## 复跑范围",
        "",
        "- 候选：`fold0p6_neck1p6_stub2p6`，true-fed L 低仰角端口。",
        "- 工作态：A_ON 与 B_ON 均重新建模并完成 HFSS 8 GHz 单点求解。",
        "- 导出口径：AEDT 原生命令行 `CreateReport/ExportToFile`，绕开 PyAEDT `get_solution_data` 挂起点。",
        "- 限制：逐源 `EditSources` 在 AEDT 2023.1 非图形脚本和 PyAEDT 中均挂起/中断；本报告复核全端口 S11 与默认激励 far-field，不把逐源覆盖口径标为已完成。",
        "",
        "## 核心指标",
        "",
        f"- 最差工作端口 S11：`{worst_active['worst_active_s11_db']:.3f} dB`，来自 `{worst_active['case']}` / `{worst_active['worst_active_s11_expr']}`。",
        f"- 最差 L 端口 S11：`{worst_low['worst_low_s11_db']:.3f} dB`，来自 `{worst_low['case']}` / `{worst_low['worst_low_s11_expr']}`。",
        f"- 默认激励 FOV 最差 RealizedGainTotal：`{worst_realized['default_realized_gain_total_min_dbi']:.3f} dBi`，来自 `{worst_realized['case']}`，Theta `{worst_realized['default_realized_gain_total_min_theta_deg']:.0f} deg`，Phi `{worst_realized['default_realized_gain_total_min_phi_deg']:.0f} deg`。",
        "",
        "## 达标判断",
        "",
        f"- S11：`{'达标' if s11_pass else '未达标'}`，目标为所有工作端口与 L 端口 `<= -10 dB`。",
        f"- 默认激励增益：`{'达标' if default_gain_pass else '未达标'}`，目标为 FOV 内 `GainTotal/RealizedGainTotal >= -5 dBi`。",
        "- 逐源覆盖增益：`未完成复核`，原因是 AEDT 2023.1 源切换和 PyAEDT 后处理接口挂起；已保留可复现脚本与日志。",
        "",
        "## 输出文件",
        "",
        f"- 汇总 CSV：`{SUMMARY_CSV}`",
        f"- 指标 JSON：`{METRICS_JSON}`",
        f"- 本报告：`{REPORT_MD}`",
    ]
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run() -> dict[str, Any]:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    candidate = truefed_check.truefed_candidate(37)
    rows = []
    cases = [workstate.CASES[0], workstate.CASES[1]]
    for case in cases:
        case_start = time.time()
        print(f"=== Native rerun {case.name} ===", flush=True)
        params = workstate.set_case_params(candidate.params, case)
        builder.TOPOLOGIES[fov_gain.TOPOLOGY]["params"] = params
        builder.build_project(
            fov_gain.TOPOLOGY,
            analyze=True,
            non_graphical=True,
            quick=True,
            band_samples=False,
            sparam_only=False,
            return_hfss=False,
            analysis_cores=1,
            analysis_tasks=1,
        )
        exported = native_export(case)
        s_metrics = parse_s_csv(exported["s"], case)
        ff_metrics = parse_ff_csv(exported["ff"])
        row = {
            "candidate_index": 37,
            "candidate": candidate.name,
            "case": case.name,
            "active_pol": case.active_pol,
            "elapsed_s": time.time() - case_start,
            "sources": ",".join(read_sources(exported["sources"])),
            **s_metrics,
            **ff_metrics,
            "native_export_log": str(exported["log"]),
        }
        rows.append(row)
    write_csv(SUMMARY_CSV, rows)
    payload = {"candidate_index": 37, "candidate": candidate.name, "rows": rows, "summary_csv": str(SUMMARY_CSV), "report_md": str(REPORT_MD)}
    METRICS_JSON.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    write_report(rows)
    print(f"Wrote {REPORT_MD}", flush=True)
    return payload


if __name__ == "__main__":
    run()
