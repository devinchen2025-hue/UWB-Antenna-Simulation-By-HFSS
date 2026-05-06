# D44 双极化孔缝耦合 S11 匹配优化报告

## 目标

- 持续迭代优化当前八端口双极化孔缝耦合模型的 S11/回波，目标为全端口带内最差回波 `<= -10.0 dB`。
- 本轮只跑 S 参数快速筛选，不重新导出远场；重点扫描贴片尺寸、孔缝长度/宽度、下层馈线宽度/长度和下层介质厚度。
- 当前可视模型参考候选 `slot_l3p6_w0p45_feed0p60` 的最差回波为 `-1.79 dB`；上一轮 S 参数筛选最佳为 `-2.29 dB`。

## 筛选排名

| 排名 | 候选 | 最差回波 | X回波 | Y回波 | 回波差 | 同阵元X/Y隔离 | 同馈跨阵元隔离 |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | `p9p75_l5p6_w0p70_fw0p80_stub1p90_w1p00_off1p55` | -9.29 dB | -9.29 dB | -9.69 dB | 0.41 dB | 0.20 dB | 42.35 dB |
| 2 | `p9p75_l5p6_w0p70_fw0p80_stub1p90_w1p00_off1p4` | -8.91 dB | -8.91 dB | -9.13 dB | 0.22 dB | 0.21 dB | 41.78 dB |
| 3 | `p9p75_l5p6_w0p70_fw0p80_stub1p90_w1p00_off1p2` | -8.27 dB | -8.49 dB | -8.27 dB | 0.22 dB | 0.26 dB | 40.56 dB |
| 4 | `p9p75_l5p6_w0p70_fw0p80_stub1p90_w0p70_off1p0` | -8.16 dB | -8.43 dB | -8.16 dB | 0.27 dB | 0.32 dB | 38.93 dB |
| 5 | `p9p75_l5p6_w0p70_fw0p80_stub1p90_w0p70_off1p4` | -7.97 dB | -7.97 dB | -8.22 dB | 0.25 dB | 0.23 dB | 39.99 dB |
| 6 | `p9p75_l5p6_w0p70_fw0p80_stub1p95_w1p00_off1p4` | -7.56 dB | -8.06 dB | -7.56 dB | 0.50 dB | 0.20 dB | 41.17 dB |
| 7 | `p9p75_l5p6_w0p70_fw0p80_stub1p90_w1p00_off1p1` | -7.55 dB | -7.55 dB | -8.23 dB | 0.67 dB | 0.22 dB | 42.50 dB |
| 8 | `p9p75_l5p6_w0p70_fw0p80_stub1p90_w1p00_off1p58` | -7.50 dB | -7.55 dB | -7.50 dB | 0.06 dB | 0.25 dB | 40.59 dB |
| 9 | `p9p75_l5p6_w0p70_fw0p80_stub1p90_w0p70_off1p2` | -7.47 dB | -7.47 dB | -7.60 dB | 0.13 dB | 0.30 dB | 39.98 dB |
| 10 | `p9p75_l5p6_w0p70_fw0p80_stub1p90_w0p96_off1p2` | -7.43 dB | -7.98 dB | -7.43 dB | 0.54 dB | 0.21 dB | 42.82 dB |
| 11 | `p9p75_l5p6_w0p70_fw0p80_stub1p90_w1p00_off1p54` | -7.37 dB | -7.37 dB | -7.59 dB | 0.23 dB | 0.18 dB | 39.70 dB |
| 12 | `p9p75_l5p6_w0p70_fw0p80_stub1p90_w1p00_off1p60` | -7.24 dB | -7.24 dB | -7.26 dB | 0.02 dB | 0.25 dB | 41.28 dB |
| 13 | `p9p75_l5p6_w0p70_fw0p80_stub1p85_w1p00_off1p4` | -7.22 dB | -7.61 dB | -7.22 dB | 0.39 dB | 0.22 dB | 38.20 dB |
| 14 | `p9p75_l5p6_w0p70_fw0p80_stub1p90_w0p95_off1p4` | -7.06 dB | -7.74 dB | -7.06 dB | 0.67 dB | 0.23 dB | 36.04 dB |
| 15 | `p9p75_l5p6_w0p70_fw0p80_stub1p90_w1p00_off1p53` | -7.01 dB | -7.01 dB | -7.32 dB | 0.31 dB | 0.18 dB | 42.30 dB |
| 16 | `p9p75_l5p6_w0p70_fw0p80_stub1p90_w0p90_off1p2` | -7.00 dB | -7.00 dB | -7.58 dB | 0.58 dB | 0.21 dB | 39.67 dB |
| 17 | `p9p75_l5p6_w0p70_fw0p80_stub1p85_w1p00_off1p2` | -6.91 dB | -7.57 dB | -6.91 dB | 0.66 dB | 0.23 dB | 41.73 dB |
| 18 | `p9p75_l5p6_w0p70_fw0p80_stub1p90_w1p00_off1p35` | -6.90 dB | -6.90 dB | -7.35 dB | 0.45 dB | 0.21 dB | 39.81 dB |
| 19 | `p9p75_l5p6_w0p70_fw0p80_stub1p90_w0p80_off1p2` | -6.83 dB | -6.84 dB | -6.83 dB | 0.01 dB | 0.28 dB | 41.48 dB |
| 20 | `p9p75_l5p6_w0p70_fw0p80_stub1p90_w0p98_off1p55` | -6.83 dB | -6.87 dB | -6.83 dB | 0.04 dB | 0.21 dB | 37.54 dB |
| 21 | `p9p75_l5p6_w0p70_fw0p80_stub1p90_w1p00_off1p45` | -6.72 dB | -6.75 dB | -6.72 dB | 0.04 dB | 0.18 dB | 42.98 dB |
| 22 | `p9p75_l5p6_w0p70_fw0p80_stub1p90_w1p02_off1p55` | -6.68 dB | -6.74 dB | -6.68 dB | 0.06 dB | 0.29 dB | 36.88 dB |
| 23 | `p9p75_l5p6_w0p70_fw0p80_stub1p90_w0p42_off1p2` | -6.68 dB | -6.68 dB | -6.79 dB | 0.11 dB | 0.48 dB | 40.22 dB |
| 24 | `p9p75_l5p6_w0p70_fw0p80_stub1p95_w1p00_off1p2` | -6.67 dB | -7.48 dB | -6.67 dB | 0.80 dB | 0.24 dB | 35.07 dB |
| 25 | `p9p75_l5p6_w0p70_fw0p80_stub1p90_w0p70_off0p9` | -6.65 dB | -6.93 dB | -6.65 dB | 0.28 dB | 0.34 dB | 40.48 dB |
| 26 | `p9p75_l5p6_w0p70_fw0p80_stub1p90_w1p05_off1p4` | -6.62 dB | -7.22 dB | -6.62 dB | 0.60 dB | 0.19 dB | 39.16 dB |
| 27 | `p9p75_l5p6_w0p70_fw0p80_stub1p90_w1p00_off1p52` | -6.61 dB | -6.61 dB | -6.93 dB | 0.32 dB | 0.20 dB | 43.39 dB |
| 28 | `p9p75_l5p6_w0p70_fw0p80_stub1p90_w0p98_off1p2` | -6.58 dB | -6.92 dB | -6.58 dB | 0.34 dB | 0.22 dB | 38.22 dB |
| 29 | `p9p75_l5p6_w0p70_fw0p80_stub1p90_w0p36_off1p0` | -6.57 dB | -6.63 dB | -6.57 dB | 0.06 dB | 0.66 dB | 39.39 dB |
| 30 | `p9p75_l5p6_w0p70_fw0p80_stub1p90_w0p48_off1p2` | -6.52 dB | -6.52 dB | -6.52 dB | 0.01 dB | 0.36 dB | 37.97 dB |
| 31 | `p9p75_l5p6_w0p70_fw0p80_stub1p90_w1p00_off1p3` | -6.49 dB | -7.02 dB | -6.49 dB | 0.53 dB | 0.20 dB | 40.95 dB |
| 32 | `p9p75_l5p6_w0p70_fw0p80_stub2p10_w0p70_off1p2` | -6.37 dB | -6.69 dB | -6.37 dB | 0.32 dB | 0.26 dB | 39.74 dB |
| 33 | `p9p75_l5p6_w0p70_fw0p80_stub1p90_w1p04_off1p2` | -6.35 dB | -6.35 dB | -7.13 dB | 0.78 dB | 0.21 dB | 36.18 dB |
| 34 | `p9p75_l5p6_w0p70_fw0p80_stub1p90_w1p06_off1p2` | -6.34 dB | -6.34 dB | -6.86 dB | 0.52 dB | 0.27 dB | 40.74 dB |
| 35 | `p9p75_l5p6_w0p70_fw0p80_stub2p15_w0p30_off1p2` | -6.30 dB | -6.38 dB | -6.30 dB | 0.08 dB | 0.37 dB | 40.16 dB |
| 36 | `p9p75_l5p6_w0p70_fw0p80_stub1p90_w1p00_off1p57` | -6.25 dB | -6.44 dB | -6.25 dB | 0.19 dB | 0.23 dB | 39.02 dB |
| 37 | `p9p75_l5p6_w0p70_fw0p80_stub1p90_w0p56_off1p2` | -6.14 dB | -6.23 dB | -6.14 dB | 0.09 dB | 0.41 dB | 40.29 dB |
| 38 | `p9p75_l5p6_w0p70_fw0p80_stub1p90_w0p36_off1p2` | -6.07 dB | -6.07 dB | -6.07 dB | 0.00 dB | 0.42 dB | 39.28 dB |
| 39 | `p9p75_l5p6_w0p70_fw0p80_stub1p90_w0p36_off1p4` | -5.89 dB | -5.93 dB | -5.89 dB | 0.05 dB | 0.35 dB | 41.27 dB |
| 40 | `p9p75_l5p6_w0p70_fw0p80_stub1p90_w1p02_off1p2` | -5.86 dB | -5.86 dB | -6.33 dB | 0.47 dB | 0.23 dB | 40.35 dB |
| 41 | `p9p75_l5p6_w0p70_fw0p80_stub1p90_w1p08_off1p2` | -5.84 dB | -5.84 dB | -6.18 dB | 0.34 dB | 0.21 dB | 42.66 dB |
| 42 | `p9p75_l5p6_w0p70_fw0p80_stub2p15_off1p2` | -5.78 dB | -5.82 dB | -5.78 dB | 0.04 dB | 0.59 dB | 38.46 dB |
| 43 | `p9p75_l5p6_w0p70_fw0p80_stub1p90_off1p0` | -5.65 dB | -5.71 dB | -5.65 dB | 0.06 dB | 0.69 dB | 38.79 dB |
| 44 | `p9p75_l5p6_w0p70_fw0p80_stub1p90_w1p00_off1p0` | -5.61 dB | -5.61 dB | -6.23 dB | 0.62 dB | 0.27 dB | 38.52 dB |
| 45 | `p9p75_l5p6_w0p70_fw0p80_stub1p70_w0p70_off1p2` | -5.59 dB | -5.59 dB | -5.66 dB | 0.06 dB | 0.35 dB | 41.49 dB |
| 46 | `p9p75_l5p6_w0p70_fw0p80_stub1p90_w1p15_off1p2` | -5.59 dB | -6.45 dB | -5.59 dB | 0.86 dB | 0.21 dB | 41.86 dB |
| 47 | `p9p75_l5p6_w0p70_fw0p80_stub2p15_w0p36_off1p2` | -5.56 dB | -5.58 dB | -5.56 dB | 0.01 dB | 0.36 dB | 40.60 dB |
| 48 | `p9p75_l5p8_w0p70_fw0p80_stub1p90_off1p2` | -5.56 dB | -5.56 dB | -5.57 dB | 0.01 dB | 0.55 dB | 39.12 dB |
| 49 | `p9p75_l5p6_w0p70_fw0p80_stub2p15_w0p50_off1p2` | -5.50 dB | -5.61 dB | -5.50 dB | 0.11 dB | 0.30 dB | 36.40 dB |
| 50 | `p9p75_l5p6_w0p70_fw0p80_stub1p90_off1p4` | -5.35 dB | -5.45 dB | -5.35 dB | 0.10 dB | 0.60 dB | 39.19 dB |
| 51 | `p9p75_l5p6_w0p70_fw0p80_stub1p90_w0p30_off1p2` | -5.35 dB | -5.43 dB | -5.35 dB | 0.08 dB | 0.55 dB | 40.39 dB |
| 52 | `p9p75_l5p6_w0p70_fw0p80_stub1p90_off1p2` | -5.29 dB | -5.35 dB | -5.29 dB | 0.06 dB | 0.57 dB | 40.51 dB |
| 53 | `p9p75_l5p6_w0p70_fw0p80_stub2p00_off1p2` | -5.22 dB | -5.25 dB | -5.22 dB | 0.03 dB | 0.51 dB | 40.28 dB |
| 54 | `p9p75_l5p8_w0p75_fw0p85_stub1p90_off1p2` | -5.12 dB | -5.14 dB | -5.12 dB | 0.02 dB | 0.51 dB | 38.42 dB |
| 55 | `p9p75_l5p6_w0p70_fw0p80_stub1p65_off1p2` | -5.06 dB | -5.06 dB | -5.06 dB | 0.00 dB | 0.55 dB | 40.77 dB |
| 56 | `p9p75_l5p6_w0p70_fw0p80_stub1p90_off0p8` | -5.02 dB | -5.02 dB | -5.08 dB | 0.06 dB | 0.90 dB | 38.28 dB |
| 57 | `p9p75_l5p6_w0p70_fw0p80_stub2p40_off1p2` | -5.00 dB | -5.00 dB | -5.04 dB | 0.04 dB | 0.36 dB | 38.26 dB |
| 58 | `p9p75_l5p6_w0p70_fw0p80_stub1p90_w1p00_off1p50` | -4.99 dB | -4.99 dB | -5.12 dB | 0.13 dB | 0.23 dB | 38.57 dB |
| 59 | `p9p75_l5p6_w0p70_fw0p80_stub1p50_off1p2` | -4.87 dB | -5.03 dB | -4.87 dB | 0.16 dB | 0.65 dB | 38.46 dB |
| 60 | `p9p75_l5p6_w0p70_fw0p80_stub1p90_w0p18_off1p2` | -4.87 dB | -4.89 dB | -4.87 dB | 0.03 dB | 0.70 dB | 36.30 dB |
| 61 | `p9p75_l5p6_w0p70_fw0p80_stub1p80_off1p2` | -4.69 dB | -4.75 dB | -4.69 dB | 0.06 dB | 0.62 dB | 40.75 dB |
| 62 | `p9p75_l5p6_w0p70_fw0p80_stub2p25_off1p2` | -4.67 dB | -4.74 dB | -4.67 dB | 0.08 dB | 0.47 dB | 42.43 dB |
| 63 | `p9p75_l5p6_w0p70_fw0p80_stub2p15_w0p42_off1p2` | -4.65 dB | -4.67 dB | -4.65 dB | 0.03 dB | 0.36 dB | 41.72 dB |
| 64 | `p9p75_l5p6_w0p70_fw0p80_stub0p75_w0p32_off1p2` | -4.55 dB | -4.55 dB | -4.55 dB | 0.00 dB | 1.08 dB | 38.28 dB |
| 65 | `p9p75_l5p6_w0p70_fw0p80_stub1p90_w1p30_off1p2` | -4.46 dB | -5.44 dB | -4.46 dB | 0.98 dB | 0.23 dB | 35.03 dB |
| 66 | `p9p75_l5p6_w0p70_fw0p80_stub1p90_off1p6` | -4.37 dB | -4.40 dB | -4.37 dB | 0.04 dB | 0.55 dB | 42.30 dB |
| 67 | `p9p75_l5p6_w0p70_fw0p80_stub0p90_off1p2` | -4.34 dB | -4.36 dB | -4.34 dB | 0.02 dB | 1.11 dB | 38.84 dB |
| 68 | `p9p75_l5p6_w0p70_fw0p80_stub0p75_off1p5` | -4.33 dB | -4.33 dB | -4.33 dB | 0.00 dB | 1.19 dB | 40.62 dB |
| 69 | `p9p75_l5p6_w0p70_fw0p80_stub1p10_w0p32_off1p2` | -4.28 dB | -4.28 dB | -4.39 dB | 0.10 dB | 0.77 dB | 41.06 dB |
| 70 | `p9p75_l5p6_w0p70_fw0p80_stub0p75_off1p2` | -4.14 dB | -4.14 dB | -4.15 dB | 0.01 dB | 0.70 dB | 40.39 dB |
| 71 | `p9p75_l5p6_w0p70_fw0p80_stub1p90_w1p00_off1p56` | -4.11 dB | -4.11 dB | -4.26 dB | 0.15 dB | 0.17 dB | 42.79 dB |
| 72 | `p9p75_l5p6_w0p70_fw0p80_stub0p65_off1p2` | -4.11 dB | -4.11 dB | -4.15 dB | 0.04 dB | 1.08 dB | 39.20 dB |
| 73 | `p9p75_l5p6_w0p70_fw0p80_stub1p10` | -3.96 dB | -3.99 dB | -3.96 dB | 0.03 dB | 1.73 dB | 42.51 dB |
| 74 | `p9p75_l5p6_w0p70_fw0p80_stub1p15_off1p2` | -3.94 dB | -3.95 dB | -3.94 dB | 0.01 dB | 0.85 dB | 40.44 dB |
| 75 | `p9p75_l5p6_w0p70_fw0p80_stub0p45` | -3.84 dB | -3.84 dB | -3.84 dB | 0.00 dB | 1.73 dB | 42.85 dB |
| 76 | `p9p75_l5p4_w0p65_fw0p75_stub1p90_off1p2` | -3.78 dB | -3.82 dB | -3.78 dB | 0.04 dB | 0.95 dB | 41.63 dB |
| 77 | `p9p75_l5p6_w0p70_fw0p80_stub0p75` | -3.75 dB | -3.75 dB | -3.77 dB | 0.02 dB | 1.39 dB | 39.34 dB |
| 78 | `p9p75_l5p6_w0p70_fw0p80_stub1p45` | -3.71 dB | -3.71 dB | -3.75 dB | 0.03 dB | 1.16 dB | 42.26 dB |
| 79 | `p9p75_l5p6_w0p70_fw0p80_stub0p75_off0p6` | -3.63 dB | -3.66 dB | -3.63 dB | 0.03 dB | 0.92 dB | 41.38 dB |
| 80 | `p9p75_l5p6_w0p70_fw0p80_stub0p75_off0p9` | -3.63 dB | -3.65 dB | -3.63 dB | 0.02 dB | 0.95 dB | 38.60 dB |
| 81 | `p9p75_l5p6_w0p70_fw0p80_stub0p75_off1p8` | -3.61 dB | -3.61 dB | -3.64 dB | 0.03 dB | 1.55 dB | 45.02 dB |
| 82 | `p9p55_l4p8_w0p60_fw0p70_stub0p75` | -3.61 dB | -3.63 dB | -3.61 dB | 0.02 dB | 1.58 dB | 39.74 dB |
| 83 | `p9p75_l5p2_w0p65_fw0p75_stub0p75` | -3.56 dB | -3.58 dB | -3.56 dB | 0.03 dB | 1.18 dB | 47.14 dB |
| 84 | `p9p75_l5p6_w0p70_fw0p80_stub0p75_off3p0` | -3.48 dB | -3.51 dB | -3.48 dB | 0.03 dB | 1.22 dB | 41.25 dB |
| 85 | `p9p75_l5p6_w0p70_fw0p80_port0p80_stub0p75` | -3.42 dB | -3.47 dB | -3.42 dB | 0.05 dB | 1.60 dB | 38.67 dB |
| 86 | `p9p75_l5p6_w0p70_fw0p80` | -3.35 dB | -3.35 dB | -3.38 dB | 0.03 dB | 1.29 dB | 42.19 dB |
| 87 | `p9p75_l5p6_w0p70_fw0p80_stub0p75_neg` | -3.06 dB | -3.11 dB | -3.06 dB | 0.05 dB | 1.88 dB | 46.07 dB |
| 88 | `p9p55_l4p8_w0p60_fw0p70` | -2.93 dB | -2.96 dB | -2.93 dB | 0.04 dB | 1.18 dB | 41.43 dB |
| 89 | `p9p75_l5p2_w0p65_fw0p75` | -2.83 dB | -2.83 dB | -2.87 dB | 0.04 dB | 2.05 dB | 42.25 dB |
| 90 | `p9p35_l4p8_w0p60_fw0p70` | -2.81 dB | -2.84 dB | -2.81 dB | 0.03 dB | 1.50 dB | 39.24 dB |
| 91 | `p8p95_l4p4_w0p58_fw0p68` | -2.79 dB | -2.79 dB | -2.79 dB | 0.00 dB | 1.70 dB | 29.94 dB |
| 92 | `p9p55_l5p2_w0p65_fw0p75` | -2.74 dB | -2.74 dB | -2.76 dB | 0.02 dB | 1.79 dB | 40.30 dB |
| 93 | `p9p25_l4p5_w0p58_fw0p68` | -2.60 dB | -2.60 dB | -2.63 dB | 0.03 dB | 2.36 dB | 38.37 dB |
| 94 | `p9p05_l4p4_w0p58_fw0p68` | -2.59 dB | -2.59 dB | -2.63 dB | 0.03 dB | 1.53 dB | 34.80 dB |
| 95 | `p9p05_l4p25_w0p56_fw0p66` | -2.37 dB | -2.37 dB | -2.37 dB | 0.01 dB | 2.18 dB | 37.17 dB |
| 96 | `p8p95_l4p2_w0p55_fw0p65` | -2.31 dB | -2.33 dB | -2.31 dB | 0.02 dB | 2.40 dB | 40.22 dB |
| 97 | `p9p35_l4p4_w0p55_fw0p65_ref` | -2.29 dB | -2.29 dB | -2.30 dB | 0.01 dB | 1.37 dB | 38.80 dB |
| 98 | `p9p15_l4p4_w0p55_fw0p65` | -2.27 dB | -2.29 dB | -2.27 dB | 0.02 dB | 2.43 dB | 43.01 dB |
| 99 | `p9p00_l4p2_w0p56_fw0p66` | -2.23 dB | -2.23 dB | -2.25 dB | 0.02 dB | 2.30 dB | 42.19 dB |
| 100 | `p8p95_l4p2_w0p60_fw0p70` | -2.18 dB | -2.18 dB | -2.29 dB | 0.11 dB | 3.11 dB | 40.37 dB |
| 101 | `p9p15_l4p0_w0p50_fw0p60` | -2.06 dB | -2.08 dB | -2.06 dB | 0.01 dB | 1.32 dB | 38.63 dB |
| 102 | `p8p90_l4p15_w0p54_fw0p64` | -2.04 dB | -2.07 dB | -2.04 dB | 0.04 dB | 2.22 dB | 35.65 dB |
| 103 | `p8p75_l4p0_w0p50_fw0p65` | -1.88 dB | -1.94 dB | -1.88 dB | 0.06 dB | 3.67 dB | 39.62 dB |
| 104 | `p8p55_l3p8_w0p50_fw0p60` | -1.84 dB | -1.84 dB | -1.85 dB | 0.01 dB | 2.12 dB | 36.60 dB |
| 105 | `p8p95_l3p8_w0p50_fw0p60` | -1.80 dB | -1.81 dB | -1.80 dB | 0.01 dB | 2.01 dB | 39.18 dB |
| 106 | `p8p95_l4p2_w0p55_fw0p65_len12` | -1.62 dB | -1.62 dB | -1.65 dB | 0.03 dB | 5.25 dB | 46.14 dB |
| 107 | `p8p55_l3p4_w0p45_fw0p55` | -1.03 dB | -1.03 dB | -1.17 dB | 0.14 dB | 3.08 dB | 36.22 dB |
| 108 | `p8p75_l3p6_w0p45_fw0p60` | -0.70 dB | -0.74 dB | -0.70 dB | 0.04 dB | 2.06 dB | 40.46 dB |
| 109 | `p8p95_l4p2_w0p55_fw0p65_len8` | -0.46 dB | -0.46 dB | -0.52 dB | 0.06 dB | 21.07 dB | 33.70 dB |
| 110 | `p8p75_l4p0_w0p50_fw0p65_h0p508` | -0.36 dB | -0.51 dB | -0.36 dB | 0.15 dB | 3.62 dB | 20.29 dB |

