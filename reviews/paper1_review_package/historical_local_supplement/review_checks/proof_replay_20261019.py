"""Read-only replay of the focused manuscript's deterministic calculations.

This audits code/result consistency, not the theorem or continuous-log TV.
Source files and existing result files are not overwritten. No Monte Carlo runs.
"""
from pathlib import Path
import hashlib
import json
import sys

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT
sys.dont_write_bytecode = True
sys.path.insert(0, str(SOURCE))
import numpy as np
import experiments as ex
from vector_core import arr, run_tree, quadrature_check

names = ("theory.tex", "vector_proof.tex", "vector_core.py", "experiments.py",
         "physical_check.py", "vector_data/results.json", "vector_data/physical_check.json")
before = {n: hashlib.sha256((SOURCE/n).read_bytes()).hexdigest() for n in names}
old = json.loads((SOURCE / "vector_data/results.json").read_text(encoding="utf-8"))
residuals = {"constants": 0.0, "rows": 0.0, "budgets": 0.0,
             "mass": 0.0, "witness": 0.0, "damage_identity": 0.0}
def compare(kind, a, b):
    gap = abs(float(a)-float(b))
    residuals[kind] = max(residuals[kind], gap)
    assert gap < 5e-12, (kind, a, b)

case_reports = {}
for name, specific in ex.PARAMETERS["cases"].items():
    model = arr(dict(ex.PARAMETERS["common"], **specific))
    k = ex.PARAMETERS["k"]
    c = ex.constants(model, k, ex.PARAMETERS["b_ref"])
    for key, val in c.items():
        if key == "radii":
            for x, y in zip(val, old["cases"][name]["constants"][key]):
                compare("constants", x, y)
        else:
            compare("constants", val, old["cases"][name]["constants"][key])
    healthy = run_tree(model, k, 0.0, "healthy")
    healthy_score = ex.score_moments(healthy, model, c)
    lower_row = None
    for row in [r for r in old["rows"] if r["case"] == name]:
        policy, b = row["policy"], row["b"]
        eta = b*c["kappa"] if policy == "compensated_rademacher" else b
        tree = run_tree(model, k, eta, policy)
        dc = tree["e_trace"]-healthy["e_trace"]
        J = tree["e_bias2"]+dc
        tv = .5*sum(abs(tree["bits"][h]-healthy["bits"][h]) for h in healthy["bits"])
        score = ex.score_moments(tree, model, c)
        for key, val in {"J":J, "bias2":tree["e_bias2"], "covariance_change":dc,
                         "event_word_TV":tv,
                         "score_gap":healthy_score["mean"]-score["mean"],
                         **score}.items():
            compare("rows", val, row[key])
        assert tree["diagnostics"]["peak_attack_norm"] <= b*(1+1e-12)
        residuals["mass"] = max(residuals["mass"], tree["diagnostics"]["probability_mass_error"])
        residuals["witness"] = max(residuals["witness"], tree["diagnostics"]["witness_residual"])
        if policy == "compensated_rademacher":
            compare("damage_identity", J, c["L_v"]*eta*eta)
            assert tv <= c["C_pm"]*eta*eta+1e-12
            if b == ex.PARAMETERS["budget_peak"]:
                lower_row = dict(b=b, J=J, tv=tv, upper=c["C_pm"]*eta*eta)
    for row in [r for r in old["budget_rows"] if r["case"] == name]:
        lam = min(1., row["epsilon"]/lower_row["upper"])
        for key, val in {"mixture_probability":lam, "achievable_J":lam*lower_row["J"],
                         "event_word_TV":lam*lower_row["tv"],
                         "full_log_TV_analytic_upper":lam*lower_row["upper"],
                         "worst_case_upper":min(c["C_peak"]*lower_row["b"]**2,
                                                 c["C_record"]*row["epsilon"])}.items():
            compare("budgets", val, row[key])
        assert lam*lower_row["upper"] <= row["epsilon"]+1e-15
    qc = quadrature_check(model, 40)
    assert qc["silent_covariance_error_fro"] < 1e-9
    case_reports[name] = dict(C_pm=c["C_pm"], L_v=c["L_v"], kappa=c["kappa"],
                              quadrature=qc, lower_at_b_0_1=lower_row)

after = {n: hashlib.sha256((SOURCE/n).read_bytes()).hexdigest() for n in names}
assert before == after
report = dict(status="passed_deterministic_replay", source=str(SOURCE),
              rows=16, budget_rows=10, residuals=residuals, cases=case_reports,
              unchanged_files_sha256=after,
              limitations=["Existing algorithms were replayed; this is not an independent implementation.",
                           "No Monte Carlo rerun and no continuous-payload joint-TV integration.",
                           "Floating point, not interval arithmetic or formal proof verification."])
out = Path(__file__).with_suffix(".json")
out.write_text(json.dumps(report, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
print(json.dumps({"status":report["status"], "residuals":residuals, "cases":case_reports}, indent=2))
