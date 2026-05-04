# D44 锚点天线 PDOA 极化稳定性优化报告

## 本轮目标

- 不同入射线极化 `0 / 45 / 90 / 135 deg` 下，PDOA 鉴角曲线变化最小。
- 目标阈值：平均 RMS 漂移 `<= 10.0 deg`，最大漂移 `<= 20.0 deg`。
- 同时参考天线指标：`Sii <= -10.0 dB`、隔离 `>= 15.0 dB`、轴比 `<= 3.0 dB`、FOV 最小增益 `>= -5.0 dBi`。

## 优化路径

- 本轮不重建几何，直接使用已求解 HFSS 工程中的 `re/im(rETheta)` 与 `re/im(rEPhi)` 嵌入式复数远场。
- 扫描双馈 B 路相对 A 路的输出幅度和相位，等价于优化 90 度混合器输出幅相平衡。
- 幅度范围 `0.80-1.20`，步进 `0.025`；相位范围 `-125 deg` 到 `-55 deg`，步进 `2.5 deg`。
- 评分函数直接惩罚 45/90/135 deg 线极化相对 0 deg 的 PDOA RMS 漂移、95 分位 RMS 漂移、最大漂移、弱响应点和参考曲线单调性不足。

## 纯 PDOA 最优候选

- B 路幅度：`1.000`，相对 A 路。
- B 路相位：`-92.5 deg`，相对 A 路。
- 纯 PDOA 评分：`112.81`，越低越好。
- 平均 RMS PDOA 漂移：`46.39 deg`。
- 95 分位 RMS PDOA 漂移：`79.75 deg`。
- 全局最大 PDOA 漂移：`179.96 deg`。

## 综合最优幅相候选

- B 路幅度：`1.000`，相对 A 路。
- B 路相位：`-97.5 deg`，相对 A 路。
- 综合候选来自 Top PDOA 候选的轴比/增益复核，兼顾 PDOA 漂移和轴比异常值。
- PDOA 评分：`114.11`，越低越好。
- 平均 RMS PDOA 漂移：`46.74 deg`。
- 95 分位 RMS PDOA 漂移：`79.20 deg`。
- 平均最大 PDOA 漂移：`134.60 deg`。
- 全局最大 PDOA 漂移：`179.94 deg`。
- 平均有效点比例：`99.7%`。
- 参考极化曲线平均单调片段比例：`71.5%`。

## 与当前默认 1.00 / -90 deg 对比

- 默认平均 RMS 漂移：`46.44 deg`。
- 纯 PDOA 最优平均 RMS 漂移：`46.39 deg`。
- 优化后平均 RMS 漂移：`46.74 deg`。
- 默认 95 分位 RMS 漂移：`80.85 deg`。
- 纯 PDOA 最优 95 分位 RMS 漂移：`79.75 deg`。
- 综合候选 95 分位 RMS 漂移：`79.20 deg`。
- 默认最大漂移：`179.98 deg`。
- 优化后最大漂移：`179.94 deg`。
- 纯 PDOA 平均 RMS 改善：`0.05 deg`。
- 综合候选平均 RMS 变化：`0.30 deg`。

## 轴比和 S 参数验证

- 当前工程最差 Sii：`-8.57 dB`，目标 `<= -10 dB`。
- 当前工程隔离度：`12.44 dB`，目标 `>= 15 dB`。
- 最优幅相候选的 FOV 最小增益：`-17.58 dBi`。
- 最优幅相候选的 FOV 最大轴比：`431.44 dB`。
- 最优幅相候选的 CP 覆盖率下限：`65.5%`。

## 达标情况

- PDOA 平均 RMS 目标：`未通过`。
- PDOA 最大漂移目标：`未通过`。
- S 参数目标：`未通过`。
- 轴比目标：`未通过`。

## 工程结论

- 仅优化双馈输出幅相对 PDOA 漂移改善很有限：纯 PDOA 最优只带来约 0.05 deg 的平均 RMS 改善，综合候选则为了降低轴比异常值牺牲了约 0.30 deg 的平均 RMS。
- 这说明极化敏感性不只是混合器输出误差导致，还来自阵元复数矢量有效长度、端口耦合、馈线路径和阵元间不一致。
- 轴比与 PDOA 稳定性有相关性，但本轮再次表明：轴比不是充分条件。综合候选轴比异常值比默认点低很多，但 PDOA 最大漂移仍接近 180 deg。
- 下一轮建议进入几何层：优先围绕端口隔离、双馈物理对称性、DGS/隔离枝节非直连耦合、四阵元馈线等长等相位继续优化。

## 输出文件

- 优化历史：`D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_pdoa_stability_opt\UWB_CH9_D44_PDOA_polarization_stability_history.csv`
- Top 候选轴比验证：`D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_pdoa_stability_opt\UWB_CH9_D44_PDOA_polarization_stability_top_validation.csv`
- 最优曲线 CSV：`D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_pdoa_stability_opt\UWB_CH9_D44_PDOA_polarization_stability_best_curves.csv`
- 最优结果 JSON：`D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_pdoa_stability_opt\UWB_CH9_D44_PDOA_polarization_stability_best.json`
- 评分热力图：`D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_pdoa_stability_opt\UWB_CH9_D44_PDOA_polarization_stability_score_heatmap.png`
