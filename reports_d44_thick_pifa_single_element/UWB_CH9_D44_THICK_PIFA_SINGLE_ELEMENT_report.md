# D44 厚板短路 PIFA 低成本优化复核报告

## 目标口径

- 结构方向：厚 PCB 顶层铜、短路 via wall/边镀墙、开口槽、腔体边缘耦合与馈点联动；不使用独立 L 单极子金属臂。
- S11 目标：`S11 <= -10.0 dB`。
- 增益目标：Theta `45..90 deg`，最佳连续 `270 deg` 方位窗口内 `GainTotal >= -5.0 dBi`。

## 结论

- 综合结论：本轮低成本厚板 PIFA/边镀腔体电流路径扫描尚未找到 S11 与低仰角覆盖增益同时达标点。
- 已复核候选：`143` 个；S11 达标 `1` 个，增益达标 `35` 个，双指标同时达标 `0` 个。
- 当前排序候选：`#142 h8p0_l14p8_capfeed_f1365_gap0p10_i1p2x3p0`，S11 `-3.221 dB`，最佳 270° 窗口最小 GainTotal `-4.252 dBi`，结果 `未达标`。
- 当前排序候选距离 S11 目标仍差约 `6.779 dB`；说明高低仰角覆盖增益可以达标，但端口匹配仍是主瓶颈。
- S11 最优候选：`#36 h3p5_l8p8_w8p0_sw4p0_fence6p0_feed8p40`，S11 `-10.970 dB`，最佳 270° 窗口最小 GainTotal `-8.573 dBi`。
- S11 最优候选距离增益目标仍差约 `3.573 dB`；说明低高度强短路腔体容易匹配，但低仰角辐射不足。
- 增益最优候选：`#86 h8p0_l12p0_w10p0_sw4p0_fence8p0_feed11p30_lip2p4_w6p0_match_l2p8_c0p22_gap0p08_loadside`，最佳 270° 窗口最小 GainTotal `-3.201 dBi`，S11 `-1.644 dB`。
- 增益最优候选距离 S11 目标仍差约 `8.356 dB`；说明继续单纯抬高/放宽口径会迅速牺牲匹配。

## 数据复核

- 已从现有 native CSV 重新解析 `106` 行，统一使用修正后的 Phi/Theta 轴判断。
- 旧阶段部分行曾按 AEDT 导出标签直接读取，可能把 Phi/Theta 互换后的数据误判为低仰角覆盖；本报告以重新解析后的 CSV 为准。
- 新增几何自由度覆盖：侧向 via wall/边镀墙起点、开路端耦合壁高度与长度、顶层中心槽、板边开口槽、开路端下翻 lip、馈点到短路墙距离。

## 关键候选

| # | 候选 | S11 worst dB | Best 270° min Gain dBi | All-phi min Gain dBi | 结果 |
|---:|---|---:|---:|---:|---|
| 142 | `h8p0_l14p8_capfeed_f1365_gap0p10_i1p2x3p0` | -3.221 | -4.252 | -15.884 | 未达标 |
| 36 | `h3p5_l8p8_w8p0_sw4p0_fence6p0_feed8p40` | -10.970 | -8.573 | -13.441 | 未达标 |
| 86 | `h8p0_l12p0_w10p0_sw4p0_fence8p0_feed11p30_lip2p4_w6p0_match_l2p8_c0p22_gap0p08_loadside` | -1.644 | -3.201 | -10.941 | 未达标 |
| 139 | `h8p0_l14p8_capfeed_f1365_gap0p08_i0p8x2p4` | -3.147 | -3.957 | -15.663 | 未达标 |
| 136 | `h8p0_l14p8_capfeed_f1345_gap0p10_i0p8x2p4` | -3.011 | -4.024 | -18.206 | 未达标 |
| 140 | `h8p0_l14p8_capfeed_f1385_gap0p06_i1p0x2p8` | -3.000 | -4.426 | -13.339 | 未达标 |
| 100 | `h8p0_l14p0_w11p2_f1355_slot` | -2.984 | -3.980 | -17.131 | 未达标 |
| 141 | `h8p0_l15p4_capfeed_f1415_gap0p08_i0p8x2p4` | -2.688 | -4.596 | -12.782 | 未达标 |
| 78 | `h7p2_l9p6_w9p6_sw4p0_fence6p8_feed8p80_match_l2p5_c0p22_loadside` | -2.652 | -4.346 | -14.965 | 未达标 |
| 76 | `h7p2_l9p6_w9p6_sw4p0_fence6p8_feed8p80_lim10_lowcost` | -2.264 | -4.954 | -8.075 | 未达标 |
| 126 | `h8p0_l13p6_w11p2_sw5p8_fence6p0_start2p0_feed13p05_lip1p2_edgec4p8_h7p0_slot7p6x5p0` | -2.220 | -4.833 | -14.294 | 未达标 |
| 95 | `h8p0_w11p2_f1105_slot` | -2.133 | -3.353 | -13.158 | 未达标 |

## 工程判断

- 8 mm PCB-only PIFA 能把最佳 270° 低仰角增益推到门限附近，但端口阻抗过高且强感性，L/C 匹配岛未能把 S11 拉进目标。
- 3.5..4.5 mm 低高度族更容易满足或接近 S11，但最佳 270° 窗口增益明显低于目标，说明低仰角覆盖需要更强竖向/边缘电流。
- 7.2..8.0 mm 高度族能满足低仰角 270° 覆盖增益，但 S11 远离 `-10 dB`，说明当前同相位中心厚板 PIFA 存在明确的匹配/覆盖折中。
- 本轮新增几何路径仍保持低成本加工方式：顶层蚀刻槽、侧向 via wall 或边镀墙、开口端局部耦合壁，不引入独立折弯金属臂。

## 输出文件

- 当前候选 AEDT 工程：`D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\UWB_CH9_D44_THICK_PIFA_SINGLE_ELEMENT_h8p0_l14p8_capfeed_f1365_gap0p10_i1p2x3p0.aedt`
- 候选汇总 CSV：`D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_thick_pifa_single_element\UWB_CH9_D44_THICK_PIFA_SINGLE_ELEMENT_summary.csv`
- 方位窗口 CSV：`D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_thick_pifa_single_element\UWB_CH9_D44_THICK_PIFA_SINGLE_ELEMENT_azimuth_window_summary.csv`
- 指标 JSON：`D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_thick_pifa_single_element\UWB_CH9_D44_THICK_PIFA_SINGLE_ELEMENT_metrics.json`
