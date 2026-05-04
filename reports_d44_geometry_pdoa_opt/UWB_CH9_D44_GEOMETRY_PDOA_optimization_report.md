# D44 锚点天线几何/隔离结构 PDOA 稳定性优化报告

## 本轮目标

- S 参数：最差 `Sii <= -10.0 dB`，端口隔离 `>= 15.0 dB`。
- FOV：最小增益 `>= -5.0 dBi`，轴比 `<= 3.0 dB`。
- PDOA：不同线极化下平均 RMS 漂移 `<= 10.0 deg`，最大漂移 `<= 20.0 deg`。

## 优化路径

- 从上一轮结论出发，不再只调整 90 度混合器输出幅相，而是进入阵元几何和隔离结构层。
- 本轮稳定完成的候选覆盖：馈电焊盘/端口片缩小、馈点外移、贴片边长联动。
- 脚本中保留了阵列隔离槽加宽/加长和局部 DGS 候选，但这批候选在 AEDT 阶段曾出现异常中断，未纳入本次默认排名，后续需要单独排查。
- 先使用三频点 S 参数快速筛选，再对排名最优候选重新带远场求解，并提取复数远场做 PDOA 极化稳定性评估。

## S 参数筛选排名

| 排名 | 候选 | 评分 | 最差 Sii | 隔离度 | 说明 |
| ---: | --- | ---: | ---: | ---: | --- |
| 1 | `probe_reference_current` | 43.52 | -8.57 dB | 12.44 dB | 当前双馈探针/焊盘参考结构，作为几何层优化基线。 |
| 2 | `small_pad_feed3p30` | 46.62 | -8.39 dB | 12.55 dB | 缩小馈电焊盘和端口片，降低同贴片 A/B 端口近场耦合。 |
| 3 | `patch9p25_feed3p65` | 54.16 | -8.48 dB | 10.98 dB | 略增贴片边长并外移馈点，尝试恢复谐振同时降低双馈耦合。 |
| 4 | `small_pad_feed3p55` | 56.44 | -8.08 dB | 11.99 dB | 在小焊盘基础上把双馈点外移，观察匹配和正交模隔离是否改善。 |

## 最优完整复核候选

- 候选：`small_pad_feed3p30`
- 说明：缩小馈电焊盘和端口片，降低同贴片 A/B 端口近场耦合。
- AEDT 工程：`D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\UWB_CH9_Diamond_CP_Array_D44_DUALFEED_CP.aedt`
- 最差 Sii：`-8.39 dB`
- 隔离度：`12.55 dB`
- PDOA 最优 B 路幅度：`1.000`
- PDOA 最优 B 路相位：`-90.0 deg`
- 平均 RMS PDOA 漂移：`46.58 deg`
- 95 分位 RMS PDOA 漂移：`79.03 deg`
- 最大 PDOA 漂移：`179.89 deg`
- FOV 最小增益：`-18.19 dBi`
- FOV 最大轴比：`932.54 dB`
- CP 覆盖率下限：`55.5%`

## 达标情况

- S 参数目标：`未通过`。
- PDOA 极化稳定性目标：`未通过`。
- FOV/轴比目标：`未通过`。
- 全部目标：`未通过`。

## 工程结论

- 缩小焊盘和端口片对同贴片 A/B 隔离有正向作用，是本轮最可靠的几何趋势。
- 馈点外移会改变匹配和隔离折中，但本轮没有改善 PDOA 对线极化的根本敏感性。
- 本轮最优完整候选仍未把 PDOA 最大漂移压低到目标内，说明需要引入真正的双极化接收/标定融合，或进一步做阵元级矢量有效长度一致性优化。
- 下一轮建议在当前小焊盘趋势上继续细扫 `feed_pad_radius=0.28-0.36 mm`、`port_width=0.45-0.60 mm`、`feed_offset=3.20-3.60 mm`，并增加可调的 A/B 间弱耦合隔离开路线或过孔栅栏模型。

## 输出文件

- S 参数筛选：`D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_geometry_pdoa_opt\UWB_CH9_D44_GEOMETRY_PDOA_sparam_screening.csv`
- 完整复核：`D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_geometry_pdoa_opt\UWB_CH9_D44_GEOMETRY_PDOA_full_validation.csv`
- 最优源幅相扫：`D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_geometry_pdoa_opt\UWB_CH9_D44_GEOMETRY_PDOA_best_source_sweep.csv`
- 最优曲线：`D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_geometry_pdoa_opt\UWB_CH9_D44_GEOMETRY_PDOA_best_curves.csv`
- 最优结果 JSON：`D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_geometry_pdoa_opt\UWB_CH9_D44_GEOMETRY_PDOA_best.json`
