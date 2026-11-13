"""Receiver-side full-prefix GLS attribution and deterministic correction delivery.

Research prototype: fixed, public schedule; one receiver; synchronous reliable
control subslots are explicit assumptions. No attack simulator or truth is an
input to detection, localization, delivery, or write-back.
"""
from __future__ import annotations
from collections import deque
from dataclasses import dataclass
from pathlib import Path
import struct
import sys
import numpy as np

BRANCH = Path(__file__).resolve().parents[1]
ROOT = BRANCH.parents[1]
sys.path.insert(0, str(ROOT / 'simulation'))
sys.path.insert(0, str(BRANCH / 'code'))
import compare_deghat_outputs as prior

@dataclass(frozen=True)
class Reception:
    edge: int
    time: int

@dataclass(frozen=True)
class AttributedEvent:
    event: Reception
    decision_time: int
    theta: np.ndarray
    score: float

@dataclass(frozen=True)
class Candidate:
    event: Reception
    state_response: np.ndarray
    raw_response: np.ndarray
    gain: np.ndarray
    information: np.ndarray

@dataclass(frozen=True)
class FittedGLS:
    receiver: int
    begin: int
    decision_time: int
    mean: np.ndarray
    candidates: tuple[Candidate, ...]
    expected_receptions: tuple[Reception, ...]
    threshold: float
    training_count: int
    calibration_count: int


def candidates_from_receptions(receptions, edges, receiver, begin, decision_time):
    """Candidate events come from local receive records, excluding same-tick events.

    An event at decision_time cannot affect this receiver's innovation at that
    time in the existing update ordering. The packet itself is not examined here.
    """
    edges = np.asarray(edges, dtype=int)
    events = set()
    for rec in receptions:
        if not isinstance(rec, Reception):
            raise TypeError('reception records must be Reception objects')
        if not 0 <= rec.edge < len(edges) or edges[rec.edge, 1] != receiver:
            raise ValueError('record is not an incoming edge of this receiver')
        if begin <= rec.time < decision_time:
            events.add(rec)
    return tuple(sorted(events, key=lambda e: (e.time, e.edge)))


def _response(model, schedule, event, decision_time):
    """Model/schedule-only response; no actual neighbor estimate is read."""
    if not schedule[event.time, model.edges[event.edge, 0]]:
        raise ValueError('event is not an actual scheduled reception')
    S, aligned = prior.event_sensitivity(model, schedule, event.edge, event.time)
    last = np.full(len(model.edges), -1, dtype=int)
    for t in range(decision_time + 1):
        last = np.where(schedule[t, model.edges[:, 0]], t, last)
    if np.any(last < 0):
        raise ValueError('every cache must have an initial received packet')
    # At the reception time age=0, aligned sensitivity is the raw packet
    # sensitivity. This uses no inverse of A and remains valid for singular A.
    raw_at_decision = np.stack([aligned[last[e], e] for e in range(len(last))])
    return S, raw_at_decision


def fit_full_prefix(model, schedule, receiver, begin, decision_time,
                    reception_records, train_innovations, calibration_innovations,
                    ridge_fraction=0.02, quantile=0.95):
    """Fit one normal model and the maximum of the existing GLS scores.

    Inputs are disjoint normal training and calibration innovation sequences.
    Quantile calibrates the *maximum over all candidates*, not single-event
    scores; its finite calibration uncertainty remains to be reported.
    """
    if receiver != prior.TARGET_NODE:
        raise ValueError('prior feature sensitivity is implemented for receiver 1')
    if not (0 <= begin < decision_time < model.cfg['T']):
        raise ValueError('invalid fixed window')
    train = np.asarray(train_innovations, dtype=float)
    cal = np.asarray(calibration_innovations, dtype=float)
    expected = (decision_time - begin + 1, model.cfg['n'])
    if train.ndim != 3 or cal.ndim != 3 or train.shape[1:] != expected or cal.shape[1:] != expected:
        raise ValueError('innovations must have shape (trials, window, state_dim)')
    if len(train) < 2 or len(cal) < 2 or not np.isfinite(train).all() or not np.isfinite(cal).all():
        raise ValueError('insufficient or nonfinite normal data')
    events = candidates_from_receptions(reception_records, model.edges, receiver, begin, decision_time)
    if not events:
        raise ValueError('empty reception candidate set')
    mean, _, precision = prior.fit_covariance(train.reshape(len(train), -1), ridge_fraction)
    times = np.arange(begin, decision_time + 1)
    candidates = []
    for event in events:
        S, raw = _response(model, schedule, event, decision_time)
        J = prior.feature_sensitivity(S, np.zeros((0,)), model, times, False)
        info = J.T @ precision @ J
        if np.linalg.matrix_rank(info) < model.cfg['n']:
            continue  # cannot identify a full payload vector under this model
        gain = np.linalg.pinv(info, rcond=1e-10) @ J.T @ precision
        candidates.append(Candidate(event, S, raw, gain, info))
    if not candidates:
        raise ValueError('no observable candidate payloads')
    centered = cal.reshape(len(cal), -1) - mean
    scores = np.stack([np.einsum('si,ij,sj->s', centered@c.gain.T,
                                c.information, centered@c.gain.T)
                       for c in candidates], axis=1)
    threshold = float(np.quantile(scores.max(axis=1), quantile, method='higher'))
    return FittedGLS(receiver, begin, decision_time, mean, tuple(candidates),
                     events, threshold, len(train), len(cal))


