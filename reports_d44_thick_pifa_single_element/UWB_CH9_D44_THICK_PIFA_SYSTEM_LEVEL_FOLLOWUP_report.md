# D44 单端口厚板基准与系统级测角复核

## 结论先说

- 单端口厚板 PIFA 基准已达标，可作为后续系统级设计锚点。
- 现有系统级 PDOA 标定链路是可用的，但更高层的 FOV 增益与角度组合仍未达标。
- 也就是说，当前卡点不在单阵元匹配，而在阵列布置和极化组合的系统级上界。

## 单端口基准

| 候选 | S11 worst | 270deg 窗口最小 GainTotal | 结果 |
| --- | ---: | ---: | --- |
| `#36 h3p5_l8p8_w8p0_sw4p0_fence6p0_feed8p40` | `-10.970 dB` | `-3.326 dBi` | 达标 |

参考报告：

- [单端口厚板报告](D:/WorkSpace/HFSS%20Sim/UWB-Antenna-Simulation-By-HFSS/reports_d44_thick_pifa_single_element/UWB_CH9_D44_THICK_PIFA_SINGLE_ELEMENT_report.md)

## 系统级 PDOA / 极化标定

现有 RF switch 工作态与 PDOA 留出验证显示，吸收式 off-state 是可用的：

- `A_ON_absorptive_50ohm_c0p08pf`：最差 S11 `-13.36 dB`，留出 RMS `6.72 deg`
- `B_ON_absorptive_50ohm_c0p08pf`：最差 S11 `-11.01 dB`，留出 RMS `5.66 deg`
- 平均留出 RMS：`6.19 deg`
- 目标：`<= 10.0 deg`

这说明“可校准阵列 + 极化 LUT”这条测角路径本身是成立的。

参考报告：

- [PDOA 工作态报告](D:/WorkSpace/HFSS%20Sim/UWB-Antenna-Simulation-By-HFSS/reports_d44_dualpol_rf_switch_pdoa_workstate/UWB_CH9_D44_DUALPOL_RF_SWITCH_PDOA_workstate_report.md)
- [RF switch 工作态报告](D:/WorkSpace/HFSS%20Sim/UWB-Antenna-Simulation-By-HFSS/reports_d44_dualpol_rf_switch_workstate/UWB_CH9_D44_DUALPOL_RF_SWITCH_workstate_report.md)

## 系统级 FOV / 角度组合

### FOV 增益

- 最佳候选仍只有 `S11` 先过门，严格 FOV 增益未过门。
- 当前最优：严格 `GainTotal min=-24.14 dBi`，覆盖 `GainTotal min=-16.07 dBi`。
- 这与 `-5 dBi` 门限差距很大，说明阵列几何/覆盖单元还不够独立。

参考报告：

- [FOV 增益优化报告](D:/WorkSpace/HFSS%20Sim/UWB-Antenna-Simulation-By-HFSS/reports_d44_dualpol_rf_switch_fov_gain_opt/UWB_CH9_D44_DUALPOL_RF_SWITCH_FOV_GAIN_report.md)

### 角度组合

- 当前最优角度组合仍未满足 XPD、正交度、条件数和增益联合门限。
- 代表性最佳结果：Pair XPD min `-25.458 dB`，正交度 min `0.004 dB`，条件数 max `37.560 dB`，估算 GainTotal min `-30.881 dBi`。
- 结论：仅靠复权重或极化组合，无法把当前物理源集合推到达标区间。

参考报告：

- [角度组合优化报告](D:/WorkSpace/HFSS%20Sim/UWB-Antenna-Simulation-By-HFSS/reports_d44_dualpol_angle_combining_opt/UWB_CH9_D44_DUALPOL_ANGLE_COMBINING_report.md)
- [角度指标报告](D:/WorkSpace/HFSS%20Sim/UWB-Antenna-Simulation-By-HFSS/reports_d44_dualpol_angle_metrics/UWB_CH9_D44_DUALPOL_ANGLE_METRICS_report.md)

## 下一步建议

- 继续保留厚板单端口 PIFA 作为物理基准。
- 系统级部分应转向真正的低仰角覆盖单元或板边独立辐射臂，而不是继续在当前 dualpol 源集合上硬拧。
- 如果后续要做测角验证，优先验证“可校准阵列 + 低仰角覆盖单元 + 极化 LUT”的组合，而不是只提升复权重排序。

