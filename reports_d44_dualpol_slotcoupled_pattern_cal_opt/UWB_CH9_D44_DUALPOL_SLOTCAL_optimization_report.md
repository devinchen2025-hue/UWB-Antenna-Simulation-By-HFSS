# D44 双极化锚点天线缝隙耦合窗口与复方向图标定报告

## 本轮目标

- 从叠层寄生贴片路线转向真实双层过渡：下层微带线、接地层正交缝隙窗口、上层双极化贴片。
- 扫描缝隙长度/宽度、A/B 槽错位、下层馈线宽度、下层介质厚度和是否保留弱寄生贴片。
- 在完整远场复核中导出每阵元、每端口的复数方向图标定表，给后端做按角度/频点查表的矢量标定。
- 仍只评估线极化入射 `0 / 45 / 90 / 135 deg`；目标为回波 `<= -10.0 dB`、同阵元 X/Y 隔离 `>= 15.0 dB`、方向图镜像 RMS `<= 3.0 dB`、标定后 PDOA 平均 RMS `<= 10.0 deg`。

## 方法说明

- S 参数阶段优先筛选真实缝隙耦合窗口候选，`stacked_reference_prev` 只作为上一轮叠层方案对照。
- 完整复核阶段提取所有端口嵌入远场，计算未标定双极化向量相关 PDOA、2x2 幅相标定 PDOA、方向图镜像误差和等效相位中心残差。
- 复方向图标定表包含 `source/element/feed/freq/theta/phi` 索引，以及 `rETheta/rEPhi` 的实部/虚部和 0/45/90/135 deg 线极化投影。

## S 参数筛选

| 排名 | 候选 | 缝隙耦合 | 评分 | 最差回波 | X回波 | Y回波 | 回波差 | 同阵元X/Y隔离 | 同馈跨阵元隔离 |
| ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | `stacked_reference_prev` | 否 | 55.06 | -6.38 dB | -6.82 dB | -6.38 dB | 0.44 dB | 10.39 dB | 14.48 dB |
| 2 | `slot_l3p6_w0p45_feed0p60` | 是 | 125.55 | -1.79 dB | -1.83 dB | -1.79 dB | 0.04 dB | 2.83 dB | 38.17 dB |
| 3 | `slot_l4p0_w0p50_feed0p60` | 是 | 128.37 | -1.97 dB | -1.97 dB | -1.98 dB | 0.01 dB | 1.98 dB | 44.14 dB |
| 4 | `slot_l4p4_w0p55_feed0p65` | 是 | 128.81 | -2.29 dB | -2.29 dB | -2.30 dB | 0.01 dB | 1.37 dB | 38.80 dB |
| 5 | `slot_l3p2_w0p40_feed0p55_patch9p35` | 是 | 133.03 | -0.99 dB | -0.99 dB | -1.20 dB | 0.22 dB | 2.62 dB | 32.89 dB |
| 6 | `slot_sep_l4p8_w0p70_h0p10_feed0p80` | 是 | 134.09 | -0.06 dB | -0.06 dB | -0.06 dB | 0.00 dB | 3.89 dB | 50.95 dB |
| 7 | `slot_sep_l5p0_w0p70_h0p18_feed0p80_patch9p55` | 是 | 145.86 | -0.15 dB | -0.15 dB | -0.16 dB | 0.01 dB | 1.38 dB | 43.50 dB |
| 8 | `slot_sep_l5p2_w0p75_h0p18_feed0p85` | 是 | 146.06 | -0.12 dB | -0.12 dB | -0.17 dB | 0.05 dB | 1.40 dB | 39.85 dB |
| 9 | `slot_sep_l4p4_w0p65_h0p18_feed0p75` | 是 | 146.68 | -0.21 dB | -0.23 dB | -0.21 dB | 0.03 dB | 1.13 dB | 38.28 dB |
| 10 | `slot_sep_l4p4_w0p65_h0p18_par9p75` | 是 | 146.98 | -0.22 dB | -0.22 dB | -0.23 dB | 0.00 dB | 1.05 dB | 39.21 dB |

## 完整复核结果

| 候选 | 综合评分 | 最差回波 | 同阵元X/Y隔离 | 方向图镜像RMS | 相位中心残差RMS | 标定后PDOA均值RMS | 标定后PDOA最大漂移 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `slot_l3p6_w0p45_feed0p60` | 253.20 | -1.79 dB | 2.83 dB | 7.68 dB | 86.91 deg | 32.45 deg | 179.93 deg |

## 最优候选

- 候选：`slot_l3p6_w0p45_feed0p60`
- 缝隙耦合窗口：`启用`
- 说明：居中孔缝馈电，窗口略加长，完整复核显示 PDOA 与镜像对称性优于叠层参考，但匹配与同阵元 X/Y 隔离仍未达标。
- AEDT 工程：`D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\UWB_CH9_Diamond_CP_Array_D44_DUALPOL_XY.aedt`
- 最差回波：`-1.79 dB`
- X/Y 回波差：`0.04 dB`
- 同阵元 X/Y 隔离：`2.83 dB`
- 同馈跨阵元隔离：`38.17 dB`
- 方向图镜像 RMS：`7.68 dB`
- X/Y 幅度 RMS 差：`8.67 dB`
- X/Y 相位离散 RMS：`69.72 deg`
- 未标定双极化向量 PDOA 平均 RMS：`73.14 deg`
- 2x2 标定后 PDOA 平均 RMS：`32.45 deg`
- 2x2 标定后 PDOA 最大漂移：`179.93 deg`
- 相位中心校正后残差 RMS：`86.91 deg`
- 复方向图标定表行数：`33288`

## 最优几何参数

