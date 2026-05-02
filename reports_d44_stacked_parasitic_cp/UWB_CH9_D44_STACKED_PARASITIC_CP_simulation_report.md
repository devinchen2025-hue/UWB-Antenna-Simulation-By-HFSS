# UWB CH9 D44 STACKED_PARASITIC_CP 仿真报告

## 模型

- AEDT 项目：`D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\UWB_CH9_Diamond_CP_Array_D44_STACKED_PARASITIC_CP.aedt`
- 设计名：`Array4_Diamond_D44_StackedParasitic_CP`
- 拓扑：Driven corner-truncated patches plus stacked parasitic patches using the available 8 mm height margin.
- PCB 直径：`44.0 mm`
- 总高度约束：`<= 8.0 mm`
- 板厚：`2.0 mm`
- 贴片边长：`8.95 mm`
- 截角：`0.84 mm`

## 核心指标

- 最差回波损耗：`-4.80 dB`，表达式 `dB(S(P4:1,P4:1))`
- 最差耦合：`-17.93 dB`，表达式 `dB(S(P1:1,P3:1))`
- 对应隔离度：`17.93 dB`
- 最佳端口覆盖包络最小增益：`-7.20 dBi`
- CP 合格包络最大轴比：`48.16 dB`
- CP 合格包络最小增益：`-14.18 dBi`
- CP 覆盖率最小值：`33.4%`

## 关键激励场景

| 场景 | 最小增益 | 最大轴比 | CP 覆盖率最小值 |
| --- | ---: | ---: | ---: |
| sequential_quadrature_all_ports | -18.54 dBi | 4049.06 dB | 56.3% |

## 结论

- 该版本已完成 HFSS 建模、三频点快速求解、S 参数导出和 FOV/轴比后处理。
- 是否最终达标需要同时查看 S 参数、FOV 最小增益和全 FOV 轴比；详细数据见同目录 CSV/JSON。

## 文件

- 指标 JSON：`D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_stacked_parasitic_cp\UWB_CH9_D44_STACKED_PARASITIC_CP_metrics.json`
- FOV CSV：`D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_stacked_parasitic_cp\UWB_CH9_D44_STACKED_PARASITIC_CP_fov_cp_metrics.csv`
- S 参数 CSV：`D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_stacked_parasitic_cp\UWB_CH9_D44_STACKED_PARASITIC_CP_s_parameters.csv`
