"""Read-only formal E3 artifact audit; does not simulate or propose any actions."""
from pathlib import Path
from collections import Counter, defaultdict
import json, math, hashlib, sys, csv
import numpy as np

ROOT=Path.cwd()
sys.path.insert(0,str(ROOT))
from reviews.g1r_risk_constrained_recovery.code.g1r_e3_runner.config_loader import load_config,canonical_sha256
from reviews.g1r_risk_constrained_recovery.code.g1r_e3_runner.authorization_guard import authorize,bindings
from reviews.g1r_risk_constrained_recovery.code.g1r_e3_runner.storage import verify_manifest,digest
from reviews.g1r_risk_constrained_recovery.code.g1r_e3_runner.execution_state import Checkpoint
from reviews.g1r_risk_constrained_recovery.code.g1r_e3_runner.integrity_checker import validate_rows
from reviews.g1r_risk_constrained_recovery.code.g1r_e3_runner.statistics_reporter import recompute,resample_indices
from reviews.g1r_risk_constrained_recovery.code.g1r_e3_runner.independent_statistics import compare

EXTERNAL=Path(__file__).parent
BASE=ROOT/'reviews/g1r_risk_constrained_recovery'
RUN=BASE/'results/g1r_e3_run_20261116_001'
OUT=BASE/'results/g1r_e3_completion_audit_20261116_r01'

def saved(path): return json.loads(path.read_text(encoding='utf-8'))

