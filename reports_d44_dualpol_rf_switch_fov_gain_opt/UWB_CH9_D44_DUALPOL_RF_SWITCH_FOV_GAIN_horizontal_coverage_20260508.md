# D44 双极化 RF-switch 水平面覆盖转向优化记录

更新时间：2026-05-08

## 本轮决策

系统必须覆盖水平面，因此停止继续围绕小型贴片扰动做细扫，改为验证独立低仰角覆盖路径：

- 板边专用寄生 IFA / 单极子式覆盖单元。
- 连接到辐射体的板边折叠辐射臂。
- 在必要时放宽外形高度到 10 mm，检查高度是否是水平面覆盖的主导杠杆。

FOV 口径保持为 HFSS `Theta=45..90 deg`、`Phi=0..360 deg`。增益目标仍为 `GainTotal` 与 `RealizedGainTotal` 均不低于 `-5 dBi`，工作态约束为 A_ON / B_ON 最差 S11 不高于 `-10 dB`。

## 新增结构

本轮在 `scripts/build_uwb_ch9_hfss_d44_topology.py` 中加入两类可参数化结构：

- `slot_coupled_board_edge_ifa_*`：带接地短路壁的寄生板边 IFA，和主贴片保留小间隙，通过近场耦合激励。
- `slot_coupled_folded_edge_arm_*`：由贴片边缘升高的折叠辐射臂，包含竖直 riser、径向段和切向段，直接把电流抬高到更适合水平面辐射的位置。

## 候选结果

| 候选 | 结构 | 高度约束 | 严格 Realized 最小值 | 覆盖 Realized 最小值 | 最差 S11 | 判定 |
| ---: | --- | ---: | ---: | ---: | ---: | --- |
| 39 | 4.6 mm 板边寄生 IFA，3.8 mm 高 | 8 mm | `-36.78 dBi` | `-21.50 dBi` | `-9.41 dB` | 不可用，增益和匹配均退化 |
| 40 | 4.5 mm 板边寄生 IFA，5.5 mm 高 | 8 mm | `-32.33 dBi` | `-20.86 dBi` | `-10.84 dB` | 匹配通过，但水平面收益不足 |
| 41 | 折叠边臂，1.8 mm 径向 / 4.0 mm 切向 / 5.2 mm 高 / 0.30 mm 宽 | 8 mm | `-23.26 dBi` | `-16.11 dBi` | `-9.89 dB` | 增益最好，但 S11 差约 0.11 dB |
| 42 | 折叠边臂升高到 7.2 mm | 10 mm | `-28.12 dBi` | `-17.11 dBi` | `-12.53 dB` | 匹配通过，但严格底值回落 |
| 43 | 41 号缩短并降高：1.6 mm / 3.8 mm / 5.0 mm / 0.30 mm | 8 mm | `-24.77 dBi` | `-16.42 dBi` | `-11.70 dB` | 匹配通过，水平面收益保留 |
| 44 | 41 号降高并窄化：1.8 mm / 4.0 mm / 5.0 mm / 0.24 mm | 8 mm | `-24.16 dBi` | `-16.08 dBi` | `-12.13 dB` | 本轮最佳工程候选 |
| 45 | 41 号变长并窄化：2.0 mm / 4.2 mm / 5.2 mm / 0.25 mm | 8 mm | `-25.61 dBi` | `-16.30 dBi` | `-12.48 dB` | 匹配通过，略弱于 44 |

## 当前最佳

按“先满足工作态 S11，再比较 FOV 增益”的工程排序，当前最佳为 44 号：

`p9p75_l5p6_w0p70_fw0p80_stub1p90_w1p00_off1p55_dstub0p70_step1p0_iso11p5_w0p55_i3p6_slit4p0_off0p45_foldededge_r1p8_t4p0_h5p2_w0p30_foldededge_r1p8_t4p0_h5p0_w0p24`

| 指标 | 结果 |
| --- | ---: |
| 严格口径最小 `GainTotal` | `-24.14 dBi` |
| 严格口径最小 `RealizedGainTotal` | `-24.16 dBi` |
| 覆盖口径最小 `GainTotal` | `-16.07 dBi` |
| 覆盖口径最小 `RealizedGainTotal` | `-16.08 dBi` |
| 工作态最差 S11 | `-12.13 dB` |
| 严格口径目标 | 未达标 |
| 覆盖口径目标 | 未达标 |
| S11 约束 | 达标 |

相比上一轮 S11 合格最佳 18 号，44 号严格 `RealizedGainTotal` 底值提升约 `2.21 dB`，覆盖口径 `RealizedGainTotal` 底值提升约 `3.62 dB`。这说明高折叠边臂确实是比寄生板边 IFA 更有效的水平面覆盖方向。

## 工程判断

- 板边寄生 IFA 没有形成有效的低仰角补偿，尤其 39 号同时破坏匹配和严格口径底值，应暂时停止这条寄生耦合路线。
- 连接式折叠边臂首次显著抬升水平面覆盖底值，且 44 号在 8 mm 外形内满足工作态 S11，是当前可继续优化的主线。
- 单纯增加到 10 mm 高度并不自动改善严格底值，42 号说明高度需要和臂宽、切向长度、馈电匹配一起协同调谐。
- 目标 `-5 dBi` 仍未达成，44 号距离严格 Realized 目标仍差约 `19.16 dB`，但方向已经从“局部扰动无效”转为“可观测的水平面收益”。

## 下一步建议

- 围绕 44 号继续做折叠边臂的局部优化：臂宽 `0.20..0.28 mm`、高度 `4.8..5.4 mm`、切向长度 `3.6..4.4 mm`。
- 同步加入馈线匹配补偿，例如微调 `slot_coupled_stub_length_mm`、`slot_coupled_step_length_mm` 和 aperture 长度，避免边臂改善覆盖时把 S11 拉坏。
- 若系统仍要求单天线端口在完整水平面接近 `-5 dBi`，建议进入多单元选择/系统级端口合成验证，因为 44 mm 圆板四阵元低剖面结构仍存在明显几何覆盖短板。

## 相关文件

- 自动报告：`reports_d44_dualpol_rf_switch_fov_gain_opt/UWB_CH9_D44_DUALPOL_RF_SWITCH_FOV_GAIN_report.md`
- 指标 JSON：`reports_d44_dualpol_rf_switch_fov_gain_opt/UWB_CH9_D44_DUALPOL_RF_SWITCH_FOV_GAIN_metrics.json`
- 候选汇总 CSV：`reports_d44_dualpol_rf_switch_fov_gain_opt/UWB_CH9_D44_DUALPOL_RF_SWITCH_FOV_GAIN_summary.csv`
- 逐端口明细 CSV：`reports_d44_dualpol_rf_switch_fov_gain_opt/UWB_CH9_D44_DUALPOL_RF_SWITCH_FOV_GAIN_source_summary.csv`
- 覆盖口径明细 CSV：`reports_d44_dualpol_rf_switch_fov_gain_opt/UWB_CH9_D44_DUALPOL_RF_SWITCH_FOV_GAIN_coverage_summary.csv`
- 最佳工程候选 AEDT：`reports_d44_dualpol_rf_switch_fov_gain_opt/UWB_CH9_D44_DUALPOL_RF_SWITCH_FOV_GAIN_44_*_A_ON_absorptive_50ohm_c0p08pf.aedt` 与 `..._B_ON_absorptive_50ohm_c0p08pf.aedt`