## 最佳候选

- 候选：`p9p75_l5p6_w0p70_fw0p80_stub1p90_w1p00_off1p55`
- 最差回波：`-9.29 dB`
- 相对当前可视模型变化：`-7.50 dB`（负值为改善）。
- 相对上一轮 S 参数最佳变化：`-7.00 dB`（负值为改善）。
- S11 目标：`未通过`。

## 最佳几何参数

- `patch_side_mm`: `9.750`
- `port_width_mm`: `0.500`
- `dualpol_slotcoupled_enabled`: `1.000`
- `feed_substrate_h_mm`: `0.254`
- `slot_coupled_aperture_length_a_mm`: `5.600`
- `slot_coupled_aperture_length_b_mm`: `5.600`
- `slot_coupled_aperture_width_mm`: `0.700`
- `slot_coupled_offset_a_mm`: `0.000`
- `slot_coupled_offset_b_mm`: `0.000`
- `slot_coupled_aperture_center_a_v_mm`: `0.000`
- `slot_coupled_aperture_center_b_u_mm`: `0.000`
- `slot_coupled_feedline_length_mm`: `10.000`
- `slot_coupled_feedline_width_mm`: `0.800`
- `slot_coupled_feedline_offset_a_v_mm`: `0.000`
- `slot_coupled_feedline_offset_b_u_mm`: `0.000`
- `slot_coupled_stub_enabled`: `1.000`
- `slot_coupled_stub_length_mm`: `1.900`
- `slot_coupled_stub_width_mm`: `1.000`
- `slot_coupled_stub_offset_mm`: `1.550`
- `slot_coupled_stub_side_sign`: `1.000`
- `dualpol_parasitic_enabled`: `0.000`
- `parasitic_side_mm`: `0.000`
- `air_gap_mm`: `0.000`
- `isolation_slot_enabled`: `1.000`
- `isolation_slot_length_mm`: `10.000`
- `isolation_slot_width_mm`: `0.420`
- `isolation_slot_inner_mm`: `3.200`

