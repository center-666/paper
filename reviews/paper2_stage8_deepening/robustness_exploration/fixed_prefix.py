"""Paired codeword replay with identical transmitted times, centres, and physical states."""
from concurrent.futures import ProcessPoolExecutor
from decimal import Decimal
import argparse
import hashlib
import json
import math
from pathlib import Path
import sys
import time
sys.dont_write_bytecode=True
import numpy as np
from gmpy2 import mpq
import stable_sweep as base
from stable_sweep import ROOT, REG, GATES, GROUPS, Truth, frozen

BITS=(12,10,8,6,4)


def quantize(z,bits):
    spacing=10./((1<<bits)-1)
    code=int(np.rint((min(5.,max(-5.,z))+5.)/spacing))
    return -5.+min((1<<bits)-1,max(0,code))*spacing


def identity(frames):
    return hashlib.sha256(json.dumps(frames,separators=(",",":")).encode()).hexdigest()


def original_history(group,i):
    b={"health":0.,"strong_positive":.35,"strong_negative":-.35}[group]
    frames,states=frozen.record(REG["test_seed"],list(REG["groups"]).index(group),i,b)
    archive=frozen.read(ROOT.parent/"results/confirmation"/f"{group}-{i:02d}.json")
    assert frames==archive["public"]
    oracle=Truth(base.dynamics(0));means=[]
    for t,s,c,z in frames:
        u,v=map(lambda x:mpq(str(float(x))),frozen.control(t))
        obs=mpq(z)-mpq(str(b))*(t>=50) if s else mpq(c)
        means.append(oracle.step(obs,s,((6*u+v)/100,(2*u+5*v)/100)))
    return frames,states,means


def one_group(group,i,verify):
    reference_start=time.process_time()
    frames,states,means=original_history(group,i)
    preparation_cpu=time.process_time()-reference_start
    original_hash=identity(frames)
    for bits in BITS:
        start=time.process_time()
        dest=ROOT/"prefix_data"/f"{bits}bit_{group}_{i:02d}.json"
        reg_hash=base.sha(ROOT/"prefix_registration.json")
        if dest.exists() and not verify:
            assert frozen.read(dest)["registration_hash"]==reg_hash
            continue
        receiver=frozen.Methods(Decimal(".35"),GATES["M1"])
        rec=[[t,s,c,quantize(z,bits) if s else None] for t,s,c,z in frames]
        measures={name:dict(actual_gain=[],conditional_gain=[],conditional_negative_steps=0,certificate_checks=0,
                            risk_violations=0,useful_steps=0,first_useful=None,endpoint_useful=False,
                            nonzero_steps=0,false_action=False) for name in ("M0","M1","M2","M3")}
        failure=None
        for (t,s,c,z),x,(mx,my) in zip(rec,states,means,strict=True):
            offset=float(c-receiver.prior[0])
            try:
                acts,_,_,_=receiver.step([t,s,c,z])
            except ValueError as exc:
                if str(exc)!="Invalid measurement-center offset":
                    raise
                assert abs(offset)>float(frozen.MODEL["quantization_half_width"])
                failure=dict(reason=str(exc),t=t,offset=offset)
                break
            acts["M0"]=(0,0),None
            dx=mpq(float(receiver.monitor[0]))-mx
            dy=mpq(float(receiver.monitor[1]))-my
            e=x-receiver.monitor
            for m,(act,lb) in acts.items():
                out=measures[m]
                ax,ay=(mpq(int(a.numerator),int(a.denominator)) for a in act)
                cond=2*(dx*ax+dy*ay)-ax*ax-ay*ay
                on=any(act)
                assert abs(ax)+abs(ay)<=1
                out["nonzero_steps"]+=int(on)
                out["false_action"] |= on
                if lb and on:
                    out["certificate_checks"]+=1
                    out["risk_violations"]+=int(cond+mpq(1,10**10)<mpq(lb.numerator,lb.denominator))
                if t in frozen.WINDOW:
                    corrected=e+np.asarray(act,float)
                    out["actual_gain"].append(float(e@e-corrected@corrected))
                    out["conditional_gain"].append(float(cond))
                    out["conditional_negative_steps"]+=int(cond<0)
                    useful=lb>=frozen.USEFUL if lb is not None else on
                    out["useful_steps"]+=int(useful)
                    if useful and out["first_useful"] is None:out["first_useful"]=t
                    if t==561:out["endpoint_useful"]=useful
        for out in measures.values():
            for key in ("actual_gain","conditional_gain"):
                out[key]=math.fsum(out[key])
        row=dict(experiment="fixed_prefix",scenario=f"{bits}bit",index=i,group=group,seed=REG["test_seed"],
                 horizon=len(frames),transmissions=sum(f[1] for f in frames),
                 clipped_sends=sum(s and abs(z)>5 for _,s,_,z in frames),
                 registration_hash=reg_hash,sender_sha256=original_hash,public_history_sha256=identity(rec),
                 spectral_radius_A_plant=float(max(abs(np.linalg.eigvals(frozen.A)))),failure=failure,
                 metrics=measures if failure is None else None,
                 cpu_seconds=time.process_time()-start+(preparation_cpu if bits==BITS[0] else 0.))
        if verify:
            archived=frozen.read(dest)
            for key in row.keys()-{"cpu_seconds"}: assert row[key]==archived[key],(dest.name,key)
        else:base.dump(dest,row)


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--register",action="store_true");p.add_argument("--verify",action="store_true")
    p.add_argument("--workers",type=int,default=6);args=p.parse_args()
    spec=dict(seed=REG["test_seed"],groups=list(GROUPS),indices=list(range(12)),bits=list(BITS),
              continuous_reference="original frozen, public gamma/center and physical state fixed across bit depth",
              rule="endpoint-inclusive nearest level on [-5,5], ties to even index",failure_handling="record first inadmissible centre, all full-path outcomes missing",source=base.sha(Path(__file__)),
              truth_source=base.sha(ROOT/"stable_sweep.py"),stage8_registration=base.sha(ROOT.parent/"registration.json"),
              window=[50,561],horizon=608,budget=64,point_gates=GATES,queries=list(frozen.TIMES))
    reg=ROOT/"prefix_registration.json"
    if args.register:
        if reg.exists(): assert spec==frozen.read(reg)
        else:base.dump(reg,spec)
        return
    assert spec==frozen.read(reg)
    with ProcessPoolExecutor(args.workers) as pool:
        for g in GROUPS:
            for start in (0,6):
                jobs=[pool.submit(one_group,g,i,args.verify) for i in range(start,start+6)]
                for job in jobs: job.result()
            print("fixed sender history complete",g,flush=True)


if __name__=="__main__":
    main()
