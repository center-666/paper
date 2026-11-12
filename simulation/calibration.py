"""Normal-data calibration only. Attack data must never enter these functions."""
from __future__ import annotations
from dataclasses import dataclass, asdict
import numpy as np


def quantile(x, p):
    x = np.asarray(x)
    if len(x) == 0:
        raise ValueError("Empty calibration set")
    return float(np.quantile(x, p, method="higher"))


def interval_bins(delta, cfg):
    return np.minimum(np.searchsorted(cfg["interval_upper_bounds"], delta, side="left"), len(cfg["interval_upper_bounds"])-1)


def moments(x, ridge):
    if len(x) < 3:
        raise ValueError("Insufficient normal training samples")
    mu = x.mean(axis=0)
    cov = np.cov(x, rowvar=False, ddof=1)
    scale = max(np.trace(cov) / cov.shape[0], 1e-8)
    cov = cov + ridge * scale * np.eye(cov.shape[0])
    return mu, np.linalg.inv(cov)


def quadratic(x, mu, precision):
    d = x - mu
    return np.einsum("...i,...ij,...j->...", d, precision, d)


def reference_evidence(spatial_ratio,temporal_ratio,previous_spatial_ratio,valid,method,cfg):
    gs=np.maximum(spatial_ratio-1,0);gt=np.maximum(temporal_ratio-1,0)
    if method=="spatial_soft":return gs
    reliability=(previous_spatial_ratio<=1).astype(float) if method=="reference_reset" else np.exp(-np.maximum(previous_spatial_ratio-1,0))
    alpha=cfg["alpha"]
    g=(alpha*gs+(1-alpha)*reliability*gt)/(alpha+(1-alpha)*reliability)
    return np.where(valid,g,gs)


