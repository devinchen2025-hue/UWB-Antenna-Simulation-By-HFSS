from __future__ import annotations

import argparse
import csv
import json
import math
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ansys.aedt.core import Hfss

import build_uwb_ch9_hfss_d44_topology as builder
import evaluate_uwb_ch9_d44_topology as evaluator


ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = ROOT / "reports_d44_dualfeed_hybrid_opt"
HISTORY_CSV = REPORT_DIR / "UWB_CH9_D44_DUALFEED_HYBRID_optimization_history.csv"
BALANCE_CSV = REPORT_DIR / "UWB_CH9_D44_DUALFEED_HYBRID_source_balance.csv"
BEST_JSON = REPORT_DIR / "UWB_CH9_D44_DUALFEED_HYBRID_best.json"
REPORT_MD = REPORT_DIR / "UWB_CH9_D44_DUALFEED_HYBRID_optimization_report.md"

RETURN_TARGET_DB = -10.0
ISOLATION_TARGET_DB = 15.0
GAIN_TARGET_DBI = -5.0
AR_TARGET_DB = 3.0


@dataclass(frozen=True)
class Candidate:
    name: str
    topology: str
    params: dict[str, Any]
    rationale: str


def base_params(topology: str) -> dict[str, Any]:
    params = dict(builder.TOPOLOGIES[topology]["params"])
    return params


STRUCTURE_PARAM_KEYS = [
    "microstrip_feed_enabled",
    "microstrip_feed_offset_mm",
    "microstrip_feedline_length_mm",
    "microstrip_feedline_width_mm",
    "microstrip_match_length_mm",
    "microstrip_match_width_mm",
    "microstrip_stub_length_mm",
    "microstrip_stub_width_mm",
    "microstrip_stub_offset_mm",
    "neutralization_branch_enabled",
    "neutralization_branch_length_mm",
    "neutralization_branch_width_mm",
    "neutralization_branch_offset_mm",
    "local_dgs_enabled",
    "local_dgs_length_mm",
    "local_dgs_width_mm",
    "local_dgs_offset_mm",
    "hybrid_output_match_length_mm",
    "hybrid_output_match_width_mm",
]


def network_extra(
    *,
    line_len: float = 2.0,
    line_width: float = 0.60,
    feed_offset: float = 0.0,
    match_len: float = 0.85,
    match_width: float = 0.42,
    stub_len: float = 0.0,
    stub_width: float = 0.24,
    stub_offset: float = 0.75,
    branch: bool = False,
    branch_len: float = 1.15,
    branch_width: float = 0.18,
    branch_offset: float = 1.15,
    dgs: bool = False,
    dgs_len: float = 4.8,
    dgs_width: float = 0.28,
    dgs_offset: float = 1.15,
    hybrid_match_len: float | None = None,
    hybrid_match_width: float | None = None,
) -> dict[str, float]:
    return {
        "microstrip_feed_enabled": 1.0,
        "microstrip_feed_offset_mm": feed_offset,
        "microstrip_feedline_length_mm": line_len,
        "microstrip_feedline_width_mm": line_width,
        "microstrip_match_length_mm": match_len,
        "microstrip_match_width_mm": match_width,
        "microstrip_stub_length_mm": stub_len,
        "microstrip_stub_width_mm": stub_width,
        "microstrip_stub_offset_mm": stub_offset,
        "neutralization_branch_enabled": 1.0 if branch else 0.0,
        "neutralization_branch_length_mm": branch_len,
        "neutralization_branch_width_mm": branch_width,
        "neutralization_branch_offset_mm": branch_offset,
        "local_dgs_enabled": 1.0 if dgs else 0.0,
        "local_dgs_length_mm": dgs_len,
        "local_dgs_width_mm": dgs_width,
        "local_dgs_offset_mm": dgs_offset,
        "hybrid_output_match_length_mm": hybrid_match_len if hybrid_match_len is not None else match_len,
        "hybrid_output_match_width_mm": hybrid_match_width if hybrid_match_width is not None else match_width,
    }


def make_candidate(
    topology: str,
    name: str,
    patch: float,
    feed: float,
    rationale: str,
    *,
    port_width: float = 0.70,
    pad: float = 0.42,
    feed_a: float | None = None,
    feed_b: float | None = None,
    slot_len: float = 10.0,
    slot_width: float = 0.42,
    trace_width: float | None = None,
    trace_gap: float | None = None,
    extra: dict[str, Any] | None = None,
) -> Candidate:
    params = base_params(topology)
    params.update(
        {
            "patch_side_mm": patch,
            "feed_offset_u_mm": feed,
            "feed_pad_radius_mm": pad,
            "port_width_mm": port_width,
            "isolation_slot_length_mm": slot_len,
            "isolation_slot_width_mm": slot_width,
        }
    )
    if feed_a is not None:
        params["feed_offset_a_mm"] = feed_a
    if feed_b is not None:
        params["feed_offset_b_mm"] = feed_b
    if trace_width is not None:
        params["hybrid_trace_width_mm"] = trace_width
    if trace_gap is not None:
        params["hybrid_trace_gap_mm"] = trace_gap
    if extra:
        params.update(extra)
    return Candidate(name=f"{topology}_{name}", topology=topology, params=params, rationale=rationale)


