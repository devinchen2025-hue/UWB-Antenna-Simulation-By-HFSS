# D44 dual-feed / 90-degree hybrid optimization report

## Targets

- Worst Sii <= -10.0 dB across 7.738/7.9855/8.233 GHz.
- Port isolation >= 15.0 dB.
- FOV envelope minimum gain >= -5.0 dBi.
- AxialRatioValue <= 3.0 dB in the selected FOV, or best available source-balance result recorded.

## Best candidate

- Candidate: `dualfeed_feed_3p3`
- Topology: `dualfeed`
- Rationale: Fine sweep just inside the 3.4 mm best point.
- Meets all targets: `False`

## Geometry parameters

- `patch_side_mm`: `9.150`
- `feed_offset_u_mm`: `3.300`
- `port_width_mm`: `0.700`
- `feed_pad_radius_mm`: `0.420`
- `isolation_slot_length_mm`: `10.000`
- `isolation_slot_width_mm`: `0.420`

## Core metrics

- Worst return loss: `-8.57 dB` via `dB(S(P3A:1,P3A:1))`
- Worst coupling: `-12.44 dB` via `dB(S(P1B:1,P1A:1))`
- Isolation: `12.44 dB`
- Coverage-envelope min gain: `-7.99 dBi`
- CP-qualified envelope max AR: `10.15 dB`
- CP-qualified envelope min gain: `-19.55 dBi`
- CP-qualified min coverage: `48.6%`

## Best source phase/amplitude balance

- B-feed amplitude: `1.000` relative to A-feed.
- B-feed phase: `-105.0 deg` relative to A-feed.
- Balanced-array min gain: `-14.72 dBi`
- Balanced-array max AR: `1046.40 dB`
- Balanced-array min CP coverage: `29.9%`

## S-parameter screening ranking

| Rank | Candidate | Topology | Score | Worst Sii | Isolation | Notes |
| ---: | --- | --- | ---: | ---: | ---: | --- |
| 1 | dualfeed_feed_3p3 | dualfeed | 25.61 | -8.57 dB | 12.44 dB | Fine sweep just inside the 3.4 mm best point. |
| 2 | dualfeed_feed_3p3 | dualfeed | 25.61 | -8.57 dB | 12.44 dB | Fine sweep just inside the 3.4 mm best point. |
| 3 | dualfeed_feed_3p4 | dualfeed | 27.54 | -8.52 dB | 12.19 dB | Move both feeds outward to test higher input resistance. |
| 4 | dualfeed_feed_3p4 | dualfeed | 27.54 | -8.52 dB | 12.19 dB | Move both feeds outward to test higher input resistance. |
| 5 | dualfeed_feed_3p4_narrow_port | dualfeed | 28.44 | -8.46 dB | 12.19 dB | Keep best feed offset and reduce local feed capacitance. |
| 6 | dualfeed_feed_3p2 | dualfeed | 32.10 | -8.10 dB | 12.77 dB | Fine sweep between baseline and the 3.4 mm best point. |
| 7 | dualfeed_feed_3p6 | dualfeed | 39.47 | -7.74 dB | 12.38 dB | Fine sweep outward from the best return-loss trend. |
| 8 | dualfeed_feed_3p4_wide_port | dualfeed | 43.99 | -7.45 dB | 12.46 dB | Keep best feed offset and increase local feed capacitance. |
| 9 | dualfeed_feed_3p8 | dualfeed | 56.28 | -6.87 dB | 11.75 dB | Continue outward feed sweep toward the patch edge for matching. |
| 10 | hybrid_baseline | hybrid | 85.97 | -4.27 dB | 16.50 dB | Previous 90-degree hybrid topology baseline. |

## Output files

- Optimization history: `D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_dualfeed_hybrid_opt\UWB_CH9_D44_DUALFEED_HYBRID_optimization_history.csv`
- Source balance sweep: `D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_dualfeed_hybrid_opt\UWB_CH9_D44_DUALFEED_HYBRID_source_balance.csv`
- Best JSON: `D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_dualfeed_hybrid_opt\UWB_CH9_D44_DUALFEED_HYBRID_best.json`
- Final topology report directory: `D:\WorkSpace\HFSS Sim\UWB-Antenna-Simulation-By-HFSS\reports_d44_dualfeed_cp`