@dataclass
class Calibration:
    mode: str
    space_mu: np.ndarray
    space_precision: np.ndarray
    space_q: np.ndarray
    time_mu: np.ndarray
    time_precision: np.ndarray
    time_q: np.ndarray
    train_counts: np.ndarray
    cal_counts: np.ndarray
    fallback: np.ndarray

    def save(self, path):
        np.savez_compressed(path, **asdict(self))

    @classmethod
    def load(cls, path):
        with np.load(path) as f:
            args = {k: f[k] for k in f.files}
        args["mode"] = str(args["mode"])
        return cls(**args)

    @classmethod
    def fit(cls, train, cal, cfg, mode):
        E, B, n = len(cfg["edges_sender_receiver"]), len(cfg["interval_upper_bounds"]), cfg["n"]
        sm, sp, sq = np.empty((E,n)), np.empty((E,n,n)), np.empty(E)
        tm, tp, tq = np.empty((E,B,n)), np.empty((E,B,n,n)), np.empty((E,B))
        nt, nc, fallback = np.zeros((E,B),int), np.zeros((E,B),int), np.zeros((E,B),bool)
        tb, cb = interval_bins(train["delta"], cfg), interval_bins(cal["delta"], cfg)
        for edge in range(E):
            ti, ci = train["edge"] == edge, cal["edge"] == edge
            sm[edge], sp[edge] = moments(train["space"][ti], cfg["covariance_ridge_relative"])
            sq[edge] = quantile(quadratic(cal["space"][ci], sm[edge], sp[edge]), cfg["marginal_quantile"])
            valid_t, valid_c = ti & train["time_valid"], ci & cal["time_valid"]
            pm, pp = moments(train["temporal"][valid_t], cfg["covariance_ridge_relative"])
            for b in range(B):
                bt, bc = valid_t & (tb == b), valid_c & (cb == b)
                nt[edge,b], nc[edge,b] = bt.sum(), bc.sum()
                fallback[edge,b] = min(nt[edge,b],nc[edge,b]) < cfg["minimum_bin_samples"]
                if mode == "pooled" or fallback[edge,b]:
                    tm[edge,b], tp[edge,b] = pm, pp
                else:
                    tm[edge,b], tp[edge,b] = moments(train["temporal"][bt], cfg["covariance_ridge_relative"])
            # Common tail after using each sample's own scale is a meaningful direct control.
            js = quadratic(cal["temporal"][valid_c], tm[edge,cb[valid_c]], tp[edge,cb[valid_c]])
            common_q = quantile(js, cfg["marginal_quantile"])
            for b in range(B):
                if mode == "interval_tail" and not fallback[edge,b]:
                    tq[edge,b] = quantile(js[cb[valid_c] == b], cfg["marginal_quantile"])
                elif fallback[edge,b]:
                    # Use a genuinely pooled reference for under-supported cells.
                    tq[edge,b] = quantile(quadratic(cal["temporal"][valid_c], pm, pp), cfg["marginal_quantile"])
                else:
                    tq[edge,b] = common_q
        return cls(mode,sm,sp,np.maximum(sq,1e-10),tm,tp,np.maximum(tq,1e-10),nt,nc,fallback)

    def scores(self, space, temporal, delta, valid, cfg):
        E = space.shape[-2]
        edges = np.arange(E)[None,:]
        bins = interval_bins(delta, cfg)
        js = quadratic(space, self.space_mu, self.space_precision)
        jt = quadratic(temporal, self.time_mu[edges,bins], self.time_precision[edges,bins])
        gs = np.maximum(js / self.space_q - 1, 0)
        gt = np.maximum(jt / self.time_q[edges,bins] - 1, 0)
        g = np.where(valid, cfg["alpha"]*gs + (1-cfg["alpha"])*gt, gs)
        return g, js / self.space_q, jt / self.time_q[edges,bins]

    def observation_scores(self, obs, cfg):
        e, b = obs["edge"], interval_bins(obs["delta"], cfg)
        js = quadratic(obs["space"], self.space_mu[e], self.space_precision[e]) / self.space_q[e]
        jt = quadratic(obs["temporal"], self.time_mu[e,b], self.time_precision[e,b]) / self.time_q[e,b]
        gs, gt = np.maximum(js-1,0), np.maximum(jt-1,0)
        combined = np.where(obs["time_valid"], cfg["alpha"]*gs+(1-cfg["alpha"])*gt, gs)
        return combined, js, jt


def fit_control(method, normal_observations, calibration, cfg):
    """Controls are fit on independent NORMAL validation trajectories only."""
    p = cfg["normal_low_weight_target"]
    if method == "zhou_random":
        D = normal_observations["distance_squared"]
        lo, hi = 1e-8, max(float(D.max()),1.0)*1e4
        for _ in range(70):
            nu = (lo+hi)/2
            rejection = np.mean(-np.expm1(-D/nu))
            if rejection > p: lo = nu
            else: hi = nu
        return (lo+hi)/2
    if method == "spatial_hard":
        _, spatial, _ = calibration.observation_scores(normal_observations,cfg)
        return quantile(spatial,1-p)
    if method in {"spatial_soft","reference_reset","reference_soft"}:
        _,js,jt=calibration.observation_scores(normal_observations,cfg)
        e=normal_observations["edge"]
        previous=quadratic(normal_observations["previous_space"],calibration.space_mu[e],calibration.space_precision[e])/calibration.space_q[e]
        combined=reference_evidence(js,jt,previous,normal_observations["time_valid"],method,cfg)
        q=quantile(combined,1-p)
        return -np.log(cfg["low_weight_threshold"])/q if q>1e-8 else 1.0
    if method in {"pooled","interval_scale","interval_tail","tail_shared_scale"}:
        combined, _, _ = calibration.observation_scores(normal_observations,cfg)
        q = quantile(combined,1-p)
        if q < 1e-8:
            # Target unattainable with this family; recorded by validation, not hidden.
            return 1.0
        return -np.log(cfg["low_weight_threshold"])/q
    return 1.0
