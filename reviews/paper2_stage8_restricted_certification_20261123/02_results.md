# Stage 8: re-certification over retained parameter intervals

## Frozen-record comparison

This deterministic replay uses nine successful re-certification queries from the independent Stage 7 confirmation seed 202611226603. Each query uses only successful certificates at times strictly earlier than its target time. The physical traces, received histories, target direction, threshold, confidence reference, and continuous likelihood implementation are identical. Only the search domain differs: all onset/amplitude candidates versus the onset-associated intervals retained by earlier certificates.

All nine full-domain and restricted searches certified the target query and returned exactly the same correction vector and guaranteed gain. The restricted search considered 2,932 onset entries across these queries, compared with 4,608 in the full searches; low-support interval segments fell from 9,544 to 3,789. Continuous likelihood calls fell from 19,063 to 7,578.

| Measure | Full domain | Retained domain |
|---|---:|---:|
| Queries | 9 | 9 |
| Likelihood evaluations | 19,063 | 7,578 |
| Low-support intervals tested | 9,544 | 3,789 |
| Mean query time | 53.26 s | 25.27 s |
| Median query time | 45.73 s | 22.67 s |

The ratio of total mean times is 2.11x, and median per-query speedup is 2.48x. One query ran slightly slower under the restricted routine, so timing is not uniform. The exact likelihood-call and interval-segment reductions provide the more stable evidence of lower search work.

| Episode | Retained onsets | Full search | Restricted search | Likelihood calls, full/restricted |
|---:|---:|---:|---:|---:|
| 1 | 384 | 37.50 s | 37.17 s | 1,699 / 1,440 |
| 3 | 382 | 20.29 s | 22.67 s | 1,017 / 764 |
| 5 | 383 | 66.41 s | 43.96 s | 2,712 / 1,532 |
| 6 | 252 | 56.06 s | 16.78 s | 2,007 / 488 |
| 7 | 384 | 54.65 s | 31.43 s | 2,336 / 1,062 |
| 8 | 382 | 93.36 s | 23.42 s | 3,516 / 762 |
| 9 | 254 | 42.75 s | 16.55 s | 1,617 / 508 |
| 10 | 256 | 62.58 s | 17.02 s | 2,488 / 512 |
| 11 | 255 | 45.73 s | 18.45 s | 1,671 / 510 |

## Witness-scan ablation

The no-witness version and the optional witnessed version gave identical decisions and corrections on all nine queries. The witness scan accounted for only 18 additional likelihood calls over all queries, so removing it had little effect in this set. Most of the measured savings came from not revisiting onsets already excluded by earlier certificates.

The deterministic unit checks also cover singleton retained intervals at both safe and low-support endpoints. A singleton with certified support can pass; a singleton that remains in the likelihood confidence set while below the requested support returns unresolved instead of being dropped.

## Scope and limits

This is a deterministic recertification ablation on saved Stage 7 records, not a new random performance experiment. It excludes full trace generation and original record maintenance from query timing. It does not establish a lower endpoint-to-endpoint wall-clock cost for a deployed estimator, nor a confidence failure rate below 0.1%. The statistical MSE results remain those of the separate 36-episode Stage 7 confirmation.

No monitor, trigger, or likelihood definition changed. The formal manuscript was not modified.
