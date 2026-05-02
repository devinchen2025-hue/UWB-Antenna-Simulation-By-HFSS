# UWB CH9 D44 H8 PCB圆极化结构仿真报告

## 模型

- AEDT项目: `C:\Users\Administrator\Documents\HFSS Sim\UWB_CH9_Diamond_CP_Array_D44_H8_PCB_CP.aedt`
- 设计名: `Array4_Diamond_D44_H8_PCB_CP`
- 结构: 四阵元菱形布阵，低剖面PCB印刷单馈角截短方形圆极化贴片。
- PCB直径: `44.0 mm`
- 总高度约束: `<= 8.0 mm`
- 当前板厚/总高: `2.0 mm` / `2.070 mm`
- 阵元间距: `17.0 mm`
- 贴片边长/截角: `8.91 mm` / `0.62 mm`

## 验收指标

- 频点: `7.738000GHz / 7.985500GHz / 8.233000GHz`
- FOV区域: `Theta 0-360 deg, Phi 45-90 deg`
- 增益判据: `GainTotal`最小值 >= `-5.0 dBi`
- 圆极化判据: `AxialRatioValue`最大值 <= `3.0 dB`

## FOV与圆极化结果

| 频点 | 源设置 | 最小增益 | 最大轴比 | CP覆盖率 | 结论 |
| ---: | --- | ---: | ---: | ---: | --- |
| 7.738000GHz | P1_only | -13.04 dBi | 13810.61 dB | 14.1% | 未通过 |
| 7.738000GHz | P2_only | -20.13 dBi | 1535.46 dB | 9.6% | 未通过 |
| 7.738000GHz | P3_only | -13.56 dBi | 1783.17 dB | 9.9% | 未通过 |
| 7.738000GHz | P4_only | -19.77 dBi | 10020.57 dB | 12.3% | 未通过 |
| 7.738000GHz | sequential_quadrature_all_ports | -18.12 dBi | 1756.55 dB | 65.1% | 未通过 |
| 7.738000GHz | coverage_envelope_best_port | -7.12 dBi | 1535.46 dB | 11.1% | 未通过 |
| 7.738000GHz | cp_qualified_envelope | -19.77 dBi | 9.54 dB | 29.5% | 未通过 |
| 7.985500GHz | P1_only | -12.62 dBi | 18262.41 dB | 12.6% | 未通过 |
| 7.985500GHz | P2_only | -18.68 dBi | 11888.24 dB | 3.6% | 未通过 |
| 7.985500GHz | P3_only | -13.03 dBi | 11998.58 dB | 9.9% | 未通过 |
| 7.985500GHz | P4_only | -19.26 dBi | 9499.70 dB | 4.9% | 未通过 |
| 7.985500GHz | sequential_quadrature_all_ports | -20.76 dBi | 604.91 dB | 63.2% | 未通过 |
| 7.985500GHz | coverage_envelope_best_port | -6.34 dBi | 9499.70 dB | 1.8% | 未通过 |
| 7.985500GHz | cp_qualified_envelope | -18.92 dBi | 37.76 dB | 23.4% | 未通过 |
| 8.233000GHz | P1_only | -12.15 dBi | 3517.45 dB | 18.4% | 未通过 |
| 8.233000GHz | P2_only | -15.65 dBi | 27642.78 dB | 4.5% | 未通过 |
| 8.233000GHz | P3_only | -12.52 dBi | 16371.61 dB | 17.0% | 未通过 |
| 8.233000GHz | P4_only | -16.46 dBi | 67135.70 dB | 5.2% | 未通过 |
| 8.233000GHz | sequential_quadrature_all_ports | -22.20 dBi | 979.19 dB | 60.3% | 未通过 |
| 8.233000GHz | coverage_envelope_best_port | -7.07 dBi | 67135.70 dB | 4.7% | 未通过 |
| 8.233000GHz | cp_qualified_envelope | -16.32 dBi | 57.53 dB | 32.9% | 未通过 |

## S参数快照

- CH9内最差回波损耗: `-9.27 dB`，项 `dB(S(P3:1,P3:1))`
- CH9内最差耦合: `-17.11 dB`，项 `dB(S(P4:1,P2:1))`
- 对应最差隔离度: `17.11 dB`

## 本轮优化结论

- 初始单馈角截短贴片候选的三频点最差回波约 `-1.51 dB`。
- 粗扫、局部细扫和馈电等效参数扫后，最佳候选为 `patch_side=8.91 mm / feed_offset=2.68 mm / corner_cut=0.62 mm`。
- 最终三频点最差回波为 `-9.27 dB`，已接近但尚未完全满足 `Sii < -10 dB`。
- 当前单馈贴片能提供局部低轴比区域，但全FOV圆极化覆盖仍不达标；下一步应引入印刷匹配支节、双馈正交合成、缝隙耦合或小型90度混合网络。

## 工程说明

- 本版本用于替代超高的顶加载垂直单极子，满足PCB+天线整体高度小于等于8 mm的加工约束。
- 单馈角截短贴片是圆极化的加工友好起点；若全FOV AR<=3 dB不足，需要继续引入双馈正交合成、顺序旋转馈电网络或多层/缝隙耦合结构。
- `coverage_envelope_best_port`仍是PDOA接收覆盖的主要视角；`sequential_quadrature_all_ports`仅用于阵列圆极化趋势检查。
- 详细CSV: `C:\Users\Administrator\Documents\HFSS Sim\reports_d44_h8_pcb_cp\UWB_CH9_D44_H8_PCB_CP_fov_cp_metrics.csv`
- S参数CSV: `C:\Users\Administrator\Documents\HFSS Sim\reports_d44_h8_pcb_cp\UWB_CH9_D44_H8_PCB_CP_s_parameters.csv`
