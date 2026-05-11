# D44 厚板短路 PIFA/腔体化单阵元验证报告

## 目标与口径

- 验证对象：去除 A/B/L 后的单端口厚板短路 PIFA/准腔体阵元，单阵元相位中心放在阵元中心参考点。
- 匹配目标：`S11 <= -10.0 dB`。
- 增益目标：Theta `45..90 deg`，在最佳连续 `270 deg` 方位窗口内 `GainTotal >= -5.0 dBi`。
- 说明：本阶段只做单阵元可行性验证，不评估 4 阵元互耦、PDOA 单调性或整机遮挡。

## 最佳候选

- 选择口径：若没有候选同时满足 S11 和增益，则在增益达标候选中优先选择 S11 最接近目标的候选。
- 候选序号：`36`。
- 候选：`h3p5_l8p8_w8p0_sw4p0_fence6p0_feed8p40`。
- S11 最差值：`-10.970 dB`。
- 最佳 270° 窗口：Phi `0..270 deg`。
- 最佳 270° 窗口最小 GainTotal：`-3.326 dBi`，最差点 Theta `90 deg` / Phi `90 deg`。
- 全 360° 方位最小 GainTotal：`-3.326 dBi`。

## 达标情况

- S11：`达标`。
- 270° 方位增益：`达标`。
- 综合结论：`达标`。

## 复核结论

- 已完成候选数：`43` 个，所有候选在 Theta `45..90 deg`、最佳连续 `270 deg` 方位窗口内均满足 `GainTotal >= -5.0 dBi`。
- S11 最优候选：`#36 h3p5_l8p8_w8p0_sw4p0_fence6p0_feed8p40`，S11 `-10.970 dB`，已优于 `-10 dB` 目标约 `0.97 dB`。
- 增益最优候选：`#25 h6p5_l8p4_w8p0_feed7p90`，最佳 270° 窗口最小 GainTotal `-0.691 dBi`，但 S11 `-2.387 dB`。
- 本轮有效路径是保持靠近开路端的真实几何馈电，同时把厚板高度从 `5.0 mm` 收敛到 `3.5 mm` 并保留 `4.0 mm` 短路墙、`6.0 mm` 侧墙；S11 从上一轮最佳 `-4.786 dB` 推进到 `-10.970 dB`。
- 外接匹配岛候选 11..16 已修正为 AEDT `Serial` 串联 RLC 写法，但 S11 对 L/C 数值不敏感，当前 lumped matching 拓扑不能作为达标签核依据。
- 最佳候选复阻抗诊断：`D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_thick_pifa_single_element\h3p5_l8p8_w8p0_sw4p0_fence6p0_feed8p40_complex_native_s_parameters.csv`；8 GHz 端口约为 `89.429 + j0.296 ohm`。

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
| 26 | `h5p0_l8p8_w8p0_sw4p0_fence6p0_feed7p80` | -3.779 | -2.110 | -2.110 | 未达标 |
| 27 | `h5p0_l8p8_w8p0_sw4p0_fence6p0_feed8p00` | -4.175 | -1.944 | -1.944 | 未达标 |
| 28 | `h5p0_l8p8_w8p0_sw4p0_fence6p0_feed8p20` | -4.380 | -2.228 | -2.228 | 未达标 |
| 29 | `h5p0_l8p8_w8p0_sw4p0_fence6p0_feed8p48` | -4.774 | -1.902 | -1.902 | 未达标 |
| 30 | `h5p0_l9p2_w8p4_sw4p0_fence6p0_feed8p80` | -4.800 | -2.206 | -2.206 | 未达标 |
| 31 | `h5p0_l8p8_w10p0_sw4p0_fence6p0_feed8p40` | -5.037 | -2.552 | -2.552 | 未达标 |
| 32 | `h4p5_l8p8_w8p0_sw4p0_fence6p0_feed8p40` | -6.299 | -2.592 | -2.592 | 未达标 |
| 33 | `h5p0_l8p8_w8p0_sw5p5_fence7p0_feed8p20` | -3.440 | -2.366 | -2.366 | 未达标 |
| 34 | `h5p0_l8p8_w8p0_sw4p0_fence6p0_feed8p40_lip1p0` | -5.088 | -2.368 | -2.368 | 未达标 |
| 35 | `h4p0_l8p8_w8p0_sw4p0_fence6p0_feed8p40` | -8.538 | -2.828 | -2.828 | 未达标 |
| 36 | `h3p5_l8p8_w8p0_sw4p0_fence6p0_feed8p40` | -10.970 | -3.326 | -3.326 | 达标 |
| 37 | `h4p5_l8p8_w8p0_sw4p0_fence6p0_feed8p00` | -5.449 | -2.396 | -2.396 | 未达标 |
| 38 | `h4p5_l8p8_w8p0_sw4p0_fence6p0_feed8p20` | -5.818 | -2.521 | -2.521 | 未达标 |
| 39 | `h4p5_l8p8_w8p0_sw4p0_fence6p0_feed8p48` | -6.234 | -2.541 | -2.541 | 未达标 |
| 40 | `h4p0_l8p8_w8p0_sw4p0_fence6p0_feed8p20` | -8.079 | -2.898 | -2.898 | 未达标 |
| 41 | `h4p0_l8p8_w10p0_sw4p0_fence6p0_feed8p40` | -8.560 | -3.144 | -3.144 | 未达标 |
| 42 | `h4p5_l8p8_w8p0_sw5p5_fence7p0_feed8p20` | -3.866 | -2.837 | -2.837 | 未达标 |
| 43 | `h4p5_l9p2_w8p4_sw4p0_fence6p0_feed8p80` | -6.351 | -2.369 | -2.369 | 未达标 |

## 工程判断

- 该方案避免了独立 4.8 mm L 单极子金属臂，制造上可转化为厚 PCB 顶层铜箔、短路 via wall/边镀墙和局部开口腔体。
- 单阵元口径下，S11 和低仰角 270° 覆盖增益已经同时达标；低高度强短路墙 PIFA 是当前可继续推进的结构方向。
- 下一步应把该单阵元扩展到 4 阵元，保持约 17 mm 相位中心间距并复核互耦、相位单调性、PDOA 模糊和人体/外壳遮挡。
- 量产结构上仍建议优先使用 via wall/边镀墙和清晰 50 ohm 馈电过渡，避免回退到 A/B 贴片低仰角硬覆盖。

## 输出文件

- 最佳 AEDT 工程：`D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\UWB_CH9_D44_THICK_PIFA_SINGLE_ELEMENT_h3p5_l8p8_w8p0_sw4p0_fence6p0_feed8p40.aedt`
- 候选汇总 CSV：`D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_thick_pifa_single_element\UWB_CH9_D44_THICK_PIFA_SINGLE_ELEMENT_summary.csv`
- 方位窗口 CSV：`D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_thick_pifa_single_element\UWB_CH9_D44_THICK_PIFA_SINGLE_ELEMENT_azimuth_window_summary.csv`
- 指标 JSON：`D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_thick_pifa_single_element\UWB_CH9_D44_THICK_PIFA_SINGLE_ELEMENT_metrics.json`
