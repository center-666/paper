"""Receiver operations on batched V2 records. Axis 0 indexes independent runs."""
import numpy as np


class V2Filter:
    def __init__(self, model):
        self.A = np.asarray(model["A"], dtype=float)
        self.C = np.asarray(model["C"], dtype=float)[0]
        self.Q = np.asarray(model["Q"], dtype=float)
        self.R = float(model["R"])
        self.Z = float(model["Z"])
        self.P0 = np.asarray(model["P0_prior"], dtype=float)
        self.W = np.asarray(model["W"], dtype=float)

    def initial(self, batch_size):
        return np.zeros((batch_size, 2)), np.tile(self.P0, (batch_size, 1, 1))

    def predict(self, mean, cov):
        return mean @ self.A.T, self.A @ cov @ self.A.T + self.Q

    def update(self, mean, cov, center, payload, erase=False):
        """NaN encodes a silent bit. An erased send leaves the prior unchanged."""
        sent = ~np.isnan(payload)
        pc = cov @ self.C
        tag = pc @ self.C + self.R + (~sent)/self.Z
        gain = pc/tag[:, None]
        gain = np.where((sent & erase)[:, None], 0., gain)
        observation = np.where(sent, payload, center)
        post = mean + gain*(observation - mean @ self.C)[:, None]
        new_cov = cov - gain[:, :, None]*pc[:, None, :]
        return post, new_cov, gain

    def response(self, previous_post_H, gain, sent, active):
        prior_H = previous_post_H @ self.A.T
        return prior_H + gain*((sent & active).astype(float) - prior_H @ self.C)[:, None]

    def replay(self, checkpoint_time, mean, cov, centers, payloads, start, end):
        """Read only the supplied log prefix; return the prior for its next tick."""
        if centers.shape != payloads.shape or not -1 <= checkpoint_time < start <= end:
            raise ValueError("Invalid checkpoint, window or log")
        if checkpoint_time >= len(centers):
            raise ValueError("Checkpoint is outside log prefix")
        if checkpoint_time >= 0:
            mean, cov = self.predict(mean, cov)
        for t in range(checkpoint_time+1, len(centers)):
            post, pcov, _ = self.update(mean, cov, centers[t], payloads[t], start <= t < end)
            mean, cov = self.predict(post, pcov)
        return mean, cov


def decide(monitor, recovery, directions, W):
    """Compare actual representable actions under the supplied deviation vectors."""
    h = monitor - recovery
    q = np.einsum("ni,ij,nj->n", h, W, h)
    n = len(monitor)
    directions = np.asarray(directions)
    if directions.ndim != 3 or directions.shape[0] != n or directions.shape[2] != h.shape[1]:
        raise ValueError("Expected one candidate vector set per record")
    if directions.shape[1] == 0:
        return monitor.copy(), np.zeros(n), np.zeros(n), np.ones(n, bool)
    g = np.einsum("ni,ij,nkj->nk", h, W, directions).min(axis=1)
    valid = np.isfinite(g) & np.isfinite(q) & (q > 0)
    weight = np.clip(np.divide(g, q, out=np.zeros(n), where=valid), 0., 1.)
    published = np.where(weight[:,None] == 0, monitor, monitor-weight[:,None]*h)
    action = monitor - published
    gain = (2*np.einsum("ni,ij,nkj->nk", action, W, directions).min(axis=1)
            - np.einsum("ni,ij,nj->n", action, W, action))
    fallback = ~np.isfinite(q) | ~np.isfinite(g) | ~np.isfinite(gain) | (gain < 0)
    return (np.where(fallback[:,None], monitor, published), np.where(fallback,0.,weight),
            np.where(fallback,0.,gain), fallback)
