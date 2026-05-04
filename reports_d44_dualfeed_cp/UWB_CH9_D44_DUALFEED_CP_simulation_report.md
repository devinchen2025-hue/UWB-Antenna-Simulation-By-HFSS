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

- 最差回波损耗：`-8.57 dB`，表达式 `dB(S(P3A:1,P3A:1))`
- 最差耦合：`-12.44 dB`，表达式 `dB(S(P1A:1,P1B:1))`
- 对应隔离度：`12.44 dB`
- 最佳端口覆盖包络最小增益：`-7.99 dBi`
- CP 合格包络最大轴比：`10.15 dB`
- CP 合格包络最小增益：`-19.55 dBi`
- CP 覆盖率最小值：`48.6%`

## 关键激励场景

| 场景 | 最小增益 | 最大轴比 | CP 覆盖率最小值 |
| --- | ---: | ---: | ---: |
| sequential_quadrature_all_ports | -12.72 dBi | 43306.39 dB | 47.8% |
| E1_dualfeed_quadrature | -14.81 dBi | 2145.75 dB | 75.5% |
| E2_dualfeed_quadrature | -11.08 dBi | 5781.43 dB | 55.8% |
| E3_dualfeed_quadrature | -14.53 dBi | 1440.52 dB | 76.0% |
| E4_dualfeed_quadrature | -11.34 dBi | 41614.18 dB | 60.7% |
| dualfeed_array_quadrature | -21.39 dBi | 8733.55 dB | 59.2% |

## 结论

- 该版本已完成 HFSS 建模、三频点快速求解、S 参数导出和 FOV/轴比后处理。
- 是否最终达标需要同时查看 S 参数、FOV 最小增益和全 FOV 轴比；详细数据见同目录 CSV/JSON。

## 文件

- 指标 JSON：`D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_dualfeed_cp\UWB_CH9_D44_DUALFEED_CP_metrics.json`
- FOV CSV：`D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_dualfeed_cp\UWB_CH9_D44_DUALFEED_CP_fov_cp_metrics.csv`
- S 参数 CSV：`D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_dualfeed_cp\UWB_CH9_D44_DUALFEED_CP_s_parameters.csv`
