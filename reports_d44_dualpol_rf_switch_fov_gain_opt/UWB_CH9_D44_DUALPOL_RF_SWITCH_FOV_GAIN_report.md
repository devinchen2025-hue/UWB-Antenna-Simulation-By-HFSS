# D44 RF Switch 工作态 FOV 增益优化报告

## 目标与坐标口径

- HFSS 球坐标口径：`Theta=45..90 deg`，`Phi=0..360 deg`；对应从水平面到上仰 45 deg 的完整 360 deg 方位覆盖。
- 增益目标：FOV 内 `GainTotal` 与 `RealizedGainTotal` 均 `>= -5.0 dBi`。
- 工作态：只评估工程有效的吸收式 off 端 `50 ohm // 0.08 pF`，分别为 A_ON 与 B_ON。
- 匹配约束：选通工作态最差 S11 需不高于 `-10.0 dB`。
- 严格口径：每个选通端口单独激励，其他选通端口关闭，逐端口、逐频点、逐方向均需满足。
- 覆盖口径：同一工作态、同一频点和方向上，在四个选通端口里取最高增益，反映阵列端口选择后的覆盖上限。
- 本轮报告包含 `42` 条候选记录；本次运行入口为 `52`，计划评估 `2` 条，总候选池 `53` 条。

## 当前最佳

- 候选：`p9p75_l5p6_w0p70_fw0p80_stub1p90_w1p00_off1p55_dstub0p70_step1p0_iso11p5_w0p55_i3p6_slit4p0_off0p45_foldededge_r1p8_t4p0_h5p2_w0p30_foldededge_r1p8_t4p0_h5p0_w0p24`
- 严格口径最小 GainTotal：`-24.14 dBi`。
- 严格口径最小 RealizedGainTotal：`-24.16 dBi`。
- 覆盖口径最小 GainTotal：`-16.07 dBi`。
- 覆盖口径最小 RealizedGainTotal：`-16.08 dBi`。
- 工作态最差 S11：`-12.13 dB`。
- 结论：严格口径 `未达标`，覆盖口径 `未达标`。

## 候选排名

