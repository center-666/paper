"""Independent, deliberately non-isotropic checks of the declared research model.

This script does not modify the estimator, calibration, or existing runs.
It is not a reproduction of a complete published algorithm.
"""
from __future__ import annotations
import copy
import hashlib
import json
from pathlib import Path
import time
import numpy as np

from model import Model, nominal_gains, generate_data
from engine import simulate
from calibration import Calibration


def expected_step(A,H,K,edges,eps,hat,y,caches):
    """Straight node-by-node column-vector calculation, no stacked B or einsum."""
    result=np.empty_like(hat)
    for s in range(len(hat)):
        for i in range(len(H)):
            value=A@hat[s,i]+K[i]@(y[s,i]-H[i]@hat[s,i])
            for edge,(j,receiver) in enumerate(edges):
                if receiver==i:
                    value=value+eps*A@(caches[s,edge]-hat[s,i])
            result[s,i]=value
    return result


def propagated_covariance(A,H,R,Q,P,K,edges,eps):
    """Independent covariance from scalar noise-basis responses of manual equations."""
    N,n=len(H),len(A)
    total=N*n+n+N*n
    response=np.empty((N*n,total))
    for basis in range(total):
        previous=np.zeros((N,n));process=np.zeros(n);measurement=np.zeros((N,n))
        if basis<N*n:previous.reshape(-1)[basis]=1
        elif basis<N*n+n:process[basis-N*n]=1
        else:measurement.reshape(-1)[basis-(N*n+n)]=1
        next_error=np.empty_like(previous)
        for i in range(N):
            value=A@previous[i]-K[i]@(H[i]@previous[i])+process-K[i]@measurement[i]
            for j,receiver in edges:
                if receiver==i:value+=eps*A@(previous[j]-previous[i])
            next_error[i]=value
        response[:,basis]=next_error.reshape(-1)
    input_cov=np.zeros((total,total))
    input_cov[:N*n,:N*n]=P
    input_cov[N*n:N*n+n,N*n:N*n+n]=Q
    for i in range(N):
        sl=slice(N*n+n+i*n,N*n+n+(i+1)*n)
        input_cov[sl,sl]=R[i]
    return response@input_cov@response.T


def mixed_model(base):
    cfg=copy.deepcopy(base)
    cfg.update(N=3,n=2,T=30,warmup=3,epsilon=.07,max_interval=10)
    cfg["edges_sender_receiver"]=[[0,1],[1,2],[2,0],[0,2]]
    cfg["attack"].update(sender=0,receiver=1,start=10,end_inclusive=15,replay_packet_lag=2)
    A=np.array([[1.02,.18],[-.04,.95]])
    Q=np.array([[.03,.008],[.008,.02]])
    P0=np.array([[.8,.25],[.25,.6]])
    H=np.array([[[1,.2],[-.1,.7]],[[.6,-.3],[.4,1.1]],[[1.2,.1],[.2,.5]]])
    R=np.array([[[.05,.01],[.01,.03]],[[.07,-.015],[-.015,.04]],[[.025,.006],[.006,.06]]])
    edges=np.asarray(cfg["edges_sender_receiver"])
    gains,cov=nominal_gains(A,Q,P0,H,R,edges,cfg["epsilon"],cfg["T"])
    local,_=nominal_gains(A,Q,P0,H,R,edges,0,cfg["T"])
    powers=np.stack([np.linalg.matrix_power(A,k) for k in range(cfg["T"]+1)])
    return Model(cfg,A,Q,P0,H,R,edges,powers,gains,local,cov)


