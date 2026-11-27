"""Independent per-step drift truth and audit denominators on the saved seed paths."""
from __future__ import annotations
from concurrent.futures import ProcessPoolExecutor
import hashlib
import json
import math
import sys
import time
from fractions import Fraction
from pathlib import Path
sys.dont_write_bytecode=True
import gmpy2
from gmpy2 import mpq
import numpy as np

import stable_sweep as base
import replay_registered as history

ROOT=base.ROOT


def fraction(q):
    return Fraction(int(q.numerator),int(q.denominator))


def check(path):
    start=time.process_time()
    row=json.loads(path.read_bytes())
    engine=history.ENGINE
    task={key:row[key] for key in ("experiment","scenario","rho","bias_kind","bias","fraction","index","group")}
    frames,states,_,biases,_=engine.generate_record(row["seed"],row["group"],row["index"],task)
    assert hashlib.sha256(json.dumps(frames,separators=(",",":")).encode()).hexdigest()==row["public_history_sha256"]
    method=engine.Methods(engine.D(".35"),engine.D(base.GATES["M1"]))
    nominal=base.Truth(base.dynamics(0))
    candidate=base.Truth(base.dynamics(0))
    dx=dy=mpq(0)
    impulses={}
    anchors={}
    audited={name:dict(window_checks=0,window_viol=0,full_checks=0,full_viol=0,
                        window_strict=0,full_strict=0,negative_steps=0,conditional=[])
             for name in ("M0","M1","M2","M3","M3_rho")}
    rho=Fraction(row["rho"])
    max_position_error=0.
    for t,frame in enumerate(frames):
        _,sent,c,z=frame
        Kx=nominal.p/(nominal.p+mpq(1,50)+(0 if sent else mpq(1,2)))
        Ky=nominal.r/(nominal.p+mpq(1,50)+(0 if sent else mpq(1,2)))
        a,b,k,l=nominal.a,nominal.b,nominal.c,nominal.d
        f00,f01=(1-Kx)*a,(1-Kx)*b
        f10,f11=k-Ky*a,l-Ky*b
        bias=mpq(biases[t])
        dx,dy=(f00*dx+f01*dy+Kx*bias, f10*dx+f11*dy+Ky*bias)
        obs=mpq(str(z if sent else c))
        u,v=map(lambda x:mpq(str(float(x))),base.frozen.control(t))
        bu=((6*u+v)/100,(2*u+5*v)/100)
        mx,my=nominal.step(obs,sent,bu)
        tx,ty=candidate.step(obs-bias,sent,bu)
        if (mx-tx,my-ty)!=(dx,dy):
            raise AssertionError((path.name,t,"delta recurrence"))
        acts,query,_,_=method.step(frame)
        if query and any(level["certified"] for level in query["levels"]):
            anchors={onset:t for onset in method.intervals}
        if rho:
            if t<=max(engine.TIMES) or method.directions:
                impulses={s:(f00*x+f01*y,f10*x+f11*y) for s,(x,y) in impulses.items()}
                if sent:
                    impulses[t]=(Kx,Ky)
            # Direct dot products independently check the adjoint-transport implementation.
            projected=[]
            for direction in method.directions:
                x,y=map(mpq,direction)
                projected.append(dict(direction=direction,projections=[
                    fraction(x*i+y*j) for i,j in impulses.values()]))
            acts["M3_rho"]=engine.m3_rho_action(method,acts["M2"][0],acts["M3"],rho,anchors,projected)
        else:
            acts["M3_rho"]=acts["M3"]
        acts["M0"]=(0,0),None
        max_position_error=max(max_position_error,abs(float(mx)-method.monitor[0]),abs(float(my)-method.monitor[1]))
        for name,m in audited.items():
            act,lb=acts[name]
            ax,ay=(mpq(int(i.numerator),int(i.denominator)) for i in act)
            improve=2*(dx*ax+dy*ay)-ax*ax-ay*ay
            if t in base.frozen.WINDOW:
                m["conditional"].append(float(improve))
                m["negative_steps"]+=int(improve<0)
            if lb and any(act):
                for scope in (("full","window") if t in base.frozen.WINDOW else ("full",)):
                    m[scope+"_checks"]+=1
                    m[scope+"_strict"]+=int(improve<mpq(int(lb.numerator),int(lb.denominator)))
                    m[scope+"_viol"]+=int(improve+mpq(1,10**10)<mpq(int(lb.numerator),int(lb.denominator)))
    for name,m in audited.items():
        target=row["metrics"][name]
        m["conditional"]=math.fsum(m["conditional"])
        assert math.isclose(m["conditional"],target["conditional_gain"],abs_tol=1e-10,rel_tol=1e-12)
        assert (m["negative_steps"],m["full_checks"],m["full_viol"])==(
            target["conditional_negative_steps"],target["certificate_checks"],target["risk_violations"])
    return dict(scenario=row["scenario"],index=row["index"],checked_steps=len(frames),
                max_position_error=max_position_error,methods=audited,cpu_seconds=time.process_time()-start)


if __name__=="__main__":
    paths=sorted((ROOT/"data_v2/drift").glob("decay_*.json"))
    assert len(paths)==72
    with ProcessPoolExecutor(4,initializer=history.load_kernel,initargs=(2,)) as pool:
        result=list(pool.map(check,paths))
    base.dump(ROOT/"drift_oracle_audit.json",result)
    print("independent stepwise rational equalities:",sum(r["checked_steps"] for r in result))
