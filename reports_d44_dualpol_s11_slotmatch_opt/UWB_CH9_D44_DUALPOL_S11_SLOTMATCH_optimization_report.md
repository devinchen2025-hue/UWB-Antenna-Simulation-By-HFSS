# D44 双极化独立过桥谐振馈电 S11 优化报告

## 目标与结论

- 目标：真正独立双端口馈电/过桥谐振耦合网络，8 端口带内最差 S11 `<= -10.0 dB`，并同步观察 A/B 隔离。
- 仿真方式：S 参数快速筛选，HFSS 非图形模式，`analysis_cores=8`，`analysis_tasks=8`。
- 本轮累计有效候选：`331` 个，其中独立过桥候选 `169` 个。
- 结论：`S11 未达标`。最终独立过桥候选 `p9p75_l5p0_w0p58_fw0p74_h0p30_fl11p8_untrl2p2_fsvia0p74_ares1p7x1p3_rbridge_gap1p7_qstub4p4_dstub1p9` 的最差回波为 `-10.87 dB`。
- 限制：同阵元 A/B 隔离仍低，为 `0.38 dB`；同馈跨阵元隔离为 `39.81 dB`。

## 最佳独立候选指标

| 指标 | 数值 |
| --- | ---: |
| 最差 S11 | -10.87 dB |
| X/A 极化最差回波 | -11.46 dB |
| Y/B 极化最差回波 | -10.87 dB |
| X/Y 回波不平衡 | 0.60 dB |
| 同阵元 A/B 隔离 | 0.38 dB |
| 同馈跨阵元隔离 | 39.81 dB |
| 最差回波表达式 | `dB(S(P4B:1,P4B:1))` |
| 最差耦合表达式 | `dB(S(P3B:1,P3A:1))` |

## 关键结构参数

