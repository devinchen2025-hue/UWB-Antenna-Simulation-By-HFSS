# D44 厚板短路 PIFA 低成本优化复核报告

## 目标口径

- 结构方向：厚 PCB 顶层铜、短路 via wall/边镀墙、局部匹配岛；不使用独立 L 单极子金属臂。
- S11 目标：`S11 <= -10.0 dB`。
- 增益目标：Theta `45..90 deg`，最佳连续 `270 deg` 方位窗口内 `GainTotal >= -5.0 dBi`。

## 结论

- 综合结论：本轮低成本厚板 PIFA/匹配岛扫描尚未找到 S11 与低仰角覆盖增益同时达标点。
- 已复核候选：`83` 个；S11 达标 `1` 个，增益达标 `15` 个，双指标同时达标 `0` 个。
- 当前排序候选：`#78 h7p2_l9p6_w9p6_sw4p0_fence6p8_feed8p80_match_l2p5_c0p22_loadside`，S11 `-2.652 dB`，最佳 270° 窗口最小 GainTotal `-4.346 dBi`，结果 `未达标`。
- S11 最优候选：`#36 h3p5_l8p8_w8p0_sw4p0_fence6p0_feed8p40`，S11 `-10.970 dB`，最佳 270° 窗口最小 GainTotal `-8.573 dBi`。
- 增益最优候选：`#86 h8p0_l12p0_w10p0_sw4p0_fence8p0_feed11p30_lip2p4_w6p0_match_l2p8_c0p22_gap0p08_loadside`，最佳 270° 窗口最小 GainTotal `-3.201 dBi`，S11 `-1.644 dB`。

## 数据复核

- 已从现有 native CSV 重新解析 `58` 行，统一使用修正后的 Phi/Theta 轴判断。
- 旧阶段部分行曾按 AEDT 导出标签直接读取，可能把 Phi/Theta 互换后的数据误判为低仰角覆盖；本报告以重新解析后的 CSV 为准。
- 新增阻抗诊断：8 mm 高增益底座约 `111 + j257 ohm`，4.5 mm 候选 43 约 `78.9 + j62.6 ohm`。

## 关键候选

| # | 候选 | S11 worst dB | Best 270° min Gain dBi | All-phi min Gain dBi | 结果 |
|---:|---|---:|---:|---:|---|
| 43 | `h4p5_l9p2_w8p4_sw4p0_fence6p0_feed8p80` | -6.351 | -9.510 | -12.612 | 未达标 |
| 51 | `h8p0_l8p0_w8p0_sw4p0_fence6p0_feed7p55_lim10_lowcost` | -1.202 | -4.762 | -5.494 | 未达标 |
| 53 | `h8p0_l8p0_w8p0_sw4p0_fence6p0_feed7p55_lim10_lowcost_c0p09_l10p7` | -1.257 | -5.153 | -9.703 | 未达标 |
| 58 | `h4p5_l9p2_w8p4_sw4p0_fence6p0_feed8p80_c0p25_l5p6` | -9.608 | -10.005 | -16.626 | 未达标 |

## 工程判断

- 8 mm PCB-only PIFA 能把最佳 270° 低仰角增益推到门限附近，但端口阻抗过高且强感性，L/C 匹配岛未能把 S11 拉进目标。
- 候选 43 的阻抗更容易匹配；候选 58 已把 S11 推到接近 `-10 dB`，但低仰角覆盖增益明显塌陷，说明纯匹配网络会改变有效辐射电流，不是最终解。
- 低成本方向仍应保留，但下一轮应优先改几何电流路径：边镀/过孔墙位置、开口槽、腔体边缘耦合与馈点位置联动，而不是继续只放大 L/C 匹配值。

## 输出文件

- 当前候选 AEDT 工程：`D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\UWB_CH9_D44_THICK_PIFA_SINGLE_ELEMENT_h7p2_l9p6_w9p6_sw4p0_fence6p8_feed8p80_match_l2p5_c0p22_loadside.aedt`
- 候选汇总 CSV：`D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_thick_pifa_single_element\UWB_CH9_D44_THICK_PIFA_SINGLE_ELEMENT_summary.csv`
- 方位窗口 CSV：`D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_thick_pifa_single_element\UWB_CH9_D44_THICK_PIFA_SINGLE_ELEMENT_azimuth_window_summary.csv`
- 指标 JSON：`D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_thick_pifa_single_element\UWB_CH9_D44_THICK_PIFA_SINGLE_ELEMENT_metrics.json`
