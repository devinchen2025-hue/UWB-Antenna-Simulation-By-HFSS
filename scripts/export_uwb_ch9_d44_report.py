from __future__ import annotations

import json
from pathlib import Path

from ansys.aedt.core import Hfss

import export_uwb_ch9_report as base


ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = ROOT / "reports_d44"

base.PROJECT_PATH = ROOT / "UWB_CH9_Diamond_CP_Array_D44.aedt"
base.PARAM_PATH = ROOT / "UWB_CH9_Diamond_CP_Array_D44_params.json"
base.REPORT_DIR = REPORT_DIR
base.S_CSV = REPORT_DIR / "UWB_CH9_D44_s_parameters.csv"
base.FARFIELD_CSV = REPORT_DIR / "UWB_CH9_D44_farfield_summary.csv"
base.METRICS_JSON = REPORT_DIR / "UWB_CH9_D44_metrics.json"
base.REPORT_MD = REPORT_DIR / "UWB_CH9_D44_simulation_report.md"
base.DESIGN = "Array4_Diamond_D44"
base.SOLUTION = "Setup_CH9 : Sweep_CH9"
base.SPHERE = "Upper_Hemisphere_5deg"


def status_pass(condition: bool) -> str:
    return "通过" if condition else "未通过"


def write_chinese_report(params: dict, metrics: dict) -> None:
    s = metrics["s_parameters"]
    gd = metrics["group_delay_proxy"]
    ff = metrics["farfield_summary"]
    p = params["parameters"]

    lines = [
        "# UWB CH9 菱形阵列 D44 圆形 PCB 约束版 HFSS 仿真报告",
        "",
        "## 项目信息",
        "",
        f"- AEDT 项目文件：`{base.PROJECT_PATH}`",
        f"- 设计名称：`{base.DESIGN}`",
        "- 自动化使用的 AEDT 版本：2023.1",
        "- Python/PyAEDT 自动化接口：`ansys.aedt.core`",
        "- 本版本与原 `UWB_CH9_Diamond_CP_Array.aedt` 独立保存，原版本未覆盖。",
        "",
        "## 几何模型概览",
        "",
        "- 拓扑结构：四个微带馈电平面 UWB 单极子阵元，采用菱形布阵。",
        f"- PCB 尺寸约束：圆形 PCB，直径 `{p['board_diameter_mm']} mm`",
        f"- 最近邻阵元间距：`{params['nearest_neighbor_spacing_mm']} mm`",
        f"- 介质材料：近似 RO4350B，厚度 h=`{p['substrate_h_mm']} mm`，相对介电常数 epsr=`{p['epsr']}`，损耗角正切 tan_delta=`{p['tan_delta']}`",
        f"- 辐射圆盘半径：`{p['disc_radius_mm']} mm`",
        f"- 馈线宽度：`{p['feed_w_mm']} mm`",
        f"- 局部地宽度/缝隙：`{p['partial_ground_w_mm']} mm` / `{p['partial_ground_gap_mm']} mm`",
        f"- 馈电端口距圆板边缘内缩：`{p['edge_clearance_mm']} mm`",
        "",
        "## 指标检查",
        "",
        "| 指标项 | 目标 | 仿真结果 | 状态 |",
        "| --- | --- | --- | --- |",
        f"| S11/S22/S33/S44 | 7.7-8.3 GHz 内 < -10 dB | 最差为 `{base.fmt(s['worst_return_db'])} dB`，出现在 `{s['worst_return_expr']}` | {status_pass(s['worst_return_db'] < -10)} |",
        f"| CH9 标称频段回波损耗 | 7.738-8.233 GHz 内 < -10 dB | 最差为 `{base.fmt(s['ch9_worst_return_db'])} dB`，出现在 `{s['ch9_worst_return_expr']}` | {status_pass(s['ch9_worst_return_db'] < -10)} |",
        f"| 阵元隔离度 | > 25 dB | 最差耦合为 `{base.fmt(s['worst_coupling_db'])} dB`，对应隔离度 `{base.fmt(s['isolation_db'])} dB`，出现在 `{s['worst_coupling_expr']}` | {status_pass(s['isolation_db'] > 25)} |",
        f"| 群时延 | < 100 ps | 基于 Sij 相位的代理计算最大绝对值为 `{base.fmt(gd['worst_max_abs_ps'])} ps`，出现在 `{gd['worst_term']}` | {'通过，代理值' if gd['worst_max_abs_ps'] < 100 else '未通过，代理值'} |",
        "| 圆极化 / 轴比 | 全频段 AR <= 3 dB | 已导出默认源激励下的远场轴比；当前单馈单极子拓扑不是已验证的圆极化阵元 | 未满足，需重新设计 |",
        "| 上半球增益覆盖 | 边缘最小增益 >= -5 dBi，增益不圆度 <= 3 dB | 已导出默认源激励下的远场摘要；尚不是最终单端口或相控合成源签核结果 | 需要专门源激励设置 |",
        "| 相位中心稳定性 | +/-0.2 mm | 本轮自动化未提取该指标 | 未验证 |",
        "| 保真度因子 | >= 99% | 本轮未提取；需要建立时域双天线脉冲相关仿真流程 | 未验证 |",
        "",
        "## S 参数详情",
        "",
        f"- 完整 S 参数 CSV：`{base.S_CSV}`",
        f"- 7.7-8.3 GHz 内最差回波损耗项：`{s['worst_return_expr']}` = `{base.fmt(s['worst_return_db'])} dB`",
        f"- CH9 标称频段内最差回波损耗项：`{s['ch9_worst_return_expr']}` = `{base.fmt(s['ch9_worst_return_db'])} dB`",
        f"- 7.7-8.3 GHz 内最差耦合项：`{s['worst_coupling_expr']}` = `{base.fmt(s['worst_coupling_db'])} dB`",
        "",
        "7.7-8.3 GHz 内各端口最差回波损耗如下：",
        "",
    ]
    for expr, value in sorted(s["self_worst_db"].items()):
        lines.append(f"- `{expr}`：`{base.fmt(value)} dB`")

    lines.extend([
        "",
        "## 远场摘要",
        "",
        f"- 远场摘要 CSV：`{base.FARFIELD_CSV}`",
        "- 说明：以下远场值使用 HFSS 默认源上下文和 `Upper_Hemisphere_5deg` 远场球导出。最终天线方向图签核仍需要为单端口激励或相位合成激励建立专门的源上下文。",
        "",
        "| 频率 | GainTotal 最小值/最大值/起伏 | RealizedGainTotal 最小值/最大值 | AxialRatioValue 最小值/最大值 |",
        "| --- | --- | --- | --- |",
    ])
    for freq, row in ff["samples"].items():
        lines.append(
            "| "
            + freq
            + " | "
            + f"{row['GainTotal_min_dBi']} / {row['GainTotal_max_dBi']} / {row['GainTotal_ripple_dB']} dB"
            + " | "
            + f"{row['RealizedGainTotal_min_dBi']} / {row['RealizedGainTotal_max_dBi']} dBi"
            + " | "
            + f"{row['AxialRatioValue_min']} / {row['AxialRatioValue_max']}"
            + " |"
        )

    lines.extend([
        "",
        "## 工程说明",
        "",
        "- D44 版本在原有四阵元菱形布阵基础上，将 PCB 外形约束为直径 44 mm 的圆形板。",
        "- 由于圆板边缘更靠近馈电端口，馈电端口和局部地已向板内收缩，以避免端口矩形超出圆形 PCB 轮廓。",
        "- 该版本优先优化 S 参数匹配；隔离度、圆极化、相位中心和保真度仍需要专门的结构与源激励设计来进一步满足。",
    ])

    base.REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    lock = base.PROJECT_PATH.with_suffix(".aedt.lock")
    if lock.exists():
        lock.unlink()

    params = json.loads(base.PARAM_PATH.read_text(encoding="utf-8"))
    hfss = Hfss(
        project=str(base.PROJECT_PATH),
        design=base.DESIGN,
        version="2023.1",
        non_graphical=True,
        new_desktop=True,
        close_on_exit=False,
        remove_lock=True,
    )
    try:
        s_metrics = base.export_s_parameters(hfss)
        group_delay = base.export_group_delay_proxy(hfss, s_metrics)
        farfield = base.export_farfield_summary(hfss, s_metrics)
        metrics = {
            "project": str(base.PROJECT_PATH),
            "design": base.DESIGN,
            "s_parameters": {k: v for k, v in s_metrics.items() if k != "s_data_db"},
            "group_delay_proxy": group_delay,
            "farfield_summary": farfield,
        }
        base.METRICS_JSON.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
        write_chinese_report(params, metrics)
    finally:
        hfss.release_desktop(close_projects=False, close_desktop=True)

    print(f"Wrote {base.S_CSV}")
    print(f"Wrote {base.FARFIELD_CSV}")
    print(f"Wrote {base.METRICS_JSON}")
    print(f"Wrote {base.REPORT_MD}")


if __name__ == "__main__":
    main()