| 排名 | 候选 | 严格 Realized 最小值 | 严格 Gain 最小值 | 覆盖 Realized 最小值 | 覆盖 Gain 最小值 | 最差 S11 |
| ---: | --- | ---: | ---: | ---: | ---: | ---: |
| 1 | `p9p75_l5p6_w0p70_fw0p80_stub1p90_w1p00_off1p55_dstub0p70_step1p0_iso11p5_w0p55_i3p6_slit4p0_off0p45_foldededge_r1p8_t4p0_h5p2_w0p30_foldededge_r1p8_t4p0_h5p0_w0p24` | -24.16 dBi | -24.14 dBi | -16.08 dBi | -16.07 dBi | -12.13 dB |
| 2 | `p9p75_l5p6_w0p70_fw0p80_stub1p90_w1p00_off1p55_dstub0p70_step1p0_iso11p5_w0p55_i3p6_slit4p0_off0p45_foldededge_r1p8_t4p0_h5p2_w0p30_foldededge_r1p8_t4p0_h5p0_w0p24_foldededge_t3p8_h4p8_w0p20` | -24.26 dBi | -24.24 dBi | -15.98 dBi | -15.96 dBi | -12.61 dB |
| 3 | `p9p75_l5p6_w0p70_fw0p80_stub1p90_w1p00_off1p55_dstub0p70_step1p0_iso11p5_w0p55_i3p6_slit4p0_off0p45_foldededge_r1p8_t4p0_h5p2_w0p30_foldededge_r1p8_t4p0_h5p0_w0p24_foldededge_t3p6_h5p0_w0p24` | -24.29 dBi | -24.10 dBi | -16.28 dBi | -16.26 dBi | -10.60 dB |
| 4 | `p9p75_l5p6_w0p70_fw0p80_stub1p90_w1p00_off1p55_dstub0p70_step1p0_iso11p5_w0p55_i3p6_slit4p0_off0p45_foldededge_r1p8_t4p0_h5p2_w0p30_foldededge_r1p6_t3p8_h5p0_w0p30` | -24.77 dBi | -24.72 dBi | -16.42 dBi | -16.42 dBi | -11.70 dB |
| 5 | `p9p75_l5p6_w0p70_fw0p80_stub1p90_w1p00_off1p55_dstub0p70_step1p0_iso11p5_w0p55_i3p6_slit4p0_off0p45_foldededge_r1p8_t4p0_h5p2_w0p30_foldededge_r2p0_t4p2_h5p2_w0p25` | -25.61 dBi | -25.57 dBi | -16.30 dBi | -16.29 dBi | -12.48 dB |
| 6 | `p9p75_l5p6_w0p70_fw0p80_stub1p90_w1p00_off1p55_dstub0p70_step1p0_iso11p5_w0p55_i3p6_slit4p0_off0p45` | -26.37 dBi | -26.26 dBi | -19.70 dBi | -19.69 dBi | -11.54 dB |
| 7 | `p9p75_l5p6_w0p70_fw0p80_stub1p90_w1p00_off1p55_dstub0p70_step1p0_iso11p5_w0p55_i3p6_slit4p0_off0p45_slit4p0_w0p16_off0p45` | -28.12 dBi | -28.11 dBi | -19.73 dBi | -19.69 dBi | -13.07 dB |
| 8 | `p9p75_l5p6_w0p70_fw0p80_stub1p90_w1p00_off1p55_dstub0p70_step1p0_iso11p5_w0p55_i3p6_slit4p0_off0p45_highfolded_r1p8_t4p0_h7p2_lim10` | -28.12 dBi | -28.09 dBi | -17.11 dBi | -17.11 dBi | -12.53 dB |
| 9 | `p9p75_l5p6_w0p70_fw0p80_stub1p90_w1p00_off1p55_dstub0p70_step1p0_iso11p5_w0p55_i3p6_slit4p0_off0p45_slit5p0_offu0p00_v0p80` | -28.18 dBi | -28.18 dBi | -20.46 dBi | -20.37 dBi | -11.78 dB |
| 10 | `p9p75_l5p6_w0p70_fw0p80_stub1p90_w1p00_off1p55_dstub0p70_step1p0_iso11p5_w0p55_i3p6_slit4p0_off0p45_slit3p8_off0p45` | -28.60 dBi | -28.43 dBi | -19.83 dBi | -19.80 dBi | -12.81 dB |
| 11 | `p9p75_l5p6_w0p70_fw0p80_stub1p90_w1p00_off1p55_dstub0p70_step1p0_iso11p5_w0p55_i3p6_stack_p9p55_gap0p80` | -29.33 dBi | -29.13 dBi | -20.31 dBi | -20.22 dBi | -11.80 dB |
| 12 | `p9p75_l5p6_w0p70_fw0p80_stub1p90_w1p00_off1p55_dstub0p70_step1p0_iso11p5_w0p55_i3p6_slit4p0_off0p45_slit4p0_ang30_off0p45` | -29.45 dBi | -29.38 dBi | -20.66 dBi | -20.66 dBi | -11.00 dB |
| 13 | `p9p75_l5p6_w0p70_fw0p80_stub1p90_w1p00_off1p55_dstub0p70_step1p0_iso11p5_w0p55_i3p6_slit4p0_off0p45_edgewall3p0_w0p45` | -29.99 dBi | -29.78 dBi | -20.77 dBi | -20.77 dBi | -11.80 dB |
| 14 | `p9p75_l5p6_w0p70_fw0p80_stub1p90_w1p00_off1p55_dstub0p70_step1p0_iso11p5_w0p55_i3p6_slit4p0_off0p45_slit5p0_offu0p80_v0p00` | -30.21 dBi | -30.07 dBi | -20.35 dBi | -20.33 dBi | -12.31 dB |
| 15 | `p9p75_l5p6_w0p70_fw0p80_stub1p90_w1p00_off1p55_dstub0p70_step1p0_iso11p5_w0p55_i3p6_slit4p0_off0p45_slit3p6_off0p35` | -30.57 dBi | -30.30 dBi | -20.46 dBi | -20.34 dBi | -10.59 dB |
| 16 | `p9p75_l5p6_w0p70_fw0p80_stub1p90_w1p00_off1p55_dstub0p70_step1p0_iso11p5_w0p55_i3p6_slit4p0_off0p45_edgearm3p2_w0p30` | -30.60 dBi | -30.51 dBi | -20.73 dBi | -20.72 dBi | -11.02 dB |
| 17 | `p9p75_l5p6_w0p70_fw0p80_stub1p90_w1p00_off1p55_dstub0p70_step1p0_iso11p5_w0p55_i3p6_slit4p0_off0p45_boardifa4p5_h5p5_g0p20_w0p30` | -32.33 dBi | -32.05 dBi | -20.86 dBi | -20.86 dBi | -10.84 dB |
| 18 | `p9p75_l5p6_w0p70_fw0p80_stub1p90_w1p00_off1p55_dstub0p70_step1p0_iso11p5_w0p55_i3p6_slit4p0_off0p45_foldededge_r1p8_t4p0_h5p2_w0p30_foldededge_r1p8_t4p0_h5p0_w0p24_foldededge_t4p0_h5p4_w0p22` | -32.42 dBi | -32.33 dBi | -16.42 dBi | -16.40 dBi | -11.37 dB |
| 19 | `p9p75_l5p6_w0p70_fw0p80_stub1p90_w1p00_off1p55_dstub0p70_step1p0_iso11p5_w0p55_i3p6_slit4p0_off0p45_slit5p5_offu0p60_v0p00` | -32.43 dBi | -32.39 dBi | -19.95 dBi | -19.94 dBi | -10.04 dB |
| 20 | `p9p75_l5p6_w0p70_fw0p80_stub1p90_w1p00_off1p55_dstub0p70_step1p0_iso11p5_w0p55_i3p6_slit4p0_off0p45_slit5p5_offu0p00_v0p60` | -32.51 dBi | -32.50 dBi | -20.28 dBi | -20.26 dBi | -11.84 dB |
| 21 | `p9p75_l5p0_w0p58_fw0p74_h0p30_fl11p8_abc_g0p12_l1p8_ph2p10_z0p06` | -33.19 dBi | -33.10 dBi | -20.46 dBi | -20.30 dBi | -13.16 dB |
| 22 | `p9p75_l5p6_w0p70_fw0p80_stub1p90_w1p00_off1p55_dstub0p70_step1p0_iso11p5_w0p55_i3p6_slit4p0_off0p45_edgearm2p4_w0p30` | -33.35 dBi | -33.24 dBi | -20.29 dBi | -20.29 dBi | -11.42 dB |
| 23 | `p9p75_l5p6_w0p70_fw0p80_stub1p90_w1p00_off1p55_dstub0p70_step1p0_iso11p5_w0p55_i3p6_slit4p0_off0p45_neutralizer2p2_abc` | -33.69 dBi | -33.25 dBi | -19.55 dBi | -19.53 dBi | -10.16 dB |
| 24 | `p9p75_l5p6_w0p70_fw0p80_stub1p90_w1p00_off1p55_dstub0p70_step1p0_iso11p5_w0p55_i3p6_stack_p9p75_gap1p20` | -33.94 dBi | -33.93 dBi | -20.75 dBi | -20.71 dBi | -12.56 dB |
| 25 | `p9p75_l5p6_w0p70_fw0p80_stub1p90_w1p00_off1p55_dstub0p70_step1p0_iso11p5_w0p55_i3p6_stack_p9p95_gap1p60` | -43.64 dBi | -43.59 dBi | -20.44 dBi | -20.40 dBi | -12.40 dB |
| 26 | `p9p75_l5p6_w0p70_fw0p80_stub1p90_w1p00_off1p55_dstub0p70_step1p0_iso11p5_w0p55_i3p6_slit4p0_off0p45_foldededge_r1p8_t4p0_h5p2_w0p30` | -23.26 dBi | -23.26 dBi | -16.11 dBi | -16.11 dBi | -9.89 dB |
| 27 | `p9p75_l5p6_w0p70_fw0p80_stub1p90_w1p00_off1p55_dstub0p70_step1p0_iso11p5_w0p55_i3p6_slit4p0_off0p45_foldededge_r1p8_t4p0_h5p2_w0p30_foldededge_r1p8_t4p0_h5p0_w0p24_foldededge_t4p0_h4p8_w0p22` | -23.49 dBi | -23.46 dBi | -16.29 dBi | -16.28 dBi | -9.82 dB |
| 28 | `p9p75_l5p6_w0p70_fw0p80_stub1p90_w1p00_off1p55_dstub0p70_step1p0_iso11p5_w0p55_i3p6_slit4p0_off0p45_foldededge_r1p8_t4p0_h5p2_w0p30_foldededge_r1p8_t4p0_h5p0_w0p24_foldededge_t3p8_h4p8_w0p22` | -24.41 dBi | -24.41 dBi | -16.07 dBi | -16.06 dBi | -9.89 dB |
| 29 | `p9p75_l5p6_w0p70_fw0p80_stub1p90_w1p00_off1p55_dstub0p70_step1p0_iso11p5_w0p55_i3p6_slit4p0_off0p45_foldededge_r1p8_t4p0_h5p2_w0p30_foldededge_r1p8_t4p0_h5p0_w0p24_foldededge_t4p4_h5p0_w0p24` | -25.85 dBi | -25.81 dBi | -16.22 dBi | -16.22 dBi | -9.37 dB |
| 30 | `p9p75_l5p6_w0p70_fw0p80_stub1p90_w1p00_off1p55_dstub0p70_step1p0_iso11p5_w0p55_i3p6_slit4p0_off0p45_foldededge_r1p8_t4p0_h5p2_w0p30_foldededge_r1p8_t4p0_h5p0_w0p24_foldedmatch_stub1p70_step0p80` | -26.49 dBi | -24.58 dBi | -15.83 dBi | -15.77 dBi | -4.44 dB |
| 31 | `p9p75_l5p6_w0p70_fw0p80_stub1p90_w1p00_off1p55_dstub0p70_step1p0_iso11p5_w0p55_i3p6_slit4p0_off0p45_foldededge_r1p8_t4p0_h5p2_w0p30_foldededge_r1p8_t4p0_h5p0_w0p24_foldedmatch_aper5p4_stub1p80` | -27.71 dBi | -26.24 dBi | -15.53 dBi | -15.52 dBi | -5.14 dB |
| 32 | `p9p75_l5p6_w0p70_fw0p80_stub1p90_w1p00_off1p55_dstub0p70_step1p0_iso11p5_w0p55_i3p6` | -28.89 dBi | -28.85 dBi | -20.40 dBi | -20.35 dBi | -9.31 dB |
| 33 | `p9p75_l5p6_w0p70_fw0p80_stub1p90_w1p00_off1p55_dstub0p70_step1p0_iso11p5_w0p55_i3p6_weakline2p4_gap0p12` | -28.89 dBi | -28.85 dBi | -20.40 dBi | -20.35 dBi | -9.31 dB |
| 34 | `p9p75_l5p6_w0p70_fw0p80_stub1p90_w1p00_off1p55_dstub0p70_step1p0_iso11p5_w0p55_i3p6_slit4p0_off0p45_neutralizer2p2` | -29.74 dBi | -29.60 dBi | -19.70 dBi | -19.69 dBi | -7.06 dB |
| 35 | `p9p75_l5p6_w0p70_fw0p80_stub1p90_w1p00_off1p55_dstub0p70_step1p0_iso11p5_w0p55_i3p6_slit4p0_off0p45_neutralizer2p6` | -30.51 dBi | -30.44 dBi | -20.00 dBi | -19.98 dBi | -9.52 dB |
| 36 | `p9p75_l5p6_w0p70_fw0p80_stub1p90_w1p00_off1p55_dstub0p70_step1p0_iso11p5_w0p55_i3p6_slit4p0_off0p45_horizonloop5p8_clean` | -34.16 dBi | -30.97 dBi | -26.96 dBi | -24.40 dBi | -2.56 dB |
| 37 | `p9p75_l5p6_w0p70_fw0p80_stub1p90_w1p00_off1p55_dstub0p70_step1p0_iso10p5_w0p50_i2p8` | -34.68 dBi | -34.55 dBi | -22.12 dBi | -22.11 dBi | -9.58 dB |
| 38 | `p9p75_l5p6_w0p70_fw0p80_stub1p90_w1p00_off1p55_dstub0p70_step1p0_iso11p5_w0p55_i3p6_slit4p0_off0p45_neutralizer2p2_z0p10` | -34.98 dBi | -34.96 dBi | -20.43 dBi | -20.35 dBi | -9.58 dB |
| 39 | `p9p75_l5p6_w0p70_fw0p80_stub1p90_w1p00_off1p55_dstub0p70_step1p0_iso11p5_w0p55_i3p6_slit4p0_off0p45_boardifa4p6_h3p8_g0p15_w0p35` | -36.78 dBi | -36.26 dBi | -21.50 dBi | -21.48 dBi | -9.41 dB |
| 40 | `p9p75_l5p6_w0p70_fw0p80_stub1p90_w1p00_off1p55_dstub0p70_step1p0_iso11p5_w0p55_i3p6_slit4p0_off0p45_horizonloop6p2_clean` | -38.76 dBi | -36.74 dBi | -26.98 dBi | -24.65 dBi | -3.07 dB |
| 41 | `p9p75_l5p0_w0p58_fw0p74_h0p30_fl11p8_ares1p7x1p3_rbridge_gap1p7_qstub4p4_dstub1p9` | -41.73 dBi | -41.41 dBi | -23.51 dBi | -23.01 dBi | -7.26 dB |
| 42 | `p9p75_l5p6_w0p70_fw0p80_stub1p90_w1p00_off1p55_dstub0p70_step1p0_iso11p5_w0p55_i3p6_slit4p0_off0p45_horizonloop6p6_clean` | -44.61 dBi | -42.26 dBi | -27.64 dBi | -25.44 dBi | -3.14 dB |