def check_nondiagonal(model):
    cfg=model.cfg;N,n,T=cfg["N"],cfg["n"],cfg["T"]
    worst=0.
    for t in range(T):
        independent=propagated_covariance(model.A,model.H,model.R,model.Q,
                    model.nominal_covariance[t],model.gains[t],model.edges,cfg["epsilon"])
        difference=np.linalg.norm(independent-model.nominal_covariance[t+1])
        worst=max(worst,float(difference))
    assert worst<1e-11

    # A distinct vectorized state simulation, with its own noise generation.
    rng=np.random.default_rng(780310)
    count=20000
    state=rng.multivariate_normal(np.zeros(n),model.P0,size=count)
    hat=np.zeros((count,N,n))
    for t in range(T):
        measurement=np.stack([state@model.H[i].T+rng.multivariate_normal(np.zeros(n),model.R[i],size=count) for i in range(N)],axis=1)
        next_hat=np.empty_like(hat)
        for i in range(N):
            value=hat[:,i]@model.A.T+(measurement[:,i]-hat[:,i]@model.H[i].T)@model.gains[t,i].T
            for j,receiver in model.edges:
                if receiver==i:value+=cfg["epsilon"]*(hat[:,j]-hat[:,i])@model.A.T
            next_hat[:,i]=value
        state=state@model.A.T+rng.multivariate_normal(np.zeros(n),model.Q,size=count)
        hat=next_hat
    error=(state[:,None,:]-hat).reshape(count,-1)
    empirical=error.T@error/count
    exact=model.nominal_covariance[-1]
    relative=float(np.linalg.norm(empirical-exact)/np.linalg.norm(exact))
    assert relative<.05

    # Test public data generation under correlated measurement/process noise.
    seeds=np.arange(781000,782000)
    x,y=generate_data(model,seeds)
    process=x[:,1:]-x[:,:-1]@model.A.T
    empirical_q=np.cov(process.reshape(-1,n),rowvar=False)
    q_error=float(np.linalg.norm(empirical_q-model.Q)/np.linalg.norm(model.Q))
    r_errors=[]
    for i in range(N):
        noise=y[:,:,i]-x[:,:-1]@model.H[i].T
        covariance=np.cov(noise.reshape(-1,n),rowvar=False)
        r_errors.append(float(np.linalg.norm(covariance-model.R[i])/np.linalg.norm(model.R[i])))
    assert q_error<.05 and max(r_errors)<.05
    small_x,small_y=x[:8],y[:8]
    schedule=np.ones((8,T,N),bool)
    run=simulate(model,small_x,small_y,seeds[:8],"yang",schedule=schedule,collect=False)
    manual=np.zeros_like(run.estimates)
    for t in range(T):
        caches=manual[:,t,model.edges[:,0]]
        manual[:,t+1]=expected_step(model.A,model.H,model.gains[t],model.edges,cfg["epsilon"],manual[:,t],small_y[:,t],caches)
    engine_difference=float(np.max(np.abs(manual-run.estimates)))
    assert engine_difference<1e-12
    assert np.all(run.estimates[:,0]==0)
    return {"independent_basis_max_absolute_covariance_difference":worst,
            "monte_carlo_trials":count,"monte_carlo_seed":780310,
            "monte_carlo_relative_covariance_difference":relative,
            "data_generator_process_covariance_relative_difference":q_error,
            "data_generator_measurement_covariance_relative_differences":r_errors,
            "manual_node_update_vs_engine_max_absolute_difference":engine_difference}


