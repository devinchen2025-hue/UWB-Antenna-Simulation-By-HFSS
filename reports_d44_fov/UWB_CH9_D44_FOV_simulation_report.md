# UWB CH9 D44 FOV结构仿真报告

## 模型

- AEDT项目: `C:\Users\Administrator\Documents\HFSS Sim\UWB_CH9_Diamond_CP_Array_D44_FOV.aedt`
- 设计名: `Array4_Diamond_D44_FOV`
- 结构: 四阵元菱形布阵，每个阵元改为顶加载垂直单极子，用于获得近似甜甜圈方向图。
- PCB直径: `44.0 mm`
- 阵元间距: `17.0 mm`
- 单极子高度: `8.6 mm`
- 电容帽半径: `1.55 mm`

## FOV指标

- 评估频点: `7.738000GHz / 7.985500GHz / 8.233000GHz`，若工程只有单点解则自动使用已有频点。
- FOV区域: `Theta=0-360 deg, Phi=45-90 deg`
- 判据: `GainTotal`最小值 >= `-5 dBi`

| 频点 | 源设置 | 最小增益 | 最大增益 | 起伏 | 最小值位置 | 结论 |
| ---: | --- | ---: | ---: | ---: | --- | --- |
| 7.738000GHz | P1_only | -2.80 dBi | 2.76 dBi | 5.57 dB | Theta=355 deg, Phi=45 deg | 通过 |
| 7.738000GHz | P2_only | -6.75 dBi | 2.88 dBi | 9.62 dB | Theta=240 deg, Phi=90 deg | 未通过 |
| 7.738000GHz | P3_only | -2.87 dBi | 2.70 dBi | 5.57 dB | Theta=10 deg, Phi=45 deg | 通过 |
| 7.738000GHz | P4_only | -6.86 dBi | 2.63 dBi | 9.50 dB | Theta=120 deg, Phi=90 deg | 未通过 |
| 7.738000GHz | equal_phase_all_ports | -27.56 dBi | 2.49 dBi | 30.05 dB | Theta=0 deg, Phi=45 deg | 未通过 |
| 7.738000GHz | coverage_envelope_best_port | -2.07 dBi | 2.88 dBi | 4.95 dB | Theta=0 deg, Phi=55 deg | 通过 |
| 7.985500GHz | P1_only | -2.92 dBi | 3.06 dBi | 5.98 dB | Theta=355 deg, Phi=45 deg | 通过 |
| 7.985500GHz | P2_only | -6.93 dBi | 3.32 dBi | 10.24 dB | Theta=235 deg, Phi=90 deg | 未通过 |
| 7.985500GHz | P3_only | -2.99 dBi | 3.10 dBi | 6.09 dB | Theta=5 deg, Phi=45 deg | 通过 |
| 7.985500GHz | P4_only | -7.02 dBi | 3.05 dBi | 10.06 dB | Theta=125 deg, Phi=90 deg | 未通过 |
| 7.985500GHz | equal_phase_all_ports | -27.05 dBi | 2.79 dBi | 29.85 dB | Theta=360 deg, Phi=50 deg | 未通过 |
| 7.985500GHz | coverage_envelope_best_port | -2.22 dBi | 3.32 dBi | 5.53 dB | Theta=360 deg, Phi=65 deg | 通过 |
| 8.233000GHz | P1_only | -2.98 dBi | 3.33 dBi | 6.31 dB | Theta=355 deg, Phi=45 deg | 通过 |
| 8.233000GHz | P2_only | -7.48 dBi | 3.67 dBi | 11.16 dB | Theta=235 deg, Phi=90 deg | 未通过 |
| 8.233000GHz | P3_only | -3.05 dBi | 3.44 dBi | 6.50 dB | Theta=5 deg, Phi=45 deg | 通过 |
| 8.233000GHz | P4_only | -7.64 dBi | 3.38 dBi | 11.03 dB | Theta=130 deg, Phi=90 deg | 未通过 |
| 8.233000GHz | equal_phase_all_ports | -26.50 dBi | 3.10 dBi | 29.60 dB | Theta=0 deg, Phi=55 deg | 未通过 |
| 8.233000GHz | coverage_envelope_best_port | -2.31 dBi | 3.67 dBi | 5.99 dB | Theta=360 deg, Phi=80 deg | 通过 |

## S参数快照

- 最差回波损耗: `-4.40 dB`
- 最差耦合: `-13.41 dB`

## 工程说明

- `equal_phase_all_ports`是四端口等幅同相激励，会包含阵因子零陷；这不是PDOA接收阵列的常规单通道方向图判据。
- `coverage_envelope_best_port`表示四个阵元中每个方向取最强端口，是评估360度覆盖可用性的更合理视角。
- 当前版本优先解决FOV最小增益和甜甜圈形方向图；圆极化、隔离度和群时延仍需要后续结构细化。
- 详细数据CSV: `C:\Users\Administrator\Documents\HFSS Sim\reports_d44_fov\UWB_CH9_D44_FOV_fov_metrics.csv`
