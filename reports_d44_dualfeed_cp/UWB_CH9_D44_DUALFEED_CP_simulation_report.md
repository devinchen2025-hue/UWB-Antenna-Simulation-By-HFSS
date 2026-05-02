# UWB CH9 D44 DUALFEED_CP 仿真报告

## 模型

- AEDT 项目：`D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\UWB_CH9_Diamond_CP_Array_D44_DUALFEED_CP.aedt`
- 设计名：`Array4_Diamond_D44_DualFeed_CP`
- 拓扑：Dual orthogonal feed square patches. Each element exposes A/B feeds intended for 90 degree CP excitation.
- PCB 直径：`44.0 mm`
- 总高度约束：`<= 8.0 mm`
- 板厚：`2.0 mm`
- 贴片边长：`9.15 mm`
- 截角：`0.0 mm`

## 核心指标

- 最差回波损耗：`-4.20 dB`，表达式 `dB(S(P2A:1,P2A:1))`
- 最差耦合：`-16.46 dB`，表达式 `dB(S(P2A:1,P4A:1))`
- 对应隔离度：`16.46 dB`
- 最佳端口覆盖包络最小增益：`-6.10 dBi`
- CP 合格包络最大轴比：`13.36 dB`
- CP 合格包络最小增益：`-11.65 dBi`
- CP 覆盖率最小值：`47.1%`

## 关键激励场景

| 场景 | 最小增益 | 最大轴比 | CP 覆盖率最小值 |
| --- | ---: | ---: | ---: |
| sequential_quadrature_all_ports | -12.47 dBi | 1658.61 dB | 48.1% |
| E1_dualfeed_quadrature | -13.23 dBi | 925.47 dB | 75.9% |
| E2_dualfeed_quadrature | -11.86 dBi | 10419.13 dB | 63.2% |
| E3_dualfeed_quadrature | -14.18 dBi | 1228.30 dB | 74.7% |
| E4_dualfeed_quadrature | -11.68 dBi | 654.72 dB | 64.9% |
| dualfeed_array_quadrature | -21.23 dBi | 4269.26 dB | 62.7% |

## 结论

- 该版本已完成 HFSS 建模、三频点快速求解、S 参数导出和 FOV/轴比后处理。
- 是否最终达标需要同时查看 S 参数、FOV 最小增益和全 FOV 轴比；详细数据见同目录 CSV/JSON。

## 文件

- 指标 JSON：`D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_dualfeed_cp\UWB_CH9_D44_DUALFEED_CP_metrics.json`
- FOV CSV：`D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_dualfeed_cp\UWB_CH9_D44_DUALFEED_CP_fov_cp_metrics.csv`
- S 参数 CSV：`D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_dualfeed_cp\UWB_CH9_D44_DUALFEED_CP_s_parameters.csv`
