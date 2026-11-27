"""Output-only single-direction ablation on the preregistered nominal subset."""
from concurrent.futures import ProcessPoolExecutor
from decimal import Decimal
from fractions import Fraction as F
import math
from pathlib import Path
import sys
import time
sys.dont_write_bytecode=True
import numpy as np
from stable_sweep import ROOT, GATES, REG, frozen, dump, sha
from exact_linear import matmul, transpose, inverse, update

GROUPS=("strong_positive","strong_negative")


def score(job):
    g,i=job
    start=time.process_time()
    bias=.35 if g==GROUPS[0] else -.35
    frames,states=frozen.record(REG["test_seed"],list(REG["groups"]).index(g),i,bias)
    archived=frozen.read(ROOT.parent/"results/confirmation"/f"{g}-{i:02d}.json")
    assert frames==archived["public"]
    method=frozen.Methods(Decimal(".35"),GATES["M1"])
    H=np.zeros(2)
    values={k:dict(actual=[],conditional=[],useful=0) for k in ("M2","single","M3")}
    selected=None
    choices=0
    for frame,state in zip(frames,states,strict=True):
        t,sent,_,_=frame
        if selected is not None:
            c=method.core
            _,_,tr=update(c.P,c.C,c.R+(0 if sent else 1/c.Z))
            selected=frozen.move(selected,transpose(inverse(matmul(tr,c.A))))[0]
        acts,_,K,f=method.step(frame)
        if method.old is not None:
            selected=method.old[0]
        action,bound=acts["M2"]
        if method.intervals and selected is not None:
            assert selected in method.directions
            def lower(k,box):
                coeff=method.core.support_coefficient(k,selected)
                return min(F(q)*b for q in (coeff.lo,coeff.hi) for b in box)
            z=min(lower(k,box) for k,box in method.intervals.items())
            if z>0:
                proposed,score=frozen.capped_halfspace_action((selected,z),frozen.W,frozen.CAP)
                _,legacy=frozen.capped_halfspace_action(method.old,frozen.W,frozen.CAP)
                if score>=legacy:
                    cand=frozen.publish(method.monitor,proposed,method.radius)
                    if cand[1]>bound:
                        action,bound=cand[:2]
        if method.intervals=={}:
            action,bound=(F(0),F(0)),F(0)
        assert bound<=acts["M3"][1]
        acts["single"]=(action,bound)
        H=f@H+(K if sent and t>=50 else 0)
        if t not in frozen.WINDOW: continue
        choices+=acts["M3"][0]!=action
        for m,out in values.items():
            a,lb=acts[m]
            assert sum(map(abs,a))<=frozen.CAP
            a=np.asarray(a,float)
            err=state-method.monitor
            out["actual"].append(float(err@err-(err+a)@(err+a)))
            cond=float(2*bias*H@a-a@a)
            assert cond+1e-10>=float(lb)
            out["conditional"].append(cond)
            out["useful"]+=int(lb>=frozen.USEFUL)
    for m,v in values.items():
        v["actual"]=math.fsum(v["actual"])
        v["conditional"]=math.fsum(v["conditional"])
        if m!="single":
            old=archived["metrics"][m]
            assert abs(v["conditional"]-old["conditional"])<1e-10
            assert abs(v["actual"]-(archived["metrics"]["M0"]["loss"]-old["loss"]))<1e-10
            assert v["useful"]==old["useful"]
    return dict(group=g,index=i,metrics=values,other_direction_steps=choices,cpu_seconds=time.process_time()-start)


if __name__=="__main__":
    with ProcessPoolExecutor(4) as pool:
        rows=list(pool.map(score,[(g,i) for g in GROUPS for i in range(12)]))
    dump(ROOT/"direction_ablation.json",dict(source=sha(Path(__file__)),rows=rows))
