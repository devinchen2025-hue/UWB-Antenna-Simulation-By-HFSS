# D44 电-磁双模式单阵元验证报告

## 目标与结构

- 目标：把双极化测角从现有 A/B/L 混合源转向同相位中心的物理正交双模式单元。
- A 端口：水平环，近似 z 向磁偶极，目标局部极化为 `H = Ephi`。
- B 端口：厚板短路 PIFA 或中心顶加载单极子，近似 z 向电偶极，目标局部极化为 `V = -Etheta`。
- 单源门限：S11 `<= -10.0 dB`，最佳连续 `270 deg` 低仰角窗口 GainTotal `>= -5.0 dBi`，局部 XPD min `>= 25.0 dB`。

## 当前最佳源

- 候选：`me_sym_h5p5_cap3p8_loop8p8_air1p4` / `P1B`，目标极化 `V`。
- S11：`-0.752 dB`。
- 最佳窗口：Phi `135..45 deg`。
- GainTotal min：`-35.956 dBi`。
- XPD：min `1.918 dB`，P5 `25.901 dB`。
- 综合结论：`未达标`。

## 源级结果

| 候选 | 源 | 目标极化 | S11 | Gain min | XPD min | XPD P5 | 结论 |
| --- | --- | --- | ---: | ---: | ---: | ---: | --- |
| `me_h3p5_loop10p4_gap0p55` | `P1A` | `H` | -0.704 | -18.425 | -52.381 | -17.273 | 未达标 |
| `me_h3p5_loop10p4_gap0p55` | `P1B` | `V` | -10.240 | -12.696 | -29.317 | 4.547 | 未达标 |
| `me_h3p5_loop12p0_gap0p55` | `P1A` | `H` | -0.332 | -22.090 | -40.832 | -12.260 | 未达标 |
| `me_h3p5_loop12p0_gap0p55` | `P1B` | `V` | -10.319 | -13.218 | -27.984 | 4.694 | 未达标 |
| `me_h4p0_loop10p8_gap0p55` | `P1A` | `H` | -0.850 | -17.999 | -45.635 | -15.383 | 未达标 |
| `me_h4p0_loop10p8_gap0p55` | `P1B` | `V` | -8.601 | -13.550 | -30.580 | 4.508 | 未达标 |
| `me_sym_h5p5_cap3p8_loop8p8_air1p4` | `P1A` | `H` | -1.207 | -19.775 | -33.017 | -18.137 | 未达标 |
| `me_sym_h5p5_cap3p8_loop8p8_air1p4` | `P1B` | `V` | -0.752 | -35.956 | 1.918 | 25.901 | 未达标 |
| `me_sym_h6p5_cap4p2_loop9p4_air1p0` | `P1A` | `H` | -2.421 | -19.571 | -32.087 | -16.807 | 未达标 |
| `me_sym_h6p5_cap4p2_loop9p4_air1p0` | `P1B` | `V` | -0.720 | -30.689 | -28.236 | 20.464 | 未达标 |
| `cross_pifa_h3p5_l8p8_w8p0_feed8p40` | `P1A` | `H` | -0.004 | -19.635 | -12.660 | -9.250 | 未达标 |
| `cross_pifa_h3p5_l8p8_w8p0_feed8p40` | `P1B` | `V` | -0.004 | -11.527 | -22.418 | -7.364 | 未达标 |
| `cross_pifa_h4p0_l8p8_w8p0_feed8p40` | `P1A` | `H` | -0.007 | -10.492 | -17.945 | -6.079 | 未达标 |
| `cross_pifa_h4p0_l8p8_w8p0_feed8p40` | `P1B` | `V` | -0.007 | -9.386 | -32.929 | -7.905 | 未达标 |
| `cross_pifa_h3p5_l9p2_w8p4_feed8p80` | `P1A` | `H` | -0.004 | -18.541 | -13.668 | -10.989 | 未达标 |
| `cross_pifa_h3p5_l9p2_w8p4_feed8p80` | `P1B` | `V` | -0.004 | -11.496 | -21.665 | -4.739 | 未达标 |
| `offset_pifa_h3p5_l8p8_sep9p0_feed8p40` | `P1A` | `H` | -12.822 | -16.050 | -10.663 | -7.360 | 未达标 |
| `offset_pifa_h3p5_l8p8_sep9p0_feed8p40` | `P1B` | `V` | -15.645 | -13.164 | -24.068 | -4.050 | 未达标 |
| `offset_pifa_h3p5_l8p8_sep10p0_feed8p40` | `P1A` | `H` | -16.936 | -11.170 | -16.502 | -12.181 | 未达标 |
| `offset_pifa_h3p5_l8p8_sep10p0_feed8p40` | `P1B` | `V` | -13.112 | -10.086 | -22.251 | -4.940 | 未达标 |
| `offset_pifa_h4p0_l8p8_sep10p0_feed8p40` | `P1A` | `H` | -4.282 | -9.964 | -33.541 | -16.226 | 未达标 |
| `offset_pifa_h4p0_l8p8_sep10p0_feed8p40` | `P1B` | `V` | -5.142 | -8.990 | -18.634 | -3.988 | 未达标 |
| `offset_pifa_h3p5_l8p8_sep12p0_feed8p40` | `P1A` | `H` | -9.259 | -8.167 | -34.152 | -21.011 | 未达标 |
| `offset_pifa_h3p5_l8p8_sep12p0_feed8p40` | `P1B` | `V` | -9.541 | -10.590 | -21.069 | -6.700 | 未达标 |
| `offset_pifa_h4p0_l8p8_sep12p0_feed8p40` | `P1A` | `H` | -4.276 | -14.377 | -28.496 | -15.463 | 未达标 |
| `offset_pifa_h4p0_l8p8_sep12p0_feed8p40` | `P1B` | `V` | -4.836 | -8.418 | -21.206 | -5.330 | 未达标 |
| `offset_pifa_h3p5_l8p8_sep14p0_feed8p40` | `P1A` | `H` | -8.540 | -10.815 | -37.295 | -21.800 | 未达标 |
| `offset_pifa_h3p5_l8p8_sep14p0_feed8p40` | `P1B` | `V` | -8.649 | -9.743 | -22.384 | -6.864 | 未达标 |
| `offset_pifa_h5p8_l8p6_sep10p0_feed7p80` | `P1A` | `H` | -4.148 | -18.983 | -15.347 | -8.813 | 未达标 |
| `offset_pifa_h5p8_l8p6_sep10p0_feed7p80` | `P1B` | `V` | -2.762 | -6.710 | -28.292 | -8.558 | 未达标 |
| `offset_pifa_h6p5_l8p4_sep10p0_feed7p90` | `P1A` | `H` | -4.105 | -16.196 | -15.453 | -10.639 | 未达标 |
| `offset_pifa_h6p5_l8p4_sep10p0_feed7p90` | `P1B` | `V` | -2.945 | -7.403 | -30.397 | -8.068 | 未达标 |
| `offset_pifa_h6p5_l8p4_sep12p0_feed7p90` | `P1A` | `H` | -3.791 | -14.939 | -23.987 | -11.426 | 未达标 |
| `offset_pifa_h6p5_l8p4_sep12p0_feed7p90` | `P1B` | `V` | -2.500 | -8.355 | -30.735 | -9.554 | 未达标 |
| `mirror_pifa_h3p5_l8p8_sep17p0_feed8p40` | `P1A` | `H` | -8.396 | -7.489 | -33.000 | -15.516 | 未达标 |
| `mirror_pifa_h3p5_l8p8_sep17p0_feed8p40` | `P1B` | `V` | -8.259 | -7.034 | -50.799 | -7.235 | 未达标 |
| `mirror_pifa_h3p5_l8p8_sep19p0_feed8p40` | `P1A` | `H` | -9.123 | -6.945 | -42.499 | -14.361 | 未达标 |
| `mirror_pifa_h3p5_l8p8_sep19p0_feed8p40` | `P1B` | `V` | -9.543 | -7.066 | -50.683 | -7.438 | 未达标 |
| `parallel_pifa_h3p5_l8p8_sep17p0_feed8p40` | `P1A` | `H` | -8.213 | -8.400 | -18.770 | -10.680 | 未达标 |
| `parallel_pifa_h3p5_l8p8_sep17p0_feed8p40` | `P1B` | `V` | -10.503 | -7.278 | -37.416 | -6.586 | 未达标 |
| `mirror_pifa_h4p0_l8p8_sep17p0_feed8p40` | `P1A` | `H` | -4.894 | -7.969 | -22.013 | -10.506 | 未达标 |
| `mirror_pifa_h4p0_l8p8_sep17p0_feed8p40` | `P1B` | `V` | -4.995 | -7.769 | -38.970 | -6.914 | 未达标 |
| `parallel_pifa_h5p8_l8p6_sep17p0_feed7p80` | `P1A` | `H` | -3.677 | -8.204 | -9.407 | -7.119 | 未达标 |
| `parallel_pifa_h5p8_l8p6_sep17p0_feed7p80` | `P1B` | `V` | -2.413 | -13.241 | -37.884 | -13.493 | 未达标 |
| `parallel_pifa_h6p5_l8p4_sep17p0_feed7p90` | `P1A` | `H` | -3.078 | -9.682 | -11.083 | -9.607 | 未达标 |
| `parallel_pifa_h6p5_l8p4_sep17p0_feed7p90` | `P1B` | `V` | -2.086 | -12.649 | -27.451 | -13.713 | 未达标 |
| `mirror_pifa_h5p8_l8p6_sep17p0_feed7p80` | `P1A` | `H` | -2.429 | -10.787 | -22.721 | -8.249 | 未达标 |
| `mirror_pifa_h5p8_l8p6_sep17p0_feed7p80` | `P1B` | `V` | -2.407 | -10.915 | -31.756 | -9.886 | 未达标 |
| `mirror_pifa_h6p5_l8p4_sep17p0_feed7p90` | `P1A` | `H` | -1.949 | -11.741 | -23.234 | -5.539 | 未达标 |
| `mirror_pifa_h6p5_l8p4_sep17p0_feed7p90` | `P1B` | `V` | -1.988 | -11.128 | -34.779 | -12.209 | 未达标 |

## 工程判断

- 这是结构级验证，不再依赖 A/B/L 现有贴片源的线性组合。
- 若 A 环或 B 电偶极任一源未达标，下一步优先分别调环周长/间隙/高度，以及 B 通道馈点/顶加载/短路结构，再扩展到四阵元并计算完整 2x2 条件数和 PDOA。

## 输出文件

- 汇总 CSV：`D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_me_dualpol_single_element\UWB_CH9_D44_ME_DUALPOL_SINGLE_ELEMENT_summary.csv`
- 窗口 CSV：`D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_me_dualpol_single_element\UWB_CH9_D44_ME_DUALPOL_SINGLE_ELEMENT_window_summary.csv`
- 指标 JSON：`D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_me_dualpol_single_element\UWB_CH9_D44_ME_DUALPOL_SINGLE_ELEMENT_metrics.json`
