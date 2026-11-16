"""E2-P0 regression. Synthetic identifiers only; no valid authorization files."""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

import numpy as np

from .. import authorization_guard as auth, environment_guard as env
from .. import batch_runner as batch, offline_evaluator as offline
from .. import online_proposal as online, statistics_reporter as statistics
from ..config_loader import BASE, canonical_sha256, load_frozen_config, load_public_model
from ..execution_state import (ExecutionAborted, emergency_marker, require_not_aborted)
from ..integrity_checker import validate_batch_rows, IntegrityError
from ..result_writer import ResultWriter
from ..scenario_builder import OfflineTruth, ScenarioCase

EVIDENCE_DIR = None
MODULE = 'reviews.g1r_risk_constrained_recovery.code.g1r_e2_runner'


class PrelaunchIntegrityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = load_frozen_config()
        cls.public = load_public_model(cls.config)
        cls.runtime = env.current_environment()
        cls.debug_file = BASE/'results/g1r_e2_status_resolution_20261115_r01/cached_debug_features.npz'
        with np.load(cls.debug_file, allow_pickle=False) as data:
            cls.z = data['replay_packet_141400001'].copy()

    @contextmanager
    def workspace(self):
        if EVIDENCE_DIR is None:
            with tempfile.TemporaryDirectory() as name:
                yield Path(name)/'fixture_run'
        else:
            # Keep deterministic fixture paths below Windows path limits.
            case_id = hashlib.sha256(self._testMethodName.encode()).hexdigest()[:6]
            path = Path(EVIDENCE_DIR)/'f'/case_id
            path.parent.mkdir(parents=True, exist_ok=True)
            yield path

    def _config(self):
        return replace(self.config, normal_seeds=(710000,710001), attack_seeds=(810000,),
                       ages=(64,), events=(self.config.main_event,))

    def _case(self, group, seed, event=None, age=None, **changes):
        normal = group == 'normal'
        truth = OfflineTruth(
            'normal' if normal else 'replay', seed,
            normal or (event == self.config.main_event and age == 64), event, age,
            None if normal else event[1]-age, age,
            None if normal else event[1]+8,
            None if normal else event[1]+1, None if normal else event[1]+1,
            None if normal else (0.1,-0.1), (0.2,0.1), None if normal else (0.3,0.0),
            'PASS', f'{group}:{seed}')
        truth = replace(truth, **changes)
        inp = online.build_online_input(self.z, self.public,
                                       self.config.thresholds[self.config.methods[0]], self.config.methods[0])
        return ScenarioCase(inp, truth)

    def _provider(self):
        provider = Mock()
        provider.build_formal_normal.side_effect = lambda seed, receipt: self._case('normal',seed)
        provider.prepare_formal_attack_seed.return_value = 'fixed_context_no_generation'
        provider.build_formal_replay.side_effect = lambda seed, event, age, receipt, ctx: self._case('attack',seed,event,age)
        return provider

    def _runner(self, directory):
        c=self._config()
        # Never mint a formal receipt, nor write a valid authorization file.
        return batch.BatchRunner(c, auth.authorize('dry_run', c), directory)

    def _assert_abort(self, directory, provider=None, group='normal', extra_patch=None):
        runner=self._runner(directory)
        provider=self._provider() if provider is None else provider
        seed=710000 if group=='normal' else 810000
        plan=((group,0,(seed,)),)
        with patch.object(runner,'_batch_plan',return_value=plan), patch.object(batch,'ScenarioBuilder',return_value=provider):
            if extra_patch is None:
                with self.assertRaises(ExecutionAborted): runner._execute_checked_run()
            else:
                with extra_patch, self.assertRaises(ExecutionAborted): runner._execute_checked_run()
        state=json.loads((directory/'run_status.json').read_text())
        self.assertEqual(state['status'],'ABORTED_INCONCLUSIVE')
        records=list((directory/'execution_failures').glob('*.json'))
        self.assertTrue(records)
        error=json.loads(records[0].read_text())
        expected = {
            'test_normal_simulator_exception_aborts': 'injected Yang normal exception',
            'test_replay_simulator_exception_aborts': 'injected Yang Replay exception',
            'test_data_generation_exception_aborts': 'injected data generator exception',
            'test_replay_source_mismatch_aborts': 'actual Replay source/age/send mismatch',
            'test_replay_age_mismatch_aborts': 'actual Replay source/age/send mismatch',
            'test_replay_cache_replacement_mismatch_aborts': 'incorrect cache replacement time',
            'test_nonpass_scenario_never_becomes_completed_seed': 'scenario failed before proposal',
            'test_nonfinite_innovation_aborts': 'twelve finite innovations',
            'test_unexpected_frozen_proposal_exception_not_swallowed': 'unexpected proposal defect',
            'test_online_write_failure_aborts': 'injected disk write error',
            'test_offline_evaluator_failure_aborts': 'injected offline evaluator defect',
            'test_coverage_program_exception_aborts_instead_of_uncovered': 'unexpected membership defect',
            'test_true_impact_required_even_if_coverage_false': 'finite true impact',
            'test_partial_online_records_survive_later_method_failure': 'second method failure',
            'test_checkpoint_write_failure_never_completes_seed': 'checkpoint write failure',
        }.get(self._testMethodName)
        if expected is not None:
            self.assertIn(expected, error['message'])
        self.assertTrue(error['traceback'])
        self.assertIn('Traceback',error['traceback'])
        self.assertEqual(error['context']['seed'],seed)
        checkpoint=directory/'checkpoint.json'
        if checkpoint.exists():
            state=json.loads(checkpoint.read_text())
            self.assertNotIn(f'{group}:{seed}',state['completed_seeds'])
            self.assertFalse(state['completed_batches'])
        self.assertFalse((directory/'gate_counts.json').exists())
        with self.assertRaises(ExecutionAborted): require_not_aborted(directory)
        return error

    def _environment_failure(self, field):
        actual=dict(self.runtime)
        if field=='blas_configuration': actual[field]+='CHANGED BLAS/LAPACK ABI\n'
        else: actual[field]='999.0.test'
        with self.workspace() as out:
            runner=self._runner(out)
            with patch.object(env,'current_environment',return_value=actual), \
                 patch.object(batch,'ScenarioBuilder',side_effect=AssertionError('must not construct model')) as builder:
                with self.assertRaises(env.EnvironmentMismatch): env.verify_environment(self.config)
                with self.assertRaises(env.EnvironmentMismatch): auth.authorization_bindings(self.config)
                with self.assertRaises(env.EnvironmentMismatch): runner.run_formal_e2()
                builder.assert_not_called()
            self.assertFalse(out.exists())

    def test_python_mismatch_refused_before_output(self): self._environment_failure('python')
    def test_numpy_mismatch_refused_before_output(self): self._environment_failure('numpy')
    def test_scipy_mismatch_refused_before_output(self): self._environment_failure('scipy')
    def test_blas_mismatch_refused_before_output(self): self._environment_failure('blas_configuration')

    def test_original_calibration_and_r12_and_live_environment_match(self):
        self.assertTrue(env.verify_environment(self.config)['match'])
        self.assertEqual(dict(self.config.environment_fingerprint),env.reference_environment(self.config.base))
        self.assertEqual(canonical_sha256(self.config.contract_dict()),self.config.runner_config_sha256)

    def test_blas_normalization_preserves_meaningful_configuration(self):
        self.assertEqual(env.normalize_blas('a\r\nb\r\n'),'a\nb\n')
        self.assertNotEqual(env.fingerprint(self.runtime), env.fingerprint({**self.runtime,'blas_configuration':self.runtime['blas_configuration'].replace('OpenBLAS','ChangedBLAS')}))

    def test_old_five_bindings_invalid_and_environment_is_bound(self):
        old={'final_code_sha256':'b8a0b0e7905fd6d99e491d689ea9add53454130d04eacb02185a749a61d2ccec',
             'protocol_sha256':self.config.protocol_sha256,'calibration_thresholds_sha256':self.config.thresholds_sha256,
             'seed_list_sha256':'8dd8d513d0bcff0ee80b5aa3dd797a2f49df2e5655aba40d2024645e37ddd946',
             'experiment_config_sha256':'34f9404f6f53fe9c40d630bacc194e15d268de4cbe921cf1430c297a783f33c2'}
        new=auth.authorization_bindings(self.config)
        self.assertEqual(set(new),set(old))
        self.assertNotEqual(new['experiment_config_sha256'],old['experiment_config_sha256'])
        for field in ('protocol_sha256','calibration_thresholds_sha256','seed_list_sha256'):
            self.assertEqual(new[field],old[field])
        virtual=Mock(); virtual.is_file.return_value=True
        virtual.read_text.return_value=json.dumps({'scope':'E2','authorized':True,'owner':'test','authorization_id':'virtual','bindings':old})
        with self.assertRaises(auth.AuthorizationError): auth.authorize('formal_e2',self.config,virtual)
        altered=self.config.contract_dict()
        altered['environment_fingerprint']['python']='different'
        self.assertNotEqual(canonical_sha256(altered),self.config.runner_config_sha256)
        # A receipt prepared in memory becomes invalid after the live environment changes.
        virtual.read_text.return_value=json.dumps({'scope':'E2','authorized':True,'owner':'test','authorization_id':'virtual','bindings':new})
        original_sha=auth.sha256_file
        with patch.object(auth,'sha256_file',side_effect=lambda p: 'memory-only' if p is virtual else original_sha(p)):
            receipt=auth.authorize('formal_e2',self.config,virtual)
        with patch.object(env,'current_environment',return_value={**self.runtime,'python':'wrong'}):
            with self.assertRaises(env.EnvironmentMismatch): auth.require_formal_e2(receipt,self.config)

    def test_reference_ambiguity_is_rejected(self):
        with patch.object(env,'REFERENCE_SHA256',{env.CALIBRATION:'0'*64,env.R12:'0'*64}):
            with self.assertRaises(env.EnvironmentMismatch): env.reference_environment(self.config.base)

    def test_normal_simulator_exception_aborts(self):
        provider=self._provider(); provider.build_formal_normal.side_effect=RuntimeError('injected Yang normal exception')
        with self.workspace() as out: self._assert_abort(out,provider)

    def test_replay_simulator_exception_aborts(self):
        provider=self._provider(); provider.build_formal_replay.side_effect=RuntimeError('injected Yang Replay exception')
        with self.workspace() as out: self._assert_abort(out,provider,'attack')

    def test_data_generation_exception_aborts(self):
        provider=self._provider(); provider.prepare_formal_attack_seed.side_effect=RuntimeError('injected data generator exception')
        with self.workspace() as out: self._assert_abort(out,provider,'attack')

    def test_model_builder_exception_aborts(self):
        with self.workspace() as out:
            runner=self._runner(out)
            with patch.object(runner,'_batch_plan',return_value=(('normal',0,(710000,)),)), patch.object(batch,'ScenarioBuilder',side_effect=RuntimeError('injected model construction')):
                with self.assertRaises(ExecutionAborted): runner._execute_checked_run()
            state=json.loads((out/'run_status.json').read_text())
            self.assertEqual(state['status'],'ABORTED_INCONCLUSIVE')
            self.assertFalse((out/'gate_counts.json').exists())

    def test_replay_source_mismatch_aborts(self):
        provider=self._provider()
        provider.build_formal_replay.side_effect=lambda seed,e,a,receipt,ctx:self._case('attack',seed,e,a,replay_source_time=e[1]-a+1)
        with self.workspace() as out: self._assert_abort(out,provider,'attack')

    def test_replay_age_mismatch_aborts(self):
        provider=self._provider()
        provider.build_formal_replay.side_effect=lambda seed,e,a,receipt,ctx:self._case('attack',seed,e,a,actual_replay_age=a+1)
        with self.workspace() as out: self._assert_abort(out,provider,'attack')

    def test_replay_cache_replacement_mismatch_aborts(self):
        provider=self._provider()
        provider.build_formal_replay.side_effect=lambda seed,e,a,receipt,ctx:self._case('attack',seed,e,a,cache_replacement_time=e[1]+9)
        with self.workspace() as out: self._assert_abort(out,provider,'attack')

    def test_nonpass_scenario_never_becomes_completed_seed(self):
        provider=self._provider()
        provider.build_formal_normal.side_effect=lambda seed,receipt:self._case('normal',seed,simulation_status='FAIL:injected')
        with self.workspace() as out: self._assert_abort(out,provider)

    def test_nonfinite_innovation_aborts(self):
        provider=self._provider(); case=self._case('normal',710000)
        bad=replace(case.online_input,z=(float('nan'),)*12)
        provider.build_formal_normal.return_value=replace(case,online_input=bad)
        provider.build_formal_normal.side_effect=None
        with self.workspace() as out: self._assert_abort(out,provider)

    def test_unexpected_frozen_proposal_exception_not_swallowed(self):
        with self.workspace() as out:
            error=self._assert_abort(out,extra_patch=patch.object(offline.v2_estimators,'propose',side_effect=RuntimeError('unexpected proposal defect')))
            self.assertEqual(error['exception_type'],'RuntimeError')
            self.assertIn('unexpected proposal defect',error['traceback'])
            self.assertFalse(list((out/'seed_shards').glob('*offline.csv')))

    def test_online_write_failure_aborts(self):
        with self.workspace() as out:
            self._assert_abort(out,extra_patch=patch.object(ResultWriter,'write_online_seed',side_effect=OSError('injected disk write error')))

    def test_offline_evaluator_failure_aborts(self):
        with self.workspace() as out:
            self._assert_abort(out,extra_patch=patch.object(batch,'evaluate',side_effect=RuntimeError('injected offline evaluator defect')))
            self.assertTrue(list((out/'seed_shards').glob('*online.jsonl')))

    def test_coverage_program_exception_aborts_instead_of_uncovered(self):
        with self.workspace() as out:
            self._assert_abort(out,group='attack',extra_patch=patch.object(offline,'set_union_covers',side_effect=RuntimeError('unexpected membership defect')))

    def test_true_impact_required_even_if_coverage_false(self):
        provider=self._provider()
        provider.build_formal_replay.side_effect=lambda seed,e,a,receipt,ctx:self._case('attack',seed,e,a,true_impact=(float('nan'),0.0))
        with self.workspace() as out: self._assert_abort(out,provider,'attack')

    def _rejection_rows(self,status,group='normal'):
        seed=710000 if group=='normal' else 810000
        case=self._case(group,seed,None if group=='normal' else (0,200),None if group=='normal' else 64)
        rows=[]
        for method in self.config.methods:
            cert={'zero_or_unresolved':True} if status=='ZERO_OR_UNRESOLVED' else {'stage':'center','reason':'returned rejection'}
            raw_status='VALID' if status in ('ZERO_OR_UNRESOLVED','ZERO_PROPOSAL','GATE_REJECT') else status
            raw=offline.v2_estimators.Proposal(method,np.zeros(2),0.0,raw_status,None,cert)
            with patch.object(offline.v2_estimators,'propose',return_value=raw):
                record=online.propose(online.build_online_input(self.z,self.public,self.config.thresholds[method],method))
            row=offline.evaluate(record,case.offline_truth,self.public)
            rows.append(row)
        validate_batch_rows(self._config(),group,(seed,),rows)
        self.assertTrue(all(r['set_action_norm']==0.0 for r in rows))
        return rows

    def test_returned_solver_reject_is_a_legitimate_zero_action(self):
        rows=self._rejection_rows('SOLVER_REJECT','attack')
        self.assertTrue(all(r['proposal_status']=='SOLVER_REJECT' for r in rows))

    def test_zero_or_unresolved_is_preserved(self):
        rows=self._rejection_rows('ZERO_OR_UNRESOLVED','attack')
        self.assertTrue(all(r['proposal_status']=='ZERO_OR_UNRESOLVED' for r in rows))

    def test_all_returned_algorithm_rejection_codes_are_preserved(self):
        for status in ('INPUT_INVALID','MODEL_INVALID','EMPTY_UNION','SOLVER_REJECT','ZERO_OR_UNRESOLVED','ZERO_PROPOSAL','GATE_REJECT'):
            with self.subTest(status=status): self._rejection_rows(status)

    def test_gate_reject_remains_in_normal_denominator(self):
        from ..tests.test_runner import RunnerAcceptanceTests
        # Pure synthetic 20-batch CSV test, no generator and no official IDs.
        test=RunnerAcceptanceTests('test_independent_twenty_csv_statistics_recompute_on_synthetic_rows')
        test.config=self.config
        test.test_independent_twenty_csv_statistics_recompute_on_synthetic_rows()

    def test_invalid_vectors_and_nonpass_rows_are_rejected(self):
        rows=self._rejection_rows('SOLVER_REJECT','attack')
        for field,bad in [('simulation_status','FAIL'),('set_action_norm',float('nan')),
                          ('proposal_vector_json','[NaN,0]'),('final_action_json','[0,Infinity]'),
                          ('true_impact_x',None),('true_impact_y',float('inf')),
                          ('replay_source_time',137),('actual_replay_age',65),('cache_replacement_time',209)]:
            mutated=[dict(r) for r in rows]; mutated[0][field]=bad
            with self.subTest(field=field), self.assertRaises((IntegrityError,ValueError,TypeError)):
                validate_batch_rows(self._config(),'attack',(810000,),mutated)

    def test_aborted_run_cannot_publish_or_recompute_gate(self):
        provider=self._provider(); provider.build_formal_normal.side_effect=RuntimeError('abort fixture')
        with self.workspace() as out:
            self._assert_abort(out,provider)
            with self.assertRaises(ExecutionAborted): statistics.summarize_rows(self.config,[],run_dir=out)
            with self.assertRaises(ExecutionAborted):
                statistics.independent_recompute(self.config,tuple(out/f'n{i}.csv' for i in range(10)),tuple(out/f'a{i}.csv' for i in range(10)))
            with patch.object(batch,'ScenarioBuilder') as b:
                with self.assertRaises(ExecutionAborted): self._runner(out)._execute_checked_run()
                b.assert_not_called()

    def test_interrupt_resume_keeps_completed_seed_hashes(self):
        provider=self._provider()
        def normal(seed,receipt):
            if seed==710001: raise KeyboardInterrupt('simulated process interruption')
            return self._case('normal',seed)
        provider.build_formal_normal.side_effect=normal
        with self.workspace() as out:
            runner=self._runner(out)
            plan=(('normal',0,(710000,710001)),)
            with patch.object(runner,'_batch_plan',return_value=plan),patch.object(batch,'ScenarioBuilder',return_value=provider):
                with self.assertRaises(KeyboardInterrupt): runner._execute_checked_run()
            state=json.loads((out/'run_status.json').read_text())
            self.assertEqual(state['status'],'INTERRUPTED_RESUMABLE')
            ledger=json.loads((out/'checkpoint.json').read_text())
            self.assertIn('normal:710000',ledger['completed_seeds'])
            self.assertNotIn('normal:710001',ledger['completed_seeds'])
            hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (out/'seed_shards').iterdir()}
            provider.build_formal_normal.reset_mock()
            resumed=self._runner(out)
            with patch.object(resumed,'_batch_plan',return_value=plan),patch.object(batch,'ScenarioBuilder',return_value=provider):
                with self.assertRaises(KeyboardInterrupt): resumed._execute_checked_run()
            self.assertEqual([c.args[0] for c in provider.build_formal_normal.call_args_list],[710001])
            self.assertEqual(hashes,{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (out/'seed_shards').iterdir()})
            self.assertFalse((out/'gate_counts.json').exists())

    def test_corrupt_checkpoint_aborts_and_is_preserved(self):
        provider=self._provider(); provider.build_formal_normal.side_effect=KeyboardInterrupt('interrupt before seed completion')
        with self.workspace() as out:
            runner=self._runner(out)
            with patch.object(runner,'_batch_plan',return_value=(('normal',0,(710000,)),)), patch.object(batch,'ScenarioBuilder',return_value=provider):
                with self.assertRaises(KeyboardInterrupt): runner._execute_checked_run()
            (out/'checkpoint.json').write_text('{broken',encoding='utf-8')
            resumed=self._runner(out)
            with patch.object(resumed,'_batch_plan',return_value=(('normal',0,(710000,)),)), self.assertRaises(ExecutionAborted):
                resumed._execute_checked_run()
            self.assertEqual((out/'checkpoint.json').read_text(),'{broken')
            self.assertEqual(json.loads((out/'run_status.json').read_text())['status'],'ABORTED_INCONCLUSIVE')

    def test_partial_online_records_survive_later_method_failure(self):
        original=batch.propose
        count=0
        def fail_second(inp):
            nonlocal count
            count+=1
            if count==2: raise RuntimeError('second method failure')
            return original(inp)
        with self.workspace() as out:
            self._assert_abort(out,extra_patch=patch.object(batch,'propose',side_effect=fail_second))
            self.assertEqual(len(list((out/'partial_online').glob('*.json'))),1)

    def test_checkpoint_write_failure_never_completes_seed(self):
        with self.workspace() as out:
            self._assert_abort(out,extra_patch=patch.object(batch.CheckpointManager,'mark_seed_complete',side_effect=OSError('checkpoint write failure')))

    def test_real_frozen_simulator_exception_is_not_suppressed(self):
        from ..scenario_builder import ScenarioBuilder
        builder=ScenarioBuilder(self.config,self.public)
        with patch.object(builder,'_simulate',side_effect=RuntimeError('real fixture path simulator defect')):
            with self.assertRaises(RuntimeError): builder.build_fixture_pair(0)

    def test_cached_proposals_exactly_match_frozen_adapter(self):
        import e2_status_adapter
        comparisons=[]
        with np.load(self.debug_file,allow_pickle=False) as data:
            count=0
            for key in sorted(data.files):
                for method in self.config.methods:
                    threshold=self.config.thresholds[method]
                    legacy=e2_status_adapter.propose_adapted(data[key],self.public,threshold,method)
                    new=online.propose(online.build_online_input(data[key],self.public,threshold,method))
                    self.assertEqual(new.score,legacy.score_before_gate)
                    self.assertEqual(new.raw_status,legacy.raw.status)
                    self.assertEqual(new.proposal_status,legacy.proposal_status)
                    self.assertEqual(new.gate_status,legacy.gate_status)
                    self.assertEqual(new.proposal_vector,tuple(legacy.raw.action))
                    self.assertEqual(new.final_action,tuple(legacy.final_action))
                    self.assertEqual(json.loads(new.certificate_json),online._jsonable(legacy.raw.certificate))
                    comparisons.append({'cache_key':key,'method':method,
                        'score_exact':new.score==legacy.score_before_gate,
                        'proposal_max_abs_difference':float(np.max(np.abs(np.asarray(new.proposal_vector)-legacy.raw.action))),
                        'action_max_abs_difference':float(np.max(np.abs(np.asarray(new.final_action)-legacy.final_action))),
                        'raw_status':new.raw_status,'proposal_status':new.proposal_status,'gate_status':new.gate_status,
                        'certificate_exact':json.loads(new.certificate_json)==online._jsonable(legacy.raw.certificate)})
                    count+=1
            self.assertEqual(count,30)
        if EVIDENCE_DIR is not None:
            with (Path(EVIDENCE_DIR)/'proposal_equivalence.json').open('x',encoding='utf-8') as file:
                json.dump(comparisons,file,indent=2)

    def test_corrupted_completed_shard_stops_resume(self):
        provider=self._provider()
        def normal(seed,receipt):
            if seed==710001: raise KeyboardInterrupt('fixture interruption')
            return self._case('normal',seed)
        provider.build_formal_normal.side_effect=normal
        with self.workspace() as out:
            runner=self._runner(out)
            plan=(('normal',0,(710000,710001)),)
            with patch.object(runner,'_batch_plan',return_value=plan),patch.object(batch,'ScenarioBuilder',return_value=provider):
                with self.assertRaises(KeyboardInterrupt): runner._execute_checked_run()
            target=next((out/'seed_shards').glob('*offline.csv'))
            target.write_bytes(target.read_bytes()+b'CORRUPT')
            provider.build_formal_normal.reset_mock()
            resumed=self._runner(out)
            with patch.object(resumed,'_batch_plan',return_value=plan),patch.object(batch,'ScenarioBuilder',return_value=provider):
                with self.assertRaises(ExecutionAborted): resumed._execute_checked_run()
            provider.build_formal_normal.assert_not_called()
            self.assertTrue(target.read_bytes().endswith(b'CORRUPT'))
            self.assertEqual(json.loads((out/'run_status.json').read_text())['status'],'ABORTED_INCONCLUSIVE')
            self.assertFalse((out/'gate_counts.json').exists())

    def test_late_execution_failure_quarantines_unreleased_gate(self):
        from ..result_writer import write_exclusive,canonical_json_bytes
        with self.workspace() as out:
            runner=self._runner(out)
            def late_failure():
                out.mkdir(parents=True,exist_ok=True)
                write_exclusive(out/'gate_counts.json',canonical_json_bytes({'synthetic_unreleased':True}))
                raise OSError('injected manifest write failure')
            with patch.object(runner,'_execute_batches',side_effect=late_failure):
                with self.assertRaises(ExecutionAborted): runner._execute_checked_run()
            self.assertFalse((out/'gate_counts.json').exists())
            self.assertEqual(len(list((out/'execution_failures').glob('*.gate_counts.unreleased.json'))),1)
            with self.assertRaises(ExecutionAborted): statistics.summarize_rows(self.config,[],run_dir=out)

    def test_unknown_or_nonfinite_proposal_return_aborts(self):
        with self.workspace() as out:
            raw=offline.v2_estimators.Proposal('hard_gls_capped',np.zeros(2),0.0,'UNEXPECTED_STATUS')
            self._assert_abort(out,extra_patch=patch.object(offline.v2_estimators,'propose',return_value=raw))
            error=json.loads(next((out/'execution_failures').glob('*.json')).read_text())
            self.assertIn('undocumented status',error['message'])
        raw=offline.v2_estimators.Proposal('hard_gls_capped',np.array([float('nan'),0.0]),0.0,'VALID')
        with patch.object(offline.v2_estimators,'propose',return_value=raw):
            with self.assertRaises(ValueError):
                online.propose(online.build_online_input(self.z,self.public,self.config.thresholds['hard_gls_capped'],'hard_gls_capped'))

    def test_interruption_resumes_to_completed_synthetic_transaction(self):
        # Ten+ten ONE-ID fixture batches exercise the real persistence loop.
        # Statistical endpoints use explicit synthetic sentinels here; the
        # separate 200+200 CSV test checks actual frozen statistics.
        c=replace(self.config,normal_seeds=tuple(range(710100,710110)),
                  attack_seeds=tuple(range(810100,810110)),batch_size=1)
        receipt=auth.authorize('dry_run',c)
        provider=self._provider()
        interrupted=[False]
        def normal(seed,receipt):
            if seed==710101 and not interrupted[0]:
                interrupted[0]=True
                raise KeyboardInterrupt('one-time fixture interruption')
            return self._case('normal',seed)
        provider.build_formal_normal.side_effect=normal
        sentinel={'methods':{'fixture_only':True},'event_age_strata':{}}
        cached={m:online.propose(online.build_online_input(self.z,self.public,c.thresholds[m],m))
                for m in c.methods}
        with self.workspace() as out:
            runner=batch.BatchRunner(c,receipt,out)
            with patch.object(batch,'ScenarioBuilder',return_value=provider):
                with self.assertRaises(KeyboardInterrupt): runner._execute_checked_run()
            files=list((out/'seed_shards').glob('*710100*'))
            before={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
            provider.build_formal_normal.reset_mock()
            resumed=batch.BatchRunner(c,receipt,out)
            with (patch.object(batch,'ScenarioBuilder',return_value=provider),
                  patch.object(batch,'propose',side_effect=lambda inp:cached[inp.method]),
                  patch.object(batch,'summarize_rows',return_value=dict(sentinel)),
                  patch.object(batch,'independent_recompute',return_value=dict(sentinel))):
                summary=resumed._execute_checked_run()
            self.assertFalse(summary['formal_experiment_executed'])
            self.assertEqual(json.loads((out/'run_status.json').read_text())['status'],'COMPLETED')
            ledger=json.loads((out/'checkpoint.json').read_text())
            self.assertEqual(len(ledger['completed_seeds']),20)
            self.assertEqual(len(ledger['completed_batches']),20)
            self.assertEqual(before,{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in files})
            self.assertNotIn(710100,[x.args[0] for x in provider.build_formal_normal.call_args_list])

    def test_all_logging_disk_errors_emit_trace_and_remain_ineligible(self):
        import contextlib,io
        from .. import execution_state as states
        with self.workspace() as out:
            stderr=io.StringIO()
            try:
                raise OSError('simulated write failure')
            except OSError as exc:
                with contextlib.redirect_stderr(stderr), patch.object(states,'write_exclusive',side_effect=OSError('full disk')), patch.object(states,'write_replace_atomic',side_effect=OSError('full disk')):
                    record=states.record_failure(out,exc,{'seed':710000,'event':None,'stage':'disk'})
            self.assertEqual(record['status'],'ABORTED_INCONCLUSIVE')
            self.assertIn('Traceback',stderr.getvalue())
            self.assertIn('emergency_logging_failure',record)
            self.assertFalse((out/'gate_counts.json').exists())


if __name__ == '__main__':
    unittest.main()

