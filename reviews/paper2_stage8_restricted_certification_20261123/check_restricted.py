"""Deterministic tests for restricted post-certificate likelihood search."""
from __future__ import annotations
from fractions import Fraction as F
import hashlib, json, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
STAGE6 = HERE.parent / "paper2_stage6_vector_correction_20261122"
STAGE7 = HERE.parent / "paper2_stage7_fixed_amplitude_20261122"
sys.path.insert(0, str(STAGE6))
sys.path.insert(0, str(STAGE7))

from vector_record import VectorRecord, I, D
from direction_cache_corrected import CorrectedFastEnvelope
from restricted_certification import certify_direction_restricted


def main():
    model = json.loads((STAGE6 / "model.json").read_text(encoding="utf8"))
    checks = []

    def check(name, value, detail=None):
        checks.append({"name": name, "pass": bool(value), "detail": detail})
        if not value:
            raise AssertionError((name, detail))

    # An all-send deterministic fixture creates a valid first certificate,
    # whose onset-specific intervals then become the second search domain.
    rows = [(True, ".13", ".001"), (False, None, "-.002"),
            (True, "-.21", "0"), (True, ".37", ".003"),
            (False, None, "0"), (True, "-.09", "-.001"),
            (True, ".16", ".002"), (False, None, "-.003")]
    record = VectorRecord(model)
    envelope = CorrectedFastEnvelope(model)
    for row in rows:
        record.append(*row)
        envelope.advance(row[0])

    direction = (F(1), F(0))
    empty = certify_direction_restricted(record, direction, ".025", {})
    check("empty_restricted_domain_is_unresolved", empty["reason"] == "EMPTY_RETAINED_DOMAIN")
    check("empty_restricted_domain_never_certifies", not empty["certified"])

    # Use a high-information deterministic send record so the precondition
    # (strictly positive full-time confidence threshold) is active.
    record = VectorRecord(model)
    envelope = CorrectedFastEnvelope(model)
    for _ in range(8):
        record.append(True, ".00001", "0")
        envelope.advance(True)
    first = record.certify_direction(direction, ".025", max_nodes=128)
    check("first_full_domain_certificate_succeeds", first["certified"], first)
    envelope.add_certificate(direction, ".025")
    bounds = envelope.bounds
    full = record.certify_direction(direction, ".05", max_nodes=128)
    before = record.stats["likelihood_evaluations"]
    result = certify_direction_restricted(record, direction, ".05", bounds,
                                          max_nodes=128)
    no_witness_evaluations = record.stats["likelihood_evaluations"] - before
    before = record.stats["likelihood_evaluations"]
    result_with_witness = certify_direction_restricted(record, direction, ".05", bounds,
                                          max_nodes=128, require_witness=True)
    witness_evaluations = record.stats["likelihood_evaluations"] - before
    check("restricted_and_full_decisions_agree", result["certified"] == full["certified"],
          {"full": full["reason"], "restricted": result["reason"]})
    check("witnessless_and_witnessed_decisions_agree",
          result["certified"] == result_with_witness["certified"] and
          result["correction"] == result_with_witness["correction"])
    check("witness_scan_is_omitted_by_default",
          no_witness_evaluations < witness_evaluations,
          {"without": no_witness_evaluations, "with": witness_evaluations})
    check("restricted_result_declares_restricted_search", result["restricted"] is True)
    check("retained_domain_is_strictly_narrower_than_full_domain",
          D(result["search_width"]) < D(".25") * len(bounds))
    check("restricted_search_tests_only_retained_onsets",
          result["search_onsets"] <= len(bounds))
    check("restricted_segments_are_nonempty", result["segments_tested"] > 0)
    check("restricted_certificate_preserves_correction_and_gain",
          result["certified"] == full["certified"] and
          (not full["certified"] or result["correction"] == full["correction"] and
           result["guaranteed_gain"] == full["guaranteed_gain"]))
    check("restricted_result_is_certified_or_explicitly_unresolved",
          result["certified"] or result["reason"] in {
              "RESTRICTED_WITNESS_UNRESOLVED", "HEALTH_OR_FUTURE_START_RETAINED", "UNRESOLVED_NODE_LIMIT",
              "UNRESOLVED_OR_FEASIBLE"})

    # An interval above the cap is removed before likelihood evaluation.
    bad = certify_direction_restricted(record, direction, ".025",
                                       {0: (".30", ".40")})
    check("out_of_cap_interval_rejected", bad["reason"] == "EMPTY_RETAINED_DOMAIN")

    # A valid positive interval remains valid if the upper endpoint is larger
    # than the model cap; it is clipped to bmax.
    clipped = certify_direction_restricted(record, direction, ".025",
                                           {0: (".05", ".40")})
    check("upper_endpoint_is_clipped_to_attack_cap", D(clipped["search_width"]) == D(".20"))

    out = {"status": "PASS", "check_count": len(checks), "checks": checks,
           "performance_random_samples_generated": False,
           "source_sha256": hashlib.sha256((HERE / "restricted_certification.py").read_bytes()).hexdigest()}
    (HERE / "restricted_checks.json").write_text(json.dumps(out, indent=2) + "\n",
                                                  encoding="utf8", newline="\n")
    print(json.dumps({"status": out["status"], "check_count": len(checks),
                      "restricted_segments": result["segments_tested"],
                      "restricted_reason": result["reason"]}))


if __name__ == "__main__":
    main()
