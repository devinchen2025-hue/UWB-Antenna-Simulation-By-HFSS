# D44 双极化 XY 真实馈电网络与接收端标定优化报告

## 本轮目标

- 在保留独立 X/Y 双极化接收架构的前提下，引入真实双极化馈电网络。
- 两路馈线采用等长微带过渡，避免固定 90 度混合器把 X/Y 信息提前合成为单一圆极化端口。
- 扫描可调匹配段、开路匹配支节、同阵元隔离枝节与局部 DGS。
- 后端评估加入每阵元 2x2 复数幅相标定矩阵，用于衡量接收端双通道可校准上限。
- 目标：最差回波 `<= -10.0 dB`，同阵元 X/Y 隔离 `>= 15.0 dB`，X/Y 回波差 `<= 0.5 dB`，标定后 PDOA 平均 RMS `<= 10.0 deg`。

## 方法说明

- S 参数阶段优先筛选真实微带网络候选，探针/焊盘参考解只作为对照。
- 完整复核阶段提取嵌入远场，分别计算未标定双极化向量相关 PDOA 与标定后 2x2 向量相关 PDOA。
- 标定矩阵来自线极化 `0 / 45 / 90 / 135 deg` 的嵌入远场样本最小二乘拟合；它代表后端接收机幅相标定能力，不等同于纯硬件指标改善。

## S 参数筛选排名

| 排名 | 候选 | 真实网络 | 评分 | 最差Sii | X回波 | Y回波 | 回波差 | 同阵元X/Y隔离 | 说明 |
| ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | `probe_ref_pad0p28` | 否 | 20.25 | -8.87 dB | -9.02 dB | -8.87 dB | 0.15 dB | 12.76 dB | 上一轮小焊盘探针/焊盘最优解，仅作为真实微带网络的对照基线。 |
| 2 | `edge_eq_l1p70_w0p58_m0p75_w0p40` | 是 | 49.95 | -6.36 dB | -6.36 dB | -6.66 dB | 0.30 dB | 10.43 dB | 等长微带过渡参考解，匹配段宽度接近上一轮混合器输出段中值。 |
| 3 | `edge_eq_l1p78_w0p62_m0p82_w0p44` | 是 | 51.03 | -6.63 dB | -6.78 dB | -6.63 dB | 0.15 dB | 9.79 dB | 加宽并拉长等长微带过渡，测试回波改善与同阵元串扰变化。 |
| 4 | `edge_eq_l1p60_w0p50_m0p62_w0p34` | 是 | 56.76 | -5.86 dB | -5.86 dB | -6.47 dB | 0.61 dB | 9.96 dB | 两路等长短微带过渡，窄匹配段降低边缘过耦合。 |
| 5 | `edge_offset0p20_l1p70_m0p75` | 是 | 61.59 | -6.98 dB | -6.98 dB | -7.06 dB | 0.08 dB | 7.11 dB | 两路保持等长，加入 0.20 mm 横向偏移用于补偿 X/Y 边馈不对称。 |
| 6 | `edge_stub0p85_branch0p65` | 是 | 75.70 | -4.49 dB | -5.22 dB | -4.49 dB | 0.73 dB | 8.46 dB | 加入开路匹配支节和短同阵元隔离枝节，优先改善同阵元 X/Y 隔离。 |
| 7 | `edge_stub1p05_branch0p85` | 是 | 82.73 | -4.20 dB | -4.46 dB | -4.20 dB | 0.26 dB | 7.34 dB | 加长开路匹配支节并提高隔离枝节耦合长度，观察隔离收益上限。 |
| 8 | `edge_patch9p05_branch_dgs` | 是 | 84.34 | -4.66 dB | -5.27 dB | -4.66 dB | 0.61 dB | 6.37 dB | 略缩小贴片边长补偿边馈电容性加载，并保留隔离枝节/DGS。 |
| 9 | `edge_branch1p05_dgs0p65` | 是 | 89.85 | -3.60 dB | -4.29 dB | -3.60 dB | 0.69 dB | 7.01 dB | 隔离枝节叠加局部 DGS，尝试压低同阵元耦合并保持可制造尺寸。 |
| 10 | `edge_patch9p25_branch_dgs` | 是 | 91.18 | -3.09 dB | -3.47 dB | -3.09 dB | 0.38 dB | 7.43 dB | 略放大贴片边长抵消边缘馈入导致的谐振上移，同时保留真实网络。 |
| 11 | `edge_branch1p20_dgs0p85` | 是 | 97.04 | -3.16 dB | -3.64 dB | -3.16 dB | 0.48 dB | 6.14 dB | 更强隔离枝节与外移 DGS 组合，验证隔离提升是否牺牲匹配。 |

## 完整复核结果

