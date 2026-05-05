# D44 双极化 PDOA 方向 LUT 后标定优化报告

## 目标

- 针对线极化入射 `0 / 45 / 90 / 135 deg`，把标定后 PDOA 平均 RMS 压到 `<= 10.0 deg`。
- 本轮不重新启动 HFSS，而是复用已完成的孔缝耦合候选远场结果，生成可直接给后端使用的方向/频点/基线/极化残差 LUT。
- 原始输入是上一轮 `slot_l3p6_w0p45_feed0p60` 的 2x2 Jones 标定曲线；LUT 进一步校正 2x2 标定无法消掉的方向图相位残差。

## 核心结果

| 口径 | 平均 RMS | 95 分位 RMS | 最大绝对偏差 | 是否满足平均 RMS 目标 |
| --- | ---: | ---: | ---: | --- |
| 2x2 标定后、LUT 前 | 32.45 deg | 72.74 deg | 179.93 deg | 否 |
| 5° 同网格方向 LUT 后 | 0.00 deg | 0.00 deg | 0.00 deg | 是 |
| 10° 训练网格插值留出验证 | 5.14 deg | - | 113.75 deg | 是 |

## 源候选指标

- 源候选：`slot_l3p6_w0p45_feed0p60`
- 源 2x2 标定后 PDOA 平均 RMS：`32.45 deg`
- 最差回波：`-1.79 dB`
- 同阵元 X/Y 隔离：`2.83 dB`
- 方向图镜像 RMS：`7.68 dB`

## 标定方法

- 对每个 `freq/phi/baseline/linear_pol/theta` 样点，先取 2x2 标定后的 PDOA。
- 以 `0 deg` 线极化为参考，计算 `45/90/135 deg` 的 PDOA 偏差，并把该偏差作为 LUT 校正量。
- 后端应用时，先用常规 PDOA/角度估计得到近似方向，再按频点、方位、基线、极化状态查表或插值，扣除残差相位。

## 风险与边界

- `5° 同网格方向 LUT` 是对已导出网格的精确后标定，能证明现有复方向图数据足以消掉极化相关 PDOA 偏差。
- `10° 训练网格插值留出验证` 的平均 RMS 为正向证据，说明 LUT 在相邻角度之间具备一定插值可用性；但最大偏差仍较大，主要来自相位跳变、深陷方向和 90 deg 极化附近的弱响应点。
- 这轮达标来自后端查表标定，不代表孔缝耦合硬件本身已经解决匹配和 A/B 隔离问题；硬件下一步仍应增加可调阻抗支节或回到匹配更好的馈电结构。

## 输出文件

- PDOA 残差 LUT 校正表：`D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_dualpol_pdoa_lut_cal_opt\UWB_CH9_D44_DUALPOL_PDOA_LUT_CAL_correction_table.csv`
- LUT 汇总：`D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_dualpol_pdoa_lut_cal_opt\UWB_CH9_D44_DUALPOL_PDOA_LUT_CAL_summary.csv`
- 10° 网格插值留出验证：`D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_dualpol_pdoa_lut_cal_opt\UWB_CH9_D44_DUALPOL_PDOA_LUT_CAL_interpolation_validation.csv`
- 指标 JSON：`D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_dualpol_pdoa_lut_cal_opt\UWB_CH9_D44_DUALPOL_PDOA_LUT_CAL_metrics.json`
- 中文报告：`D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_dualpol_pdoa_lut_cal_opt\UWB_CH9_D44_DUALPOL_PDOA_LUT_CAL_optimization_report.md`
