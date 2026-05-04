# D44 PDOA 线极化鉴角曲线对比图

## 图表范围

- 入射极化仅包含线极化 `0 / 45 / 90 / 135 deg`。
- 图中上半部分为展开后的 PDOA 鉴角曲线，下半部分为相对 `0 deg` 线极化的相位偏移。
- 无效点按空缺处理，避免弱响应点把曲线误连。

## 输出图片

- 总览拼图: `D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_pdoa_linear\plots\pdoa_linear_polarization_comparison_panel.png`
- 中心频点 A 馈 E1-E3 基线: `D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_pdoa_linear\plots\center_best_a_feed_e1_e3_phi90.png`
  - 上一轮汇总中单调性最好的中心频点候选之一，用于观察理想较优基线下的极化偏移。
- 中心频点 双馈合成 E1-E3 基线: `D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_pdoa_linear\plots\center_dualfeed_e1_e3_phi75.png`
  - 采用 A+B*exp(-j90deg) 双馈合成通道，展示接近当前 CP 使用方式下的鉴角曲线变化。
- 低频点 B 馈 E1-E2 敏感基线: `D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_pdoa_linear\plots\worst_sensitive_b_feed_e1_e2_phi45.png`
  - 上一轮指标中最大偏移接近 180 deg 的敏感案例，用于展示极化方向造成的最坏相位偏置。

## 数据来源

- 曲线 CSV: `D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_pdoa_linear\UWB_CH9_D44_PDOA_linear_polarization_curves.csv`
- PDOA 线极化评估脚本输出的 `pdoa_unwrapped_deg` 用于鉴角曲线，`pdoa_deg` 用于计算相对 0 deg 偏移。
