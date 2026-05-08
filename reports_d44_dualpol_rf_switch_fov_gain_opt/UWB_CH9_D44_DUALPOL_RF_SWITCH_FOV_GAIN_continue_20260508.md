# D44 双极化 RF-switch FOV 增益继续优化记录

更新时间：2026-05-08

## 本轮目标

- 继续优化 D44 双极化 RF-switch 工作态在 CH9 频段的 FOV 增益。
- FOV 口径：HFSS `Theta=45..90 deg`、`Phi=0..360 deg`。
- 增益目标：FOV 内 `GainTotal` 与 `RealizedGainTotal` 均不低于 `-5 dBi`。
- 匹配约束：A_ON / B_ON 吸收式 off 端 `50 ohm // 0.08 pF`，选通工作态最差 S11 不高于 `-10 dB`。

## 新增结构与候选

本轮在上一轮最佳 18 号候选基础上，加入面向水平面辐射的结构变量：

- 35 号：2.4 mm 径向边缘平面臂，宽 0.30 mm。
- 36 号：3.2 mm 径向边缘平面臂，宽 0.30 mm。
- 37 号：2.0 mm 垂直边缘电流片，宽 0.50 mm。
- 38 号：3.0 mm 垂直边缘电流片，宽 0.45 mm。

## 最佳结果

本轮没有刷新全局最佳。当前最佳仍为 18 号：

`p9p75_l5p6_w0p70_fw0p80_stub1p90_w1p00_off1p55_dstub0p70_step1p0_iso11p5_w0p55_i3p6_slit4p0_off0p45`

| 指标 | 结果 |
| --- | ---: |
| 严格口径最小 `GainTotal` | `-26.26 dBi` |
| 严格口径最小 `RealizedGainTotal` | `-26.37 dBi` |
| 覆盖口径最小 `GainTotal` | `-19.69 dBi` |
| 覆盖口径最小 `RealizedGainTotal` | `-19.70 dBi` |
| 工作态最差 S11 | `-11.54 dB` |
| 严格口径目标 | 未达标 |
| 覆盖口径目标 | 未达标 |

距离 `-5 dBi` 严格 Realized 目标仍差约 `21.37 dB`。

## 本轮新增候选结果

| 候选 | 结构 | 严格 Realized 最小值 | 覆盖 Realized 最小值 | 最差 S11 | 判定 |
| ---: | --- | ---: | ---: | ---: | --- |
| 35 | 2.4 mm 径向边缘平面臂 | `-33.35 dBi` | `-20.29 dBi` | `-11.42 dB` | S11 通过，但增益显著退化 |
| 36 | 3.2 mm 径向边缘平面臂 | `-30.60 dBi` | `-20.73 dBi` | `-11.02 dB` | S11 通过，但增益退化 |
| 37 | 2.0 mm 垂直边缘电流片 | 无有效远场数据 | 无有效远场数据 | 仅生成 A_ON S 参数 | 无效候选，需复核 HFSS 远场后处理 |
| 38 | 3.0 mm 垂直边缘电流片 | `-29.99 dBi` | `-20.77 dBi` | `-11.80 dB` | S11 通过，但增益退化 |

## 工程判断

- 径向边缘平面臂没有填平水平面低谷，反而把严格 Realized 底值从 `-26.37 dBi` 拉低到 `-30.60..-33.35 dBi`。
- 3.0 mm 垂直电流片可正常求解并提取远场，但仍没有改善 FOV 底值；2.0 mm 垂直片在 A_ON 工况远场提取阶段返回空数据，未进入排名。
- 小型贴片开槽、horizon loop、边缘平面臂、垂直电流片这几类局部结构均未接近 `-5 dBi` 目标，说明当前 44 mm 圆板、低剖面四阵元贴片架构在 `Theta=90 deg` 附近存在结构性覆盖短板。

## 下一步建议

- 停止继续围绕小型局部扰动做细扫；收益已经明显不足。
- 若系统必须覆盖水平面，建议转向独立低仰角覆盖单元、板边专用单极子/IFA、或允许外形高度更高的折叠辐射臂。
- 若硬件外形不能新增低仰角单元，应重新定义验收口径，把 `Theta=90 deg` 水平面从单天线全向高增益要求中剥离，转为系统级端口/阵元选择和标定覆盖口径。

## 相关文件

- 自动汇总报告：`reports_d44_dualpol_rf_switch_fov_gain_opt/UWB_CH9_D44_DUALPOL_RF_SWITCH_FOV_GAIN_report.md`
- 指标 JSON：`reports_d44_dualpol_rf_switch_fov_gain_opt/UWB_CH9_D44_DUALPOL_RF_SWITCH_FOV_GAIN_metrics.json`
- 候选汇总 CSV：`reports_d44_dualpol_rf_switch_fov_gain_opt/UWB_CH9_D44_DUALPOL_RF_SWITCH_FOV_GAIN_summary.csv`
- 逐端口明细 CSV：`reports_d44_dualpol_rf_switch_fov_gain_opt/UWB_CH9_D44_DUALPOL_RF_SWITCH_FOV_GAIN_source_summary.csv`
- 覆盖口径明细 CSV：`reports_d44_dualpol_rf_switch_fov_gain_opt/UWB_CH9_D44_DUALPOL_RF_SWITCH_FOV_GAIN_coverage_summary.csv`
- 新增结构实现：`scripts/build_uwb_ch9_hfss_d44_topology.py`
- FOV 增益优化器：`scripts/optimize_uwb_ch9_d44_dualpol_rf_switch_fov_gain.py`
- 本轮日志：`reports_d44_dualpol_rf_switch_fov_gain_opt_run8_c35_admin.log`、`reports_d44_dualpol_rf_switch_fov_gain_opt_run8_c36_38_admin.log`、`reports_d44_dualpol_rf_switch_fov_gain_opt_run8_c38_admin.log`
