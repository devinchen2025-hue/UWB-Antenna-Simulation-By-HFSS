# D44 真实馈电 L 端口匹配小扫报告

## 目标

- 基线：候选 61 真实板边馈电单极子，覆盖口径 RealizedGainTotal 最差值已达到 -0.58 dBi，但 L 端口最差 S11 仅约 -4.14 dB。
- 本轮只做 s-parameter-only 小扫，目标是把 `P1L..P4L` 与选通 A/B 路径的最差回波推向 `-10.0 dB`。
- 新增结构：每个 L 端口馈点附近可选短 shunt stub，并可在 stub 端加入无损并联 C/L 作为一阶匹配网络模型。

## 排名

| 排名 | 候选 | 最差总回波 | 最差 L 端口回波 | 最差项 | 达标 |
| ---: | --- | ---: | ---: | --- | --- |
| 1 | `stub1p2_c0p12` | -5.77 dB | -5.77 dB | `dB(S(P3L:1,P3L:1))` / `B_ON_absorptive_50ohm_c0p08pf` | 否 |
| 2 | `stub1p6_open` | -5.44 dB | -5.44 dB | `dB(S(P4L:1,P4L:1))` / `B_ON_absorptive_50ohm_c0p08pf` | 否 |
| 3 | `top2p4_stub0p8_c0p12` | -4.66 dB | -4.66 dB | `dB(S(P1L:1,P1L:1))` / `B_ON_absorptive_50ohm_c0p08pf` | 否 |
| 4 | `stub0p8_c0p08` | -4.17 dB | -4.17 dB | `dB(S(P2L:1,P2L:1))` / `B_ON_absorptive_50ohm_c0p08pf` | 否 |
| 5 | `stub0p8_c0p16` | -4.17 dB | -4.17 dB | `dB(S(P2L:1,P2L:1))` / `B_ON_absorptive_50ohm_c0p08pf` | 否 |
| 6 | `c61_fedmono_h4p8_g0p80_w0p24` | -4.14 dB | -4.14 dB | `dB(S(P2L:1,P2L:1))` / `B_ON_absorptive_50ohm_c0p08pf` | 否 |
| 7 | `stub0p8_open` | -4.03 dB | -4.03 dB | `dB(S(P4L:1,P4L:1))` / `B_ON_absorptive_50ohm_c0p08pf` | 否 |
| 8 | `stub0p8_l1p0` | -1.95 dB | -1.95 dB | `dB(S(P3L:1,P3L:1))` / `A_ON_absorptive_50ohm_c0p08pf` | 否 |
| 9 | `stub0p8_l0p6` | -1.61 dB | -1.61 dB | `dB(S(P3L:1,P3L:1))` / `A_ON_absorptive_50ohm_c0p08pf` | 否 |

## 当前结论

- 本轮最佳候选：`stub1p2_c0p12`，最差总回波 `-5.77 dB`，最差 L 端口回波 `-5.77 dB`。
- 匹配目标仍未达成；如果无损 shunt C/L 方向不能改善，下一轮应改为串联 feed neck/微带 L-match，或通过端口位置/单极子电长度重构输入阻抗。

## 输出文件

- 汇总 CSV：`D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_dualpol_truefed_l_match_opt\UWB_CH9_D44_DUALPOL_TRUEFED_L_MATCH_summary.csv`
- 指标 JSON：`D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_dualpol_truefed_l_match_opt\UWB_CH9_D44_DUALPOL_TRUEFED_L_MATCH_metrics.json`
- 最佳 `A_ON_absorptive_50ohm_c0p08pf` AEDT 快照：`D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_dualpol_truefed_l_match_opt\UWB_CH9_D44_DUALPOL_TRUEFED_L_MATCH_06_stub1p2_c0p12_A_ON_absorptive_50ohm_c0p08pf.aedt`
- 最佳 `B_ON_absorptive_50ohm_c0p08pf` AEDT 快照：`D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_dualpol_truefed_l_match_opt\UWB_CH9_D44_DUALPOL_TRUEFED_L_MATCH_06_stub1p2_c0p12_B_ON_absorptive_50ohm_c0p08pf.aedt`
