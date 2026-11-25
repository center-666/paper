"""Single-node tank simulation, paired signed point and direction-certificate methods."""
from __future__ import annotations
import os
import sys
sys.dont_write_bytecode = True
for key in ("OMP_NUM_THREADS","MKL_NUM_THREADS","OPENBLAS_NUM_THREADS"):
    os.environ[key]="1"
import hashlib
import json
import time
import math
from decimal import Decimal as D
from fractions import Fraction as F
from functools import lru_cache
from pathlib import Path
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
REV=ROOT.parent
for name in ("paper2_stage6_vector_correction_20261122","paper2_stage7_fixed_amplitude_20261122",
             "paper2_stage7_confirmation/code"):
    sys.path.insert(0,str(REV/name))
from engine import publish, point_output, ZERO, CAP, ScoredGrid
from pilot_v2 import choose_point
from exact_linear import update, asfloat, matmul, transpose, inverse, add, matrix
from fixed_amplitude import capped_halfspace_action
from vector_record import I, interval_fraction
from signed_certify import SignedRecord, certify, restrict

def read(path):
    return json.loads(path.read_text(encoding="utf8"))

def save(path,obj):
    path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix(".tmp")
    tmp.write_text(json.dumps(obj,ensure_ascii=False,allow_nan=False)+"\n",encoding="utf8",newline="\n")
    tmp.replace(path)

def digest(path):
    return hashlib.sha256(path.read_bytes().replace(b"\r\n",b"\n")).hexdigest()

plant=read(ROOT/"config/plants.json")["plants"]["industrial_two_tank"]
MODEL=dict(A=plant["A"],C=plant["C"],P0_prior=plant["P0"],Q=plant["Q"],W=plant["W"],
           R=plant["R"][0][0],Z=plant["Z"],quantization_half_width="0.011628232298833967")
A,B,Q,P0=[np.array(plant[k],float) for k in ("A","B","Q","P0")]
W=matrix(plant["W"])
TIMES=(127,255,383,511)
WINDOW=range(50,562)
USEFUL=F(1,1600)
SQRTQ=np.linalg.cholesky(Q)
EPS=".001"

def grid(cap):
    return [str(cap*D(i)/5) for i in (-5,-4,-3,-2,-1,1,2,3,4,5)]

def control(t):
    return np.array([.15 if t%120<60 else .08, .05])

def record(seed,group,index,b):
    phys,trigger,phase=[np.random.default_rng(s) for s in
                        np.random.SeedSequence([seed,group,index]).spawn(3)]
    x=np.linalg.cholesky(P0)@phys.normal(size=2)
    prior=np.zeros(2)
    covariance=matrix(plant["P0"])
    ax,c,q=[matrix(plant[n]) for n in ("A","C","Q")]
    public=[]; states=[]
    for t in range(608):
        y=float(x[0]+math.sqrt(float(MODEL["R"]))*phys.normal())
        center=float(prior[0]+(float(MODEL["quantization_half_width"])*.999999999*(2*phase.random()-1) if t else 0.))
        sent=bool(trigger.random()>math.exp(-float(MODEL["Z"])*(y-center)**2/2))
        payload=float(y+(b if t>=50 else 0.)) if sent else None
        post,K,_=update(covariance,c,F(MODEL["R"])+(0 if sent else 1/F(MODEL["Z"])))
        covariance=add(matmul(matmul(ax,post),transpose(ax)),q)
        posterior=prior+np.array(asfloat(K)).ravel()*((payload if sent else center)-prior[0])
        public.append([t,sent,center,payload]); states.append(x.copy())
        bu=B@control(t)
        x=A@x+bu+SQRTQ@phys.normal(size=2)
        prior=A@posterior+bu
    return public,states

def move(d,inv_transpose):
    v=tuple(row[0] for row in matmul(inv_transpose,[[x] for x in d]))
    scale=max(map(abs,v))
    return tuple(x/scale for x in v),scale

