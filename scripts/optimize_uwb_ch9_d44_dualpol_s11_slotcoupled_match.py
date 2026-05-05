from __future__ import annotations

import argparse
import csv
import json
import math
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import build_uwb_ch9_hfss_d44_topology as builder
import evaluate_uwb_ch9_d44_dualpol as dualpol_eval
import evaluate_uwb_ch9_d44_topology as topology_eval


ROOT = Path(__file__).resolve().parents[1]
TOPOLOGY = "dualpol"
REPORT_DIR = ROOT / "reports_d44_dualpol_s11_slotmatch_opt"
STEM = "UWB_CH9_D44_DUALPOL_S11_SLOTMATCH"
SPARAM_CSV = REPORT_DIR / f"{STEM}_sparam_screening.csv"
BEST_JSON = REPORT_DIR / f"{STEM}_best.json"
REPORT_MD = REPORT_DIR / f"{STEM}_optimization_report.md"

RETURN_TARGET_DB = -10.0
CURRENT_MODEL_REFERENCE_DB = -1.787889
PREVIOUS_SPARAM_BEST_DB = -2.289091

STRUCTURE_KEYS = [
    "patch_side_mm",
    "port_width_mm",
    "dualpol_slotcoupled_enabled",
    "feed_substrate_h_mm",
    "slot_coupled_aperture_length_a_mm",
    "slot_coupled_aperture_length_b_mm",
    "slot_coupled_aperture_width_mm",
    "slot_coupled_offset_a_mm",
    "slot_coupled_offset_b_mm",
    "slot_coupled_aperture_center_a_v_mm",
    "slot_coupled_aperture_center_b_u_mm",
    "slot_coupled_feedline_length_mm",
    "slot_coupled_feedline_width_mm",
    "slot_coupled_feedline_offset_a_v_mm",
    "slot_coupled_feedline_offset_b_u_mm",
    "dualpol_parasitic_enabled",
    "parasitic_side_mm",
    "air_gap_mm",
    "isolation_slot_enabled",
    "isolation_slot_length_mm",
    "isolation_slot_width_mm",
    "isolation_slot_inner_mm",
]

