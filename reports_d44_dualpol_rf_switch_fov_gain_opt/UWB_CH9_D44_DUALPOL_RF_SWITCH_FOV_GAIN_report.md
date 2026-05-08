# D44 RF Switch 工作态 FOV 增益优化报告

## 目标与坐标口径

- HFSS 球坐标口径：`Theta=45..90 deg`，`Phi=0..360 deg`；对应从水平面到上仰 45 deg 的完整 360 deg 方位覆盖。
- 目标：FOV 内 `GainTotal` 与 `RealizedGainTotal` 均 `>= -5.0 dBi`。
- 工作态：只评估工程有效的吸收式 off 端 `50 ohm // 0.08 pF`，分别为 A_ON 与 B_ON。
- 严格口径：每个选通端口单独激励，其余选通端口关断，逐端口/逐频点/逐方向都必须满足。
- 覆盖口径：同一工作态、同一频点和方向上，在四个选通端口里取最高增益，反映阵列端口选择后的覆盖上限。

## 当前最佳

- 候选：`p9p75_l5p6_w0p70_fw0p80_stub1p90_w1p00_off1p55_dstub0p70_step1p0_iso11p5_w0p55_i3p6`
- 严格口径最小 GainTotal：`-28.85 dBi`。
- 严格口径最小 RealizedGainTotal：`-28.89 dBi`。
- 覆盖口径最小 GainTotal：`-20.35 dBi`。
- 覆盖口径最小 RealizedGainTotal：`-20.40 dBi`。
- 工作态最差 S11：`-9.31 dB`。
- 结论：严格口径 `未达标`，覆盖口径 `未达标`。

## 候选排名

| 排名 | 候选 | 严格 Realized 最小值 | 严格 Gain 最小值 | 覆盖 Realized 最小值 | 覆盖 Gain 最小值 | 最差 S11 |
| ---: | --- | ---: | ---: | ---: | ---: | ---: |
| 1 | `p9p75_l5p6_w0p70_fw0p80_stub1p90_w1p00_off1p55_dstub0p70_step1p0_iso11p5_w0p55_i3p6` | -28.89 dBi | -28.85 dBi | -20.40 dBi | -20.35 dBi | -9.31 dB |
| 2 | `p9p75_l5p0_w0p58_fw0p74_h0p30_fl11p8_abc_g0p12_l1p8_ph2p10_z0p06` | -33.19 dBi | -33.10 dBi | -20.46 dBi | -20.30 dBi | -13.16 dB |
| 3 | `p9p75_l5p6_w0p70_fw0p80_stub1p90_w1p00_off1p55_dstub0p70_step1p0_iso10p5_w0p50_i2p8` | -34.68 dBi | -34.55 dBi | -22.12 dBi | -22.11 dBi | -9.58 dB |
| 4 | `p9p75_l5p0_w0p58_fw0p74_h0p30_fl11p8_ares1p7x1p3_rbridge_gap1p7_qstub4p4_dstub1p9` | -41.73 dBi | -41.41 dBi | -23.51 dBi | -23.01 dBi | -7.26 dB |

## 最差点

- 严格口径最差 Realized：`B_ON_absorptive_50ohm_c0p08pf` / `P4B` / 8.2330 GHz / Theta 90 deg / Phi 45 deg。
- 覆盖口径最差 Realized：`A_ON_absorptive_50ohm_c0p08pf` / best source `P2A` / 8.2330 GHz / Theta 85 deg / Phi 40 deg。

## 工程判断

- 本轮尚未达到 -5 dBi FOV 目标。最差点仍落在 Theta=90 deg 附近，说明当前低剖面贴片/孔缝结构在水平面方向存在结构性辐射低谷。
- 继续只调 S11 匹配网络收益有限；下一轮应加入面向水平面辐射的结构，例如边缘寄生/折叠单极子、垂直电流支路、或独立的低仰角覆盖单元。

## 输出文件

- 候选汇总 CSV：`D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_dualpol_rf_switch_fov_gain_opt\UWB_CH9_D44_DUALPOL_RF_SWITCH_FOV_GAIN_summary.csv`
- 逐端口明细 CSV：`D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_dualpol_rf_switch_fov_gain_opt\UWB_CH9_D44_DUALPOL_RF_SWITCH_FOV_GAIN_source_summary.csv`
- 覆盖口径明细 CSV：`D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_dualpol_rf_switch_fov_gain_opt\UWB_CH9_D44_DUALPOL_RF_SWITCH_FOV_GAIN_coverage_summary.csv`
- 指标 JSON：`D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_dualpol_rf_switch_fov_gain_opt\UWB_CH9_D44_DUALPOL_RF_SWITCH_FOV_GAIN_metrics.json`
- 最佳 `A_ON_absorptive_50ohm_c0p08pf` AEDT 快照：`D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_dualpol_rf_switch_fov_gain_opt\UWB_CH9_D44_DUALPOL_RF_SWITCH_FOV_GAIN_04_p9p75_l5p6_w0p70_fw0p80_stub1p90_w1p00_off1p55_dstub0p70_step1p0_iso11p5_w0p55_A_ON_absorptive_50ohm_c0p08pf.aedt`
- 最佳 `B_ON_absorptive_50ohm_c0p08pf` AEDT 快照：`D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_dualpol_rf_switch_fov_gain_opt\UWB_CH9_D44_DUALPOL_RF_SWITCH_FOV_GAIN_04_p9p75_l5p6_w0p70_fw0p80_stub1p90_w1p00_off1p55_dstub0p70_step1p0_iso11p5_w0p55_B_ON_absorptive_50ohm_c0p08pf.aedt`
