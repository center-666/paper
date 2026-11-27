"""Stable hydraulic relaxation perturbation, frozen Stage 8 online methods."""
from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor
from decimal import Decimal
import hashlib
import json
import math
from pathlib import Path
import sys
import time

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent / "code"))
import experiment as frozen
import gmpy2
from gmpy2 import mpq
import numpy as np

EPS = (-5, -2, -1, 0, 1, 2, 5)
GROUPS = ("health", "strong_positive", "strong_negative")
REG = frozen.read(ROOT.parent / "registration.json")
GATES = frozen.read(ROOT.parent / "supplement/registration.json")["thresholds"]
ORIGINAL_POINT = frozen.choose_point


def sha(path):
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def dump(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(value, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf8", newline="\n")
    temp.replace(path)


def dynamics(percent):
    # Euler-discretized internal flow relaxation: h[t+1]-h[t] = (A-I) h[t] / (1+eps).
    scale = 1 + mpq(percent, 100)
    return [[int(i == j) + (mpq(x) - int(i == j)) / scale
             for j, x in enumerate(row)] for i, row in enumerate(frozen.plant["A"])]


def configuration():
    return dict(model="A_plant = I + (A_nom-I)/(1+eps); internal relaxation time only, B fixed",
                percentages=list(EPS), groups=list(GROUPS), indices=list(range(12)),
                stages="exploratory physical parameter contrast; reused seeds",
                base_seed=REG["test_seed"], group_order=list(REG["groups"]),
                frozen_point_gates=GATES, queries=list(frozen.TIMES),
                physical_parameters=frozen.plant, cap="0.35", onset=50,
                risk_window=[50,561], audit_horizon=[0,607], useful="1/1600",
                tolerance="1e-10", nodes=64, epsilon=".001", wall_batch_size=6,
                zero_source="archived continuous replay; independently check three frozen histories",
                decision="run all 6 nonzero percentages, all 3 groups, all 12 IDs",
                runner_sha256_lf=sha(Path(__file__)), stage8_registration_sha256_lf=sha(ROOT.parent/"registration.json"),
                python=sys.version.split()[0], numpy=np.__version__, gmpy2=gmpy2.version())


class Truth:
    """Exact 2-state scalar-sensor Riccati and conditional mean, GMP rational arithmetic."""
    def __init__(self, matrix):
        self.a, self.b = matrix[0]
        self.c, self.d = matrix[1]
        self.p = self.s = mpq(1,4)
        self.r = self.x = self.y = mpq(0)

    def step(self, measurement, sent, bu):
        noise = mpq(1,50) + (0 if sent else mpq(1,2))
        denom = self.p + noise
        k, l = self.p / denom, self.r / denom
        innov = measurement - self.x
        x, y = self.x + k*innov, self.y + l*innov
        self.x, self.y = self.a*x + self.b*y + bu[0], self.c*x + self.d*y + bu[1]
        p, r, s = k*noise, l*noise, self.s - l*self.r
        a,b,c,d = self.a,self.b,self.c,self.d
        self.p = a*a*p + 2*a*b*r + b*b*s + mpq(1,400)
        self.r = a*c*p + (a*d+b*c)*r + b*d*s
        self.s = c*c*p + 2*c*d*r + d*d*s + mpq(1,400)
        return x,y


def run_trial(percent, group, index):
    start = time.process_time()
    reg_id = sha(ROOT/"stable_registration.json")
    destination = ROOT/"stable_data"/f"{percent:+03d}_{group}_{index:02d}.json"
    if destination.exists():
        row = frozen.read(destination)
        if (row["registration_hash"],row["percent"],row["group"],row["index"]) != (reg_id,percent,group,index):
            raise ValueError(destination.name)
        return
    seed = REG["test_seed"]
    case = list(REG["groups"]).index(group)
    phys, events, jitter = [np.random.default_rng(child) for child in
                            np.random.SeedSequence([seed,case,index]).spawn(3)]
    aq = dynamics(percent)
    af = np.array(aq, float)
    radius = float(max(abs(np.linalg.eigvals(af))))
    assert radius < 1
    exact = Truth(aq)
    state = np.linalg.cholesky(frozen.P0) @ phys.normal(size=2)
    amplitude = mpq({"health":0,"strong_positive":35,"strong_negative":-35}[group],100)
    method = frozen.Methods(Decimal(".35"), GATES["M1"])
    branches = {name:(np.zeros(2),0.) for name in ("h0","q95")}
    proposal = None

    def capture(grid, points):
        nonlocal proposal
        result = ORIGINAL_POINT(grid, points)
        proposal = result
        return result

    names = ("M0","M1","M2","M3","M1_h0","M1_q95")
    metrics = {name:dict(actual_gain=0., loss=0., conditional_gain=0., conditional_negative_steps=0,
                         certificate_checks=0, risk_violations=0, useful_steps=0, nonzero_steps=0,
                         first_useful=None, endpoint_useful=False, false_action=False) for name in names}
    gains = {name:[] for name in names}
    actuals = {name:[] for name in names}
    send_count = 0
    prefix = []
    cap_error = 0
    frozen.choose_point = capture
    try:
        for t in range(REG["steps"]):
            y = float(state[0] + math.sqrt(.02)*phys.normal())
            center = float(method.prior[0] + (float(frozen.MODEL["quantization_half_width"]) *
                           .999999999 * (2*jitter.random()-1) if t else 0.))
            sent = bool(events.random() > math.exp(-2*(y-center)**2/2))
            active_bias = amplitude if t >= REG["onset"] else mpq(0)
            payload = float(y + float(active_bias)) if sent else None
            frame = [t,sent,center,payload]
            prefix.append(frame)
            send_count += sent
            actions,query,K,F = method.step(frame)
            actions["M0"] = ((0,0),None)
            for name,(point,held) in branches.items():
                point = F @ point + (K*held if sent else 0.)
                if query:
                    if Decimal(query["score"]) > Decimal(GATES[name]):
                        _,point,est = proposal
                        held = float(est)
                    else:
                        point,held = np.zeros(2),0.
                point,act = frozen.point_output(method.monitor,point)
                actions["M1_"+name] = act,None
                branches[name] = point,held
            u,v = map(lambda x:mpq(str(float(x))), frozen.control(t))
            bu = (mpq(6,100)*u+mpq(1,100)*v, mpq(2,100)*u+mpq(5,100)*v)
            observation = mpq(float(payload)) - active_bias if sent else mpq(center)
            mx,my = exact.step(observation,sent,bu)
            dx,dy = mpq(float(method.monitor[0]))-mx, mpq(float(method.monitor[1]))-my
            err = state-method.monitor
            for name,(act,lb) in actions.items():
                row = metrics[name]
                on = any(act)
                if on:
                    row["nonzero_steps"] += 1
                    row["false_action"] = True
                ax,ay = (mpq(v.numerator,v.denominator) for v in act)
                cap_error += abs(ax)+abs(ay)>1
                gain = 2*(dx*ax+dy*ay)-ax*ax-ay*ay if on else 0
                if lb and on:
                    row["certificate_checks"] += 1
                    row["risk_violations"] += int(gain+mpq(1,10**10) < mpq(lb.numerator,lb.denominator))
                if t in frozen.WINDOW:
                    corrected = err+np.array(act,float)
                    loss = float(corrected@corrected)
                    row["loss"] += loss
                    actuals[name].append(float(err@err) - loss)
                    gains[name].append(float(gain))
                    row["conditional_negative_steps"] += int(gain<0)
                    useful = lb>=frozen.USEFUL if lb is not None else on
                    if useful and row["first_useful"] is None:
                        row["first_useful"]=t
                    row["useful_steps"] += int(useful)
                    if t == frozen.WINDOW.stop-1:
                        row["endpoint_useful"]=bool(useful)
            state = af @ state + frozen.B @ frozen.control(t) + frozen.SQRTQ @ phys.normal(size=2)
    finally:
        frozen.choose_point = ORIGINAL_POINT
    assert cap_error == 0
    for name in names:
        metrics[name]["conditional_gain"] = math.fsum(gains[name])
        metrics[name]["actual_gain"] = math.fsum(actuals[name])
    record_hash=hashlib.sha256(json.dumps(prefix,separators=(",",":")).encode()).hexdigest()
    if percent==0:
        previous=frozen.read(ROOT/"data/quantization"/f"continuous_{group}_{index:02d}.json")
        assert previous["public_history_sha256"]==record_hash
        for name in names:
            for key in ("actual_gain","conditional_gain","useful_steps","risk_violations","certificate_checks"):
                assert math.isclose(metrics[name][key],previous["metrics"][name][key],abs_tol=1e-10,rel_tol=1e-10),(name,key)
    row = dict(experiment="stable_model",scenario=f"tau_{percent:+d}%",percent=percent,
               registration_hash=reg_id,seed=seed,group=group,index=index,
               public_history_sha256=record_hash, transmissions=send_count,
               horizon=REG["steps"], spectral_radius_A_plant=radius, metrics=metrics,
               cpu_seconds=time.process_time()-start)
    dump(destination,row)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--workers",type=int,default=6)
    parser.add_argument("--register",action="store_true")
    args=parser.parse_args()
    path=ROOT/"stable_registration.json"
    spec=configuration()
    if args.register:
        if path.exists() and frozen.read(path)!=spec:
            raise RuntimeError("Existing registration differs")
        if not path.exists():
            dump(path,spec)
        return
    if frozen.read(path)!=spec:
        raise RuntimeError("Stable sweep registration differs")
    with ProcessPoolExecutor(args.workers) as pool:
        for percent in (0,-5,5,-2,2,-1,1):
            for group in GROUPS:
                indices=range(1) if not percent else range(12)
                for first in range(0,len(indices),6):
                    futures=[pool.submit(run_trial,percent,group,i) for i in indices[first:first+6]]
                    for future in futures:
                        future.result()
            print("stable hydraulic sweep finished",percent,flush=True)


if __name__=="__main__":
    main()
