# Stage 8: re-certification over retained parameter intervals

## Frozen-record comparison

This deterministic replay uses nine successful re-certification queries from the independent Stage 7 confirmation seed 202611226603. Each query had at least one earlier successful certificate. The physical traces, received histories, target direction, threshold, confidence reference, and continuous likelihood implementation are identical. Only the search domain differs: all onset/amplitude candidates versus the onset-associated intervals retained by earlier certificates.

All nine full-domain and restricted searches certified the target query and returned exactly the same correction vector and guaranteed gain. The restricted search considered 2,932 onset entries across these queries, compared with 4,608 in the full searches; low-support interval segments fell from 9,544 to 3,789. Continuous likelihood calls fell from 19,063 to 7,578.

| Measure | Full domain | Retained domain |
|---|---:|---:|
| Queries | 9 | 9 |
| Likelihood evaluations | 19,063 | 7,578 |
| Low-support intervals tested | 9,544 | 3,789 |
| Mean query time | 55.05 s | 26.25 s |
| Median query time | 52.20 s | 22.39 s |

The ratio of total mean times is 2.10x, and median per-query speedup is 2.45x. One query ran slightly slower under the restricted routine, so the result supports a workload reduction and a useful speedup on this trace set, not a per-query timing guarantee.

| Episode | Retained onsets | Full search | Restricted search | Likelihood calls, full/restricted |
|---:|---:|---:|---:|---:|
| 1 | 384 | 39.28 s | 40.24 s | 1,699 / 1,440 |
| 3 | 382 | 24.09 s | 22.39 s | 1,017 / 764 |
| 5 | 383 | 75.56 s | 48.93 s | 2,712 / 1,532 |
| 6 | 252 | 56.34 s | 19.11 s | 2,007 / 488 |
| 7 | 384 | 52.20 s | 29.16 s | 2,336 / 1,062 |
| 8 | 382 | 100.42 s | 26.60 s | 3,516 / 762 |
| 9 | 254 | 42.60 s | 15.32 s | 1,617 / 508 |
| 10 | 256 | 59.47 s | 15.86 s | 2,488 / 512 |
| 11 | 255 | 45.51 s | 18.60 s | 1,671 / 510 |

## Witness-scan ablation

The no-witness version and the optional witnessed version gave identical decisions and corrections on all nine queries. The witness scan accounted for only 18 additional likelihood calls over all queries, so removing it had little effect in this set. Most of the measured savings came from not revisiting onsets already excluded by earlier certificates.

## Scope and limits

This is a deterministic recertification ablation on saved Stage 7 records, not a new random performance experiment. It excludes full trace generation and original record maintenance from query timing. It does not establish a lower endpoint-to-endpoint wall-clock cost for a deployed estimator, nor a confidence failure rate below 0.1%. The statistical MSE results remain those of the separate 36-episode Stage 7 confirmation.

No monitor, trigger, or likelihood definition changed. The formal manuscript was not modified.
