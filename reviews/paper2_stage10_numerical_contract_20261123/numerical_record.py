"""Numerical monitor enclosures on a common exact-valued observation record.

The arithmetic contract accepts exact decimal/rational observations and logged
binary64 monitor states. The likelihood cache describes the physical candidate
under the exact nominal monitor. Its directional target is b*H. Effective output
risk additionally uses the monitor error enclosure returned by this module.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from fractions import Fraction as F
import math
from pathlib import Path
import sys

STAGE6 = Path(__file__).resolve().parents[1] / "paper2_stage6_vector_correction_20261122"
sys.path.insert(0, str(STAGE6))

from exact_linear import add, matmul, matrix, spd2, transpose, update
from vector_record import VectorRecord, dot, interval_fraction, I
from interval_arithmetic import log_trigger


def exact_value(value):
    """Interpret a declared exact scalar without implicit binary conversion."""
    if isinstance(value, bool) or isinstance(value, float):
        raise TypeError("Declare exact observations with Fraction, Decimal, int, or text")
    if isinstance(value, (F, Decimal, int, str)):
        return F(value)
    raise TypeError("Unsupported exact observation type")


def binary64_value(value):
    """Return the exact real value of a finite binary64 representation."""
    if isinstance(value, bool):
        raise TypeError("Boolean state components are invalid")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("A finite binary64 component is required")
    return F.from_float(number)


def binary64_rounding_cell(value):
    """Enclose real inputs rounding to value under binary64 nearest-even."""
    number = float(value)
    point = binary64_value(number)
    previous = math.nextafter(number, -math.inf)
    following = math.nextafter(number, math.inf)
    if math.isfinite(previous):
        lower = (binary64_value(previous) + point) / 2
    else:
        lower = point - (binary64_value(following) - point) / 2
    if math.isfinite(following):
        upper = (point + binary64_value(following)) / 2
    else:
        upper = point + (point - binary64_value(previous)) / 2
    return lower, upper


def finite_decimal(value):
    """Convert a finite-decimal rational exactly, including subnormals."""
    value = F(value)
    denominator = value.denominator
    powers = []
    for factor in (2, 5):
        count = 0
        while denominator % factor == 0:
            denominator //= factor
            count += 1
        powers.append(count)
    if denominator != 1:
        raise ValueError("Selection zeros require exact finite-decimal input differences")
    places = max(powers)
    numerator = value.numerator * 2 ** (places - powers[0]) * 5 ** (places - powers[1])
    return Decimal(str(numerator) + "e-" + str(places))


def exact_matvec(coefficients, vector):
    return tuple(sum((a * b for a, b in zip(row, vector)), F(0)) for row in coefficients)


def interval_matvec(coefficients, vector):
    return tuple(dot([interval_fraction(a) for a in row], vector) for row in coefficients)


@dataclass(frozen=True)
class MonitorFrame:
    time: int
    sent: bool
    payload: F | None
    center: F
    actual_prior: tuple[F, ...]
    actual_posterior: tuple[F, ...]
    prior_error: tuple[I, ...]
    posterior_error: tuple[I, ...]
    prediction_residual: tuple[F, ...]
    update_residual: tuple[F, ...]
    nominal_innovation: I | None
    nominal_center_residual: I
    actual_innovation: F | None
    actual_center_residual: F
    gain: tuple[F, ...]
    transition: tuple[tuple[F, ...], ...]
    prior_covariance: tuple[tuple[F, ...], ...]
    next_covariance: tuple[tuple[F, ...], ...]

    @property
    def nominal_prior(self):
        return tuple(interval_fraction(value) - error
                     for value, error in zip(self.actual_prior, self.prior_error))

    @property
    def nominal_posterior(self):
        return tuple(interval_fraction(value) - error
                     for value, error in zip(self.actual_posterior, self.posterior_error))


class MonitorEnclosure:
    """Audit logged prediction/update results with exact local residuals."""

    def __init__(self, model, initial_nominal_prior=None):
        self.A, self.C, self.Q, self.P = (
            matrix(model[key]) for key in ("A", "C", "Q", "P0_prior"))
        self.R, self.Z = F(model["R"]), F(model["Z"])
        self.dimension = len(self.A)
        initial = initial_nominal_prior if initial_nominal_prior is not None else [0] * self.dimension
        self.initial_prior = tuple(exact_value(x) for x in initial)
        if len(self.initial_prior) != self.dimension:
            raise ValueError("Initial mean dimension differs from the model")
        self.time = -1
        self.posterior_error = tuple(I.exact(0) for _ in self.A)
        self.actual_posterior = None

    def _prepare(self, sent, payload, center, actual_prior, actual_posterior):
        if not isinstance(sent, bool) or sent != (payload is not None):
            raise ValueError("Trusted event and payload availability differ")
        received = exact_value(payload) if sent else None
        center = exact_value(center)
        prior = tuple(binary64_value(x) for x in actual_prior)
        posterior = tuple(binary64_value(x) for x in actual_posterior)
        if len(prior) != self.dimension or len(posterior) != self.dimension:
            raise ValueError("Monitor state dimension differs from the model")
        if self.time < 0:
            prediction_residual = tuple(a - b for a, b in zip(prior, self.initial_prior))
            prior_error = tuple(interval_fraction(x) for x in prediction_residual)
        else:
            predicted_exact = exact_matvec(self.A, self.actual_posterior)
            prediction_residual = tuple(a - b for a, b in zip(prior, predicted_exact))
            propagated = interval_matvec(self.A, self.posterior_error)
            prior_error = tuple(a + interval_fraction(b) for a, b in zip(propagated, prediction_residual))
        posterior_covariance, gain_matrix, transition = update(
            self.P, self.C, self.R + (0 if sent else 1 / self.Z))
        gain = tuple(row[0] for row in gain_matrix)
        observation = received if sent else center
        exact_update = exact_matvec(transition, prior)
        update_residual = tuple(a - (b + k * observation)
                                for a, b, k in zip(posterior, exact_update, gain))
        propagated = interval_matvec(transition, prior_error)
        posterior_error = tuple(a + interval_fraction(b) for a, b in zip(propagated, update_residual))
        measured_prior = exact_matvec(self.C, prior)[0]
        shift = interval_matvec(self.C, prior_error)[0]
        actual_innovation = received - measured_prior if sent else None
        actual_residual = center - measured_prior
        next_covariance = add(matmul(matmul(self.A, posterior_covariance), transpose(self.A)), self.Q)
        return MonitorFrame(
            time=self.time + 1, sent=sent, payload=received, center=center,
            actual_prior=prior, actual_posterior=posterior,
            prior_error=prior_error, posterior_error=posterior_error,
            prediction_residual=prediction_residual, update_residual=update_residual,
            nominal_innovation=interval_fraction(actual_innovation) + shift if sent else None,
            nominal_center_residual=interval_fraction(actual_residual) + shift,
            actual_innovation=actual_innovation, actual_center_residual=actual_residual,
            gain=gain, transition=tuple(tuple(row) for row in transition),
            prior_covariance=tuple(tuple(row) for row in self.P),
            next_covariance=tuple(tuple(row) for row in next_covariance))

    def _commit(self, frame):
        self.time = frame.time
        self.posterior_error = frame.posterior_error
        self.actual_posterior = frame.actual_posterior
        self.P = [list(row) for row in frame.next_covariance]

    def append(self, sent, payload, center, *, prior, posterior):
        frame = self._prepare(sent, payload, center, prior, posterior)
        self._commit(frame)
        return frame


class NumericalLikelihoodRecord:
    """Build physical likelihood intervals in exact nominal coordinates."""

    def __init__(self, model, initial_nominal_prior=None):
        if (len(model["A"]) != 2 or any(len(row) != 2 for row in model["A"])
                or len(model["C"]) != 1 or len(model["C"][0]) != 2):
            raise ValueError("The inherited likelihood cache is scoped to V2")
        if F(model["R"]) <= 0 or F(model["Z"]) <= 0:
            raise ValueError("Positive measurement noise and trigger precision are required")
        if F(model["quantization_half_width"]) <= 0:
            raise ValueError("A positive quantization half-width is required")
        self.monitor = MonitorEnclosure(model, initial_nominal_prior)
        self.core = VectorRecord(model)

    def append(self, sent, payload, center, *, prior, posterior):
        frame = self.monitor._prepare(sent, payload, center, prior, posterior)
        core = self.core
        if abs(frame.actual_center_residual) > F(core.model["quantization_half_width"]):
            raise ValueError("Center violates the quantization contract")
        if core.P != [list(row) for row in frame.prior_covariance]:
            raise ArithmeticError("Monitor and likelihood covariance states differ")
        variance = matmul(matmul(core.C, core.P), transpose(core.C))[0][0] + core.R
        S = interval_fraction(variance)
        V = S + interval_fraction(1 / core.Z)
        u, r = frame.nominal_innovation, frame.nominal_center_residual
        gain = [interval_fraction(x) for x in frame.gain]
        transition = [[interval_fraction(x) for x in row] for row in frame.transition]
        A = [[interval_fraction(x) for x in row] for row in core.A]
        C = [interval_fraction(x) for x in core.C[0]]
        mark = None
        denominator = None
        if sent:
            zero = finite_decimal(frame.payload - frame.center)
            denominator = log_trigger(I.exact(zero), core.model["Z"])
            if not denominator.lo.is_finite():
                raise ArithmeticError("Healthy density at the input cannot be resolved")
            mark = (zero, denominator)
        # Construct complete next states before committing either cache.
        candidates = []
        new_candidate = {"H": [I.exact(0), I.exact(0)],
                         "a": I.exact(0), "B": I.exact(0), "sends": 0}
        for old in [*core.candidates, new_candidate]:
            predicted = [dot(row, old["H"]) for row in A]
            eta = dot(C, predicted)
            if sent:
                coefficient = 1 - eta
                linear = old["a"] + coefficient * u / S
                quadratic = old["B"] + coefficient.square() / S
            else:
                linear = old["a"] - r * eta / V
                quadratic = old["B"] + eta.square() / V
            response = [dot(row, predicted) + (gain[j] if sent else 0)
                        for j, row in enumerate(transition)]
            candidates.append({"H": response, "a": linear, "B": quadratic,
                               "sends": old["sends"] + int(sent)})
        warm = []
        for old in core.warm:
            d, b = dot(C, old["d"]), old["b"]
            if sent:
                shift = b + d
                # The exact trigger difference is independent of monitor rounding.
                logfactor = ((u * shift - shift.square() / 2) / S +
                             log_trigger(I.exact(mark[0]) - b, core.model["Z"]) - denominator)
            else:
                logfactor = (r * d - d.square() / 2) / V
            weight = I.exact(1) / ((core.n + 1) * (core.n + 2))
            mass = (old["mass"] + weight) * logfactor.exp()
            post = [dot(row, old["d"]) - (gain[j] * b if sent else 0)
                    for j, row in enumerate(transition)]
            warm.append({"d": [dot(row, post) for row in A], "mass": mass, "b": b})
        reference = sum((row["mass"] / 3 for row in warm), I.exact(1) / (core.n + 2))
        self.monitor._commit(frame)
        core.candidates, core.warm, core.ref = candidates, warm, reference
        core.marks.append(mark)
        core.P = [list(row) for row in frame.next_covariance]
        core.n += 1
        core.stats["candidate_updates"] += len(candidates)
        return frame


def effective_risk_lower(frame, response_boxes, amplitude_intervals, published, weight, cap):
    """Bound effective-output risk for supplied parameter outer intervals.

    The caller supplies the coverage justification for the parameter intervals.
    All arithmetic below includes the current numerical monitor error.
    """
    emitted = tuple(binary64_value(x) for x in published)
    if len(emitted) != len(frame.actual_posterior):
        raise ValueError("Published state dimension differs")
    action = tuple(a - b for a, b in zip(frame.actual_posterior, emitted))
    if sum(map(abs, action)) > exact_value(cap):
        raise ValueError("Effective action exceeds the declared cap")
    W = matrix(weight)
    if (len(W) != len(action) or any(len(row) != len(action) for row in W)
            or len(action) != 2 or not spd2(W)):
        raise ValueError("The output audit requires a positive definite two-state weight")
    weighted_action = exact_matvec(W, action)
    norm = sum((a * b for a, b in zip(action, weighted_action)), F(0))
    support = None
    for onset, intervals in amplitude_intervals.items():
        response = response_boxes[onset]
        if len(response) != len(action):
            raise ValueError("Pollution response dimension differs")
        for lo, hi in intervals:
            lo, hi = exact_value(lo), exact_value(hi)
            if lo < 0 or hi < lo:
                raise ValueError("Invalid amplitude interval")
            amplitude = I(interval_fraction(lo).lo, interval_fraction(hi).hi)
            pollution = [error + coefficient * amplitude
                         for error, coefficient in zip(frame.posterior_error, response)]
            value = dot(pollution, [interval_fraction(x) for x in weighted_action]).lo
            support = value if support is None else min(support, value)
    if support is None:
        raise ValueError("A nonempty parameter outer set is required")
    return {"effective_action": action, "risk_lower": 2 * F(support) - norm,
            "action_energy": norm}
