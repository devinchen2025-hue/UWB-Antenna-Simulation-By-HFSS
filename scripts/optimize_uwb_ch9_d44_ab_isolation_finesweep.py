from __future__ import annotations

import argparse
import csv
import json
import math
import shutil
from pathlib import Path
from typing import Any

import build_uwb_ch9_hfss_d44_topology as builder
import optimize_uwb_ch9_d44_geometry_pdoa_stability as geom


ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = ROOT / "reports_d44_ab_isolation_finesweep"
SPARAM_CSV = REPORT_DIR / "UWB_CH9_D44_AB_ISOLATION_finesweep_sparam_screening.csv"
FULL_CSV = REPORT_DIR / "UWB_CH9_D44_AB_ISOLATION_finesweep_full_validation.csv"
SOURCE_SWEEP_CSV = REPORT_DIR / "UWB_CH9_D44_AB_ISOLATION_finesweep_best_source_sweep.csv"
BEST_CURVES_CSV = REPORT_DIR / "UWB_CH9_D44_AB_ISOLATION_finesweep_best_curves.csv"
BEST_JSON = REPORT_DIR / "UWB_CH9_D44_AB_ISOLATION_finesweep_best.json"
REPORT_MD = REPORT_DIR / "UWB_CH9_D44_AB_ISOLATION_finesweep_report.md"
PREVIOUS_BEST_JSON = ROOT / "reports_d44_geometry_pdoa_opt" / "UWB_CH9_D44_GEOMETRY_PDOA_best.json"

TOPOLOGY = "dualfeed"

RETURN_TARGET_DB = geom.RETURN_TARGET_DB
ISOLATION_TARGET_DB = geom.ISOLATION_TARGET_DB
GAIN_TARGET_DBI = geom.GAIN_TARGET_DBI
AR_TARGET_DB = geom.AR_TARGET_DB
PDOA_RMS_TARGET_DEG = geom.PDOA_RMS_TARGET_DEG
PDOA_MAX_TARGET_DEG = geom.PDOA_MAX_TARGET_DEG

BASE_PARAMS: dict[str, Any] = dict(builder.TOPOLOGIES[TOPOLOGY]["params"])
BASE_PARAMS.update(
    {
        "patch_side_mm": 9.15,
        "corner_cut_mm": 0.0,
        "feed_offset_u_mm": 3.30,
        "feed_offset_v_mm": 0.0,
        "feed_pad_radius_mm": 0.34,
        "port_width_mm": 0.55,
        "microstrip_feed_enabled": 0.0,
        "neutralization_branch_enabled": 0.0,
        "local_dgs_enabled": 0.0,
        "weak_coupling_open_line_enabled": 0.0,
        "weak_coupling_open_line_length_mm": 2.20,
        "weak_coupling_open_line_width_mm": 0.12,
        "weak_coupling_open_line_offset_mm": 1.65,
        "weak_coupling_open_line_gap_mm": 0.08,
        "via_fence_enabled": 0.0,
        "via_fence_count": 3.0,
        "via_fence_radius_mm": 0.10,
        "via_fence_pitch_mm": 0.55,
        "via_fence_edge_offset_mm": 0.45,
        "via_fence_center_mm": 3.30,
        "isolation_slot_enabled": 1.0,
        "isolation_slot_length_mm": 10.0,
        "isolation_slot_width_mm": 0.42,
        "isolation_slot_inner_mm": 3.20,
    }
)


def configure_geom_paths() -> None:
    geom.REPORT_DIR = REPORT_DIR
    geom.SPARAM_CSV = SPARAM_CSV
    geom.FULL_CSV = FULL_CSV
    geom.SOURCE_SWEEP_CSV = SOURCE_SWEEP_CSV
    geom.BEST_CURVES_CSV = BEST_CURVES_CSV
    geom.BEST_JSON = BEST_JSON
    geom.REPORT_MD = REPORT_MD


