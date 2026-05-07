# D44 RF Switch 工作态 Theta=0 增益核查报告

## 判据

- 目标：Theta=0 deg（+Z 轴/法向方向）GainTotal 与 RealizedGainTotal 均 `>= -5.0 dBi`。
- 核查工况：仅核查工程有效的吸收式 off 端 `50 ohm // 0.08 pF`，包括 A_ON 与 B_ON。
- 每个选通端口单独激励，其余选通端口关断，用所有 Phi 重复样本中的最小值作为 Theta=0 的保守值。

## 结论

- Theta=0 最小 GainTotal：`-15.28 dBi`。
- Theta=0 最小 RealizedGainTotal：`-15.47 dBi`。
- 上半球峰值 GainTotal 的跨端口/频点最小值：`-12.76 dBi`。
- 上半球峰值 RealizedGainTotal 的跨端口/频点最小值：`-12.95 dBi`。
- 结论：`不满足`。

## 分工况最差值

| 工况 | Theta=0 GainTotal 最小值 | Theta=0 RealizedGainTotal 最小值 | 上半球峰值 GainTotal 最小值 | 最差端口/频点 | 是否满足 |
| --- | ---: | ---: | ---: | --- | --- |
| `A_ON_absorptive_50ohm_c0p08pf` | -15.28 dBi | -15.47 dBi | -12.76 dBi | `P3A` / 8.2330 GHz | 否 |
| `B_ON_absorptive_50ohm_c0p08pf` | -13.92 dBi | -14.13 dBi | -11.71 dBi | `P4B` / 8.2330 GHz | 否 |

## 文件

- 明细 CSV: `D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_dualpol_rf_switch_gain_check\UWB_CH9_D44_DUALPOL_RF_SWITCH_GAIN_theta0_check.csv`
- 指标 JSON: `D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_dualpol_rf_switch_gain_check\UWB_CH9_D44_DUALPOL_RF_SWITCH_GAIN_theta0_check_metrics.json`
- `A_ON_absorptive_50ohm_c0p08pf` AEDT 快照: `D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_dualpol_rf_switch_gain_check\UWB_CH9_D44_DUALPOL_RF_SWITCH_GAIN_A_ON_absorptive_50ohm_c0p08pf.aedt`
- `B_ON_absorptive_50ohm_c0p08pf` AEDT 快照: `D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_dualpol_rf_switch_gain_check\UWB_CH9_D44_DUALPOL_RF_SWITCH_GAIN_B_ON_absorptive_50ohm_c0p08pf.aedt`
