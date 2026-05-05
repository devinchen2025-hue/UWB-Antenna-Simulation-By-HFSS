# D44 双极化孔缝耦合 S11 匹配优化报告

## 目标

- 持续迭代优化当前八端口双极化孔缝耦合模型的 S11/回波，目标为全端口带内最差回波 `<= -10.0 dB`。
- 本轮只跑 S 参数快速筛选，不重新导出远场；重点扫描贴片尺寸、孔缝长度/宽度、下层馈线宽度/长度和下层介质厚度。
- 当前可视模型参考候选 `slot_l3p6_w0p45_feed0p60` 的最差回波为 `-1.79 dB`；上一轮 S 参数筛选最佳为 `-2.29 dB`。

## 筛选排名

| 排名 | 候选 | 最差回波 | X回波 | Y回波 | 回波差 | 同阵元X/Y隔离 | 同馈跨阵元隔离 |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | `p9p75_l5p6_w0p70_fw0p80` | -3.35 dB | -3.35 dB | -3.38 dB | 0.03 dB | 1.29 dB | 42.19 dB |
| 2 | `p9p55_l4p8_w0p60_fw0p70` | -2.93 dB | -2.96 dB | -2.93 dB | 0.04 dB | 1.18 dB | 41.43 dB |
| 3 | `p9p75_l5p2_w0p65_fw0p75` | -2.83 dB | -2.83 dB | -2.87 dB | 0.04 dB | 2.05 dB | 42.25 dB |
| 4 | `p9p35_l4p8_w0p60_fw0p70` | -2.81 dB | -2.84 dB | -2.81 dB | 0.03 dB | 1.50 dB | 39.24 dB |
| 5 | `p8p95_l4p4_w0p58_fw0p68` | -2.79 dB | -2.79 dB | -2.79 dB | 0.00 dB | 1.70 dB | 29.94 dB |
| 6 | `p9p55_l5p2_w0p65_fw0p75` | -2.74 dB | -2.74 dB | -2.76 dB | 0.02 dB | 1.79 dB | 40.30 dB |
| 7 | `p9p25_l4p5_w0p58_fw0p68` | -2.60 dB | -2.60 dB | -2.63 dB | 0.03 dB | 2.36 dB | 38.37 dB |
| 8 | `p9p05_l4p4_w0p58_fw0p68` | -2.59 dB | -2.59 dB | -2.63 dB | 0.03 dB | 1.53 dB | 34.80 dB |
| 9 | `p9p05_l4p25_w0p56_fw0p66` | -2.37 dB | -2.37 dB | -2.37 dB | 0.01 dB | 2.18 dB | 37.17 dB |
| 10 | `p8p95_l4p2_w0p55_fw0p65` | -2.31 dB | -2.33 dB | -2.31 dB | 0.02 dB | 2.40 dB | 40.22 dB |
| 11 | `p9p35_l4p4_w0p55_fw0p65_ref` | -2.29 dB | -2.29 dB | -2.30 dB | 0.01 dB | 1.37 dB | 38.80 dB |
| 12 | `p9p15_l4p4_w0p55_fw0p65` | -2.27 dB | -2.29 dB | -2.27 dB | 0.02 dB | 2.43 dB | 43.01 dB |
| 13 | `p9p00_l4p2_w0p56_fw0p66` | -2.23 dB | -2.23 dB | -2.25 dB | 0.02 dB | 2.30 dB | 42.19 dB |
| 14 | `p8p95_l4p2_w0p60_fw0p70` | -2.18 dB | -2.18 dB | -2.29 dB | 0.11 dB | 3.11 dB | 40.37 dB |
| 15 | `p9p15_l4p0_w0p50_fw0p60` | -2.06 dB | -2.08 dB | -2.06 dB | 0.01 dB | 1.32 dB | 38.63 dB |
| 16 | `p8p90_l4p15_w0p54_fw0p64` | -2.04 dB | -2.07 dB | -2.04 dB | 0.04 dB | 2.22 dB | 35.65 dB |
| 17 | `p8p75_l4p0_w0p50_fw0p65` | -1.88 dB | -1.94 dB | -1.88 dB | 0.06 dB | 3.67 dB | 39.62 dB |
| 18 | `p8p55_l3p8_w0p50_fw0p60` | -1.84 dB | -1.84 dB | -1.85 dB | 0.01 dB | 2.12 dB | 36.60 dB |
| 19 | `p8p95_l3p8_w0p50_fw0p60` | -1.80 dB | -1.81 dB | -1.80 dB | 0.01 dB | 2.01 dB | 39.18 dB |
| 20 | `p8p95_l4p2_w0p55_fw0p65_len12` | -1.62 dB | -1.62 dB | -1.65 dB | 0.03 dB | 5.25 dB | 46.14 dB |
| 21 | `p8p55_l3p4_w0p45_fw0p55` | -1.03 dB | -1.03 dB | -1.17 dB | 0.14 dB | 3.08 dB | 36.22 dB |
| 22 | `p8p75_l3p6_w0p45_fw0p60` | -0.70 dB | -0.74 dB | -0.70 dB | 0.04 dB | 2.06 dB | 40.46 dB |
| 23 | `p8p95_l4p2_w0p55_fw0p65_len8` | -0.46 dB | -0.46 dB | -0.52 dB | 0.06 dB | 21.07 dB | 33.70 dB |
| 24 | `p8p75_l4p0_w0p50_fw0p65_h0p508` | -0.36 dB | -0.51 dB | -0.36 dB | 0.15 dB | 3.62 dB | 20.29 dB |

