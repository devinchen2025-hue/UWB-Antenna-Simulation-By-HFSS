# D44 双极化 XY 镜像馈线、阻抗变换与方向图对称化优化报告

## 本轮目标

- 在上一轮真实边馈网络基础上，引入二级阶梯阻抗变换，降低贴片边缘过强加载。
- 将每个阵元的 X/Y 边馈线按阵元位置镜像到外侧象限，减少阵列方向图不对称。
- 扫描贴片边长、二级变换段宽度、馈线偏移、短隔离枝节、开路支节和轻量 DGS。
- 后端评估加入每阵元 2x2 复数幅相标定矩阵，用于衡量接收端双通道可校准上限。
- 目标：最差回波 `<= -10.0 dB`，同阵元 X/Y 隔离 `>= 15.0 dB`，X/Y 回波差 `<= 0.5 dB`，方向图镜像对称 RMS `<= 3.0 dB`，标定后 PDOA 平均 RMS `<= 10.0 deg`。

## 方法说明

- S 参数阶段优先筛选镜像馈线和阻抗变换候选，探针/焊盘参考解只作为对照。
- 完整复核阶段提取嵌入远场，分别计算未标定双极化向量相关 PDOA 与标定后 2x2 向量相关 PDOA。
- 方向图对称性通过 E1/E3、E2/E4 在方位镜像点的双通道向量幅度差计算，指标越小代表阵元方向图越一致。
- 标定矩阵来自线极化 `0 / 45 / 90 / 135 deg` 的嵌入远场样本最小二乘拟合；它代表后端接收机幅相标定能力，不等同于纯硬件指标改善。

## S 参数筛选排名

| 排名 | 候选 | 真实网络 | 评分 | 最差Sii | X回波 | Y回波 | 回波差 | 同阵元X/Y隔离 | 说明 |
| ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | `probe_ref_pad0p28` | 否 | 20.25 | -8.87 dB | -9.02 dB | -8.87 dB | 0.15 dB | 12.76 dB | 上一轮小焊盘探针/焊盘最优解，仅作为真实微带网络的对照基线。 |
| 2 | `mirror_patch9p25_xform_mid` | 是 | 44.02 | -7.82 dB | -7.82 dB | -8.10 dB | 0.28 dB | 9.58 dB | 略放大贴片边长，验证镜像边馈后谐振点是否需要下移。 |
| 3 | `mirror_xform_wide_0p38_0p54` | 是 | 47.59 | -6.64 dB | -6.71 dB | -6.64 dB | 0.06 dB | 10.69 dB | 较宽入口和二级变换段，测试阻抗变换对回波损耗的上限改善。 |
| 4 | `mirror_eq_l1p70_m0p75` | 是 | 49.41 | -6.29 dB | -6.38 dB | -6.29 dB | 0.09 dB | 10.87 dB | 保持上一轮阻抗尺寸，仅将每个阵元的边馈线镜像到外侧象限，观察方向图对称性收益。 |
| 5 | `mirror_xform_short_0p30_0p46` | 是 | 49.58 | -6.41 dB | -6.54 dB | -6.41 dB | 0.13 dB | 10.60 dB | 边馈使用窄高阻入口加二级阻抗变换，减少贴片边缘过强加载。 |
| 6 | `mirror_patch9p05_xform_mid` | 是 | 49.73 | -5.62 dB | -5.62 dB | -5.67 dB | 0.05 dB | 11.85 dB | 略缩小贴片边长，补偿镜像边馈和阻抗变换引入的边缘电容加载。 |
| 7 | `edge_unmirror_prev_l1p70` | 是 | 49.95 | -6.36 dB | -6.36 dB | -6.66 dB | 0.30 dB | 10.43 dB | 上一轮真实边馈网络最优解，不启用镜像馈线，作为本轮真实网络基线。 |
| 8 | `mirror_xform_mid_0p34_0p50` | 是 | 50.08 | -6.39 dB | -6.59 dB | -6.39 dB | 0.20 dB | 10.64 dB | 中等高阻入口加 0.50 mm 二级变换段，兼顾匹配和线宽可制造性。 |
| 9 | `mirror_offset0p15_xform_mid` | 是 | 60.68 | -6.38 dB | -6.71 dB | -6.38 dB | 0.33 dB | 8.41 dB | 镜像馈线基础上加入 0.15 mm 共同横向偏移，补偿端口片和馈线不对称。 |
| 10 | `mirror_branch0p55_xform_mid` | 是 | 74.68 | -4.57 dB | -4.91 dB | -4.57 dB | 0.34 dB | 8.35 dB | 轻微同阵元隔离枝节随镜像象限布置，优先不破坏匹配。 |

