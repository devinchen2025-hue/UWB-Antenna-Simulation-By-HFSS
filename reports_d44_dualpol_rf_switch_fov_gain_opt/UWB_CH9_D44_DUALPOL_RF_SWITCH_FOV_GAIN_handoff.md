# D44 双极化 RF-switch FOV 增益优化交接记录

更新时间：2026-05-08 11:20 CST

## 当前优化目标

- FOV 口径：`Theta=45..90 deg`，`Phi=0..360 deg`。
- 增益目标：FOV 内 `GainTotal` 与 `RealizedGainTotal` 均不低于 `-5 dBi`。
- 工作态：A_ON / B_ON，off 端采用吸收式 `50 ohm // 0.08 pF`。
- 匹配约束：选通工作态最差 S11 需不高于 `-10 dB`。

## 当前最佳结果

最佳候选仍为 18 号：

`p9p75_l5p6_w0p70_fw0p80_stub1p90_w1p00_off1p55_dstub0p70_step1p0_iso11p5_w0p55_i3p6_slit4p0_off0p45`

| 指标 | 结果 |
| --- | ---: |
| 严格口径最小 `GainTotal` | `-26.26 dBi` |
| 严格口径最小 `RealizedGainTotal` | `-26.37 dBi` |
| 覆盖口径最小 `GainTotal` | `-19.69 dBi` |
| 覆盖口径最小 `RealizedGainTotal` | `-19.70 dBi` |
| 工作态最差 S11 | `-11.54 dB` |
| 严格 Realized 最差点 | `B_ON / P4B / 7.9855 GHz / Theta 90 deg / Phi 45 deg` |

结论：S11 过线，但 FOV 增益距离 `-5 dBi` 目标仍差约 `21.37 dB`，未达标。

## 本轮新增搜索结论

- 15-17 号 stacked parasitic：S11 变好，但 FOV 严格 Realized 退化到 `-29.33..-43.64 dBi`，不建议继续沿此方向微调。
- 18 号 4.0 mm、0.45 mm 偏置 45 度斜缝：目前唯一有效改善点，将严格 Realized 从基线约 `-28.89 dBi` 抬到 `-26.37 dBi`。
- 20-27 号斜缝微调：缩短、加宽、单轴偏移、旋转都未超过 18 号；其中 26 号 S11 最好但严格 Realized 只有 `-28.12 dBi`。
- 28-31 号 underfeed neutralizer / A-B cancel：覆盖口径个别点略动，但严格口径明显退化；28、29、30 号还出现 S11 不过线，不建议继续此小参数族。

## 下一步建议

- 不要继续只调匹配网络、斜缝长度、neutralizer 高度这类小参数，收益已经很窄。
- 下一轮应换成真正面向水平面辐射的拓扑：边缘寄生辐射臂、折叠单极子、垂直电流支路，或独立低仰角覆盖单元。
- 如果系统允许按方位选择端口/阵元，优先把目标拆成“覆盖口径”和“单端严格口径”两条验收线；当前结构覆盖口径仍在 `-19.5..-19.7 dBi` 附近，说明仅靠端口选择也远不够。

## 关键文件

- 自动中文报告：`reports_d44_dualpol_rf_switch_fov_gain_opt/UWB_CH9_D44_DUALPOL_RF_SWITCH_FOV_GAIN_report.md`
- 指标 JSON：`reports_d44_dualpol_rf_switch_fov_gain_opt/UWB_CH9_D44_DUALPOL_RF_SWITCH_FOV_GAIN_metrics.json`
- 候选汇总 CSV：`reports_d44_dualpol_rf_switch_fov_gain_opt/UWB_CH9_D44_DUALPOL_RF_SWITCH_FOV_GAIN_summary.csv`
- 逐端口明细 CSV：`reports_d44_dualpol_rf_switch_fov_gain_opt/UWB_CH9_D44_DUALPOL_RF_SWITCH_FOV_GAIN_source_summary.csv`
- 覆盖口径明细 CSV：`reports_d44_dualpol_rf_switch_fov_gain_opt/UWB_CH9_D44_DUALPOL_RF_SWITCH_FOV_GAIN_coverage_summary.csv`
- 优化脚本：`scripts/optimize_uwb_ch9_d44_dualpol_rf_switch_fov_gain.py`
- 本轮运行日志：`reports_d44_dualpol_rf_switch_fov_gain_opt_run4.log` 到 `reports_d44_dualpol_rf_switch_fov_gain_opt_run7.log`
