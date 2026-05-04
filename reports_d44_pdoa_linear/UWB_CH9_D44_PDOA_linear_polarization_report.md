# D44 双馈贴片线极化 PDOA 评估报告

## 评估目标

- 本轮只考虑入射线极化，角度固定为 `0 / 45 / 90 / 135 deg`。
- 不评估圆极化、椭圆极化或任意连续极化角扫描。
- 目标是观察入射线极化方向变化对当前 PDOA 测角/鉴角曲线的影响。

## 数据来源和方法

- AEDT 项目: `D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\UWB_CH9_Diamond_CP_Array_D44_DUALFEED_CP.aedt`
- 设计名: `Array4_Diamond_D44_DualFeed_CP`
- 解算: `Setup_CH9 : Sweep_CH9`
- 远场球面: `Upper_Hemisphere_5deg`
- 端口源: `P1A, P1B, P2A, P2B, P3A, P3B, P4A, P4B`
- 评估频点: `7.7380 GHz, 7.9855 GHz, 8.2330 GHz`
- 方位切面: `45 deg, 60 deg, 75 deg, 90 deg`
- 使用 HFSS 远场复数量 `re/im(rETheta)` 与 `re/im(rEPhi)`。
- 线极化投影定义为 `V = Etheta*cos(psi) + Ephi*sin(psi)`，其中 `psi` 为本地球坐标切向基下的线极化角。
- PDOA 定义为两个接收通道复响应相位差 `angle(V_left)-angle(V_right)`，并按 theta 曲线展开。
- 双馈合成通道采用与前序 CP 激励一致的 `A + B*exp(-j90deg)` 作为工程近似。

## 核心结论

- 共生成 `864` 条 PDOA 曲线汇总。
- 最大线极化敏感项: `B_feed_only` / `E1-E2`，`freq=7.7380 GHz`，`phi=45 deg`，`pol=90 deg`，相对 0 deg 线极化最大 PDOA 偏移 `180.00 deg`。
- 最大 RMS 偏移项: `B_feed_only` / `E3-E4`，`freq=7.7380 GHz`，`phi=45 deg`，`pol=90 deg`，RMS 偏移 `159.98 deg`。
- 当前结构对线极化方向非常敏感，说明如果 PDOA 标定只用单一线极化，换成 45/90/135 deg 入射时会引入显著鉴角曲线偏移。

## 按线极化角汇总

| 入射线极化 | 曲线数 | 平均有效点 | 平均单调片段 | 平均 RMS 偏移 | 最大偏移 |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 0deg | 216 | 99.4% | 68.8% | 0.00 deg | 0.00 deg |
| 45deg | 216 | 98.8% | 68.4% | 68.89 deg | 179.96 deg |
| 90deg | 216 | 99.2% | 68.7% | 92.29 deg | 180.00 deg |
| 135deg | 216 | 99.7% | 69.5% | 57.11 deg | 179.98 deg |

## 相对较优的鉴角曲线候选

| 频点GHz | Phi | 极化 | 通道组 | 基线 | PDOA展开跨度deg | 单调片段 | RMS偏移deg |
| ---: | ---: | ---: | --- | --- | ---: | ---: | ---: |
| 7.9855 | 90 | 0 | A_feed_only | E1-E3 | 720.00 | 100.0% | 0.00 |
| 7.7380 | 90 | 0 | A_feed_only | E1-E3 | 720.00 | 100.0% | 0.00 |
| 7.7380 | 75 | 0 | dualfeed_quadrature_minus90 | E1-E3 | 720.00 | 100.0% | 0.00 |
| 7.7380 | 90 | 0 | dualfeed_quadrature_minus90 | E1-E3 | 720.00 | 100.0% | 0.00 |
| 7.9855 | 75 | 0 | dualfeed_quadrature_minus90 | E1-E3 | 720.00 | 100.0% | 0.00 |

## 工程判断

- 若 PDOA 系统使用当前双馈贴片直接测角，应把线极化角作为标定维度，否则不同入射线极化会造成系统性相位偏置。
- 若希望降低对入射线极化方向的敏感性，优先继续优化双馈幅相平衡、端口隔离和混合网络输出匹配；只改善单端口 S11 不足以稳定 PDOA 曲线。
- 本报告使用嵌入式发射远场按互易性构造接收响应代理，尚未包含实测线缆相位、接收机通道相位和暗室标定误差。

## 输出文件

- 曲线 CSV: `D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_pdoa_linear\UWB_CH9_D44_PDOA_linear_polarization_curves.csv`
- 汇总 CSV: `D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_pdoa_linear\UWB_CH9_D44_PDOA_linear_polarization_summary.csv`
- 指标 JSON: `D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_pdoa_linear\UWB_CH9_D44_PDOA_linear_polarization_metrics.json`
- 中文报告: `D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_pdoa_linear\UWB_CH9_D44_PDOA_linear_polarization_report.md`
