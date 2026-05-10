# D44 当前天线不同极化角度相位误差复核

## 口径

- 当前天线：candidate 37 `fold0p6_neck1p6_stub2p6`，true-fed L 低仰角覆盖单元已保留；相位复核使用 A_ON/B_ON 两个 absorptive 50 ohm 工作态的 A/B 四阵元通道。
- 避开 AEDT/PyAEDT 源切换接口：每个 A/B 端口单独重建工程，只保留一个真实端口，其余 A/B/L 源同位置端接，再导出复数远场。
- 极化角：入射线极化 `0 / 45 / 90 / 135 deg`；误差定义为同一工作态、Theta、基线、方位下，相对 `0 deg` 极化的 PDOA 相位偏差。
- 方位-相位曲线图固定 `Theta=90 deg`、`Freq=8.0 GHz`，横轴为方位 `Phi 0..360 deg`。
- AEDT native Rectangular Plot 导出中角度列按球面采样自动校正：本次远场球面为 `Theta 0..90 deg / Phi 0..360 deg`。

## 按极化角汇总

| 工作态 | 极化角 | 曲线数 | 平均RMS相位误差 | P95 RMS相位误差 | 最大相位误差 | 平均折算方位RMS | P95折算方位RMS | 最大折算方位误差 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `A_ON_absorptive_50ohm_c0p08pf` | 0 deg | 24 | 0.000 deg | 0.000 deg | 0.000 deg | 0.000 deg | 0.000 deg | 0.000 deg |
| `A_ON_absorptive_50ohm_c0p08pf` | 45 deg | 24 | 74.345 deg | 104.115 deg | 179.874 deg | 53.994 deg | 108.420 deg | 299.257 deg |
| `A_ON_absorptive_50ohm_c0p08pf` | 90 deg | 24 | 111.391 deg | 153.884 deg | 179.968 deg | 89.951 deg | 140.600 deg | 340.516 deg |
| `A_ON_absorptive_50ohm_c0p08pf` | 135 deg | 24 | 75.390 deg | 115.704 deg | 179.432 deg | 58.895 deg | 86.466 deg | 310.314 deg |
| `B_ON_absorptive_50ohm_c0p08pf` | 0 deg | 24 | 0.000 deg | 0.000 deg | 0.000 deg | 0.000 deg | 0.000 deg | 0.000 deg |
| `B_ON_absorptive_50ohm_c0p08pf` | 45 deg | 24 | 55.496 deg | 97.606 deg | 179.001 deg | 44.962 deg | 89.206 deg | 260.129 deg |
| `B_ON_absorptive_50ohm_c0p08pf` | 90 deg | 24 | 113.241 deg | 146.389 deg | 179.794 deg | 90.629 deg | 168.227 deg | 342.196 deg |
| `B_ON_absorptive_50ohm_c0p08pf` | 135 deg | 24 | 51.570 deg | 78.335 deg | 175.193 deg | 39.924 deg | 81.810 deg | 220.298 deg |

## 结论

- 相对 `0 deg` 极化，最大相位偏差来自 `A_ON_absorptive_50ohm_c0p08pf` / `90 deg` 极化，最大绝对相位误差 `179.968 deg`。
- 按局部参考曲线斜率折算，最大方位误差来自 `B_ON_absorptive_50ohm_c0p08pf` / `90 deg` 极化，最大折算方位误差 `342.196 deg`。斜率接近零的方位点不参与折算方位误差统计。
- `90 deg` 极化在 A_ON/B_ON 中最敏感，说明当前 A/B 单极化通道仍需要按极化角做相位 LUT 标定；增益覆盖达标不等同于任意极化下相位曲线天然重合。

## 输出图

- 方位-PDOA相位对比图：`D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_dualpol_truefed_l_polarization_phase\plots\UWB_CH9_D44_DUALPOL_TRUEFED_L_POLARIZATION_PHASE_azimuth_phase_comparison_panel.png`
- 方位-相位误差图：`D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_dualpol_truefed_l_polarization_phase\plots\UWB_CH9_D44_DUALPOL_TRUEFED_L_POLARIZATION_PHASE_azimuth_phase_error_panel.png`

## 输出数据

- 曲线 CSV：`D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_dualpol_truefed_l_polarization_phase\UWB_CH9_D44_DUALPOL_TRUEFED_L_POLARIZATION_PHASE_azimuth_phase_curves.csv`
- 极化误差汇总 CSV：`D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_dualpol_truefed_l_polarization_phase\UWB_CH9_D44_DUALPOL_TRUEFED_L_POLARIZATION_PHASE_polarization_error_summary.csv`
- 极化误差聚合 CSV：`D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_dualpol_truefed_l_polarization_phase\UWB_CH9_D44_DUALPOL_TRUEFED_L_POLARIZATION_PHASE_polarization_aggregate.csv`
- 指标 JSON：`D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_dualpol_truefed_l_polarization_phase\UWB_CH9_D44_DUALPOL_TRUEFED_L_POLARIZATION_PHASE_metrics.json`
- 字段导出清单：`D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_dualpol_truefed_l_polarization_phase\UWB_CH9_D44_DUALPOL_TRUEFED_L_POLARIZATION_PHASE_field_manifest.csv`
