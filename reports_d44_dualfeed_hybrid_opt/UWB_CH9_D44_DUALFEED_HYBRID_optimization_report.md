# D44 双馈正交贴片 / 90 度混合网络真实匹配结构优化报告

## 设计目标

- 7.738 / 7.9855 / 8.233 GHz 三个频点内，最差自反射 `Sii <= -10.0 dB`。
- 端口隔离度 `>= 15.0 dB`。
- FOV 覆盖包络最小增益 `>= -5.0 dBi`。
- 在选定 FOV 内轴比 `AxialRatioValue <= 3.0 dB`；若未达标，则记录本轮最优幅相平衡结果。

## 本轮细扫范围

- 上一轮：隔离枝节长度 `0.65 / 1.05 / 1.35 mm`，DGS 位置 `0.75 / 1.25 mm`，90 度混合器输出段宽度 `0.28 / 0.32 / 0.40 / 0.46 mm`。
- 本轮：新增真实微带馈线边缘馈入偏移 `0.25 / 0.50 mm`，并联动贴片边长 `9.05 / 9.15 / 9.25 / 9.35 / 9.45 mm`。
- 本轮：围绕 `DGS offset 0.55-0.95 mm` 与开路支节 `1.05-1.25 mm` 做组合筛选，重点观察匹配接近 `-10 dB` 时隔离度是否还能保持。
- 源幅相平衡：B 端幅度 `0.90-1.10`、相位 `-120 deg` 到 `-75 deg`，围绕上一轮 `-105 deg` 做细扫。
- `dualfeed_fine_branch_len1p35_dgs_o0p85` 在 AEDT 保存/求解阶段卡住，已停止该单个组合候选，未纳入排名；本轮 Full 远场重评估在源幅相后半段超时，报告保留上一轮完整 FOV 指标并更新 S 参数筛选结论。

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

- 候选名称：`dualfeed_link_p9p25_shift0p50_dgs0p65_stub1p25`
- 拓扑类型：`dualfeed`
- 评分：`35.08`
- 最差回波损耗：`-9.76 dB`
- 隔离度：`5.23 dB`
- 微带馈电网络：`启用`
- 端口间隔离枝节：`未启用`
- 局部 DGS：`启用`
- 说明：贴片略放大，馈线偏移 0.50 mm，支节 1.25 mm，测试较长支节与内侧 DGS 的组合。
- 结论：当前真实结构候选尚未超过探针/焊盘参考解，说明引入网络后需要重新做贴片边长、馈入位置和特性阻抗的联合细扫。

## S 参数筛选排名

| 排名 | 候选 | 拓扑 | 评分 | 最差 Sii | 隔离度 | 说明 |
| ---: | --- | --- | ---: | ---: | ---: | --- |
| 1 | dualfeed_probe_reference_3p3 | dualfeed | 25.61 | -8.57 dB | 12.44 dB | 上一轮最佳探针/焊盘双馈结果，作为本轮真实馈电网络对照。 |
| 2 | dualfeed_link_p9p25_shift0p50_dgs0p65_stub1p25 | dualfeed | 35.08 | -9.76 dB | 5.23 dB | 贴片略放大，馈线偏移 0.50 mm，支节 1.25 mm，测试较长支节与内侧 DGS 的组合。 |
| 3 | dualfeed_link_p9p35_shift0p50_dgs0p95_stub1p25 | dualfeed | 36.51 | -9.79 dB | 4.75 dB | 贴片继续放大，馈线偏移 0.50 mm，DGS 外移至 0.95 mm，验证较弱 DGS 与长支节组合。 |
| 4 | dualfeed_link_p9p25_shift0p25_dgs0p85_stub1p10 | dualfeed | 43.84 | -8.78 dB | 7.05 dB | 贴片略放大，馈线偏移 0.25 mm，DGS 外移到 0.85 mm，观察谐振下移后的匹配恢复。 |
| 5 | dualfeed_link_p9p35_shift0p25_dgs0p75_stub1p15 | dualfeed | 50.72 | -8.49 dB | 6.52 dB | 贴片继续放大，馈线偏移 0.25 mm，DGS offset=0.75 mm，支节 1.15 mm，检查谐振频移趋势。 |
| 6 | dualfeed_fine_dgs_o0p75 | dualfeed | 53.46 | -7.35 dB | 10.48 dB | 不加端口间隔离枝节，仅把 DGS 位置向贴片中心侧移动到 0.75 mm，隔离地电流但减少端口扰动。 |
| 7 | dualfeed_fine_dgs_o1p25 | dualfeed | 55.52 | -7.29 dB | 10.25 dB | 不加端口间隔离枝节，仅把 DGS 位置外移到 1.25 mm，测试较弱地槽耦合对回波的影响。 |
| 8 | dualfeed_link_p9p45_shift0p50_dgs0p85_stub1p20 | dualfeed | 55.82 | -8.59 dB | 4.83 dB | 贴片最大化到可用板边界附近，馈线偏移 0.50 mm，并用 DGS 0.85 mm 与 1.20 mm 支节做联合补偿。 |
| 9 | dualfeed_fine_stub_1p25 | dualfeed | 63.24 | -6.89 dB | 9.95 dB | 围绕最佳真实结构候选继续延长开路匹配支节到 1.25 mm，检查匹配电纳细调效果。 |
| 10 | dualfeed_edge_stub_1p10 | dualfeed | 63.44 | -6.76 dB | 10.41 dB | 延长开路匹配支节，观察支节电纳增强后的 Sii 与隔离变化。 |

## 结论

- 本轮是否完全达标：`否`。
- 当前主要瓶颈：最差回波损耗为 `-8.57 dB`，隔离度为 `12.44 dB`，CP 合格包络最大轴比为 `10.15 dB`。
- 真实结构联动细扫中，`dualfeed_link_p9p25_shift0p50_dgs0p65_stub1p25` 的综合评分最低：最差 Sii 约 `-9.76 dB`，已经接近 `-10 dB` 目标，但隔离度下降到约 `5.23 dB`。
- 同类趋势中，`patch_side=9.35 mm / feed_offset=0.50 mm / DGS offset=0.95 mm / stub=1.25 mm` 可得到约 `-9.79 dB` 的最差 Sii，但隔离度进一步降至约 `4.75 dB`。
- 源幅相细扫把最佳平衡点更新为 `amp_b=0.95 / phase_b=-97.5 deg`，轴比相对上一轮明显下降，但仍未接近 `3 dB` 圆极化目标。
- 下一轮建议：保留 `patch_side=9.25-9.35 mm / feed_offset=0.50 mm / stub=1.20-1.30 mm` 的匹配方向，同时必须引入非直连式隔离方案，例如弱耦合开路隔离线、接地过孔栅栏或重新分离 A/B 馈线出口，否则匹配接近目标时隔离会塌陷。

## 输出文件

- 优化历史：`D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_dualfeed_hybrid_opt\UWB_CH9_D44_DUALFEED_HYBRID_optimization_history.csv`
- 源幅相扫描：`D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_dualfeed_hybrid_opt\UWB_CH9_D44_DUALFEED_HYBRID_source_balance.csv`
- 最佳结果 JSON：`D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_dualfeed_hybrid_opt\UWB_CH9_D44_DUALFEED_HYBRID_best.json`
- 最终拓扑报告目录：`D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_dualfeed_cp`
