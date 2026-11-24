"""Output-only TRSR on V2 single-channel logs. No state truth enters these functions."""
from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class Packet:
    center: float
    payload: float | None  # None = trusted silence


@dataclass(frozen=True)
class State:
    mean: np.ndarray
    covariance: np.ndarray


class Filter:
    def __init__(self, model):
        self.A = np.array(model["A"], dtype=float)
        self.C = np.array(model["C"], dtype=float)[0]
        self.Q = np.array(model["Q"], dtype=float)
        self.R = float(model["R"])
        self.Z = float(model["Z"])
        self.W = np.array(model["W"], dtype=float)
        self.initial = State(np.zeros(len(self.C)), np.array(model["P0"], dtype=float))

    def predict(self, post):
        return State(self.A @ post.mean, self.A @ post.covariance @ self.A.T + self.Q)

    def update(self, prior, packet, erase=False):
        sent = packet.payload is not None
        if sent and erase:
            return prior, None
        observation = packet.payload if sent else packet.center
        pc = prior.covariance @ self.C
        noise = self.R if sent else self.R + 1/self.Z
        gain = pc / (self.C @ pc + noise)
        mean = prior.mean + gain * (observation - self.C @ prior.mean)
        return State(mean, prior.covariance - np.outer(gain, pc)), gain


def replay(model, log, checkpoint_time, next_prior, start, end):
    """Use the saved prior for checkpoint_time+1; return the prior at len(log)."""
    if not -1 <= checkpoint_time < start < end or len(log) < start:
        raise ValueError("Checkpoint must precede a nonempty suspect window")
    prior = next_prior
    for t in range(checkpoint_time + 1, len(log)):
        post, _ = model.update(prior, log[t], erase=start <= t < end)
        prior = model.predict(post)
    return prior


def recovery_weight(h, directions, W):
    """Return (weight, worst gain); directions enclose the possible deviations."""
    q = h @ W @ h
    if q <= 0 or not np.isfinite(q) or len(directions) == 0:
        return 0.0, 0.0
    supports = np.asarray(directions) @ (W @ h)
    if not np.all(np.isfinite(supports)):
        return 0.0, 0.0
    g = supports.min()
    weight = float(np.clip(g/q, 0, 1))
    return weight, float(weight*(2*g - weight*q))
