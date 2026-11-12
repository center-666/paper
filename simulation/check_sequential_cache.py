"""Independent checks for causal whitening and recursive/whole-prefix agreement."""
from __future__ import annotations
import copy,json
from pathlib import Path
import numpy as np
from model import Model
from sequential_cache import Episode,PhaseStatistics,SequentialController,DETECTORS
from run_study import write_json


def main():
    out=Path("simulation/checks/2026-11-11_sequential_cache")
    if out.exists():raise FileExistsError("Preserve check records")
    out.mkdir(parents=True)
    rng=np.random.default_rng(221106)
    cfg=json.loads(Path("simulation/config.json").read_text(encoding="utf-8"))
    cfg.update(N=2,T=80,H_scales=[1.,.8],R_variances=[.05,.08],edges_sender_receiver=[[0,1],[1,0]],max_interval=8)
    model=Model.build(cfg);m=2;L=8
    C=np.kron(.7*np.ones((L,L))+.25*np.eye(L),np.array([[1.,.2],[.2,.8]]))
    chol=np.linalg.cholesky(C)
    def samples(count):
        eps=[]
        for phase,start in enumerate((0,10,60)):
            for e in range(2):
                scale=1+phase+e*.2
                z=(rng.standard_normal((count,2*L))@chol.T*scale).reshape(count,L,2)
                eps.extend(Episode(j,e,start,True,r) for j,r in enumerate(z))
        return eps
    train,cal=samples(1000),samples(1000)
    st=PhaseStatistics.fit(train,cal,2,2,8,50)
    max_conditional=0
    for phase in range(3):
        for e in range(2):
            for length in range(2,9):
                fit=st.models[phase,e,length];S=fit["cov"]
                coeff=np.linalg.solve(S[:-2,:-2],S[:-2,-2:]).T
                R=S[-2:,-2:]-coeff@S[:-2,-2:]
                Cinv=np.linalg.inv(np.linalg.cholesky(R))
                row=Cinv@np.c_[-coeff,np.eye(2)]
                max_conditional=max(max_conditional,float(np.max(np.abs(row-fit["whiten_last"]))))
    assert max_conditional<1e-10
    residual=(rng.standard_normal((12,2,L*2))@chol.T).reshape(12,2,L,2)
    max_score_error=0
    for detector in DETECTORS:
        controller=SequentialController(model,st,detector,np.ones(3),4)
        expected=[st.episode_scores(0,e,residual[:,e]) for e in range(2)]
        for age in range(8):
            fresh=np.full((12,2),age==0);ages=np.full((12,2),age)
            w=controller.update(age,fresh,ages,np.zeros((12,2,2)),residual[:,:,age],np.zeros((12,2,2)))
            for e in range(2):
                ratio=expected[e][detector][:,:age+1].max(axis=1)/st.thresholds[detector][0,e]
                max_score_error=max(max_score_error,float(np.max(np.abs(controller.max_ratio[:,e]-ratio))))
                assert np.array_equal(w[:,e]==0,ratio>1)
        controller.update(8,np.ones((12,2),bool),np.zeros((12,2),int),np.zeros((12,2,2)),np.zeros((12,2,2)),np.zeros((12,2,2)))
        ep=controller.finish();assert sum(z.complete for z in ep)==24 and sum(not z.complete for z in ep)==24
        assert all(z.start==0 and len(z.residuals)==8 for z in ep if z.complete)
        assert all(z.start==8 and len(z.residuals)==1 for z in ep if not z.complete)
    assert max_score_error<1e-10
    # Changing future residuals does not change any earlier score from prefix evaluation.
    b=residual[:,0].copy();a=st.episode_scores(0,0,b);b[:,4:]+=1000;c=st.episode_scores(0,0,b)
    assert all(np.array_equal(a[d][:,:4],c[d][:,:4]) for d in DETECTORS)
    # Whitening a population with the training model covariance is identity in expectation.
    fit=st.models[2,0,8];z=rng.standard_normal((20000,16))@np.linalg.cholesky(fit["cov"]).T+fit["mean"]
    white=np.linalg.solve(np.linalg.cholesky(fit["cov"]),(z-fit["mean"]).T).T
    cov=np.cov(white,rowvar=False);max_population=float(np.max(np.abs(cov-np.eye(16))))
    assert max_population<.05
    report={"passed":True,"conditional_whitening_vs_schur_max_error":max_conditional,
        "online_vs_prefix_detector_max_error":max_score_error,"population_whitened_cov_max_error":max_population,
        "detectors":list(DETECTORS),"future_residual_invariance":True,"complete_censored_phase_boundary_checks":True,
        "study_holdout_seeds_used":False,"scope":"Implementation checks under a known Gaussian covariance, not a deployment Gaussianity guarantee"}
    write_json(out/"results.json",report)
    import shutil
    shutil.copy2(__file__,out/Path(__file__).name);shutil.copy2("simulation/sequential_cache.py",out/"sequential_cache.py")
    print(json.dumps(report))


if __name__=="__main__":main()
