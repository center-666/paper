"""Replay Stage 9's unthresholded point comparator on one archived early-strong seed."""
from fractions import Fraction as F
from decimal import Decimal
import numpy as np
from engine import (TASK,MODEL,A,STAGE6,TIMES,VectorRecord,ScoredGrid,GRID,choose_point,
                    simulate,point_output)
from exact_linear import asfloat,matmul,update
from run import read,save,digest
if __name__=="__main__":
    path=TASK.parent/"paper2_stage9_cumulative_evidence_20261123/fresh_episodes/case2_episode000.json"
    archived=read(path)
    pub,errors=simulate(archived["seed"],2,0,.25,50,562)
    core=VectorRecord(MODEL)
    point,monitor=np.zeros(2),np.zeros(2)
    b=0.
    gain=0.
    for (t,sent,r,u),e in zip(pub,errors):
        _,km,tm=update(core.P,core.C,core.R+(0 if sent else 1/core.Z))
        K=np.array(asfloat(km)).ravel()
        point=np.array(asfloat(matmul(tm,core.A)))@point+(K*b if sent else 0.)
        core.append(sent,repr(u) if sent else None,repr(r))
        if t in TIMES:
            g=ScoredGrid(core)
            _,proposal,b=choose_point(g,GRID)
            b=float(b)
            point=proposal if g.score>0 else np.zeros(2)
            if g.score<=0: b=0.
        monitor=A@monitor+K*(u if sent else r)
        point,act=point_output(monitor,point)
        if t>=50:
            err=e+np.asarray(act,float)
            gain+=float(e@e-err@err)
    reference=archived["metrics"]["point"]["sample_gain"]
    assert abs(reference-gain)<2e-8
    save(TASK/"results/h0_archive.json",dict(file=path.name,sha256=digest(path),reference=reference,
         binary64_emitted_gain=gain,absolute_difference=abs(reference-gain),tolerance=2e-8))
    print(reference,gain)