BASE_PARAMS: dict[str, Any] = dict(builder.TOPOLOGIES[TOPOLOGY]["params"])
BASE_PARAMS.update(
    {
        "patch_side_mm": 9.35,
        "corner_cut_mm": 0.0,
        "feed_offset_u_mm": 3.40,
        "feed_offset_v_mm": 0.0,
        "feed_pad_radius_mm": 0.28,
        "port_width_mm": 0.50,
        "microstrip_feed_enabled": 0.0,
        "microstrip_feed_mirror_enabled": 1.0,
        "neutralization_branch_enabled": 0.0,
        "local_dgs_enabled": 0.0,
        "dualpol_parasitic_enabled": 0.0,
        "parasitic_side_mm": 0.0,
        "air_gap_mm": 0.0,
        "dualpol_slotcoupled_enabled": 1.0,
        "feed_substrate_h_mm": 0.254,
        "slot_coupled_aperture_length_a_mm": 3.6,
        "slot_coupled_aperture_length_b_mm": 3.6,
        "slot_coupled_aperture_width_mm": 0.45,
        "slot_coupled_offset_a_mm": 0.0,
        "slot_coupled_offset_b_mm": 0.0,
        "slot_coupled_aperture_center_a_v_mm": 0.0,
        "slot_coupled_aperture_center_b_u_mm": 0.0,
        "slot_coupled_feedline_length_mm": 10.0,
        "slot_coupled_feedline_width_mm": 0.60,
        "slot_coupled_feedline_offset_a_v_mm": 0.0,
        "slot_coupled_feedline_offset_b_u_mm": 0.0,
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


def fmt(value: Any, digits: int = 2) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    if math.isnan(number):
        return "nan"
    return f"{number:.{digits}f}"


def write_csv(path: Path, rows: list[dict], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        return
    fields = list(fieldnames or rows[0].keys())
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: f"{row[key]:.6f}" if isinstance(row.get(key), float) else row.get(key, "") for key in fields})


def read_csv(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def slot_params(
    *,
    patch: float,
    slot_len: float,
    slot_width: float,
    feed_width: float,
    feed_len: float = 10.0,
    feed_h: float = 0.254,
    port_width: float = 0.50,
    iso_len: float = 10.0,
    iso_width: float = 0.42,
) -> dict[str, Any]:
    params = dict(BASE_PARAMS)
    params.update(
        {
            "patch_side_mm": patch,
            "port_width_mm": port_width,
            "feed_substrate_h_mm": feed_h,
            "slot_coupled_aperture_length_a_mm": slot_len,
            "slot_coupled_aperture_length_b_mm": slot_len,
            "slot_coupled_aperture_width_mm": slot_width,
            "slot_coupled_feedline_length_mm": feed_len,
            "slot_coupled_feedline_width_mm": feed_width,
            "isolation_slot_length_mm": iso_len,
            "isolation_slot_width_mm": iso_width,
        }
    )
    return params


def make_candidate(name: str, rationale: str, **kwargs: Any) -> Candidate:
    return Candidate(name=name, params=slot_params(**kwargs), rationale=rationale)


def candidates() -> list[Candidate]:
    raw = [
        make_candidate(
            "p9p35_l4p4_w0p55_fw0p65_ref",
            "上一轮 S 参数筛选中孔缝耦合回波最好的参考候选。",
            patch=9.35,
            slot_len=4.4,
            slot_width=0.55,
            feed_width=0.65,
        ),
        make_candidate(
            "p9p15_l4p0_w0p50_fw0p60",
            "缩小贴片把匹配谷往高频移动，保持中等孔缝耦合。",
            patch=9.15,
            slot_len=4.0,
            slot_width=0.50,
            feed_width=0.60,
        ),
        make_candidate(
            "p9p15_l4p4_w0p55_fw0p65",
            "缩小贴片并沿用上一轮最佳孔缝尺寸，检查高频端 S11。",
            patch=9.15,
            slot_len=4.4,
            slot_width=0.55,
            feed_width=0.65,
        ),
        make_candidate(
            "p8p95_l3p8_w0p50_fw0p60",
            "进一步缩小贴片，略减孔缝长度，避免高频端过强失配。",
            patch=8.95,
            slot_len=3.8,
            slot_width=0.50,
            feed_width=0.60,
        ),
        make_candidate(
            "p8p95_l4p2_w0p55_fw0p65",
            "较小贴片配较强中心孔缝，寻找 8.233 GHz 回波改善点。",
            patch=8.95,
            slot_len=4.2,
            slot_width=0.55,
            feed_width=0.65,
        ),
        make_candidate(
            "p8p75_l3p6_w0p45_fw0p60",
            "显著缩小贴片，回到原始中等孔缝，优先拉高谐振频率。",
            patch=8.75,
            slot_len=3.6,
            slot_width=0.45,
            feed_width=0.60,
        ),
        make_candidate(
            "p8p75_l4p0_w0p50_fw0p65",
            "小贴片配中强孔缝，观察带内三点最差回波能否继续下降。",
            patch=8.75,
            slot_len=4.0,
            slot_width=0.50,
            feed_width=0.65,
        ),
        make_candidate(
            "p8p55_l3p4_w0p45_fw0p55",
            "更高频谐振试探候选，用较弱孔缝避免过耦合。",
            patch=8.55,
            slot_len=3.4,
            slot_width=0.45,
            feed_width=0.55,
        ),
        make_candidate(
            "p8p55_l3p8_w0p50_fw0p60",
            "更小贴片配中等孔缝，检查高频端改善是否牺牲低频端。",
            patch=8.55,
            slot_len=3.8,
            slot_width=0.50,
            feed_width=0.60,
        ),
        make_candidate(
            "p8p95_l4p2_w0p55_fw0p65_len8",
            "在较小贴片最佳附近缩短下层馈线，改变开路支节等效电抗。",
            patch=8.95,
            slot_len=4.2,
            slot_width=0.55,
            feed_width=0.65,
            feed_len=8.0,
        ),
        make_candidate(
            "p8p95_l4p2_w0p55_fw0p65_len12",
            "在较小贴片最佳附近加长下层馈线，检查开路支节长度匹配。",
            patch=8.95,
            slot_len=4.2,
            slot_width=0.55,
            feed_width=0.65,
            feed_len=12.0,
        ),
        make_candidate(
            "p8p75_l4p0_w0p50_fw0p65_h0p508",
            "加厚下层介质降低孔缝加载，尝试改善回波而不改变孔缝中心。",
            patch=8.75,
            slot_len=4.0,
            slot_width=0.50,
            feed_width=0.65,
            feed_h=0.508,
        ),
        make_candidate(
            "p9p35_l4p8_w0p60_fw0p70",
            "沿上一轮参考继续加长中心孔缝，检查强一点的中心耦合是否继续改善 S11。",
            patch=9.35,
            slot_len=4.8,
            slot_width=0.60,
            feed_width=0.70,
        ),
        make_candidate(
            "p9p55_l4p8_w0p60_fw0p70",
            "放大贴片配 4.8 mm 中心孔缝，判断高频端失配是否需要更低谐振配合更强孔缝。",
            patch=9.55,
            slot_len=4.8,
            slot_width=0.60,
            feed_width=0.70,
        ),
        make_candidate(
            "p9p55_l5p2_w0p65_fw0p75",
            "放大贴片并进一步增强中心孔缝耦合，寻找深一点的回波谷。",
            patch=9.55,
            slot_len=5.2,
            slot_width=0.65,
            feed_width=0.75,
        ),
        make_candidate(
            "p9p75_l5p2_w0p65_fw0p75",
            "更大贴片搭配 5.2 mm 孔缝，测试中心强耦合路线的上限。",
            patch=9.75,
            slot_len=5.2,
            slot_width=0.65,
            feed_width=0.75,
        ),
        make_candidate(
            "p9p75_l5p6_w0p70_fw0p80",
            "强中心孔缝上限候选，判断矩形孔缝扫描是否已到不可用的过耦合区。",
            patch=9.75,
            slot_len=5.6,
            slot_width=0.70,
            feed_width=0.80,
        ),
        make_candidate(
            "p9p25_l4p5_w0p58_fw0p68",
            "在 p9.15/p9.35 之间插值，细扫上一轮参考和本轮最佳之间的局部谷。",
            patch=9.25,
            slot_len=4.5,
            slot_width=0.58,
            feed_width=0.68,
        ),
        make_candidate(
            "p9p05_l4p25_w0p56_fw0p66",
            "围绕 p8.95/l4.2 的局部细扫，略放大贴片和孔缝。",
            patch=9.05,
            slot_len=4.25,
            slot_width=0.56,
            feed_width=0.66,
        ),
        make_candidate(
            "p9p00_l4p2_w0p56_fw0p66",
            "围绕 p8.95/l4.2 的局部细扫，主要提高馈线与孔缝宽度。",
            patch=9.00,
            slot_len=4.2,
            slot_width=0.56,
            feed_width=0.66,
        ),
        make_candidate(
            "p8p90_l4p15_w0p54_fw0p64",
            "围绕 p8.95/l4.2 的低侧细扫，确认最佳点是否已越过。",
            patch=8.90,
            slot_len=4.15,
            slot_width=0.54,
            feed_width=0.64,
        ),
        make_candidate(
            "p8p95_l4p2_w0p60_fw0p70",
            "固定当前最佳贴片和孔缝长度，仅提高孔缝/馈线宽度调阻抗。",
            patch=8.95,
            slot_len=4.2,
            slot_width=0.60,
            feed_width=0.70,
        ),
        make_candidate(
            "p8p95_l4p4_w0p58_fw0p68",
            "当前最佳附近略加长孔缝，寻找更深回波。",
            patch=8.95,
            slot_len=4.4,
            slot_width=0.58,
            feed_width=0.68,
        ),
        make_candidate(
            "p9p05_l4p4_w0p58_fw0p68",
            "当前最佳附近同时略放大贴片和孔缝，做局部二维插值。",
            patch=9.05,
            slot_len=4.4,
            slot_width=0.58,
            feed_width=0.68,
        ),
        make_candidate(
            "p9p75_l6p0_w0p75_fw0p85",
            "沿当前最佳继续增强中心孔缝，检查 S11 改善是否仍未饱和。",
            patch=9.75,
            slot_len=6.0,
            slot_width=0.75,
            feed_width=0.85,
        ),
        make_candidate(
            "p9p95_l5p6_w0p70_fw0p80",
            "略放大贴片并保持当前最佳孔缝，检查贴片谐振位置对强耦合匹配的影响。",
            patch=9.95,
            slot_len=5.6,
            slot_width=0.70,
            feed_width=0.80,
        ),
        make_candidate(
            "p9p95_l6p0_w0p75_fw0p85",
            "更大贴片加更强孔缝，寻找中心强耦合路线的下一处回波谷。",
            patch=9.95,
            slot_len=6.0,
            slot_width=0.75,
            feed_width=0.85,
        ),
        make_candidate(
            "p10p15_l6p2_w0p80_fw0p90",
            "继续放大贴片和孔缝，测试矩形中心孔缝路线是否可进一步压低 S11。",
            patch=10.15,
            slot_len=6.2,
            slot_width=0.80,
            feed_width=0.90,
        ),
        make_candidate(
            "p9p75_l6p4_w0p80_fw0p90",
            "固定贴片 9.75 mm，进一步加长加宽孔缝，判断是否进入过耦合区。",
            patch=9.75,
            slot_len=6.4,
            slot_width=0.80,
            feed_width=0.90,
        ),
        make_candidate(
            "p10p15_l6p8_w0p85_fw0p95",
            "强耦合上限候选，用于界定当前矩形孔缝扫描的边界。",
            patch=10.15,
            slot_len=6.8,
            slot_width=0.85,
            feed_width=0.95,
        ),
        make_candidate(
            "p9p75_l5p6_w0p70_fw0p80_port0p80",
            "当前最佳几何不变，把端口宽度匹配到 0.8 mm 馈线宽度，减少端口过渡失配。",
            patch=9.75,
            slot_len=5.6,
            slot_width=0.70,
            feed_width=0.80,
            port_width=0.80,
        ),
        make_candidate(
            "p9p95_l6p0_w0p75_fw0p85_port0p85",
            "强耦合候选同时匹配端口宽度和 0.85 mm 馈线，检查端口定义对 S11 的影响。",
            patch=9.95,
            slot_len=6.0,
            slot_width=0.75,
            feed_width=0.85,
            port_width=0.85,
        ),
        make_candidate(
            "p9p55_l4p8_w0p60_fw0p70_port0p70",
            "第二轮次优几何不变，把端口宽度匹配到 0.7 mm 馈线宽度。",
            patch=9.55,
            slot_len=4.8,
            slot_width=0.60,
            feed_width=0.70,
            port_width=0.70,
        ),
        make_candidate(
            "p9p95_l6p0_w0p75_fw0p85_len9",
            "强耦合候选缩短下层馈线到 9 mm，微调开路段电抗。",
            patch=9.95,
            slot_len=6.0,
            slot_width=0.75,
            feed_width=0.85,
            feed_len=9.0,
        ),
    ]
    valid: list[Candidate] = []
    for item in raw:
        full_params = dict(builder.BASE_PARAMS)
        full_params.update(item.params)
        try:
            builder.validate_params(full_params)
            valid.append(item)
        except Exception as exc:
            print(f"Skip invalid {item.name}: {exc}", flush=True)
    return valid


def apply_candidate(item: Candidate) -> None:
    params = builder.TOPOLOGIES[TOPOLOGY].setdefault("params", {})
    params.clear()
    params.update(item.params)


def build_and_open() -> Any:
    return builder.build_project(
        TOPOLOGY,
        analyze=True,
        non_graphical=True,
        quick=True,
        band_samples=True,
        sparam_only=True,
        return_hfss=True,
    )


def sparam_score(row: dict[str, Any]) -> float:
    ret = float(row["worst_return_db"])
    balance = float(row["xy_return_balance_db"])
    iso = float(row["same_element_xy_isolation_db"])
    return_gap = max(0.0, ret - RETURN_TARGET_DB)
    iso_gap = max(0.0, 8.0 - iso)
    return 10.0 * return_gap + 2.0 * balance + 0.5 * iso_gap


def sparam_screen(item: Candidate, index: int) -> dict[str, Any]:
    started = time.time()
    apply_candidate(item)
    _project, hfss = build_and_open()
    try:
        sparams = topology_eval.get_s_parameter_snapshot(hfss, REPORT_DIR / f"{item.name}_s_parameters.csv")
        extra = dualpol_eval.enrich_sparams(sparams)
    finally:
        hfss.release_desktop(close_projects=False, close_desktop=True)
    x_return = extra["x_return_worst_db"]
    y_return = extra["y_return_worst_db"]
    row: dict[str, Any] = {
        "index": index,
        "candidate": item.name,
        "elapsed_s": time.time() - started,
        "rationale": item.rationale,
        "worst_return_db": sparams["worst_return_db"],
        "isolation_db": sparams["isolation_db"],
        "worst_return_expr": sparams["worst_return_expr"],
        "worst_coupling_expr": sparams["worst_coupling_expr"],
        "x_return_worst_db": x_return,
        "y_return_worst_db": y_return,
        "xy_return_balance_db": abs(x_return - y_return),
        "same_element_xy_isolation_db": extra["same_element_xy_isolation_db"],
        "same_feed_inter_element_isolation_db": extra["same_feed_inter_element_isolation_db"],
    }
    for key in STRUCTURE_KEYS:
        row[key] = item.params.get(key, "")
    row["score"] = sparam_score(row)
    print(json.dumps(row, indent=2, ensure_ascii=False), flush=True)
    return row


def rank_rows(rows: list[dict]) -> list[dict]:
    return sorted(rows, key=lambda row: (float(row["worst_return_db"]), float(row["score"])))


def rebuild_best_project(item: Candidate) -> None:
    print(f"Stage: rebuilding runnable best S11 project {item.name}", flush=True)
    apply_candidate(item)
    _project, hfss = build_and_open()
    hfss.release_desktop(close_projects=False, close_desktop=True)


def write_report(rows: list[dict], best: dict, outputs: dict[str, str]) -> None:
    ranked = rank_rows(rows)
    lines = [
        "# D44 双极化孔缝耦合 S11 匹配优化报告",
        "",
        "## 目标",
        "",
        f"- 持续迭代优化当前八端口双极化孔缝耦合模型的 S11/回波，目标为全端口带内最差回波 `<= {RETURN_TARGET_DB:.1f} dB`。",
        "- 本轮只跑 S 参数快速筛选，不重新导出远场；重点扫描贴片尺寸、孔缝长度/宽度、下层馈线宽度/长度和下层介质厚度。",
        "- 当前可视模型参考候选 `slot_l3p6_w0p45_feed0p60` 的最差回波为 `-1.79 dB`；上一轮 S 参数筛选最佳为 `-2.29 dB`。",
        "",
        "## 筛选排名",
        "",
        "| 排名 | 候选 | 最差回波 | X回波 | Y回波 | 回波差 | 同阵元X/Y隔离 | 同馈跨阵元隔离 |",
        "| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for idx, row in enumerate(ranked, start=1):
        lines.append(
            f"| {idx} | `{row['candidate']}` | {fmt(row['worst_return_db'])} dB | "
            f"{fmt(row['x_return_worst_db'])} dB | {fmt(row['y_return_worst_db'])} dB | "
            f"{fmt(row['xy_return_balance_db'])} dB | {fmt(row['same_element_xy_isolation_db'])} dB | "
            f"{fmt(row['same_feed_inter_element_isolation_db'])} dB |"
        )
    params = best["parameters"]
    improvement_current = float(best["worst_return_db"]) - CURRENT_MODEL_REFERENCE_DB
    improvement_previous = float(best["worst_return_db"]) - PREVIOUS_SPARAM_BEST_DB
    lines.extend(
        [
            "",
            "## 最佳候选",
            "",
            f"- 候选：`{best['candidate']}`",
            f"- 最差回波：`{fmt(best['worst_return_db'])} dB`",
            f"- 相对当前可视模型变化：`{fmt(improvement_current)} dB`（负值为改善）。",
            f"- 相对上一轮 S 参数最佳变化：`{fmt(improvement_previous)} dB`（负值为改善）。",
            f"- S11 目标：`{'通过' if float(best['worst_return_db']) <= RETURN_TARGET_DB else '未通过'}`。",
            "",
            "## 最佳几何参数",
            "",
        ]
    )
    for key in STRUCTURE_KEYS:
        if key in params:
            lines.append(f"- `{key}`: `{fmt(params[key], 3)}`")
    lines.extend(
        [
            "",
            "## 工程判断",
            "",
        ]
    )
    best_patch = float(params.get("patch_side_mm", 0.0))
    best_slot = float(params.get("slot_coupled_aperture_length_a_mm", 0.0))
    if float(best["worst_return_db"]) < PREVIOUS_SPARAM_BEST_DB and (best_patch > 9.35 or best_slot > 4.8):
        lines.append("- 更大贴片配更长、更宽的中心孔缝后最差回波出现正向改善，说明当前孔缝耦合强度不足是 S11 的主要限制。")
        lines.append("- 代价是同阵元 X/Y 隔离下降，后续需要把 S11 调谐支节和 A/B 去耦结构分开设计。")
    elif float(best["worst_return_db"]) < PREVIOUS_SPARAM_BEST_DB:
        lines.append("- 本轮几何扫描带来正向改善，但趋势仍较浅，需要继续引入可调阻抗结构。")
    else:
        lines.append("- 本轮没有超过上一轮 S 参数最佳，说明仅靠贴片缩小和孔缝尺寸还不足以解决匹配。")
    lines.extend(
        [
            "- 如果仍未到 -10 dB，下一轮应在下层孔缝馈线中加入真正的开路/短路调谐支节、阶梯阻抗线或电容耦合调谐，而不是继续只扫矩形孔缝。",
            "- 本轮重建的 AEDT 工程保存为最佳 S11 候选，可直接打开检查八端口 S 参数。",
            "",
            "## 输出文件",
            "",
        ]
    )
    for label, path in outputs.items():
        lines.append(f"- {label}：`{path}`")
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run(max_candidates: int, resume: bool) -> dict[str, Any]:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    cands = candidates()[:max_candidates]
    by_name = {item.name: item for item in cands}
    rows = [row for row in read_csv(SPARAM_CSV) if row.get("candidate") in by_name] if resume else []
    completed = {row["candidate"] for row in rows}
    for idx, item in enumerate(cands, start=1):
        if item.name in completed:
            print(f"Stage: S11 screening {idx}/{len(cands)} {item.name} reused", flush=True)
            continue
        print(f"Stage: S11 screening {idx}/{len(cands)} {item.name}", flush=True)
        rows.append(sparam_screen(item, idx))
        write_csv(SPARAM_CSV, rows)
    ranked = rank_rows(rows)
    best_row = ranked[0]
    best_item = by_name[best_row["candidate"]]
    rebuild_best_project(best_item)
    best = dict(best_row)
    best["parameters"] = best_item.params
    outputs = {
        "S 参数筛选 CSV": str(SPARAM_CSV),
        "最佳 JSON": str(BEST_JSON),
        "中文报告": str(REPORT_MD),
        "AEDT 工程": str(builder.topology_paths(TOPOLOGY)["project"]),
        "参数 JSON": str(builder.topology_paths(TOPOLOGY)["params"]),
    }
    payload = {
        "targets": {
            "return_target_db": RETURN_TARGET_DB,
            "current_model_reference_db": CURRENT_MODEL_REFERENCE_DB,
            "previous_sparam_best_db": PREVIOUS_SPARAM_BEST_DB,
        },
        "candidate_count": len(cands),
        "sparam_rows": rows,
        "best": best,
        "outputs": outputs,
    }
    BEST_JSON.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    write_report(rows, best, outputs)
    print(json.dumps({k: v for k, v in best.items() if k != "parameters"}, indent=2, ensure_ascii=False), flush=True)
    print(f"Wrote {REPORT_MD}", flush=True)
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-candidates", type=int, default=12)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    run(args.max_candidates, args.resume)


if __name__ == "__main__":
    main()
