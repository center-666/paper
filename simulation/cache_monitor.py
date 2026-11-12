"""Correlated cache-residual prefix statistics with episode-level calibration.

This module never reads the latent system state or modifies an estimator.
Each episode starts at a received packet (age zero), with subsequent rows
representing residuals y_i-H_i A^age payload before the next packet arrives.
Calibration controls a maximum over a whole episode, not independent tests
of its correlated prefixes. Statistical guarantees beyond the calibration
distribution are not asserted.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Iterable, Mapping

import numpy as np


METRICS = ("instant", "joint", "gls", "mean")


@dataclass(frozen=True)
class CacheEpisode:
    edge: int
    residuals: np.ndarray


def _parts(episode):
    if isinstance(episode, CacheEpisode):
        return int(episode.edge), np.asarray(episode.residuals, float)
    if isinstance(episode, Mapping):
        return int(episode["edge"]), np.asarray(episode["residuals"], float)
    if isinstance(episode, (tuple, list)) and len(episode) == 2:
        return int(episode[0]), np.asarray(episode[1], float)
    raise TypeError("Use CacheEpisode, {'edge','residuals'}, or (edge,residuals)")


def _moments(rows, ridge):
    rows = np.asarray(rows, float)
    mean = rows.mean(axis=0)
    centered = rows - mean
    covariance = centered.T @ centered / max(1, len(rows)-1)
    scale = max(float(np.trace(covariance))/covariance.shape[0], 1e-12)
    covariance = (covariance+covariance.T)/2 + ridge*scale*np.eye(covariance.shape[0])
    return mean, covariance


def _qform(centered, matrix):
    return np.maximum(0.0, np.einsum("bi,ij,bj->b", centered, matrix, centered, optimize=True))


class CacheMonitor:
    """Four scores with shared normal prefix moments.

    Inputs accept scalar or vector measurements; H_by_edge has shape (m,n)
    per directed edge. `scores_batch(edge, prefixes)` accepts (S,L,m) and
    returns dict(metric -> array[S]); L is current age+1, never future length.
    It is safe to group online evaluations by known edge/current age.
    """
    def __init__(self, H_by_edge, A, max_age, min_samples, ridge_relative,
                 false_alarm_target, models, thresholds, cal_counts, coverage,
                 packet_thresholds=None):
        self.H_by_edge = H_by_edge
        self.A = A
        self.max_age = int(max_age)
        self.min_samples = int(min_samples)
        self.ridge_relative = float(ridge_relative)
        self.false_alarm_target = float(false_alarm_target)
        self.models = models
        self.thresholds = thresholds
        self.calibration_episode_counts = cal_counts
        self.calibration_prefix_counts = coverage
        self.packet_thresholds = {} if packet_thresholds is None else packet_thresholds

    @classmethod
    def fit(cls, train_episodes: Iterable, calibration_episodes: Iterable,
            H_by_edge=None, A=None, max_age=10, min_samples=40,
            ridge_relative=1e-3, false_alarm_target=.05, *, edge_h=None):
        if H_by_edge is None:
            H_by_edge = edge_h
        if H_by_edge is None or A is None:
            raise ValueError("H_by_edge and A are required")
        A = np.asarray(A, float)
        h = {int(e):np.atleast_2d(np.asarray(H,float)) for e,H in dict(H_by_edge).items()}
        if not h or max_age < 0 or min_samples < 2 or ridge_relative <= 0:
            raise ValueError("Invalid dimensions/configuration")
        if not 0 < false_alarm_target < 1:
            raise ValueError("false_alarm_target must lie in (0,1)")

        def prepare(episodes):
            grouped = {e:[] for e in h}
            for episode in episodes:
                e,r = _parts(episode)
                if e not in h:
                    raise ValueError(f"Unknown edge {e}")
                if r.ndim == 1 and len(h[e]) == 1:
                    r = r[:,None]
                if r.ndim != 2 or r.shape[1] != len(h[e]) or not len(r):
                    raise ValueError(f"Malformed residual episode on edge {e}")
                if len(r) > max_age+1:
                    raise ValueError("Episode exceeds max_age; do not silently drop later alarm opportunities")
                if not np.isfinite(r).all():
                    raise ValueError("Nonfinite residual")
                grouped[e].append(r)
            return grouped

        train,cal = prepare(train_episodes),prepare(calibration_episodes)
        models={}
        for e,H in h.items():
            m,n=H.shape
            if A.shape != (n,n) or len(train[e])<2 or len(cal[e])<2:
                raise ValueError(f"Insufficient data or incompatible A for edge {e}")
            all_rows=np.concatenate(train[e])
            pooled_mean,pooled_cov=_moments(all_rows,ridge_relative)
            for L in range(1,max_age+2):
                rows=[r[:L].reshape(-1) for r in train[e] if len(r)>=L]
                count=len(rows)
                fallback=count<max(min_samples,L*m+2)
                if not fallback:
                    mean,cov=_moments(np.asarray(rows),ridge_relative)
                    fallback_kind="none"
                else:
                    # Explicit conservative engineering fallback. Cross-age
                    # correlations are unavailable; episode-max empirical
                    # calibration still does not assume prefix independence.
                    mean=np.zeros(L*m);cov=np.zeros((L*m,L*m))
                    for age in range(L):
                        ar=np.asarray([r[age] for r in train[e] if len(r)>age])
                        mu,block=_moments(ar,ridge_relative) if len(ar)>=min_samples else (pooled_mean,pooled_cov)
                        sl=slice(age*m,(age+1)*m)
                        mean[sl]=mu;cov[sl,sl]=block
                    fallback_kind="block_diagonal_age_moments"
                precision=np.linalg.inv(cov)
                M=np.vstack([H@np.linalg.matrix_power(A,age) for age in range(L)])
                # Stable GLS projection using S^{-1/2}M, avoids squaring a
                # potentially ill-conditioned information matrix before pinv.
                chol=np.linalg.cholesky(cov)
                whitened_M=np.linalg.solve(chol,M)
                U,singular,_=np.linalg.svd(whitened_M,full_matrices=False)
                tol=max(whitened_M.shape)*np.finfo(float).eps*(singular[0] if len(singular) else 0)
                rank=int(np.sum(singular>tol))
                U=U[:,:rank]
                Z=np.linalg.solve(chol.T,U)
                projection=Z@Z.T
                last=slice((L-1)*m,L*m)
                # Strong simple cumulative comparator: average the original
                # residuals, then normalize using their FULL joint covariance.
                # It makes no independence assumption and has no A^age match.
                average=np.tile(np.eye(m),(1,L))/L
                average_cov=average@cov@average.T
                mean_projection=average.T@np.linalg.inv(average_cov)@average
                models[e,L]={"mean":mean,"covariance":cov,"precision":precision,
                    "instant_mean":mean[last].copy(),"instant_precision":np.linalg.inv(cov[last,last]),
                    "gls_projection":(projection+projection.T)/2,"mean_projection":(mean_projection+mean_projection.T)/2,"design_matrix":M,
                    "train_count":count,"fallback":fallback,"fallback_kind":fallback_kind,"gls_rank":rank}

        obj=cls(h,A,max_age,min_samples,ridge_relative,false_alarm_target,models,{}, {}, {})
        for e in h:
            count=len(cal[e]);maxima={metric:np.zeros(count) for metric in METRICS}
            coverage=[]
            for L in range(1,max_age+2):
                ids=np.asarray([idx for idx,r in enumerate(cal[e]) if len(r)>=L],int)
                coverage.append(int(len(ids)))
                if not len(ids):continue
                scores=obj.scores_batch(e,np.asarray([cal[e][idx][:L] for idx in ids]))
                for metric in METRICS:
                    maxima[metric][ids]=np.maximum(maxima[metric][ids],scores[metric])
            # All calibration episodes contribute once. No conditioning on
            # eventual episode length, which is unknown during monitoring.
            obj.thresholds[e]={metric:max(float(np.quantile(v,1-false_alarm_target,method="higher")),1e-12)
                               for metric,v in maxima.items()}
            obj.calibration_episode_counts[e]=count
            obj.calibration_prefix_counts[e]=coverage
            age0=np.asarray([r[:1] for r in cal[e]])
            first_scores=obj.scores_batch(e,age0)["instant"]
            obj.packet_thresholds[e]=max(float(np.quantile(first_scores,1-false_alarm_target,method="higher")),1e-12)
        return obj

    def scores_batch(self, edge, residual_prefixes, normalized=False):
        edge=int(edge);values=np.asarray(residual_prefixes,float)
        if values.ndim!=3 or values.shape[2]!=len(self.H_by_edge[edge]):
            raise ValueError("Expected (batch,current_prefix_length,measurement_dim)")
        L=values.shape[1]
        if not 1<=L<=self.max_age+1:
            raise ValueError("Current age exceeds fitted max_age")
        if not np.isfinite(values).all():raise ValueError("Nonfinite residual")
        fit=self.models[edge,L]
        d=values.reshape(len(values),-1)-fit["mean"]
        result={"instant":_qform(values[:,-1]-fit["instant_mean"],fit["instant_precision"]),
                "joint":_qform(d,fit["precision"]),"gls":_qform(d,fit["gls_projection"]),
                "mean":_qform(d,fit["mean_projection"])}
        if normalized:
            # Older snapshots have no calibrated mean threshold. Preserve
            # their original normalized API rather than inventing one.
            return {name:score/self.thresholds[edge][name] for name,score in result.items() if name in self.thresholds[edge]}
        return result

    def score(self, edge, residual_prefix, normalized=False):
        values=np.asarray(residual_prefix,float)
        if values.ndim==1 and len(self.H_by_edge[int(edge)])==1:values=values[:,None]
        return {name:float(value[0]) for name,value in self.scores_batch(edge,values[None],normalized).items()}

    def normalized_scores_batch(self, edge, residual_prefixes):
        return self.scores_batch(edge,residual_prefixes,normalized=True)

    def scores_prefixes_batch(self, edge, residuals, normalized=False):
        values=np.asarray(residuals,float)
        if values.ndim!=3 or not 1<=values.shape[1]<=self.max_age+1:
            raise ValueError("Expected valid batch of full episodes")
        results=[self.scores_batch(edge,values[:,:L],normalized) for L in range(1,values.shape[1]+1)]
        return {name:np.stack([result[name] for result in results],axis=1) for name in results[0]}

    def episode_maxima(self, episodes, normalized=False):
        result=[]
        for episode in episodes:
            e,r=_parts(episode)
            if r.ndim==1:r=r[:,None]
            scores=self.scores_prefixes_batch(e,r[None],normalized)
            result.append({"edge":e,"length":len(r),**{name:float(v.max()) for name,v in scores.items()}})
        return result

    def summary(self):
        return {"max_age":self.max_age,"min_samples":self.min_samples,
            "ridge_relative":self.ridge_relative,"false_alarm_target":self.false_alarm_target,
            "threshold_scope":"edge-specific maxima over whole observed calibration episodes; no future-length conditioning",
            "thresholds":self.thresholds,"packet_thresholds":self.packet_thresholds,"calibration_episode_counts":self.calibration_episode_counts,
            "calibration_prefix_counts":self.calibration_prefix_counts,
            "prefix_models":[{"edge":e,"length":L,"train_count":fit["train_count"],"fallback":fit["fallback"],
                              "fallback_kind":fit["fallback_kind"],"gls_rank":fit["gls_rank"]} for (e,L),fit in sorted(self.models.items())]}

    def save(self, path):
        arrays={"A":self.A,"metadata":np.asarray(json.dumps(self.summary()))}
        for e,H in self.H_by_edge.items():arrays[f"H_{e}"]=H
        for (e,L),fit in self.models.items():
            for name,value in fit.items():
                if isinstance(value,np.ndarray):arrays[f"p_{e}_{L}_{name}"]=value
        np.savez_compressed(path,**arrays)

    @classmethod
    def load(cls,path):
        with np.load(path,allow_pickle=False) as data:
            meta=json.loads(str(data["metadata"]))
            h={int(k[2:]):data[k].copy() for k in data.files if k.startswith("H_")}
            models={}
            for item in meta["prefix_models"]:
                e,L=item["edge"],item["length"]
                fit={k:v for k,v in item.items() if k not in ("edge","length")}
                prefix=f"p_{e}_{L}_"
                fit.update({k[len(prefix):]:data[k].copy() for k in data.files if k.startswith(prefix)})
                if "mean_projection" not in fit:
                    m=len(h[e]);average=np.tile(np.eye(m),(1,L))/L
                    average_cov=average@fit["covariance"]@average.T
                    fit["mean_projection"]=average.T@np.linalg.inv(average_cov)@average
                models[e,L]=fit
            return cls(h,data["A"].copy(),meta["max_age"],meta["min_samples"],meta["ridge_relative"],
                meta["false_alarm_target"],models,{int(k):v for k,v in meta["thresholds"].items()},
                {int(k):v for k,v in meta["calibration_episode_counts"].items()},
                {int(k):v for k,v in meta["calibration_prefix_counts"].items()},
                {int(k):v for k,v in meta.get("packet_thresholds",{}).items()})
