# UWB CH9 D44 双极化 RF Switch 工作态 PDOA 极化误差评估报告

## 评估目标

- 基于当前 S11 最优孔缝耦合候选，评估 RF switch 分时单通道工作态下，线极化入射 `0 / 45 / 90 / 135 deg` 对 PDOA 测角稳定性的影响。
- 选通极化保留为 HFSS lumped port，未选极化替换为 RF switch off 状态并联 RLC 等效负载。
- 主判据沿用前序 PDOA 极化标定目标：10 deg theta 网格留出验证后，PDOA 残差平均 group RMS `<= 10.0 deg`。
- 报告同时列出 LUT 前的原始极化敏感度；反射式高阻 off-state 因 S11 已严重不达标，仅作为失效风险对照。

## 核心结论

- 吸收式 off 端 `50 ohm // 0.08 pF` 的 A_ON/B_ON 工程有效工况，平均留出 RMS 为 `6.19 deg`，目标判定：`通过`。
- 单通道 RF switch 架构在 PDOA 上必须按“选通极化 + 入射极化角 + 频点 + 方位切面 + 基线”做查表标定；未做极化 LUT 时，原始 PDOA 偏差会随入射极化显著变化。
- 高阻反射式 off 端已经导致 S11 约 -0.34 dB，测角结果即使可提取，也不应作为可用工程状态。

## 工况汇总

| 工况 | 选通极化 | Off 等效 | 最差 S11 | S11达标 | 原始平均RMS | 10deg LUT留出平均RMS | 留出95%绝对残差 | 工程判定 |
| --- | --- | --- | ---: | --- | ---: | ---: | ---: | --- |
| `A_ON_absorptive_50ohm_c0p08pf` | A | 50 ohm // 0.08 pF | -13.36 dB | 是 | 74.62 deg | 6.72 deg | 11.05 deg | 可用 |
| `B_ON_absorptive_50ohm_c0p08pf` | B | 50 ohm // 0.08 pF | -11.01 dB | 是 | 73.28 deg | 5.66 deg | 10.08 deg | 可用 |
| `A_ON_reflective_5kohm_c0p08pf` | A | 5000 ohm // 0.08 pF | -0.34 dB | 否 | 89.81 deg | 8.29 deg | 14.79 deg | 不可用/需谨慎 |
| `B_ON_reflective_5kohm_c0p08pf` | B | 5000 ohm // 0.08 pF | -0.34 dB | 否 | 68.50 deg | 4.79 deg | 7.04 deg | 不可用/需谨慎 |

## 分极化结果

| 工况 | 入射线极化 | 曲线数 | 有效点比例 | LUT前RMS | LUT留出RMS | LUT留出95% | 最大留出残差 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `A_ON_absorptive_50ohm_c0p08pf` | 0 deg | 72 | 99.9% | 0.00 deg | 0.00 deg | 0.00 deg | 0.00 deg |
| `A_ON_absorptive_50ohm_c0p08pf` | 45 deg | 72 | 99.4% | 73.89 deg | 8.32 deg | 12.20 deg | 103.15 deg |
| `A_ON_absorptive_50ohm_c0p08pf` | 90 deg | 72 | 99.6% | 82.69 deg | 8.62 deg | 12.15 deg | 112.73 deg |
| `A_ON_absorptive_50ohm_c0p08pf` | 135 deg | 72 | 99.8% | 67.27 deg | 6.80 deg | 9.35 deg | 95.78 deg |
| `A_ON_reflective_5kohm_c0p08pf` | 0 deg | 72 | 99.2% | 0.00 deg | 0.00 deg | 0.00 deg | 0.00 deg |
| `A_ON_reflective_5kohm_c0p08pf` | 45 deg | 72 | 98.9% | 95.04 deg | 10.20 deg | 16.84 deg | 120.07 deg |
| `A_ON_reflective_5kohm_c0p08pf` | 90 deg | 72 | 99.0% | 100.50 deg | 8.87 deg | 10.89 deg | 119.67 deg |
| `A_ON_reflective_5kohm_c0p08pf` | 135 deg | 72 | 98.9% | 73.90 deg | 10.20 deg | 16.14 deg | 119.14 deg |
| `B_ON_absorptive_50ohm_c0p08pf` | 0 deg | 72 | 99.9% | 0.00 deg | 0.00 deg | 0.00 deg | 0.00 deg |
| `B_ON_absorptive_50ohm_c0p08pf` | 45 deg | 72 | 99.5% | 62.52 deg | 6.13 deg | 10.26 deg | 68.70 deg |
| `B_ON_absorptive_50ohm_c0p08pf` | 90 deg | 72 | 99.7% | 84.67 deg | 7.84 deg | 13.48 deg | 91.56 deg |
| `B_ON_absorptive_50ohm_c0p08pf` | 135 deg | 72 | 99.9% | 72.66 deg | 6.10 deg | 8.56 deg | 72.15 deg |
| `B_ON_reflective_5kohm_c0p08pf` | 0 deg | 72 | 99.8% | 0.00 deg | 0.00 deg | 0.00 deg | 0.00 deg |
| `B_ON_reflective_5kohm_c0p08pf` | 45 deg | 72 | 98.8% | 57.43 deg | 7.56 deg | 5.40 deg | 139.22 deg |
| `B_ON_reflective_5kohm_c0p08pf` | 90 deg | 72 | 99.4% | 96.85 deg | 6.76 deg | 9.44 deg | 95.60 deg |
| `B_ON_reflective_5kohm_c0p08pf` | 135 deg | 72 | 99.7% | 51.22 deg | 5.35 deg | 6.40 deg | 61.16 deg |