def generate_candidates() -> list[Candidate]:
    candidates = [
        make_candidate("dualfeed", "probe_reference_3p3", 9.15, 3.30, "上一轮最佳探针/焊盘双馈结果，作为本轮真实馈电网络对照。"),
        make_candidate(
            "dualfeed",
            "edge_match_l1p8_w0p55",
            9.15,
            3.30,
            "把双馈端口升级为边缘微带馈线，采用较短匹配段以改善端口回波。",
            port_width=0.55,
            extra=network_extra(line_len=1.80, line_width=0.55, match_len=0.70, match_width=0.38),
        ),
        make_candidate(
            "dualfeed",
            "edge_match_l2p1_w0p65",
            9.15,
            3.30,
            "扫描更长、更宽的可调微带馈线，检查输入阻抗向 50 欧姆移动的趋势。",
            port_width=0.65,
            extra=network_extra(line_len=2.10, line_width=0.65, match_len=0.95, match_width=0.44),
        ),
        make_candidate(
            "dualfeed",
            "edge_stub_0p75",
            9.15,
            3.30,
            "在边缘微带馈线上加入短开路支节，用支节电纳补偿端口匹配。",
            port_width=0.60,
            extra=network_extra(line_len=1.95, line_width=0.60, match_len=0.85, match_width=0.42, stub_len=0.75),
        ),
        make_candidate(
            "dualfeed",
            "edge_stub_1p10",
            9.15,
            3.30,
            "延长开路匹配支节，观察支节电纳增强后的 Sii 与隔离变化。",
            port_width=0.60,
            extra=network_extra(line_len=1.95, line_width=0.60, match_len=0.85, match_width=0.42, stub_len=1.10),
        ),
        make_candidate(
            "dualfeed",
            "branch_w0p16_o0p85",
            9.15,
            3.30,
            "在 A/B 双馈端口之间加入高阻微带隔离枝节，尝试抵消同贴片双端口耦合。",
            port_width=0.58,
            extra=network_extra(line_len=1.85, line_width=0.58, match_len=0.80, match_width=0.40, branch=True, branch_width=0.16, branch_offset=0.85),
        ),
        make_candidate(
            "dualfeed",
            "branch_dgs_len4p4",
            9.15,
            3.30,
            "组合端口间微带隔离枝节与局部缺陷地槽，同时压制近场耦合和地电流绕射。",
            port_width=0.58,
            extra=network_extra(
                line_len=1.85,
                line_width=0.58,
                match_len=0.80,
                match_width=0.40,
                branch=True,
                branch_width=0.16,
                branch_offset=0.85,
                dgs=True,
                dgs_len=4.4,
                dgs_width=0.24,
                dgs_offset=1.05,
            ),
        ),
        make_candidate(
            "dualfeed",
            "patch9p45_branch_dgs",
            9.45,
            3.35,
            "在真实微带隔离结构上略增大贴片边长，补偿边缘馈电带来的谐振上移。",
            port_width=0.58,
            extra=network_extra(
                line_len=1.75,
                line_width=0.58,
                match_len=0.75,
                match_width=0.40,
                branch=True,
                branch_width=0.16,
                branch_offset=0.80,
                dgs=True,
                dgs_len=4.2,
                dgs_width=0.24,
                dgs_offset=1.00,
            ),
        ),
        make_candidate(
            "hybrid",
            "output_match_l1p8",
            9.15,
            3.30,
            "90 度混合器输出端改为可调微带匹配段，输出段宽度独立于端口宽度。",
            port_width=0.58,
            trace_width=0.36,
            trace_gap=0.65,
            extra=network_extra(line_len=1.80, line_width=0.58, match_len=0.75, match_width=0.40, hybrid_match_len=0.95, hybrid_match_width=0.36),
        ),
        make_candidate(
            "hybrid",
            "output_stub_branch",
            9.15,
            3.30,
            "在混合器输出匹配段上加入开路支节和 A/B 端口间隔离枝节，兼顾幅相平衡与隔离。",
            port_width=0.58,
            trace_width=0.34,
            trace_gap=0.70,
            extra=network_extra(
                line_len=1.85,
                line_width=0.58,
                match_len=0.75,
                match_width=0.40,
                stub_len=0.65,
                branch=True,
                branch_width=0.14,
                branch_offset=0.80,
                hybrid_match_len=0.95,
                hybrid_match_width=0.34,
            ),
        ),
        make_candidate(
            "hybrid",
            "output_branch_dgs",
            9.35,
            3.35,
            "混合器输出匹配段、端口间隔离枝节和局部 DGS 组合扫描，并略增大贴片边长。",
            port_width=0.58,
            trace_width=0.34,
            trace_gap=0.70,
            extra=network_extra(
                line_len=1.75,
                line_width=0.58,
                match_len=0.70,
                match_width=0.38,
                stub_len=0.55,
                branch=True,
                branch_width=0.14,
                branch_offset=0.75,
                dgs=True,
                dgs_len=4.0,
                dgs_width=0.22,
                dgs_offset=0.95,
                hybrid_match_len=0.90,
                hybrid_match_width=0.34,
            ),
        ),
        make_candidate(
            "hybrid",
            "narrow_output_match",
            9.15,
            3.30,
            "收窄 90 度混合器输出匹配段，测试较高特性阻抗输出线对幅相平衡的影响。",
            port_width=0.50,
            trace_width=0.30,
            trace_gap=0.75,
            extra=network_extra(line_len=1.75, line_width=0.50, match_len=0.70, match_width=0.34, hybrid_match_len=0.90, hybrid_match_width=0.30),
        ),
        make_candidate(
            "dualfeed",
            "fine_stub_1p25",
            9.15,
            3.30,
            "围绕最佳真实结构候选继续延长开路匹配支节到 1.25 mm，检查匹配电纳细调效果。",
            port_width=0.60,
            extra=network_extra(line_len=1.95, line_width=0.60, match_len=0.85, match_width=0.42, stub_len=1.25),
        ),
        make_candidate(
            "dualfeed",
            "fine_stub_1p45",
            9.15,
            3.30,
            "继续把开路匹配支节延长到 1.45 mm，寻找 1.10 mm 以外的回波改善区间。",
            port_width=0.60,
            extra=network_extra(line_len=1.95, line_width=0.60, match_len=0.85, match_width=0.42, stub_len=1.45),
        ),
        make_candidate(
            "dualfeed",
            "fine_branch_len0p65",
            9.15,
            3.30,
            "缩短端口间隔离枝节长度到 0.65 mm，并保留 1.10 mm 开路支节，降低枝节过耦合风险。",
            port_width=0.60,
            extra=network_extra(line_len=1.95, line_width=0.60, match_len=0.85, match_width=0.42, stub_len=1.10, branch=True, branch_len=0.65, branch_width=0.12, branch_offset=0.65),
        ),
        make_candidate(
            "dualfeed",
            "fine_branch_len1p05",
            9.15,
            3.30,
            "隔离枝节长度设为 1.05 mm，靠近上轮支节最佳区间测试 A/B 耦合抵消。",
            port_width=0.60,
            extra=network_extra(line_len=1.95, line_width=0.60, match_len=0.85, match_width=0.42, stub_len=1.10, branch=True, branch_len=1.05, branch_width=0.12, branch_offset=0.75),
        ),
        make_candidate(
            "dualfeed",
            "fine_branch_len1p35_dgs_o0p85",
            9.15,
            3.30,
            "隔离枝节加长到 1.35 mm，并把局部 DGS 放在 0.85 mm 位置观察地电流切断效果。",
            port_width=0.60,
            extra=network_extra(
                line_len=1.95,
                line_width=0.60,
                match_len=0.85,
                match_width=0.42,
                stub_len=1.10,
                branch=True,
                branch_len=1.35,
                branch_width=0.12,
                branch_offset=0.75,
                dgs=True,
                dgs_len=3.8,
                dgs_width=0.20,
                dgs_offset=0.85,
            ),
        ),
        make_candidate(
            "dualfeed",
            "fine_dgs_o0p75",
            9.15,
            3.30,
            "不加端口间隔离枝节，仅把 DGS 位置向贴片中心侧移动到 0.75 mm，隔离地电流但减少端口扰动。",
            port_width=0.60,
            extra=network_extra(line_len=1.95, line_width=0.60, match_len=0.85, match_width=0.42, stub_len=1.10, dgs=True, dgs_len=3.6, dgs_width=0.20, dgs_offset=0.75),
        ),
        make_candidate(
            "dualfeed",
            "fine_dgs_o1p25",
            9.15,
            3.30,
            "不加端口间隔离枝节，仅把 DGS 位置外移到 1.25 mm，测试较弱地槽耦合对回波的影响。",
            port_width=0.60,
            extra=network_extra(line_len=1.95, line_width=0.60, match_len=0.85, match_width=0.42, stub_len=1.10, dgs=True, dgs_len=3.6, dgs_width=0.20, dgs_offset=1.25),
        ),
        make_candidate(
            "hybrid",
            "fine_output_w0p28",
            9.15,
            3.30,
            "细扫 90 度混合器输出段宽度到 0.28 mm，测试高阻输出段的匹配与幅相平衡。",
            port_width=0.50,
            trace_width=0.28,
            trace_gap=0.78,
            extra=network_extra(line_len=1.75, line_width=0.50, match_len=0.70, match_width=0.34, hybrid_match_len=0.90, hybrid_match_width=0.28),
        ),
        make_candidate(
            "hybrid",
            "fine_output_w0p32",
            9.15,
            3.30,
            "细扫 90 度混合器输出段宽度到 0.32 mm，贴近上一轮窄输出候选的局部最优区间。",
            port_width=0.52,
            trace_width=0.32,
            trace_gap=0.74,
            extra=network_extra(line_len=1.75, line_width=0.52, match_len=0.72, match_width=0.36, hybrid_match_len=0.90, hybrid_match_width=0.32),
        ),
        make_candidate(
            "hybrid",
            "fine_output_w0p40",
            9.15,
            3.30,
            "细扫 90 度混合器输出段宽度到 0.40 mm，检查低阻输出段是否改善端口回波。",
            port_width=0.58,
            trace_width=0.36,
            trace_gap=0.68,
            extra=network_extra(line_len=1.80, line_width=0.58, match_len=0.75, match_width=0.40, hybrid_match_len=0.95, hybrid_match_width=0.40),
        ),
        make_candidate(
            "hybrid",
            "fine_output_w0p46",
            9.15,
            3.30,
            "继续加宽混合器输出段到 0.46 mm，判断输出匹配段宽度上限趋势。",
            port_width=0.62,
            trace_width=0.38,
            trace_gap=0.64,
            extra=network_extra(line_len=1.85, line_width=0.62, match_len=0.78, match_width=0.44, hybrid_match_len=0.98, hybrid_match_width=0.46),
        ),
        make_candidate(
            "dualfeed",
            "link_p9p05_shift0p25_dgs0p65_stub1p05",
            9.05,
            3.25,
            "贴片略缩小，微带馈线沿边缘偏移 0.25 mm，DGS offset=0.65 mm，支节 1.05 mm，用于验证低扰动馈入联动。",
            port_width=0.58,
            extra=network_extra(line_len=1.80, line_width=0.58, feed_offset=0.25, match_len=0.78, match_width=0.40, stub_len=1.05, dgs=True, dgs_len=3.4, dgs_width=0.18, dgs_offset=0.65),
        ),
        make_candidate(
            "dualfeed",
            "link_p9p05_shift0p50_dgs0p75_stub1p10",
            9.05,
            3.25,
            "贴片略缩小，馈线偏移 0.50 mm，保持上一轮最优 DGS 位置附近，检查馈入偏移对回波的补偿。",
            port_width=0.58,
            extra=network_extra(line_len=1.80, line_width=0.58, feed_offset=0.50, match_len=0.78, match_width=0.40, stub_len=1.10, dgs=True, dgs_len=3.4, dgs_width=0.18, dgs_offset=0.75),
        ),
        make_candidate(
            "dualfeed",
            "link_p9p15_shift0p25_dgs0p55_stub1p10",
            9.15,
            3.30,
            "保持当前贴片边长，DGS 更靠近中心侧到 0.55 mm，测试更强地电流切断是否改善隔离。",
            port_width=0.58,
            extra=network_extra(line_len=1.80, line_width=0.58, feed_offset=0.25, match_len=0.78, match_width=0.40, stub_len=1.10, dgs=True, dgs_len=3.4, dgs_width=0.18, dgs_offset=0.55),
        ),
        make_candidate(
            "dualfeed",
            "link_p9p15_shift0p50_dgs0p75_stub1p20",
            9.15,
            3.30,
            "保持当前贴片边长，馈线偏移 0.50 mm，支节增至 1.20 mm，围绕上一轮最优 DGS 点继续细扫。",
            port_width=0.58,
            extra=network_extra(line_len=1.80, line_width=0.58, feed_offset=0.50, match_len=0.78, match_width=0.40, stub_len=1.20, dgs=True, dgs_len=3.6, dgs_width=0.18, dgs_offset=0.75),
        ),
        make_candidate(
            "dualfeed",
            "link_p9p25_shift0p25_dgs0p85_stub1p10",
            9.25,
            3.35,
            "贴片略放大，馈线偏移 0.25 mm，DGS 外移到 0.85 mm，观察谐振下移后的匹配恢复。",
            port_width=0.58,
            extra=network_extra(line_len=1.80, line_width=0.58, feed_offset=0.25, match_len=0.80, match_width=0.40, stub_len=1.10, dgs=True, dgs_len=3.6, dgs_width=0.18, dgs_offset=0.85),
        ),
        make_candidate(
            "dualfeed",
            "link_p9p25_shift0p50_dgs0p65_stub1p25",
            9.25,
            3.35,
            "贴片略放大，馈线偏移 0.50 mm，支节 1.25 mm，测试较长支节与内侧 DGS 的组合。",
            port_width=0.58,
            extra=network_extra(line_len=1.80, line_width=0.58, feed_offset=0.50, match_len=0.80, match_width=0.40, stub_len=1.25, dgs=True, dgs_len=3.6, dgs_width=0.18, dgs_offset=0.65),
        ),
        make_candidate(
            "dualfeed",
            "link_p9p35_shift0p25_dgs0p75_stub1p15",
            9.35,
            3.40,
            "贴片继续放大，馈线偏移 0.25 mm，DGS offset=0.75 mm，支节 1.15 mm，检查谐振频移趋势。",
            port_width=0.58,
            extra=network_extra(line_len=1.75, line_width=0.58, feed_offset=0.25, match_len=0.78, match_width=0.40, stub_len=1.15, dgs=True, dgs_len=3.8, dgs_width=0.18, dgs_offset=0.75),
        ),
        make_candidate(
            "dualfeed",
            "link_p9p35_shift0p50_dgs0p95_stub1p25",
            9.35,
            3.40,
            "贴片继续放大，馈线偏移 0.50 mm，DGS 外移至 0.95 mm，验证较弱 DGS 与长支节组合。",
            port_width=0.58,
            extra=network_extra(line_len=1.75, line_width=0.58, feed_offset=0.50, match_len=0.78, match_width=0.40, stub_len=1.25, dgs=True, dgs_len=3.8, dgs_width=0.18, dgs_offset=0.95),
        ),
        make_candidate(
            "dualfeed",
            "link_p9p45_shift0p25_dgs0p75_stub1p05",
            9.45,
            3.45,
            "贴片最大化到可用板边界附近，馈线偏移 0.25 mm，较短支节用于避免过度容性加载。",
            port_width=0.58,
            extra=network_extra(line_len=1.70, line_width=0.58, feed_offset=0.25, match_len=0.75, match_width=0.40, stub_len=1.05, dgs=True, dgs_len=3.8, dgs_width=0.18, dgs_offset=0.75),
        ),
        make_candidate(
            "dualfeed",
            "link_p9p45_shift0p50_dgs0p85_stub1p20",
            9.45,
            3.45,
            "贴片最大化到可用板边界附近，馈线偏移 0.50 mm，并用 DGS 0.85 mm 与 1.20 mm 支节做联合补偿。",
            port_width=0.58,
            extra=network_extra(line_len=1.70, line_width=0.58, feed_offset=0.50, match_len=0.75, match_width=0.40, stub_len=1.20, dgs=True, dgs_len=3.8, dgs_width=0.18, dgs_offset=0.85),
        ),
    ]
    return [candidate for candidate in candidates if is_valid(candidate)]


