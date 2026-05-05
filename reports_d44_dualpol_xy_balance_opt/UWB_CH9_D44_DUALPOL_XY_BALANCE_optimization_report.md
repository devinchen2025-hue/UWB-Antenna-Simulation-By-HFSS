# D44 双极化 XY 幅相一致性与同阵元隔离优化报告

## 本轮目标

- 最差回波：`<= -10.0 dB`。
- 同阵元 X/Y 隔离：`>= 15.0 dB`。
- X/Y 回波均衡：差值 `<= 0.5 dB`。
- X/Y 远场幅度一致性：RMS 幅差 `<= 2.0 dB`。
- X/Y 相位一致性：阵元间 RMS 相位离散 `<= 30.0 deg`。
- 双极化向量相关 PDOA：平均 RMS 漂移 `<= 10.0 deg`，最大漂移 `<= 20.0 deg`。

## 优化方法

- 先用三频点 S 参数筛选整体馈点、焊盘、端口片、A/B 非对称馈点、弱耦合开路线和温和过孔栅栏候选。
- 再对排名靠前候选提取嵌入远场，复核双极化向量相关 PDOA、X/Y 幅度 RMS 差和阵元间相位离散。

## S 参数筛选排名

| 排名 | 候选 | 评分 | 最差Sii | X回波 | Y回波 | 回波差 | 同阵元X/Y隔离 | 说明 |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | `openline_l2p80` | 35.62 | -9.05 dB | -9.37 dB | -9.05 dB | 0.31 dB | 12.68 dB | 加长弱耦合开路线，增强 A/B 反向耦合调节能力。 |
| 2 | `openline_l2p40` | 36.18 | -9.17 dB | -9.28 dB | -9.17 dB | 0.10 dB | 12.34 dB | 加入悬浮弱耦合开路线，尝试提升同阵元 X/Y 隔离。 |
| 3 | `pad0p28_port0p50_feed3p40` | 38.29 | -8.87 dB | -9.02 dB | -8.87 dB | 0.15 dB | 12.76 dB | 进一步减小焊盘半径，测试隔离收益与匹配损失。 |
| 4 | `feed3p30` | 40.40 | -8.66 dB | -8.66 dB | -9.43 dB | 0.78 dB | 13.11 dB | 整体内移 X/Y 馈点，观察 Y 路匹配和同阵元隔离变化。 |
| 5 | `pad0p30_port0p50_feed3p40` | 42.63 | -8.86 dB | -9.26 dB | -8.86 dB | 0.40 dB | 12.23 dB | 减小焊盘半径，降低 A/B 近场耦合。 |
| 6 | `asym_a3p35_b3p50` | 43.26 | -8.58 dB | -9.27 dB | -8.58 dB | 0.69 dB | 12.88 dB | A 路略内移、B 路外移，直接优化 X/Y 回波均衡。 |
| 7 | `asym_a3p40_b3p50` | 43.94 | -8.72 dB | -9.33 dB | -8.72 dB | 0.61 dB | 12.44 dB | 仅外移 B/Y 馈点，用几何不对称补偿 Y 路回波偏弱。 |
| 8 | `port0p55_feed3p40` | 44.40 | -8.49 dB | -9.01 dB | -8.49 dB | 0.52 dB | 12.85 dB | 加宽端口片改善 Y 路回波，同时观察 X/Y 回波平衡。 |
| 9 | `dualpol_baseline` | 46.03 | -8.59 dB | -9.24 dB | -8.59 dB | 0.65 dB | 12.49 dB | 双极化 XY 初版，作为本轮幅相/隔离优化基线。 |
| 10 | `port0p60_feed3p40` | 47.13 | -8.46 dB | -9.20 dB | -8.46 dB | 0.73 dB | 12.68 dB | 进一步加宽端口片，追求 Y 路匹配改善。 |

## 完整复核结果

