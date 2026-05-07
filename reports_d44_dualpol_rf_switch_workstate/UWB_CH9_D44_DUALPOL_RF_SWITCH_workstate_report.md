# UWB CH9 D44 双极化 RF Switch 工作态仿真报告

## 仿真目标

- 将同阵元 A/B 双极化改为 RF switch 分时单通道工作态：选通极化保留为 HFSS lumped port，未选中极化替换为 RF switch off 状态等效 RLC 负载。
- 基线结构来自当前最佳 S11 候选：`p9p75_l5p0_w0p58_fw0p74_h0p30_fl11p8_abc_g0p12_l1p8_ph2p10_z0p06`。
- 工作态 S11 目标：选通极化端口在 7.738-8.233 GHz 内最差 S11 <= -10.0 dB。
- 本轮不再把裸 A/B 同时端口隔离作为主指标，而是观察选通态 S11 与同极化跨阵元耦合。

## RF Switch 等效模型

- 吸收式 off 端：未选中端口用 `50 ohm // 0.08 pF` 并联负载近似，代表开关或外部终端能把未选端稳定吸收。
- 反射式 off 端：未选中端口用 `5 kohm // 0.08 pF` 并联负载近似，代表未选端接近高阻但存在 off 电容。
- 选通路径未单独加入插损；HFSS 端口仍按 50 ohm 归一化，开关 on 插损应在链路预算中另加。

## 结果汇总

| 排名 | 工作态 | Off 等效 | 最差 S11 | S11 达标 | 同极化跨阵元隔离 | 最差回波项 |
| ---: | --- | --- | ---: | --- | ---: | --- |
| 1 | `A_ON_absorptive_50ohm_c0p08pf` | 50 ohm // 0.08 pF | -13.36 dB | 是 | 35.13 dB | `dB(S(P3A:1,P3A:1))` |
| 2 | `B_ON_absorptive_50ohm_c0p08pf` | 50 ohm // 0.08 pF | -13.16 dB | 是 | 42.04 dB | `dB(S(P4B:1,P4B:1))` |
| 3 | `B_ON_reflective_5kohm_c0p08pf` | 5000 ohm // 0.08 pF | -0.34 dB | 否 | 37.87 dB | `dB(S(P4B:1,P4B:1))` |
| 4 | `A_ON_reflective_5kohm_c0p08pf` | 5000 ohm // 0.08 pF | -0.34 dB | 否 | 36.18 dB | `dB(S(P3A:1,P3A:1))` |

## 结论

- 工作态整体 S11 未全部达标。
- 如果实际 RF switch 是吸收式或外部给未选端提供稳定 50 ohm 终端，则应优先采用吸收式结果作为工程判断。
- 如果实际 RF switch 是反射式高阻 off 端，则未选极化会作为寄生加载参与辐射，应以反射式结果作为更保守判断。
- 后续若拿到具体开关型号，应把 datasheet 的 off capacitance、off resistance/termination、on resistance 和封装寄生更新到本脚本后重跑。

## 输出文件

- 汇总 CSV: `D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_dualpol_rf_switch_workstate\UWB_CH9_D44_DUALPOL_RF_SWITCH_workstate_summary.csv`
- 指标 JSON: `D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_dualpol_rf_switch_workstate\UWB_CH9_D44_DUALPOL_RF_SWITCH_workstate_metrics.json`
- `A_ON_absorptive_50ohm_c0p08pf` AEDT 快照: `D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_dualpol_rf_switch_workstate\UWB_CH9_D44_DUALPOL_RF_SWITCH_A_ON_absorptive_50ohm_c0p08pf.aedt`
- `B_ON_absorptive_50ohm_c0p08pf` AEDT 快照: `D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_dualpol_rf_switch_workstate\UWB_CH9_D44_DUALPOL_RF_SWITCH_B_ON_absorptive_50ohm_c0p08pf.aedt`
- `A_ON_reflective_5kohm_c0p08pf` AEDT 快照: `D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_dualpol_rf_switch_workstate\UWB_CH9_D44_DUALPOL_RF_SWITCH_A_ON_reflective_5kohm_c0p08pf.aedt`
- `B_ON_reflective_5kohm_c0p08pf` AEDT 快照: `D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_dualpol_rf_switch_workstate\UWB_CH9_D44_DUALPOL_RF_SWITCH_B_ON_reflective_5kohm_c0p08pf.aedt`
