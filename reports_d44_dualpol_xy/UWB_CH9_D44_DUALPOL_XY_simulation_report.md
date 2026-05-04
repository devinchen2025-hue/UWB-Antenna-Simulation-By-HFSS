# D44 锚点天线双极化 XY 拓扑初版仿真报告

## 目标

- 将锚点天线从固定 90 度圆极化合成路线改为独立 X/Y 双极化接收路线。
- 入射极化只考虑线极化 `0 / 45 / 90 / 135 deg`。
- 优先指标从轴比转为：双端口匹配、X/Y 端口隔离、双极化矢量合成后的 PDOA 曲线稳定性。

## 拓扑与参数

- 分支：`feature/d44-dualpol-anchor`
- AEDT 工程：`D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\UWB_CH9_Diamond_CP_Array_D44_DUALPOL_XY.aedt`
- 设计名：`Array4_Diamond_D44_DualPolarized_XY`
- 四个阵元的贴片均保持全局同向，不再按阵列方位旋转。
- A 口定义为全局 X 极化通道，B 口定义为全局 Y 极化通道。
- 贴片边长：`9.15 mm`
- 馈电偏移：`3.4 mm`
- 焊盘半径：`0.32 mm`
- 端口片宽度：`0.5 mm`

## S 参数

- 最差回波：`-8.59 dB`，表达式 `dB(S(P3B:1,P3B:1))`
- X/A 通道最差回波：`-9.24 dB`
- Y/B 通道最差回波：`-8.59 dB`
- 同阵元 X/Y 最差隔离：`12.49 dB`
- 同极化阵元间最差隔离：`16.18 dB`
- 全端口最差隔离：`12.49 dB`
- S 参数目标：`未通过`。

## PDOA 线极化稳定性

| 策略 | 平均 RMS 漂移 | 95 分位 RMS | 最大漂移 | 平均有效点 | 说明 |
| --- | ---: | ---: | ---: | ---: | --- |
| `legacy_cp_minus90` | 52.26 deg | 77.73 deg | 179.94 deg | 99.7% | 沿用圆极化路线的 A + B*(-90 deg) 合成，仅作对照。 |
| `dualpol_vector_correlation` | 53.69 deg | 79.07 deg | 179.97 deg | 100.0% | 推荐的双极化 PDOA：用 X/Y 两通道向量相关直接估计两阵元相位差。 |
| `y_only_b_port` | 61.47 deg | 101.23 deg | 180.00 deg | 99.4% | 仅使用 B 口，全局 Y 极化通道。 |
| `x_only_a_port` | 66.03 deg | 91.99 deg | 179.98 deg | 99.4% | 仅使用 A 口，全局 X 极化通道。 |
| `dualpol_known_pol_vector` | 71.74 deg | 98.73 deg | 179.99 deg | 99.7% | 已知入射线极化角时，按 cos/sin 对 X/Y 双通道做相干合成。 |
| `dualpol_fixed_45deg_sum` | 72.43 deg | 130.26 deg | 180.00 deg | 99.4% | 固定 45 deg 双通道等权合成，作为无极化估计时的简单参考。 |

## 最优策略

- 最优策略：`legacy_cp_minus90`
- 平均 RMS PDOA 漂移：`52.26 deg`
- 95 分位 RMS PDOA 漂移：`77.73 deg`
- 最大 PDOA 漂移：`179.94 deg`
- PDOA 目标：`未通过`。

## 与上一轮圆极化/双馈路线对比

- 上一轮最优候选：`pad0p32_port0p50_feed3p40`。
- 上一轮平均 RMS PDOA 漂移：`45.78 deg`；本轮最优：`52.26 deg`。
- 上一轮 95 分位 RMS PDOA 漂移：`78.13 deg`；本轮最优：`77.73 deg`。
- 上一轮最大 PDOA 漂移：`179.98 deg`；本轮最优：`179.94 deg`。

## 工程结论

- 本轮初版双极化几何尚未优于上一轮圆极化/双馈最佳结果；当前最优仍是对照策略 `legacy_cp_minus90`。
- 推荐的双极化向量相关策略平均 RMS 漂移为 `53.69 deg`，比单独 X/Y 通道稳定，但仍未达到目标。
- 双极化拓扑已经成功建模并求解，独立 X/Y 端口为后端极化标定和矢量合成留下了自由度。
- 如果 `dualpol_known_pol_vector` 优于单端口策略，说明双极化接收对线极化入射有明确价值；但实际系统需要估计或标定入射极化角。
- 如果 `dualpol_vector_correlation` 优于单端口策略，说明可以不先压成单个极化电压，而是直接用 X/Y 两通道向量相关做相位差估计。
- 若 S 参数仍未达标，下一步应围绕 X/Y 同阵元隔离和两路幅相一致性优化，而不是继续把轴比作为主目标。
- 当前报告仍是快速三频点仿真结果，后续定版前应增加完整频扫、制造过孔/馈线模型和接收通道标定误差。

## 输出文件

- AEDT 工程：`D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\UWB_CH9_Diamond_CP_Array_D44_DUALPOL_XY.aedt`
- S 参数 CSV：`D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_dualpol_xy\UWB_CH9_D44_DUALPOL_XY_s_parameters.csv`
- PDOA 曲线 CSV：`D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_dualpol_xy\UWB_CH9_D44_DUALPOL_XY_pdoa_linear_curves.csv`
- PDOA 汇总 CSV：`D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_dualpol_xy\UWB_CH9_D44_DUALPOL_XY_pdoa_linear_summary.csv`
- 指标 JSON：`D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_dualpol_xy\UWB_CH9_D44_DUALPOL_XY_metrics.json`
