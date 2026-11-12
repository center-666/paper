"""Causal cache-prefix whitening, phase-separated moments and sequential baselines.

Empirical moment models are approximate under selection/feedback; no exact
Gaussian or independent-increments claim is made for an operating estimator.
All online inputs are local measurements, received cache and reception age.
"""
from __future__ import annotations
from dataclasses import dataclass
import json
from pathlib import Path
import numpy as np

PHASES=("initial","transient","steady")
DETECTORS=("instant","mean","white_window","white_cusum","white_signed_cusum")


def phase_of(start,warmup=50):
    if np.isscalar(start):return 0 if start==0 else 1 if start<warmup else 2
    return np.where(np.asarray(start)==0,0,np.where(np.asarray(start)<warmup,1,2))


@dataclass
class Episode:
    trajectory:int
    edge:int
    start:int
    complete:bool
    residuals:np.ndarray
    maximum:float=0.0
    alarm:bool=False


def save_episodes(path,episodes,max_length,m):
    padded=np.zeros((len(episodes),max_length,m))
    for k,ep in enumerate(episodes):padded[k,:len(ep.residuals)]=ep.residuals
    np.savez_compressed(path,trajectory=np.array([ep.trajectory for ep in episodes]),edge=np.array([ep.edge for ep in episodes]),
        start=np.array([ep.start for ep in episodes]),complete=np.array([ep.complete for ep in episodes]),
        length=np.array([len(ep.residuals) for ep in episodes]),residuals=padded,
        maximum=np.array([ep.maximum for ep in episodes]),alarm=np.array([ep.alarm for ep in episodes]))