| 参数 | 数值 |
| --- | ---: |
| `patch_side_mm` | `9.750` |
| `port_width_mm` | `0.500` |
| `dualpol_slotcoupled_enabled` | `1.000` |
| `feed_substrate_h_mm` | `0.300` |
| `slot_coupled_aperture_length_a_mm` | `5.000` |
| `slot_coupled_aperture_length_b_mm` | `5.000` |
| `slot_coupled_aperture_width_mm` | `0.580` |
| `slot_coupled_offset_a_mm` | `0.000` |
| `slot_coupled_offset_b_mm` | `0.000` |
| `slot_coupled_aperture_center_a_v_mm` | `0.000` |
| `slot_coupled_aperture_center_b_u_mm` | `0.000` |
| `slot_coupled_feedline_length_mm` | `11.800` |
| `slot_coupled_feedline_width_mm` | `0.740` |
| `slot_coupled_feedline_offset_a_v_mm` | `0.000` |
| `slot_coupled_feedline_offset_b_u_mm` | `0.000` |
| `slot_coupled_b_feed_layer_offset_mm` | `0.000` |
| `slot_coupled_bridge_enabled` | `1.000` |
| `slot_coupled_bridge_gap_mm` | `1.700` |
| `slot_coupled_bridge_offset_mm` | `0.020` |
| `slot_coupled_bridge_width_mm` | `0.740` |
| `slot_coupled_bridge_resonator_width_mm` | `2.100` |
| `slot_coupled_bridge_overhang_mm` | `0.700` |
| `slot_coupled_a_resonator_length_mm` | `1.700` |
| `slot_coupled_a_resonator_width_mm` | `1.300` |
| `slot_coupled_shield_via_enabled` | `1.000` |
| `slot_coupled_shield_via_count` | `1.000` |
| `slot_coupled_shield_via_radius_mm` | `0.050` |
| `slot_coupled_shield_via_offset_mm` | `0.740` |
| `slot_coupled_shield_via_pitch_mm` | `0.420` |
| `slot_coupled_shield_via_grounded` | `0.000` |
| `slot_coupled_shield_via_top_gap_mm` | `0.030` |
| `slot_coupled_a_neck_enabled` | `0.000` |
| `slot_coupled_a_neck_length_mm` | `2.200` |
| `slot_coupled_a_neck_width_mm` | `0.300` |
| `slot_coupled_underfeed_neutralizer_enabled` | `1.000` |
| `slot_coupled_underfeed_neutralizer_length_mm` | `2.200` |
| `slot_coupled_underfeed_neutralizer_width_mm` | `0.120` |
| `slot_coupled_underfeed_neutralizer_offset_mm` | `1.200` |
| `slot_coupled_underfeed_neutralizer_z_offset_mm` | `0.060` |
| `slot_coupled_patch_slit_enabled` | `0.000` |
| `slot_coupled_patch_slit_length_mm` | `3.000` |
| `slot_coupled_patch_slit_width_mm` | `0.100` |
| `slot_coupled_patch_slit_angle_deg` | `45.000` |
| `slot_coupled_patch_slit_offset_u_mm` | `0.000` |
| `slot_coupled_patch_slit_offset_v_mm` | `0.000` |
| `slot_coupled_stub_enabled` | `1.000` |
| `slot_coupled_stub_length_mm` | `4.400` |
| `slot_coupled_stub_width_mm` | `0.550` |
| `slot_coupled_stub_offset_mm` | `1.100` |
| `slot_coupled_stub_side_sign` | `1.000` |
| `slot_coupled_stub2_enabled` | `1.000` |
| `slot_coupled_stub2_length_mm` | `1.900` |
| `slot_coupled_stub2_width_mm` | `0.400` |
| `slot_coupled_stub2_offset_mm` | `3.000` |
| `slot_coupled_stub2_side_sign` | `-1.000` |
| `slot_coupled_step_enabled` | `1.000` |
| `slot_coupled_step_length_mm` | `1.100` |
| `slot_coupled_step_width_mm` | `1.120` |
| `weak_coupling_open_line_enabled` | `0.000` |
| `weak_coupling_open_line_length_mm` | `2.200` |
| `weak_coupling_open_line_width_mm` | `0.120` |
| `weak_coupling_open_line_offset_mm` | `1.650` |
| `weak_coupling_open_line_gap_mm` | `0.080` |
| `dualpol_parasitic_enabled` | `0.000` |
| `parasitic_side_mm` | `0.000` |
| `air_gap_mm` | `0.000` |
| `isolation_slot_enabled` | `1.000` |
| `isolation_slot_length_mm` | `10.000` |
| `isolation_slot_width_mm` | `0.420` |
| `isolation_slot_inner_mm` | `3.200` |

## 迭代观察

- 旧直连/非过桥候选参考最优为：`p9p75_l5p6_w0p70_fw0p80_stub1p90_w1p00_off1p55_dstub0p70_step1p0`，最差回波 `-17.15 dB`。该类候选 S11 更深，但不满足当前“真正独立双端口/过桥谐振网络”的架构约束。
- 独立过桥网络在 `feed_substrate_h=0.254 mm` 时停在约 `-9.67 dB`，主要卡在高频端。
- 第三轮把下层馈电介质厚度增加到 `0.300 mm` 后，最差 S11 推到 `-10.23 dB`，说明瓶颈主要是层间耦合相位/强度。
- A 孔缝长度、A 馈线偏置、端口宽度、A 中心谐振片放大/缩小均未进一步改善，多数会明显破坏匹配岛。

## 独立过桥候选排行

