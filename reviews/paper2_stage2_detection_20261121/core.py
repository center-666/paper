"""Event-only detectors and translation-invariant scalar estimation simulator.

The detector takes only the current trusted bit and probabilities fixed before
the fresh phase. Simulation truth and the true attack schedule are not inputs.
"""
from __future__ import annotations

import numpy as np
from scipy.special import ndtr, logsumexp

NAMES = ("D0_Azuma", "D1_fixed_LR", "D2_strength_mixture",
         "D3_start_strength_mixture", "D4_finite_horizon_CUSUM")


def quant(x, delta, phase):
    return phase + 2 * delta * np.floor((x - phase + delta) / (2 * delta))


def silence(Ppost, bias, model):
    """Next-event probability marginalized over the fresh full-period phase."""
    A, Q, R, Z, delta = (model[k] for k in ("A", "Q", "R", "Z", "delta"))
    V = 1 / Z + A * A * Ppost + Q + R
    root = np.sqrt(V)
    displacement = A * bias
    return np.sqrt(2 * np.pi / Z) / (2 * delta) * (
        ndtr((delta - displacement) / root) -
        ndtr((-delta - displacement) / root))


def bernoulli_kl(p, q):
    return p * np.log(p / q) + (1 - p) * np.log1p((q - p) / (1 - q))


def log_factor(Y, q, nu):
    # log1p retains small probability gaps and returns exactly zero for q=nu.
    return np.where(Y, np.log1p((q - nu) / nu),
                    np.log1p((nu - q) / (1 - nu)))


def probabilities(Ppost, K, sent, model, strengths):
    nu = silence(Ppost, 0., model)
    candidate = silence(Ppost[None, :], -np.asarray(strengths)[:, None] * K[None, :], model)
    q = np.where(sent[None, :], candidate, nu[None, :])
    return nu, q


class Detectors:
    def __init__(self, count, strengths, weights, alpha, horizon):
        self.strengths = tuple(strengths)
        self.log_weights = np.log(np.asarray(weights))[:, None]
        self.fixed_index = self.strengths.index(0.1)
        self.alpha, self.horizon = alpha, horizon
        self.h = np.sqrt(horizon / 2 * np.log(1 / alpha))
        self.score = np.zeros(count)
        self.log_lr = np.zeros((len(strengths), count))
        self.log_starts = np.full_like(self.log_lr, -np.inf)
        self.log_cusum = np.zeros_like(self.log_lr)
        self.tau = np.full((len(NAMES), count), -1, dtype=np.int32)
        self.last_statistics = None

    def step(self, n, Y, nu, q):
        if not (np.all(nu > 0) and np.all(nu < 1)
                and np.all(q > 0) and np.all(q <= nu[None, :] + 1e-14)):
            raise AssertionError("Invalid predictable probabilities")
        ell = log_factor(Y[None, :], q, nu[None, :])
        self.score += nu - Y
        self.log_lr += ell
        log_w = -np.log(float(n)) - np.log(float(n + 1))
        self.log_starts = np.logaddexp(self.log_starts, log_w) + ell
        self.log_cusum = np.maximum(self.log_cusum, 0) + ell
        stats = np.stack((
            self.score / self.h,
            self.log_lr[self.fixed_index] / np.log(1 / self.alpha),
            logsumexp(self.log_lr + self.log_weights, axis=0) / np.log(1 / self.alpha),
            np.logaddexp(logsumexp(self.log_starts + self.log_weights, axis=0),
                         -np.log(float(n + 1))) / np.log(1 / self.alpha),
            (logsumexp(self.log_cusum + self.log_weights, axis=0) -
             np.log(float(self.horizon))) / np.log(1 / self.alpha),
        ))
        alarm = stats >= 1
        if n > self.horizon:
            alarm[[0, 4], :] = False
        newly = (self.tau < 0) & alarm
        self.tau[newly] = n
        self.last_statistics = stats


def update_error(error, P, center_residual, noise, sent, action, model):
    R, Z = model["R"], model["Z"]
    Ri = np.where(sent, R, R + 1 / Z)
    K = P / (P + Ri)
    posterior_error = np.where(sent, (1 - K) * error - K * (noise + action),
                               error - K * center_residual)
    return posterior_error, P * (1 - K), K