def fmt(value: float | int | None, digits: int = 2) -> str:
    return geom.fmt(value, digits)


def token(value: float) -> str:
    return f"{value:.2f}".replace(".", "p")


def candidate(name: str, rationale: str, **overrides: float) -> geom.GeometryCandidate:
    params = dict(BASE_PARAMS)
    params.update(overrides)
    return geom.GeometryCandidate(name=name, params=params, rationale=rationale)


def validate_candidates(raw: list[geom.GeometryCandidate]) -> list[geom.GeometryCandidate]:
    valid = []
    seen = set()
    for item in raw:
        if item.name in seen:
            continue
        seen.add(item.name)
        merged = dict(builder.BASE_PARAMS)
        merged.update(item.params)
        try:
            builder.validate_params(merged)
            valid.append(item)
        except Exception as exc:
            print(f"Skip invalid {item.name}: {exc}", flush=True)
    return valid


def read_csv(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def coerce_row(row: dict) -> dict:
    converted = {}
    for key, value in row.items():
        if value in {"True", "False"}:
            converted[key] = value == "True"
            continue
        try:
            converted[key] = float(value)
        except (TypeError, ValueError):
            converted[key] = value
    return converted


def previous_best() -> dict:
    if not PREVIOUS_BEST_JSON.exists():
        return {}
    try:
        data = json.loads(PREVIOUS_BEST_JSON.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return data.get("best", {})


def metric_delta(current: Any, previous: Any) -> str:
    try:
        delta = float(current) - float(previous)
    except (TypeError, ValueError):
        return "N/A"
    return f"{delta:+.2f}"


def fine_sweep_candidates() -> list[geom.GeometryCandidate]:
    raw: list[geom.GeometryCandidate] = [
        candidate(
            "ref_pad0p34_port0p55_feed3p30",
            "上一轮最优小焊盘结构，作为本轮细扫基线。",
        )
    ]

    for radius in [0.28, 0.30, 0.32, 0.34, 0.36]:
        raw.append(
            candidate(
                f"pad{token(radius)}_port0p55_feed3p30",
                "固定端口宽度和馈电偏移，仅细扫馈电焊盘半径。",
                feed_pad_radius_mm=radius,
                port_width_mm=0.55,
                feed_offset_u_mm=3.30,
            )
        )

    for width in [0.45, 0.50, 0.55, 0.60]:
        raw.append(
            candidate(
                f"pad0p32_port{token(width)}_feed3p30",
                "使用较小焊盘并细扫端口片宽度，观察近场耦合与端口匹配折中。",
                feed_pad_radius_mm=0.32,
                port_width_mm=width,
                feed_offset_u_mm=3.30,
            )
        )

    for offset in [3.20, 3.30, 3.40, 3.50, 3.60]:
        raw.append(
            candidate(
                f"pad0p32_port0p50_feed{token(offset)}",
                "使用小焊盘/窄端口组合并细扫双馈偏移。",
                feed_pad_radius_mm=0.32,
                port_width_mm=0.50,
                feed_offset_u_mm=offset,
            )
        )

    raw.extend(
        [
            candidate(
                "pad0p30_port0p45_feed3p40",
                "交互点：小焊盘、窄端口和略外移馈点的低耦合组合。",
                feed_pad_radius_mm=0.30,
                port_width_mm=0.45,
                feed_offset_u_mm=3.40,
            ),
            candidate(
                "pad0p28_port0p45_feed3p50",
                "交互点：最小焊盘与最窄端口，测试极限小探针近场耦合。",
                feed_pad_radius_mm=0.28,
                port_width_mm=0.45,
                feed_offset_u_mm=3.50,
            ),
            candidate(
                "openline_l1p80_w0p10_gap0p08",
                "加入悬浮 A/B 弱耦合开路线，长度 1.80 mm，用于局部反向耦合补偿。",
                feed_pad_radius_mm=0.32,
                port_width_mm=0.50,
                feed_offset_u_mm=3.30,
                weak_coupling_open_line_enabled=1.0,
                weak_coupling_open_line_length_mm=1.80,
                weak_coupling_open_line_width_mm=0.10,
                weak_coupling_open_line_offset_mm=1.65,
                weak_coupling_open_line_gap_mm=0.08,
            ),
            candidate(
                "openline_l2p40_w0p12_gap0p08",
                "加长悬浮 A/B 弱耦合开路线，增强隔离补偿但控制对贴片模式扰动。",
                feed_pad_radius_mm=0.32,
                port_width_mm=0.50,
                feed_offset_u_mm=3.30,
                weak_coupling_open_line_enabled=1.0,
                weak_coupling_open_line_length_mm=2.40,
                weak_coupling_open_line_width_mm=0.12,
                weak_coupling_open_line_offset_mm=1.65,
                weak_coupling_open_line_gap_mm=0.08,
            ),
            candidate(
                "openline_l2p80_w0p10_gap0p10",
                "进一步加长但提高悬浮间隙，验证更弱电容耦合下的隔离趋势。",
                feed_pad_radius_mm=0.32,
                port_width_mm=0.50,
                feed_offset_u_mm=3.40,
                weak_coupling_open_line_enabled=1.0,
                weak_coupling_open_line_length_mm=2.80,
                weak_coupling_open_line_width_mm=0.10,
                weak_coupling_open_line_offset_mm=1.70,
                weak_coupling_open_line_gap_mm=0.10,
            ),
            candidate(
                "viafence_n2_pitch0p55_edge0p45",
                "在每个贴片 A/B 馈电象限外侧加入 2 颗接地过孔栅栏，抑制局部地电流串扰。",
                feed_pad_radius_mm=0.32,
                port_width_mm=0.50,
                feed_offset_u_mm=3.30,
                via_fence_enabled=1.0,
                via_fence_count=2.0,
                via_fence_radius_mm=0.10,
                via_fence_pitch_mm=0.55,
                via_fence_edge_offset_mm=0.45,
                via_fence_center_mm=3.30,
            ),
            candidate(
                "viafence_n3_pitch0p65_edge0p55",
                "增强过孔栅栏数量和边缘偏移，寻找隔离提升与方向图扰动的折中。",
                feed_pad_radius_mm=0.32,
                port_width_mm=0.50,
                feed_offset_u_mm=3.40,
                via_fence_enabled=1.0,
                via_fence_count=3.0,
                via_fence_radius_mm=0.10,
                via_fence_pitch_mm=0.65,
                via_fence_edge_offset_mm=0.55,
                via_fence_center_mm=3.35,
            ),
            candidate(
                "openline_viafence_combined",
                "组合弱耦合开路线和温和过孔栅栏，测试两种隔离机制的叠加效果。",
                feed_pad_radius_mm=0.32,
                port_width_mm=0.50,
                feed_offset_u_mm=3.35,
                weak_coupling_open_line_enabled=1.0,
                weak_coupling_open_line_length_mm=2.20,
                weak_coupling_open_line_width_mm=0.10,
                weak_coupling_open_line_offset_mm=1.65,
                weak_coupling_open_line_gap_mm=0.10,
                via_fence_enabled=1.0,
                via_fence_count=2.0,
                via_fence_radius_mm=0.10,
                via_fence_pitch_mm=0.55,
                via_fence_edge_offset_mm=0.45,
                via_fence_center_mm=3.30,
            ),
        ]
    )
    return validate_candidates(raw)


def param_snapshot(item: geom.GeometryCandidate) -> dict[str, Any]:
    keys = [
        "feed_pad_radius_mm",
        "port_width_mm",
        "feed_offset_u_mm",
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
    ]
    return {key: item.params.get(key, "") for key in keys}


def select_full_candidates(candidates: list[geom.GeometryCandidate], sparam_rows: list[dict], count: int) -> list[geom.GeometryCandidate]:
    by_name = {item.name: item for item in candidates}
    ranked_names = [row["candidate"] for row in sorted(sparam_rows, key=lambda row: float(row["score"]))]
    selected_names = ranked_names[:count]
    iso_names = [
        name
        for name in ranked_names
        if by_name[name].params.get("weak_coupling_open_line_enabled", 0.0) >= 0.5
        or by_name[name].params.get("via_fence_enabled", 0.0) >= 0.5
    ]
    if count > 1 and iso_names and not any(name in selected_names for name in iso_names):
        selected_names[-1] = iso_names[0]
    return [by_name[name] for name in selected_names]


def snapshot_best_exports(item_name: str) -> None:
    for src, suffix in [
        (SOURCE_SWEEP_CSV, "source_sweep.csv"),
        (BEST_CURVES_CSV, "curves.csv"),
    ]:
        if src.exists():
            shutil.copy2(src, REPORT_DIR / f"{item_name}_{suffix}")


def restore_best_exports(item_name: str) -> None:
    for dst, suffix in [
        (SOURCE_SWEEP_CSV, "source_sweep.csv"),
        (BEST_CURVES_CSV, "curves.csv"),
    ]:
        src = REPORT_DIR / f"{item_name}_{suffix}"
        if src.exists():
            shutil.copy2(src, dst)


def write_report(best: dict, sparam_rows: list[dict], full_rows: list[dict], candidate_count: int) -> None:
    top_s = sorted(sparam_rows, key=lambda row: float(row["score"]))[:12]
    prev = previous_best()
    lines = [
        "# D44 锚点天线小焊盘与 A/B 隔离结构细扫报告",
        "",
        "## 本轮目标",
        "",
        f"- 小焊盘趋势细扫：`feed_pad_radius = 0.28-0.36 mm`。",
        f"- 端口片细扫：`port_width = 0.45-0.60 mm`。",
        f"- 双馈偏移细扫：`feed_offset = 3.20-3.60 mm`。",
        "- 新增结构：可调悬浮 A/B 弱耦合开路线、贴片外侧接地过孔栅栏。",
        f"- 判据：最差 `Sii <= {RETURN_TARGET_DB:.1f} dB`，A/B 隔离 `>= {ISOLATION_TARGET_DB:.1f} dB`，PDOA 平均 RMS 漂移 `<= {PDOA_RMS_TARGET_DEG:.1f} deg`，最大漂移 `<= {PDOA_MAX_TARGET_DEG:.1f} deg`。",
        "",
        "## 建模说明",
        "",
        "- 弱耦合开路线是每个贴片上方的悬浮窄铜条，位于 A/B 馈点之间，用于提供可调的反向电容耦合。",
        "- 过孔栅栏位于每个贴片 A/B 馈电象限外侧，不穿过贴片，接地后用于抑制局部地电流串扰。",
        "- 本轮先以三频点 S 参数快速筛选，再对排名靠前候选进行远场/PDOA 线极化复核；若隔离结构未进入前列，会强制保留一个隔离结构候选进入完整复核。",
        "",
        "## S 参数筛选排名",
        "",
        f"- 本次实际筛选候选数：`{candidate_count}`。",
        "",
        "| 排名 | 候选 | 评分 | 最差 Sii | 隔离度 | 焊盘 | 端口 | 馈点 | 开路线 | 过孔栅栏 |",
        "| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for idx, row in enumerate(top_s, start=1):
        lines.append(
            "| "
            f"{idx} | `{row['candidate']}` | {fmt(row['score'])} | {fmt(row['worst_return_db'])} dB | "
            f"{fmt(row['isolation_db'])} dB | {fmt(row.get('feed_pad_radius_mm'))} | "
            f"{fmt(row.get('port_width_mm'))} | {fmt(row.get('feed_offset_u_mm'))} | "
            f"{fmt(row.get('weak_coupling_open_line_enabled'), 0)} | {fmt(row.get('via_fence_enabled'), 0)} |"
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
            f"- A/B 端口隔离：`{fmt(best.get('isolation_db'))} dB`",
            f"- 最优 B 路幅度：`{fmt(best.get('best_amp_b'), 3)}`",
            f"- 最优 B 路相位：`{fmt(best.get('best_phase_b_deg'), 1)} deg`",
            f"- 平均 RMS PDOA 漂移：`{fmt(best.get('best_avg_rms_bias_deg'))} deg`",
            f"- 95 分位 RMS PDOA 漂移：`{fmt(best.get('best_p95_rms_bias_deg'))} deg`",
            f"- 最大 PDOA 漂移：`{fmt(best.get('best_max_abs_bias_deg'))} deg`",
            f"- FOV 最小增益：`{fmt(best.get('fov_best_gain_min_dbi'))} dBi`",
            f"- FOV 最大轴比：`{fmt(best.get('fov_best_axial_ratio_max_db'))} dB`",
            f"- CP 覆盖率下限：`{fmt(best.get('fov_best_cp_coverage_min_percent'), 1)}%`",
            "",
            "## 与上一轮对比",
            "",
        ]
    )
    if prev:
        comparison = [
            ("最差 Sii", "worst_return_db", "dB"),
            ("A/B 隔离", "isolation_db", "dB"),
            ("平均 RMS PDOA 漂移", "best_avg_rms_bias_deg", "deg"),
            ("95 分位 RMS PDOA 漂移", "best_p95_rms_bias_deg", "deg"),
            ("最大 PDOA 漂移", "best_max_abs_bias_deg", "deg"),
            ("FOV 最小增益", "fov_best_gain_min_dbi", "dBi"),
            ("FOV 最大轴比", "fov_best_axial_ratio_max_db", "dB"),
        ]
        lines.extend(
            [
                f"- 上一轮最优候选：`{prev.get('candidate')}`。",
                "",
                "| 指标 | 上一轮 | 本轮 | 变化 |",
                "| --- | ---: | ---: | ---: |",
            ]
        )
        for label, key, unit in comparison:
            lines.append(
                f"| {label} | {fmt(prev.get(key))} {unit} | {fmt(best.get(key))} {unit} | {metric_delta(best.get(key), prev.get(key))} |"
            )
        lines.append("")
    else:
        lines.extend(["- 未找到上一轮最优 JSON，无法自动对比。", ""])
    lines.extend(
        [
            "## 最优参数",
            "",
        ]
    )
    for key, value in (best.get("parameters") or {}).items():
        if key in param_snapshot(geom.GeometryCandidate(str(best.get("candidate")), best.get("parameters") or {}, "")).keys():
            lines.append(f"- `{key}`：`{value}`")
    lines.extend(
        [
            "",
            "## 达标情况",
            "",
            f"- S 参数目标：`{'通过' if best.get('meets_s') else '未通过'}`。",
            f"- PDOA 极化稳定性目标：`{'通过' if best.get('meets_pdoa') else '未通过'}`。",
            f"- FOV/轴比目标：`{'通过' if best.get('meets_fov') else '未通过'}`。",
            f"- 全部目标：`{'通过' if best.get('meets_all') else '未通过'}`。",
            "",
            "## 工程判断",
            "",
        ]
    )
    if best.get("meets_all"):
        lines.append("- 当前候选已满足本轮全部判据，可以进入更完整频扫和制造约束复核。")
    else:
        lines.extend(
            [
                "- 这轮会诚实保留未达标项：若隔离或 PDOA 漂移仍不满足目标，说明仅靠小焊盘和局部弱隔离结构还不足以消除线极化敏感性。",
                "- 若过孔栅栏优于开路线，下一步应改为带真实地过孔焊盘和反焊盘的版图级模型；若开路线优于过孔栅栏，下一步应把开路线落到可制造的微带/寄生金属层并联动高度和介质。",
                "- PDOA 曲线最终仍建议配合双极化通道标定矩阵，否则单一天线轴比优化无法完全保证 0/45/90/135 deg 线极化下鉴角曲线不漂移。",
            ]
        )
    lines.extend(
        [
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


def run(max_sparam_candidates: int = 22, full_candidate_count: int = 3, resume_sparam: bool = False, skip_existing_full: bool = False) -> dict:
    configure_geom_paths()
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    candidates = fine_sweep_candidates()[:max_sparam_candidates]
    by_name = {item.name: item for item in candidates}
    sparam_rows = read_csv(SPARAM_CSV) if resume_sparam else []
    sparam_rows = [row for row in sparam_rows if row.get("candidate") in by_name]
    screened = {row["candidate"] for row in sparam_rows}
    for idx, item in enumerate(candidates, start=1):
        if item.name in screened:
            print(f"Stage: S-parameter screening {idx}/{len(candidates)} {item.name} reused", flush=True)
            continue
        print(f"Stage: S-parameter screening {idx}/{len(candidates)} {item.name}", flush=True)
        row = geom.sparam_screen(item, idx)
        row.update(param_snapshot(item))
        sparam_rows.append(row)
        geom.write_csv(SPARAM_CSV, sparam_rows)

    ranked_candidates = select_full_candidates(candidates, sparam_rows, full_candidate_count)
    existing_full = {}
    if skip_existing_full:
        for row in read_csv(FULL_CSV):
            if row.get("candidate") in by_name:
                coerced = coerce_row(row)
                coerced.setdefault("parameters", by_name[row["candidate"]].params)
                existing_full[row["candidate"]] = coerced
    full_rows = []
    for idx, item in enumerate(ranked_candidates, start=1):
        if item.name in existing_full:
            print(f"Stage: full validation {idx}/{len(ranked_candidates)} {item.name} reused", flush=True)
            full_rows.append(existing_full[item.name])
            continue
        print(f"Stage: full validation {idx}/{len(ranked_candidates)} {item.name}", flush=True)
        result = geom.full_validate(item)
        full_rows.append(result)
        snapshot_best_exports(item.name)
        geom.write_csv(FULL_CSV, [{k: v for k, v in row.items() if k != "parameters"} for row in full_rows])

    best = min(full_rows, key=lambda row: row["full_score"])
    restore_best_exports(str(best["candidate"]))

    if ranked_candidates[-1].name != best["candidate"]:
        best_item = next(item for item in candidates if item.name == best["candidate"])
        print(f"Stage: rebuilding final best project {best_item.name}", flush=True)
        geom.apply_candidate(best_item)
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
        "sweep_ranges": {
            "feed_pad_radius_mm": [0.28, 0.36],
            "port_width_mm": [0.45, 0.60],
            "feed_offset_u_mm": [3.20, 3.60],
        },
        "candidate_count": len(candidates),
        "sparam_top": sorted(sparam_rows, key=lambda row: float(row["score"]))[:12],
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
    write_report(best, sparam_rows, full_rows, len(candidates))
    print(json.dumps(best, indent=2, ensure_ascii=False), flush=True)
    print(f"Wrote {REPORT_MD}", flush=True)
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-sparam-candidates", type=int, default=22)
    parser.add_argument("--full-candidate-count", type=int, default=3)
    parser.add_argument("--resume-sparam", action="store_true")
    parser.add_argument("--skip-existing-full", action="store_true")
    args = parser.parse_args()
    run(
        max_sparam_candidates=args.max_sparam_candidates,
        full_candidate_count=args.full_candidate_count,
        resume_sparam=args.resume_sparam,
        skip_existing_full=args.skip_existing_full,
    )