class PhaseStatistics:
    def __init__(self,E,m,max_length,warmup,window=4,signed_reference=.5):
        self.E=E;self.m=m;self.max_length=max_length;self.warmup=warmup
        self.window=window;self.signed_reference=signed_reference
        self.models={};self.thresholds={d:np.ones((3,E)) for d in DETECTORS}
        self.counts=[]

    @classmethod
    def fit(cls,train,cal,E,m,max_length,warmup,window=4,signed_reference=.5,ridge=.001):
        obj=cls(E,m,max_length,warmup,window,signed_reference)
        train=[ep for ep in train if ep.complete]
        cal=[ep for ep in cal if ep.complete]
        for phase in range(3):
            for edge in range(E):
                rows=[ep.residuals for ep in train if ep.edge==edge and phase_of(ep.start,warmup)==phase]
                calibration=[ep.residuals for ep in cal if ep.edge==edge and phase_of(ep.start,warmup)==phase]
                if len(rows)<3 or len(calibration)<3:raise ValueError("Insufficient phase/edge normal episodes")
                pooled=np.concatenate(rows);pooled_mean=pooled.mean(axis=0);pooled_cov=np.cov(pooled,rowvar=False)
                for length in range(1,max_length+1):
                    selected=[r[:length].reshape(-1) for r in rows if len(r)>=length]
                    fallback=len(selected)<max(40,length*m+2)
                    if not fallback:
                        z=np.asarray(selected);mean=z.mean(axis=0);S=np.cov(z,rowvar=False)
                    else:
                        mean=np.zeros(length*m);S=np.zeros((length*m,length*m))
                        for age in range(length):
                            subset=np.asarray([r[age] for r in rows if len(r)>age]);sl=slice(age*m,(age+1)*m)
                            mu,cov=(subset.mean(axis=0),np.cov(subset,rowvar=False)) if len(subset)>=3 else (pooled_mean,pooled_cov)
                            mean[sl]=mu;S[sl,sl]=cov
                    S=(S+S.T)/2+ridge*max(np.trace(S)/(length*m),1e-9)*np.eye(length*m)
                    inverse_chol=np.linalg.solve(np.linalg.cholesky(S),np.eye(length*m))
                    C=np.tile(np.eye(m),(1,length))/length
                    obj.models[phase,edge,length]={"mean":mean,"cov":S,"whiten_last":inverse_chol[-m:],
                        "instant_mu":mean[-m:],"instant_P":np.linalg.inv(S[-m:,-m:]),
                        "mean_P":C.T@np.linalg.solve(C@S@C.T,C),"fallback":fallback,"train_count":len(selected)}
                    obj.counts.append({"phase":PHASES[phase],"edge":edge,"length":length,"train_count":len(selected),
                        "cal_count":sum(len(r)>=length for r in calibration),"fallback":bool(fallback)})
                maxima={d:[] for d in DETECTORS}
                for length in sorted({len(r) for r in calibration}):
                    batch=np.asarray([r for r in calibration if len(r)==length])
                    scores=obj.episode_scores(phase,edge,batch)
                    for d in DETECTORS:maxima[d].extend(np.max(scores[d],axis=1))
                for d in DETECTORS:obj.thresholds[d][phase,edge]=max(float(np.quantile(maxima[d],.95,method="higher")),1e-10)
        return obj

    def current(self,phase,edge,prefix):
        length=prefix.shape[1];fit=self.models[int(phase),int(edge),length]
        d=prefix.reshape(len(prefix),-1)-fit["mean"]
        last=prefix[:,-1]-fit["instant_mu"]
        return {"innovation":d@fit["whiten_last"].T,
            "instant":np.maximum(np.einsum("bi,ij,bj->b",last,fit["instant_P"],last),0),
            "mean":np.maximum(np.einsum("bi,ij,bj->b",d,fit["mean_P"],d),0)}

    def episode_scores(self,phase,edge,batch):
        S,L,_=batch.shape;output={d:np.zeros((S,L)) for d in DETECTORS}
        energies=np.zeros((S,L));cusum=np.zeros(S);plus=np.zeros((S,self.m));minus=plus.copy()
        for age in range(L):
            cur=self.current(phase,edge,batch[:,:age+1]);z=cur["innovation"]
            energies[:,age]=np.sum(z*z,axis=1);cusum=np.maximum(0,cusum+energies[:,age]-self.m)
            plus=np.maximum(0,plus+z-self.signed_reference);minus=np.maximum(0,minus-z-self.signed_reference)
            output["instant"][:,age]=cur["instant"];output["mean"][:,age]=cur["mean"]
            output["white_window"][:,age]=energies[:,max(0,age-self.window+1):age+1].sum(axis=1)
            output["white_cusum"][:,age]=cusum
            output["white_signed_cusum"][:,age]=np.maximum(plus.max(axis=1),minus.max(axis=1))
        return output

    def save(self,path):
        arrays={"metadata":np.asarray(json.dumps({"E":self.E,"m":self.m,"max_length":self.max_length,"warmup":self.warmup,
            "window":self.window,"signed_reference":self.signed_reference,"counts":self.counts}))}
        for d,q in self.thresholds.items():arrays["threshold_"+d]=q
        for (phase,edge,length),fit in self.models.items():
            for name,value in fit.items():
                if isinstance(value,np.ndarray):arrays[f"p{phase}_e{edge}_l{length}_{name}"]=value
        np.savez_compressed(path,**arrays)