def main():
    if OUT.exists(): raise FileExistsError('Do not overwrite prior audit')
    cfg=load_config(); pre=saved(EXTERNAL/'prelaunch.json')
    assert saved(EXTERNAL/'process_receipt.json')['exit_code']==0
    assert saved(RUN/'run_status.json')['status']=='COMPLETED'
    receipt=authorize(cfg,Path(pre['authorization_path']))
    assert bindings(cfg)==pre['bindings']
    manifest=verify_manifest(RUN)
    assert manifest['E3_executed'] is True
    meta=saved(RUN/'config.json')
    assert meta['authorization_file_sha256']==receipt.file_sha256
    assert meta['authorization_id']=='G1R-E3-AUTH-20261116-001'
    cp=saved(RUN/'checkpoint.json')
    assert canonical_sha256(cp['payload'])==cp['sha256']
    completed=cp['payload']['completed']
    expected_seeds={f'normal:{s}' for s in cfg.normal_seeds}|{f'attack:{s}' for s in cfg.attack_seeds}
    assert set(completed)==expected_seeds
    Checkpoint(RUN,cp['payload']['identity']).verify()
    files=sorted((RUN/'seeds').glob('*.json')); assert len(files)==400
    rows=[]; batches=[]
    for group,seeds in [('normal',cfg.normal_seeds),('attack',cfg.attack_seeds)]:
        for i in range(10):
            path=RUN/f'{group}_batch_{i:02d}.json'; data=saved(path)
            assert data['group']==group and data['seeds']==list(seeds[20*i:20*i+20])
            merged=[]
            for seed in data['seeds']:
                shard=saved(RUN/'seeds'/f'{group}_{seed}.json')
                assert shard['seed']==seed and shard['group']==group
                assert len(shard['rows'])==(3 if group=='normal' else 75)
                merged.extend(shard['rows'])
            assert merged==data['rows']
            batches.append(path); rows.extend(merged)
    assert len(rows)==15600 and len(batches)==20
    assert Counter(r['role'] for r in rows)=={'normal':600,'paired_healthy':600,'attack':14400}
    validate_rows(cfg,rows)
    # Verify online record hashes and fields, and offline action-to-file joins.
    online_paths=list((RUN/'online').glob('*.json')); assert len(online_paths)==15600
    checked=set(); grouped=defaultdict(list); max_loss_error=0.
    allowed={'method','z','threshold','raw_status','proposal_status','gate_status','score','proposal_vector','final_action','action_norm_before_gate','action_norm_after_gate','certificate_zero_or_unresolved','certificate_json','solver_stage','solver_gap','solver_reject_reason','execution_success','validation_status','public_model_sha256','record_sha256'}
    for row in rows:
        grouped[(row['role'],row['seed'],tuple(row['event']) if row['event'] else None,row['age'])].append(row)
        for filename_key,sha_key,action_key in [('proposal_file','proposal_file_sha256','u'),('healthy_proposal_file','healthy_proposal_file_sha256','u0')]:
            path=RUN/'online'/row[filename_key]
            assert digest(path)==row[sha_key]
            record=saved(path); p=record['proposal']
            assert canonical_sha256(p)==record['record_sha256']
            assert canonical_sha256({k:v for k,v in p.items() if k!='record_sha256'})==p['record_sha256']
            assert set(p)==allowed
            assert len(p['z'])==12 and np.isfinite(p['z']).all()
            assert p['final_action']==row[action_key] and p['method']==row['method']
            if filename_key=='proposal_file':
                for name in ('raw_status','proposal_status','gate_status','threshold','score'): assert p[name]==row[name]
            checked.add(path.name)
        x,h,a,u,u0=(np.asarray(row[k],float) for k in ('true_state','healthy_estimate','attacked_estimate','u','u0'))
        e=h-x; delta=a-h
        sq=lambda v:math.fsum(float(t)*float(t) for t in v)
        calc={'L0':sq(e),'La':sq(a-x),'L0_u':sq(h-u0-x),'La_u':sq(a-u-x)}
        calc.update(attack_gain=calc['La']-calc['La_u'],healthy_gain=calc['L0']-calc['L0_u'],normal_risk_change=calc['L0_u']-calc['L0'])
        calc.update(pollution_gain=2*float(delta@u)-sq(u),healthy_cross_term=2*float(e@u),net_gain=calc['attack_gain']-calc['healthy_gain'])
        for k,value in calc.items():
            error=abs(value-row[k]); max_loss_error=max(max_loss_error,error)
            assert math.isclose(value,row[k],rel_tol=1e-10,abs_tol=1e-12),(row['seed'],k,value,row[k])
        for k,value in [('corrected_attacked_estimate',a-u),('corrected_healthy_estimate',h-u0),('corrected_attack_error',a-u-x),('corrected_healthy_error',h-u0-x)]:
            assert np.allclose(row[k],value,rtol=1e-12,atol=1e-12)
    assert len(checked)==15600
    for group in grouped.values():
        assert len(group)==3 and {r['method'] for r in group}==set(cfg.methods)
        for r in group[1:]:
            for name in ('true_state','healthy_estimate','attacked_estimate','delta','pairing_sha256'): assert r[name]==group[0][name]
        zs=[saved(RUN/'online'/r['proposal_file'])['proposal']['z'] for r in group]
        assert zs[0]==zs[1]==zs[2]
    # Replay only the frozen bootstrap index generation, not any trajectories.
    ix=resample_indices(cfg.bootstrap_seed,200,1999)
    current=saved(RUN/'statistics.json')
    assert hashlib.sha256(ix.astype('<i8').tobytes()).hexdigest()==current['bootstrap_indices_sha256']
    reconstructed=recompute(cfg,RUN,formal=True,indices=ix,receipt=receipt)
    assert reconstructed==current
    independent=compare(cfg,rows,ix,current)
    # Recover all methods' descriptive primary intervals and raw baseline contrasts.
    methods=list(cfg.methods)+['yang']; primary=[]
    for seed in cfg.attack_seeds:
        rs={r['method']:r for r in grouped['attack',seed,(0,200),64]}
        primary.append([rs[m]['La_u'] for m in cfg.methods]+[rs[cfg.methods[0]]['La']])
    primary=np.asarray(primary); boot=primary[ix].mean(axis=1)
    descriptive={}
    for j,m in enumerate(methods):
        gain=(boot[:,-1]-boot[:,j])/boot[:,-1]
        descriptive[m]={'mse':float(primary[:,j].mean()),'relative_gain_vs_yang':float(1-primary[:,j].mean()/primary[:,-1].mean()),
                        'relative_gain_vs_yang_ci95':np.quantile(gain,[.025,.975]).tolist()}
    statuses=Counter((r['role'],r['method'],r['raw_status'],r['proposal_status'],r['gate_status']) for r in rows)
    counts={'normal_seeds':200,'attack_seeds':200,'batches':20,'normal_rows':600,'paired_healthy_rows':600,'attack_rows':14400,'online_files':15600,'unique_attack_seed_event_age':4800}
    results={'status':'PASS_COMPLETENESS_HASHES_AND_INDEPENDENT_STATISTICS','run_id':RUN.name,'counts':counts,
             'frozen_summary_exact_match':True,'independent_vector_bootstrap':independent,
             'max_abs_loss_reconstruction_error':max_loss_error,'all_proposal_joins_verified':True,
             'manifest_verified_files':len(manifest['files_sha256']),'manifest_sha256':digest(RUN/'artifact_manifest.json'),
             'bootstrap_indices_sha256':current['bootstrap_indices_sha256'],'bootstrap_seed':141460000,'bootstrap_resamples':1999,
             'primary_descriptive':descriptive,'status_counts':{'|'.join(k):v for k,v in sorted(statuses.items())},
             'decision':current['decision'],'execution_failures':len(list((RUN/'failures').glob('*'))) if (RUN/'failures').exists() else 0,
             'all_zero_and_rejected_rows_retained':True,'no_new_trajectory_generation_in_audit':True}
    OUT.mkdir()
    (OUT/'independent_recompute.json').write_bytes((json.dumps(results,indent=2,sort_keys=True)+'\n').encode())
    (OUT/'frozen_statistics_recomputed.json').write_bytes((json.dumps(reconstructed,indent=2,sort_keys=True)+'\n').encode())
    with (OUT/'event_age_metrics.csv').open('w',encoding='utf-8',newline='') as f:
        fields=['event_age','method','n_independent_seeds','mse','relative_gain_vs_yang','attack_gain','healthy_gain_paired','net_gain','net_ci95_lower','net_ci95_upper','pollution_gain','healthy_cross_term','nonzero_rate','saturation_rate','zero_action_rate','rejection_rate']
        writer=csv.DictWriter(f,fieldnames=fields,lineterminator='\n');writer.writeheader()
        for case,metrics in current['per_event_age'].items():
            for m,v in metrics.items():
                row={'event_age':case,'method':m,'n_independent_seeds':200,'relative_gain_vs_yang':1-v['mse']/metrics['yang']['mse'],
                     'net_ci95_lower':v['net_gain_interval_95'][0],'net_ci95_upper':v['net_gain_interval_95'][1]}
                row.update({k:v[k] for k in fields if k in v});writer.writerow(row)
    print(json.dumps({'audit':results,'main_case':current['per_event_age']['0:200@64'],
                     'yang_primary':current['yang_primary'],'confirmatory':current['confirmatory_worst_event_age64'],
                     'normal':current['normal'],'net_advantages':current['exploratory_net_advantages']},indent=2))

if __name__=='__main__': main()