- `patch_side_mm`: `9.350`
- `feed_offset_u_mm`: `3.400`
- `feed_pad_radius_mm`: `0.280`
- `port_width_mm`: `0.500`
- `microstrip_feed_enabled`: `0.000`
- `microstrip_feedline_length_mm`: `1.780`
- `microstrip_feedline_width_mm`: `0.580`
- `microstrip_match_length_mm`: `0.480`
- `microstrip_match_width_mm`: `0.340`
- `microstrip_transform2_length_mm`: `0.550`
- `microstrip_transform2_width_mm`: `0.500`
- `microstrip_feed_mirror_enabled`: `1.000`
- `dualpol_parasitic_enabled`: `0.000`
- `parasitic_side_mm`: `0.000`
- `parasitic_corner_cut_mm`: `0.000`
- `parasitic_rotation_deg`: `0.000`
- `parasitic_offset_u_mm`: `0.000`
- `parasitic_offset_v_mm`: `0.000`
- `air_gap_mm`: `0.000`
- `dualpol_slotcoupled_enabled`: `1.000`
- `feed_substrate_h_mm`: `0.254`
- `slot_coupled_aperture_length_a_mm`: `3.600`
- `slot_coupled_aperture_length_b_mm`: `3.600`
- `slot_coupled_aperture_width_mm`: `0.450`
- `slot_coupled_offset_a_mm`: `0.000`
- `slot_coupled_offset_b_mm`: `0.000`
- `slot_coupled_aperture_center_a_v_mm`: `0.000`
- `slot_coupled_aperture_center_b_u_mm`: `0.000`
- `slot_coupled_feedline_length_mm`: `10.000`
- `slot_coupled_feedline_width_mm`: `0.600`
- `slot_coupled_feedline_offset_a_v_mm`: `0.000`
- `slot_coupled_feedline_offset_b_u_mm`: `0.000`
- `neutralization_branch_enabled`: `0.000`
- `local_dgs_enabled`: `0.000`
- `isolation_slot_enabled`: `1.000`
- `isolation_slot_length_mm`: `10.000`
- `isolation_slot_width_mm`: `0.420`
- `isolation_slot_inner_mm`: `3.200`

## 与上一轮叠层最优对比

| 指标 | 上一轮 | 本轮 | 变化 |
| --- | ---: | ---: | ---: |
| 最差回波 | -6.38 dB | -1.79 dB | 4.59 |
| 同阵元 X/Y 隔离 | 10.39 dB | 2.83 dB | -7.56 |
| X/Y 回波差 | 0.44 dB | 0.04 dB | -0.40 |
| 方向图镜像 RMS | 11.68 dB | 7.68 dB | -4.01 |
| 标定后 PDOA 平均 RMS | 52.06 deg | 32.45 deg | -19.62 |
| 相位中心残差 RMS | 124.24 deg | 86.91 deg | -37.33 |

## 达标情况

- S 参数/隔离目标：`未通过`。
- X/Y 幅相一致性目标：`未通过`。
- 标定后 PDOA 稳定性目标：`未通过`。
- 方向图镜像对称性目标：`未通过`。
- 相位中心残差目标：`未通过`。
- 全部目标：`未通过`。

## 工程判断

- 如果缝隙耦合候选优于叠层参考，说明馈线从辐射贴片主电流区退耦有效，下一轮应围绕窗口尺寸和馈线端口阻抗继续细扫。
- 如果匹配不足但方向图或相位中心改善，下一轮应增加可调电容耦合窗口、下层馈线开路支节或短路过孔调谐。
- 如果 PDOA 仍大幅漂移，应把复方向图表直接用于后端按角度/频点的矢量标定，而不是只依赖 2x2 幅相矩阵。

## 输出文件

- S 参数筛选：`D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_dualpol_slotcoupled_pattern_cal_opt\UWB_CH9_D44_DUALPOL_SLOTCAL_sparam_screening.csv`
- 完整复核：`D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_dualpol_slotcoupled_pattern_cal_opt\UWB_CH9_D44_DUALPOL_SLOTCAL_full_validation.csv`
- 最优未标定曲线：`D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_dualpol_slotcoupled_pattern_cal_opt\UWB_CH9_D44_DUALPOL_SLOTCAL_best_curves.csv`
- 最优 2x2 标定后曲线：`D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_dualpol_slotcoupled_pattern_cal_opt\UWB_CH9_D44_DUALPOL_SLOTCAL_best_calibrated_curves.csv`
- 最优相位中心标定明细：`D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_dualpol_slotcoupled_pattern_cal_opt\UWB_CH9_D44_DUALPOL_SLOTCAL_best_phase_center.csv`
- 最优复方向图标定表 CSV：`D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_dualpol_slotcoupled_pattern_cal_opt\UWB_CH9_D44_DUALPOL_SLOTCAL_best_complex_pattern_table.csv`
- 最优复方向图标定表说明 JSON：`D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_dualpol_slotcoupled_pattern_cal_opt\UWB_CH9_D44_DUALPOL_SLOTCAL_best_complex_pattern_table.json`
- 最优 JSON：`D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_dualpol_slotcoupled_pattern_cal_opt\UWB_CH9_D44_DUALPOL_SLOTCAL_best.json`

## 本轮补充说明

- 已完成 10 个候选的 S 参数筛选；第二轮完整复核在重复导出 `slot_l3p6_w0p45_feed0p60` 远场时停滞，已停止冗余进程。
- 完整复核指标沿用本轮已成功完成的 `slot_l3p6_w0p45_feed0p60` 结果；该候选仍是当前孔缝耦合路线的最佳折中。
- 分离式孔缝候选没有改善匹配，说明当前问题不是简单的窗口中心重叠，而是孔缝、馈线、贴片之间缺少可调阻抗变换或调谐支节。
