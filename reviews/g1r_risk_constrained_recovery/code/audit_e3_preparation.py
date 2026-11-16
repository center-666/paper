"""Deterministic E3 acceptance harness, with hard blocks on reserved-seed RNG/data."""
from __future__ import annotations
import argparse
import io
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
import numpy as np

from .g1r_e3_runner.config_loader import ROOT


def run(out):
    if out.exists(): raise FileExistsError(out)
    for path in (ROOT/'simulation',ROOT/'reviews/g1_retroactive_recovery/code'):
        sys.path.insert(0,str(path))
    import model
    original_data=model.generate_data; original_rng=np.random.default_rng
    generation=[]; rng_calls=[]; blocked=[]
    def data_guard(m,seeds):
        values=list(map(int,np.asarray(seeds).ravel()))
        if any(s!=0 for s in values):
            blocked.append(values); raise AssertionError('preparation may generate only seed 0')
        generation.extend(values); return original_data(m,seeds)
    def rng_guard(seed=None):
        if isinstance(seed,(int,np.integer)):
            seed=int(seed)
            if 141440000<=seed<=141440199 or 141450000<=seed<=141450199 or seed==141460000:
                blocked.append(seed); raise AssertionError('reserved E3 RNG prohibited in preparation')
            rng_calls.append(seed)
        return original_rng(seed)
    suite=unittest.defaultTestLoader.loadTestsFromName('reviews.g1r_risk_constrained_recovery.code.g1r_e3_runner.tests.test_preparation')
    log=io.StringIO()
    with patch.object(model,'generate_data',data_guard),patch.object(np.random,'default_rng',rng_guard):
        result=unittest.TextTestRunner(stream=log,verbosity=2).run(suite)
    out.mkdir(parents=True)
    (out/'tests.log.txt').write_bytes(log.getvalue().encode('utf-8'))
    summary={'tests_run':result.testsRun,'passed':result.wasSuccessful(),
             'failures':[{'test':str(t),'traceback':s} for t,s in result.failures],
             'errors':[{'test':str(t),'traceback':s} for t,s in result.errors],
             'generated_trajectory_seeds':generation,'rng_calls':rng_calls,
             'unexpected_seed_rng_or_generation_attempts':blocked,
             'formal_E3_trajectory_count':0,'formal_E3_executed':False,
             'formal_authorization_file_created':False,'scope':'fixture seed0, synthetic numeric data, existing E2 cache only'}
    (out/'summary.json').write_bytes((json.dumps(summary,sort_keys=True,indent=2)+'\n').encode())
    print(json.dumps(summary,indent=2))
    return result.wasSuccessful()


if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('--out',type=Path,required=True)
    raise SystemExit(0 if run(p.parse_args().out.resolve()) else 1)
