"""Provenance-bound cumulative likelihood and directional pollution envelope.

This implementation is scoped to the Stage 6 V2 two-state model and the
Stage 7 fixed-onset, fixed-nonnegative-amplitude attack family. It keeps an
outer union of amplitude intervals for each onset. Likelihood upper bounds are
advanced by one observation at a time and are tightened with the exact cached
record when a branch remains unresolved.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal as D, localcontext
from fractions import Fraction as F
import hashlib
import json
from pathlib import Path
import sys

STAGE6 = Path(__file__).resolve().parents[1] / "paper2_stage6_vector_correction_20261122"
STAGE4 = Path(__file__).resolve().parents[1] / "paper2_stage4_certified_correction_20261122"
STAGE7 = Path(__file__).resolve().parents[1] / "paper2_stage7_fixed_amplitude_20261122"
for path in (STAGE6, STAGE4, STAGE7):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from interval_arithmetic import Interval as I, PRECISION, log_trigger
from vector_record import VectorRecord, interval_fraction
from projection import inner


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _json_hash(value) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return _sha256(payload.encode("utf8"))


def _strict_fraction(value, name: str) -> F:
    if isinstance(value, float):
        raise TypeError(f"{name} cannot be supplied as a binary float")
    if isinstance(value, F):
        return value
    if isinstance(value, (D, int, str)):
        return F(str(value))
    raise TypeError(f"Unsupported exact value for {name}")


def _canonical_observation(sent: bool, u, r) -> dict:
    if not isinstance(sent, bool):
        raise TypeError("The trusted event must be a bool")
    if not sent and u is not None:
        raise ValueError("Silent observations cannot carry a payload")
    if sent and u is None:
        raise ValueError("Sent observations require the received payload")

    def decimal_text(value, label):
        if isinstance(value, (float, F, bool)):
            raise TypeError(f"{label} must be supplied as exact decimal text")
        if not isinstance(value, (str, D, int)):
            raise TypeError(f"Unsupported {label} type {type(value).__name__}")
        parsed = D(str(value))
        if not parsed.is_finite():
            raise ValueError(f"{label} must be finite")
        return str(parsed)

    payload = decimal_text(u, "payload") if sent else None
    center = decimal_text(r, "center offset")
    return {"sent": sent, "payload": payload, "center_offset": center}


@dataclass(frozen=True)
class CertifiedCertificate:
    certificate_id: str
    model_hash: str
    confidence_process_hash: str
    implementation_hash: str
    epsilon: str
    amplitude_cap: str
    observation_prefix_hash: str
    time: int
    direction: tuple[F, ...]
    support: F
    likelihood_source: str
    source_envelope_id: str | None
    parent_certificate_ids: tuple[str, ...]


@dataclass(frozen=True)
class LikelihoodNode:
    onset: int
    lower: D
    upper: D
    loglik_upper: D


class EvidenceRecord:
    """Hash-chained observations paired with the exact Stage 6 likelihood."""

    def __init__(self, model: dict, epsilon=".001", amplitude_cap=".25"):
        self.model = json.loads(json.dumps(model, sort_keys=True))
        self.epsilon = str(epsilon)
        self.amplitude_cap = str(amplitude_cap)
        self.core = VectorRecord(self.model)
        self.model_hash = _json_hash(self.model)
        source_paths = {
            "likelihood": STAGE6 / "vector_record.py",
            "intervals": STAGE4 / "interval_arithmetic.py",
            "linear_algebra": STAGE6 / "exact_linear.py",
            "fixed_amplitude": STAGE7 / "fixed_amplitude.py",
            "direction_cache": STAGE7 / "direction_cache_corrected.py",
            "cumulative_envelope": Path(__file__).resolve(),
        }
        self.implementation_sources = {name: _sha256(path.read_bytes())
                                       for name, path in source_paths.items()}
        self.implementation_hash = _json_hash(self.implementation_sources)
        self.reference_spec = {
            "kind": "stage6-warm-joint-density-martingale-v1",
            "candidate_amplitudes": [".05", ".10", ".25"],
            "epsilon": self.epsilon,
            "amplitude_cap": self.amplitude_cap,
            "implementation_hash": self.implementation_hash,
        }
        self.confidence_process_hash = _json_hash(self.reference_spec)
        genesis = _json_hash({"model": self.model_hash, "confidence": self.confidence_process_hash})
        self.prefix_hashes = [genesis]
        self.observations: list[dict] = []
        self.increments: dict[int, tuple[I, I]] = {}
        self.certificates: dict[str, CertifiedCertificate] = {}
        self.time = -1
        self._envelope = None
        if not 0 < D(self.epsilon) < 1 or not 0 < D(self.amplitude_cap) <= D(self.model["attack_amplitude_cap"]):
            raise ValueError("Invalid confidence budget or amplitude cap")

    @property
    def prefix_hash(self) -> str:
        return self.prefix_hashes[-1]

    def append(self, sent: bool, u, r):
        observation = _canonical_observation(sent, u, r)
        old_coefficients = [
            (candidate["a"], candidate["B"]) for candidate in self.core.candidates
        ]
        self.core.append(sent, u, r)
        deltas = {}
        for onset, candidate in enumerate(self.core.candidates):
            if onset < len(old_coefficients):
                previous_a, previous_b = old_coefficients[onset]
            else:
                previous_a, previous_b = I.exact(0), I.exact(0)
            deltas[onset] = (candidate["a"] - previous_a, candidate["B"] - previous_b)
        self.increments = deltas
        self.observations.append(observation)
        self.time += 1
        self.prefix_hashes.append(_json_hash({"previous": self.prefix_hash, "observation": observation}))

    def _mint(self, time: int, direction, support, likelihood_source: str,
              source_envelope_id=None, parents=()) -> CertifiedCertificate:
        if time < 0 or time != self.time:
            raise ValueError("A certificate must be bound to the current observation prefix")
        d = tuple(_strict_fraction(x, "direction") for x in direction)
        z = _strict_fraction(support, "support")
        if z <= 0:
            raise ValueError("Only positive support certificates can shrink the parameter set")
        fields = {
            "model_hash": self.model_hash,
            "confidence_process_hash": self.confidence_process_hash,
            "implementation_hash": self.implementation_hash,
            "epsilon": self.epsilon,
            "amplitude_cap": self.amplitude_cap,
            "observation_prefix_hash": self.prefix_hash,
            "time": self.time,
            "direction": [str(x) for x in d],
            "support": str(z),
            "likelihood_source": likelihood_source,
            "source_envelope_id": source_envelope_id,
            "parent_certificate_ids": parents,
        }
        certificate = CertifiedCertificate(
            certificate_id=_json_hash(fields),
            model_hash=self.model_hash,
            confidence_process_hash=self.confidence_process_hash,
            implementation_hash=self.implementation_hash,
            epsilon=self.epsilon,
            amplitude_cap=self.amplitude_cap,
            observation_prefix_hash=self.prefix_hash,
            time=self.time,
            direction=d,
            support=z,
            likelihood_source=likelihood_source,
            source_envelope_id=source_envelope_id,
            parent_certificate_ids=parents,
        )
        self.certificates[certificate.certificate_id] = certificate
        return certificate

    def certify_full(self, direction, support, max_nodes=256):
        direction = tuple(_strict_fraction(x, "direction") for x in direction)
        support_fraction = _strict_fraction(support, "support")
        if len(direction) != len(self.core.W) or support_fraction <= 0:
            raise ValueError("Invalid direction or support")
        support_decimal = interval_fraction(support_fraction).lo
        result = self.core.certify_direction(
            direction,
            str(support_decimal),
            epsilon=self.epsilon,
            bmax=self.amplitude_cap,
            max_nodes=max_nodes,
        )
        certificate = None
        if result["certified"]:
            certificate = self._mint(self.time, direction,
                                     F(str(result["target_support"])), "full-domain")
        return result, certificate

    def import_frozen_certificate(self, artifact_path, expected_sha256: str, query: dict):
        """Re-verify a hash-pinned certificate query on this exact history."""
        raw = Path(artifact_path).read_bytes()
        actual_sha = _sha256(raw)
        if actual_sha != expected_sha256:
            raise ValueError("Frozen certificate artifact hash mismatch")
        artifact = json.loads(raw.decode("utf8"))
        binding = artifact.get("source_binding")
        if not isinstance(binding, dict):
            raise ValueError("The artifact lacks a bound observation-history certificate")
        expected_binding = {
            "model_hash": self.model_hash,
            "confidence_process_hash": self.confidence_process_hash,
            "implementation_hash": self.implementation_hash,
            "epsilon": self.epsilon,
            "amplitude_cap": self.amplitude_cap,
            "observation_prefix_hash": self.prefix_hash,
        }
        if any(binding.get(key) != value for key, value in expected_binding.items()):
            raise ValueError("The artifact is bound to a different model, confidence process, or history")
        time_value = int(query["time"])
        if time_value != self.time:
            raise ValueError("The replayed observation prefix does not match certificate time")
        query_match = any(
            item.get("certified") is True
            and int(item.get("time", -1)) == time_value
            and item.get("direction") == query.get("direction")
            and item.get("target_support") == query.get("target_support")
            and item.get("level") == query.get("level")
            for item in artifact.get("certificate_queries", [])
        )
        if not query_match:
            raise ValueError("The pinned artifact does not contain this successful query")
        successful_match = any(
            int(item.get("time", -1)) == time_value
            and item.get("direction") == query.get("direction")
            and item.get("z") == query.get("target_support")
            for item in artifact.get("successful_certificates", [])
        )
        if not successful_match:
            raise ValueError("The query has no corresponding stored certificate record")
        epsilon = str(query.get("epsilon", self.epsilon))
        amplitude_cap = str(query.get("amplitude_cap", self.amplitude_cap))
        if epsilon != self.epsilon or amplitude_cap != self.amplitude_cap:
            raise ValueError("The artifact query uses a different confidence process")
        support = _strict_fraction(query["target_support"], "support")
        direction = tuple(_strict_fraction(x, "direction") for x in query["direction"])
        verification = self.core.certify_direction(
            direction, str(interval_fraction(support).lo), epsilon=epsilon,
            bmax=amplitude_cap, max_nodes=int(query.get("max_nodes", 256)))
        if not verification["certified"]:
            raise ValueError("The stored certificate could not be verified on this history")
        verified_support = F(str(verification["target_support"]))
        return self._mint(
            time_value,
            direction,
            verified_support,
            f"frozen-artifact-reverified:{actual_sha}",
        )

    def validate_certificate(self, certificate: CertifiedCertificate):
        if not isinstance(certificate, CertifiedCertificate):
            raise TypeError("A typed successful certificate is required")
        known = self.certificates.get(certificate.certificate_id)
        if known != certificate:
            raise ValueError("Certificate was not issued by this evidence record")
        if certificate.model_hash != self.model_hash:
            raise ValueError("Certificate model hash mismatch")
        if certificate.confidence_process_hash != self.confidence_process_hash:
            raise ValueError("Certificate confidence-process hash mismatch")
        if certificate.implementation_hash != self.implementation_hash:
            raise ValueError("Certificate implementation hash mismatch")
        if certificate.epsilon != self.epsilon or certificate.amplitude_cap != self.amplitude_cap:
            raise ValueError("Certificate risk budget or amplitude cap mismatch")
        if certificate.time > self.time:
            raise ValueError("Certificate comes from a future observation time")
        if self.prefix_hashes[certificate.time + 1] != certificate.observation_prefix_hash:
            raise ValueError("Certificate observation prefix is not on this record lineage")


class CertifiedParameterEnvelope:
    """Typed outer set with provenance, multiple intervals, and incremental likelihood bounds."""

    def __init__(self, record: EvidenceRecord, certificate: CertifiedCertificate, *,
                 refinement_tolerance=".00001", refinement_budget=64):
        record.validate_certificate(certificate)
        if certificate.time != record.time:
            raise ValueError("An initial envelope must be built at its certificate time")
        if certificate.source_envelope_id is not None or record._envelope is not None:
            raise ValueError("An envelope starts once from an independent certificate")
        self.model_hash = record.model_hash
        self.confidence_process_hash = record.confidence_process_hash
        self.implementation_hash = record.implementation_hash
        self.epsilon = record.epsilon
        self.amplitude_cap = record.amplitude_cap
        self.birth_time = certificate.time
        self.last_certificate_time = certificate.time
        self.time = record.time
        self.observation_prefix_hash = record.prefix_hash
        self._certificate_history = [certificate]
        self._query_snapshot_id = None
        self._trigger_upper_cache = {}
        self.refinement_tolerance = D(refinement_tolerance)
        self.refinement_budget = int(refinement_budget)
        self.stats = {"increment_updates": 0, "increment_log_calls": 0,
                      "direct_likelihood_bounds": 0, "branches_split": 0,
                      "low_support_boxes": 0}
        initial_nodes = self._certificate_lower(record, certificate)
        self._nodes = self._refine_nodes(record, initial_nodes, self.refinement_budget)
        record._envelope = self

    @property
    def certificate_history(self):
        return tuple(self._certificate_history)

    @property
    def nodes(self) -> tuple[LikelihoodNode, ...]:
        return tuple(self._nodes)

    @staticmethod
    def _certificate_lower(record: EvidenceRecord, certificate: CertifiedCertificate):
        nodes = []
        bmax = D(record.amplitude_cap)
        z = certificate.support
        for onset in range(len(record.core.candidates)):
            q = record.core.support_coefficient(onset, certificate.direction)
            if q.hi <= 0:
                continue
            lower_interval = interval_fraction(z) / I.exact(q.hi)
            lower = max(D(0), lower_interval.lo)
            if lower > bmax:
                continue
            initial = I(lower, bmax)
            upper = record.core.likelihood(onset, initial).hi
            nodes.append(LikelihoodNode(onset, lower, bmax, upper))
        return nodes

    @classmethod
    def start(cls, record: EvidenceRecord, certificate: CertifiedCertificate,
              *, refinement_tolerance=".00001", refinement_budget=64):
        return cls(record, certificate, refinement_tolerance=refinement_tolerance,
                   refinement_budget=refinement_budget)

    def _validate_record(self, record: EvidenceRecord, allow_advance=True):
        if record.model_hash != self.model_hash:
            raise ValueError("Envelope model hash mismatch")
        if record.confidence_process_hash != self.confidence_process_hash:
            raise ValueError("Envelope confidence-process hash mismatch")
        if record.implementation_hash != self.implementation_hash:
            raise ValueError("Envelope implementation hash mismatch")
        if record.epsilon != self.epsilon or record.amplitude_cap != self.amplitude_cap:
            raise ValueError("Envelope risk budget or amplitude cap mismatch")
        if self.time >= len(record.prefix_hashes) or \
                record.prefix_hashes[self.time + 1] != self.observation_prefix_hash:
            raise ValueError("Envelope observation history is not a prefix of this record")
        if record.time < self.time:
            raise ValueError("Envelope cannot be applied to an earlier record")
        if record._envelope is not self:
            raise ValueError("The envelope was not initialized by this evidence record")
        if not allow_advance and record.time != self.time:
            raise ValueError("Initial envelope time must match the record")

    def _threshold(self, record: EvidenceRecord) -> I:
        return (I.exact(self.epsilon) * record.core.ref).ln()

    def _direct_upper(self, record: EvidenceRecord, onset: int, lower: D, upper: D) -> D:
        result = record.core.likelihood(onset, I(lower, upper)).hi
        self.stats["direct_likelihood_bounds"] += 1
        return result

    def _split_at_observation_zero(self, node: LikelihoodNode, record: EvidenceRecord, t: int):
        mark = record.core.marks[t]
        if mark is None:
            return [node]
        zero = mark[0]
        if node.lower < zero < node.upper:
            return [LikelihoodNode(node.onset, node.lower, zero, node.loglik_upper),
                    LikelihoodNode(node.onset, zero, node.upper, node.loglik_upper)]
        return [node]

    def _split_all_observation_zeros(self, node: LikelihoodNode, record: EvidenceRecord,
                                     through_time: int):
        cuts = {mark[0] for mark in record.core.marks[node.onset:through_time + 1]
                if mark is not None and node.lower < mark[0] < node.upper}
        if not cuts:
            return [node]
        endpoints = [node.lower, *sorted(cuts), node.upper]
        return [LikelihoodNode(node.onset, left, right, node.loglik_upper)
                for left, right in zip(endpoints, endpoints[1:])]

    def _increment_upper(self, record: EvidenceRecord, node: LikelihoodNode, t: int) -> D:
        delta = record.increments[node.onset]
        delta_a, delta_b = delta
        b = I(node.lower, node.upper)
        value = delta_a * b - delta_b * b.square() / 2
        mark = record.core.marks[t]
        if mark is not None:
            v, denominator = mark
            key = (node.lower, node.upper)
            if key not in self._trigger_upper_cache:
                self._trigger_upper_cache[key] = log_trigger(I.exact(v) - b, record.core.model["Z"]) - denominator
                self.stats["increment_log_calls"] += 1
            value = value + self._trigger_upper_cache[key]
        return value.hi

    def _refine_nodes(self, record: EvidenceRecord, nodes: list[LikelihoodNode], budget: int,
                      threshold: I | None = None):
        if threshold is None:
            threshold = self._threshold(record)
        pending = [piece for node in nodes
                   for piece in self._split_all_observation_zeros(node, record, record.time)]
        retained = []
        used = 0
        while pending:
            node = pending.pop()
            if node.loglik_upper < threshold.lo:
                continue
            if node.upper - node.lower <= self.refinement_tolerance or used >= budget:
                retained.append(node)
                continue
            with localcontext() as context:
                context.prec = PRECISION
                mid = (node.lower + node.upper) / 2
            if mid <= node.lower or mid >= node.upper:
                retained.append(node)
                continue
            children = [LikelihoodNode(node.onset, node.lower, mid, D(0)),
                        LikelihoodNode(node.onset, mid, node.upper, D(0))]
            used += 1
            self.stats["branches_split"] += 1
            for pending_child in children:
                child = LikelihoodNode(pending_child.onset, pending_child.lower,
                    pending_child.upper, self._direct_upper(record, pending_child.onset,
                                                            pending_child.lower, pending_child.upper))
                if child.loglik_upper >= threshold.lo:
                    pending.append(child)
        retained.sort(key=lambda node: (node.onset, node.lower))
        merged = []
        for node in retained:
            if (merged and merged[-1].onset == node.onset and merged[-1].upper == node.lower
                    and merged[-1].loglik_upper == node.loglik_upper):
                previous = merged.pop()
                node = LikelihoodNode(node.onset, previous.lower, node.upper, node.loglik_upper)
            merged.append(node)
        return merged

    def advance(self, record: EvidenceRecord, *, refinement_budget=0):
        self._validate_record(record)
        if record.time == self.time:
            return {"time": self.time, "nodes_before": len(self._nodes),
                    "nodes_after": len(self._nodes), "pruned": 0, "updated_steps": 0}
        if record.time != self.time + 1:
            raise ValueError("Cumulative likelihood bounds must be updated once per new observation")
        before = len(self._nodes)
        self._query_snapshot_id = None
        self._trigger_upper_cache.clear()
        threshold = self._threshold(record)
        updated_nodes = []
        for node in self._nodes:
            increment = self._increment_upper(record, node, record.time)
            updated = (I.exact(node.loglik_upper) + I.exact(increment)).hi
            self.stats["increment_updates"] += 1
            if updated >= threshold.lo:
                updated_nodes.append(LikelihoodNode(node.onset, node.lower, node.upper, updated))
        self._nodes = self._refine_nodes(record, updated_nodes, int(refinement_budget), threshold) \
            if refinement_budget else updated_nodes
        self.time = record.time
        self.observation_prefix_hash = record.prefix_hash
        return {"time": self.time, "nodes_before": before,
                "nodes_after": len(self._nodes), "updated_steps": 1}

    def snapshot_id(self, record):
        self._validate_record(record, allow_advance=False)
        if self.last_certificate_time >= record.time:
            raise ValueError("Restricted search requires certificates strictly earlier than the query")
        if self._query_snapshot_id is None:
            self._query_snapshot_id = _json_hash({
                "prefix": self.observation_prefix_hash,
                "parents": [item.certificate_id for item in self.certificate_history],
                "nodes": [[node.onset, str(node.lower), str(node.upper), str(node.loglik_upper)]
                          for node in self._nodes],
            })
        return self._query_snapshot_id

    def _apply_direction(self, record: EvidenceRecord, certificate: CertifiedCertificate):
        q_intervals = {node.onset: record.core.support_coefficient(
            node.onset, certificate.direction) for node in self._nodes}
        updated = []
        removed = 0
        for node in self._nodes:
            q = q_intervals[node.onset]
            if q.hi <= 0:
                removed += 1
                continue
            lower_bound = (interval_fraction(certificate.support) / I.exact(q.hi)).lo
            new_lower = max(node.lower, lower_bound)
            if new_lower > node.upper:
                removed += 1
                continue
            updated.append(LikelihoodNode(node.onset, new_lower, node.upper, node.loglik_upper))
        self._nodes = updated
        self._certificate_history.append(certificate)
        self.last_certificate_time = certificate.time
        self.observation_prefix_hash = record.prefix_hash
        return {"time": self.time, "nodes_before": len(q_intervals),
                "nodes_after": len(updated), "removed_nodes": removed}

    def apply_certificate(self, record: EvidenceRecord, certificate: CertifiedCertificate):
        self._validate_record(record, allow_advance=False)
        record.validate_certificate(certificate)
        if certificate.time != record.time:
            raise ValueError("A certificate can only be applied at its source time")
        if any(item.certificate_id == certificate.certificate_id
               for item in self.certificate_history):
            raise ValueError("Certificate has already been applied")
        if certificate.time < self.last_certificate_time:
            raise ValueError("A stale direction certificate cannot shrink the envelope")
        if certificate.source_envelope_id is not None:
            parents = tuple(item.certificate_id for item in self.certificate_history
                            if item.time < record.time)
            if certificate.source_envelope_id != self._query_snapshot_id or \
                    certificate.parent_certificate_ids != parents:
                raise ValueError("Restricted certificate has a different source snapshot")
        self._apply_direction(record, certificate)

    def confidence_intervals(self):
        intervals: dict[int, list[tuple[D, D]]] = {}
        for node in self._nodes:
            intervals.setdefault(node.onset, []).append((node.lower, node.upper))
        merged = {}
        for onset, values in intervals.items():
            values.sort()
            components: list[list[D]] = []
            for lower, upper in values:
                if not components or lower > components[-1][1]:
                    components.append([lower, upper])
                else:
                    components[-1][1] = max(components[-1][1], upper)
            merged[onset] = [(lower, upper) for lower, upper in components]
        return merged

    def contains_parameter(self, onset: int, amplitude) -> bool:
        b = _strict_fraction(amplitude, "amplitude")
        return any(node.onset == onset and node.lower <= b <= node.upper for node in self._nodes)

    def propose_direction(self, record: EvidenceRecord, *, decimals=6):
        """Choose a deterministic direction from the current outer likelihood set."""
        self._validate_record(record, allow_advance=False)
        if not self._nodes:
            return None
        node = max(self._nodes, key=lambda item: item.loglik_upper)
        with localcontext() as context:
            context.prec = PRECISION
            amplitude = (node.lower + node.upper) / 2
            response = record.core.candidates[node.onset]["H"]
            point = [amplitude * (value.lo + value.hi) / 2 for value in response]
            scale = max((abs(value) for value in point), default=D(0))
            if scale == 0:
                return None
            quantum = D(1).scaleb(-int(decimals))
            rounded = [value.__truediv__(scale).quantize(quantum) for value in point]
        direction = tuple(F(str(value)) for value in rounded)
        if not any(direction):
            return None
        return {"direction": direction,"onset":node.onset,
                "amplitude_interval":[str(node.lower),str(node.upper)],
                "proposal_loglik_upper":str(node.loglik_upper)}

    def directional_action(self, record: EvidenceRecord, direction, *, l1_cap=None):
        """Return a one-sided certified support correction over all outer nodes."""
        self._validate_record(record, allow_advance=False)
        d=tuple(_strict_fraction(value,"direction") for value in direction)
        if len(d)!=len(record.core.W) or not any(d):
            raise ValueError("Direction must be nonzero and match the state dimension")
        lower_support=None
        for node in self._nodes:
            q=record.core.support_coefficient(node.onset,d)
            amplitude=I(node.lower,node.upper)
            product=q*amplitude
            lower=product.lo
            lower_support=lower if lower_support is None else min(lower_support,lower)
        if lower_support is None or lower_support<=0:
            zero=tuple(F(0) for _ in d)
            return {"action":zero,"support":None if lower_support is None else str(lower_support),
                    "guaranteed_gain":"0"}
        support=F(str(lower_support))
        weight=record.core.W
        norm=sum((d[i]*weight[i][j]*d[j]
                  for i in range(len(d)) for j in range(len(d))),F(0))
        if norm<=0:raise ValueError("State weight must be positive definite")
        action=tuple(support/norm*value for value in d)
        if l1_cap is not None:
            cap=_strict_fraction(l1_cap,"output cap")
            if cap<0:raise ValueError("Output cap must be nonnegative")
            l1=sum((abs(value) for value in action),F(0))
            if l1>cap:action=tuple(cap/l1*value for value in action)
        gain=sum((action[i]*weight[i][j]*action[j]
                  for i in range(len(action)) for j in range(len(action))),F(0))
        return {"action":action,"support":str(support),"guaranteed_gain":str(gain)}

    def certify_direction(self, record: EvidenceRecord, direction, support,
                           *, max_nodes=256, min_width=".00000001"):
        snapshot = self.snapshot_id(record)
        d = tuple(_strict_fraction(x, "direction") for x in direction)
        z = _strict_fraction(support, "support")
        if len(d) != len(record.core.W) or not any(d) or z <= 0:
            raise ValueError("Invalid direction or support")
        threshold = self._threshold(record)
        result = {"certified": False, "restricted": True, "nodes": 0, "boxes_tested": 0,
                  "target_support": str(z), "source_envelope_id": snapshot}
        if not self._nodes:
            return dict(result, reason="EMPTY_OUTER_SET"), None

        jobs = []
        coefficients = {}
        for node in self._nodes:
            if node.loglik_upper < threshold.lo:
                continue
            if node.onset not in coefficients:
                coefficients[node.onset] = record.core.support_coefficient(node.onset, d)
            q = coefficients[node.onset]
            upper = node.upper
            if q.lo > 0:
                upper = min(upper, (interval_fraction(z) / I.exact(q.lo)).hi)
            if upper < node.lower:
                continue
            box = I(node.lower, upper)
            if upper == node.lower and (q * box).lo >= z:
                continue
            clipped = LikelihoodNode(node.onset, node.lower, upper, node.loglik_upper)
            jobs.extend((piece.onset, I(piece.lower, piece.upper), piece.loglik_upper)
                        for piece in self._split_all_observation_zeros(clipped, record, record.time))

        while jobs:
            onset, box, inherited = jobs.pop()
            bound = min(inherited, record.core.tangent_upper(onset, box))
            result["boxes_tested"] += 1
            if bound < threshold.lo:
                continue
            if result["nodes"] >= max_nodes or box.hi - box.lo <= D(min_width):
                return dict(result, reason="UNRESOLVED_LOW_SUPPORT_BOX",
                            unresolved_onset=onset, unresolved_box=box.json()), None
            with localcontext() as context:
                context.prec = PRECISION
                mid = (box.lo + box.hi) / 2
            if not box.lo < mid < box.hi:
                return dict(result, reason="UNRESOLVED_SUBDIVISION"), None
            jobs.extend(((onset, I(box.lo, mid), bound), (onset, I(mid, box.hi), bound)))
            result["nodes"] += 1
            self.stats["low_support_boxes"] += 1
        parents = tuple(item.certificate_id for item in self.certificate_history)
        certificate = record._mint(record.time, d, z, "cumulative-envelope-restricted",
                                   snapshot, parents)
        gain = z**2 / inner(d, d, record.core.W)
        return dict(result, certified=True, reason="ALL_RETAINED_LOW_SUPPORT_BOXES_EXCLUDED",
                    guaranteed_gain=str(gain)), certificate