## 工程判断

- 更大贴片配更长、更宽的中心孔缝后最差回波出现正向改善，说明当前孔缝耦合强度不足是 S11 的主要限制。
- 代价是同阵元 X/Y 隔离下降，后续需要把 S11 调谐支节和 A/B 去耦结构分开设计。
- 如果仍未到 -10 dB，下一轮应在下层孔缝馈线中加入真正的开路/短路调谐支节、阶梯阻抗线或电容耦合调谐，而不是继续只扫矩形孔缝。
- 本轮重建的 AEDT 工程保存为最佳 S11 候选，可直接打开检查八端口 S 参数。

## 输出文件

- S 参数筛选 CSV：`D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_dualpol_s11_slotmatch_opt\UWB_CH9_D44_DUALPOL_S11_SLOTMATCH_sparam_screening.csv`
- 最佳 JSON：`D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_dualpol_s11_slotmatch_opt\UWB_CH9_D44_DUALPOL_S11_SLOTMATCH_best.json`
- 中文报告：`D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_dualpol_s11_slotmatch_opt\UWB_CH9_D44_DUALPOL_S11_SLOTMATCH_optimization_report.md`
- AEDT 工程：`D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\UWB_CH9_Diamond_CP_Array_D44_DUALPOL_XY.aedt`
- 参数 JSON：`D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\UWB_CH9_Diamond_CP_Array_D44_DUALPOL_XY_params.json`
