"""Historical audit and deterministic fixtures. No historical results are rewritten."""
from __future__ import annotations
import itertools
from decimal import Decimal
from fractions import Fraction as F
from pathlib import Path
from statistics import mean,stdev
import numpy as np
from scipy.stats import t as student
from engine import (TASK, STAGE7, MODEL, STAGE6, Online, ScoredGrid, GRID,
                    choose_point, publish, point_output, ZERO, A, USEFUL, VectorRecord)
from exact_linear import matrix, update, add, matmul, transpose
from run import read,save,digest

def history():
    freeze = read(STAGE7/"fresh_confirmation_freeze.json")
    for root,key in ((STAGE7,"stage7_sources"),(STAGE6,"stage6_inputs")):
        assert all(digest(root/n)==s for n,s in freeze[key].items())
    stage9 = TASK.parent/"paper2_stage9_cumulative_evidence_20261123"
    files = sorted((STAGE7/"results"/"fresh_confirmation").glob("b0.25_episode*.json"))
    rows = [read(f)["snapshots"]["512"] for f in files]
    d = [s["old"]-s["new"] for s in rows]
    half = float(student.ppf(.975,len(d)-1))*stdev(d)/len(d)**.5
    counts = [sum(s[m+"_current_action_norm"] >= .025-1e-12 for s in rows) for m in ("old","new")]
    early = sorted((stage9/"fresh_episodes").glob("case2_episode*.json"))
    nine = [read(f) for f in early]
    assert all(r["amplitude"]=="1/4" and r["onset"]==50 and r["steps"]==562 for r in nine)
    gains = [mean(r["metrics"]["monitor"]["loss"]-r["metrics"][m]["loss"] for r in nine) for m in ("point","9")]
    stats = [mean(d),mean(d)-half,mean(d)+half,*gains]
    assert [round(v,4) for v in stats]==[2.0869,.9417,3.2322,8.2577,2.2472]
    assert counts==[0,7] and len(files)==12 and len(early)==3
    return dict(stage7_n=12,stage7_difference_ci=stats[:3],endpoint_norm_counts=counts,
                stage9_n=3,stage9_point_cert_gain=gains,
                inputs={f.relative_to(TASK.parent).as_posix():digest(f) for f in files+early})

def exact_check():
    AX, C, Q = (matrix(MODEL[n]) for n in ("A","C","Q"))
    count=0
    for bits in itertools.product((False,True),repeat=4):
        for k in (0,1,3,4):
            P=matrix(MODEL["P0_prior"])
            mon=mu=h=[[F(0)],[F(0)]]
            for t,sent in enumerate(bits):
                b=F(1,4)
                post,K,T=update(P,C,F(".2")+(0 if sent else F(".5")))
                mon,mu,h=[matmul(AX,v) for v in (mon,mu,h)]
                obs=F((t+1)*3,7) if sent else F(1,100)
                active=sent and t>=k
                def updated(x, measurement):
                    residual=measurement-matmul(C,x)[0][0]
                    return [[v[0]+g[0]*residual] for v,g in zip(x,K)]
                mon,mu=updated(mon,obs),updated(mu,obs-b*active)
                h=[[v[0]+g[0]*active] for v,g in zip(matmul(T,h),K)]
                assert all(x[0]-y[0]==b*z[0] for x,y,z in zip(mon,mu,h))
                P=add(matmul(matmul(AX,post),transpose(AX)),Q)
                count+=1
    return count

def fixtures():
    from vector_record import I
    class Tie:
        candidates=[{"H":[I.exact(1),I.exact(0)]}]*2
        def all_likelihoods(self,b):
            return [I.exact(1)]*2
    scores=ScoredGrid(Tie())
    _,p,b=choose_point(scores,GRID)
    assert b==Decimal(".05") and scores.onset==0 and scores.score==1
    # Equal score is rejected; nonzero must persist consistently from query.
    pub=[(t,bool(t%3),.001,.35 if t%3 else None) for t in range(131)]
    def replay(frames,offline_labels,h):
        instance=Online({"h0":"0","gate":h})
        saved=[]
        for frame in frames:
            actions,query,_,_,_=instance.step(frame)
            saved.append((tuple(actions.items()),query["score"] if query else None))
        return saved
    a=replay(pub,("health",None,0),"Infinity")
    b=replay(pub,("attack",128,.25),"Infinity")
    assert a==b
    score=a[127][1]
    assert score is not None
    c=replay(pub,("attack",126,.1),score)
    assert all(dict(actions)["gate"][0]==ZERO for actions,_ in c)
    # Deliberately force a positive first wave and then a rejection. Only
    # public proposal scores are supplied; the same class performs both queries.
    from unittest.mock import patch
    from engine import SPEC
    def controlled(scored,grid):
        scored.score=Decimal(2 if scored.record.n==2 else 0)
        scored.onset=0 if scored.score else None
        return ((F(1),F(0)),np.array([.1,0]),Decimal(".1")) if scored.score else (None,np.zeros(2),Decimal(0))
    with patch("engine.TIMES",(1,3)),patch("engine.choose_point",controlled):
        inst=Online({"gate":"1"})
        outs=[inst.step(frame) for frame in pub[:6]]
        assert any(outs[1][0]["gate"][0]) and any(outs[2][0]["gate"][0])
        assert all(o[0]["gate"][0]==ZERO for o in outs[3:])
        assert outs[1][1]["levels"][0]["reason"]=="HEALTH_OR_FUTURE_START_RETAINED"
    # A large absolute monitor cannot represent this small correction.
    assert publish([2.**60,0],(F(1,10),F(0)),(F(1),F(1)))==(ZERO,F(0),True)
    x,bound,fallback=publish([0.,0.],(F(1,32),F(0)),(F(1),F(1)))
    assert sum(map(abs,x))<=1 and bound==F(1,1024) and bound>=USEFUL and not fallback
    return dict(exact_response_steps=exact_check(),label_invariant_replayed_steps=len(a),
                tied_amplitude=".05",tied_onset=0,equality_rejected=True,
                reject_clears_action_and_bias=True,failed_query_checked=True,
                fallback_and_positive_output_checked=True)
if __name__=="__main__":
    data=dict(historical=history(),fixtures=fixtures())
    save(TASK/"results"/"audit.json",data)
    print(data["historical"]["stage7_difference_ci"],data["historical"]["stage9_point_cert_gain"],data["fixtures"])
