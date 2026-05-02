# UWB CH9 D44 H8 PCB CP 自动优化报告

## 设计目标

- PCB 直径：44 mm
- 总高度：不超过 8 mm
- 工作频段：7.738-8.233 GHz
- 回波损耗目标：三频点最差 Sii <= -10.0 dB
- 端口隔离目标：最差耦合对应隔离度 >= 15.0 dB
- FOV 增益目标：Theta 0-360 deg, Phi 45-90 deg 内最小 GainTotal >= -5.0 dBi
- 圆极化目标：FOV 内 AxialRatioValue <= 3.0 dB

## 自动优化方法

- 采用微带贴片经验公式和上一轮仿真结果生成候选：贴片边长控制谐振频点，馈点偏移控制输入阻抗，截角控制正交模分裂，板厚和地槽控制带宽/耦合/FOV。
- 第一阶段使用三频点快速离散扫频，只保存 S 参数，快速筛除失配候选。
- 第二阶段对 S 参数最佳候选重建包含远场球面的 HFSS 工程，并导出 FOV 增益和轴比指标。
- 最终 AEDT 工程保存为项目根目录下的 `UWB_CH9_Diamond_CP_Array_D44_H8_PCB_CP.aedt`，可直接用 AEDT 打开复核。

## 最佳参数

- `substrate_h_mm`: `2.000`
- `patch_side_mm`: `9.000`
- `corner_cut_mm`: `0.840`
- `feed_offset_u_mm`: `2.740`
- `feed_pad_radius_mm`: `0.450`
- `port_width_mm`: `0.750`
- `ground_radius_mm`: `21.400`
- `isolation_slot_length_mm`: `11.000`
- `isolation_slot_width_mm`: `0.450`
- `isolation_slot_inner_mm`: `3.200`

## 核心仿真指标

- 最差回波损耗：`-9.83 dB`，表达式 `dB(S(P4:1,P4:1))`
- 最差端口耦合：`-17.38 dB`，表达式 `dB(S(P4:1,P2:1))`
- 对应隔离度：`17.38 dB`
- 最佳端口覆盖包络最小增益：`-7.99 dBi`
- CP 合格包络最大轴比：`32.09 dB`
- CP 合格包络最小增益：`-25.42 dBi`
- CP 覆盖率最小值：`33.4%`
- 顺序 90 度四端口激励 CP 覆盖率最小值：`60.0%`

## 是否满足目标

- 综合结论：`未完全通过`

## S 参数候选排名

| 排名 | 候选 | 分数 | 最差 Sii | 隔离度 | 说明 |
| ---: | --- | ---: | ---: | ---: | --- |
| 1 | combo_patch9_corner084_slot11 | 1.32 | -9.83 dB | 17.38 dB | Test a more aggressive decoupling slot length. |
| 2 | final_slot11_feed278 | 2.08 | -9.76 dB | 17.13 dB | Move feed outward on the slot11 best point. |
| 3 | combo_patch898_corner084_slot10 | 2.92 | -9.67 dB | 17.33 dB | Raise resonance slightly and combine with longer decoupling slot. |
| 4 | local_patch_9p00_corner_0p84 | 3.21 | -9.64 dB | 17.55 dB | Slightly lower resonance and keep the stronger CP modal split. |
| 5 | combo_patch9_corner084_slot10_narrowport | 3.49 | -9.61 dB | 17.63 dB | Combine best geometry with lower feed capacitance. |
| 6 | combo_patch9_corner086_slot10 | 4.00 | -9.56 dB | 17.40 dB | Increase corner split slightly with longer decoupling slot. |
| 7 | local_corner_0p86 | 4.18 | -9.54 dB | 17.47 dB | Continue the first-round trend by increasing the corner perturbation. |
| 8 | ground_slot_longer | 5.04 | -9.47 dB | 17.02 dB | Increase decoupling slot length for isolation and FOV ripple control. |

## 工程文件

- 最终 AEDT 项目：`D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\UWB_CH9_Diamond_CP_Array_D44_H8_PCB_CP.aedt`
- 详细 FOV CSV：`D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_h8_pcb_cp\UWB_CH9_D44_H8_PCB_CP_fov_cp_metrics.csv`
- S 参数 CSV：`D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_h8_pcb_cp\UWB_CH9_D44_H8_PCB_CP_s_parameters.csv`
- 指标 JSON：`D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_h8_pcb_cp\UWB_CH9_D44_H8_PCB_CP_metrics.json`
- 优化历史 CSV：`D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_h8_pcb_cp\UWB_CH9_D44_H8_PCB_CP_optimization_history.csv`
- 最佳参数 JSON：`D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_h8_pcb_cp\UWB_CH9_D44_H8_PCB_CP_optimization_best.json`
