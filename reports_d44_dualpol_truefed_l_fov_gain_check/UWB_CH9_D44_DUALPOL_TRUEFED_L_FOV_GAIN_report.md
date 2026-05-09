# D44 true-fed L 端口 FOV 复核记录

## 目标

- 复核候选：`fold0p6_neck1p6_stub2p6`。
- 增益目标：覆盖口径 `GainTotal` 与 `RealizedGainTotal` 均 `>= -5.0 dBi`。
- 匹配目标：A/B 工作态与 L 端口最差 S11 均 `<= -10.0 dB`。

## 已完成结果

- S11 已达标：候选 37 最差总回波与最差 L 端口回波均为 `-10.32 dB`。
- 候选 61 已验证覆盖增益仍作为本轮增益参考基线：覆盖口径 `RealizedGainTotal` 最差 `-0.582281 dBi`，`GainTotal` 最差 `1.123451 dBi`。
- 候选 37 保留候选 61 的真实板边馈电单极子覆盖结构，只增加 `1.6 mm` feed neck、`2.6 mm` open stub 与 `0.6 mm` folded open branch 作为 L 端口匹配网络。

## 本轮 FOV 复核状态

- 已补充专用脚本：`D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\scripts\evaluate_uwb_ch9_d44_truefed_l_fov_gain.py`。
- 已尝试全带 FOV 复核：AEDT 2023.1 在 `Setup_CH9` 的 `Solving design setup` 阶段挂起，未产出远场数据。
- 已尝试中心频点 `8 GHz` 轻量复核：仍在同一求解阶段挂起，未产出远场数据。
- 因此，本轮结论为：S11 已达标；覆盖增益有候选 61 的同辐射结构基线达标证据，但候选 37 的同候选完整 FOV signoff 仍待 AEDT 求解恢复后复跑。

## 输出与日志

- S11 报告：`D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_dualpol_truefed_l_match_opt\UWB_CH9_D44_DUALPOL_TRUEFED_L_MATCH_report.md`
- FOV 全带日志：`D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_dualpol_truefed_l_fov_gain_check\UWB_CH9_D44_DUALPOL_TRUEFED_L_FOV_GAIN_run.log`
- FOV 中心频点日志：`D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_dualpol_truefed_l_fov_gain_check\UWB_CH9_D44_DUALPOL_TRUEFED_L_FOV_GAIN_center_run.log`
