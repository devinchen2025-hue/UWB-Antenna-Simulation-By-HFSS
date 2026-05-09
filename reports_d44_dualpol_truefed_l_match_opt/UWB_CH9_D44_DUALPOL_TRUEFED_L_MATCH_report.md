# D44 真实馈电 L 端口匹配小扫报告

## 目标

- 基线：候选 61 真实板边馈电单极子，覆盖口径 RealizedGainTotal 最差值已达到 -0.58 dBi，但 L 端口最差 S11 仅约 -4.14 dB。
- 本轮继续做 s-parameter-only 小扫，目标是把 `P1L..P4L` 与选通 A/B 路径的最差回波推到 `-10.0 dB` 或更低。
- 新增结构：L 端口可使用串联 feed neck 移动真实馈点，并可与短 shunt stub/无损并联 C-L 一起扫；后续候选也加入真实板边 IFA 馈电抽头。

## 排名

| 排名 | 候选 | 最差总回波 | 最差 L 端口回波 | 最差项 | 达标 |
| ---: | --- | ---: | ---: | --- | --- |
| 1 | `neck1p6_w0p08_stub2p6_open` | -8.70 dB | -8.70 dB | `dB(S(P2L:1,P2L:1))` / `A_ON_absorptive_50ohm_c0p08pf` | 否 |
| 2 | `neck1p2_w0p08_stub3p0_open` | -8.20 dB | -8.20 dB | `dB(S(P3L:1,P3L:1))` / `B_ON_absorptive_50ohm_c0p08pf` | 否 |
| 3 | `neck1p6_w0p08_stub2p4_c0p02` | -7.92 dB | -7.92 dB | `dB(S(P2L:1,P2L:1))` / `A_ON_absorptive_50ohm_c0p08pf` | 否 |
| 4 | `neck1p6_w0p08_stub2p6_c0p02` | -7.81 dB | -7.81 dB | `dB(S(P3L:1,P3L:1))` / `B_ON_absorptive_50ohm_c0p08pf` | 否 |
| 5 | `neck1p6_w0p08_stub1p6_c0p04` | -7.38 dB | -7.38 dB | `dB(S(P3L:1,P3L:1))` / `A_ON_absorptive_50ohm_c0p08pf` | 否 |
| 6 | `neck1p6_w0p08_stub2p4_open` | -7.31 dB | -7.31 dB | `dB(S(P4L:1,P4L:1))` / `B_ON_absorptive_50ohm_c0p08pf` | 否 |
| 7 | `mono_w0p40_g0p50_neck1p6_stub2p4` | -7.21 dB | -7.21 dB | `dB(S(P4L:1,P4L:1))` / `B_ON_absorptive_50ohm_c0p08pf` | 否 |
| 8 | `neck2p0_w0p08_stub1p6_open` | -6.24 dB | -6.24 dB | `dB(S(P4L:1,P4L:1))` / `A_ON_absorptive_50ohm_c0p08pf` | 否 |
| 9 | `neck1p6_w0p06_stub1p6_open` | -6.14 dB | -6.14 dB | `dB(S(P1L:1,P1L:1))` / `B_ON_absorptive_50ohm_c0p08pf` | 否 |
| 10 | `neck1p6_w0p08_stub1p6_open` | -6.02 dB | -6.02 dB | `dB(S(P2L:1,P2L:1))` / `B_ON_absorptive_50ohm_c0p08pf` | 否 |
| 11 | `neck1p6_w0p08_stub2p0_open` | -5.84 dB | -5.84 dB | `dB(S(P3L:1,P3L:1))` / `A_ON_absorptive_50ohm_c0p08pf` | 否 |
| 12 | `stub1p2_c0p12` | -5.77 dB | -5.77 dB | `dB(S(P3L:1,P3L:1))` / `B_ON_absorptive_50ohm_c0p08pf` | 否 |
| 13 | `neck2p2_w0p06_stub1p8_open` | -5.56 dB | -5.56 dB | `dB(S(P2L:1,P2L:1))` / `B_ON_absorptive_50ohm_c0p08pf` | 否 |
| 14 | `stub1p6_open` | -5.44 dB | -5.44 dB | `dB(S(P4L:1,P4L:1))` / `B_ON_absorptive_50ohm_c0p08pf` | 否 |
| 15 | `neck1p2_w0p10_stub1p2_c0p12` | -5.28 dB | -5.28 dB | `dB(S(P4L:1,P4L:1))` / `B_ON_absorptive_50ohm_c0p08pf` | 否 |
| 16 | `mono_w0p60_g0p35_neck1p4_stub2p6` | -5.21 dB | -5.21 dB | `dB(S(P3L:1,P3L:1))` / `A_ON_absorptive_50ohm_c0p08pf` | 否 |
| 17 | `neck1p2_neg_w0p10_stub1p2_c0p12` | -5.04 dB | -5.04 dB | `dB(S(P2L:1,P2L:1))` / `B_ON_absorptive_50ohm_c0p08pf` | 否 |
| 18 | `neck1p8_w0p08` | -4.67 dB | -4.67 dB | `dB(S(P2L:1,P2L:1))` / `B_ON_absorptive_50ohm_c0p08pf` | 否 |
| 19 | `top2p4_stub0p8_c0p12` | -4.66 dB | -4.66 dB | `dB(S(P1L:1,P1L:1))` / `B_ON_absorptive_50ohm_c0p08pf` | 否 |
| 20 | `neck1p4_w0p12` | -4.57 dB | -4.57 dB | `dB(S(P2L:1,P2L:1))` / `B_ON_absorptive_50ohm_c0p08pf` | 否 |
| 21 | `neck1p0_w0p08` | -4.36 dB | -4.36 dB | `dB(S(P2L:1,P2L:1))` / `A_ON_absorptive_50ohm_c0p08pf` | 否 |
| 22 | `stub0p8_c0p08` | -4.17 dB | -4.17 dB | `dB(S(P2L:1,P2L:1))` / `B_ON_absorptive_50ohm_c0p08pf` | 否 |
| 23 | `stub0p8_c0p16` | -4.17 dB | -4.17 dB | `dB(S(P2L:1,P2L:1))` / `B_ON_absorptive_50ohm_c0p08pf` | 否 |
| 24 | `c61_fedmono_h4p8_g0p80_w0p24` | -4.14 dB | -4.14 dB | `dB(S(P2L:1,P2L:1))` / `B_ON_absorptive_50ohm_c0p08pf` | 否 |
| 25 | `neck1p0_w0p12` | -4.06 dB | -4.06 dB | `dB(S(P2L:1,P2L:1))` / `B_ON_absorptive_50ohm_c0p08pf` | 否 |
| 26 | `stub0p8_open` | -4.03 dB | -4.03 dB | `dB(S(P4L:1,P4L:1))` / `B_ON_absorptive_50ohm_c0p08pf` | 否 |
| 27 | `neck0p6_w0p12` | -3.76 dB | -3.76 dB | `dB(S(P1L:1,P1L:1))` / `B_ON_absorptive_50ohm_c0p08pf` | 否 |
| 28 | `fedifa_l3p8_h5p2_f1p60` | -2.86 dB | -2.86 dB | `dB(S(P3L:1,P3L:1))` / `B_ON_absorptive_50ohm_c0p08pf` | 否 |
| 29 | `fedifa_l3p8_h5p2_f1p20` | -2.31 dB | -2.31 dB | `dB(S(P3L:1,P3L:1))` / `A_ON_absorptive_50ohm_c0p08pf` | 否 |
| 30 | `fedifa_l3p8_h5p2_f1p20_stub1p6_open` | -2.27 dB | -2.27 dB | `dB(S(P3L:1,P3L:1))` / `B_ON_absorptive_50ohm_c0p08pf` | 否 |
| 31 | `stub0p8_l1p0` | -1.95 dB | -1.95 dB | `dB(S(P3L:1,P3L:1))` / `A_ON_absorptive_50ohm_c0p08pf` | 否 |
| 32 | `stub0p8_l0p6` | -1.61 dB | -1.61 dB | `dB(S(P3L:1,P3L:1))` / `A_ON_absorptive_50ohm_c0p08pf` | 否 |
| 33 | `c64_fedifa_l3p8_h5p2_g0p60_f0p70_w0p24` | -1.50 dB | -1.50 dB | `dB(S(P2L:1,P2L:1))` / `B_ON_absorptive_50ohm_c0p08pf` | 否 |
| 34 | `c65_fedifa_l3p2_h6p8_g0p60_f0p65_w0p20_lim10` | -0.90 dB | -0.90 dB | `dB(S(P3L:1,P3L:1))` / `A_ON_absorptive_50ohm_c0p08pf` | 否 |

