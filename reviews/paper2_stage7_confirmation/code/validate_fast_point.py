"""Compare the vectorized calibration scorer with frozen Stage 6 point scoring."""
from __future__ import annotations
import json, math, sys
from fractions import Fraction as F
from pathlib import Path
import numpy as np
TASK = Path(__file__).resolve().parents[1]; REVIEWS = TASK.parent
STAGE6 = REVIEWS / "paper2_stage6_vector_correction_20261122"
STAGE7 = REVIEWS / "paper2_stage7_fixed_amplitude_20261122"
sys.path.insert(0, str(STAGE6)); sys.path.insert(0, str(STAGE7)); sys.path.insert(0, str(Path(__file__).resolve().parent))
from vector_record import VectorRecord
from exact_linear import asfloat, update
from pilot_v2 import choose_point
from engine import ScoredGrid
from fast_point_state import FastPointState

def main():
    model = json.loads((STAGE6 / "model.json").read_text(encoding="utf8"))
    protocol = json.loads((STAGE7 / "fresh_protocol.json").read_text(encoding="utf8"))
    grid = protocol["point_estimator_grid"]
    fast = FastPointState(model, grid); exact = VectorRecord(model)
    phys, events, phase = [np.random.default_rng(s) for s in np.random.SeedSequence([202611251799, 0]).spawn(3)]
    A=np.array(model["A"],float); C=np.array(model["C"],float); Q=np.array(model["Q"],float)
    R=float(model["R"]); Z=float(model["Z"]); delta=float(model["quantization_half_width"])
    error=np.linalg.cholesky(np.array(model["P0_prior"],float))@phys.normal(size=2)
    checks=[]
    for t in range(144):
        v=math.sqrt(R)*phys.normal(); w=np.linalg.cholesky(Q)@phys.normal(size=2)
        r=0.0 if t==0 else delta*(2*phase.random()-1); y=float((C@error).item()+v)
        sent=bool(events.random()>math.exp(-.5*Z*(y-r)**2)); u=repr(float(y)) if sent else None
        Kfast,_=fast.append(sent,u,repr(float(r)))
        _,Kexact,_=update(exact.P,exact.C,exact.R+(F(0) if sent else F(1)/F(model["Z"])))
        exact.append(sent,u,repr(float(r)))
        K=np.asarray(asfloat(Kexact),float).ravel()
        post=error-K*(y if sent else r)
        if t in (63,95,127,143):
            scored=ScoredGrid(exact)
            ref=choose_point(scored,grid)
            candidate=fast.proposal()
            err=abs(float(scored.score)-candidate[3])
            point_error=float(np.max(np.abs(ref[1]-candidate[1])))
            assert err < 1e-10 and point_error < 1e-12
            assert ref[0]==candidate[0] and float(ref[2])==candidate[2]
            checks.append(dict(time=t,score_error=err,point_error=point_error,b=candidate[2]))
        error=A@post+w
    print(json.dumps(checks,indent=2))
if __name__=="__main__": main()