## 完整复核结果

| 候选 | 综合评分 | 最差Sii | 同阵元X/Y隔离 | 回波差 | 方向图对称RMS | 幅差RMS | 相位离散RMS | 未标定PDOA均值RMS | 标定后PDOA均值RMS | 标定后95分位 | 标定后最大漂移 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `probe_ref_pad0p28` | 129.62 | -8.87 dB | 12.76 dB | 0.15 dB | 11.23 dB | 5.48 dB | 48.54 deg | 53.38 deg | 53.82 deg | 81.43 deg | 179.96 deg |
| `mirror_patch9p25_xform_mid` | 170.99 | -7.82 dB | 9.58 dB | 0.28 dB | 11.56 dB | 5.08 dB | 74.77 deg | 86.84 deg | 51.32 deg | 80.73 deg | 179.98 deg |
| `mirror_xform_wide_0p38_0p54` | 173.84 | -6.64 dB | 10.69 dB | 0.06 dB | 11.51 dB | 5.08 dB | 75.21 deg | 86.21 deg | 50.89 deg | 80.66 deg | 179.99 deg |
| `mirror_eq_l1p70_m0p75` | 175.66 | -6.29 dB | 10.87 dB | 0.09 dB | 11.46 dB | 4.95 dB | 75.62 deg | 86.42 deg | 51.02 deg | 80.30 deg | 179.96 deg |

## 最优候选

- 候选：`mirror_patch9p25_xform_mid`
- 是否真实馈电网络：`是`
- 说明：略放大贴片边长，验证镜像边馈后谐振点是否需要下移。
- AEDT 工程：`D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\UWB_CH9_Diamond_CP_Array_D44_DUALPOL_XY.aedt`
- 最差回波：`-7.82 dB`
- X/A 最差回波：`-7.82 dB`
- Y/B 最差回波：`-8.10 dB`
- X/Y 回波差：`0.28 dB`
- 同阵元 X/Y 隔离：`9.58 dB`
- 同馈跨阵元隔离：`15.28 dB`
- 方向图镜像对称 RMS：`11.56 dB`
- 方向图镜像对称最大差：`42.96 dB`
- X/Y 幅度 RMS 差：`5.08 dB`
- X/Y 相位离散 RMS：`74.77 deg`
- 未标定双极化向量 PDOA 平均 RMS：`86.84 deg`
- 2x2 标定后 PDOA 平均 RMS：`51.32 deg`
- 2x2 标定后 PDOA 95 分位：`80.73 deg`
- 2x2 标定后 PDOA 最大漂移：`179.98 deg`

## 最优几何参数

