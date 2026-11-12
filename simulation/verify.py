"""Checks of causality, legal attacks, and joint-covariance implementation."""
from __future__ import annotations
import copy
import json
from pathlib import Path
import numpy as np
from model import load_model, Model, generate_data, diagonal_blocks
from engine import simulate


def verify(config_path, output_path):
    model=load_model(config_path)
    cfg=copy.deepcopy(model.cfg)
    cfg["T"]=60
    cfg["warmup"]=10
    short=Model.build(cfg)
    seeds=np.arange(600000,604000)
    x,y=generate_data(short,seeds)
    schedule=np.ones((len(seeds),cfg["T"],cfg["N"]),bool)
    run=simulate(short,x,y,seeds,"yang",schedule=schedule,collect=False)
    error=(run.estimates[:,-1]-x[:,-1,None,:]).reshape(len(seeds),-1)
    empirical=error.T@error/len(seeds)
    exact=short.nominal_covariance[-1]
    covariance_error=float(np.linalg.norm(empirical-exact)/np.linalg.norm(exact))
    # Monte Carlo tolerance is intentionally loose; catches shared-noise and indexing errors.
    assert covariance_error<0.10,(covariance_error,"joint covariance mismatch")
    analytic=np.trace(diagonal_blocks(exact,cfg["N"],cfg["n"]),axis1=-2,axis2=-1).mean()
    empirical_mse=float(np.sum(error.reshape(len(seeds),cfg["N"],cfg["n"])**2,axis=-1).mean())

    c=copy.deepcopy(model.cfg)
    c["T"]=80;c["warmup"]=10
    c["attack"]["start"]=25;c["attack"]["end_inclusive"]=44;c["attack"]["replay_packet_lag"]=3
    small=Model.build(c)
    s=np.arange(800000,800006)
    xx,yy=generate_data(small,s)
    clean=simulate(small,xx,yy,s,"yang")
    fixed=clean.sends
    repeated=simulate(small,xx,yy,s,"yang",schedule=fixed)
    assert np.array_equal(clean.estimates,repeated.estimates),"fixed replay schedule differs in nominal run"
    capped=simulate(small,xx,yy,s,"capped",schedule=fixed,cap=np.inf)
    assert np.array_equal(repeated.estimates,capped.estimates),"infinite cap should be identity"
    replay=simulate(small,xx,yy,s,"yang",scenario="replay_packet",schedule=fixed)
    step=simulate(small,xx,yy,s,"yang",scenario="step",schedule=fixed)
    assert np.array_equal(replay.sends,fixed)
    assert np.array_equal(step.estimates[:,:26],clean.estimates[:,:26]),"attack affected pre-update state"
    target_sender=c["attack"]["sender"]
    for trial,t in zip(*np.where(replay.injected)):
        source=replay.replay_source[trial,t]
        assert 0<=source<t
        assert fixed[trial,t,target_sender] and fixed[trial,source,target_sender]
        assert 25<=t<=44
    target_edge=np.flatnonzero(np.all(small.edges==[c["attack"]["sender"],c["attack"]["receiver"]],axis=1))[0]
    unaffected_edges=np.arange(len(small.edges))!=target_edge
    assert not np.any(step.cache_bad[:,:,unaffected_edges]),"direct cache corruption leaked to another edge"
    positive_age_cache=False
    for trial in range(len(s)):
        times=np.flatnonzero(clean.sends[trial,:,target_sender])
        assert np.diff(times).max()<=c["max_interval"]
        positive_age_cache|=bool(np.any(step.cache_bad[trial,45:,target_edge]))
    # Local estimator cannot depend on messages or injected payloads.
    lc=simulate(small,xx,yy,s,"local")
    la=simulate(small,xx,yy,s,"local",scenario="step")
    assert np.array_equal(lc.estimates,la.estimates)
    assert la.sends.sum()==0
    all_sends=np.ones_like(fixed)
    protected=simulate(small,xx,yy,s,"zhou_random",schedule=all_sends,control=.12,cap=.5)
    obs=protected.observations
    d=obs["distance_squared"].reshape(c["T"]-c["warmup"],len(s),len(small.edges))
    w=obs["weight"].reshape(c["T"]-c["warmup"],len(s),len(small.edges))
    for receiver in range(c["N"]):
        incoming=np.flatnonzero(small.edges[:,1]==receiver)
        for e1 in incoming:
            for e2 in incoming:
                # A shared threshold cannot reject the smaller difference while
                # accepting the larger one at the same receiving node and time.
                assert np.all((d[:,:,e1]-d[:,:,e2])*(w[:,:,e1]-w[:,:,e2])<=1e-14)
    report={"passed":True,"checks":["shared-process full joint covariance vs 4000 independent trials",
        "nominal schedule replay identity","infinite-cap identity","attack causality",
        "only actual historical sent packets used","fixed sending opportunities unchanged",
        "direct cache corruption restricted to attacked edge","max communication gap",
        "local estimator independent of communication attacks","Zhou threshold shared across receiver incoming edges"],
        "joint_covariance_relative_error":covariance_error,"expected_nominal_mse":float(analytic),
        "empirical_nominal_mse":empirical_mse,"replay_injected_packets":int(replay.injected.sum()),
        "post_window_malicious_cache_observed":positive_age_cache,
        "warning":"This validates implementation of the declared research model, not reproduction of all Yang/Zhou paper results."}
    Path(output_path).write_text(json.dumps(report,indent=2),encoding="utf-8")
    return report


if __name__=="__main__":
    import argparse
    p=argparse.ArgumentParser();p.add_argument("--config",default="simulation/config.json");p.add_argument("--output",default="simulation/verification.json")
    a=p.parse_args();print(json.dumps(verify(a.config,a.output),indent=2))
