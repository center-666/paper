"""E3 online interface has no scenario/truth argument or lookup."""
from dataclasses import dataclass
import json
import numpy as np

from .config_loader import canonical_sha256
from ..g1r_e2_runner.online_proposal import (build_online_input as frozen_input,
    propose as frozen_propose, record_dict)


@dataclass(frozen=True)
class OnlineInput:
    z: tuple
    frozen_public_model: object
    threshold: float
    method: str


@dataclass(frozen=True)
class E3ProposalRecord:
    payload_json: str
    record_sha256: str

    def payload(self):
        payload = json.loads(self.payload_json)
        if canonical_sha256(payload) != self.record_sha256:
            raise ValueError('E3 proposal record corrupted')
        return payload


def propose(online):
    if type(online) is not OnlineInput or set(vars(online)) != {'z','frozen_public_model','threshold','method'}:
        raise ValueError('E3 online input whitelist violated')
    z = np.asarray(online.z, dtype=float)
    if z.shape != (12,) or not np.isfinite(z).all():
        raise ValueError('12 finite innovations required')
    raw = frozen_propose(frozen_input(z, online.frozen_public_model, online.threshold, online.method))
    payload = record_dict(raw)
    encoded = json.dumps(payload, sort_keys=True, separators=(',', ':'), allow_nan=False)
    return E3ProposalRecord(encoded, canonical_sha256(payload))