- `patch_side_mm`: `9.250`
- `feed_offset_u_mm`: `3.400`
- `feed_pad_radius_mm`: `0.280`
- `port_width_mm`: `0.500`
- `microstrip_feed_enabled`: `1.000`
- `microstrip_feed_offset_mm`: `0.000`
- `microstrip_feedline_length_mm`: `1.780`
- `microstrip_feedline_width_mm`: `0.580`
- `microstrip_match_length_mm`: `0.480`
- `microstrip_match_width_mm`: `0.340`
- `microstrip_transform2_length_mm`: `0.550`
- `microstrip_transform2_width_mm`: `0.500`
- `microstrip_feed_mirror_enabled`: `1.000`
- `microstrip_stub_length_mm`: `0.000`
- `microstrip_stub_width_mm`: `0.240`
- `microstrip_stub_offset_mm`: `0.600`
- `neutralization_branch_enabled`: `0.000`
- `neutralization_branch_length_mm`: `0.850`
- `neutralization_branch_width_mm`: `0.120`
- `neutralization_branch_offset_mm`: `0.650`
- `local_dgs_enabled`: `0.000`
- `local_dgs_length_mm`: `3.600`
- `local_dgs_width_mm`: `0.180`
- `local_dgs_offset_mm`: `0.750`
- `isolation_slot_enabled`: `1.000`
- `isolation_slot_length_mm`: `10.000`
- `isolation_slot_width_mm`: `0.420`
- `isolation_slot_inner_mm`: `3.200`

## 与上一轮真实边馈网络最优解对比

| 指标 | 上一轮 | 本轮最优 | 变化 |
| --- | ---: | ---: | ---: |
| 最差回波 | -6.36 dB | -7.82 dB | -1.45 |
| 同阵元 X/Y 隔离 | 10.43 dB | 9.58 dB | -0.85 |
| X/Y 回波差 | 0.30 dB | 0.28 dB | -0.02 |
| X/Y 幅度 RMS 差 | 5.29 dB | 5.08 dB | -0.20 |
| X/Y 相位离散 RMS | 45.66 deg | 74.77 deg | 29.11 |
| 未标定向量 PDOA 平均 RMS | 49.42 deg | 86.84 deg | 37.42 |
| 方向图镜像对称 RMS | N/A dB | 11.56 dB | N/A |

## 达标情况

- S 参数/隔离目标：`未通过`。
- X/Y 幅相一致性目标：`未通过`。
- 标定后 PDOA 稳定性目标：`未通过`。
- 方向图镜像对称性目标：`未通过`。
- 全部目标：`未通过`。

## 工程判断

- 本轮把馈线镜像和二级阻抗变换纳入真实 HFSS 几何；如果匹配改善有限，说明边馈位置仍偏离贴片等效 50 欧姆点。
- `mirror_stub0p65_xform_mid` 在一次 S 参数尝试中 AEDT 未返回有效解数据，`mirror_dgs_light_xform_mid` 未进入最终复核；这两类支节/DGS 结构需要拆成更温和的独立细扫。
- 若方向图对称性改善但 PDOA 仍漂移，下一步应重点做端口相位中心校正和每阵元独立方向图标定。
- 若方向图对称性没有改善，下一步应考虑双层过渡或叠层寄生贴片，使馈线从辐射贴片主电流区域退耦。

## 输出文件

- S 参数筛选：`D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_dualpol_mirror_symmetry_opt\UWB_CH9_D44_DUALPOL_MIRROR_SYMMETRY_sparam_screening.csv`
- 完整复核：`D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_dualpol_mirror_symmetry_opt\UWB_CH9_D44_DUALPOL_MIRROR_SYMMETRY_full_validation.csv`
- 最优未标定曲线：`D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_dualpol_mirror_symmetry_opt\UWB_CH9_D44_DUALPOL_MIRROR_SYMMETRY_best_curves.csv`
- 最优未标定汇总：`D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_dualpol_mirror_symmetry_opt\UWB_CH9_D44_DUALPOL_MIRROR_SYMMETRY_best_summary.csv`
- 最优标定后曲线：`D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_dualpol_mirror_symmetry_opt\UWB_CH9_D44_DUALPOL_MIRROR_SYMMETRY_best_calibrated_curves.csv`
- 最优标定后汇总：`D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_dualpol_mirror_symmetry_opt\UWB_CH9_D44_DUALPOL_MIRROR_SYMMETRY_best_calibrated_summary.csv`
- 最优 JSON（含每频点、每阵元 2x2 复数标定矩阵）：`D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_dualpol_mirror_symmetry_opt\UWB_CH9_D44_DUALPOL_MIRROR_SYMMETRY_best.json`
