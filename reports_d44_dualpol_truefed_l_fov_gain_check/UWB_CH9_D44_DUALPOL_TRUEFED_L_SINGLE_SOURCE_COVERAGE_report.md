# D44 candidate 37 逐源覆盖增益复核报告

## 复核口径

- 复核对象：`fold0p6_neck1p6_stub2p6`，A_ON/B_ON 两个 absorptive 50 ohm 工作态。
- 复核方法：每个可选源单独重建 HFSS 工程，仅保留该源为 lumped port，其余 A/B/L 源在同位置变为 50 ohm/RLC 端接；随后用 AEDT 原生命令导出默认远场。
- 复核原因：AEDT 2023.1 的 `EditSources`/PyAEDT 后处理在源切换路径仍会挂起或中断；本方法不依赖源切换接口。
- FOV：Theta `45..90 deg`，Phi `0..360 deg`，频点 `8 GHz`。
- 完成源数：`16/16`。

## 核心指标

- 严格逐源最小 GainTotal：`-20.180 dBi`。
- 严格逐源最小 RealizedGainTotal：`-20.487 dBi`。
- 覆盖口径最小 GainTotal：`1.518 dBi`。
- 覆盖口径最小 RealizedGainTotal：`1.433 dBi`。
- 全端口 native 复跑最差工作源 S11：`-15.125 dB`。
- 全端口 native 复跑最差 L 源 S11：`-12.976 dB`。

## 达标判断

- 严格逐源增益：`未达标`。
- 端口选择覆盖增益：`达标`。
- S11：`达标`。
- 综合结论：`达标`。

## 最差点

- 严格 Realized 最差：`A_ON_absorptive_50ohm_c0p08pf` / `P4A` / 8.0000 GHz / Theta 90 deg / Phi 70 deg。
- 覆盖 Realized 最差：`A_ON_absorptive_50ohm_c0p08pf` / best source `P4L` / 8.0000 GHz / Theta 45 deg / Phi 0 deg。

## 工程判断

- 逐源覆盖和全端口 S11 同时达标；当前结构可进入端口选择策略、开关链路损耗和标定误差预算验证。
- 当前电脑内存不是本次挂起主因：此前 4 核/4 任务求解完成时内存余量仍约 11 GB，卡点集中在源切换后的后处理接口。

## 输出文件

- 汇总 CSV：`D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_dualpol_truefed_l_fov_gain_check\UWB_CH9_D44_DUALPOL_TRUEFED_L_SINGLE_SOURCE_COVERAGE_summary.csv`
- 逐源 CSV：`D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_dualpol_truefed_l_fov_gain_check\UWB_CH9_D44_DUALPOL_TRUEFED_L_SINGLE_SOURCE_COVERAGE_source_summary.csv`
- 覆盖汇总 CSV：`D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_dualpol_truefed_l_fov_gain_check\UWB_CH9_D44_DUALPOL_TRUEFED_L_SINGLE_SOURCE_COVERAGE_coverage_summary.csv`
- 覆盖方向点 CSV：`D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_dualpol_truefed_l_fov_gain_check\UWB_CH9_D44_DUALPOL_TRUEFED_L_SINGLE_SOURCE_COVERAGE_coverage_grid.csv`
- 指标 JSON：`D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_dualpol_truefed_l_fov_gain_check\UWB_CH9_D44_DUALPOL_TRUEFED_L_SINGLE_SOURCE_COVERAGE_metrics.json`
