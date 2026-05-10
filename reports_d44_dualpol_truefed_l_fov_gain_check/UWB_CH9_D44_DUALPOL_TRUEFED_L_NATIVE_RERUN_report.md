# D44 candidate 37 原生导出复跑报告

## 复跑范围

- 候选：`fold0p6_neck1p6_stub2p6`，true-fed L 低仰角端口。
- 工作态：A_ON 与 B_ON 均重新建模并完成 HFSS 8 GHz 单点求解。
- 导出口径：AEDT 原生命令行 `CreateReport/ExportToFile`，绕开 PyAEDT `get_solution_data` 挂起点。
- 限制：逐源 `EditSources` 在 AEDT 2023.1 非图形脚本和 PyAEDT 中均挂起/中断；本报告复核全端口 S11 与默认激励 far-field，不把逐源覆盖口径标为已完成。

## 核心指标

- 最差工作端口 S11：`-15.125 dB`，来自 `A_ON_absorptive_50ohm_c0p08pf` / `dB(S(P3A,P3A))`。
- 最差 L 端口 S11：`-12.976 dB`，来自 `A_ON_absorptive_50ohm_c0p08pf` / `dB(S(P2L,P2L))`。
- 默认激励 FOV 最差 RealizedGainTotal：`-21.105 dBi`，来自 `A_ON_absorptive_50ohm_c0p08pf`，Theta `80 deg`，Phi `90 deg`。

## 达标判断

- S11：`达标`，目标为所有工作端口与 L 端口 `<= -10 dB`。
- 默认激励增益：`未达标`，目标为 FOV 内 `GainTotal/RealizedGainTotal >= -5 dBi`。
- 逐源覆盖增益：`未完成复核`，原因是 AEDT 2023.1 源切换和 PyAEDT 后处理接口挂起；已保留可复现脚本与日志。

## 输出文件

- 汇总 CSV：`D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_dualpol_truefed_l_fov_gain_check\UWB_CH9_D44_DUALPOL_TRUEFED_L_NATIVE_RERUN_summary.csv`
- 指标 JSON：`D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_dualpol_truefed_l_fov_gain_check\UWB_CH9_D44_DUALPOL_TRUEFED_L_NATIVE_RERUN_metrics.json`
- 本报告：`D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_dualpol_truefed_l_fov_gain_check\UWB_CH9_D44_DUALPOL_TRUEFED_L_NATIVE_RERUN_report.md`
