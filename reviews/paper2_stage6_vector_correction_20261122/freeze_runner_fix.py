"""Transparent pre-performance amendment: NumPy scalar repr is not decimal text."""
from pathlib import Path
import json,hashlib
HERE=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
original=json.loads((HERE/"freeze.json").read_text(encoding="utf8"))
assert not list((HERE/"results").rglob("b*_episode*.json"))
assert not (HERE/"results_v2").exists()
updated=dict(original)
updated["stage"]="BEFORE_RETRY_AFTER_FIRST_SEND_SERIALIZATION_FAILURE"
updated["inputs"]=dict(original["inputs"])
updated["inputs"].pop("pilot.py")
updated["inputs"]["pilot_v2.py"]=sha(HERE/"pilot_v2.py")
updated["superseded_freeze_sha256"]=sha(HERE/"freeze.json")
updated["amendment"]={
    "failure":"NumPy 2 scalar repr includes np.float64(...), invalid Decimal literal",
    "fix":"convert scalar to built-in float before repr; same represented binary64 value",
    "unchanged":"all model, reference, certificate, seed, sample-count and statistic parameters",
    "prior_random_inputs":"initial samples drawn before first sent payload caused conversion failure",
    "completed_prior_performance_episodes":0,
    "retry_identity":"new results_v2 directory, same declared independent episode seeds; old failure start record retained",
    "testing":"fixed numpy scalar serializes to Decimal after built-in float conversion"
}
(HERE/"freeze_v2.json").write_text(json.dumps(updated,indent=2)+"\n",encoding="utf8",newline="\n")
print("AMENDMENT FROZEN")