class SequentialController:
    def __init__(self,model,statistics=None,method="age_only",multipliers=None,half_life=4,record_residuals=False,carry_across_packets=False):
        self.model=model;self.statistics=statistics;self.method=method;self.half_life=half_life
        self.multipliers=np.ones(3) if multipliers is None else np.asarray(multipliers)
        self.record_residuals=record_residuals;self.buf=None;self.episodes=[];self._finished=False
        self.carry_across_packets=carry_across_packets
        if carry_across_packets and method not in {"white_cusum","white_signed_cusum"}:
            raise ValueError("Carry state is only defined for the CUSUM comparators")

    def _flush(self,mask,complete):
        for trial,edge in zip(*np.where(mask)):
            L=int(self.length[trial,edge])
            if not L:continue
            residuals=self.buf[trial,edge,:L].copy() if self.record_residuals else np.empty((L,0))
            self.episodes.append(Episode(int(trial),int(edge),int(self.starts[trial,edge]),complete,residuals,
                float(self.max_ratio[trial,edge]),bool(self.bad[trial,edge])))

    def update(self,t,fresh,age,aligned,measurement,local_hat):
        S,E=fresh.shape;m=self.model.cfg["n"];L=self.model.cfg["max_interval"]
        if self.buf is None:
            self.buf=np.zeros((S,E,L,m));self.length=np.zeros((S,E),int);self.starts=np.full((S,E),-1,int)
            self.bad=np.zeros((S,E),bool);self.max_ratio=np.zeros((S,E));self.energy=np.zeros((S,E,L))
            self.cs=np.zeros((S,E));self.cp=np.zeros((S,E,m));self.cm=np.zeros((S,E,m))
        self._flush(fresh&(self.starts>=0),True)
        self.starts=np.where(fresh,t,self.starts);self.length=np.where(fresh,0,self.length)
        self.buf=np.where(fresh[...,None,None],0,self.buf);self.energy=np.where(fresh[...,None],0,self.energy)
        if not self.carry_across_packets:
            self.cs=np.where(fresh,0,self.cs);self.cp=np.where(fresh[...,None],0,self.cp);self.cm=np.where(fresh[...,None],0,self.cm)
        self.bad=np.where(fresh,False,self.bad);self.max_ratio=np.where(fresh,0,self.max_ratio)
        residual=measurement-np.einsum("emn,sen->sem",self.model.H[self.model.edges[:,1]],aligned)
        phases=phase_of(self.starts,self.model.cfg["warmup"])
        for edge in range(E):
            for a in np.unique(age[:,edge]):
                ids=np.flatnonzero(age[:,edge]==a);a=int(a)
                if a>=L:raise ValueError("Cache exceeded supported age; no silent extension")
                self.buf[ids,edge,a]=residual[ids,edge];self.length[ids,edge]=a+1
                if self.statistics is None or self.method=="age_only":continue
                for phase in np.unique(phases[ids,edge]):
                    ii=ids[phases[ids,edge]==phase];phase=int(phase)
                    cur=self.statistics.current(phase,edge,self.buf[ii,edge,:a+1]);z=cur["innovation"]
                    en=np.sum(z*z,axis=1);self.energy[ii,edge,a]=en
                    self.cs[ii,edge]=np.maximum(0,self.cs[ii,edge]+en-m)
                    self.cp[ii,edge]=np.maximum(0,self.cp[ii,edge]+z-self.statistics.signed_reference)
                    self.cm[ii,edge]=np.maximum(0,self.cm[ii,edge]-z-self.statistics.signed_reference)
                    if self.method in {"instant","mean"}:score=cur[self.method]
                    elif self.method=="white_window":score=self.energy[ii,edge,max(0,a-self.statistics.window+1):a+1].sum(axis=1)
                    elif self.method=="white_cusum":score=self.cs[ii,edge]
                    elif self.method=="white_signed_cusum":score=np.maximum(self.cp[ii,edge].max(axis=1),self.cm[ii,edge].max(axis=1))
                    else:raise ValueError(self.method)
                    ratio=score/self.statistics.thresholds[self.method][phase,edge]
                    self.max_ratio[ii,edge]=np.maximum(self.max_ratio[ii,edge],ratio)
                    alarm=ratio>self.multipliers[phase]
                    self.bad[ii,edge]|=alarm
                    if self.carry_across_packets:
                        # Preserve accumulated evidence across NEW messages, but reset
                        # detector sums after an alarm as in ordinary CUSUM operation.
                        # An isolated current cache remains isolated until replacement.
                        jj=ii[alarm];self.cs[jj,edge]=0;self.cp[jj,edge]=0;self.cm[jj,edge]=0
        return (~self.bad).astype(float)*np.exp(-np.log(2)*age/self.half_life)

    def finish(self):
        if not self._finished:
            self._flush(self.starts>=0,False);self._finished=True
        return self.episodes


def phase_rates(episodes,warmup=50):
    return {phase:{"count":sum(ep.complete and phase_of(ep.start,warmup)==p for ep in episodes),
                   "false_isolation_rate":float(np.mean([ep.alarm for ep in episodes if ep.complete and phase_of(ep.start,warmup)==p]))}
            for p,phase in enumerate(PHASES)}


def retune_multipliers(episodes,warmup=50):
    result=[]
    for phase in range(3):
        values=[ep.maximum for ep in episodes if ep.complete and phase_of(ep.start,warmup)==phase]
        if not values:raise ValueError("No complete tuning episodes in phase")
        result.append(max(float(np.quantile(values,.95,method="higher")),1e-8))
    return np.asarray(result)
