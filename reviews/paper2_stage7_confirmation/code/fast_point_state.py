"""Vectorized finite-grid point likelihood for development-only calibration."""
from __future__ import annotations
import math
from fractions import Fraction as F
import numpy as np

from exact_linear import add, asfloat, matmul, matrix, transpose, update
from common import _log_trigger_float


class FastPointState:
    def __init__(self, model, grid):
        self.model = model
        self.grid = [float(value) for value in grid]
        self.A = np.asarray(model["A"], dtype=float)
        self.C = np.asarray(model["C"], dtype=float).reshape(-1)
        self.Q = matrix(model["Q"])
        self.P = matrix(model["P0_prior"])
        self.R = F(model["R"])
        self.Z = float(model["Z"])
        self.H = np.empty((0, 2), dtype=float)
        self.a = np.empty(0, dtype=float)
        self.B = np.empty(0, dtype=float)
        self.selection = {value: np.empty(0, dtype=float) for value in self.grid}

    def append(self, sent, payload, center_offset):
        measurement_noise = F(0) if sent else F(1) / F(self.model["Z"])
        posterior, gain, transition = update(self.P, matrix(self.model["C"]), self.R + measurement_noise)
        prior_covariance = matmul(matmul(matrix(self.model["C"]), self.P), transpose(matrix(self.model["C"])))[0][0] + self.R
        S = float(prior_covariance)
        V = S + 1.0 / self.Z
        prior_H = self.H @ self.A.T
        eta = prior_H @ self.C

        if sent:
            residual = float(payload) - float(center_offset)
            coefficient = 1.0 - eta
            next_a = self.a + coefficient * float(payload) / S
            next_B = self.B + coefficient * coefficient / S
            next_H = prior_H @ np.asarray(asfloat(transition), float).T + np.asarray(asfloat(gain), float).ravel()
            selection_increments = {
                b: _log_trigger_float(residual - b, self.Z) - _log_trigger_float(residual, self.Z)
                for b in self.grid
            }
        else:
            next_a = self.a - float(center_offset) * eta / V
            next_B = self.B + eta * eta / V
            next_H = prior_H @ np.asarray(asfloat(transition), float).T
            selection_increments = {b: 0.0 for b in self.grid}

        zero_H = np.zeros((1, 2), dtype=float)
        new_H = np.asarray(asfloat(gain), float).ravel() if sent else np.zeros(2, dtype=float)
        self.H = np.vstack((next_H, new_H))
        if sent:
            new_a = float(payload) / S
            new_B = 1.0 / S
        else:
            new_a = 0.0
            new_B = 0.0
        self.a = np.append(next_a, new_a)
        self.B = np.append(next_B, new_B)
        for b in self.grid:
            old = self.selection[b] + selection_increments[b]
            self.selection[b] = np.append(old, selection_increments[b])

        A_exact = matrix(self.model["A"])
        self.P = add(matmul(matmul(A_exact, posterior), transpose(A_exact)), self.Q)
        return np.asarray(asfloat(gain), float).ravel(), np.asarray(asfloat(transition), float)

    def proposal(self):
        best_score = 0.0
        best_index = None
        best_b = 0.0
        for b in self.grid:
            scores = self.a * b - 0.5 * self.B * b * b + self.selection[b]
            if scores.size == 0:
                continue
            index = int(np.argmax(scores))
            score = float(scores[index])
            if score > best_score:
                best_score, best_index, best_b = score, index, b
        if best_index is None:
            return None, np.zeros(2), 0.0, best_score
        point = best_b * self.H[best_index]
        scale = float(np.max(np.abs(point)))
        if scale < 1e-14:
            return None, point, best_b, best_score
        direction = tuple(F(format(value / scale, ".6f")) for value in point)
        if direction == (0, 0):
            return None, point, best_b, best_score
        return direction, point, best_b, best_score
