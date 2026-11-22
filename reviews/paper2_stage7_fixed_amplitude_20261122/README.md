# Stage 7: retain fixed-amplitude attack information

This research package tests onset-associated amplitude intervals derived from successful directional certificates. It preserves the fixed onset and constant attack-amplitude assumptions from Stage 6 and does not change the estimator, event trigger, likelihood, or monitor.

## Main files

- [01_fixed_parameter_theory.md](01_fixed_parameter_theory.md): coverage, amplitude-interval, propagation, and risk-improvement arguments.
- [02_algorithm_and_validation.md](02_algorithm_and_validation.md): online update, deterministic checks, and incremental direction cache.
- [07_frozen_replay_results.md](07_frozen_replay_results.md): paired Stage 6 replay outcomes and compute results.
- [stage7_protocol.json](stage7_protocol.json), [stage7_freeze.json](stage7_freeze.json): replay design and frozen source/trace hashes.
- [fresh_protocol.json](fresh_protocol.json), [fresh_confirmation_freeze.json](fresh_confirmation_freeze.json): independent confirmation protocol and pre-sample freeze.
- [08_fresh_confirmation_results.md](08_fresh_confirmation_results.md): full-search independent-seed confirmation results.
- [fresh_confirmation.py](fresh_confirmation.py), [summarize_fresh.py](summarize_fresh.py): full-run and aggregate-analysis programs.
- [audit_fresh_response.py](audit_fresh_response.py), [analysis/fresh_response_audit.json](analysis/fresh_response_audit.json): exact long-trace response and certificate audit on the same frozen seeds.
- [fixed_amplitude.py](fixed_amplitude.py): exact rational theorem/check implementation and outward interval propagation.
- [direction_cache_corrected.py](direction_cache_corrected.py): incremental one-sided support cache.
- [replay_stage6.py](replay_stage6.py): direct support baseline for frozen-trace ablation.
- [replay_stage6_corrected.py](replay_stage6_corrected.py): cache-equivalence replay.
- [deterministic_checks.json](deterministic_checks.json), [direction_cache_corrected_checks.json](direction_cache_corrected_checks.json): reproducible check outputs.
- [development_notes.md](development_notes.md): retained early prototypes and why they are excluded from the reported timing.
- [analysis/replay_summary.json](analysis/replay_summary.json), [analysis/cache_equivalence.json](analysis/cache_equivalence.json): aggregate paired metrics and cache parity.

## Current result

On the same 12 Stage 6 strong-attack episodes, the new correction remained above the useful action threshold at lag 50 in 8/12 cases, versus 0/12 under legacy propagation. The paired 512-step MSE gain difference was 1.6376, with a descriptive 95% Student-t interval [0.2673, 3.0079]. The health and weak-attack controls retained zero correction. These traces supported algorithm design and are not an independent confirmation sample.

The corrected support cache produces exactly the same outputs as direct support evaluation on all 36 traces. Strong-attack mean support time fell 15.4-fold (81.97 to 5.33 seconds); full replay time fell from 92.05 to 17.07 seconds per episode, excluding likelihood certification.

An independent 36-episode confirmation then used new seed 202611226603 and the full likelihood search. For strong attacks, certificates succeeded in 11/12 episodes, useful lag-50 corrections occurred in 8/12, and the 512-step paired MSE improvement difference was 2.0869 with descriptive 95% Student-t interval [0.9417, 3.2322]. Healthy and weak-attack groups remained at zero correction. Full-search mean runtime was 346 seconds per strong-attack episode.

The formal manuscript remains unchanged. Larger samples, model mismatch, and finite-word-length communication remain to be studied.
