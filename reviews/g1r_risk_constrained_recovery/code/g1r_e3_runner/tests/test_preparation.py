from __future__ import annotations
from dataclasses import replace, asdict
import hashlib
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

import numpy as np

from .. import authorization_guard as guard
from ..config_loader import ROOT, load_frozen_config, load_public_model, load_config, E3Config
from ..online_proposal import OnlineInput, propose
from ..scenario_builder import ScenarioBuilder, OfflineTruth
from ..offline_evaluator import losses, evaluate
from ..storage import persist_proposal, write, digest, manifest, verify_manifest
from ..execution_state import Checkpoint, mark, require_resumable_or_complete, fail
from ..statistics_reporter import (worst_event_margin, summarize, resample_indices,
                                   interval, gate_decision)


def synthetic_rows(cfg):
    rows=[]
    for role,seeds in [('normal',cfg.normal_seeds),('paired_healthy',cfg.attack_seeds)]:
        for i,seed in enumerate(seeds):
            e0=np.array([.4+.01*i,.2]); pairing='synthetic:'+str(seed)
            for j,m in enumerate(cfg.methods):
                u0=np.array([.001*j,0.])
                metrics=losses(e0,np.zeros(2),u0,u0)
                rows.append({'seed':seed,'role':role,'event':None,'age':None,'method':m,
                    'pairing_sha256':pairing,'nonzero':bool(np.linalg.norm(u0)>0),**metrics})
            if role=='normal': continue
            for e in cfg.events:
                for age in cfg.ages:
                    delta=np.array([.15+.001*(e[1]-200)+.0001*age,.04])
                    for j,m in enumerate(cfg.methods):
                        u=np.array([.01+.004*j,.002]); u0=np.array([.001*j,0.])
                        rows.append({'seed':seed,'role':'attack','event':e,'age':age,'method':m,
                            'pairing_sha256':pairing,'nonzero':True,'saturated':False,
                            'proposal_status':'VALID','gate_status':'EXECUTED',**losses(e0,delta,u,u0)})
    return rows


class PreparationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg=load_config(); cls.public=load_public_model(cls.cfg.shared)
        cls.builder=ScenarioBuilder(cls.cfg,cls.public)
        cls.ctx=cls.builder.prepare(0,fixture=True)
        cls.clean=cls.builder.case(cls.ctx,'attack',fixture=True)
        cls.attack=cls.builder.case(cls.ctx,'attack',(0,200),64,fixture=True)
        cls.small=SimpleNamespace(methods=cls.cfg.methods,normal_seeds=tuple(range(10,14)),
            attack_seeds=tuple(range(20,24)),events=((0,200),(3,202)),ages=(32,64,96),
            shared=cls.cfg.shared,bootstrap_seed=123,bootstrap_resamples=1999)
        cls.synthetic=synthetic_rows(cls.small)
        cls.ix=np.array([[0,1,2,3],[3,2,1,0],[0,0,0,0],[1,1,2,2]],dtype=int)

    def test_online_whitelist(self):
        self.assertEqual(set(OnlineInput.__dataclass_fields__),{'z','frozen_public_model','threshold','method'})
        bad=SimpleNamespace(z=self.clean.z,true_state=(0,0))
        with self.assertRaises(ValueError): propose(bad)

    def test_input_12_finite(self):
        m=self.cfg.methods[0]
        for z in [(0,)*11,(float('nan'),)+(0,)*11]:
            with self.assertRaises(ValueError): propose(OnlineInput(z,self.public,0,m))

    def test_fixture_pairing_same_data_schedule(self):
        self.assertEqual(self.clean.truth.pairing_sha256,self.attack.truth.pairing_sha256)
        self.assertFalse(self.ctx.x.flags.writeable); self.assertFalse(self.ctx.y.flags.writeable)
        self.assertEqual(self.builder.generation_calls,[0])
        self.assertEqual(self.attack.truth.replay_source_time,136)
        self.assertEqual(self.attack.truth.cache_replacement_time,208)

    def test_fixture_truth_and_delta_time217(self):
        t=self.attack.truth
        np.testing.assert_array_equal(t.true_state,self.ctx.x[0,217])
        np.testing.assert_allclose(t.delta,np.array(t.attacked_estimate)-t.healthy_estimate,rtol=0,atol=0)
        np.testing.assert_array_equal(t.healthy_estimate,self.ctx.healthy_run.estimates[0,217,1])

    def test_fixture_all_eight_events_three_ages_pairing_and_timing(self):
        fingerprint=self.clean.truth.pairing_sha256
        for event in self.cfg.events:
            for age in self.cfg.ages:
                case=self.builder.case(self.ctx,'attack',event,age,fixture=True)
                self.assertEqual(case.truth.pairing_sha256,fingerprint)
                self.assertEqual(case.truth.replay_source_time,event[1]-age)
                self.assertEqual(case.truth.cache_replacement_time,event[1]+8)
                np.testing.assert_array_equal(case.truth.true_state,self.clean.truth.true_state)
                np.testing.assert_array_equal(case.truth.healthy_estimate,self.clean.truth.healthy_estimate)
                np.testing.assert_allclose(case.truth.delta,np.array(case.truth.attacked_estimate)-case.truth.healthy_estimate,atol=0,rtol=0)
        self.assertEqual(self.builder.generation_calls,[0])

    def test_fixture_refuses_formal_seeds(self):
        for seed in [141440000,141450000,141460000]:
            with self.assertRaises(PermissionError): self.builder.prepare(seed,fixture=True)

    def test_no_auth_refuses_data_generation(self):
        for seed in (self.cfg.normal_seeds[0],self.cfg.attack_seeds[0]):
            with self.assertRaises(guard.AuthorizationError): self.builder.prepare(seed)

    def test_correction_requires_persisted_proposals_and_all_methods(self):
        with tempfile.TemporaryDirectory() as d:
            for m in self.cfg.methods:
                clean=propose(OnlineInput(self.clean.z,self.public,self.cfg.shared.thresholds[m],m))
                attack=propose(OnlineInput(self.attack.z,self.public,self.cfg.shared.thresholds[m],m))
                c=persist_proposal(Path(d)/(m+'_c.json'),clean)
                a=persist_proposal(Path(d)/(m+'_a.json'),attack)
                r=evaluate(self.attack.truth,a,c,cap=.051261)
                np.testing.assert_allclose(r['corrected_attacked_estimate'],np.array(self.attack.truth.attacked_estimate)-attack.payload()['final_action'])
                self.assertAlmostEqual(r['attack_gain'],r['pollution_gain']+r['healthy_cross_term'],places=11)
                with self.assertRaises(TypeError): evaluate(self.attack.truth,attack,c,cap=.051261)

    def test_manual_losses(self):
        v=losses([1,2],[3,4],[.1,.2],[.05,.01])
        self.assertAlmostEqual(v['La'],52)
        self.assertAlmostEqual(v['L0'],5)
        self.assertAlmostEqual(v['La_u'],3.9**2+5.8**2)
        self.assertAlmostEqual(v['L0_u'],.95**2+1.99**2)
        self.assertAlmostEqual(v['net_gain'],v['La']-v['La_u']-(v['L0']-v['L0_u']))

    def test_zero_actions_preserved(self):
        v=losses([1,2],[3,4],[0,0],[0,0])
        self.assertEqual(v['attack_gain'],0); self.assertEqual(v['net_gain'],0)
        cfg=self.small; rows=synthetic_rows(cfg)
        for row in rows:
            row.update(losses([.4,.2],[.2,0] if row['role']=='attack' else [0,0],[0,0],[0,0]))
            row.update(nonzero=False,saturated=False,proposal_status='SOLVER_REJECT',gate_status='GATE_REJECT')
        result=summarize(cfg,rows,indices=self.ix)
        self.assertEqual(result['n_attack_seeds'],4)
        self.assertEqual(result['per_event_age']['0:200@64'][cfg.methods[2]]['zero_action_rate'],1)

    def test_whole_seed_indices(self):
        ix=resample_indices(12345,4,19)
        self.assertEqual(ix.shape,(19,4)); np.testing.assert_array_equal(ix,resample_indices(12345,4,19))
        cube=np.arange(4*2*3*3).reshape(4,2,3,3)
        for b in range(len(ix)):
            for j in range(4): np.testing.assert_array_equal(cube[ix][b,j],cube[ix[b,j]])

    def test_worst_event_not_mean_of_max(self):
        b=np.array([[10.,0],[0,10.]]); s=np.ones((2,2)); ix=np.array([[0,1],[0,0]])
        point,boot=worst_event_margin(b,s,ix)
        self.assertAlmostEqual(point,.99*5-1)
        np.testing.assert_allclose(boot,[.99*5-1,.99*10-1])

    def test_confirmatory_two_bounds(self):
        result=summarize(self.small,self.synthetic,indices=self.ix)
        self.assertEqual(len(result['confirmatory_worst_event_age64']),2)
        for value in result['confirmatory_worst_event_age64'].values():
            self.assertIn('lower_97_5',value)
        self.assertEqual(result['bootstrap_resamples'],4)

    def test_quantile_definition(self):
        data=np.arange(100.)
        self.assertEqual(interval(data),[2.475,96.52499999999999])
        self.assertAlmostEqual(float(np.quantile(data,.025,method='linear')),2.475)

    def test_synthetic_point_mse_manual(self):
        result=summarize(self.small,self.synthetic,indices=self.ix)
        rows=[r for r in self.synthetic if r['role']=='attack' and r['event']==(0,200) and r['age']==64 and r['method']==self.cfg.methods[2]]
        self.assertAlmostEqual(result['per_event_age']['0:200@64'][self.cfg.methods[2]]['mse'],sum(r['La_u'] for r in rows)/4)

    def test_duplicate_missing_rows_fail(self):
        for rows in [self.synthetic[:-1],self.synthetic+[self.synthetic[0]]]:
            with self.assertRaises(ValueError): summarize(self.small,rows,indices=self.ix)

    def test_pairing_mismatch_fails(self):
        rows=[dict(r) for r in self.synthetic]; rows[-1]['pairing_sha256']='wrong'
        with self.assertRaises(ValueError): summarize(self.small,rows,indices=self.ix)

    def test_formal_statistics_requires_e3_authorization(self):
        with self.assertRaises(guard.AuthorizationError): summarize(self.cfg,[],formal=True)

    def test_missing_authorization(self):
        with self.assertRaises(guard.AuthorizationError): guard.authorize(self.cfg,None)

    def test_e2_authorization_refused_without_file_creation(self):
        path=Mock(spec=Path); path.is_file.return_value=True
        path.read_text.return_value=json.dumps({'authorized':True,'scope':'E2'})
        with self.assertRaises(guard.AuthorizationError): guard.authorize(self.cfg,path)

    def test_template_unauthorized(self):
        path=Path(guard.__file__).parent/'authorization_template.json'
        self.assertFalse(json.loads(path.read_text())['authorized'])
        with self.assertRaises(guard.AuthorizationError): guard.authorize(self.cfg,path)

    def test_e2_receipt_not_e3(self):
        from ...g1r_e2_runner.authorization_guard import authorize
        receipt=authorize('dry_run',self.cfg.shared)
        with self.assertRaises(guard.AuthorizationError): guard.require(self.cfg,receipt)

    def test_changed_binding_invalidates_prior_e3_record(self):
        expected=guard.bindings(self.cfg)
        path=Mock(spec=Path); path.is_file.return_value=True
        path.read_text.return_value=json.dumps({'authorized':True,'scope':'E3','owner':'fixture-only',
            'authorization_id':'IN_MEMORY_ONLY','bindings':expected})
        original=guard.sha256_file
        with patch.object(guard,'sha256_file',side_effect=lambda p:'a'*64 if p is path else original(p)):
            receipt=guard.authorize(self.cfg,path)
        with patch.object(guard,'bindings',return_value={**expected,'final_code_sha256':'b'*64}):
            with self.assertRaises(guard.AuthorizationError): guard.require(self.cfg,receipt)

    def test_live_config_or_seed_scan_drift_invalidates_bindings(self):
        original=guard.sha256_file
        for target in (guard.PREP,guard.SCAN):
            with patch.object(guard,'sha256_file',side_effect=lambda p:'d'*64 if p==target else original(p)):
                with self.assertRaises(guard.AuthorizationError): guard.bindings(self.cfg)

    def test_persisted_record_tamper_fails(self):
        with tempfile.TemporaryDirectory() as d:
            m=self.cfg.methods[0]; record=propose(OnlineInput(self.clean.z,self.public,self.cfg.shared.thresholds[m],m))
            ticket=persist_proposal(Path(d)/'p.json',record)
            ticket.path.write_bytes(b'{}')
            with self.assertRaises(ValueError): ticket.read()

    def test_checkpoint_resume_deduplicates(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); p=root/'seed.json'; write(p,{'seed':0})
            cp=Checkpoint(root,{'fixture':True}); cp.complete('fixture:0',[p])
            new=Checkpoint(root,{'fixture':True}); self.assertTrue(new.done('fixture:0'))
            with self.assertRaises(ValueError): new.complete('fixture:0',[p])

    def test_checkpoint_corruption_fails(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); p=root/'seed.json'; write(p,{'seed':0}); cp=Checkpoint(root,{}); cp.complete('fixture:0',[p])
            p.write_text('{}')
            with self.assertRaises(ValueError): Checkpoint(root,{})

    def test_checkpoint_identity_change_fails(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); p=root/'seed.json'; write(p,{'seed':0}); cp=Checkpoint(root,{'owner':'A'}); cp.complete('fixture:0',[p])
            with self.assertRaises(ValueError): Checkpoint(root,{'owner':'B'})

    def test_immutable_write_preserves_evidence(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'r.json'; write(p,{'v':1})
            with self.assertRaises(ValueError): write(p,{'v':2})
            self.assertEqual(json.loads(p.read_text()),{'v':1})

    def test_manifest_detects_damage(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); p=root/'r.json'; write(p,{'v':1}); manifest(root,{'fixture':True}); verify_manifest(root)
            p.write_text('{}')
            with self.assertRaises(ValueError): verify_manifest(root)

    def test_execution_fault_and_interruption_classification(self):
        for exc,expected in [(RuntimeError('fixture fault'),'ABORTED_INCONCLUSIVE'),(KeyboardInterrupt(),'INTERRUPTED_RESUMABLE')]:
            with tempfile.TemporaryDirectory() as d:
                root=Path(d); write(root/'config.json',{'experiment_config_sha256':self.cfg.config_sha256})
                self.assertEqual(fail(root,exc,{'seed':0,'scope':'fixture'}),expected)
                self.assertEqual(json.loads((root/'run_status.json').read_text())['status'],expected)
                if expected=='ABORTED_INCONCLUSIVE':
                    with self.assertRaises(RuntimeError): require_resumable_or_complete(root,self.cfg)
                else: require_resumable_or_complete(root,self.cfg)

    def test_advantage_only_healthy_is_no_mechanism_go(self):
        margins={'hard':{'point':.1,'lower_97_5':.02},'soft':{'point':.1,'lower_97_5':.02}}
        self.assertEqual(gate_decision(.1,margins,{'hard':{'point':-.01,'interval_95':[-.1,-.001]}}),'NO_MECHANISM_GO')
        self.assertEqual(gate_decision(.1,margins,{'hard':{'point':.01,'interval_95':[-.1,.1]}}),'INCONCLUSIVE')

    def test_no_performance_go_below_one_percent(self):
        self.assertEqual(gate_decision(.009,{},{}),'NO_GO_PERFORMANCE')

    def test_saved_e2_proposals_equal_online_adapter(self):
        cfg=self.cfg; run=cfg.base/'results/g1r_e2_run_20261116_001'
        path=run/'seed_shards/attack_batch_00_seed_141430000_online.jsonl'
        saved=[json.loads(line)['proposal'] for line in path.read_text().splitlines()]
        for p in saved[:3]:
            record=propose(OnlineInput(tuple(p['z']),self.public,p['threshold'],p['method']))
            self.assertEqual(record.payload(),p)

    def test_independent_coverage_rank_deficient(self):
        from ...audit_e2_independent_coverage import independent_cover
        O=np.zeros((12,2)); O[:2]=np.eye(2)
        model={'Sigma_eta':np.eye(12),'t_Q':4.,'t_r':10.,'events':[
            {'edge':0,'r':1,'O':O,'G':np.diag([1.,0.])}]}
        self.assertTrue(independent_cover(O@np.array([2.,3.]),[2.,0.],model)[0])
        self.assertFalse(independent_cover(O@np.array([2.,3.]),[2.,.1],model)[0])

    def test_runner_missing_auth_creates_no_directory(self):
        from ..batch_runner import BatchRunner
        with tempfile.TemporaryDirectory() as d:
            out=Path(d)/'must_not_exist'
            with self.assertRaises(guard.AuthorizationError): BatchRunner(self.cfg,None,out).run()
            self.assertFalse(out.exists())

    def _synthetic_runner_setup(self):
        # All scenario data below are manual numeric fixtures, no generator call.
        from .. import batch_runner as br
        cfg=SimpleNamespace(shared=self.cfg.shared,methods=self.cfg.methods,events=self.cfg.events,
            ages=self.cfg.ages,normal_seeds=(101,),attack_seeds=(201,),dependencies={},config_sha256='fixture-only')
        cfg.bootstrap_seed=42; cfg.bootstrap_resamples=3
        parent=self
        class FixtureBuilder:
            calls=[]
            def __init__(self,*args): pass
            def prepare(self,seed):
                self.calls.append(seed); return SimpleNamespace(seed=seed)
            def case(self,ctx,group,event=None,age=None):
                x=np.array([0.,0.]); h=np.array([.4,.2]); delta=np.zeros(2) if event is None else np.array([.2,.1])
                truth=OfflineTruth(ctx.seed,group,event,age,tuple(x),tuple(h),tuple(h+delta),tuple(delta),
                    parent.clean.z,'manual-fixture-'+str(ctx.seed),None if event is None else event[1]-age,
                    age,None if event is None else event[1]+8)
                return SimpleNamespace(z=parent.clean.z if event is None else parent.attack.z,truth=truth)
        receipt=SimpleNamespace(authorization_id='IN_MEMORY_FIXTURE',owner='synthetic-test',file_sha256='c'*64,bindings=())
        def synthetic_stats(c,rows,**kwargs):
            return summarize(c,rows,indices=np.array([[0],[0]]),formal=False)
        return br,cfg,FixtureBuilder,receipt,synthetic_stats

    def test_independent_risk_and_bootstrap_reconstructed_from_vectors(self):
        from ..independent_statistics import compare
        rows=[]
        for r in self.synthetic:
            row=dict(r); i=(row['seed']-20) if row['role']!='normal' else row['seed']-10
            e0=np.array([.4+.01*i,.2]); j=self.cfg.methods.index(row['method'])
            delta=np.zeros(2) if row['role']!='attack' else np.array([.15+.001*(row['event'][1]-200)+.0001*row['age'],.04])
            row.update(true_state=[0.,0.],attacked_estimate=(e0+delta).tolist(),u=([.01+.004*j,.002] if row['role']=='attack' else [.001*j,0.]))
            rows.append(row)
        result=summarize(self.small,rows,indices=self.ix)
        audit=compare(self.small,rows,self.ix,result)
        self.assertLess(audit['max_absolute_difference'],1e-12)

    def test_runner_complete_synthetic_and_independent_recompute(self):
        br,cfg,Builder,receipt,stats=self._synthetic_runner_setup()
        with tempfile.TemporaryDirectory() as d,patch.object(br,'require'),patch.object(br,'public_model',return_value=self.public),patch.object(br,'ScenarioBuilder',Builder),patch.object(br,'summarize',side_effect=stats):
            root=Path(d)/'synthetic'; result=br.BatchRunner(cfg,receipt,root).run()
            self.assertEqual(result['scope'],'SYNTHETIC_DETERMINISTIC_ONLY')
            self.assertEqual(len(list((root/'online').glob('*.json'))),78)
            self.assertEqual(len(json.loads((root/'seeds/attack_201.json').read_text())['rows']),75)
            self.assertEqual(json.loads((root/'run_status.json').read_text())['status'],'COMPLETED')
            verify_manifest(root)

    def test_runner_execution_exception_aborts_keeps_proposals(self):
        br,cfg,Builder,receipt,stats=self._synthetic_runner_setup()
        with tempfile.TemporaryDirectory() as d,patch.object(br,'require'),patch.object(br,'public_model',return_value=self.public),patch.object(br,'ScenarioBuilder',Builder),patch.object(br,'evaluate',side_effect=RuntimeError('manual evaluator fault')):
            root=Path(d)/'synthetic'
            with self.assertRaises(RuntimeError): br.BatchRunner(cfg,receipt,root).run()
            self.assertEqual(json.loads((root/'run_status.json').read_text())['status'],'ABORTED_INCONCLUSIVE')
            self.assertEqual(len(list((root/'online').glob('*.json'))),3)
            self.assertFalse((root/'statistics.json').exists())
            if (root/'checkpoint.json').exists(): self.assertFalse(json.loads((root/'checkpoint.json').read_text())['payload']['completed'])

    def test_runner_interrupt_resume_skips_completed_seed(self):
        br,cfg,Builder,receipt,stats=self._synthetic_runner_setup()
        original=Builder.prepare; interrupted=[False]
        def prepare(builder,seed):
            if seed==201 and not interrupted[0]:
                interrupted[0]=True; raise KeyboardInterrupt()
            return original(builder,seed)
        with tempfile.TemporaryDirectory() as d,patch.object(br,'require'),patch.object(br,'public_model',return_value=self.public),patch.object(br,'ScenarioBuilder',Builder),patch.object(br,'summarize',side_effect=stats),patch.object(Builder,'prepare',prepare):
            root=Path(d)/'synthetic'
            with self.assertRaises(KeyboardInterrupt): br.BatchRunner(cfg,receipt,root).run()
            self.assertEqual(json.loads((root/'run_status.json').read_text())['status'],'INTERRUPTED_RESUMABLE')
            old=digest(root/'seeds/normal_101.json')
            result=br.BatchRunner(cfg,receipt,root,resume=True).run()
            self.assertEqual(digest(root/'seeds/normal_101.json'),old)
            self.assertEqual(Builder.calls.count(101),1)
            self.assertEqual(result['scope'],'SYNTHETIC_DETERMINISTIC_ONLY')

    def test_runner_disk_write_exception_aborts(self):
        br,cfg,Builder,receipt,stats=self._synthetic_runner_setup()
        with tempfile.TemporaryDirectory() as d,patch.object(br,'require'),patch.object(br,'public_model',return_value=self.public),patch.object(br,'ScenarioBuilder',Builder),patch.object(br,'persist_proposal',side_effect=OSError('injected disk failure')):
            root=Path(d)/'synthetic'
            with self.assertRaises(OSError): br.BatchRunner(cfg,receipt,root).run()
            self.assertEqual(json.loads((root/'run_status.json').read_text())['status'],'ABORTED_INCONCLUSIVE')
            self.assertFalse((root/'statistics.json').exists())

    def test_runner_simulation_failure_aborts_before_completion(self):
        br,cfg,Builder,receipt,stats=self._synthetic_runner_setup()
        with tempfile.TemporaryDirectory() as d,patch.object(br,'require'),patch.object(br,'public_model',return_value=self.public),patch.object(br,'ScenarioBuilder',Builder),patch.object(Builder,'prepare',side_effect=RuntimeError('injected simulation failure')):
            root=Path(d)/'synthetic'
            with self.assertRaises(RuntimeError): br.BatchRunner(cfg,receipt,root).run()
            self.assertEqual(json.loads((root/'run_status.json').read_text())['status'],'ABORTED_INCONCLUSIVE')
            self.assertFalse((root/'statistics.json').exists())

    def test_saved_loss_tamper_is_detected(self):
        from ..integrity_checker import validate_rows
        with tempfile.TemporaryDirectory() as d:
            m=self.cfg.methods[0]; record=propose(OnlineInput(self.attack.z,self.public,self.cfg.shared.thresholds[m],m))
            ticket=persist_proposal(Path(d)/'p.json',record)
            row=evaluate(self.attack.truth,ticket,ticket,cap=.051261)
            validate_rows(self.cfg,[row]); row['La_u']+=.001
            with self.assertRaises(ValueError): validate_rows(self.cfg,[row])


if __name__=='__main__': unittest.main()
