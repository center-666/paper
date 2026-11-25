"""Resolve calibration rank boundaries with the original grid and score order."""
from __future__ import annotations
from concurrent.futures import ProcessPoolExecutor
from decimal import Decimal
from engine import MODEL, TASK, Online, ScoredGrid, GRID, TIMES, choose_point, VectorRecord, simulate
from run import read,save
from fractions import Fraction as F
from exact_linear import asfloat,update
import math
import numpy as np

def exact_max(job):
    idx,seed=job
    state=VectorRecord(MODEL)
    phys,events,phase=[np.random.default_rng(s) for s in np.random.SeedSequence([seed,idx]).spawn(3)]
    error=np.linalg.cholesky(np.array(MODEL["P0_prior"],float))@phys.normal(size=2)
    Q=np.linalg.cholesky(np.asarray(MODEL["Q"],float))
    A=np.asarray(MODEL["A"],float)
    scores=[]
    for t in range(TIMES[-1]+1):
        y=float(error[0]+math.sqrt(.2)*phys.normal())
        w=Q@phys.normal(size=2)
        r=0. if not t else float(MODEL["quantization_half_width"])*(2*phase.random()-1)
        sent=bool(events.random()>math.exp(-(y-r)**2))
        _,gain,_=update(state.P,state.C,state.R+(0 if sent else 1/state.Z))
        state.append(sent,repr(y) if sent else None,repr(r))
        error=A@(error-np.array(asfloat(gain)).ravel()*(y if sent else r))+w
        if t in TIMES:
            scorer=ScoredGrid(state)
            choose_point(scorer,GRID)
            scores.append(scorer.score)
    return idx,str(max(scores))

if __name__=="__main__":
    data=read(TASK/"results/development_point_calibration.json")
    assert data["episodes"]==200
    scores=data["trajectory_maxima"]
    order=sorted(range(len(scores)),key=scores.__getitem__)
    ranks=[190,198,199]
    # Re-evaluate all IDs at, or within 1e-8 of, the three selection boundaries.
    selected=[i for i,s in enumerate(scores) if any(abs(s-scores[order[r-1]])<=1e-8 for r in ranks)]
    with ProcessPoolExecutor(max_workers=3) as pool:
        exact=dict(pool.map(exact_max,[(i,data["seed"]) for i in selected]))
    assert all(abs(float(x)-scores[i])<=1e-8 for i,x in exact.items())
    ordered=sorted(range(len(scores)),key=lambda i:Decimal(exact.get(i,str(scores[i]))))
    assert set(ordered[r-1] for r in ranks)<=exact.keys()
    thresholds={n:exact[ordered[r-1]] for n,r in zip(("q95","q99","M1"),ranks)}
    save(TASK/"results/cutoffs.json",dict(thresholds={"h0":"0",**thresholds,"reject":"Infinity"},
         n=len(scores),ranks=ranks,exact_boundary_scores=exact,fast_boundary_tolerance=1e-8))
    print(thresholds)