## 当前结论

- 本轮最佳候选：`neck1p6_w0p08_stub2p6_open`，最差总回波 `-8.70 dB`，最差 L 端口回波 `-8.70 dB`。
- 匹配目标仍未达成；当前有效方向是 `1.6 mm` 串联 feed neck 加接近板边 span 上限的长 open stub，集中小电容和 IFA 抽头均未继续改善。
- 下一轮若继续追 -10 dB，应放宽或折叠边缘支路电长度，或引入真实多节微带/LC 匹配；单纯加宽单极子、移动 IFA 抽头不是优先方向。

## 验证

- 已完成 s-parameter-only 两工作态小扫；每个纳入排名的候选均包含 `A_ON_absorptive_50ohm_c0p08pf` 与 `B_ON_absorptive_50ohm_c0p08pf`。
- 已运行 Python 编译与候选参数约束检查；本报告只统计完整两态候选。
- 因 S11 目标尚未达成，本轮未回跑完整 FOV 远场；覆盖增益仍以候选 61 的已验证结果作为参考基线。

## 输出文件

- 汇总 CSV：`D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_dualpol_truefed_l_match_opt\UWB_CH9_D44_DUALPOL_TRUEFED_L_MATCH_summary.csv`
- 指标 JSON：`D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_dualpol_truefed_l_match_opt\UWB_CH9_D44_DUALPOL_TRUEFED_L_MATCH_metrics.json`
- 报告 Markdown：`D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_dualpol_truefed_l_match_opt\UWB_CH9_D44_DUALPOL_TRUEFED_L_MATCH_report.md`
- 根目录 AEDT 工程：`D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\UWB_CH9_Diamond_CP_Array_D44_DUALPOL_XY.aedt`
- 根目录参数 JSON：`D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\UWB_CH9_Diamond_CP_Array_D44_DUALPOL_XY_params.json`
