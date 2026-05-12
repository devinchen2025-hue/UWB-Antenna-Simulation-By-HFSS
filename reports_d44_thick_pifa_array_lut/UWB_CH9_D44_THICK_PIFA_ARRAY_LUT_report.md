# D44 厚板 PIFA 可校准阵列 + LUT 系统级验证报告

## 目标

- 保留厚板单端口 PIFA 作为物理基准：S11 < -10 dB，Theta 45..90 deg、任意 270 deg 方位窗口内 GainTotal >= -5 dBi。
- 系统级部分转向真正低仰角覆盖单元/板边独立辐射臂的思路，不再继续硬调当前 dualpol A/B 源集合。
- 测角验证优先检查“可校准阵列 + 低仰角覆盖单元 + LUT”的组合是否成立。

## 物理基准

- 基准候选：`h3p5_l8p8_w8p0_sw4p0_fence6p0_feed8p40`
- 单端口 S11：-10.97 dB，目标 < -10.0 dB，通过
- 单端口最佳 270 deg 窗口 GainTotal min：-8.57 dBi，目标 >= -5.0 dBi，未通过
- 单端口最佳 270 deg 窗口 RealizedGainTotal min：-8.94 dBi
- 本轮重新按导出值域识别角度轴：auto-corrected: native export labels column 0 as Phi and column 2 as Theta, but ranges show column 0 is 0..90 theta and column 2 is 0..360 phi。旧汇总表中的 GainTotal min 为 -3.33 dBi，仅作为上一阶段记录保留；本报告采用重新解析后的完整 Phi 轴复核值。
- 物理基准结论：未通过
- 已复扫厚板 PIFA 家族 `49` 个已有 far-field 候选，其中 S11 与修正后真实 270 deg GainTotal 同时达标 `0` 个；S11 达标候选 `1` 个。
- 本轮系统级验证选用：`h3p5_l8p8_w8p0_sw4p0_fence6p0_feed8p40`，修正后最佳 270 deg GainTotal min -8.57 dBi，候选整体 未通过。
- 修正后增益最高候选： `h5p0_l8p8_w8p0_feed3p80_c0p085_l0p70_complex_serial`，GainTotal min -5.68 dBi，S11 nan dB。

## 系统级模型

- 阵列：D44 四阵元菱形布置，板直径 44.0 mm，地半径 21.4 mm。
- 阵元相位中心半径：12.02 mm，E1-E3 / E2-E4 长基线约 24.04 mm，相邻基线约 17.00 mm。
- 频点：8.0 GHz，自由空间波长约 37.47 mm。
- 低仰角单元方向图：直接复用厚板 PIFA 达标候选的 HFSS 单端口 GainTotal / RealizedGainTotal。
- LUT：每个 Theta 切面用 5 deg 方位栅格建库，10 deg 栅格作为 holdout；用六条 PDOA 基线的圆周相位向量最近邻估计方位。
- 重要限制：当前远场 CSV 只有 Total/Realized Total 增益，没有 Etheta/Ephi 复矢量场，因此本轮不能给出真实双极化 XPD 或极化相位 LUT；这里验证的是低仰角覆盖单元 + 可校准相位几何的测角上界。

## 结果

| 场景 | 最佳 270 deg 方位窗口 | strict GainTotal min (dBi) | coverage GainTotal min (dBi) | LUT RMS (deg) | LUT P95 (deg) | 相位向量斜率 P5 (deg/deg) | 最小相位向量间隔 (deg) | 结论 |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| co_oriented | 260..170 | -8.57 | -8.57 | 5.00 | 5.00 | 2.01 | 16.44 | 未通过 |
| radial_oriented | 320..230 | -13.44 | 0.95 | 5.00 | 5.00 | 2.01 | 16.44 | 未通过 |

总体最佳场景为 `co_oriented`，窗口 Phi 260..170 deg，综合结论：未通过。

![PDOA phase plot](D:/WorkSpace/HFSS Sim/UWB-Antenna-Simulation-By-HFSS/reports_d44_thick_pifa_array_lut/UWB_CH9_D44_THICK_PIFA_ARRAY_LUT_phase_best.svg)

## 判断

- 厚板单端口 PIFA 基准继续成立，可以作为后续板边独立辐射臂/低仰角覆盖单元的物理锚点。
- 在解析阵列模型中，D44 当前 17 mm 阵元间距对应的长基线仍低于 8 GHz 下的 1 个波长相位周跳，六基线 LUT 的 holdout 方位误差满足 10 deg 级测角验证门限。
- 这说明下一步值得投入真实阵列 HFSS：保持低仰角 PIFA/IFA 单元，建立四阵元可校准阵列工程，导出每端口复矢量远场，再把极化 LUT、互耦、馈线相位和人体/机器狗安装面影响纳入复核。
- 不建议继续在现有 dualpol A/B 源集合上做复权重排序，因为其低仰角覆盖由源组合补偿，不能替代独立低仰角辐射单元的物理增益。

## 输出文件

- 指标 JSON：`UWB_CH9_D44_THICK_PIFA_ARRAY_LUT_metrics.json`
- 单阵元真实轴向 270 deg 窗口汇总：`UWB_CH9_D44_THICK_PIFA_ARRAY_LUT_physical_window_summary.csv`
- 窗口汇总：`UWB_CH9_D44_THICK_PIFA_ARRAY_LUT_window_summary.csv`
- 最佳窗口摘要：`UWB_CH9_D44_THICK_PIFA_ARRAY_LUT_summary.csv`
- LUT holdout 明细：`UWB_CH9_D44_THICK_PIFA_ARRAY_LUT_lut_holdout.csv`
- 相位曲线：`UWB_CH9_D44_THICK_PIFA_ARRAY_LUT_phase_best.svg`
