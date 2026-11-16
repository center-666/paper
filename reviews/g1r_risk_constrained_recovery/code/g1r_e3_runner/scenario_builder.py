"""E3 permission boundary; shared unchanged Yang functions and timing validators."""
from dataclasses import dataclass
import hashlib
import numpy as np

from .authorization_guard import require
from ..g1r_e2_runner.scenario_builder import ScenarioBuilder as YangBridge


@dataclass(frozen=True)
class OfflineTruth:
    seed: int
    group: str
    event: tuple | None
    age: int | None
    true_state: tuple
    healthy_estimate: tuple
    attacked_estimate: tuple
    delta: tuple
    z0: tuple
    pairing_sha256: str
    replay_source_time: int | None
    actual_replay_age: int | None
    cache_replacement_time: int | None


@dataclass(frozen=True)
class E3Case:
    z: tuple
    truth: OfflineTruth


class ScenarioBuilder(YangBridge):
    def __init__(self, config, public, receipt=None):
        super().__init__(config.shared, public)
        self.e3_config = config
        self.receipt = receipt
        self.generation_calls = []

    def _model_and_data(self, seed, authorization=None, fixture=False):
        if fixture:
            if int(seed) != 0: raise PermissionError('only seed 0 fixture generation allowed')
        else:
            require(self.e3_config, self.receipt)
            if seed not in self.e3_config.normal_seeds + self.e3_config.attack_seeds:
                raise PermissionError('seed outside E3 reservation')
        model = self._build_model()
        self._verify_frozen_model(model)
        seeds = np.asarray([int(seed)], dtype=np.int64)
        self.generation_calls.append(int(seed))
        x, y = self._generate_data(model, seeds)
        if (x.shape != (1,model.cfg['T']+1,model.cfg['n'])
                or y.shape != (1,model.cfg['T'],model.cfg['N'],model.cfg['n'])
                or not np.isfinite(x).all() or not np.isfinite(y).all()):
            raise ValueError('invalid Yang generated data')
        schedule = self._common_schedule(model,1)
        expected = np.zeros_like(schedule)
        for node in range(model.cfg['N']): expected[:,:,node] = np.arange(model.cfg['T']) % 8 == node
        expected[:,0,:] = True
        if not np.array_equal(schedule,expected): raise ValueError('gap-8 schedule changed')
        for array in (x,y,seeds,schedule): array.setflags(write=False)
        return model,x,y,seeds,schedule

    def prepare(self, seed, *, fixture=False):
        return self._prepare_seed(int(seed), fixture=fixture)

    def case(self, context, group, event=None, age=None, *, fixture=False):
        if not fixture: require(self.e3_config, self.receipt)
        elif context.seed != 0: raise PermissionError('fixture seed must be 0')
        if group not in {'normal','attack'}: raise ValueError('invalid E3 group')
        if not fixture and context.seed not in (self.e3_config.normal_seeds if group=='normal' else self.e3_config.attack_seeds):
            raise PermissionError('seed in wrong E3 group')
        receiver = int(self.config.protocol['receiver']); target = self.config.target_time
        healthy = context.healthy_run.estimates[0,target,receiver]
        z0 = self._innovation(context.model,context.healthy_run,context.y)
        dig = hashlib.sha256()
        for a in (context.x,context.y,context.schedule): dig.update(np.ascontiguousarray(a).tobytes())
        pairing = dig.hexdigest()
        if event is None:
            if age is not None: raise ValueError('age without event')
            z = z0; attacked = healthy; source=actual_age=q=None
        else:
            event = tuple(map(int,event))
            if group!='attack' or event not in self.e3_config.events or age not in self.e3_config.ages:
                raise ValueError('unplanned attack case')
            case,run,checks = self._build_replay(context,event,age,fixture=fixture)
            z = case.online_input.z; attacked = run.estimates[0,target,receiver]
            source=checks['source_time']; actual_age=checks['actual_age']; q=checks['cache_replacement_time']
            if source!=event[1]-age or actual_age!=age or q!=event[1]+8:
                raise ValueError('E3 Replay timing mismatch')
        truth=OfflineTruth(context.seed,group,event,age,tuple(context.x[0,target]),tuple(healthy),
            tuple(attacked),tuple(np.asarray(attacked)-healthy),tuple(z0),pairing,source,actual_age,q)
        return E3Case(tuple(z),truth)