| 排名 | 候选 | 最差 S11 | X/A | Y/B | A/B 隔离 | 同馈跨阵元隔离 |
| ---: | --- | ---: | ---: | ---: | ---: | ---: |
| 1 | `p9p75_l5p0_w0p58_fw0p74_h0p30_fl11p8_untrl2p2_fsvia0p74_ares1p7x1p3_rbridge_gap1p7_qstub4p4_dstub1p9` | -10.87 dB | -11.46 dB | -10.87 dB | 0.38 dB | 39.81 dB |
| 2 | `p9p75_l5p0_w0p58_fw0p74_h0p30_fl11p8_fsvia0p74r0p05gap0p03_ares1p7x1p3_rbridge_gap1p7_qstub4p4_dstub1p9` | -11.52 dB | -12.12 dB | -11.52 dB | 0.36 dB | 41.19 dB |
| 3 | `p9p75_l5p0_w0p58_fw0p74_h0p30_fl11p8_untrl2p2_fsvia0p74_pslit3p2` | -11.71 dB | -11.71 dB | -12.17 dB | 0.35 dB | 41.81 dB |
| 4 | `p9p75_l5p0_w0p58_fw0p74_h0p30_fl11p8_ares1p7x1p3_rbridge_gap1p7_qstub4p4_dstub1p9` | -10.23 dB | -10.52 dB | -10.23 dB | 0.32 dB | 42.02 dB |
| 5 | `p9p75_l5p0_w0p58_fw0p74_h0p30_fl11p8_weak2p2_ares1p7x1p3_rbridge_gap1p7_qstub4p4_dstub1p9` | -10.23 dB | -10.52 dB | -10.23 dB | 0.32 dB | 42.02 dB |
| 6 | `p9p75_l5p0_w0p58_fw0p74_h0p30_fl11p8_untrl2p2_fsvia0p74_pslit2p4` | -9.96 dB | -10.57 dB | -9.96 dB | 0.37 dB | 41.46 dB |
| 7 | `p9p75_l5p0_w0p58_fw0p74_fl11p8_ares1p7x1p3_rbridge_gap1p7_qstub4p4_dstub1p9` | -9.67 dB | -9.67 dB | -9.90 dB | 0.27 dB | 47.34 dB |
| 8 | `p9p75_l5p0_w0p58_fw0p74_h0p30_fl11p8_untrl3p0w0p16o1p0z0p06_ares1p7x1p3_rbridge_gap1p7_qstub4p4_dstub1p9` | -9.46 dB | -9.88 dB | -9.46 dB | 0.28 dB | 45.87 dB |
| 9 | `p9p75_l5p0_w0p58_fw0p74_fl11p8_ares1p7x1p3_rbridge_gap1p7_qstub4p2_step1p1` | -9.25 dB | -9.51 dB | -9.25 dB | 0.29 dB | 44.98 dB |
| 10 | `p9p75_l5p0_w0p58_fw0p74_h0p30_fl11p8_aneck1p8w0p42_ares1p7x1p3_rbridge_gap1p7_qstub4p4_dstub1p9` | -9.22 dB | -9.53 dB | -9.22 dB | 0.36 dB | 42.07 dB |
| 11 | `p9p75_l5p0_w0p59_fw0p74_fl11p8_ares1p7x1p3_rbridge_gap1p7_qstub4p4_dstub1p9` | -9.11 dB | -9.36 dB | -9.11 dB | 0.26 dB | 47.73 dB |
| 12 | `p9p75_l5p0_w0p58_fw0p74_fl11p8_ares1p7x1p3_rbridge_gap1p7_qstub4p4_dstub1p9_dsw0p35` | -9.10 dB | -9.10 dB | -9.17 dB | 0.26 dB | 46.40 dB |
| 13 | `p9p75_l4p6_w0p50_fw0p70_fl11p6_ares1p5x1p1_rbridge_gap1p5_qstub4p4_step1p0` | -8.96 dB | -8.96 dB | -9.11 dB | 0.29 dB | 44.64 dB |
| 14 | `p9p75_l5p0_w0p60_fw0p78_h0p30_fl11p8_untrl3p0w0p16o1p0z0p06_ares1p7x1p3_rbridge_gap1p7_qstub4p5_dstub1p9` | -8.88 dB | -8.88 dB | -9.02 dB | 0.36 dB | 44.37 dB |
| 15 | `p9p75_l5p0_w0p58_fw0p74_fl11p8_ares1p7x1p3_rbridge_gap1p7_qstub4p3_dstub1p9` | -8.84 dB | -9.08 dB | -8.84 dB | 0.27 dB | 48.40 dB |
| 16 | `p9p75_l5p0_w0p58_fw0p74_h0p30_fl11p8_aneck2p4w0p34_ares1p7x1p3_rbridge_gap1p7_qstub4p4_dstub1p9` | -8.82 dB | -8.82 dB | -9.05 dB | 0.35 dB | 48.10 dB |
| 17 | `p9p75_l4p8_w0p54_fw0p72_fl11p8_ares1p6x1p2_rbridge_gap1p6_qstub4p4_step1p0` | -8.72 dB | -8.92 dB | -8.72 dB | 0.26 dB | 46.47 dB |
| 18 | `p9p75_l4p6_w0p50_fw0p70_fl11p8_ares1p5x1p1_rbridge_gap1p5_qstub4p4_step1p0` | -8.72 dB | -8.72 dB | -9.18 dB | 0.28 dB | 47.12 dB |
| 19 | `p9p75_l4p4_w0p48_fw0p68_fl11p8_ares1p4x1p0_rbridge_gap1p4_qstub4p4_step0p9` | -8.65 dB | -8.94 dB | -8.65 dB | 0.31 dB | 46.18 dB |
| 20 | `p9p75_l4p8_w0p54_fw0p72_fl11p8_ares1p6x1p2_rbridge_gap1p6_qstub3p8_step1p0` | -8.59 dB | -8.59 dB | -8.67 dB | 0.29 dB | 48.41 dB |

