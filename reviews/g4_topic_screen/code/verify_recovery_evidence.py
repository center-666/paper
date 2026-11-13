"""Independent artifact checks only; no simulation, fitting or mutation of runs."""
from pathlib import Path
import argparse
import csv
import hashlib
import json
import numpy as np

ROOT=Path(__file__).resolve().parents[3]
BASE=ROOT/'reviews/g4_topic_screen'


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main(run_id):
    out=BASE/'results'/run_id
    out.mkdir(parents=True,exist_ok=False)
    source=BASE/'results/2026-11-13_g4_recovery_budget_r01'
    archive=ROOT/'simulation/g2_runs/2026-11-13_g2_replay_effectiveness_v3'
    for name,digest in json.loads((source/'output_hashes.json').read_text()).items():
        assert sha(source/name)==digest,name
    for path,digest in json.loads((source/'source_hashes_before.json').read_text()).items():
        assert sha(ROOT/path)==digest,path
    checks=[]
    method_names={'raw_yang':'raw_yang_no_cap','cap_only':'cap_only','spatial_hard':'spatial_hard','zhou_random':'zhou_random_protection'}
    with np.load(source/'recovery_timelines.npz') as new,np.load(archive/'mse_timeline_per_seed.npz') as old:
        assert np.array_equal(new['seeds'],old['seeds'][:8])
        for method,label in method_names.items():
            for rule in ('fixed_lag8','nearest_current'):
                old_rule='nearest_current_sender' if rule=='nearest_current' else rule
                for scope in ('receiver','network'):
                    a=new[method+'__'+rule+'__'+scope+'_error_sq'][0]
                    b=old[old_rule+'__'+label+'__'+scope+'_error_sq'][:8,250:]
                    err=float(np.max(np.abs(a-b)))
                    assert err<1e-10,(method,rule,scope,err)
                    checks.append({'method':method,'rule':rule,'scope':scope,'state_indices':[250,400],'max_absolute_error':err})
    with (source/'all_schedule_seed_metrics.csv').open(newline='') as f:
        rows=list(csv.DictReader(f))
    assert len(rows)==4288
    assert len({(r['method'],r['selector'],r['seed'],r['action_id']) for r in rows})==4288
    assert all(int(r['extra_payload_bytes'])==32*int(r['extra_broadcasts']) and int(r['extra_broadcasts'])<=2 for r in rows)
    assert all(int(r['attacks'])==14 for r in rows)
    result={'run_id':run_id,'passed':True,'simulation_executed':False,'original_inputs_unchanged':True,
            'unique_schedule_seed_metrics':4288,'budget_bytes_verified':True,'attack_count_verified':True,
            'passive_timeline_checks':checks,'verification_code_sha256':sha(Path(__file__)),
            'scope_limit':'No componentwise all-node estimate-state equality is claimed from squared-error checks.'}
    (out/'verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps({'passed':True,'timeline_checks':len(checks),'max_error':max(c['max_absolute_error'] for c in checks)}))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--run-id',default='2026-11-13_g4_recovery_verification_r01')
    args=p.parse_args()
    if Path(args.run_id).name!=args.run_id:raise ValueError('Invalid run ID')
    main(args.run_id)
