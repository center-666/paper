# Development runs retained for audit

The completed results used in the main report are the deterministic exact/interval checks, `results/replay` direct propagation run, `results/replay_cached_corrected` one-sided cache replay, and the pre-frozen `results/fresh_confirmation` independent sample.

Two intermediate compute experiments are also retained:

- The first all-Fraction long replay prototype exceeded one minute on a single episode and was stopped before producing a result. It generated no random performance sample.
- The first cached-support replay kept each moving direction's dictionary under its original key. Lookup misses therefore fell back to the direct interval support calculation. `results/replay_cached` was interrupted at 33 episodes; the next `results/replay_cached_fast` completed but is not the reported speed result. The stale key did not affect coverage because it triggered the slower direct path.

The corrected implementation updates the direction key together with its adjoint vector. It passed 1,280 deterministic one-sided-bound checks and reproduced all 36 direct-replay outputs exactly. It is the only cache runtime included in the report.
