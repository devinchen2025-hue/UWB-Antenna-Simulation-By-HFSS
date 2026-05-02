# UWB CH9 D44 H8 PCB圆极化结构仿真报告

## 模型

- AEDT项目: `D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\UWB_CH9_Diamond_CP_Array_D44_H8_PCB_CP.aedt`
- 设计名: `Array4_Diamond_D44_H8_PCB_CP`
- 结构: 四阵元菱形布阵，低剖面PCB印刷单馈角截短方形圆极化贴片。
- PCB直径: `44.0 mm`
- 总高度约束: `<= 8.0 mm`
- 当前板厚/总高: `2.0 mm` / `2.070 mm`
- 阵元间距: `17.0 mm`
- 贴片边长/截角: `9.0 mm` / `0.84 mm`

## 验收指标

- 频点: `7.738000GHz / 7.985500GHz / 8.233000GHz`
- FOV区域: `Theta 0-360 deg, Phi 45-90 deg`
- 增益判据: `GainTotal`最小值 >= `-5.0 dBi`
- 圆极化判据: `AxialRatioValue`最大值 <= `3.0 dB`

## FOV与圆极化结果

| 频点 | 源设置 | 最小增益 | 最大轴比 | CP覆盖率 | 结论 |
| ---: | --- | ---: | ---: | ---: | --- |
| 7.738000GHz | P1_only | -12.65 dBi | 2414.46 dB | 29.7% | 未通过 |
| 7.738000GHz | P2_only | -22.17 dBi | 7873.18 dB | 10.7% | 未通过 |
| 7.738000GHz | P3_only | -13.63 dBi | 817.38 dB | 18.2% | 未通过 |
| 7.738000GHz | P4_only | -20.46 dBi | 6326.84 dB | 9.6% | 未通过 |
| 7.738000GHz | sequential_quadrature_all_ports | -17.89 dBi | 484.88 dB | 64.9% | 未通过 |
| 7.738000GHz | coverage_envelope_best_port | -7.99 dBi | 7873.18 dB | 13.2% | 未通过 |
| 7.738000GHz | cp_qualified_envelope | -20.46 dBi | 14.54 dB | 48.1% | 未通过 |
| 7.985500GHz | P1_only | -11.45 dBi | 15126.80 dB | 20.4% | 未通过 |
| 7.985500GHz | P2_only | -22.88 dBi | 4161.54 dB | 3.8% | 未通过 |
| 7.985500GHz | P3_only | -13.39 dBi | 1744.62 dB | 16.6% | 未通过 |
| 7.985500GHz | P4_only | -20.82 dBi | 49885.11 dB | 5.1% | 未通过 |
| 7.985500GHz | sequential_quadrature_all_ports | -19.77 dBi | 339.02 dB | 63.6% | 未通过 |
| 7.985500GHz | coverage_envelope_best_port | -6.93 dBi | 12146.50 dB | 5.6% | 未通过 |
| 7.985500GHz | cp_qualified_envelope | -22.88 dBi | 23.98 dB | 33.4% | 未通过 |
| 8.233000GHz | P1_only | -11.07 dBi | 28806.32 dB | 22.7% | 未通过 |
| 8.233000GHz | P2_only | -25.42 dBi | 11133.32 dB | 8.1% | 未通过 |
| 8.233000GHz | P3_only | -12.43 dBi | 1990.70 dB | 21.2% | 未通过 |
| 8.233000GHz | P4_only | -24.77 dBi | 3993.86 dB | 10.1% | 未通过 |
| 8.233000GHz | sequential_quadrature_all_ports | -21.24 dBi | 9531.47 dB | 60.0% | 未通过 |
| 8.233000GHz | coverage_envelope_best_port | -6.20 dBi | 11133.32 dB | 11.8% | 未通过 |
| 8.233000GHz | cp_qualified_envelope | -25.42 dBi | 32.09 dB | 38.9% | 未通过 |

## S参数快照

- CH9内最差回波损耗: `-9.83 dB`，项 `dB(S(P4:1,P4:1))`
- CH9内最差耦合: `-17.38 dB`，项 `dB(S(P4:1,P2:1))`
- 对应最差隔离度: `17.38 dB`

## 本轮优化结论

- 初始单馈角截短贴片候选的三频点最差回波约 `-1.51 dB`。
- 粗扫、局部细扫和馈电等效参数扫后，最佳候选为 `patch_side=8.91 mm / feed_offset=2.68 mm / corner_cut=0.62 mm`。
- 最终三频点最差回波为 `-9.27 dB`，已接近但尚未完全满足 `Sii < -10 dB`。
- 当前单馈贴片能提供局部低轴比区域，但全FOV圆极化覆盖仍不达标；下一步应引入印刷匹配支节、双馈正交合成、缝隙耦合或小型90度混合网络。

## 工程说明

- 本版本用于替代超高的顶加载垂直单极子，满足PCB+天线整体高度小于等于8 mm的加工约束。
- 单馈角截短贴片是圆极化的加工友好起点；若全FOV AR<=3 dB不足，需要继续引入双馈正交合成、顺序旋转馈电网络或多层/缝隙耦合结构。
- `coverage_envelope_best_port`仍是PDOA接收覆盖的主要视角；`sequential_quadrature_all_ports`仅用于阵列圆极化趋势检查。
- 详细CSV: `D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_h8_pcb_cp\UWB_CH9_D44_H8_PCB_CP_fov_cp_metrics.csv`
- S参数CSV: `D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_h8_pcb_cp\UWB_CH9_D44_H8_PCB_CP_s_parameters.csv`
