# D44 水平面覆盖低仰角结构优化记录

## 本轮目标

上一轮确认候选 53 是 S11 通过条件下的水平覆盖最优点，但相比候选 44 只提升约 0.106 dB，仍远低于 -5 dBi 系统目标。本轮从候选 53 出发，转向更明确的低仰角覆盖结构：

- 板边专用 IFA：增加偏置短路支路，观察能否形成独立低仰角辐射模式。
- 更高折叠辐射臂：放宽外形高度到 10 mm，验证高度是否是水平面覆盖瓶颈。
- 偏置垂直窄壁：在 folded arm 旁增加紧凑单极子式辅助电流支路。

## 已完成候选

| 候选 | 结构意图 | 严格 Realized 最小值 | 覆盖 Realized 最小值 | 最差 S11 | 结论 |
| ---: | --- | ---: | ---: | ---: | --- |
| 53 | 上轮覆盖最优基准 | -24.255904 dBi | -15.976604 dBi | -12.614198 dB | 覆盖基准 |
| 55 | folded arm + 正偏置板边 IFA | -32.093730 dBi | -17.650946 dBi | -9.299152 dB | 覆盖和匹配均退化 |
| 56 | folded arm + 负偏置板边 IFA | -24.719372 dBi | -16.843140 dBi | -9.093485 dB | 镜像偏置仍未过 S11 |
| 57 | 10 mm 高度、短高 IFA | -26.331874 dBi | -17.900725 dBi | -7.408632 dB | 高 IFA 耦合过强 |
| 58 | 10 mm 高度、窄高 folded arm | -25.753769 dBi | -17.406633 dBi | -11.301495 dB | S11 通过但覆盖退化 |
| 60 | folded arm + 偏置垂直窄壁 | -25.129556 dBi | -15.954040 dBi | -10.047787 dB | 当前覆盖口径最优 |

候选 59 为反向 folded arm。该点在 A_ON 后处理阶段卡住，模式与候选 54 的 PyAEDT 后处理卡顿相同；未写入 summary/source/coverage CSV，半成品文件已清理，本轮统计不采用。

## 当前最优

- 严格口径最优仍为候选 44：严格 Realized 最小值 -24.155444 dBi，覆盖 Realized 最小值 -16.082634 dBi，最差 S11 -12.127201 dB。
- 水平覆盖口径最优更新为候选 60：覆盖 Realized 最小值 -15.954040 dBi，严格 Realized 最小值 -25.129556 dBi，最差 S11 -10.047787 dB。
- 候选 60 相比候选 53 的覆盖 Realized 提升 0.022564 dB，但严格 Realized 下降 0.873652 dB，S11 余量仅约 0.048 dB。

## 工程判断

板边 IFA 直接叠加在现有 folded arm 周边会重塑原模式，而不是形成温和的独立覆盖补偿。55/56/57 都同时损伤覆盖和匹配，说明该 IFA 需要独立馈电、隔离距离或不同接地点，不能作为当前贴片边缘的简单寄生附件。

单纯提高 folded arm 高度也没有打开水平面覆盖瓶颈。58 在 10 mm 高度下仍退到 -17.41 dBi，说明现有耦合路径的电流分布才是主要限制，而不是外形高度单一变量。

60 的偏置垂直窄壁是本轮唯一有效方向，但提升只有 0.023 dB，且 S11 几乎贴线。它可以作为“低风险覆盖补偿”继续小步收敛，但不能改变大方向判断：若系统必须实质覆盖水平面，需要转向独立低仰角覆盖单元或真实板边馈电单极子/IFA，而不是继续围绕当前 slot-coupled patch 做寄生微调。

## 输出文件

- 自动汇总：`reports_d44_dualpol_rf_switch_fov_gain_opt/UWB_CH9_D44_DUALPOL_RF_SWITCH_FOV_GAIN_summary.csv`
- 覆盖明细：`reports_d44_dualpol_rf_switch_fov_gain_opt/UWB_CH9_D44_DUALPOL_RF_SWITCH_FOV_GAIN_coverage_summary.csv`
- 逐端口明细：`reports_d44_dualpol_rf_switch_fov_gain_opt/UWB_CH9_D44_DUALPOL_RF_SWITCH_FOV_GAIN_source_summary.csv`
- 自动报告：`reports_d44_dualpol_rf_switch_fov_gain_opt/UWB_CH9_D44_DUALPOL_RF_SWITCH_FOV_GAIN_report.md`
- 本轮日志：`reports_d44_dualpol_rf_switch_fov_gain_opt_run12_c55_60.out.log`、`reports_d44_dualpol_rf_switch_fov_gain_opt_run12b_c60.out.log`
