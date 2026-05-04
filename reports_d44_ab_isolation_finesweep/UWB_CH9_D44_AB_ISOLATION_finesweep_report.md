# D44 锚点天线小焊盘与 A/B 隔离结构细扫报告

## 本轮目标

- 小焊盘趋势细扫：`feed_pad_radius = 0.28-0.36 mm`。
- 端口片细扫：`port_width = 0.45-0.60 mm`。
- 双馈偏移细扫：`feed_offset = 3.20-3.60 mm`。
- 新增结构：可调悬浮 A/B 弱耦合开路线、贴片外侧接地过孔栅栏。
- 判据：最差 `Sii <= -10.0 dB`，A/B 隔离 `>= 15.0 dB`，PDOA 平均 RMS 漂移 `<= 10.0 deg`，最大漂移 `<= 20.0 deg`。

## 建模说明

- 弱耦合开路线是每个贴片上方的悬浮窄铜条，位于 A/B 馈点之间，用于提供可调的反向电容耦合。
- 过孔栅栏位于每个贴片 A/B 馈电象限外侧，不穿过贴片，接地后用于抑制局部地电流串扰。
- 本轮先以三频点 S 参数快速筛选，再对排名靠前候选进行远场/PDOA 线极化复核；若隔离结构未进入前列，会强制保留一个隔离结构候选进入完整复核。

## S 参数筛选排名

- 本次实际筛选候选数：`21`。

| 排名 | 候选 | 评分 | 最差 Sii | 隔离度 | 焊盘 | 端口 | 馈点 | 开路线 | 过孔栅栏 |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | `pad0p32_port0p50_feed3p40` | 33.87 | -9.12 dB | 12.17 dB | 0.32 | 0.50 | 3.40 | 0 | 0 |
| 2 | `openline_l2p80_w0p10_gap0p10` | 36.18 | -8.93 dB | 12.43 dB | 0.32 | 0.50 | 3.40 | 1 | 0 |
| 3 | `pad0p30_port0p45_feed3p40` | 37.33 | -8.92 dB | 12.27 dB | 0.30 | 0.45 | 3.40 | 0 | 0 |
| 4 | `pad0p28_port0p55_feed3p30` | 37.51 | -8.86 dB | 12.45 dB | 0.28 | 0.55 | 3.30 | 0 | 0 |
| 5 | `pad0p32_port0p50_feed3p30` | 40.45 | -8.79 dB | 12.21 dB | 0.32 | 0.50 | 3.30 | 0 | 0 |
| 6 | `pad0p32_port0p60_feed3p30` | 40.89 | -8.52 dB | 13.08 dB | 0.32 | 0.60 | 3.30 | 0 | 0 |
| 7 | `pad0p28_port0p45_feed3p50` | 41.88 | -8.71 dB | 12.26 dB | 0.28 | 0.45 | 3.50 | 0 | 0 |
| 8 | `pad0p30_port0p55_feed3p30` | 42.18 | -8.49 dB | 12.95 dB | 0.30 | 0.55 | 3.30 | 0 | 0 |
| 9 | `pad0p32_port0p50_feed3p50` | 43.16 | -8.60 dB | 12.42 dB | 0.32 | 0.50 | 3.50 | 0 | 0 |
| 10 | `openline_l1p80_w0p10_gap0p08` | 43.44 | -8.44 dB | 12.92 dB | 0.32 | 0.50 | 3.30 | 1 | 0 |
| 11 | `openline_l2p40_w0p12_gap0p08` | 45.37 | -8.46 dB | 12.53 dB | 0.32 | 0.50 | 3.30 | 1 | 0 |
| 12 | `pad0p32_port0p55_feed3p30` | 45.97 | -8.55 dB | 12.12 dB | 0.32 | 0.55 | 3.30 | 0 | 0 |

## 最优完整复核候选

