# D44 RF Switch 工作态 XY 平面增益核查报告

## 判据

- 目标：Z=0 即 XY 平面方向图，按 HFSS 球坐标 `Theta=90 deg, Phi=0..360 deg` 抽取，GainTotal 与 RealizedGainTotal 均 `>= -5.0 dBi`。
- 核查工况：工程有效的吸收式 off 端 `50 ohm // 0.08 pF`，包括 A_ON 与 B_ON。
- 每个选通端口单独激励，其余选通端口关断；对每个频点取 XY 平面整圈 Phi 的最小值作为保守判据。

## 结论

- XY 平面最小 GainTotal：`-33.10 dBi`。
- XY 平面最小 RealizedGainTotal：`-33.19 dBi`。
- XY 平面峰值 GainTotal 的跨端口/频点最小值：`-17.45 dBi`。
- XY 平面峰值 RealizedGainTotal 的跨端口/频点最小值：`-17.58 dBi`。
- 结论：`不满足`。

## 分工况最差值

| 工况 | XY平面 GainTotal 最小值 | XY平面 RealizedGainTotal 最小值 | 最差 Gain 点 | 最差 Realized 点 | 是否满足 |
| --- | ---: | ---: | --- | --- | --- |
| `A_ON_absorptive_50ohm_c0p08pf` | -26.44 dBi | -26.65 dBi | `P4A` / 8.2330 GHz / Phi 50 deg | `P4A` / 8.2330 GHz / Phi 50 deg | 否 |
| `B_ON_absorptive_50ohm_c0p08pf` | -33.10 dBi | -33.19 dBi | `P3B` / 8.2330 GHz / Phi 65 deg | `P3B` / 8.2330 GHz / Phi 65 deg | 否 |

## 文件

- 明细 CSV: `D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_dualpol_rf_switch_gain_xy_plane\UWB_CH9_D44_DUALPOL_RF_SWITCH_GAIN_XY_PLANE_check.csv`
- 指标 JSON: `D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_dualpol_rf_switch_gain_xy_plane\UWB_CH9_D44_DUALPOL_RF_SWITCH_GAIN_XY_PLANE_metrics.json`
- `A_ON_absorptive_50ohm_c0p08pf` AEDT 快照: `D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_dualpol_rf_switch_gain_xy_plane\UWB_CH9_D44_DUALPOL_RF_SWITCH_GAIN_XY_PLANE_A_ON_absorptive_50ohm_c0p08pf.aedt`
- `B_ON_absorptive_50ohm_c0p08pf` AEDT 快照: `D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_dualpol_rf_switch_gain_xy_plane\UWB_CH9_D44_DUALPOL_RF_SWITCH_GAIN_XY_PLANE_B_ON_absorptive_50ohm_c0p08pf.aedt`
