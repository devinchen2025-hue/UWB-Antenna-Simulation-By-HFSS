# D44 厚板短路 PIFA/腔体化单阵元验证报告

## 目标与口径

- 验证对象：去除 A/B/L 后的单端口厚板短路 PIFA/准腔体阵元，单阵元相位中心放在阵元中心参考点。
- 匹配目标：`S11 <= -10.0 dB`。
- 增益目标：Theta `45..90 deg`，在最佳连续 `270 deg` 方位窗口内 `GainTotal >= -5.0 dBi`。
- 说明：本阶段只做单阵元可行性验证，不评估 4 阵元互耦、PDOA 单调性或整机遮挡。

## 最佳候选

- 选择口径：若没有候选同时满足 S11 和增益，则在增益达标候选中优先选择 S11 最接近目标的候选。
- 候选序号：`23`。
- 候选：`h5p0_l8p8_w8p0_sw4p0_fence6p0_feed8p40`。
- S11 最差值：`-4.786 dB`。
- 最佳 270° 窗口：Phi `0..270 deg`。
- 最佳 270° 窗口最小 GainTotal：`-2.144 dBi`，最差点 Theta `90 deg` / Phi `90 deg`。
- 全 360° 方位最小 GainTotal：`-2.144 dBi`。

## 达标情况

- S11：`未达标`。
- 270° 方位增益：`达标`。
- 综合结论：`未完全达标`。

## 复核结论

- 已完成候选数：`25` 个，所有候选在 Theta `45..90 deg`、最佳连续 `270 deg` 方位窗口内均满足 `GainTotal >= -5.0 dBi`。
- S11 最优候选：`#23 h5p0_l8p8_w8p0_sw4p0_fence6p0_feed8p40`，S11 `-4.786 dB`，距离 `-10 dB` 目标仍差约 `5.21 dB`。
- 增益最优候选：`#25 h6p5_l8p4_w8p0_feed7p90`，最佳 270° 窗口最小 GainTotal `-0.691 dBi`，但 S11 `-2.387 dB`。
- 靠近开路端的真实几何馈电是本轮最有效方向，S11 从早期直接馈电的约 `-0.06..-0.33 dB` 改善到 `-4.786 dB`，同时低仰角增益仍保持明显余量。
- 外接匹配岛候选 11..16 已修正为 AEDT `Serial` 串联 RLC 写法，但 S11 对 L/C 数值不敏感，当前 lumped matching 拓扑不能作为达标签核依据。
- 复阻抗诊断文件：`D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_thick_pifa_single_element\h5p0_l8p8_w8p0_feed3p80_c0p085_l0p70_complex_serial_native_s_parameters.csv`；该匹配岛样例在 8 GHz 端口仍约为 `2.06 + j20.04 ohm`。

## 候选汇总

