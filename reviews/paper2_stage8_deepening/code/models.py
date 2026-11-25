"""Dimension-generic exact linear filtering primitives for Stage 8."""
from __future__ import annotations

import json
from dataclasses import dataclass
from fractions import Fraction as F
from pathlib import Path


Number = F


def matrix(rows):
    return [[F(value) for value in row] for row in rows]


def vector(values):
    return [F(value) for value in values]


def transpose(a):
    return [list(row) for row in zip(*a)]


def matmul(a, b):
    b_t = transpose(b)
    return [[sum((x * y for x, y in zip(row, col)), F(0)) for col in b_t] for row in a]


def matvec(a, x):
    return [sum((coefficient * value for coefficient, value in zip(row, x)), F(0)) for row in a]


def add(a, b):
    return [[x + y for x, y in zip(row_a, row_b)] for row_a, row_b in zip(a, b)]


def sub(a, b):
    return [[x - y for x, y in zip(row_a, row_b)] for row_a, row_b in zip(a, b)]


def eye(n):
    return [[F(i == j) for j in range(n)] for i in range(n)]


def inverse(a):
    n = len(a)
    rows = [list(row) + identity_row for row, identity_row in zip(a, eye(n))]
    for pivot_index in range(n):
        pivot = next((i for i in range(pivot_index, n) if rows[i][pivot_index]), None)
        if pivot is None:
            raise ValueError("Singular matrix")
        rows[pivot_index], rows[pivot] = rows[pivot], rows[pivot_index]
        divisor = rows[pivot_index][pivot_index]
        rows[pivot_index] = [value / divisor for value in rows[pivot_index]]
        for row_index in range(n):
            if row_index == pivot_index:
                continue
            factor = rows[row_index][pivot_index]
            rows[row_index] = [x - factor * y for x, y in zip(rows[row_index], rows[pivot_index])]
    return [row[n:] for row in rows]


def identity_row(n):
    return [F(i == 0) for i in range(n)]


@dataclass(frozen=True)
class Plant:
    name: str
    A: list[list[F]]
    B: list[list[F]]
    C: list[list[F]]
    Q: list[list[F]]
    R: list[list[F]]
    Z: F
    P0: list[list[F]]
    W: list[list[F]]
    attack_channel: int
    sample_period: F

    @property
    def n(self):
        return len(self.A)

    @property
    def measurement_dimension(self):
        return len(self.C)

    @property
    def input_dimension(self):
        return len(self.B[0]) if self.B else 0


def load_plants(path: str | Path) -> dict[str, Plant]:
    raw = json.loads(Path(path).read_text(encoding="utf8"))
    plants = {}
    for name, item in raw["plants"].items():
        plant = Plant(name=name, A=matrix(item["A"]), B=matrix(item["B"]),
                      C=matrix(item["C"]), Q=matrix(item["Q"]), R=matrix(item["R"]),
                      Z=F(item["Z"]),
                      P0=matrix(item["P0"]), W=matrix(item["W"]),
                      attack_channel=int(item["attack_channel"]),
                      sample_period=F(item["sample_period"]))
        if len(plant.B) != plant.n:
            raise ValueError(f"{name}: B row dimension does not match A")
        if len(plant.C[0]) != plant.n:
            raise ValueError(f"{name}: C column dimension does not match A")
        if plant.measurement_dimension != 1:
            raise ValueError(f"{name}: Stage 8 currently uses a scalar trusted event channel")
        if len(plant.R) != plant.measurement_dimension:
            raise ValueError(f"{name}: R dimension does not match C")
        plants[name] = plant
    return plants


def kalman_gain(plant: Plant, covariance, silent: bool):
    measurement_covariance = plant.R
    if silent:
        measurement_covariance = add(plant.R, [[F(1) / plant.Z]])
    cp = matmul(plant.C, covariance)
    innovation_covariance = add(matmul(cp, transpose(plant.C)), measurement_covariance)
    gain = matmul(matmul(covariance, transpose(plant.C)), inverse(innovation_covariance))
    transition = sub(eye(plant.n), matmul(gain, plant.C))
    posterior = matmul(transition, covariance)
    return posterior, gain, transition


def filter_step(plant: Plant, covariance, prior, observation, center, silent: bool, control):
    """Perform one update and prediction with a known control input."""
    posterior_covariance, gain, transition = kalman_gain(plant, covariance, silent)
    reference = center if silent else observation
    innovation = vector(reference) if isinstance(reference, (list, tuple)) else [F(reference)]
    innovation = [x - y for x, y in zip(innovation, matvec(plant.C, prior))]
    posterior = add_vectors(prior, matvec(gain, innovation))
    predicted = add_vectors(matvec(plant.A, posterior), matvec(plant.B, control))
    predicted_covariance = add(matmul(matmul(plant.A, posterior_covariance), transpose(plant.A)), plant.Q)
    return predicted_covariance, predicted, gain, transition


def add_vectors(a, b):
    return [x + y for x, y in zip(a, b)]
