# D44 真正板边低仰角单元验证报告

## 目标

- 结构方向: 真正板边馈电 IFA/PIFA 低仰角覆盖单元, P1L 为唯一激励源, A/B 馈点作为 50 ohm // 0.08 pF 终端负载背景。
- 加工转换: 对比实心厚板侧壁、低介电厚载体、侧壁平面 IFA, 以及保留原空气支撑电流路径的边镀立墙/立式载体方案。
- S11 目标: `S11 <= -10.0 dB`。
- 增益目标: Theta `45..90 deg`, 最佳连续 `270 deg` 方位窗口内 `GainTotal >= -5.0 dBi`。

## 当前结果

- 综合最佳: `#64 edgeplate_riser_pifa_s19p0_short_m0p6_c0p142_l2p00_r680`。
- S11: `-11.166 dB`, 达标。
- 最佳 270 deg 窗口 GainTotal 最小值: `-3.323 dBi`, 达标。
- 最差点: Theta `45 deg` / Phi `335 deg`。
- 双指标同时达标候选数: `5` / `52`。

## 板边侧壁金属化转换结论

- 实心 7.6 mm RO4350B 厚板侧壁 PIFA: `#56 sidewall_pifa_s19p0_short_m0p6_c0p142_l2p00_r680`, S11 `-2.661 dB`, Best270 GainTotal min `-15.519 dBi`, 未达标。
- 低介电厚载体/泡棉等效侧壁 PIFA: `#60 sidewall_pifa_foam_s19p0_short_m0p6_c0p142_l2p00_r680`, S11 `-7.940 dB`, Best270 GainTotal min `-11.275 dBi`, 未达标。
- 主动 IFA 完全旋到侧壁平面并保留折叠寄生臂: `#62 edgeplate_pifa_air_s19p0_short_m0p6_c0p142_l2p00_r680`, S11 `-3.148 dB`, Best270 GainTotal min `-8.513 dBi`, 未达标。
- 只保留主动侧壁平面 IFA, 去掉折叠寄生臂: `#63 edgeplate_pifa_air_nofold_s19p0_c0p142_l2p00_r680`, S11 `-1.855 dB`, Best270 GainTotal min `-10.100 dBi`, 未达标。
- 边镀立墙/立式载体实现原达标电流路径: `#64 edgeplate_riser_pifa_s19p0_short_m0p6_c0p142_l2p00_r680`, S11 `-11.166 dB`, Best270 GainTotal min `-3.323 dBi`, 达标。

- 工程判断: 不能把当前达标结构简单改成实心厚板顶层 PIFA 或完全侧壁平面 IFA; 这些版本低仰角增益明显不足。
- 可制造达标路径是 #64: 保留 #53 的空气支撑竖向/折叠电流路径, 将竖直段做成板边镀铜、castellated 立墙、过孔墙加侧边铜, 或低成本金属化立式载体。
- 这不是普通平面微带贴片; 量产图纸需要把 6.3 mm 主 IFA 高度、5.9 mm 短折叠寄生臂高度、0.142 pF 串联 C、2.0 nH // 680 ohm 并联阻尼匹配一起定义。

## 关键对比

- S11 最优: `#23 edgeifa_s19p0_foldpar_hiarm_neg_match_c0p173_l6p1`, S11 `-17.971 dB`, GainTotal min `-5.586 dBi`。
- 增益最优: `#35 edgeifa_s19p0_foldpar_match_short_offset_m0p6`, GainTotal min `-2.286 dBi`, S11 `-5.534 dB`。
- 纯无耗 L/C 匹配在当前 3D 近场模型中停在约 -8 dB S11; 最终达标方案使用高阻值 shunt R 与 L/C 组成离散阻尼匹配。

