# UWB CH9 D44 H8 PCB圆极化优化说明

## 目标

- 在直径 `44 mm` 圆形PCB内保留四阵元菱形布阵，最近邻阵元间距 `17 mm`。
- PCB+天线整体高度 `<= 8 mm`，优先使用可量产的PCB印刷结构。
- 工作频段覆盖 UWB CH9：`7.738-8.233 GHz`，仿真扫频建议 `7.7-8.3 GHz`。
- 同时评估上视场覆盖与圆极化：`Theta=0-360 deg, Phi=45-90 deg`，`GainTotal`最小值目标 `>= -5 dBi`，`AxialRatioValue`目标 `<= 3 dB`。

## 本分支结构路线

本分支新增 `D44_H8_PCB_CP` 版本，采用单馈角截短方形圆极化贴片作为加工友好的低剖面起点：

- 顶层：四个角截短方形CP贴片，按菱形位置布置。
- 底层：圆形地，预留十字向隔离槽参数。
- 馈电：每个贴片使用独立单端口探针/过孔等效馈电位置，便于后续落到同轴座、SMP、弹针或过孔转接。
- 板厚：初值 `2.0 mm`，总高约 `2.070 mm`，明显低于 `8 mm`。

## 初始优化参数

| 参数 | 初值 | 用途 |
| --- | ---: | --- |
| `substrate_h_mm` | `2.0` | 增加低剖面贴片带宽，同时保持普通PCB可加工性 |
| `patch_side_mm` | `8.91` | 三频点快速调谐后的贴片谐振尺寸 |
| `corner_cut_mm` | `0.62` | 分裂正交模，用于圆极化轴比调谐 |
| `feed_offset_u_mm` | `2.68` | 三频点快速调谐后的馈电位置 |
| `ground_radius_mm` | `21.4` | 接近整板底地，同时保留板边余量 |
| `isolation_slot_length_mm` | `8.0` | 降低相邻贴片耦合的起始参数 |

## 推荐复跑顺序

1. 先跑 `--quick --band-samples` 三频点，确认几何、端口和远场数据可导出。
2. 优先扫 `patch_side_mm=9.0..9.8` 与 `feed_offset_u_mm=1.4..2.3`，把 S 参数中心调到 CH9。
3. 再扫 `corner_cut_mm=0.45..1.05`，把 8 GHz附近轴比压低。
4. 如果轴比带宽不足，再扫 `substrate_h_mm=2.0/2.4/3.2`；`3.2 mm`可作为带宽增强备选，但需要复核表面波和隔离度。
5. 最后扫底地隔离槽长度/宽度，折中隔离度、轴比和FOV覆盖。

## 本轮快速调谐结论

- 初始候选 `patch_side=9.4 mm / feed_offset=1.85 mm / corner_cut=0.72 mm` 的三频点最差回波约 `-1.51 dB`。
- 最佳单馈贴片候选为 `patch_side=8.91 mm / feed_offset=2.68 mm / corner_cut=0.62 mm`，三频点最差回波约 `-9.27 dB`。
- 继续微调端口宽度和馈点焊盘后未超过该结果，说明单馈角截短贴片在当前44 mm四阵元强耦合环境下已经接近简单结构上限。
- 若必须签核 `Sii < -10 dB` 与全FOV `AR <= 3 dB`，下一步应加入印刷匹配支节、双馈正交合成、缝隙耦合或小型90度混合网络。

## 脚本

- 建模脚本：`scripts/build_uwb_ch9_hfss_d44_h8_pcb_cp.py`
- 评估脚本：`scripts/evaluate_uwb_ch9_d44_h8_pcb_cp.py`

常用命令：

```powershell
python scripts/build_uwb_ch9_hfss_d44_h8_pcb_cp.py --non-graphical --quick --band-samples --analyze
python scripts/evaluate_uwb_ch9_d44_h8_pcb_cp.py
```

## 判据说明

- `P*_only`：单端口独立激励，适合PDOA接收通道检查。
- `coverage_envelope_best_port`：每个方向取四端口中增益最高者，是覆盖能力的主要视角。
- `cp_qualified_envelope`：优先从 `AR<=3 dB` 的端口中取最高增益，适合检查圆极化覆盖缺口。
- `sequential_quadrature_all_ports`：四端口顺序90度相位激励，只作为阵列圆极化趋势检查，不作为PDOA单通道签核结论。
