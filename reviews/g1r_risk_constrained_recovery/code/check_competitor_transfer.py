"""Exact finite examples for theorem-transfer limits; no filter or simulation.

These examples are NOT reproductions or counterexamples to the complete
PALM-DKF algorithm. They test two stronger inferences one must not make from
its printed prior-truncation and component-consistency statements.
"""
from __future__ import annotations

import argparse
from fractions import Fraction as F
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[3]


def write(path, value):
    Path(path).write_text(json.dumps(value, indent=2, ensure_ascii=False,
                                   allow_nan=False) + "\n", encoding="utf-8")


def main(out):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=False)
    source = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    write(out / "frozen_plan.json", {
        "run_id": out.name, "source_sha256": source,
        "baseline_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT).decode().strip(),
        "scope": "exact finite algebra; no Yang model, samples, fitting or performance comparison",
        "claims": ["prior-discard mass cannot replace posterior-discard mass after likelihood update",
                   "marginal component consistency alone does not imply adaptive mixture consistency"],
        "new_trajectories": 0, "random_seed": None,
    })

    # Correct prior-mixture algebra remains valid. Only the stronger extension
    # of that bound to likelihood-weighted estimates is contradicted here.
    priors = [F(99, 100), F(1, 100)]
    likelihoods = [F(1, 1000), F(1)]
    means = [F(0), F(10)]
    weights = [p * ell for p, ell in zip(priors, likelihoods)]
    weights = [p / sum(weights) for p in weights]
    posterior_full = sum(p * mu for p, mu in zip(weights, means))
    prior_full = sum(p * mu for p, mu in zip(priors, means))
    eps_prior, eps_posterior = priors[1], weights[1]
    prior_diameter_bound = eps_prior * 10
    posterior_diameter_bound = eps_posterior * 10
    assert prior_full == prior_diameter_bound
    assert posterior_full > 2 * 10 * eps_prior
    assert posterior_full == posterior_diameter_bound

    # Two equally likely outcomes, common true state zero and fixed delivered
    # set. Each fixed estimator has E(error^2)=2 and reports P=2. Choosing
    # data-dependent weights favouring its larger error breaks the implication
    # unless stronger conditional/posterior calibration is established.
    p = F(99, 100)
    mean = 2 * p
    reported = 2 + p * (1 - p) * 4
    actual = mean ** 2
    assert reported < actual

    write(out / "checks.json", {
        "prior_vs_posterior_truncation": {
            "prior_weights": list(map(float, priors)),
            "likelihoods": list(map(float, likelihoods)),
            "component_means": list(map(float, means)),
            "posterior_weights": list(map(float, weights)),
            "prior_discard_mass": float(eps_prior),
            "posterior_discard_mass": float(eps_posterior),
            "prior_weighted_error": float(prior_full),
            "actual_posterior_weighted_error": float(posterior_full),
            "twice_xbar_times_prior_mass": float(20 * eps_prior),
            "posterior_mass_times_diameter": float(posterior_diameter_bound),
            "valid_prior_mixture_identity_preserved": True,
        },
        "marginal_vs_data_adaptive_consistency": {
            "outcomes_probability": [.5, .5],
            "true_state": 0,
            "component_estimates_by_outcome": [[2, 0], [0, 2]],
            "each_component_actual_second_moment": 2,
            "each_component_reported_covariance": 2,
            "adaptive_weights_by_outcome": [[.99, .01], [.01, .99]],
            "mixture_actual_second_moment": float(actual),
            "mixture_reported_covariance": float(reported),
            "inference_without_stronger_condition_is_false": True,
        },
        "limitations": [
            "Neither example reproduces the PALM-DKF measurement/filter model.",
            "No statement that the entire published algorithm or its full theorem is disproved.",
            "Exact model-conditioned posterior moments restore the standard mixture moment identity.",
            "These checks do not provide evidence that the proposed G1-R mechanism has a performance advantage.",
        ],
    })
    print(json.dumps({"run_id": out.name, "exact_checks": "PASS", "new_trajectories": 0}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True)
    main(parser.parse_args().out)
