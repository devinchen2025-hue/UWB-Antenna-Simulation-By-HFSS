# D44 双极化测角评估指标报告

## 指标定义

- 局部极化基准：`H = Ephi`，`V = -Etheta`，即水平切向与板法向/世界垂直投影后的局部正交基。
- 响应矩阵：每个阵元、每个方向构建 `[[A_H, A_V], [B_H, B_V]]`。
- XPD 目标：A/B 按某一 H/V 分配后，端口共极化/交叉极化比值最小值建议 `>= 25.0 dB`。
- 极化正交目标：A/B 复矢量相关系数换算的正交度建议 `>= 20.0 dB`。
- 矩阵条件数目标：2x2 极化响应矩阵条件数建议 `<= 6.0 dB`。
- 测角相位目标：H/V 同基线 PDOA 去除中值偏置后的 P95 残差建议 `<= 10.0 deg`。

## 当前最佳分配

- 评估窗口：`best270`，Phi `135..45 deg`，宽度 `270 deg`。
- 端口分配：`A_H__B_V`。
- 成对最小 XPD：min `-35.081 dB`，P5 `-10.177 dB`，median `-2.300 dB`。
- A/B 极化正交度：min `0.002 dB`，P5 `0.510 dB`，median `3.649 dB`。
- 2x2 条件数：P95 `15.433 dB`，max `39.681 dB`。
- 共极化相对幅度覆盖：min `-47.255 dB`，P5 `-16.331 dB`，`>-35 dB` 样本占比 `99.9%`。
- GainTotal 覆盖：min `-23.911 dBi`，P5 `-17.066 dBi`，目标 `>= -5.0 dBi`。
- RealizedGainTotal 覆盖：min `-24.121 dBi`，P5 `-17.260 dBi`。
- H/V PDOA 去偏置后残差：P95 avg `86.159 deg`，P95 max `151.259 deg`。
- 等效方位误差：P95 avg `53.954 deg`，P95 max `110.130 deg`。

## S 参数复核引用

- A/B 当前工作态 S11：`达标`；最差 active S11 `-15.125 dB`。
- A/B 同极化阵元间耦合最差值：`-44.946 dB`。
- 说明：这里引用已有中心频点 native S 参数摘要；完整频带 S11/S21 仍需按最终几何重新扫频确认。

## 全部分配摘要

| 范围 | 分配 | Phi窗口 | Pair XPD min | Pair XPD P5 | 正交度 P5 | 条件数 P95 | 共极化P5 | XPD达标 | 条件数达标 |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- | --- |
| `best270` | `A_H__B_V` | 135..45 | -35.081 | -10.177 | 0.510 | 15.433 | -16.331 | 否 | 否 |
| `best270` | `A_V__B_H` | 135..45 | -39.340 | -15.032 | 0.510 | 15.433 | -18.808 | 否 | 否 |
| `full360` | `A_H__B_V` | 0..0 | -35.081 | -13.773 | 0.285 | 18.123 | -18.202 | 否 | 否 |
| `full360` | `A_V__B_H` | 0..0 | -39.677 | -15.457 | 0.285 | 18.123 | -20.322 | 否 | 否 |

## 增益覆盖摘要

| 范围 | 分配 | GainTotal min | Realized min | 最差 Realized 点 | 增益达标 |
| --- | --- | ---: | ---: | --- | --- |
| `best270` | `A_H__B_V` | -23.911 dBi | -24.121 dBi | `P3A` / Theta 90 / Phi 265 | 否 |
| `best270` | `A_V__B_H` | -23.911 dBi | -24.121 dBi | `P3A` / Theta 90 / Phi 265 | 否 |
| `full360` | `A_H__B_V` | -26.591 dBi | -26.915 dBi | `P4A` / Theta 70 / Phi 105 | 否 |
| `full360` | `A_V__B_H` | -26.591 dBi | -26.915 dBi | `P4A` / Theta 70 / Phi 105 | 否 |

## 工程结论

- 该指标框架已把双极化测角拆成端口极化分离、2x2 极化矩阵可逆性、H/V PDOA 一致性、相对覆盖幅度和 S 参数五类指标。
- 当前数据若 XPD/条件数未达标，说明问题不是单纯的 `Etheta/Ephi` 坐标口径，而是 A/B 两端口在局部 H/V 基准下仍存在明显混合或矩阵病态。
- 后续优化应优先让每个阵元的 A/B 两个端口形成同相位中心、低相关、低条件数的局部 H/V 响应矩阵，再把 GainTotal 与完整频带 S11/S21 并入最终门限。

## 输出文件

- 矩阵样本 CSV：`D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_dualpol_angle_metrics\UWB_CH9_D44_DUALPOL_ANGLE_METRICS_matrix_samples.csv`
- 矩阵摘要 CSV：`D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_dualpol_angle_metrics\UWB_CH9_D44_DUALPOL_ANGLE_METRICS_matrix_summary.csv`
- PDOA 曲线 CSV：`D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_dualpol_angle_metrics\UWB_CH9_D44_DUALPOL_ANGLE_METRICS_pdoa_phase_curves.csv`
- PDOA 摘要 CSV：`D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_dualpol_angle_metrics\UWB_CH9_D44_DUALPOL_ANGLE_METRICS_pdoa_phase_summary.csv`
- S 参数摘要 CSV：`D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_dualpol_angle_metrics\UWB_CH9_D44_DUALPOL_ANGLE_METRICS_sparam_summary.csv`
- 增益覆盖摘要 CSV：`D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_dualpol_angle_metrics\UWB_CH9_D44_DUALPOL_ANGLE_METRICS_gain_summary.csv`
- 指标 JSON：`D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_dualpol_angle_metrics\UWB_CH9_D44_DUALPOL_ANGLE_METRICS_metrics.json`
- H/V PDOA 对比图：`D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_dualpol_angle_metrics\plots\UWB_CH9_D44_DUALPOL_ANGLE_METRICS_A_H__B_V_best270_theta90_pdoa_hv.png`
