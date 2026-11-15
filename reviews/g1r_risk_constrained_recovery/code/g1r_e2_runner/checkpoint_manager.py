from __future__ import annotations

import json
from pathlib import Path
import threading

from .config_loader import canonical_sha256
from .result_writer import sha256_bytes, write_replace_atomic


class CheckpointError(RuntimeError):
    pass


class CheckpointManager:
    """Append-only seed completion ledger with atomic checkpoint replacement."""

    def __init__(self, path: Path, run_id: str, mode: str):
        self.path = path
        self.run_id = str(run_id)
        self.mode = str(mode)
        self._lock = threading.Lock()
        if path.exists():
            state = json.loads(path.read_text(encoding="utf-8"))
            if state.get("run_id") != self.run_id or state.get("mode") != self.mode:
                raise CheckpointError("checkpoint belongs to a different run or mode")
            self.state = state
            if self.state.get("state_sha256") != self._state_digest(self.state):
                raise CheckpointError("checkpoint integrity hash mismatch")
        else:
            self.state = {"run_id": self.run_id, "mode": self.mode,
                          "completed_seeds": {}, "completed_batches": {}}
            self._persist()

    @staticmethod
    def _state_digest(state) -> str:
        copy = {k: v for k, v in state.items() if k != "state_sha256"}
        return canonical_sha256(copy)

    def _persist(self):
        self.state["state_sha256"] = self._state_digest(self.state)
        payload = (json.dumps(self.state, ensure_ascii=True, sort_keys=True,
                              separators=(",", ":"), allow_nan=False) + "\n").encode()
        write_replace_atomic(self.path, payload)

    def seed_entry(self, group: str, seed: int):
        return self.state["completed_seeds"].get(f"{group}:{int(seed)}")

    def seed_is_complete(self, group: str, seed: int, online_path: Path, offline_path: Path) -> bool:
        entry = self.seed_entry(group, seed)
        if entry is None:
            return False
        for key, path in (("online_path", online_path), ("offline_path", offline_path)):
            if entry[key] != path.as_posix() or not path.is_file():
                raise CheckpointError(f"completed seed output is missing or moved: {path}")
        if (self._file_sha(online_path) != entry["online_sha256"]
                or self._file_sha(offline_path) != entry["offline_sha256"]):
            raise CheckpointError(f"completed seed output changed: {group}:{seed}")
        return True

    def mark_seed_complete(self, group: str, seed: int, online_path: Path,
                           online_sha256: str, offline_path: Path,
                           offline_sha256: str):
        key = f"{group}:{int(seed)}"
        entry = {
            "online_path": online_path.as_posix(), "online_sha256": online_sha256,
            "offline_path": offline_path.as_posix(), "offline_sha256": offline_sha256,
        }
        with self._lock:
            existing = self.state["completed_seeds"].get(key)
            if existing is not None and existing != entry:
                raise CheckpointError(f"refusing to replace completed seed: {key}")
            self.state["completed_seeds"][key] = entry
            self._persist()

    def batch_entry(self, batch_id: str):
        return self.state["completed_batches"].get(batch_id)

    def mark_batch_complete(self, batch_id: str, seeds: tuple[int, ...],
                            result_path: Path, result_sha256: str):
        entry = {"seeds": list(map(int, seeds)), "result_path": result_path.as_posix(),
                 "result_sha256": result_sha256}
        with self._lock:
            old = self.state["completed_batches"].get(batch_id)
            if old is not None and old != entry:
                raise CheckpointError(f"refusing to replace completed batch: {batch_id}")
            self.state["completed_batches"][batch_id] = entry
            self._persist()

    @staticmethod
    def _file_sha(path: Path) -> str:
        return sha256_bytes(path.read_bytes())