## 下一步建议

- 若优先保持 S11 达标：以 `feed_substrate_h=0.300 mm` 的独立过桥网络作为当前基线，做窄范围厚度公差和制造容差验证。
- 若继续提升 A/B 隔离：建议加入独立中和支路、窄缝去耦、或仅作用于同阵元正交端口的桥旁补偿结构；当前 A/B 隔离是主要剩余问题。
- 若要回到 PDOA/极化标定目标：需要在此 S11 达标结构上重新跑 0/45/90/135 deg 极化入射后的 PDOA 标定流程。

## 输出文件

- S 参数筛选 CSV: `D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_dualpol_s11_slotmatch_opt\UWB_CH9_D44_DUALPOL_S11_SLOTMATCH_sparam_screening.csv`
- 最佳 JSON: `D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_dualpol_s11_slotmatch_opt\UWB_CH9_D44_DUALPOL_S11_SLOTMATCH_best.json`
- 中文报告: `D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_dualpol_s11_slotmatch_opt\UWB_CH9_D44_DUALPOL_S11_SLOTMATCH_optimization_report.md`
- AEDT 工程: `D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\UWB_CH9_Diamond_CP_Array_D44_DUALPOL_XY.aedt`
- 参数 JSON: `D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\UWB_CH9_Diamond_CP_Array_D44_DUALPOL_XY_params.json`

## 本轮补充结论

- 本轮目标：最差 S11 <= -10.0 dB，同时同阵元 A/B 端口隔离 >= 15.0 dB，并尽量保持同馈跨阵元隔离。
- 当前最佳可运行候选为 row 325：`p9p75_l5p0_w0p58_fw0p74_h0p30_fl11p8_untrl2p2_fsvia0p74_ares1p7x1p3_rbridge_gap1p7_qstub4p4_dstub1p9`。
- 核心结果：最差 S11 = -10.866 dB，X/A 最差回波 = -11.462 dB，Y/B 最差回波 = -10.866 dB，同阵元 A/B 隔离 = 0.379 dB，同馈跨阵元隔离 = 39.808 dB。
- 达标状态：S11 已达标；同阵元 A/B 隔离未达标，因此本轮整体未完全达标。
- 正向改进：相对 row 289 的 A/B 隔离 0.321 dB，row 325 提升到 0.379 dB；相对 row 316 的 A/B 隔离 0.364 dB，row 325 也有小幅改善，同时保持 S11 <= -10 dB。
- 失败路径总结：接地屏蔽过孔可把 A/B 隔离推到 10-17 dB，但会把 S11 拉回 -0.2 dB 量级；浮置过孔和下馈中和线能保住 S11，但隔离只能到亚 dB；孔缝/馈线偏移可提升隔离趋势，但 S11 会塌陷；贴片斜缝能保持或改善 S11，但没有带来有效 A/B 去耦。
- 下一轮建议：不要继续只靠局部被动几何微调；应切到带受控幅相的独立 A/B 中和支路、外部/板上耦合抵消网络，或重构为真正分离模态的双端口馈电，再统一重调孔缝耦合和匹配网络。
