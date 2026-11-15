from __future__ import annotations

from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import time
from typing import Any

import numpy as np

from .authorization_guard import RunAuthorization, require_formal_e2
from .checkpoint_manager import CheckpointManager
from .config_loader import FrozenConfig, canonical_sha256, load_public_model, sha256_file
from .integrity_checker import (source_hash_manifest, validate_batch_rows,
                                validate_full_run)
from .offline_evaluator import evaluate
from .online_proposal import (ProposalRecord, build_online_input, failed_proposal_record,
                              propose, record_dict)
from .result_writer import ResultWriter, canonical_json_bytes, write_exclusive
from .scenario_builder import OfflineTruth, ScenarioBuilder
from .statistics_reporter import benchmark_cached, independent_recompute, summarize_rows


class BatchRunner:
    def __init__(self, config: FrozenConfig, authorization: RunAuthorization,
                 output_dir: Path):
        self.config = config
        self.authorization = authorization
        self.output_dir = Path(output_dir).resolve()
        self.public_model = load_public_model(config)

    def run_dry_run(self) -> dict[str, Any]:
        if self.authorization.mode != "dry_run":
            raise PermissionError("dry-run path requires dry-run authorization")
        if self.output_dir.exists() and any(self.output_dir.iterdir()):
            raise FileExistsError(f"dry-run output already exists: {self.output_dir}")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        writer = ResultWriter(self.output_dir)
        cache_path = (self.config.base /
                      "results/g1r_e2_status_resolution_20261115_r01/cached_debug_features.npz")
        expected_cache_sha = "3d8137456ee2da019b2e18615f56166c6e6cef3c63fb0d19c59d0a8b28dfbd09"
        if sha256_file(cache_path) != expected_cache_sha:
            raise ValueError("existing Debug cache SHA mismatch")
        debug_records = []
        with np.load(cache_path, allow_pickle=False) as archive:
            expected_keys = {f"{scenario}_{seed}"
                             for scenario in ("clean", "replay_packet")
                             for seed in range(141400000, 141400005)}
            if set(archive.files) != expected_keys:
                raise ValueError("Debug cache differs from frozen five-seed diagnostics")
            for key in sorted(expected_keys):
                scenario, seed_text = key.rsplit("_", 1)
                z = np.asarray(archive[key], dtype=np.float64)
                for method in self.config.methods:
                    online = build_online_input(z, self.public_model,
                                                self.config.thresholds[method], method)
                    record = propose(online)
                    debug_records.append({
                        "debug_case": key, "scenario": scenario,
                        "debug_seed": int(seed_text), "proposal": record_dict(record),
                    })
        debug_payload = b"".join(canonical_json_bytes(row) for row in debug_records)
        debug_path = self.output_dir / "cached_debug_proposals.jsonl"
        debug_sha = write_exclusive(debug_path, debug_payload)

        fixture_grid = ScenarioBuilder(self.config, self.public_model).build_fixture_grid(0)
        fixture_records = []
        fixture_rows = []
        ordinal = 0
        fixture_coverage_cache = {}
        for case in (fixture_grid.normal,) + fixture_grid.replays:
            for method in self.config.methods:
                online = build_online_input(case.online_input.z,
                                            case.online_input.frozen_public_model,
                                            self.config.thresholds[method], method)
                record = propose(online)
                fixture_records.append({"ordinal": ordinal, "proposal": record_dict(record)})
                row = evaluate(record, case.offline_truth, self.public_model,
                               fixture_coverage_cache)
                row["online_record_ordinal"] = ordinal
                row["trial_run_id"] = f"fixture:0:{method}"
                fixture_rows.append(row)
                ordinal += 1
        online_path = self.output_dir / "fixture_online_proposals.jsonl"
        online_sha = write_exclusive(
            online_path, b"".join(canonical_json_bytes(row) for row in fixture_records))
        fixture_path = self.output_dir / "fixture_result_rows.csv"
        fixture_payload = writer.serialize_offline(fixture_rows)
        fixture_sha = write_exclusive(fixture_path, fixture_payload)
        timings = benchmark_cached(self.config, self.public_model, cache_path)
        header_bytes = len(fixture_payload.splitlines()[0]) + 1
        offline_row_bytes = max(0, len(fixture_payload) - header_bytes) / max(1, len(fixture_rows))
        planned_rows = 200 * len(self.config.methods) * (
            1 + len(self.config.events) * len(self.config.ages))
        online_bytes = timings["serialized_proposal_record_bytes_mean"] * planned_rows
        offline_bytes = offline_row_bytes * planned_rows * 3  # seed shards, batch CSVs, aggregate CSV
        timings.update({
            "fixture_final_result_csv_bytes": len(fixture_payload),
            "fixture_final_result_row_bytes_mean": offline_row_bytes,
            "projected_e2_online_proposal_bytes": online_bytes,
            "projected_e2_offline_result_bytes_three_copies": offline_bytes,
            "projected_e2_primary_storage_bytes_excluding_failure_archive": online_bytes + offline_bytes,
            "storage_estimate_note": "projection uses observed Debug proposal JSONL size and fixture final-row CSV size; failure_cases.json/checkpoints/manifests add overhead",
        })
        performance_path = self.output_dir / "performance.json"
        performance_sha = write_exclusive(performance_path, canonical_json_bytes(timings))
        source_manifest = source_hash_manifest(self.config, cache_path)
        source_path = self.output_dir / "source_hashes.json"
        source_sha = write_exclusive(source_path, canonical_json_bytes(source_manifest))
        main_timing = next(check for check in fixture_grid.timing_checks
                           if (check["edge"], check["replay_time"]) == self.config.main_event
                           and check["actual_age"] == 64)
        timing_path = self.output_dir / "fixture_timing.json"
        fixture_timing = {"main_case": main_timing,
                          "event_age_cases": list(fixture_grid.timing_checks),
                          "case_count": len(fixture_grid.timing_checks),
                          "all_fixture_seed": 0}
        timing_sha = write_exclusive(timing_path, canonical_json_bytes(fixture_timing))
        run_config = {
            "run_id": self.output_dir.name, "mode": "dry_run",
            "formal_e2": False, "formal_e3": False,
            "new_formal_trajectories": 0, "study_seeds_used": [],
            "fixture_seed_used": 0, "debug_cache_sha256": expected_cache_sha,
            "frozen_config_sha256": self.config.runner_config_sha256,
            "protocol_sha256": self.config.protocol_sha256,
            "thresholds_sha256": self.config.thresholds_sha256,
            "source_hashes_sha256": source_sha,
            "formal_authorization_file_created": False,
            "online_proposal_rows": len(debug_records),
            "fixture_online_proposal_rows": len(fixture_records),
            "fixture_attack_event_age_cases": len(fixture_grid.replays),
        }
        config_path = self.output_dir / "dry_run_config.json"
        config_sha = write_exclusive(config_path, canonical_json_bytes(run_config))
        manifest = {
            "run_id": self.output_dir.name, "mode": "dry_run",
            "formal_e2_executed": False, "formal_e3_executed": False,
            "official_seed_generation": False,
            "artifacts": {
                "cached_debug_proposals.jsonl": debug_sha,
                "fixture_online_proposals.jsonl": online_sha,
                "fixture_result_rows.csv": fixture_sha,
                "fixture_timing.json": timing_sha,
                "performance.json": performance_sha,
                "source_hashes.json": source_sha,
                "dry_run_config.json": config_sha,
            },
        }
        manifest_path = self.output_dir / "dry_run_manifest.json"
        manifest_sha = write_exclusive(manifest_path, canonical_json_bytes(manifest))
        return {**manifest, "dry_run_manifest_sha256": manifest_sha,
                "performance": timings, "fixture_timing": fixture_timing}

    def run_formal_e2(self) -> dict[str, Any]:
        """Future path; unreachable without a valid owner-bound RunAuthorization."""
        require_formal_e2(self.authorization, self.config)
        config_path = self.output_dir / "config.json"
        checkpoint_path = self.output_dir / "checkpoint.json"
        if self.output_dir.exists() and any(self.output_dir.iterdir()):
            if not config_path.is_file():
                raise FileExistsError(f"existing Run has no validated config: {self.output_dir}")
            prior_config = json.loads(config_path.read_text(encoding="utf-8"))
            if (prior_config.get("mode") != "formal_e2"
                    or prior_config.get("frozen_config_sha256") != self.config.runner_config_sha256
                    or prior_config.get("authorization_id") != self.authorization.authorization_id
                    or prior_config.get("owner") != self.authorization.owner
                    or prior_config.get("authorization_file_sha256") != self.authorization.authorization_file_sha256
                    or prior_config.get("authorization_bindings") != dict(self.authorization.bindings)):
                raise FileExistsError("existing Run ID is bound to a different config/authorization")
        plan = self._batch_plan()
        debug_cache_path = (self.config.base /
                            "results/g1r_e2_status_resolution_20261115_r01/cached_debug_features.npz")
        source_hashes = source_hash_manifest(self.config, debug_cache_path)
        source_hashes_path = self.output_dir / "source_hashes.json"
        source_hashes_payload = canonical_json_bytes(source_hashes)
        source_hashes_sha = hashlib.sha256(source_hashes_payload).hexdigest()
        config_record = {
            "run_id": self.output_dir.name, "mode": "formal_e2",
            "authorization_id": self.authorization.authorization_id,
            "owner": self.authorization.owner,
            "authorization_file_sha256": self.authorization.authorization_file_sha256,
            "authorization_bindings": dict(self.authorization.bindings),
            "frozen_config_sha256": self.config.runner_config_sha256,
            "source_hashes_sha256": source_hashes_sha,
            "batch_size": self.config.batch_size,
            "protocol_sha256": self.config.protocol_sha256,
            "calibration_thresholds_sha256": self.config.thresholds_sha256,
            "seed_scan_sha256": self.config.attack_seed_scan_sha256,
            "U_common": float(self.config.protocol["U_common"]),
            "fixed_schedule": "t=0 all nodes; thereafter sender j transmits iff t mod 8=j",
            "innovation_times": self.config.protocol["innovation_times"],
            "target_time": self.config.target_time,
            "candidate_events": [list(event) for event in self.config.events],
            "ages": list(self.config.ages),
            "batch_plan": [{"group": g, "index": i, "seeds": list(s)} for g, i, s in plan],
            "formal_e3_executed": False,
        }
        self.output_dir.mkdir(parents=True, exist_ok=True)
        write_exclusive(config_path, canonical_json_bytes(config_record))
        write_exclusive(source_hashes_path, source_hashes_payload)
        writer = ResultWriter(self.output_dir)
        checkpoint = CheckpointManager(checkpoint_path,
                                       self.output_dir.name, "formal_e2")
        builder = ScenarioBuilder(self.config, self.public_model)
        all_rows = []
        batch_paths = {"normal": [], "attack": []}
        for group, batch_index, seeds in plan:
            batch_id = f"{group}_batch_{batch_index:02d}"
            completed_batch = checkpoint.batch_entry(batch_id)
            batch_file = self.output_dir / f"{batch_id}.csv"
            if completed_batch is not None:
                if (completed_batch["result_path"] != batch_file.as_posix()
                        or not batch_file.is_file()
                        or sha256_file(batch_file) != completed_batch["result_sha256"]):
                    raise RuntimeError(f"completed batch integrity failure: {batch_id}")
                rows = writer.read_offline_seed(batch_file)
                validate_batch_rows(self.config, group, seeds, rows)
                for seed in seeds:
                    online_path, offline_path = writer.seed_paths(group, batch_index, seed)
                    if not checkpoint.seed_is_complete(group, seed, online_path, offline_path):
                        raise RuntimeError(f"completed batch has an incomplete seed shard: {group}:{seed}")
                all_rows.extend(rows)
                batch_paths[group].append(batch_file)
                continue

            batch_rows = []
            for seed in seeds:
                online_path, offline_path = writer.seed_paths(group, batch_index, seed)
                if checkpoint.seed_is_complete(group, seed, online_path, offline_path):
                    batch_rows.extend(writer.read_offline_seed(offline_path))
                    continue
                records, truths = self._process_seed(builder, group, seed, seeds, batch_index)
                online_saved_path, online_sha = writer.write_online_seed(
                    group, batch_index, seed, records)
                # No event, age, true impact, or health counterfactual enters this call.
                rows = []
                offline_coverage_cache = {}
                for ordinal, (record, truth) in enumerate(zip(records, truths)):
                    row = evaluate(record, truth, self.public_model,
                                   offline_coverage_cache)
                    row["online_record_ordinal"] = ordinal
                    row["trial_run_id"] = f"{self.output_dir.name}:{group}:{seed}"
                    rows.append(row)
                validate_batch_rows(self.config, group, (seed,), rows)
                offline_saved_path, offline_sha = writer.write_offline_seed(
                    group, batch_index, seed, rows)
                checkpoint.mark_seed_complete(group, seed, online_saved_path,
                                              online_sha, offline_saved_path, offline_sha)
                batch_rows.extend(rows)

            validate_batch_rows(self.config, group, seeds, batch_rows)
            result_path, result_sha = writer.write_batch_csv(
                group, batch_index, seeds, batch_rows)
            checkpoint.mark_batch_complete(batch_id, seeds, result_path, result_sha)
            all_rows.extend(batch_rows)
            batch_paths[group].append(result_path)

        if len(checkpoint.state["completed_batches"]) != 20:
            raise RuntimeError("statistics remain blocked until all twenty batches complete")
        normal_rows = [row for row in all_rows if row["scenario"] == "normal"]
        attack_rows = [row for row in all_rows if row["scenario"] == "replay"]
        validate_full_run(self.config, normal_rows, attack_rows)
        in_memory_summary = summarize_rows(self.config, all_rows)
        write_exclusive(self.output_dir / "per_seed_metrics.csv",
                        writer.serialize_offline(all_rows))
        independently_recomputed = independent_recompute(
            self.config, tuple(batch_paths["normal"]), tuple(batch_paths["attack"]))
        independent_match = (
            canonical_sha256(in_memory_summary["methods"])
            == canonical_sha256(independently_recomputed["methods"])
            and canonical_sha256(in_memory_summary["event_age_strata"])
            == canonical_sha256(independently_recomputed["event_age_strata"]))
        if not independent_match:
            raise RuntimeError("independent CSV statistics do not match in-memory gate counts")
        summary = independently_recomputed
        summary["formal_experiment_executed"] = True
        summary["e3_executed"] = False
        write_exclusive(self.output_dir / "statistics_audit.json",
                        canonical_json_bytes({
                            "result": "PASS_INDEPENDENT_CSV_RECOMPUTE",
                            "batch_count": 20,
                            "normal_batch_files": len(batch_paths["normal"]),
                            "attack_batch_files": len(batch_paths["attack"]),
                            "in_memory_vs_csv_summary_match": True,
                            "all_seed_rows_included": True,
                            "e2_statistics_recomputed_from_batch_csv": True,
                        }))
        failures = [row for row in all_rows
                    if str(row["simulation_status"]).startswith("FAIL:")
                    or row["proposal_status"] in {"SOLVER_REJECT", "MODEL_INVALID", "EMPTY_UNION"}
                    or row["gate_status"] == "GATE_REJECT"]
        write_exclusive(self.output_dir / "failure_cases.json",
                        canonical_json_bytes({"failure_or_rejection_rows": failures,
                                              "count": len(failures),
                                              "all_rows_remain_in_per_seed_metrics": True}))
        write_exclusive(self.output_dir / "gate_counts.json", canonical_json_bytes(summary))
        writer.write_run_artifact_manifest({
            "run_id": self.output_dir.name,
            "formal_e2_executed": True, "formal_e3_executed": False,
            "authorized_by": self.authorization.owner,
            "authorization_id": self.authorization.authorization_id,
            "batch_count": 20,
        })
        return summary

    def _batch_plan(self):
        plan = []
        for group, seeds in (("normal", self.config.normal_seeds),
                             ("attack", self.config.attack_seeds)):
            if len(set(seeds)) != len(seeds):
                raise ValueError(f"duplicate frozen seed in {group} manifest")
            for index, start in enumerate(range(0, len(seeds), self.config.batch_size)):
                plan.append((group, index, tuple(seeds[start:start + self.config.batch_size])))
        if len(plan) != 20:
            raise ValueError(f"frozen batch plan contains {len(plan)} batches, expected 20")
        return tuple(plan)

    def _process_seed(self, builder: ScenarioBuilder, group: str, seed: int,
                      batch_seeds: tuple[int, ...], batch_index: int):
        records: list[ProposalRecord] = []
        truths: list[OfflineTruth] = []
        auth = self.authorization
        if group == "normal":
            try:
                case = builder.build_formal_normal(seed, auth)
            except Exception as exc:
                truth = OfflineTruth("normal", seed, True, None, None, None, None,
                                     None, None, None, None, None, None,
                                     f"FAIL:{type(exc).__name__}:{exc}", f"normal:{seed}")
                records = [failed_proposal_record(method, self.config.thresholds[method],
                                                  f"scenario_failure:{type(exc).__name__}:{exc}")
                           for method in self.config.methods]
                truths = [truth] * len(self.config.methods)
                return records, truths
            for method in self.config.methods:
                try:
                    online = build_online_input(case.online_input.z, self.public_model,
                                                self.config.thresholds[method], method)
                    records.append(propose(online))
                    truths.append(case.offline_truth)
                except Exception as exc:
                    records.append(failed_proposal_record(
                        method, self.config.thresholds[method],
                        f"proposal_failure:{type(exc).__name__}:{exc}"))
                    truths.append(case.offline_truth)
            return records, truths

        try:
            context = builder.prepare_formal_attack_seed(seed, auth)
            for event in self.config.events:
                for age in self.config.ages:
                    try:
                        case = builder.build_formal_replay(seed, event, age, auth, context)
                    except Exception as exc:
                        main = event == self.config.main_event and age == 64
                        truth = OfflineTruth(
                            "replay", seed, main, event, age, None, None, None, None, None,
                            None, None, None,
                            f"FAIL:{type(exc).__name__}:{exc}", f"attack:{seed}")
                        records.extend([
                            failed_proposal_record(method, self.config.thresholds[method],
                                                   f"scenario_failure:{type(exc).__name__}:{exc}")
                            for method in self.config.methods])
                        truths.extend([truth] * len(self.config.methods))
                        continue
                    for method in self.config.methods:
                        try:
                            online = build_online_input(case.online_input.z, self.public_model,
                                                        self.config.thresholds[method], method)
                            records.append(propose(online))
                        except Exception as exc:
                            records.append(failed_proposal_record(
                                method, self.config.thresholds[method],
                                f"proposal_failure:{type(exc).__name__}:{exc}"))
                        truths.append(case.offline_truth)
        except Exception as exc:
            records, truths = [], []
            for event in self.config.events:
                for age in self.config.ages:
                    main = event == self.config.main_event and age == 64
                    truth = OfflineTruth(
                        "replay", seed, main, event, age, None, None, None, None, None,
                        None, None, None,
                        f"FAIL:{type(exc).__name__}:{exc}", f"attack:{seed}")
                    for method in self.config.methods:
                        records.append(failed_proposal_record(
                            method, self.config.thresholds[method],
                            f"seed_failure:{type(exc).__name__}:{exc}"))
                        truths.append(truth)
        expected = len(self.config.events) * len(self.config.ages) * len(self.config.methods)
        if len(records) != expected or len(truths) != expected:
            raise RuntimeError("attack seed did not retain the full frozen event-age-method grid")
        return records, truths
