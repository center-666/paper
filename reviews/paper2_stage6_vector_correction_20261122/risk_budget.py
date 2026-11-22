"""Deterministic display of vector failure-budget constants, no performance draws."""
from pathlib import Path
import json,math
HERE=Path(__file__).resolve().parent
p=json.loads((HERE/"pilot_protocol.json").read_text(encoding="utf8"))
model=json.loads((HERE/"model.json").read_text(encoding="utf8"))
rho=math.sqrt(19/20)
Btheta=float(model["attack_amplitude_cap"])/(math.sqrt(float(model["R"]))*(1-rho))
Bc=p["output_l1_cap"] # l2 norm <= l1 cap for W=I
eps=p["confidence_failure"]
output={"status":"PASS","deterministic_only":True,
    "rho":rho,"true_pollution_norm_bound":Btheta,"correction_norm_cap":Bc,
    "per_step_failure_penalty":2*eps*(Btheta*Bc+Bc*Bc),
    "window_penalties":{str(H):2*eps*H*(Btheta*Bc+Bc*Bc) for H in p["evaluation_windows"]},
    "healthy_cost_per_step":eps*Bc*Bc,
    "note":"A conservative all-history bound; not a prediction of actual risk or tight certificate performance."}
(HERE/"risk_budget.json").write_text(json.dumps(output,indent=2)+"\n",encoding="utf8",newline="\n")
print(json.dumps(output,indent=2))