## 最差点

- 严格口径最差 Realized：`A_ON_absorptive_50ohm_c0p08pf` / `P4A` / 8.2330 GHz / Theta 90 deg / Phi 45 deg。
- 覆盖口径最差 Realized：`A_ON_absorptive_50ohm_c0p08pf` / best source `P2A` / 8.2330 GHz / Theta 90 deg / Phi 20 deg。

## 工程判断

- 本轮尚未达到 -5 dBi FOV 目标。最差点仍落在 Theta=90 deg 附近，说明当前低剖面贴片/孔缝结构在水平面方向存在结构性辐射低谷。
- 继续只调 S11 匹配网络收益有限；下一轮应优先评估面向水平面辐射的结构，例如边缘寄生辐射臂、折叠单极子、垂直电流支路，或独立低仰角覆盖单元。

## 输出文件

- 候选汇总 CSV：`D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_dualpol_rf_switch_fov_gain_opt\UWB_CH9_D44_DUALPOL_RF_SWITCH_FOV_GAIN_summary.csv`
- 逐端口明细 CSV：`D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_dualpol_rf_switch_fov_gain_opt\UWB_CH9_D44_DUALPOL_RF_SWITCH_FOV_GAIN_source_summary.csv`
- 覆盖口径明细 CSV：`D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_dualpol_rf_switch_fov_gain_opt\UWB_CH9_D44_DUALPOL_RF_SWITCH_FOV_GAIN_coverage_summary.csv`
- 指标 JSON：`D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_dualpol_rf_switch_fov_gain_opt\UWB_CH9_D44_DUALPOL_RF_SWITCH_FOV_GAIN_metrics.json`
- 最佳 `A_ON_absorptive_50ohm_c0p08pf` AEDT 快照：`D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_dualpol_rf_switch_fov_gain_opt\UWB_CH9_D44_DUALPOL_RF_SWITCH_FOV_GAIN_44_p9p75_l5p6_w0p70_fw0p80_stub1p90_w1p00_off1p55_dstub0p70_step1p0_iso11p5_w0p55_A_ON_absorptive_50ohm_c0p08pf.aedt`
- 最佳 `B_ON_absorptive_50ohm_c0p08pf` AEDT 快照：`D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_dualpol_rf_switch_fov_gain_opt\UWB_CH9_D44_DUALPOL_RF_SWITCH_FOV_GAIN_44_p9p75_l5p6_w0p70_fw0p80_stub1p90_w1p00_off1p55_dstub0p70_step1p0_iso11p5_w0p55_B_ON_absorptive_50ohm_c0p08pf.aedt`
