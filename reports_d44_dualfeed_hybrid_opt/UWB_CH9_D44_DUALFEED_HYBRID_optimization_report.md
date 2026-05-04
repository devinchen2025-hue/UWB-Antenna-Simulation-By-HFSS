# D44 双馈正交贴片 / 90 度混合网络真实匹配结构优化报告

## 设计目标

- 7.738 / 7.9855 / 8.233 GHz 三个频点内，最差自反射 `Sii <= -10.0 dB`。
- 端口隔离度 `>= 15.0 dB`。
- FOV 覆盖包络最小增益 `>= -5.0 dBi`。
- 在选定 FOV 内轴比 `AxialRatioValue <= 3.0 dB`；若未达标，则记录本轮最优幅相平衡结果。

## 本轮细扫范围

- 隔离枝节长度：`0.65 / 1.05 / 1.35 mm`，并与 `1.10 mm` 开路支节组合验证。
- DGS 位置：`0.75 / 1.25 mm`，用于判断局部地电流切断位置对 S 参数的影响。
- 90 度混合器输出段宽度：`0.28 / 0.32 / 0.40 / 0.46 mm`。
- 源幅相平衡：B 端幅度 `0.90-1.10`、相位 `-120 deg` 到 `-75 deg`，围绕上一轮 `-105 deg` 做细扫。
- `dualfeed_fine_branch_len1p35_dgs_o0p85` 在 AEDT 保存/求解阶段卡住，已停止该单个组合候选，未纳入排名。

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
- `neutralization_branch_length_mm`: `1.150`
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

- B 馈电幅度：`0.950`，相对于 A 馈电。
- B 馈电相位：`-97.5 deg`，相对于 A 馈电。
- 平衡阵列最小增益：`-17.11 dBi`
- 平衡阵列最大轴比：`357.65 dB`
- 平衡阵列最小 CP 覆盖率：`64.9%`

## 最佳真实匹配/隔离结构候选

- 候选名称：`dualfeed_fine_dgs_o0p75`
- 拓扑类型：`dualfeed`
- 评分：`53.46`
- 最差回波损耗：`-7.35 dB`
- 隔离度：`10.48 dB`
- 微带馈电网络：`启用`
- 端口间隔离枝节：`未启用`
- 局部 DGS：`启用`
- 说明：不加端口间隔离枝节，仅把 DGS 位置向贴片中心侧移动到 0.75 mm，隔离地电流但减少端口扰动。
- 结论：当前真实结构候选尚未超过探针/焊盘参考解，说明引入网络后需要重新做贴片边长、馈入位置和特性阻抗的联合细扫。

## S 参数筛选排名

| 排名 | 候选 | 拓扑 | 评分 | 最差 Sii | 隔离度 | 说明 |
| ---: | --- | --- | ---: | ---: | ---: | --- |
| 1 | dualfeed_probe_reference_3p3 | dualfeed | 25.61 | -8.57 dB | 12.44 dB | 上一轮最佳探针/焊盘双馈结果，作为本轮真实馈电网络对照。 |
| 2 | dualfeed_fine_dgs_o0p75 | dualfeed | 53.46 | -7.35 dB | 10.48 dB | 不加端口间隔离枝节，仅把 DGS 位置向贴片中心侧移动到 0.75 mm，隔离地电流但减少端口扰动。 |
| 3 | dualfeed_fine_dgs_o1p25 | dualfeed | 55.52 | -7.29 dB | 10.25 dB | 不加端口间隔离枝节，仅把 DGS 位置外移到 1.25 mm，测试较弱地槽耦合对回波的影响。 |
| 4 | dualfeed_fine_stub_1p25 | dualfeed | 63.24 | -6.89 dB | 9.95 dB | 围绕最佳真实结构候选继续延长开路匹配支节到 1.25 mm，检查匹配电纳细调效果。 |
| 5 | dualfeed_edge_stub_1p10 | dualfeed | 63.44 | -6.76 dB | 10.41 dB | 延长开路匹配支节，观察支节电纳增强后的 Sii 与隔离变化。 |
| 6 | dualfeed_fine_stub_1p45 | dualfeed | 65.28 | -6.65 dB | 10.41 dB | 继续把开路匹配支节延长到 1.45 mm，寻找 1.10 mm 以外的回波改善区间。 |
| 7 | dualfeed_edge_stub_0p75 | dualfeed | 67.35 | -6.54 dB | 10.37 dB | 在边缘微带馈线上加入短开路支节，用支节电纳补偿端口匹配。 |
| 8 | dualfeed_edge_match_l2p1_w0p65 | dualfeed | 67.60 | -6.48 dB | 10.54 dB | 扫描更长、更宽的可调微带馈线，检查输入阻抗向 50 欧姆移动的趋势。 |
| 9 | hybrid_output_match_l1p8 | hybrid | 68.42 | -6.45 dB | 10.45 dB | 90 度混合器输出端改为可调微带匹配段，输出段宽度独立于端口宽度。 |
| 10 | hybrid_fine_output_w0p28 | hybrid | 68.68 | -6.36 dB | 10.75 dB | 细扫 90 度混合器输出段宽度到 0.28 mm，测试高阻输出段的匹配与幅相平衡。 |

## 结论

- 本轮是否完全达标：`否`。
- 当前主要瓶颈：最差回波损耗为 `-8.57 dB`，隔离度为 `12.44 dB`，CP 合格包络最大轴比为 `10.15 dB`。
- 真实结构细扫中，`dualfeed_fine_dgs_o0p75` 是当前最佳：DGS 位置内移到 0.75 mm 后，最差 Sii 提升到约 `-7.35 dB`，但隔离度仍只有约 `10.48 dB`。
- 源幅相细扫把最佳平衡点更新为 `amp_b=0.95 / phase_b=-97.5 deg`，轴比相对上一轮明显下降，但仍未接近 `3 dB` 圆极化目标。
- 下一轮建议：暂停端口间直连式隔离枝节，优先沿 `DGS offset 0.55-0.95 mm`、开路支节 `1.05-1.35 mm` 和贴片边长/馈入位置联动方向继续细扫；混合器输出段宽度单独细扫未显示突破。

## 输出文件

- 优化历史：`D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_dualfeed_hybrid_opt\UWB_CH9_D44_DUALFEED_HYBRID_optimization_history.csv`
- 源幅相扫描：`D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_dualfeed_hybrid_opt\UWB_CH9_D44_DUALFEED_HYBRID_source_balance.csv`
- 最佳结果 JSON：`D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_dualfeed_hybrid_opt\UWB_CH9_D44_DUALFEED_HYBRID_best.json`
- 最终拓扑报告目录：`D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_dualfeed_cp`