class Methods:
    def __init__(self,cap,h,mode="paired"):
        self.core=SignedRecord(MODEL,cap)
        self.cap=F(cap); self.dec_cap=cap
        self.grid=grid(cap)
        self.threshold=D(str(h)); self.mode=mode
        self.prior=np.zeros(2); self.point=np.zeros(2); self.b=0.
        self.old=None; self.intervals=None; self.directions=[]
        self.radius=ZERO

    def step(self,frame):
        t,sent,center,payload=frame
        C=self.core
        _,km,tm=update(C.P,C.C,C.R+(0 if sent else 1/C.Z))
        fm=matmul(tm,C.A)
        K=np.array(asfloat(km)).ravel()
        f=np.array(asfloat(fm))
        r=center-self.prior[0]
        u=payload-self.prior[0] if sent else None
        self.monitor=self.prior+K*(u if sent else r)
        self.prior=A@self.monitor+B@control(t)
        if self.mode!="M3":
            self.point=f@self.point+(K*self.b if sent else 0.)
        C.append(sent,repr(float(u)) if sent else None,repr(float(r)))
        if self.directions or self.old:
            inv_t=transpose(inverse(fm))
            self.directions=[move(d,inv_t)[0] for d in self.directions]
            if self.old:
                d,scale=move(self.old[0],inv_t)
                z=self.old[1]/scale
                if sent:
                    z-=self.cap*abs(sum(x*g[0] for x,g in zip(d,km)))
                self.old=(d,z) if z>0 else None
        self.radius=tuple(F(math.ceil(2**48*(sum(abs(x)*y for x,y in zip(row,self.radius))+
                  (abs(g[0])*self.cap if sent else 0))),2**48) for row,g in zip(fm,km))
        query=None
        if t in TIMES:
            start=time.perf_counter()
            view=C.view()
            scored=ScoredGrid(view)
            d,p,b=choose_point(scored,self.grid)
            if self.mode!="M3":
                self.point,self.b=(p,float(b)) if scored.score>self.threshold else (np.zeros(2),0.)
            query=dict(time=t,score=str(scored.score),b=str(b),send_class=scored.onset,
                       direction=list(map(str,d)) if d else None,levels=[])
            if d and self.mode!="M1":
                witness=view.likelihood(scored.onset,I.exact(b))
                for level in (".025",".05",".10"):
                    target=F(level)*sum(map(abs,d))
                    z=D(target.numerator)/D(target.denominator)
                    assert F(z)==target
                    result=certify(view,d,z,self.dec_cap,EPS,64,witness)
                    query["levels"].append(result)
                    if not result["certified"]:
                        break
                    intervals=self.intervals
                    if intervals is None:
                        intervals={k:(-self.cap,self.cap) for k in range(view.n)}
                    kept={}
                    for k,box in intervals.items():
                        updated=restrict(box,view.support_coefficient(k,d),target)
                        if updated is not None:
                            kept[k]=updated
                    self.intervals=kept
                    if d not in self.directions:
                        self.directions.append(d)
                    if capped_halfspace_action((d,target),W,CAP)[1]>capped_halfspace_action(self.old,W,CAP)[1]:
                        self.old=d,target
            query["seconds"]=time.perf_counter()-start
        acts={}
        if self.mode!="M3":
            self.point,point=point_output(self.monitor,self.point)
            acts["M1"]=(point,None)
        if self.mode!="M1":
            action,legacy=capped_halfspace_action(self.old,W,CAP)
            old=publish(self.monitor,action,self.radius)[:2]
            best=old
            if self.intervals:
                for direction in self.directions:
                    z=min(min(F(endpoint)*b for endpoint in (q.lo,q.hi) for b in box)
                          for k,box in self.intervals.items() for q in [C.support_coefficient(k,direction)])
                    if z>0:
                        a,g=capped_halfspace_action((direction,z),W,CAP)
                        if g>=legacy:
                            candidate=publish(self.monitor,a,self.radius)[:2]
                            if candidate[1]>best[1]:
                                best=candidate
            acts.update(M2=old,M3=best if self.intervals!= {} else (ZERO,F(0)))
        return acts,query,K,f

def evaluate(public,x,b,cap,h):
    from bisect import bisect_left
    method=Methods(cap,h)
    results={m:dict(loss=0.,conditional=0.,bound=0.,useful=0,end=False,first=None,nonzero=0)
             for m in ("M0","M1","M2","M3","Oracle")}
    prior=np.zeros(2); H=np.zeros(2)
    certs=[]; curve=[]; cross=miss=violations=checked=cap_bad=0
    hashes={m:hashlib.sha256() for m in ("M1","M2","M3")}
    for frame,state in zip(public,x,strict=True):
        t,sent,center,payload=frame
        acts,query,K,f=method.step(frame)
        if query:
            certs.append(query)
        active=sent and t>=50
        observation=(payload-(b if active else 0.)) if sent else center
        mu=prior+K*(observation-prior[0])
        prior=A@mu+B@control(t)
        H=f@H+(K if active else 0.)
        delta=b*H
        cross=max(cross,float(np.max(np.abs(method.monitor-mu-delta))))
        key=bisect_left(method.core.send_times,50)
        kept=method.intervals is None or (key in method.intervals and
                  method.intervals[key][0]<=F(str(b))<=method.intervals[key][1])
        miss+=int(not kept)
        acts.update(M0=(ZERO,None),Oracle=(delta,None))
        curve.append([float(acts[m][1]) for m in ("M2","M3")])
        for m,(a,lb) in acts.items():
            metric=results[m]
            on=bool(any(a))
            metric["nonzero"]+=int(on)
            if m in ("M1","M2","M3"):
                cap_bad+=int(sum(map(abs,a))>CAP)
                hashes[m].update(np.asarray(a,dtype=">f8").tobytes())
            a=np.asarray(a,float)
            cond=float(2*delta@a-a@a)
            if lb is not None and on and kept:
                checked+=1
                violations+=int(cond+1e-10<float(lb))
            if t in WINDOW:
                err=state-method.monitor+a
                metric["loss"]+=float(err@err)
                metric["conditional"]+=cond
                metric["bound"]+=float(lb or 0)
                useful=bool(lb>=USEFUL) if lb is not None else on
                if useful and metric["first"] is None:
                    metric["first"]=t
                metric["useful"]+=int(useful)
                if t==WINDOW.stop-1:
                    metric["end"]=useful
    if cross>1e-9:
        raise ArithmeticError("Direct oracle and bH disagree")
    return dict(metrics=results,queries=certs,bounds=curve,public=public,
                actions_sha256={m:h.hexdigest() for m,h in hashes.items()},
                max_error=cross,miss=miss,violations=violations,checked=checked,cap_bad=cap_bad)