| 候选 | 综合评分 | 同阵元X/Y隔离 | 回波差 | 幅差RMS | 相位离散RMS | 向量PDOA平均RMS | 95分位 | 最大漂移 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `pad0p28_port0p50_feed3p40` | 89.95 | 12.76 dB | 0.15 dB | 5.48 dB | 48.54 deg | 53.38 deg | 78.71 deg | 179.99 deg |
| `feed3p30` | 92.30 | 13.11 dB | 0.78 dB | 5.56 dB | 49.09 deg | 53.02 deg | 79.91 deg | 179.98 deg |
| `dualpol_baseline` | 98.09 | 12.49 dB | 0.65 dB | 5.53 dB | 49.03 deg | 53.69 deg | 79.07 deg | 179.97 deg |

## 最优候选

- 候选：`pad0p28_port0p50_feed3p40`
- 说明：进一步减小焊盘半径，测试隔离收益与匹配损失。
- AEDT 工程：`D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\UWB_CH9_Diamond_CP_Array_D44_DUALPOL_XY.aedt`
- 最差回波：`-8.87 dB`
- X/A 最差回波：`-9.02 dB`
- Y/B 最差回波：`-8.87 dB`
- X/Y 回波差：`0.15 dB`
- 同阵元 X/Y 隔离：`12.76 dB`
- X/Y 幅度 RMS 差：`5.48 dB`
- X/Y 阵元间相位离散 RMS：`48.54 deg`
- 双极化向量相关 PDOA 平均 RMS：`53.38 deg`
- 双极化向量相关 PDOA 95 分位：`78.71 deg`
- 双极化向量相关 PDOA 最大漂移：`179.99 deg`

## 与双极化初版对比

| 指标 | 初版 | 本轮最优 | 变化 |
| --- | ---: | ---: | ---: |
| 最差回波 | -8.59 dB | -8.87 dB | -0.28 |
| 同阵元 X/Y 隔离 | 12.49 dB | 12.76 dB | +0.27 |
| X/Y 回波差 | 0.65 dB | 0.15 dB | -0.50 |
| X/Y 幅度 RMS 差 | 5.53 dB | 5.48 dB | -0.05 |
| X/Y 相位离散 RMS | 49.03 deg | 48.54 deg | -0.49 |
| 向量 PDOA 平均 RMS | 53.69 deg | 53.38 deg | -0.31 |
| 向量 PDOA 95 分位 | 79.07 deg | 78.71 deg | -0.36 |

## 达标情况

- S 参数/同阵元隔离目标：`未通过`。
- X/Y 幅相一致性目标：`未通过`。
- PDOA 稳定性目标：`未通过`。
- 全部目标：`未通过`。

## 工程判断

- 本轮直接优化 X/Y 回波均衡、同阵元隔离和远场幅相一致性；若最优仍未达标，说明仅靠探针位置和简单寄生/过孔结构不足以消除双极化通道差异。
- `openline_l2p80` 和 `openline_l2p40` 在三频点 S 参数筛选中排名靠前，但 `openline_l2p80` 的完整远场复核曾触发 AEDT gRPC/无限球设置异常；本轮最终选择已完整复核并保存为可运行工程的 `pad0p28_port0p50_feed3p40`。
- 下一轮应优先进入真正的双极化馈电网络：两路等长微带过渡、可调匹配段、同阵元隔离枝节，以及接收端双通道幅相标定矩阵。
- 当前双极化方案仍建议保留，因为它提供了后端矢量相关和标定自由度；但硬件上必须把 X/Y 两路作为独立接收通道处理。

## 输出文件

- S 参数筛选：`D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_dualpol_xy_balance_opt\UWB_CH9_D44_DUALPOL_XY_BALANCE_sparam_screening.csv`
- 完整复核：`D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_dualpol_xy_balance_opt\UWB_CH9_D44_DUALPOL_XY_BALANCE_full_validation.csv`
- 最优曲线：`D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_dualpol_xy_balance_opt\UWB_CH9_D44_DUALPOL_XY_BALANCE_best_curves.csv`
- 最优汇总：`D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_dualpol_xy_balance_opt\UWB_CH9_D44_DUALPOL_XY_BALANCE_best_summary.csv`
- 最优 JSON：`D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_dualpol_xy_balance_opt\UWB_CH9_D44_DUALPOL_XY_BALANCE_best.json`
