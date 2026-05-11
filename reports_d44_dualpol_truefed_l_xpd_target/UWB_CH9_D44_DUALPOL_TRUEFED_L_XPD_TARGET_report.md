# D44 true-fed L 交叉极化抑制比目标评估

## 目标

- XPD 目标：Theta `45..90 deg`，`0 deg/Etheta` 为主极化、`90 deg/Ephi` 为交叉极化，最小 XPD `>= 25.0 dB`。
- 候选编号：`[37]`；源组：`l`。

## 最优汇总

- 当前排序首项：candidate `37` / `fold0p6_neck1p6_stub2p6` / `ALL_CASES`。
- 最小 XPD：`-33.424 dB`，距离目标 `-58.424 dB`。
- 结论：`未达标`。

## 结果表

| 候选 | 源组 | 范围 | 源 | 样本数 | 最小XPD | P5 XPD | 中位XPD | 平均XPD | 最差Theta | 最差Phi | 是否达标 |
| ---: | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 37 | `l` | `ALL_CASES` | `ALL` | 5840 | -33.424 dB | -12.014 dB | 3.050 dB | 2.787 dB | 80 deg | 195 deg | 否 |
| 37 | `l` | `A_ON_absorptive_50ohm_c0p08pf` | `P4L` | 730 | -19.036 dB | -7.580 dB | 4.968 dB | 4.760 dB | 90 deg | 5 deg | 否 |
| 37 | `l` | `B_ON_absorptive_50ohm_c0p08pf` | `P4L` | 730 | -19.036 dB | -7.580 dB | 4.968 dB | 4.760 dB | 90 deg | 5 deg | 否 |
| 37 | `l` | `A_ON_absorptive_50ohm_c0p08pf` | `P2L` | 730 | -25.700 dB | -10.198 dB | 5.011 dB | 4.967 dB | 45 deg | 235 deg | 否 |
| 37 | `l` | `B_ON_absorptive_50ohm_c0p08pf` | `P2L` | 730 | -25.700 dB | -10.198 dB | 5.011 dB | 4.967 dB | 45 deg | 235 deg | 否 |
| 37 | `l` | `B_ON_absorptive_50ohm_c0p08pf` | `P3L` | 730 | -31.383 dB | -14.682 dB | 2.370 dB | 1.590 dB | 65 deg | 155 deg | 否 |
| 37 | `l` | `A_ON_absorptive_50ohm_c0p08pf` | `P3L` | 730 | -31.383 dB | -14.682 dB | 2.370 dB | 1.590 dB | 65 deg | 155 deg | 否 |
| 37 | `l` | `A_ON_absorptive_50ohm_c0p08pf` | `P1L` | 730 | -33.424 dB | -14.677 dB | 1.519 dB | -0.171 dB | 80 deg | 195 deg | 否 |
| 37 | `l` | `B_ON_absorptive_50ohm_c0p08pf` | `P1L` | 730 | -33.424 dB | -14.677 dB | 1.519 dB | -0.171 dB | 80 deg | 195 deg | 否 |
| 37 | `l` | `A_ON_absorptive_50ohm_c0p08pf` | `ALL` | 2920 | -33.424 dB | -12.014 dB | 3.050 dB | 2.787 dB | 80 deg | 195 deg | 否 |
| 37 | `l` | `B_ON_absorptive_50ohm_c0p08pf` | `ALL` | 2920 | -33.424 dB | -12.014 dB | 3.050 dB | 2.787 dB | 80 deg | 195 deg | 否 |

## 输出文件

- CSV：`D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_dualpol_truefed_l_xpd_target\UWB_CH9_D44_DUALPOL_TRUEFED_L_XPD_TARGET_summary.csv`
- JSON：`D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_dualpol_truefed_l_xpd_target\UWB_CH9_D44_DUALPOL_TRUEFED_L_XPD_TARGET_metrics.json`