def attribute(fit, receiver_innovations, reception_records):
    """Use receiver-local data only; no simulator Run or attack metadata."""
    obs = np.asarray(receiver_innovations, dtype=float)
    if obs.shape != (fit.decision_time-fit.begin+1, fit.candidates[0].gain.shape[0]):
        raise ValueError('invalid innovation window')
    if not np.isfinite(obs).all():
        raise ValueError('nonfinite innovations')
    actual = {r for r in reception_records if fit.begin <= r.time < fit.decision_time}
    if actual != set(fit.expected_receptions):
        raise ValueError('fitted schedule does not match actual reception records')
    centered = obs.reshape(-1) - fit.mean
    fits = []
    for c in fit.candidates:
        theta = c.gain @ centered
        fits.append((float(theta @ c.information @ theta), c, theta))
    score, candidate, theta = max(fits, key=lambda z: z[0])
    if score <= fit.threshold:
        return None
    return AttributedEvent(candidate.event, fit.decision_time, theta.copy(), score)


def _tree(edges, root, n_nodes):
    """Breadth-first directed tree, with send/receive hops per control round."""
    children = {root: (None, 0)}
    q = deque([root])
    while q:
        node = q.popleft()
        for j, i in np.asarray(edges, dtype=int):
            if j == node and i not in children:
                children[int(i)] = (node, children[node][1] + 1)
                q.append(int(i))
    if len(children) != n_nodes:
        raise ValueError('repair command cannot reach all nodes')
    return sorted([(parent, node, depth) for node, (parent, depth) in children.items()
                   if parent is not None], key=lambda x: (x[2], x[1]))


def deliver_command(attribution, edges, root, n_nodes):
    """Ideal reliable in-band control rounds; returns actual serialized messages.

    Message format: edge id uint8, reception and decision times uint16, 2 float64.
    No framing, authentication, loss, retransmission, or timing model is implied.
    """
    if attribution is None:
        return {}, []
    theta = np.asarray(attribution.theta, dtype=float)
    if theta.shape != (2,) or not np.isfinite(theta).all():
        raise ValueError('the current frozen model requires two finite components')
    packet = struct.pack('<BHH2d', attribution.event.edge, attribution.event.time,
                         attribution.decision_time, *theta)
    received = {root: packet}
    transmissions = []
    for parent, node, depth in _tree(edges, root, n_nodes):
        if parent not in received:
            raise AssertionError('tree order violated')
        received[node] = received[parent]
        transmissions.append({'sender': parent, 'receiver': node, 'round': depth,
                              'payload_bytes': len(packet)})
    return received, transmissions


def apply_local_writeback(node, state, local_raw_caches, incoming_edge_ids,
                          packet, candidate, decision_time, edges):
    """Modify only the named node and its own incoming caches, on copies."""
    edge, event_time, packet_time, *theta = struct.unpack('<BHH2d', packet)
    event = Reception(edge, event_time)
    if candidate.event != event or packet_time != decision_time:
        raise ValueError('command does not match local response')
    ids = np.asarray(incoming_edge_ids, dtype=int)
    expected = np.flatnonzero(np.asarray(edges, dtype=int)[:, 1] == node)
    if ids.ndim != 1 or not np.array_equal(np.sort(ids), expected):
        raise ValueError('must supply each of this node\'s incoming caches exactly once')
    x = np.asarray(state, dtype=float).copy()
    raw = np.asarray(local_raw_caches, dtype=float).copy()
    theta = np.asarray(theta)
    if raw.shape != (len(ids), len(theta)):
        raise ValueError('cache ownership/shape mismatch')
    x -= candidate.state_response[decision_time+1, node] @ theta
    raw -= np.einsum('enp,p->en', candidate.raw_response[ids], theta)
    return x, raw