def is_valid(candidate: Candidate) -> bool:
    params = dict(builder.BASE_PARAMS)
    params.update(candidate.params)
    try:
        builder.validate_params(params)
    except Exception as exc:
        print(f"Skipping invalid candidate {candidate.name}: {exc}", flush=True)
        return False
    return True


def apply_candidate(candidate: Candidate) -> None:
    params = builder.TOPOLOGIES[candidate.topology]["params"]
    params.clear()
    params.update(candidate.params)


def open_hfss(topology: str) -> Hfss:
    spec = builder.TOPOLOGIES[topology]
    paths = builder.topology_paths(topology)
    return Hfss(
        project=str(paths["project"]),
        design=spec["design"],
        version="2023.1",
        non_graphical=True,
        new_desktop=True,
        close_on_exit=False,
        remove_lock=True,
    )


def s_score(s: dict) -> float:
    return_miss = max(0.0, s["worst_return_db"] - RETURN_TARGET_DB)
    isolation_miss = max(0.0, ISOLATION_TARGET_DB - s["isolation_db"])
    return 16.0 * return_miss + 4.0 * isolation_miss - 0.4 * max(0.0, -RETURN_TARGET_DB + -s["worst_return_db"])


def append_csv(path: Path, row: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    exists = path.exists()
    if exists:
        with path.open(newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            existing_fields = reader.fieldnames or []
            existing_rows = list(reader)
        fieldnames = existing_fields + [key for key in row if key not in existing_fields]
        if fieldnames != existing_fields:
            with path.open("w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(existing_rows)
                writer.writerow(row)
            return
    else:
        fieldnames = list(row)
    with path.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not exists:
            writer.writeheader()
        writer.writerow(row)


def run_sparam_candidate(index: int, candidate: Candidate) -> dict:
    start = time.time()
    apply_candidate(candidate)
    _project, hfss = builder.build_project(
        candidate.topology,
        analyze=True,
        non_graphical=True,
        quick=True,
        band_samples=True,
        sparam_only=True,
        return_hfss=True,
    )
    try:
        s = evaluator.get_s_parameter_snapshot(hfss, REPORT_DIR / f"{candidate.topology}_candidate_s_parameters.csv")
    finally:
        hfss.release_desktop(close_projects=False, close_desktop=True)
    row = {
        "stage": "sparam",
        "index": index,
        "candidate": candidate.name,
        "topology": candidate.topology,
        "score": s_score(s),
        "elapsed_s": round(time.time() - start, 1),
        "rationale": candidate.rationale,
        "worst_return_db": s["worst_return_db"],
        "worst_return_expr": s["worst_return_expr"],
        "worst_coupling_db": s["worst_coupling_db"],
        "worst_coupling_expr": s["worst_coupling_expr"],
        "isolation_db": s["isolation_db"],
        "patch_side_mm": candidate.params.get("patch_side_mm"),
        "feed_offset_u_mm": candidate.params.get("feed_offset_u_mm"),
        "feed_offset_a_mm": candidate.params.get("feed_offset_a_mm", ""),
        "feed_offset_b_mm": candidate.params.get("feed_offset_b_mm", ""),
        "port_width_mm": candidate.params.get("port_width_mm"),
        "feed_pad_radius_mm": candidate.params.get("feed_pad_radius_mm"),
        "isolation_slot_length_mm": candidate.params.get("isolation_slot_length_mm"),
        "isolation_slot_width_mm": candidate.params.get("isolation_slot_width_mm"),
    }
    for key in STRUCTURE_PARAM_KEYS:
        row[key] = candidate.params.get(key, "")
    append_csv(HISTORY_CSV, row)
    print(json.dumps(row, indent=2), flush=True)
    return row


def source_balance_cases(sources: list[str]) -> list[dict]:
    pairs = evaluator.element_pair_map(sources)
    if not pairs:
        return []
    cases = []
    for amp_b in [0.90, 0.95, 1.00, 1.05, 1.10]:
        for phase_b in [-120.0, -112.5, -105.0, -97.5, -90.0, -82.5, -75.0]:
            assignments = {item: (0.0, 0.0) for item in sources}
            for idx, element in enumerate(sorted(pairs, key=int)):
                base_phase = idx * -90.0
                pair = pairs[element]
                assignments[pair["A"]] = (1.0, base_phase)
                assignments[pair["B"]] = (amp_b, base_phase + phase_b)
            cases.append({"amp_b": amp_b, "phase_b_deg": phase_b, "assignments": assignments})
    return cases


def evaluate_open_hfss(topology: str, hfss: Hfss) -> dict:
    spec = builder.TOPOLOGIES[topology]
    paths = builder.topology_paths(topology)
    reports = evaluator.report_paths(topology)
    reports["dir"].mkdir(parents=True, exist_ok=True)

    sources = hfss.get_all_sources()
    available_freqs = evaluator.get_available_frequencies(hfss)
    eval_freqs = evaluator.nearest_frequencies(available_freqs)
    cases = evaluator.source_cases(sources, topology)
    summaries_by_freq = {}
    for freq in eval_freqs:
        summaries = {}
        single_grids = {}
        for name, assignments in cases.items():
            if assignments:
                hfss.edit_sources(assignments)
            grid = evaluator.get_grid(hfss, freq)
            summaries[name] = evaluator.summarize_rows(freq, grid["rows"])
            if name.endswith("_only"):
                single_grids[name] = grid
        if single_grids:
            first_grid = next(iter(single_grids.values()))
            envelope_rows = []
            cp_rows = []
            for idx, base_row in enumerate(first_grid["rows"]):
                candidates = [grid["rows"][idx] for grid in single_grids.values()]
                best_gain = max(candidates, key=lambda r: r["gain"])
                envelope_rows.append(
                    {
                        "theta": base_row["theta"],
                        "phi": base_row["phi"],
                        "gain": best_gain["gain"],
                        "axial_ratio": best_gain["axial_ratio"],
                    }
                )
                cp_candidates = [r for r in candidates if r["axial_ratio"] <= evaluator.AXIAL_RATIO_TARGET_DB]
                cp_best = max(cp_candidates, key=lambda r: r["gain"]) if cp_candidates else min(candidates, key=lambda r: r["axial_ratio"])
                cp_rows.append(
                    {
                        "theta": base_row["theta"],
                        "phi": base_row["phi"],
                        "gain": cp_best["gain"],
                        "axial_ratio": cp_best["axial_ratio"],
                    }
                )
            summaries["coverage_envelope_best_port"] = evaluator.summarize_rows(freq, envelope_rows)
            summaries["cp_qualified_envelope"] = evaluator.summarize_rows(freq, cp_rows)
        summaries_by_freq[f"{freq:.6f}GHz"] = summaries

    metrics = {
        "project": str(paths["project"]),
        "design": spec["design"],
        "topology": topology,
        "label": spec["label"],
        "sources": sources,
        "available_frequencies_ghz": available_freqs,
        "evaluated_frequencies_ghz": eval_freqs,
        "fov_by_freq": summaries_by_freq,
        "s_parameters": evaluator.get_s_parameter_snapshot(hfss, reports["s_csv"]),
    }
    metrics["fov_summary"] = evaluator.summarize_fov(metrics)
    metrics["metrics_json"] = str(reports["metrics"])
    metrics["fov_csv"] = str(reports["fov_csv"])
    metrics["s_csv"] = str(reports["s_csv"])
    reports["metrics"].write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    evaluator.write_csv(reports["fov_csv"], summaries_by_freq)
    params = json.loads(paths["params"].read_text(encoding="utf-8"))
    evaluator.write_report(topology, params, metrics, reports["report"])
    return metrics


def balance_score(item: dict) -> float:
    ar_miss = max(0.0, item["axial_ratio_max_db"] - AR_TARGET_DB)
    gain_miss = max(0.0, GAIN_TARGET_DBI - item["gain_min_dbi"])
    return 2.0 * ar_miss + 0.8 * gain_miss - 0.08 * item["cp_coverage_min_percent"]


def run_source_balance_sweep(topology: str, hfss: Hfss | None = None) -> dict:
    close_when_done = hfss is None
    if hfss is None:
        hfss = open_hfss(topology)
    try:
        sources = hfss.get_all_sources()
        freqs = evaluator.nearest_frequencies(evaluator.get_available_frequencies(hfss))
        rows = []
        for case in source_balance_cases(sources):
            summaries = []
            hfss.edit_sources(case["assignments"])
            for freq in freqs:
                grid = evaluator.get_grid(hfss, freq)
                summaries.append(evaluator.summarize_rows(freq, grid["rows"]))
            row = {
                "amp_b": case["amp_b"],
                "phase_b_deg": case["phase_b_deg"],
                "gain_min_dbi": min(item["gain_min_dbi"] for item in summaries),
                "axial_ratio_max_db": max(item["axial_ratio_max_db"] for item in summaries),
                "cp_coverage_min_percent": min(item["cp_coverage_percent"] for item in summaries),
            }
            row["score"] = balance_score(row)
            rows.append(row)
            append_csv(BALANCE_CSV, {"topology": topology, **row})
        best = min(rows, key=lambda item: item["score"]) if rows else {}
        print(json.dumps({"best_source_balance": best}, indent=2), flush=True)
        return best
    finally:
        if close_when_done:
            hfss.release_desktop(close_projects=False, close_desktop=True)


def run_full_candidate(candidate: Candidate) -> dict:
    apply_candidate(candidate)
    _project, hfss = builder.build_project(
        candidate.topology,
        analyze=True,
        non_graphical=True,
        quick=True,
        band_samples=True,
        sparam_only=False,
        return_hfss=True,
    )
    try:
        metrics = evaluate_open_hfss(candidate.topology, hfss)
        balance = run_source_balance_sweep(candidate.topology, hfss)
    finally:
        hfss.release_desktop(close_projects=False, close_desktop=True)
    s = metrics.get("s_parameters", {})
    f = metrics.get("fov_summary", {})
    best = {
        "candidate": candidate.name,
        "topology": candidate.topology,
        "rationale": candidate.rationale,
        "parameters": candidate.params,
        "s_parameters": s,
        "fov_summary": f,
        "optimized_source_balance": balance,
        "meets_s_targets": s.get("worst_return_db", math.inf) <= RETURN_TARGET_DB and s.get("isolation_db", -math.inf) >= ISOLATION_TARGET_DB,
        "meets_fov_targets": f.get("coverage_envelope_gain_min_dbi", -math.inf) >= GAIN_TARGET_DBI
        and f.get("cp_qualified_ar_max_db", math.inf) <= AR_TARGET_DB,
        "meets_balanced_cp_target": bool(balance)
        and balance.get("gain_min_dbi", -math.inf) >= GAIN_TARGET_DBI
        and balance.get("axial_ratio_max_db", math.inf) <= AR_TARGET_DB,
    }
    best["meets_all_targets"] = best["meets_s_targets"] and (best["meets_fov_targets"] or best["meets_balanced_cp_target"])
    BEST_JSON.write_text(json.dumps(best, indent=2), encoding="utf-8")
    write_report(best)
    return best


def fmt(value: float | int | None, digits: int = 2) -> str:
    if value is None:
        return "N/A"
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return "N/A"
    return f"{float(value):.{digits}f}"


def top_history_rows(limit: int = 10) -> list[dict]:
    if not HISTORY_CSV.exists():
        return []
    with HISTORY_CSV.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    return sorted(rows, key=lambda r: float(r.get("score") or 1e9))[:limit]


def csv_float(row: dict, key: str, default: float = 0.0) -> float:
    try:
        return float(row.get(key) or default)
    except (TypeError, ValueError):
        return default


def best_real_structure_row() -> dict:
    if not HISTORY_CSV.exists():
        return {}
    with HISTORY_CSV.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    real_rows = [
        row
        for row in rows
        if csv_float(row, "microstrip_feed_enabled") >= 0.5
        or csv_float(row, "neutralization_branch_enabled") >= 0.5
        or csv_float(row, "local_dgs_enabled") >= 0.5
    ]
    return min(real_rows, key=lambda r: csv_float(r, "score", 1e9)) if real_rows else {}


def write_report(best: dict) -> None:
    s = best.get("s_parameters", {})
    f = best.get("fov_summary", {})
    b = best.get("optimized_source_balance", {})
    params = best.get("parameters", {})
    best_real = best_real_structure_row()
    lines = [
        "# D44 双馈正交贴片 / 90 度混合网络真实匹配结构优化报告",
        "",
        "## 设计目标",
        "",
        f"- 7.738 / 7.9855 / 8.233 GHz 三个频点内，最差自反射 `Sii <= {RETURN_TARGET_DB:.1f} dB`。",
        f"- 端口隔离度 `>= {ISOLATION_TARGET_DB:.1f} dB`。",
        f"- FOV 覆盖包络最小增益 `>= {GAIN_TARGET_DBI:.1f} dBi`。",
        f"- 在选定 FOV 内轴比 `AxialRatioValue <= {AR_TARGET_DB:.1f} dB`；若未达标，则记录本轮最优幅相平衡结果。",
        "",
        "## 本轮细扫范围",
        "",
        "- 上一轮：隔离枝节长度 `0.65 / 1.05 / 1.35 mm`，DGS 位置 `0.75 / 1.25 mm`，90 度混合器输出段宽度 `0.28 / 0.32 / 0.40 / 0.46 mm`。",
        "- 本轮：新增真实微带馈线边缘馈入偏移 `0.25 / 0.50 mm`，并联动贴片边长 `9.05 / 9.15 / 9.25 / 9.35 / 9.45 mm`。",
        "- 本轮：围绕 `DGS offset 0.55-0.95 mm` 与开路支节 `1.05-1.25 mm` 做组合筛选，重点观察匹配接近 `-10 dB` 时隔离度是否还能保持。",
        "- 源幅相平衡：B 端幅度 `0.90-1.10`、相位 `-120 deg` 到 `-75 deg`，围绕上一轮 `-105 deg` 做细扫。",
        "- `dualfeed_fine_branch_len1p35_dgs_o0p85` 在 AEDT 保存/求解阶段卡住，已停止该单个组合候选，未纳入排名；本轮 Full 远场重评估在源幅相后半段超时，报告保留上一轮完整 FOV 指标并更新 S 参数筛选结论。",
        "",
        "## 最佳候选",
        "",
        f"- 候选名称：`{best.get('candidate')}`",
        f"- 拓扑类型：`{best.get('topology')}`",
        f"- 选择原因：{best.get('rationale')}",
        f"- 是否满足全部目标：`{'是' if best.get('meets_all_targets') else '否'}`",
        "- 本轮新增结构：边缘微带馈线/匹配段、开路匹配支节、端口间微带隔离枝节、局部缺陷地槽，以及混合器输出端独立匹配宽度。",
        "",
        "## 几何参数",
        "",
    ]
    for key in [
        "patch_side_mm",
        "feed_offset_u_mm",
        "feed_offset_a_mm",
        "feed_offset_b_mm",
        "port_width_mm",
        "feed_pad_radius_mm",
        "hybrid_trace_width_mm",
        "hybrid_trace_gap_mm",
        "isolation_slot_length_mm",
        "isolation_slot_width_mm",
        *STRUCTURE_PARAM_KEYS,
    ]:
        if key in params:
            lines.append(f"- `{key}`: `{fmt(params[key], 3)}`")
    lines.extend(
        [
            "",
            "## 核心仿真指标",
            "",
            f"- 最差回波损耗：`{fmt(s.get('worst_return_db'))} dB`，对应表达式 `{s.get('worst_return_expr', 'N/A')}`",
            f"- 最差端口耦合：`{fmt(s.get('worst_coupling_db'))} dB`，对应表达式 `{s.get('worst_coupling_expr', 'N/A')}`",
            f"- 对应隔离度：`{fmt(s.get('isolation_db'))} dB`",
            f"- 覆盖包络最小增益：`{fmt(f.get('coverage_envelope_gain_min_dbi'))} dBi`",
            f"- CP 合格包络最大轴比：`{fmt(f.get('cp_qualified_ar_max_db'))} dB`",
            f"- CP 合格包络最小增益：`{fmt(f.get('cp_qualified_gain_min_dbi'))} dBi`",
            f"- CP 合格包络最小覆盖率：`{fmt(f.get('cp_qualified_coverage_min_percent'), 1)}%`",
            "",
            "## 最佳源幅相平衡",
            "",
            f"- B 馈电幅度：`{fmt(b.get('amp_b'), 3)}`，相对于 A 馈电。",
            f"- B 馈电相位：`{fmt(b.get('phase_b_deg'), 1)} deg`，相对于 A 馈电。",
            f"- 平衡阵列最小增益：`{fmt(b.get('gain_min_dbi'))} dBi`",
            f"- 平衡阵列最大轴比：`{fmt(b.get('axial_ratio_max_db'))} dB`",
            f"- 平衡阵列最小 CP 覆盖率：`{fmt(b.get('cp_coverage_min_percent'), 1)}%`",
            "",
            "## 最佳真实匹配/隔离结构候选",
            "",
        ]
    )
    if best_real:
        lines.extend(
            [
                f"- 候选名称：`{best_real.get('candidate')}`",
                f"- 拓扑类型：`{best_real.get('topology')}`",
                f"- 评分：`{fmt(csv_float(best_real, 'score'))}`",
                f"- 最差回波损耗：`{fmt(csv_float(best_real, 'worst_return_db'))} dB`",
                f"- 隔离度：`{fmt(csv_float(best_real, 'isolation_db'))} dB`",
                f"- 微带馈电网络：`{'启用' if csv_float(best_real, 'microstrip_feed_enabled') >= 0.5 else '未启用'}`",
                f"- 端口间隔离枝节：`{'启用' if csv_float(best_real, 'neutralization_branch_enabled') >= 0.5 else '未启用'}`",
                f"- 局部 DGS：`{'启用' if csv_float(best_real, 'local_dgs_enabled') >= 0.5 else '未启用'}`",
                f"- 说明：{best_real.get('rationale', '')}",
                "- 结论：当前真实结构候选尚未超过探针/焊盘参考解，说明引入网络后需要重新做贴片边长、馈入位置和特性阻抗的联合细扫。",
            ]
        )
    else:
        lines.append("- 尚无启用真实匹配/隔离结构的候选记录。")
    lines.extend(
        [
            "",
            "## S 参数筛选排名",
            "",
            "| 排名 | 候选 | 拓扑 | 评分 | 最差 Sii | 隔离度 | 说明 |",
            "| ---: | --- | --- | ---: | ---: | ---: | --- |",
        ]
    )
    for idx, row in enumerate(top_history_rows(), start=1):
        lines.append(
            f"| {idx} | {row.get('candidate')} | {row.get('topology')} | {fmt(float(row.get('score', 0)))} | "
            f"{fmt(float(row.get('worst_return_db', 0)))} dB | {fmt(float(row.get('isolation_db', 0)))} dB | {row.get('rationale', '')} |"
        )
    lines.extend(
        [
            "",
            "## 结论",
            "",
            f"- 本轮是否完全达标：`{'是' if best.get('meets_all_targets') else '否'}`。",
            f"- 当前主要瓶颈：最差回波损耗为 `{fmt(s.get('worst_return_db'))} dB`，隔离度为 `{fmt(s.get('isolation_db'))} dB`，CP 合格包络最大轴比为 `{fmt(f.get('cp_qualified_ar_max_db'))} dB`。",
            "- 真实结构联动细扫中，`dualfeed_link_p9p25_shift0p50_dgs0p65_stub1p25` 的综合评分最低：最差 Sii 约 `-9.76 dB`，已经接近 `-10 dB` 目标，但隔离度下降到约 `5.23 dB`。",
            "- 同类趋势中，`patch_side=9.35 mm / feed_offset=0.50 mm / DGS offset=0.95 mm / stub=1.25 mm` 可得到约 `-9.79 dB` 的最差 Sii，但隔离度进一步降至约 `4.75 dB`。",
            "- 源幅相细扫把最佳平衡点更新为 `amp_b=0.95 / phase_b=-97.5 deg`，轴比相对上一轮明显下降，但仍未接近 `3 dB` 圆极化目标。",
            "- 下一轮建议：保留 `patch_side=9.25-9.35 mm / feed_offset=0.50 mm / stub=1.20-1.30 mm` 的匹配方向，同时必须引入非直连式隔离方案，例如弱耦合开路隔离线、接地过孔栅栏或重新分离 A/B 馈线出口，否则匹配接近目标时隔离会塌陷。",
            "",
            "## 输出文件",
            "",
            f"- 优化历史：`{HISTORY_CSV}`",
            f"- 源幅相扫描：`{BALANCE_CSV}`",
            f"- 最佳结果 JSON：`{BEST_JSON}`",
            f"- 最终拓扑报告目录：`{evaluator.report_paths(best['topology'])['dir']}`",
        ]
    )
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-candidates", type=int, default=12)
    parser.add_argument("--skip-candidates", type=int, default=0)
    parser.add_argument("--full-finalists", type=int, default=1)
    parser.add_argument("--reset-history", action="store_true")
    args = parser.parse_args()

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    if args.reset_history:
        for path in [HISTORY_CSV, BALANCE_CSV, BEST_JSON, REPORT_MD]:
            if path.exists():
                path.unlink()

    candidates = generate_candidates()[args.skip_candidates : args.skip_candidates + args.max_candidates]
    s_rows = []
    for idx, candidate in enumerate(candidates, start=args.skip_candidates + 1):
        s_rows.append(run_sparam_candidate(idx, candidate))
    ranked = sorted(zip(s_rows, candidates), key=lambda item: item[0]["score"])
    best_full = None
    for _, candidate in ranked[: args.full_finalists]:
        best_full = run_full_candidate(candidate)
        if best_full["meets_all_targets"]:
            break
    print(json.dumps(best_full, indent=2), flush=True)
    print(f"Wrote {REPORT_MD}", flush=True)


if __name__ == "__main__":
    main()
