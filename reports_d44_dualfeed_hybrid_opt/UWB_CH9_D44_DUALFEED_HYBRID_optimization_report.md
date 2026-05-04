# D44 双馈正交贴片 / 90 度混合网络优化报告

## 设计目标

- 7.738 / 7.9855 / 8.233 GHz 三个频点内，最差自反射 `Sii <= -10.0 dB`。
- 端口隔离度 `>= 15.0 dB`。
- FOV 覆盖包络最小增益 `>= -5.0 dBi`。
- 在选定 FOV 内轴比 `AxialRatioValue <= 3.0 dB`；若未达标，则记录本轮最优幅相平衡结果。

## 最佳候选

- 候选名称：`dualfeed_feed_3p3`
- 拓扑类型：`dualfeed`，即双馈正交贴片
- 选择原因：在 `3.4 mm` 最佳馈点附近继续内收微调，得到本轮综合评分最低的候选。
- 是否满足全部目标：`否`

## 几何参数

- `patch_side_mm`：`9.150`
- `feed_offset_u_mm`：`3.300`
- `port_width_mm`：`0.700`
- `feed_pad_radius_mm`：`0.420`
- `isolation_slot_length_mm`：`10.000`
- `isolation_slot_width_mm`：`0.420`

## 核心仿真指标

- 最差回波损耗：`-8.57 dB`，对应表达式 `dB(S(P3A:1,P3A:1))`
- 最差端口耦合：`-12.44 dB`，对应表达式 `dB(S(P1B:1,P1A:1))`
- 对应隔离度：`12.44 dB`
- 覆盖包络最小增益：`-7.99 dBi`
- CP 合格包络最大轴比：`10.15 dB`
- CP 合格包络最小增益：`-19.55 dBi`
- CP 合格包络最小覆盖率：`48.6%`

## 最佳源幅相平衡

- B 馈电幅度：`1.000`，相对于 A 馈电
- B 馈电相位：`-105.0 deg`，相对于 A 馈电
- 平衡阵列最小增益：`-14.72 dBi`
- 平衡阵列最大轴比：`1046.40 dB`
- 平衡阵列最小 CP 覆盖率：`29.9%`

## S 参数筛选排名

| 排名 | 候选 | 拓扑 | 评分 | 最差 Sii | 隔离度 | 说明 |
| ---: | --- | --- | ---: | ---: | ---: | --- |
| 1 | dualfeed_feed_3p3 | dualfeed | 25.61 | -8.57 dB | 12.44 dB | 在 3.4 mm 最佳馈点附近略向内微调。 |
| 2 | dualfeed_feed_3p3 | dualfeed | 25.61 | -8.57 dB | 12.44 dB | 在 3.4 mm 最佳馈点附近略向内微调。 |
| 3 | dualfeed_feed_3p4 | dualfeed | 27.54 | -8.52 dB | 12.19 dB | 双馈点外移以提高输入阻抗。 |
| 4 | dualfeed_feed_3p4 | dualfeed | 27.54 | -8.52 dB | 12.19 dB | 双馈点外移以提高输入阻抗。 |
| 5 | dualfeed_feed_3p4_narrow_port | dualfeed | 28.44 | -8.46 dB | 12.19 dB | 保持最佳馈点，减小端口宽度和馈电焊盘电容。 |
| 6 | dualfeed_feed_3p2 | dualfeed | 32.10 | -8.10 dB | 12.77 dB | 在基线和 3.4 mm 最佳点之间做中间值扫描。 |
| 7 | dualfeed_feed_3p6 | dualfeed | 39.47 | -7.74 dB | 12.38 dB | 沿回波改善趋势继续向外移动馈点。 |
| 8 | dualfeed_feed_3p4_wide_port | dualfeed | 43.99 | -7.45 dB | 12.46 dB | 保持最佳馈点，增大局部馈电电容。 |
| 9 | dualfeed_feed_3p8 | dualfeed | 56.28 | -6.87 dB | 11.75 dB | 继续向贴片边缘移动馈点以尝试匹配。 |
| 10 | hybrid_baseline | hybrid | 85.97 | -4.27 dB | 16.50 dB | 上一轮 90 度混合网络基线拓扑。 |

## 结论

本轮优化未完全达到目标。相对上一版双馈基线，最差回波损耗从约 `-4.20 dB` 改善到 `-8.57 dB`，CP 合格包络最大轴比从约 `13.36 dB` 降到 `10.15 dB`，说明馈点外移方向有效。

当前主要瓶颈是同一贴片内 A/B 双馈端口之间耦合偏强，最差隔离度只有 `12.44 dB`，低于 `15.0 dB` 目标；同时全 FOV 圆极化仍未压到 `3.0 dB` 轴比目标。下一轮建议引入真实匹配/隔离结构，例如双馈端口间微带隔离枝节、局部缺陷地结构、90 度混合器输出端匹配段，或将双馈端口从简单探针/焊盘过渡升级为可调微带网络。

## 输出文件

- 优化历史：`D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_dualfeed_hybrid_opt\UWB_CH9_D44_DUALFEED_HYBRID_optimization_history.csv`
- 源幅相扫描：`D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_dualfeed_hybrid_opt\UWB_CH9_D44_DUALFEED_HYBRID_source_balance.csv`
- 最佳结果 JSON：`D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_dualfeed_hybrid_opt\UWB_CH9_D44_DUALFEED_HYBRID_best.json`
- 最终拓扑报告目录：`D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_dualfeed_cp`