def check_cache_and_causality(base):
    cfg=copy.deepcopy(base)
    cfg.update(N=2,n=2,T=7,warmup=0,epsilon=.2,max_interval=10)
    cfg["edges_sender_receiver"]=[[0,1],[1,0]]
    cfg["attack"].update(sender=0,receiver=1,start=1,end_inclusive=1,bias=[3.,-1.])
    A=np.array([[1.,.5],[0.,1.]])
    H=np.repeat(np.eye(2)[None],2,axis=0)
    gains=np.repeat(H[None],cfg["T"],axis=0)
    model=Model(cfg,A,np.eye(2),np.eye(2),H,H.copy(),np.asarray(cfg["edges_sender_receiver"]),
        np.stack([np.linalg.matrix_power(A,k) for k in range(cfg["T"]+1)]),gains,gains.copy(),np.zeros((cfg["T"]+1,4,4)))
    x=np.zeros((1,cfg["T"]+1,2));y=np.zeros((1,cfg["T"],2,2))
    y[0,0,0]=[1.,2.]
    schedule=np.zeros((1,cfg["T"],2),bool)
    schedule[0,[0,1,4],0]=True;schedule[0,[0,2,4],1]=True
    run=simulate(model,x,y,np.array([820001]),"yang","step",schedule=schedule)
    manual=np.zeros_like(run.estimates)
    caches=np.zeros((1,2,2));received=np.zeros((1,2),int)
    aligned_saved=[]
    for t in range(cfg["T"]):
        for edge,(sender,receiver) in enumerate(model.edges):
            if schedule[0,t,sender]:
                caches[0,edge]=manual[0,t,sender]
                if t==1 and edge==0:caches[0,edge]+=np.array([3.,-1.])
                received[0,edge]=t
        aligned=np.empty_like(caches)
        for edge in range(2):aligned[0,edge]=np.linalg.matrix_power(A,t-received[0,edge])@caches[0,edge]
        aligned_saved.append(aligned.copy())
        manual[:,t+1]=expected_step(A,H,gains[t],model.edges,cfg["epsilon"],manual[:,t],y[:,t],aligned)
    assert np.max(np.abs(manual-run.estimates))<1e-12
    assert np.allclose(run.estimates[0,2,1],[.9,.2],atol=1e-14)
    assert np.allclose(run.estimates[0,3,1],[.9,.16],atol=1e-14)
    assert run.injected[0].tolist()==[False,True,False,False,False,False,False]
    assert run.cache_bad[0,:,0].tolist()==[False,True,True,True,False,False,False]
    assert not run.cache_bad[0,:,1].any()
    assert np.allclose(aligned_saved[2][0,0],[4.5,1.])
    assert np.allclose(aligned_saved[3][0,0],[5.,1.])
    assert np.allclose(aligned_saved[4][0,0],run.estimates[0,4,0])
    # Truth passed to simulate is evaluative, not an estimator input.
    changed_truth=np.full_like(x,1e8)
    same=simulate(model,changed_truth,y,np.array([820001]),"yang","step",schedule=schedule)
    assert np.array_equal(same.estimates,run.estimates)
    assert np.array_equal(same.sends,run.sends)
    # Future measurements must not alter estimates already calculated.
    future=y.copy();future[:,3:]+=1000
    changed=simulate(model,x,future,np.array([820001]),"yang","step",schedule=schedule)
    assert np.array_equal(changed.estimates[:,:4],run.estimates[:,:4])
    # Reuse a legal, fixed synthetic scoring rule to check the defended branch too.
    E,B=2,len(cfg["interval_upper_bounds"])
    calibration=Calibration("interval_tail",np.zeros((E,2)),np.repeat(np.eye(2)[None],E,axis=0),np.ones(E),
          np.zeros((E,B,2)),np.tile(np.eye(2),(E,B,1,1)),np.ones((E,B)),np.full((E,B),1000),np.full((E,B),1000),np.zeros((E,B),bool))
    defense=simulate(model,x,y,np.array([820001]),"interval_tail","step",schedule=schedule,calibration=calibration,control=.8,cap=2.)
    defense_truth=simulate(model,changed_truth,y,np.array([820001]),"interval_tail","step",schedule=schedule,calibration=calibration,control=.8,cap=2.)
    assert np.array_equal(defense.estimates,defense_truth.estimates)
    assert np.array_equal(defense.weights,defense_truth.weights)
    return {"manual_one_step_attacked_receiver":[.9,.2],"manual_next_step_no_new_packet":[.9,.16],
            "manual_engine_max_difference":float(np.max(np.abs(manual-run.estimates))),
            "direct_bad_cache_mask":run.cache_bad[0,:,0].tolist(),
            "injected_only_at_actual_packet":True,"normal_packet_overwrites_direct_cache_flag":True,
            "truth_argument_invariance_nominal_and_scored":True,"future_measurement_causality":True,
            "note":"A current normal sender estimate may be indirectly contaminated; clearing cache_bad only denotes no direct payload substitution."}


def main():
    root=Path(__file__).resolve().parent
    folder=root/"checks"/"2026-11-10_independent"
    if folder.exists():raise FileExistsError("Do not overwrite independent check evidence")
    folder.mkdir(parents=True)
    base=json.loads((root/"config.json").read_text(encoding="utf-8-sig"))
    model=mixed_model(base)
    start=time.perf_counter()
    result={"passed":False}
    try:
        result["nondiagonal_case"]=check_nondiagonal(model)
        result["cache_and_causality_case"]=check_cache_and_causality(base)
        result["passed"]=True
    finally:
        result["elapsed_seconds"]=time.perf_counter()-start
        result["limitations"]=["No full-paper reproduction or stability proof",
            "Public configuration builder still supports scaled identity H and isotropic R; general matrices injected only for checks",
            "These tests do not certify train/validation split logic or calibration contribution; separate audit required"]
        (folder/"results.json").write_text(json.dumps(result,indent=2),encoding="utf-8")
        configuration={"A":model.A.tolist(),"Q":model.Q.tolist(),"P0":model.P0.tolist(),"H":model.H.tolist(),"R":model.R.tolist(),"edges":model.edges.tolist(),"epsilon":model.cfg["epsilon"],"T":model.cfg["T"],"numpy":np.__version__,"source_hashes":{name:hashlib.sha256((root/name).read_bytes()).hexdigest() for name in ("model.py","engine.py","calibration.py","independent_checks.py")}}
        (folder/"config.json").write_text(json.dumps(configuration,indent=2),encoding="utf-8")
        (folder/"independent_checks.py").write_bytes(Path(__file__).read_bytes())
    print(json.dumps(result,indent=2))


if __name__=="__main__":main()
