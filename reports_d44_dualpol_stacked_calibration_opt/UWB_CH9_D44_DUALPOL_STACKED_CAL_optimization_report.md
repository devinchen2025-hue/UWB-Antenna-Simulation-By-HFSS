# D44 双极化锚点天线叠层寄生贴片与相位中心标定优化报告

## 本轮目标

- 在上一轮镜像边馈真实网络基础上，增加双层过渡/叠层寄生贴片，让上层浮置贴片主导辐射孔径。
- 对比不同寄生贴片边长、空气间隙、旋转角和微小偏移对端口匹配、方向图对称性与 PDOA 曲线漂移的影响。
- 增加等效端口相位中心标定指标：用每个频点/基线的二维相位中心偏移拟合 PDOA 残差，评估硬件误差是否能被后端标定吸收。
- 仍只评估线极化入射 `0 / 45 / 90 / 135 deg`，目标为回波 `<= -10.0 dB`、同阵元 X/Y 隔离 `>= 15.0 dB`、方向图镜像 RMS `<= 3.0 dB`、标定后 PDOA 平均 RMS `<= 10.0 deg`。

## 方法说明

- S 参数阶段先筛选叠层候选，参考候选 `mirror_patch9p25_reference` 只作为上一轮基线。
- 完整复核阶段提取所有端口的嵌入远场，计算未标定双极化向量相关 PDOA、接收端 2x2 幅相矩阵标定后的 PDOA、X/Y 幅相一致性和 E1/E3、E2/E4 镜像方向图误差。
- 相位中心指标先扣除每个 `phi/极化` 曲线的常量相位偏置，再拟合 `dx/dy` 等效基线偏移；`phase_center_calibrated_rms_deg` 越小，说明剩余角度相关相位误差越容易通过相位中心标定处理。

## S 参数筛选

| 排名 | 候选 | 叠层 | 评分 | 最差回波 | X回波 | Y回波 | 回波差 | 同阵元X/Y隔离 | 同馈跨阵元隔离 |
| ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | `stack_p9p55_gap0p80` | 是 | 41.63 | -7.69 dB | -7.69 dB | -7.70 dB | 0.01 dB | 10.38 dB | 15.47 dB |
| 2 | `mirror_patch9p25_reference` | 否 | 46.02 | -7.82 dB | -7.82 dB | -8.10 dB | 0.28 dB | 9.58 dB | 15.28 dB |
| 3 | `stack_drive9p15_par9p75_gap1p20` | 是 | 54.06 | -6.38 dB | -6.82 dB | -6.38 dB | 0.44 dB | 10.39 dB | 14.48 dB |
| 4 | `stack_p9p75_gap1p20` | 是 | 60.95 | -5.76 dB | -5.77 dB | -5.76 dB | 0.01 dB | 10.01 dB | 14.47 dB |
| 5 | `stack_p9p75_gap1p20_wide_out` | 是 | 62.32 | -5.40 dB | -5.40 dB | -5.41 dB | 0.01 dB | 10.34 dB | 14.38 dB |
| 6 | `stack_p9p75_gap1p20_offu0p15` | 是 | 62.48 | -5.32 dB | -5.60 dB | -5.32 dB | 0.28 dB | 10.43 dB | 14.40 dB |
| 7 | `stack_p9p75_gap1p20_offv0p15` | 是 | 63.64 | -5.52 dB | -5.61 dB | -5.52 dB | 0.09 dB | 9.87 dB | 14.43 dB |
| 8 | `stack_p9p95_gap1p60` | 是 | 64.34 | -5.15 dB | -5.15 dB | -5.15 dB | 0.00 dB | 10.59 dB | 13.74 dB |
| 9 | `stack_p9p75_gap1p20_rot45` | 是 | 64.94 | -5.45 dB | -5.60 dB | -5.45 dB | 0.15 dB | 9.72 dB | 14.44 dB |
| 10 | `stack_drive9p35_par9p95_gap1p20` | 是 | 69.75 | -4.53 dB | -4.53 dB | -4.66 dB | 0.13 dB | 10.43 dB | 13.93 dB |

## 完整复核结果

| 候选 | 综合评分 | 最差回波 | 同阵元X/Y隔离 | 方向图镜像RMS | 相位中心残差RMS | 相位中心偏移均值 | 标定后PDOA均值RMS | 标定后PDOA最大漂移 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `mirror_patch9p25_reference` | 216.59 | -7.82 dB | 9.58 dB | 11.56 dB | 129.72 deg | 10.734 mm | 51.32 deg | 179.98 deg |
| `stack_drive9p15_par9p75_gap1p20` | 222.39 | -6.38 dB | 10.39 dB | 11.68 dB | 124.24 deg | 10.266 mm | 52.06 deg | 179.94 deg |
| `stack_p9p55_gap0p80` | 224.17 | -6.16 dB | 10.16 dB | 11.74 dB | 124.74 deg | 12.127 mm | 51.34 deg | 179.95 deg |

## 最优候选