## 方法说明

- 基线候选：`p9p75_l5p0_w0p58_fw0p74_h0p30_fl11p8_abc_g0p12_l1p8_ph2p10_z0p06`。
- 每个工况重新建立 HFSS 远场工作态工程，使用 8 cores / 8 tasks，并在 `Upper_Hemisphere_5deg` 上提取嵌入远场。
- 对每个选通端口逐一激励，读取 `rETheta/rEPhi`，用 `Etheta*cos(psi)+Ephi*sin(psi)` 投影到 0/45/90/135 deg 线极化。
- PDOA 定义为同一选通极化通道下两个阵元复响应的相位差；0 deg 极化作为参考，统计其他极化相对 0 deg 的 PDOA 偏差。
- 10 deg LUT 留出验证：用 theta=0/10/20/.../90 deg 点训练极化残差 LUT，用 theta=5/15/.../85 deg 点验证插值后的残差 RMS。

## 输出文件

- 曲线 CSV: `D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_dualpol_rf_switch_pdoa_workstate\UWB_CH9_D44_DUALPOL_RF_SWITCH_PDOA_curves.csv`
- 曲线汇总 CSV: `D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_dualpol_rf_switch_pdoa_workstate\UWB_CH9_D44_DUALPOL_RF_SWITCH_PDOA_summary.csv`
- 分极化汇总 CSV: `D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_dualpol_rf_switch_pdoa_workstate\UWB_CH9_D44_DUALPOL_RF_SWITCH_PDOA_polarization_summary.csv`
- LUT 留出验证 CSV: `D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_dualpol_rf_switch_pdoa_workstate\UWB_CH9_D44_DUALPOL_RF_SWITCH_PDOA_lut_holdout_validation.csv`
- 指标 JSON: `D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_dualpol_rf_switch_pdoa_workstate\UWB_CH9_D44_DUALPOL_RF_SWITCH_PDOA_metrics.json`
- `A_ON_absorptive_50ohm_c0p08pf` AEDT 工作态快照: `D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_dualpol_rf_switch_pdoa_workstate\UWB_CH9_D44_DUALPOL_RF_SWITCH_PDOA_A_ON_absorptive_50ohm_c0p08pf.aedt`
- `B_ON_absorptive_50ohm_c0p08pf` AEDT 工作态快照: `D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_dualpol_rf_switch_pdoa_workstate\UWB_CH9_D44_DUALPOL_RF_SWITCH_PDOA_B_ON_absorptive_50ohm_c0p08pf.aedt`
- `A_ON_reflective_5kohm_c0p08pf` AEDT 工作态快照: `D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_dualpol_rf_switch_pdoa_workstate\UWB_CH9_D44_DUALPOL_RF_SWITCH_PDOA_A_ON_reflective_5kohm_c0p08pf.aedt`
- `B_ON_reflective_5kohm_c0p08pf` AEDT 工作态快照: `D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_dualpol_rf_switch_pdoa_workstate\UWB_CH9_D44_DUALPOL_RF_SWITCH_PDOA_B_ON_reflective_5kohm_c0p08pf.aedt`