| 候选 | 综合评分 | 最差Sii | 同阵元X/Y隔离 | 回波差 | 幅差RMS | 相位离散RMS | 未标定PDOA均值RMS | 标定后PDOA均值RMS | 标定后95分位 | 标定后最大漂移 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `edge_eq_l1p70_w0p58_m0p75_w0p40` | 133.86 | -6.36 dB | 10.43 dB | 0.30 dB | 5.29 dB | 45.66 deg | 49.42 deg | 50.85 deg | 82.47 deg | 179.82 deg |

## 最优候选

- 候选：`edge_eq_l1p70_w0p58_m0p75_w0p40`
- 是否真实馈电网络：`是`
- 说明：等长微带过渡参考解，匹配段宽度接近上一轮混合器输出段中值。
- AEDT 工程：`D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\UWB_CH9_Diamond_CP_Array_D44_DUALPOL_XY.aedt`
- 最差回波：`-6.36 dB`
- X/A 最差回波：`-6.36 dB`
- Y/B 最差回波：`-6.66 dB`
- X/Y 回波差：`0.30 dB`
- 同阵元 X/Y 隔离：`10.43 dB`
- 同馈跨阵元隔离：`17.66 dB`
- X/Y 幅度 RMS 差：`5.29 dB`
- X/Y 相位离散 RMS：`45.66 deg`
- 未标定双极化向量 PDOA 平均 RMS：`49.42 deg`
- 2x2 标定后 PDOA 平均 RMS：`50.85 deg`
- 2x2 标定后 PDOA 95 分位：`82.47 deg`
- 2x2 标定后 PDOA 最大漂移：`179.82 deg`

## 最优几何参数

- `patch_side_mm`: `9.150`
- `feed_offset_u_mm`: `3.400`
- `feed_pad_radius_mm`: `0.280`
- `port_width_mm`: `0.500`
- `microstrip_feed_enabled`: `1.000`
- `microstrip_feed_offset_mm`: `0.000`
- `microstrip_feedline_length_mm`: `1.700`
- `microstrip_feedline_width_mm`: `0.580`
- `microstrip_match_length_mm`: `0.750`
- `microstrip_match_width_mm`: `0.400`
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

## 与上一轮小焊盘最优解对比

| 指标 | 上一轮 | 本轮最优 | 变化 |
| --- | ---: | ---: | ---: |
| 最差回波 | -8.87 dB | -6.36 dB | 2.50 |
| 同阵元 X/Y 隔离 | 12.76 dB | 10.43 dB | -2.33 |
| X/Y 回波差 | 0.15 dB | 0.30 dB | 0.15 |
| X/Y 幅度 RMS 差 | 5.48 dB | 5.29 dB | -0.19 |
| X/Y 相位离散 RMS | 48.54 deg | 45.66 deg | -2.88 |
| 未标定向量 PDOA 平均 RMS | 53.38 deg | 49.42 deg | -3.96 |

## 达标情况

- S 参数/隔离目标：`未通过`。
- X/Y 幅相一致性目标：`未通过`。
- 标定后 PDOA 稳定性目标：`未通过`。
- 全部目标：`未通过`。

## 工程判断

- 本轮完成了从探针/焊盘到等长微带双通道馈电网络的结构升级，并保留 X/Y 独立接收端口。
- 如果硬件 S 参数没有明显提升，而标定后 PDOA 明显改善，说明主要矛盾已经从天线几何转向接收链路幅相一致性与标定质量。
- 如果标定后 PDOA 仍大幅漂移，下一步需要从阵元方向图对称性入手，考虑双极化贴片旋转一致化、馈线镜像布局、双层过渡或叠层寄生贴片。

## 输出文件

- S 参数筛选：`D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_dualpol_feed_network_opt\UWB_CH9_D44_DUALPOL_FEED_NETWORK_sparam_screening.csv`
- 完整复核：`D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_dualpol_feed_network_opt\UWB_CH9_D44_DUALPOL_FEED_NETWORK_full_validation.csv`
- 最优未标定曲线：`D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_dualpol_feed_network_opt\UWB_CH9_D44_DUALPOL_FEED_NETWORK_best_curves.csv`
- 最优未标定汇总：`D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_dualpol_feed_network_opt\UWB_CH9_D44_DUALPOL_FEED_NETWORK_best_summary.csv`
- 最优标定后曲线：`D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_dualpol_feed_network_opt\UWB_CH9_D44_DUALPOL_FEED_NETWORK_best_calibrated_curves.csv`
- 最优标定后汇总：`D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_dualpol_feed_network_opt\UWB_CH9_D44_DUALPOL_FEED_NETWORK_best_calibrated_summary.csv`
- 最优 JSON（含每频点、每阵元 2x2 复数标定矩阵）：`D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_dualpol_feed_network_opt\UWB_CH9_D44_DUALPOL_FEED_NETWORK_best.json`
