"""Read-only audit of the existing episode detector; no new trajectories."""
from __future__ import annotations
import csv
import hashlib
import json
from pathlib import Path
import numpy as np

ROOT=Path(__file__).resolve().parents[3]
RUN=ROOT/'simulation/validation_runs/2026-11-11_sequential_strong_v1'
OUT=ROOT/'reviews/fdi_replay_20261112'


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def load_csv(p):
    with p.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))


def main():
    code=ROOT/'simulation/sequential_cache.py'
    train_config=json.loads((RUN/'gap8/config.json').read_text(encoding='utf8'))
    sched={};lengths={}
    for name in ('gap8','irregular'):
        folder=RUN/name
        sample=load_csv(folder/'phase_sample_counts.csv')
        selected=[r for r in sample if r['phase']=='steady' and r['edge']=='0']
        sched[name]=[{'prefix_length':int(r['length']),'train_episodes_covering_prefix':int(r['train_count']),
                      'calibration_episodes_covering_prefix':int(r['cal_count']),'block_diagonal_fallback':r['fallback'].lower()=='true'}
                     for r in selected]
        clean=load_csv(folder/'primary/mean__clean_episodes.csv')
        edge=[r for r in clean if r['edge']=='0' and int(r['start'])>=50]
        complete=[r for r in edge if r['complete'].lower()=='true']
        censored=[r for r in edge if r['complete'].lower()!='true']
        hist={}
        for r in complete:hist[int(r['length'])]=hist.get(int(r['length']),0)+1
        lengths[name]={'steady_main_edge_test_episodes_total':len(edge),
          'complete':len(complete),'right_censored':len(censored),
          'right_censor_fraction':len(censored)/len(edge) if edge else None,
          'complete_episode_length_histogram':dict(sorted(hist.items())),
          'right_censored_length_histogram':{str(k):sum(int(r['length'])==k for r in censored) for k in sorted({int(r['length']) for r in censored})}}
    # Verify the stored existing "mean" quadratic equals its explicit code-form matrix
    # for every supported steady-state prefix on the attacked main edge.
    checks=[]
    rng=np.random.default_rng(20261112)
    for name in ('gap8','irregular'):
        with np.load(RUN/name/'phase_statistics.npz') as f:
            md=json.loads(f['metadata'].item())
            for L in range(1,9):
                stem=f'p2_e0_l{L}_'
                S=f[stem+'cov'];mu=f[stem+'mean'];Pcode=f[stem+'mean_P']
                C=np.tile(np.eye(md['m']),(1,L))/L
                Pexplicit=C.T@np.linalg.solve(C@S@C.T,C)
                assert np.allclose(Pcode,Pexplicit,rtol=1e-11,atol=1e-11)
                d=rng.normal(size=L*md['m'])
                direct=float((C@d)@np.linalg.solve(C@S@C.T,C@d))
                implemented=float(d@Pcode@d)
                assert abs(direct-implemented)<1e-10
                X=np.tile(np.eye(md['m']),(L,1))
                Si=np.linalg.inv(S)
                Pgls=Si@X@np.linalg.inv(X.T@Si@X)@X.T@Si
                rel=float(np.linalg.norm(Pcode-Pgls)/max(np.linalg.norm(Pgls),1e-12))
                count=next(r['train_episodes_covering_prefix'] for r in sched[name] if r['prefix_length']==L)
                fallback=next(r['block_diagonal_fallback'] for r in sched[name] if r['prefix_length']==L)
                checks.append({'schedule':name,'prefix_length':L,'train_episodes_covering_prefix':count,
                    'full_joint_covariance_fallback_used':fallback,
                    'existing_score_equals_full_covariance_normalized_arithmetic_mean':True,
                    'operator_relative_difference_from_unrestricted_GLS_common_constant_mean':rel})
    result={'status':'READ_ONLY_REAUDIT_PASSED','new_physical_trajectories':0,
      'source_code_sha256':sha(code),'source_run':'2026-11-11_sequential_strong_v1',
      'actual_attack_and_cache_settings':{'A':train_config['A'],'Q':train_config['Q'],'P0':train_config['P0'],
          'H_matrices':train_config.get('H_matrices',train_config.get('H_scales')),
          'R_matrices':train_config.get('R_matrices',train_config.get('R_variances')),
          'send_delta_squared':train_config['send_delta_squared'],'max_interval':train_config['max_interval'],
          'fixed_schedules':train_config.get('cache_schedule_pattern'),
          'attack_edges':{'primary':[0,1]},'attack':train_config['attack']},
      'existing_method_code':'PhaseStatistics.fit/current/episode_scores + SequentialController.update',
      'existing_mean_statistic':'d.T C.T (C S_L C.T)^-1 C d; C=[I ... I]/L; S_L is empirical full joint prefix covariance where supported',
      'meaning':'covariance-normalized prefix-average/Wald statistic for a constant residual offset; not unrestricted GLS for arbitrary S_L',
      'episode_max_threshold':True,
      'threshold_calibration':'training/calibration normal episodes fit S_L; each detector tune set re-used for 4 quantile-retuning rounds; separate normal-audit and test seeds.',
      'cache_isolation':'bad flag ORs any prefix alarm during one cache episode; reset on the next received packet.',
      'trigger_schedule':'each local measurement is available every simulation tick; new estimate packets use a fixed exogenous repeated schedule in this benchmark. In the online engine, Send-on-Delta checks current pre-measurement estimate difference and timeout; t=0 forced send.',
      'cache_timing':'fresh packet resets last_receive and payload before aligned=A^age payload and monitor update. Episode includes residuals at ages 0..Delta-1; next fresh packet closes it before that time sample is assigned to the old episode.',
      'right_censor':'finish() labels final unclosed episodes complete=False; fit and false-isolation denominators exclude incomplete episodes.',
      'steady_main_edge_episode_length_and_censor_audit':lengths,
      'main_edge_prefix_covariance_audit':sched,'score_equivalence_checks':checks,
      'conditional_distribution_limit':'send selection and survival without a next packet depend on the sender estimate/process path; conditional cache error need not remain Gaussian. Stored covariance is empirical for the age-only-policy training trajectories.',
      'baseline_gap':'an unrestricted GLS matched to the dynamic attack response X=[H;HA;...] is not the existing arithmetic-prefix statistic. It is a standard GLS/GLRT, not a new mechanism; do not claim exact identity. The existing detector already covers full-covariance prefix averaging and episode-max cache isolation.'}
    (OUT/'g1_existing_code_audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps({'status':result['status'],'new_trajectories':0,'checks':len(checks),
      'episode_audit':lengths,'full_cov_counts':{name:[r['train_episodes_covering_prefix'] for r in rows if not r['block_diagonal_fallback']] for name,rows in sched.items()}},ensure_ascii=False,indent=2))


if __name__=='__main__':main()
