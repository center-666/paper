"""Focused checks of new validation-only branches before using holdout seeds."""
from __future__ import annotations
import copy
import json
from pathlib import Path
import numpy as np
from model import Model,generate_data
from engine import simulate,basic_metrics
from calibration import Calibration
from validation_suite import repeated_schedule,audit_run
from run_study import write_json


def main():
    old=Path("simulation/runs/2026-11-10_five_node_v2")
    cfg=json.loads((old/"config.json").read_text(encoding="utf-8"))
    plan=json.loads(Path("simulation/validation_plan.json").read_text(encoding="utf-8"))
    m=Model.build(cfg)
    with np.load(old/"test_inputs.npz") as f:x,y,seeds,schedule=(f[k][:3] for k in ("x","y","seeds","reference_schedule"))
    controls=json.loads((old/"reference_schedule/policy_controls.json").read_text(encoding="utf-8"))
    regression={}
    for method in ("yang","interval_scale","zhou_random"):
        cal=Calibration.load(old/("reference_schedule/"+method+"_calibration.npz")) if method=="interval_scale" else None
        c=controls[method]
        run=simulate(m,x,y,seeds,method,"replay_packet",schedule,cal,c["control"],c["cap"])
        with np.load(old/("reference_schedule/"+method+"__replay_packet.npz")) as f:
            error=float(np.max(np.abs(run.estimates-f["estimates"][:3])))
        assert error<1e-12
        regression[method]=error
    c=copy.deepcopy(cfg);c["T"]=180;c["warmup"]=20
    c["attack"].update(start=100,end_inclusive=139,matched_replay_time_lag=80,low_bias_factor=.25)
    model=Model.build(c);s=np.arange(970000,970003);xx,yy=generate_data(model,s)
    fixed=repeated_schedule(c,len(s),plan)
    replay=simulate(model,xx,yy,s,"yang","replay_matched",fixed)
    metrics,_=basic_metrics(model,replay,xx)
    pairs=audit_run(model,replay,xx,s,fixed,"replay_matched",metrics)
    assert pairs>0
    target=np.flatnonzero(np.all(model.edges==[0,1],axis=1))[0]
    for trial in range(len(s)):
        times=np.flatnonzero(replay.injected[trial])
        for prev,t in zip(times[:-1],times[1:]):
            source=t-80;oldprev=prev-80
            expected=replay.estimates[trial,source,0]-model.powers[t-prev]@replay.estimates[trial,oldprev,0]
            obs=replay.observations;mask=(obs["trajectory"]==trial)&(obs["time"]==t)&(obs["edge"]==target)
            assert mask.sum()==1 and np.allclose(obs["temporal"][mask][0],expected,atol=1e-12)
    low=simulate(model,xx,yy,s,"yang","low_step",fixed)
    c2=copy.deepcopy(c);c2["attack"]["bias"]=(.25*np.asarray(c2["attack"]["bias"])).tolist()
    scaled=simulate(Model.build(c2),xx,yy,s,"yang","step",fixed)
    assert np.array_equal(low.estimates,scaled.estimates)
    for trial in range(len(s)):
        for node in range(c["N"]):
            ticks=np.flatnonzero(fixed[trial,:,node])
            assert np.diff(ticks).max()<=c["max_interval"]
            assert c["T"]-1-ticks[-1]<c["max_interval"]
    report={"passed":True,"previous_v2_estimate_regression_max_errors":regression,"matched_replay_pairs_checked":pairs,
        "checks":["old method outputs preserved","matched replay source packets legal and time gaps identical",
                  "actual temporal residual equals replay-history dynamic difference after boundary","low_step equals fixed 0.25-amplitude step",
                  "repeated schedule respects max gaps including final tail"],"holdout_validation_seeds_used":False}
    out=Path("simulation/checks/2026-11-10_validation_extensions");out.mkdir(parents=True,exist_ok=False)
    write_json(out/"results.json",report)
    import shutil
    shutil.copy2(__file__,out/"validate_extensions.py")
    print(json.dumps(report))


if __name__=="__main__":main()
