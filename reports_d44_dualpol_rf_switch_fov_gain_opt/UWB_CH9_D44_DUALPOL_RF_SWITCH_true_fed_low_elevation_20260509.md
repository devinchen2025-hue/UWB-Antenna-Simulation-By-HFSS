# D44 真实馈电低仰角覆盖单元优化报告

## 目标与口径

- 任务方向：从寄生板边辅助结构转向独立低仰角覆盖单元，优先验证真实板边馈电单极子/IFA 是否能覆盖水平面。
- 仿真频点：CH9 目标带内 7.738 GHz、约 7.9855/8.0 GHz、8.233 GHz。
- FOV 口径：HFSS 球坐标 `Theta=45..90 deg`、`Phi=0..360 deg`，覆盖从水平面到上仰 45 deg 的完整方位。
- 增益目标：FOV 内 `GainTotal` 与 `RealizedGainTotal` 均不低于 `-5 dBi`。
- 匹配目标：A_ON/B_ON 吸收式工作态内，选通 A/B 端口与新增低仰角端口 `P1L..P4L` 的最差回波均需 `<= -10 dB`。

## 本轮改动

- 在 `scripts/build_uwb_ch9_hfss_d44_topology.py` 增加真实板边馈电低仰角单元：
  - `board_edge_fed_monopole_enabled`：在每个阵元板边创建独立 `P1L..P4L` 单极子 lumped port。
  - `board_edge_fed_ifa_enabled`：预留真实板边馈电 IFA tap/short 几何和 `P1L..P4L` 端口。
  - 高度、间隙、宽度、顶载、IFA tap 位置均纳入参数校验和工程 notes 的高度统计。
- 在 `scripts/optimize_uwb_ch9_d44_dualpol_rf_switch_fov_gain.py` 增加候选 61-65：
  - 61：8 mm 外形内，4.8 mm 高真实馈电单极子。
  - 62：8 mm 外形内，4.8 mm 高真实馈电单极子加 1.2 mm 短顶载。
  - 63：10 mm 外形内，6.8 mm 高真实馈电单极子。
  - 64：8 mm 外形内，真实馈电 IFA。
  - 65：10 mm 外形内，较高真实馈电 IFA。
- 覆盖评估已把 `P1L..P4L` 自动纳入逐源激励和覆盖口径；匹配评估新增 `worst_low_elevation_s11_db`，并把 L 端口回波纳入 `all_workstate_s11_pass`。

## 核心结果

| 候选 | 结构 | 高度约束 | 覆盖口径 Realized 最小值 | 覆盖口径 Gain 最小值 | 最差 S11 | L 端口 S11 达标 | 总体达标 |
| ---: | --- | ---: | ---: | ---: | ---: | --- | --- |
| 60 | 旧的板边窄 wall 辅助覆盖基线 | 8 mm | -15.95 dBi | -15.95 dBi | -10.05 dB | 无 L 端口 | 否，覆盖不达标 |
| 61 | 真实板边馈电单极子，h=4.8 mm | 8 mm | -0.58 dBi | 1.12 dBi | -4.14 dB | 否 | 否，匹配不达标 |
| 63 | 真实板边馈电单极子，h=6.8 mm | 10 mm | -2.16 dBi | 1.14 dBi | -2.32 dB | 否 | 否，匹配不达标 |

## 关键判断

- 方向被验证：真实独立低仰角端口能大幅补水平面覆盖。候选 61 将覆盖口径 `RealizedGainTotal` 最差值从候选 60 的 `-15.95 dBi` 提升到 `-0.58 dBi`，已经越过 `-5 dBi` 覆盖目标。
- 当前瓶颈已从“辐射覆盖不足”转为“低仰角端口匹配不足”。候选 61/63 的最差回波分别只有 `-4.14 dB` 与 `-2.32 dB`，不满足 `-10 dB`。
- 加高单极子没有改善匹配：候选 63 仍能覆盖，但 S11 更差，说明单纯增加外形高度不是匹配解。
- 严格逐端口口径仍很差，主要因为每个 L 端口自身方向图存在深谷；但系统级“端口选择覆盖口径”已经接近可用，后续应围绕 L 端口匹配和切换策略优化，而不是再只调原 A/B patch。

## 未完成项与异常

- 候选 62 保存了 A_ON 快照，但 B_ON 后处理阶段 AEDT/PyAEDT 会话无 CPU 和无日志进展，已终止；未写入候选汇总。
- 候选 64 在独立 IFA 工程构建早期出现 AEDT 会话停滞，已终止；候选 65 因同属 IFA 路径，本轮未继续消耗时间。
- 以上异常没有影响候选 61/63 的已写入 CSV、A/B 工程快照和主工程恢复；但 IFA 路径需要单独用更短的 s-parameter-only 流程复跑验证。

## 下一步建议

1. 对候选 61 的 `P1L..P4L` 增加专用匹配网络，而不是继续拉高辐射臂：
   - 板边端口串联短微带/电感等效；
   - 单极子底部加小电容/折线调谐；
   - 先跑 s-parameter-only 小扫，目标把 L 端口最差 S11 从 `-4.14 dB` 拉到 `<= -10 dB`。
2. 保留 8 mm 外形的 4.8 mm 单极子作为主线，因为它在本轮覆盖最好且高度未放宽。
3. IFA 路径建议拆成独立脚本先只建单阵元/单端口，排除 AEDT 会话卡住后再回到四阵元全覆盖仿真。
4. 系统架构上应把低仰角端口视为第三类可选端口 `L`，与 A/B 极化端口并列进入端口选择策略，而不是把它当寄生结构。

## 输出文件

- 候选汇总 CSV：`reports_d44_dualpol_rf_switch_fov_gain_opt/UWB_CH9_D44_DUALPOL_RF_SWITCH_FOV_GAIN_summary.csv`
- 逐端口明细 CSV：`reports_d44_dualpol_rf_switch_fov_gain_opt/UWB_CH9_D44_DUALPOL_RF_SWITCH_FOV_GAIN_source_summary.csv`
- 覆盖口径明细 CSV：`reports_d44_dualpol_rf_switch_fov_gain_opt/UWB_CH9_D44_DUALPOL_RF_SWITCH_FOV_GAIN_coverage_summary.csv`
- 候选 61 A/B AEDT 快照：`reports_d44_dualpol_rf_switch_fov_gain_opt/UWB_CH9_D44_DUALPOL_RF_SWITCH_FOV_GAIN_61_*_A_ON_absorptive_50ohm_c0p08pf.aedt` 与 `*_B_ON_absorptive_50ohm_c0p08pf.aedt`
- 候选 63 A/B AEDT 快照：`reports_d44_dualpol_rf_switch_fov_gain_opt/UWB_CH9_D44_DUALPOL_RF_SWITCH_FOV_GAIN_63_*_A_ON_absorptive_50ohm_c0p08pf.aedt` 与 `*_B_ON_absorptive_50ohm_c0p08pf.aedt`
- 本报告：`reports_d44_dualpol_rf_switch_fov_gain_opt/UWB_CH9_D44_DUALPOL_RF_SWITCH_true_fed_low_elevation_20260509.md`
