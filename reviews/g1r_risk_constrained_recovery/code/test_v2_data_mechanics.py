"""Stage B deterministic fixture checks for gap-8 Replay timing and data reproducibility."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
SIM = ROOT / "simulation"
OLD = ROOT / "reviews/g1_retroactive_recovery/code"
sys.path[:0] = [str(SIM), str(OLD)]
from engine import simulate
from model import generate_data
from minimal_recovery_screen import build_model, common_schedule, R


class ReceiveTrace:
    def __init__(self, model):
        self.edge = int(np.flatnonzero(np.all(model.edges == [0, 1], axis=1))[0])
        self.received = {}

    def update(self, t, fresh, age, aligned, measurement, local_hat):
        if bool(fresh[0, self.edge]):
            self.received[int(t)] = aligned[0, self.edge].copy()
        return np.ones(fresh.shape)


def test_fixed_seed_data_generation_repeats_exactly():
    model = build_model()
    seeds = np.array([0], dtype=np.int64)  # deterministic unit fixture, not study seed
    x1, y1 = generate_data(model, seeds)
    x2, y2 = generate_data(model, seeds)
    assert np.array_equal(x1, x2)
    assert np.array_equal(y1, y2)
    assert x1.shape == (1, model.cfg["T"]+1, model.cfg["n"])
    assert y1.shape == (1, model.cfg["T"], model.cfg["N"], model.cfg["n"])
    process = x1[:, 1:] - np.einsum("ab,stb->sta", model.A, x1[:, :-1])
    measurement = y1 - np.einsum("iab,stb->stia", model.H, x1[:, :-1])
    assert np.all(np.isfinite(process)) and np.all(np.isfinite(measurement))


def test_gap8_schedule_and_single_historical_replay_timing():
    model = build_model()
    schedule = common_schedule(model, 1)
    assert np.all(schedule[0, 0, :])
    for node in range(model.cfg["N"]):
        actual = np.flatnonzero(schedule[0, :, node])
        expected = np.unique(np.r_[0, np.arange(node, model.cfg["T"], 8)])
        assert np.array_equal(actual, expected), node
    sender_times = np.flatnonzero(schedule[0, :, 0])
    assert schedule[0, R, 0] and R % 8 == 0
    source = int(sender_times[sender_times < R][-8])
    q = int(sender_times[sender_times > R][0])
    assert source == R-64 == 136 and schedule[0, source, 0]
    assert q == 208

    # Deterministic measurement fixture: no random state/measurement draw.
    x = np.zeros((1, model.cfg["T"]+1, model.cfg["n"]))
    t = np.arange(model.cfg["T"], dtype=float)
    y = np.zeros((1, model.cfg["T"], model.cfg["N"], model.cfg["n"]))
    for node in range(model.cfg["N"]):
        y[0, :, node, 0] = .001*(node+1)*t
        y[0, :, node, 1] = .0003*(node+2)*t
    seed = np.array([0], dtype=np.int64)
    clean_log, attack_log = ReceiveTrace(model), ReceiveTrace(model)
    clean = simulate(model, x, y, seed, "yang", scenario="clean",
                     schedule=schedule, cache_monitor=clean_log, collect=False)
    attack = simulate(model, x, y, seed, "yang", scenario="replay_packet",
                      schedule=schedule, cache_monitor=attack_log, collect=False)
    edge = clean_log.edge
    assert attack.replay_source[0, R] == source
    assert attack.sends[0, source, 0] and attack.sends[0, R, 0]
    assert attack.injected[0, R]
    assert not np.any(attack.injected[0, np.arange(model.cfg["T"]) != R])
    assert np.allclose(attack_log.received[R], clean.estimates[0, source, 0], atol=1e-12)
    assert np.array_equal(clean.estimates[0, :R+1], attack.estimates[0, :R+1])
    assert np.linalg.norm(attack.estimates[0, R+1, 1]-clean.estimates[0, R+1, 1]) > 0
    assert np.allclose(attack_log.received[q], attack.estimates[0, q, 0], atol=1e-12)
    return {"source_time": source, "replay_time": R, "cache_replaced_time": q,
            "receiver_first_affected_state": R+1,
            "attacked_payload_matches_captured_historical_send": True,
            "post_replay_packet_is_current_sender_estimate": True,
            "no_future_or_unsent_packet_used": True}


def main(out: Path | None = None):
    test_fixed_seed_data_generation_repeats_exactly()
    timing = test_gap8_schedule_and_single_historical_replay_timing()
    result = {"data_generation_repeatability": "PASS_FIXED_SEED_FIXTURE_ONLY",
              "timing": timing, "E2_trajectories": 0,
              "fixed_fixture_seed": 0, "study_seed": None}
    if out is not None:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                       encoding="utf-8", newline="\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    main(args.out if args.out is None or args.out.is_absolute() else ROOT / args.out)
