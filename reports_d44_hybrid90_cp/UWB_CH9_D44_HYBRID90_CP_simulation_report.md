# UWB CH9 D44 HYBRID90_CP 仿真报告

## 模型

- AEDT 项目：`D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\UWB_CH9_Diamond_CP_Array_D44_HYBRID90_CP.aedt`
- 设计名：`Array4_Diamond_D44_Hybrid90_CP`
- 拓扑：Dual-feed patches with ideal 90 degree hybrid excitation intent and printable branch traces for network layout study.
- PCB 直径：`44.0 mm`
- 总高度约束：`<= 8.0 mm`
- 板厚：`2.0 mm`
- 贴片边长：`9.15 mm`
- 截角：`0.0 mm`

## 核心指标

- 最差回波损耗：`-4.27 dB`，表达式 `dB(S(P1A:1,P1A:1))`
- 最差耦合：`-16.50 dB`，表达式 `dB(S(P3A:1,P1A:1))`
- 对应隔离度：`16.50 dB`
- 最佳端口覆盖包络最小增益：`-6.87 dBi`
- CP 合格包络最大轴比：`15.68 dB`
- CP 合格包络最小增益：`-12.49 dBi`
- CP 覆盖率最小值：`47.5%`

## 关键激励场景

| 场景 | 最小增益 | 最大轴比 | CP 覆盖率最小值 |
| --- | ---: | ---: | ---: |
| sequential_quadrature_all_ports | -16.14 dBi | 6086.94 dB | 47.4% |
| E1_dualfeed_quadrature | -14.05 dBi | 1563.24 dB | 74.7% |
| E2_dualfeed_quadrature | -12.12 dBi | 1166.45 dB | 63.8% |
| E3_dualfeed_quadrature | -14.35 dBi | 1188.70 dB | 76.7% |
| E4_dualfeed_quadrature | -13.75 dBi | 850.52 dB | 59.2% |
| ideal_hybrid_array_quadrature | -24.33 dBi | 3317.57 dB | 59.6% |

## 结论

- 该版本已完成 HFSS 建模、三频点快速求解、S 参数导出和 FOV/轴比后处理。
- 是否最终达标需要同时查看 S 参数、FOV 最小增益和全 FOV 轴比；详细数据见同目录 CSV/JSON。

## 文件

- 指标 JSON：`D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_hybrid90_cp\UWB_CH9_D44_HYBRID90_CP_metrics.json`
- FOV CSV：`D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_hybrid90_cp\UWB_CH9_D44_HYBRID90_CP_fov_cp_metrics.csv`
- S 参数 CSV：`D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_hybrid90_cp\UWB_CH9_D44_HYBRID90_CP_s_parameters.csv`