- 候选：`stack_drive9p15_par9p75_gap1p20`
- 叠层寄生贴片：`启用`
- 说明：缩小下层驱动贴片、保持中等寄生贴片，弱化下层边馈加载。
- AEDT 工程：`D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\UWB_CH9_Diamond_CP_Array_D44_DUALPOL_XY.aedt`
- 最差回波：`-6.38 dB`
- X/Y 回波差：`0.44 dB`
- 同阵元 X/Y 隔离：`10.39 dB`
- 同馈跨阵元隔离：`14.48 dB`
- 方向图镜像 RMS：`11.68 dB`
- X/Y 幅度 RMS 差：`5.30 dB`
- X/Y 相位离散 RMS：`74.70 deg`
- 未标定双极化向量 PDOA 平均 RMS：`88.40 deg`
- 2x2 标定后 PDOA 平均 RMS：`52.06 deg`
- 2x2 标定后 PDOA 最大漂移：`179.94 deg`
- 相位中心校正后残差 RMS：`124.24 deg`
- 相位中心校正后 95 分位残差：`243.55 deg`
- 等效相位中心偏移均值：`10.266 mm`

## 最优几何参数

- `patch_side_mm`: `9.150`
- `feed_offset_u_mm`: `3.400`
- `feed_pad_radius_mm`: `0.280`
- `port_width_mm`: `0.500`
- `microstrip_feed_enabled`: `1.000`
- `microstrip_feedline_length_mm`: `1.780`
- `microstrip_feedline_width_mm`: `0.580`
- `microstrip_match_length_mm`: `0.480`
- `microstrip_match_width_mm`: `0.340`
- `microstrip_transform2_length_mm`: `0.550`
- `microstrip_transform2_width_mm`: `0.500`
- `microstrip_feed_mirror_enabled`: `1.000`
- `dualpol_parasitic_enabled`: `1.000`
- `parasitic_side_mm`: `9.750`
- `parasitic_corner_cut_mm`: `0.000`
- `parasitic_rotation_deg`: `0.000`
- `parasitic_offset_u_mm`: `0.000`
- `parasitic_offset_v_mm`: `0.000`
- `air_gap_mm`: `1.200`
- `neutralization_branch_enabled`: `0.000`
- `local_dgs_enabled`: `0.000`
- `isolation_slot_enabled`: `1.000`
- `isolation_slot_length_mm`: `10.000`
- `isolation_slot_width_mm`: `0.420`
- `isolation_slot_inner_mm`: `3.200`

## 与上一轮最优对比

| 指标 | 上一轮 | 本轮 | 变化 |
| --- | ---: | ---: | ---: |
| 最差回波 | -7.82 dB | -6.38 dB | 1.44 |
| 同阵元 X/Y 隔离 | 9.58 dB | 10.39 dB | 0.81 |
| X/Y 回波差 | 0.28 dB | 0.44 dB | 0.15 |
| 方向图镜像 RMS | 11.56 dB | 11.68 dB | 0.12 |
| 标定后 PDOA 平均 RMS | 51.32 deg | 52.06 deg | 0.75 |
| 标定后 PDOA 最大漂移 | 179.98 deg | 179.94 deg | -0.04 |

## 达标情况

- S 参数/隔离目标：`未通过`。
- X/Y 幅相一致性目标：`未通过`。
- 标定后 PDOA 稳定性目标：`未通过`。
- 方向图镜像对称性目标：`未通过`。
- 相位中心残差目标：`未通过`。
- 全部目标：`未通过`。

## 工程判断

- 若本轮叠层候选优于参考候选，说明上层浮置贴片已经开始隔离馈线布局对辐射孔径的扰动，下一步应围绕寄生片尺寸、空气层和微带匹配段做更细扫描。
- 若叠层候选只改善方向图或相位中心残差但牺牲端口匹配，下一步应引入真正的双层过渡结构，例如下层驱动片到上层寄生片的可控缝隙/电容耦合窗口。
- 若相位中心残差仍很大，说明单一基线相位中心模型不足，需要把每阵元方向图复数响应表作为接收端标定矩阵的一部分。

## 输出文件

- S 参数筛选：`D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_dualpol_stacked_calibration_opt\UWB_CH9_D44_DUALPOL_STACKED_CAL_sparam_screening.csv`
- 完整复核：`D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_dualpol_stacked_calibration_opt\UWB_CH9_D44_DUALPOL_STACKED_CAL_full_validation.csv`
- 最优未标定曲线：`D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_dualpol_stacked_calibration_opt\UWB_CH9_D44_DUALPOL_STACKED_CAL_best_curves.csv`
- 最优未标定汇总：`D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_dualpol_stacked_calibration_opt\UWB_CH9_D44_DUALPOL_STACKED_CAL_best_summary.csv`
- 最优 2x2 标定后曲线：`D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_dualpol_stacked_calibration_opt\UWB_CH9_D44_DUALPOL_STACKED_CAL_best_calibrated_curves.csv`
- 最优 2x2 标定后汇总：`D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_dualpol_stacked_calibration_opt\UWB_CH9_D44_DUALPOL_STACKED_CAL_best_calibrated_summary.csv`
- 最优相位中心标定明细：`D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_dualpol_stacked_calibration_opt\UWB_CH9_D44_DUALPOL_STACKED_CAL_best_phase_center.csv`
- 最优 JSON：`D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_dualpol_stacked_calibration_opt\UWB_CH9_D44_DUALPOL_STACKED_CAL_best.json`