| # | 候选 | S11 worst dB | Best270 min Gain dBi | All-phi min Gain dBi | 结果 |
|---:|---|---:|---:|---:|---|
| 1 | `edgeifa_s17_h5p6_l4p2_f0p60_g0p25` | -2.175 | -7.142 | -13.759 | 未达标 |
| 2 | `edgeifa_s17_h5p8_l4p8_f0p75_g0p25` | -2.260 | -6.647 | -13.246 | 未达标 |
| 3 | `edgeifa_s17_h5p4_l5p4_f0p95_g0p20_patch7p4` | -1.526 | -7.480 | -9.748 | 未达标 |
| 4 | `edgeifa_s17_h5p8_l4p8_f1p35_g0p25` | -2.516 | -6.419 | -14.147 | 未达标 |
| 5 | `edgeifa_s17_h5p8_l4p8_f0p75_g0p25_stub1p2_c0p18` | -2.068 | -6.582 | -14.089 | 未达标 |
| 6 | `edgemono_s17_h5p8_g0p35_top2p2` | -7.737 | -9.306 | -12.870 | 未达标 |
| 7 | `edgemono_s17_h5p9_g0p25_top1p4_neck0p6` | -7.522 | -9.333 | -13.519 | 未达标 |
| 8 | `edgemono_s17_h5p8_g0p35_top2p2_stub1p0_l1p8` | -3.840 | -6.743 | -9.511 | 未达标 |
| 9 | `edgeifa_s18p5_p6p2_h6p3_l4p8_f1p35_g0p18` | -1.553 | -5.527 | -6.367 | 未达标 |
| 10 | `edgeifa_s18p5_p6p2_h6p3_l4p8_f2p10_g0p18` | -2.204 | -6.235 | -7.665 | 未达标 |
| 11 | `edgeifa_s19p5_p4p8_h6p3_l5p2_f1p80_g0p18` | -1.612 | -5.644 | -7.067 | 未达标 |
| 12 | `edgeifa_s19p5_p4p8_h6p3_l5p2_f2p60_g0p18` | -2.584 | -5.731 | -7.126 | 未达标 |
| 13 | `edgeifa_s20p0_p4p2_h6p3_l5p4_f2p00_g0p15` | -1.779 | -5.298 | -6.392 | 未达标 |
| 14 | `edgeifa_s20p0_p4p2_h6p3_l5p4_f2p80_g0p15` | -2.349 | -5.939 | -7.525 | 未达标 |
| 15 | `edgeifa_s19p0_p5p4_h6p3_l5p0_f1p80_foldpar` | -2.664 | -4.802 | -6.190 | 未达标 |
| 16 | `edgeifa_s19p5_p4p8_h6p3_l5p2_f1p80_hloop` | -2.100 | -5.716 | -6.616 | 未达标 |
| 17 | `edgeifa_s19p0_foldpar_match_c0p173_l6p1` | -12.308 | -5.439 | -8.355 | 未达标 |
| 18 | `edgeifa_s19p0_foldpar_match_c0p160_l5p6` | -9.909 | -5.510 | -8.060 | 未达标 |
| 19 | `edgeifa_s19p0_foldpar_match_c0p190_l6p8` | -11.987 | -5.549 | -8.397 | 未达标 |
| 20 | `edgeifa_s19p0_foldpar_hiarm_raw` | -2.084 | -5.236 | -6.186 | 未达标 |
| 21 | `edgeifa_s19p0_foldpar_hiarm_match_c0p173_l6p1` | -12.678 | -5.323 | -8.074 | 未达标 |
| 22 | `edgeifa_s19p0_foldpar_hiarm_match_c0p190_l6p8` | -13.406 | -5.530 | -8.070 | 未达标 |
| 23 | `edgeifa_s19p0_foldpar_hiarm_neg_match_c0p173_l6p1` | -17.971 | -5.586 | -8.320 | 未达标 |
| 24 | `edgeifa_s19p0_foldpar_mini_match_c0p173_l6p1` | -14.541 | -5.630 | -8.874 | 未达标 |
| 25 | `edgeifa_s19p0_foldpar_mini_match_c0p165_l5p8` | -15.185 | -5.746 | -9.103 | 未达标 |
| 26 | `edgeifa_s19p0_foldpar_mini_match_c0p185_l6p4` | -13.819 | -5.668 | -8.837 | 未达标 |
| 27 | `edgeifa_s19p0_foldpar_mini_match_stub0p45_c0p173_l6p1` | -5.800 | -5.405 | -8.590 | 未达标 |
| 28 | `edgeifa_s19p0_foldpar_tall_mini_match_c0p173_l6p1` | -11.206 | -5.527 | -8.546 | 未达标 |
| 29 | `edgeifa_s19p0_foldpar_stub0p45_c0p150_l8p0` | -2.462 | -5.386 | -7.375 | 未达标 |
| 30 | `edgeifa_s19p0_foldpar_stub0p45_c0p140_l9p5` | -2.826 | -5.344 | -7.431 | 未达标 |
| 31 | `edgeifa_s19p0_foldpar_stub0p45_c0p130_l11p0` | -1.241 | -5.303 | -6.825 | 未达标 |
| 32 | `edgeifa_s19p0_foldpar_stub0p30_c0p155_l8p0` | -5.573 | -5.472 | -7.432 | 未达标 |
| 33 | `edgeifa_s19p0_foldpar_stub0p25_c0p160_l7p0` | -7.466 | -5.680 | -7.726 | 未达标 |
| 34 | `edgeifa_s19p0_foldpar_stub0p60_c0p140_l10p0` | -0.005 | -5.613 | -6.056 | 未达标 |
| 35 | `edgeifa_s19p0_foldpar_match_short_offset_m0p6` | -5.534 | -2.286 | -10.908 | 未达标 |
| 41 | `edgeifa_s19p0_short_m0p6_match_c0p142_l3p65` | -7.436 | -2.558 | -10.817 | 未达标 |
| 45 | `edgeifa_s19p0_short_m0p6_match_c0p124_l3p00` | -8.251 | -2.743 | -11.215 | 未达标 |
| 46 | `edgeifa_s19p0_short_m0p6_match_c0p125_l2p98` | -7.463 | -2.629 | -11.288 | 未达标 |
| 47 | `edgeifa_s19p0_short_m0p6_match_c0p122_l3p05` | -7.273 | -2.708 | -11.357 | 未达标 |
| 48 | `edgeifa_s19p0_short_m0p6_match_c0p127_l2p95` | -7.611 | -2.827 | -10.920 | 未达标 |
| 49 | `edgeifa_s19p0_short_m0p6_match_c0p110_l2p70` | -8.144 | -2.935 | -10.748 | 未达标 |
| 50 | `edgeifa_s19p0_short_m0p6_damped_c0p156_l2p20_r820` | -10.098 | -3.064 | -12.480 | 达标 |
| 51 | `edgeifa_s19p0_short_m0p6_damped_c0p146_l2p30_r1000` | -9.370 | -3.068 | -12.037 | 未达标 |
| 52 | `edgeifa_s19p0_short_m0p6_damped_c0p134_l2p40_r1500` | -9.115 | -3.004 | -11.931 | 未达标 |
| 53 | `edgeifa_s19p0_short_m0p6_damped_c0p142_l2p00_r680` | -11.166 | -3.323 | -12.294 | 达标 |
| 54 | `edgeifa_s19p0_short_m0p6_damped_c0p130_l2p10_r820` | -10.838 | -3.304 | -12.060 | 达标 |
| 55 | `edgeifa_s19p0_short_m0p6_damped_c0p178_l1p80_r390` | -11.080 | -3.451 | -12.742 | 达标 |
| 56 | `sidewall_pifa_s19p0_short_m0p6_c0p142_l2p00_r680` | -2.661 | -15.519 | -16.048 | 未达标 |
| 60 | `sidewall_pifa_foam_s19p0_short_m0p6_c0p142_l2p00_r680` | -7.940 | -11.275 | -16.004 | 未达标 |
| 62 | `edgeplate_pifa_air_s19p0_short_m0p6_c0p142_l2p00_r680` | -3.148 | -8.513 | -8.565 | 未达标 |
| 63 | `edgeplate_pifa_air_nofold_s19p0_c0p142_l2p00_r680` | -1.855 | -10.100 | -13.172 | 未达标 |
| 64 | `edgeplate_riser_pifa_s19p0_short_m0p6_c0p142_l2p00_r680` | -11.166 | -3.323 | -12.294 | 达标 |

## 输出文件

- 汇总 CSV: `D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_board_edge_low_angle_single_element\UWB_CH9_D44_BOARD_EDGE_LOW_ANGLE_SINGLE_ELEMENT_summary.csv`
- 方位窗口 CSV: `D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_board_edge_low_angle_single_element\UWB_CH9_D44_BOARD_EDGE_LOW_ANGLE_SINGLE_ELEMENT_azimuth_window_summary.csv`
- 指标 JSON: `D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_board_edge_low_angle_single_element\UWB_CH9_D44_BOARD_EDGE_LOW_ANGLE_SINGLE_ELEMENT_metrics.json`
- 当前最佳 AEDT: `D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\UWB_CH9_Diamond_CP_Array_D44_BEDGE_edgeplate_riser_pifa_s19p0_s_0b2d3f9.aedt`
