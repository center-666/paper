"""Preserved deterministic E2-P0 acceptance runs; never execute E2/E3."""
from __future__ import annotations
import argparse
import contextlib
import hashlib
import json
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[3]
BASE=ROOT/'reviews/g1r_risk_constrained_recovery'
sys.path[:0]=[str(ROOT),str(ROOT/'simulation'),str(BASE/'code')]


def save(path,value):
    with path.open('x',encoding='utf-8',newline='\n') as file:
        json.dump(value,file,indent=2,ensure_ascii=True,allow_nan=False)
        file.write('\n')


def main(out:Path):
    out.mkdir(parents=True,exist_ok=False)
    save(out/'config.json',{'scope':'E2-P0 deterministic audit only','E2':False,'E3':False,
         'formal_authorization_created':False,'allowed_generated_seeds':[0],
         'baseline':'09637308c03c51dfa5891ed35d17cfa5ab0c1a7e',
         'head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()})
    protected=['simulation/engine.py','simulation/model.py',
        'reviews/g1r_risk_constrained_recovery/code/v2_estimators.py',
        'reviews/g1r_risk_constrained_recovery/code/calibrate_v2_normal.py',
        'reviews/g1r_risk_constrained_recovery/code/e2_status_adapter.py',
        'reviews/g1r_risk_constrained_recovery/protocol_v2.json',
        'reviews/g1r_risk_constrained_recovery/results/g1r_task5_calibration_20261115_r01/frozen_thresholds.json']
    before={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in protected}
    save(out/'protected_before.json',before)
    import model
    original=model.generate_data
    used=[]
    def guard(m,seeds):
        ids=[int(s) for s in seeds]
        if any(s!=0 for s in ids):
            raise AssertionError('P0 cannot generate any non-fixture seed trajectory')
        used.extend(ids)
        return original(m,seeds)
    from reviews.g1r_risk_constrained_recovery.code.g1r_e2_runner import config_loader as cfg
    from reviews.g1r_risk_constrained_recovery.code.g1r_e2_runner import environment_guard as env
    from reviews.g1r_risk_constrained_recovery.code.g1r_e2_runner import authorization_guard as auth
    from reviews.g1r_risk_constrained_recovery.code.g1r_e2_runner.tests import test_prelaunch_integrity as p0,test_runner as prior
    p0.EVIDENCE_DIR=out
    c=cfg.load_frozen_config()
    save(out/'live_environment.json',{'validation':env.verify_environment(c),'captured':env.current_environment()})
    # A hash report only; it has no owner/id and explicitly cannot authorize.
    save(out/'authorization_bindings.json',{'scope':'E2','authorized':False,'bindings':auth.authorization_bindings(c)})
    suite=unittest.TestSuite([unittest.defaultTestLoader.loadTestsFromModule(p0),unittest.defaultTestLoader.loadTestsFromModule(prior)])
    class DetailedResult(unittest.TextTestResult):
        records=[]
        def addSuccess(self,test):
            super().addSuccess(test); self.records.append({'test':test.id(),'result':'PASS'})
        def addFailure(self,test,err):
            super().addFailure(test,err); self.records.append({'test':test.id(),'result':'FAIL'})
        def addError(self,test,err):
            super().addError(test,err); self.records.append({'test':test.id(),'result':'ERROR'})
    with (out/'tests.log').open('x',encoding='utf-8') as log, patch.object(model,'generate_data',side_effect=guard), contextlib.redirect_stderr(log):
        result=unittest.TextTestRunner(stream=log,verbosity=2,resultclass=DetailedResult).run(suite)
    after={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in protected}
    assert before==after,'Frozen algorithm/input files changed during audit'
    summary={'tests_run':result.testsRun,'pass':result.wasSuccessful(),'failures':len(result.failures),'errors':len(result.errors),
        'tests':result.records,'formal_seed_generation_calls':0,'generated_fixture_seed_calls':used,
        'E2':False,'E3':False,'frozen_sources_unchanged':True}
    save(out/'tests.json',summary)
    sources={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
             for p in (BASE/'code/g1r_e2_runner').rglob('*.py')}
    sources[Path(__file__).resolve().relative_to(ROOT).as_posix()]=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    save(out/'source_hashes.json',sources)
    save(out/'manifest.json',{'status':'PASS' if result.wasSuccessful() else 'FAILED_DETERMINISTIC_AUDIT',
         'files_sha256':{p.relative_to(out).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
                         for p in out.rglob('*') if p.is_file() and p.name!='manifest.json'},'E2':False,'E3':False})
    print(json.dumps({k:v for k,v in summary.items() if k not in ('tests','generated_fixture_seed_calls')},indent=2))
    for test,err in result.errors+result.failures:
        print(str(test)+'\n'+err[-2000:])
    return 0 if result.wasSuccessful() else 1


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--out',required=True,type=Path)
    a=parser.parse_args()
    raise SystemExit(main(a.out.resolve()))