## 最佳候选

- 候选：`p9p75_l5p6_w0p70_fw0p80`
- 最差回波：`-3.35 dB`
- 相对当前可视模型变化：`-1.56 dB`（负值为改善）。
- 相对上一轮 S 参数最佳变化：`-1.06 dB`（负值为改善）。
- S11 目标：`未通过`。

## 最佳几何参数

- `patch_side_mm`: `9.750`
- `port_width_mm`: `0.500`
- `dualpol_slotcoupled_enabled`: `1.000`
- `feed_substrate_h_mm`: `0.254`
- `slot_coupled_aperture_length_a_mm`: `5.600`
- `slot_coupled_aperture_length_b_mm`: `5.600`
- `slot_coupled_aperture_width_mm`: `0.700`
- `slot_coupled_offset_a_mm`: `0.000`
- `slot_coupled_offset_b_mm`: `0.000`
- `slot_coupled_aperture_center_a_v_mm`: `0.000`
- `slot_coupled_aperture_center_b_u_mm`: `0.000`
- `slot_coupled_feedline_length_mm`: `10.000`
- `slot_coupled_feedline_width_mm`: `0.800`
- `slot_coupled_feedline_offset_a_v_mm`: `0.000`
- `slot_coupled_feedline_offset_b_u_mm`: `0.000`
- `dualpol_parasitic_enabled`: `0.000`
- `parasitic_side_mm`: `0.000`
- `air_gap_mm`: `0.000`
- `isolation_slot_enabled`: `1.000`
- `isolation_slot_length_mm`: `10.000`
- `isolation_slot_width_mm`: `0.420`
- `isolation_slot_inner_mm`: `3.200`

## 工程判断

- 更大贴片配更长、更宽的中心孔缝后最差回波出现正向改善，说明当前孔缝耦合强度不足是 S11 的主要限制。
- 代价是同阵元 X/Y 隔离下降，后续需要把 S11 调谐支节和 A/B 去耦结构分开设计。
- 如果仍未到 -10 dB，下一轮应在下层孔缝馈线中加入真正的开路/短路调谐支节、阶梯阻抗线或电容耦合调谐，而不是继续只扫矩形孔缝。
- 本轮重建的 AEDT 工程保存为最佳 S11 候选，可直接打开检查八端口 S 参数。
- 补充尝试：第三轮新增更强孔缝候选时，`p9p75_l6p0_w0p75_fw0p85` 在 AEDT 建模早期停滞，已停止该进程并将工程重建回已完成最佳候选；本报告只统计 24 个已完成候选。

## 输出文件

- S 参数筛选 CSV：`D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_dualpol_s11_slotmatch_opt\UWB_CH9_D44_DUALPOL_S11_SLOTMATCH_sparam_screening.csv`
- 最佳 JSON：`D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_dualpol_s11_slotmatch_opt\UWB_CH9_D44_DUALPOL_S11_SLOTMATCH_best.json`
- 中文报告：`D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_dualpol_s11_slotmatch_opt\UWB_CH9_D44_DUALPOL_S11_SLOTMATCH_optimization_report.md`
- AEDT 工程：`D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\UWB_CH9_Diamond_CP_Array_D44_DUALPOL_XY.aedt`
- 参数 JSON：`D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\UWB_CH9_Diamond_CP_Array_D44_DUALPOL_XY_params.json`
