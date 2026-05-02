# UWB CH9 D44 SLOTCOUPLED_CP 仿真报告

## 模型

- AEDT 项目：`D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\UWB_CH9_Diamond_CP_Array_D44_SLOTCOUPLED_CP.aedt`
- 设计名：`Array4_Diamond_D44_SlotCoupled_CP`
- 拓扑：Aperture-coupled top patches fed by underside microstrip lines through ground slots.
- PCB 直径：`44.0 mm`
- 总高度约束：`<= 8.0 mm`
- 板厚：`2.0 mm`
- 贴片边长：`9.55 mm`
- 截角：`0.72 mm`

## 核心指标

- 最差回波损耗：`-0.02 dB`，表达式 `dB(S(P3:1,P3:1))`
- 最差耦合：`-56.70 dB`，表达式 `dB(S(P1:1,P4:1))`
- 对应隔离度：`56.70 dB`
- 最佳端口覆盖包络最小增益：`-3.22 dBi`
- CP 合格包络最大轴比：`120.30 dB`
- CP 合格包络最小增益：`-14.26 dBi`
- CP 覆盖率最小值：`39.2%`

## 关键激励场景

| 场景 | 最小增益 | 最大轴比 | CP 覆盖率最小值 |
| --- | ---: | ---: | ---: |
| sequential_quadrature_all_ports | -9.44 dBi | 15162.77 dB | 44.1% |

## 结论

- 该版本已完成 HFSS 建模、三频点快速求解、S 参数导出和 FOV/轴比后处理。
- 是否最终达标需要同时查看 S 参数、FOV 最小增益和全 FOV 轴比；详细数据见同目录 CSV/JSON。

## 文件

- 指标 JSON：`D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_slotcoupled_cp\UWB_CH9_D44_SLOTCOUPLED_CP_metrics.json`
- FOV CSV：`D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_slotcoupled_cp\UWB_CH9_D44_SLOTCOUPLED_CP_fov_cp_metrics.csv`
- S 参数 CSV：`D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_slotcoupled_cp\UWB_CH9_D44_SLOTCOUPLED_CP_s_parameters.csv`
