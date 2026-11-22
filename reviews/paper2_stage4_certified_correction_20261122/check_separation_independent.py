"""Independent 100-digit point recomputation of risk and age certificates.

This check does not generate samples and does not replace directed arithmetic
or analytic proofs. It checks recorded interval outputs against a separately
written scalar implementation and verifies monotonicity beyond each age.
"""
from decimal import Decimal, localcontext
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
D = Decimal


def main():
    record = json.loads((HERE / "separation_bounds.json").read_text(encoding="utf8"))
    checks = []
    for row in record["rows"]:
        with localcontext() as context:
            context.prec = 100
            A = D("0.82") if row["model"] == "S1" else D("1.04")
            Q, R, Z, P0 = D(".05"), D(".2"), D(2), D(".8")
            b, bmax, eps = D(row["b"]), D(".25"), D(".001")
            linear = R - Q - A * A * R
            prior_min = (-linear + (linear * linear + 4 * Q * R).sqrt()) / 2
            gain_min = prior_min / (prior_min + R)
            gain_max = P0 / (P0 + R)
            R0 = R + 1 / Z
            rho = A * R0 / (prior_min + R0)
            gain = gain_max if A < 1 else gain_min
            cB = gain / (1 - A * (1 - gain))
            B = bmax * cB
            p_send = 1 - 1 / (1 + Z * (prior_min + R)).sqrt()
            v = (b * gain_min / 2) ** 2
            eps_limit = v * p_send / (v + 2 * B * B)
            L = 0
            while cB * rho ** L > gain_min / 2:
                L += 1
            assert L == row["forgetting_length"]
            enclosure = row["risk_budget_epsilon_upper_limit"]
            assert D(enclosure["lo"]) <= eps_limit <= D(enclosure["hi"])
            result = {
                "model": row["model"], "b": row["b"], "forgetting_length": L,
                "independent_epsilon_limit_100digit": str(eps_limit),
                "epsilon_limit_inside_recorded_enclosure": True,
            }
            n = row["certified_sufficient_attack_age"]
            if n is not None:
                a = D(row["separation"]["affinity_upper"])
                true_weight = D(".5") / D(201 * 202 * 3)
                bound = (2 * (200 + n) * a ** n + (L - 1) * a ** (n - L + 1)
                         + a ** n) / (eps * true_weight).sqrt()
                improvement = v * (p_send - eps - bound) - 2 * eps * B * B
                assert bound <= D(row["exclusion_failure_upper"])
                assert improvement >= D(row["per_step_expected_gain_lower_at_and_after_age"])
                assert improvement > 0
                ratio = D(n + 201) / D(n + 200) * a
                assert ratio < 1
                result.update({
                    "sufficient_age": n, "independent_exclusion_bound": str(bound),
                    "independent_gain_lower": str(improvement),
                    "next_age_polynomial_exponential_ratio": str(ratio),
                    "monotonic_for_all_later_ages": True,
                })
            else:
                assert v * (p_send - eps) - 2 * eps * B * B <= 0
                result["insufficient_epsilon_budget_confirmed"] = True
            result["status"] = "PASS"
            checks.append(result)
    output = {
        "status": "PASS", "random_samples_generated": False,
        "checks": checks, "check_count": len(checks),
        "scope": "Independent deterministic point calculation; not a replacement for outward interval proofs",
        "input_sha256": hashlib.sha256((HERE / "separation_bounds.json").read_bytes()).hexdigest(),
        "source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    }
    (HERE / "independent_separation_checks.json").write_text(
        json.dumps(output, indent=2) + "\n", encoding="utf8", newline="\n")
    print(json.dumps({"status": "PASS", "cases": len(checks)}))


if __name__ == "__main__":
    main()
