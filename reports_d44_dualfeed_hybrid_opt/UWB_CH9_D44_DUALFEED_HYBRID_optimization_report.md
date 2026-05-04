# D44 双馈正交贴片 / 90 度混合网络真实匹配结构优化报告

## 设计目标

- 7.738 / 7.9855 / 8.233 GHz 三个频点内，最差自反射 `Sii <= -10.0 dB`。
- 端口隔离度 `>= 15.0 dB`。
- FOV 覆盖包络最小增益 `>= -5.0 dBi`。
- 在选定 FOV 内轴比 `AxialRatioValue <= 3.0 dB`；若未达标，则记录本轮最优幅相平衡结果。

## 最佳候选

- 候选名称：`dualfeed_probe_reference_3p3`
- 拓扑类型：`dualfeed`
- 选择原因：上一轮最佳探针/焊盘双馈结果，作为本轮真实馈电网络对照。
- 是否满足全部目标：`否`
- 本轮新增结构：边缘微带馈线/匹配段、开路匹配支节、端口间微带隔离枝节、局部缺陷地槽，以及混合器输出端独立匹配宽度。

## 几何参数

- `patch_side_mm`: `9.150`
- `feed_offset_u_mm`: `3.300`
- `port_width_mm`: `0.700`
- `feed_pad_radius_mm`: `0.420`
- `isolation_slot_length_mm`: `10.000`
- `isolation_slot_width_mm`: `0.420`
- `microstrip_feed_enabled`: `0.000`
- `microstrip_feedline_length_mm`: `2.000`
- `microstrip_feedline_width_mm`: `0.600`
- `microstrip_match_length_mm`: `0.850`
- `microstrip_match_width_mm`: `0.420`
- `microstrip_stub_length_mm`: `0.000`
- `microstrip_stub_width_mm`: `0.240`
- `microstrip_stub_offset_mm`: `0.750`
- `neutralization_branch_enabled`: `0.000`
- `neutralization_branch_width_mm`: `0.180`
- `neutralization_branch_offset_mm`: `1.150`
- `local_dgs_enabled`: `0.000`
- `local_dgs_length_mm`: `4.800`
- `local_dgs_width_mm`: `0.280`
- `local_dgs_offset_mm`: `1.150`

## 核心仿真指标

- 最差回波损耗：`-8.57 dB`，对应表达式 `dB(S(P3A:1,P3A:1))`
- 最差端口耦合：`-12.44 dB`，对应表达式 `dB(S(P1B:1,P1A:1))`
- 对应隔离度：`12.44 dB`
- 覆盖包络最小增益：`-7.99 dBi`
- CP 合格包络最大轴比：`10.15 dB`
- CP 合格包络最小增益：`-19.55 dBi`
- CP 合格包络最小覆盖率：`48.6%`

## 最佳源幅相平衡

- B 馈电幅度：`1.000`，相对于 A 馈电。
- B 馈电相位：`-105.0 deg`，相对于 A 馈电。
- 平衡阵列最小增益：`-14.72 dBi`
- 平衡阵列最大轴比：`1046.40 dB`
- 平衡阵列最小 CP 覆盖率：`29.9%`

## 最佳真实匹配/隔离结构候选

- 候选名称：`dualfeed_edge_stub_1p10`
- 拓扑类型：`dualfeed`
- 评分：`63.44`
- 最差回波损耗：`-6.76 dB`
- 隔离度：`10.41 dB`
- 微带馈电网络：`启用`
- 端口间隔离枝节：`未启用`
- 局部 DGS：`未启用`
- 说明：延长开路匹配支节，观察支节电纳增强后的 Sii 与隔离变化。
- 结论：当前真实结构候选尚未超过探针/焊盘参考解，说明引入网络后需要重新做贴片边长、馈入位置和特性阻抗的联合细扫。

## S 参数筛选排名

| 排名 | 候选 | 拓扑 | 评分 | 最差 Sii | 隔离度 | 说明 |
| ---: | --- | --- | ---: | ---: | ---: | --- |
| 1 | dualfeed_probe_reference_3p3 | dualfeed | 25.61 | -8.57 dB | 12.44 dB | 上一轮最佳探针/焊盘双馈结果，作为本轮真实馈电网络对照。 |
| 2 | dualfeed_edge_stub_1p10 | dualfeed | 63.44 | -6.76 dB | 10.41 dB | 延长开路匹配支节，观察支节电纳增强后的 Sii 与隔离变化。 |
| 3 | dualfeed_edge_stub_0p75 | dualfeed | 67.35 | -6.54 dB | 10.37 dB | 在边缘微带馈线上加入短开路支节，用支节电纳补偿端口匹配。 |
| 4 | dualfeed_edge_match_l2p1_w0p65 | dualfeed | 67.60 | -6.48 dB | 10.54 dB | 扫描更长、更宽的可调微带馈线，检查输入阻抗向 50 欧姆移动的趋势。 |
| 5 | hybrid_output_match_l1p8 | hybrid | 68.42 | -6.45 dB | 10.45 dB | 90 度混合器输出端改为可调微带匹配段，输出段宽度独立于端口宽度。 |
| 6 | dualfeed_edge_match_l1p8_w0p55 | dualfeed | 69.03 | -6.41 dB | 10.46 dB | 把双馈端口升级为边缘微带馈线，采用较短匹配段以改善端口回波。 |
| 7 | hybrid_narrow_output_match | hybrid | 72.13 | -6.27 dB | 10.26 dB | 收窄 90 度混合器输出匹配段，测试较高特性阻抗输出线对幅相平衡的影响。 |
| 8 | hybrid_output_stub_branch | hybrid | 124.32 | -3.93 dB | 6.80 dB | 在混合器输出匹配段上加入开路支节和 A/B 端口间隔离枝节，兼顾幅相平衡与隔离。 |
| 9 | dualfeed_branch_w0p16_o0p85 | dualfeed | 129.55 | -3.75 dB | 6.24 dB | 在 A/B 双馈端口之间加入高阻微带隔离枝节，尝试抵消同贴片双端口耦合。 |
| 10 | dualfeed_branch_dgs_len4p4 | dualfeed | 133.84 | -3.36 dB | 6.75 dB | 组合端口间微带隔离枝节与局部缺陷地槽，同时压制近场耦合和地电流绕射。 |

## 结论

- 本轮是否完全达标：`否`。
- 当前主要瓶颈：最差回波损耗为 `-8.57 dB`，隔离度为 `12.44 dB`，CP 合格包络最大轴比为 `10.15 dB`。
- 本轮已经把建议中的真实匹配/隔离结构参数化并纳入快速筛选；若仍未完全达标，下一轮应围绕最佳候选继续细扫隔离枝节长度、DGS 位置、混合器输出段宽度和源幅相平衡。

## 输出文件

- 优化历史：`D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_dualfeed_hybrid_opt\UWB_CH9_D44_DUALFEED_HYBRID_optimization_history.csv`
- 源幅相扫描：`D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_dualfeed_hybrid_opt\UWB_CH9_D44_DUALFEED_HYBRID_source_balance.csv`
- 最佳结果 JSON：`D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_dualfeed_hybrid_opt\UWB_CH9_D44_DUALFEED_HYBRID_best.json`
- 最终拓扑报告目录：`D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_dualfeed_cp`
