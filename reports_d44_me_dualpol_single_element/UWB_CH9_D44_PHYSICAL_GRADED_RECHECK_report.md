# D44 物理分级低仰角单元复核报告

## 目标

- 验证路径：从同相位中心双模式尝试，转向两个物理分离但可校准的低仰角 PIFA/IFA 单元。
- 判据：单源 `S11 <= -10 dB`，Theta `45..90 deg` 内存在连续 `270 deg` 方位窗口，且 `GainTotal >= -5 dBi`。
- 复核范围：在 `UWB_CH9_D44_ME_DUALPOL_SINGLE_ELEMENT_summary.csv` 中重点复核 candidate 18-25 的物理分离镜像/平行 PIFA 组合。

## 物理分级结果

| 分级 | 方案 | 结论 |
| --- | --- | --- |
| 0 | 已有厚板单 PIFA 基准 | 单端口可达标，candidate 36 曾达到 `S11=-10.970 dB`、低仰角 270 deg 窗口 `GainTotal min=-3.326 dBi`。 |
| 1 | 同相位中心电-磁/交叉 PIFA 双模式 | 双端口低仰角增益和端口匹配无法同时达标。 |
| 2 | 两个物理分离但可校准低仰角单元 | 比同相位中心方案更接近目标，但本轮 candidate 18-25 仍未同时满足两端口 S11 与增益门限。 |

## 物理分离候选对比

| Candidate | 方案 | P1A S11 (dB) | P1A Gain min (dBi) | P1B S11 (dB) | P1B Gain min (dBi) | 结论 |
| ---: | --- | ---: | ---: | ---: | ---: | --- |
| 18 | `mirror_pifa_h3p5_l8p8_sep17p0_feed8p40` | -8.396 | -7.489 | -8.259 | -7.034 | 未达标 |
| 19 | `mirror_pifa_h3p5_l8p8_sep19p0_feed8p40` | -9.123 | -6.945 | -9.543 | -7.066 | 当前最均衡，未达标 |
| 20 | `parallel_pifa_h3p5_l8p8_sep17p0_feed8p40` | -8.213 | -8.400 | -10.503 | -7.278 | P1B 匹配达标，增益未达标 |
| 21 | `mirror_pifa_h4p0_l8p8_sep17p0_feed8p40` | -4.894 | -7.969 | -4.995 | -7.769 | 未达标 |
| 22 | `parallel_pifa_h5p8_l8p6_sep17p0_feed7p80` | -3.677 | -8.204 | -2.413 | -13.241 | 未达标 |
| 23 | `parallel_pifa_h6p5_l8p4_sep17p0_feed7p90` | -3.078 | -9.682 | -2.086 | -12.649 | 未达标 |
| 24 | `mirror_pifa_h5p8_l8p6_sep17p0_feed7p80` | -2.429 | -10.787 | -2.407 | -10.915 | 未达标 |
| 25 | `mirror_pifa_h6p5_l8p4_sep17p0_feed7p90` | -1.949 | -11.741 | -1.988 | -11.128 | 未达标 |

## 当前最佳

- 最佳物理分离候选：candidate 19 `mirror_pifa_h3p5_l8p8_sep19p0_feed8p40`。
- P1A：`S11=-9.123 dB`，270 deg 窗口 `GainTotal min=-6.945 dBi`。
- P1B：`S11=-9.543 dB`，270 deg 窗口 `GainTotal min=-7.066 dBi`。
- 与目标差距：S11 约差 `0.46..0.88 dB`，增益约差 `1.95..2.07 dB`。

## 工程判断

- 物理分离确实改善了低仰角覆盖，相比同相位中心双模式方案更接近目标。
- 继续增厚到 `5.8..6.5 mm` 并未带来预期收益，反而导致匹配明显恶化，说明当前双单元耦合/地板边界条件已主导谐振。
- 在 44 mm 圆板内做两个低仰角单元时，19 mm 左右分离是本轮更均衡的工作点；如果继续沿该路线优化，应优先做匹配网络/馈点/短路墙微调，而不是单纯增加高度。
- 若必须一次性满足 `S11 < -10 dB` 和低仰角 `GainTotal >= -5 dBi`，当前结果仍建议回到单端口厚板 PIFA 达标基准，再围绕可校准阵列布置与极化组合做系统级测角验证。

## 产物

- 全量汇总：`reports_d44_me_dualpol_single_element/UWB_CH9_D44_ME_DUALPOL_SINGLE_ELEMENT_summary.csv`
- 全量报告：`reports_d44_me_dualpol_single_element/UWB_CH9_D44_ME_DUALPOL_SINGLE_ELEMENT_report.md`
- 本复核报告：`reports_d44_me_dualpol_single_element/UWB_CH9_D44_PHYSICAL_GRADED_RECHECK_report.md`
- 当前最佳 AEDT 工程：
  - `UWB_CH9_D44_ME_DUALPOL_SINGLE_ELEMENT_mirror_pifa_h3p5_l8p8_sep19p0_feed8p40_P1A.aedt`
  - `UWB_CH9_D44_ME_DUALPOL_SINGLE_ELEMENT_mirror_pifa_h3p5_l8p8_sep19p0_feed8p40_P1B.aedt`
