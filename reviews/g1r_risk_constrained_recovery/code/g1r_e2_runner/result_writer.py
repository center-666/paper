from __future__ import annotations

import csv
import hashlib
import io
import json
import os
from pathlib import Path
import tempfile
from typing import Any

from .config_loader import canonical_sha256
from .online_proposal import ProposalRecord, record_dict

RESULT_FIELDS = (
    "sample_id", "trial_run_id", "seed", "scenario", "main_case", "event", "age",
    "method", "raw_status", "proposal_status", "gate_status", "score", "threshold",
    "proposal_vector_json", "final_action_json", "set_proposal_norm", "set_action_norm",
    "coverage_confirmed", "compatible_event_count", "zero_or_unresolved", "solver_stage",
    "solver_gap", "solver_reject_reason", "execution_success", "replay_source_time",
    "actual_replay_age", "cache_replacement_time", "first_pollution_state",
    "first_receiver_pollution_state", "true_impact_x", "true_impact_y", "simulation_status",
    "statistical_cluster", "online_record_sha256", "online_record_ordinal",
)


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def canonical_json_bytes(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, ensure_ascii=True, separators=(",", ":"),
                       allow_nan=False) + "\n").encode("utf-8")


def csv_bytes(rows: list[dict[str, Any]], fields=RESULT_FIELDS) -> bytes:
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=list(fields), extrasaction="raise",
                            lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue().encode("utf-8")


def write_exclusive(path: Path, payload: bytes) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp",
                                             dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        try:
            os.link(temporary, path)
        except FileExistsError:
            existing = path.read_bytes()
            if existing != payload:
                raise FileExistsError(f"refusing to overwrite an existing result: {path}")
            return sha256_bytes(existing)
    finally:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
    return sha256_bytes(payload)


def write_replace_atomic(path: Path, payload: bytes) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp",
                                             dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    except Exception:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise
    return sha256_bytes(payload)


class ResultWriter:
    def __init__(self, run_dir: Path):
        self.run_dir = run_dir
        self.shard_dir = run_dir / "seed_shards"
        self.shard_dir.mkdir(parents=True, exist_ok=True)

    def seed_paths(self, group: str, batch_index: int, seed: int) -> tuple[Path, Path]:
        stem = f"{group}_batch_{batch_index:02d}_seed_{int(seed)}"
        return (self.shard_dir / f"{stem}_online.jsonl",
                self.shard_dir / f"{stem}_offline.csv")

    def serialize_online(self, records: list[ProposalRecord]) -> bytes:
        return b"".join(canonical_json_bytes({"ordinal": index, "proposal": record_dict(record)})
                        for index, record in enumerate(records))

    def write_online_seed(self, group: str, batch_index: int, seed: int,
                          records: list[ProposalRecord]) -> tuple[Path, str]:
        online_path, _ = self.seed_paths(group, batch_index, seed)
        payload = self.serialize_online(records)
        return online_path, write_exclusive(online_path, payload)

    def serialize_offline(self, rows: list[dict[str, Any]]) -> bytes:
        return csv_bytes(rows)

    def write_offline_seed(self, group: str, batch_index: int, seed: int,
                           rows: list[dict[str, Any]]) -> tuple[Path, str]:
        _, offline_path = self.seed_paths(group, batch_index, seed)
        payload = self.serialize_offline(rows)
        return offline_path, write_exclusive(offline_path, payload)

    def write_batch_csv(self, group: str, batch_index: int, seeds: tuple[int, ...],
                        rows: list[dict[str, Any]]) -> tuple[Path, str]:
        path = self.run_dir / f"{group}_batch_{batch_index:02d}.csv"
        expected_rows = len(seeds) * (3 if group == "normal" else 24 * 3)
        if len(rows) != expected_rows:
            raise ValueError(f"batch has {len(rows)} rows, expected {expected_rows}")
        return path, write_exclusive(path, csv_bytes(rows))

    def write_run_artifact_manifest(self, metadata: dict[str, Any]) -> Path:
        files = {}
        for path in sorted(self.run_dir.rglob("*")):
            if path.is_file() and path.name != "artifact_manifest.json":
                files[path.relative_to(self.run_dir).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
        payload = {**metadata, "files_sha256": files,
                   "manifest_content_sha256": canonical_sha256(files)}
        target = self.run_dir / "artifact_manifest.json"
        write_exclusive(target, canonical_json_bytes(payload))
        return target

    def read_offline_seed(self, path: Path) -> list[dict[str, str]]:
        with path.open("r", encoding="utf-8", newline="") as stream:
            return list(csv.DictReader(stream))