| # | 候选 | S11 worst dB | Best 270° min Gain dBi | All-phi min Gain dBi | 结果 |
|---:|---|---:|---:|---:|---|
| 1 | `h5p0_l8p8_w8p0_feed1p25` | -0.057 | -3.047 | -3.047 | 未达标 |
| 2 | `h5p0_l9p6_w8p2_feed1p45` | -0.056 | -3.167 | -3.167 | 未达标 |
| 3 | `h5p8_l8p6_w8p0_feed1p20` | -0.054 | -2.348 | -2.348 | 未达标 |
| 4 | `h4p5_l10p4_w8p6_feed1p65` | -0.060 | -3.695 | -3.695 | 未达标 |
| 5 | `h5p0_l8p8_w9p6_feed1p10_wide` | -0.078 | -3.186 | -3.186 | 未达标 |
| 6 | `h5p0_l8p8_w8p0_feed1p25_lip0p8` | -0.053 | -2.983 | -2.983 | 未达标 |
| 7 | `h5p0_l8p8_w8p0_feed2p20` | -0.122 | -3.022 | -3.022 | 未达标 |
| 8 | `h5p0_l8p8_w8p0_feed3p00` | -0.200 | -3.263 | -3.263 | 未达标 |
| 9 | `h5p0_l8p8_w8p0_feed3p80` | -0.328 | -2.935 | -2.935 | 未达标 |
| 10 | `h5p0_l9p6_w8p2_feed3p20` | -0.173 | -3.010 | -3.010 | 未达标 |
| 11 | `h5p0_l8p8_w8p0_feed3p80_c0p093_l0p64` | -0.616 | -2.040 | -2.881 | 未达标 |
| 12 | `h5p0_l8p8_w8p0_feed3p80_c0p085_l0p70` | -0.616 | -2.040 | -2.881 | 未达标 |
| 13 | `h5p0_l8p8_w8p0_feed3p80_c0p105_l0p58` | -0.616 | -2.040 | -2.881 | 未达标 |
| 14 | `h5p0_l8p8_w8p0_feed3p80_c0p45_l0p24` | -0.616 | -2.040 | -2.881 | 未达标 |
| 15 | `h5p0_l8p8_w8p0_feed3p80_c0p65_l0p20` | -0.616 | -2.040 | -2.881 | 未达标 |
| 16 | `h5p0_l8p8_w8p0_feed3p80_c0p90_l0p16` | -0.616 | -2.040 | -2.881 | 未达标 |
| 17 | `h5p0_l8p8_w8p0_feed5p50` | -0.927 | -2.407 | -2.407 | 未达标 |
| 18 | `h5p0_l8p8_w8p0_feed7p00` | -2.025 | -2.204 | -2.204 | 未达标 |
| 19 | `h5p0_l8p8_w8p0_feed8p00` | -2.690 | -1.456 | -1.456 | 未达标 |
| 20 | `h5p0_l10p4_w8p6_feed8p80` | -1.887 | -1.839 | -1.990 | 未达标 |
| 21 | `h5p8_l8p6_w8p0_feed7p80` | -2.517 | -1.285 | -1.285 | 未达标 |
| 22 | `h5p0_l8p8_w8p0_feed8p40` | -3.568 | -1.031 | -1.150 | 未达标 |
| 23 | `h5p0_l8p8_w8p0_sw4p0_fence6p0_feed8p40` | -4.786 | -2.144 | -2.144 | 未达标 |
| 24 | `h5p0_l7p8_w8p0_feed7p40` | -3.852 | -1.602 | -1.602 | 未达标 |
| 25 | `h6p5_l8p4_w8p0_feed7p90` | -2.387 | -0.691 | -0.691 | 未达标 |

## 工程判断

- 该方案避免了独立 4.8 mm L 单极子金属臂，制造上可转化为厚 PCB 顶层铜箔、短路 via wall/边镀墙和局部开口腔体。
- 方向图侧已经满足低仰角覆盖目标；当前瓶颈是端口匹配，不是低仰角辐射能力。
- 下一轮不建议回退到 A/B 贴片低仰角硬覆盖；应改为真实分布式馈电/耦合结构，例如 inset/slot 耦合、短路墙开槽馈电、带清晰回流路径的 50 ohm 微带过渡，或可制造的板内/板边耦合馈电。
- 单阵元 S11 达标后，再扩展到 4 阵元，保持约 17 mm 相位中心间距并复核互耦、相位单调性和人体/外壳遮挡。

## 输出文件

- 最佳 AEDT 工程：`D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\UWB_CH9_D44_THICK_PIFA_SINGLE_ELEMENT_h5p0_l8p8_w8p0_sw4p0_fence6p0_feed8p40.aedt`
- 候选汇总 CSV：`D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_thick_pifa_single_element\UWB_CH9_D44_THICK_PIFA_SINGLE_ELEMENT_summary.csv`
- 方位窗口 CSV：`D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_thick_pifa_single_element\UWB_CH9_D44_THICK_PIFA_SINGLE_ELEMENT_azimuth_window_summary.csv`
- 指标 JSON：`D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_thick_pifa_single_element\UWB_CH9_D44_THICK_PIFA_SINGLE_ELEMENT_metrics.json`