- 候选：`pad0p32_port0p50_feed3p40`
- 说明：使用小焊盘/窄端口组合并细扫双馈偏移。
- AEDT 工程：`D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\UWB_CH9_Diamond_CP_Array_D44_DUALFEED_CP.aedt`
- 最差 Sii：`-9.12 dB`
- A/B 端口隔离：`12.17 dB`
- 最优 B 路幅度：`1.000`
- 最优 B 路相位：`-90.0 deg`
- 平均 RMS PDOA 漂移：`45.78 deg`
- 95 分位 RMS PDOA 漂移：`78.13 deg`
- 最大 PDOA 漂移：`179.98 deg`
- FOV 最小增益：`-18.97 dBi`
- FOV 最大轴比：`4831.39 dB`
- CP 覆盖率下限：`61.8%`

## 与上一轮对比

- 上一轮最优候选：`small_pad_feed3p30`。

| 指标 | 上一轮 | 本轮 | 变化 |
| --- | ---: | ---: | ---: |
| 最差 Sii | -8.39 dB | -9.12 dB | -0.73 |
| A/B 隔离 | 12.55 dB | 12.17 dB | -0.37 |
| 平均 RMS PDOA 漂移 | 46.58 deg | 45.78 deg | -0.80 |
| 95 分位 RMS PDOA 漂移 | 79.03 deg | 78.13 deg | -0.90 |
| 最大 PDOA 漂移 | 179.89 deg | 179.98 deg | +0.09 |
| FOV 最小增益 | -18.19 dBi | -18.97 dBi | -0.79 |
| FOV 最大轴比 | 932.54 dB | 4831.39 dB | +3898.85 |

## 最优参数

- `feed_offset_u_mm`：`3.4`
- `feed_pad_radius_mm`：`0.32`
- `port_width_mm`：`0.5`
- `weak_coupling_open_line_enabled`：`0.0`
- `weak_coupling_open_line_length_mm`：`2.2`
- `weak_coupling_open_line_width_mm`：`0.12`
- `weak_coupling_open_line_offset_mm`：`1.65`
- `weak_coupling_open_line_gap_mm`：`0.08`
- `via_fence_enabled`：`0.0`
- `via_fence_count`：`3.0`
- `via_fence_radius_mm`：`0.1`
- `via_fence_pitch_mm`：`0.55`
- `via_fence_edge_offset_mm`：`0.45`
- `via_fence_center_mm`：`3.3`

## 达标情况

- S 参数目标：`未通过`。
- PDOA 极化稳定性目标：`未通过`。
- FOV/轴比目标：`未通过`。
- 全部目标：`未通过`。

## 工程判断

- 这轮会诚实保留未达标项：若隔离或 PDOA 漂移仍不满足目标，说明仅靠小焊盘和局部弱隔离结构还不足以消除线极化敏感性。
- 若过孔栅栏优于开路线，下一步应改为带真实地过孔焊盘和反焊盘的版图级模型；若开路线优于过孔栅栏，下一步应把开路线落到可制造的微带/寄生金属层并联动高度和介质。
- PDOA 曲线最终仍建议配合双极化通道标定矩阵，否则单一天线轴比优化无法完全保证 0/45/90/135 deg 线极化下鉴角曲线不漂移。

## 输出文件

- S 参数筛选：`D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_ab_isolation_finesweep\UWB_CH9_D44_AB_ISOLATION_finesweep_sparam_screening.csv`
- 完整复核：`D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_ab_isolation_finesweep\UWB_CH9_D44_AB_ISOLATION_finesweep_full_validation.csv`
- 最优源幅相扫：`D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_ab_isolation_finesweep\UWB_CH9_D44_AB_ISOLATION_finesweep_best_source_sweep.csv`
- 最优曲线：`D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_ab_isolation_finesweep\UWB_CH9_D44_AB_ISOLATION_finesweep_best_curves.csv`
- 最优结果 JSON：`D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_ab_isolation_finesweep\UWB_CH9_D44_AB_ISOLATION_finesweep_best.json`
