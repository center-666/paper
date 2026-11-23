"""Check the stored results against the frozen inputs and certificate lineages."""
from __future__ import annotations

from fractions import Fraction as F
from math import isclose

from paired_recovery import HERE, REVIEWS, inputs, read, sha, source_path, summarize


def verify(mode, protocol, checks):
    frozen_path = HERE / f"{mode}_freeze.json"
    manifest = read(frozen_path)
    digest = sha(frozen_path)
    assert manifest["inputs"] == inputs(protocol)
    assert all(sha(REVIEWS / path) == h for path, h in manifest["inputs"].items())
    if mode == "fresh":
        assert manifest["replay_results_sha256"] == sha(HERE / "replay_summary.json")
    rows = [read(path) for path in (HERE / f"{mode}_episodes").glob("*.json")]
    rows.sort(key=lambda row: (row["case"], row["episode"]))
    expected = [(-1, i) for i in protocol["episode_indices"]] if mode == "replay" else [
        (case, i) for case in range(len(protocol["cases"]))
        for i in range(protocol["episodes_per_case"])]
    assert [(row["case"], row["episode"]) for row in rows] == expected
    assert len({row["final_prefix_hash"] for row in rows}) == len(rows)
    queries = 0
    for row in rows:
        assert row["freeze_sha256"] == digest and row["mode"] == mode
        if mode == "replay":
            archived = read(source_path(row["episode"]))
            assert abs(row["monitor_replay_difference"]) < 1e-9
            assert [(q["time"], F(q["target"]), q["archived_success"]) for q in row["queries"]] == [
                (q["time"], F(q["target_support"]), q["certified"]) for q in archived["certificate_queries"]]
        else:
            assert row["seed"] == protocol["fresh_seed"]
            assert row["onset"] == protocol["cases"][row["case"]]["onset"]
            assert F(row["amplitude"]) == F(protocol["cases"][row["case"]]["b"])
        parent_times = {}
        batch = {}
        for q in row["queries"]:
            if "9" not in q:
                continue
            outcome = q["9"]
            if not outcome["certified"]:
                assert "certificate_id" not in outcome
                continue
            assert outcome["certificate_id"] not in parent_times
            if outcome["source_envelope_id"] is None:
                assert not outcome["parent_certificate_ids"]
            else:
                strict_parents = [cid for cid, t in parent_times.items() if t < q["time"]]
                assert outcome["parent_certificate_ids"] == strict_parents and strict_parents
                identity = (outcome["source_envelope_id"], outcome["prefix_hash"])
                assert batch.setdefault(q["time"], identity) == identity
            parent_times[outcome["certificate_id"]] = q["time"]
        for version in ("8", "9"):
            metric = row["metrics"][version]
            assert metric["coverage_misses"] == 0 and metric["risk_violations"] == 0
            assert metric["guarantee"] >= 0 and metric["false_steps"] <= metric["nonzero_steps"]
            if not F(row["amplitude"]):
                assert metric["false_steps"] == metric["nonzero_steps"]
            assert isclose(metric["sample_gain"],
                           row["metrics"]["monitor"]["loss"] - metric["loss"], abs_tol=1e-12)
            timing = row["timing"][version]
            assert isclose(timing["end_to_end"], sum(row["shared_timing"].values()) +
                           sum(timing[k] for k in ("advance", "query", "commit", "output")))
        queries += len(row["queries"])
    summary = read(HERE / f"{mode}_summary.json")
    assert summary == summarize(rows, mode, digest)
    checks[mode] = {"episodes": len(rows), "logged_queries": queries,
                    "verified_stage9_certificate_ids": sum(
                        "certificate_id" in q.get("9", {}) for row in rows for q in row["queries"])}
    return set(row["final_prefix_hash"] for row in rows)


def main():
    protocol = read(HERE / "stage9_protocol.json")
    deterministic = read(HERE / "stage9_checks.json")
    assert deterministic["status"] == "PASS"
    assert deterministic["source_sha256"] == sha(HERE / "cumulative_envelope.py")
    assert len(deterministic["checks"]) == deterministic["check_count"]
    assert all(row["pass"] for row in deterministic["checks"])
    checks = {}
    replay = verify("replay", protocol, checks)
    fresh = verify("fresh", protocol, checks)
    assert replay.isdisjoint(fresh)
    print({"deterministic_checks": deterministic["check_count"], **checks})


if __name__ == "__main__":
    main()
