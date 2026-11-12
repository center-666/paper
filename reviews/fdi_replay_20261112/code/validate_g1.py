"""Validate G1 deliverables, source hashes and no-new-run boundary."""
import csv
import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT=Path(__file__).resolve().parents[3]
PKG=ROOT/'reviews/fdi_replay_20261112'


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    required=['identifiability_audit.md','baseline_equivalence.md','g1_experiment_plan.md','g1_decision.md']
    for name in required:
        p=PKG/name
        assert p.exists() and p.stat().st_size>1800,p
    audit=json.loads((PKG/'g1_existing_code_audit.json').read_text(encoding='utf8'))
    assert audit['status']=='READ_ONLY_REAUDIT_PASSED' and audit['new_physical_trajectories']==0
    sample=json.loads((PKG/'g1_sample_size.json').read_text(encoding='utf8'))
    assert len(sample['comparisons'])==12
    reg=ROOT/'simulation/validation_runs/2026-11-11_sequential_strong_v1/registration.json'
    source=json.loads(reg.read_text(encoding='utf8'))
    for rel,digest in source['source_sha256'].items():
        assert sha(reg.parent/'sources'/rel)==digest,rel
    changed=subprocess.check_output(['git','diff','--name-only','HEAD'],cwd=ROOT,text=True,encoding='utf8').splitlines()
    assert not any(p.startswith(('simulation/','papers/')) for p in changed),changed
    runroot=ROOT/'simulation/validation_runs'
    assert not [p.name for p in runroot.iterdir() if p.is_dir() and 'g1' in p.name.lower()]
    broken=[]
    for name in required:
        p=PKG/name;text=p.read_text(encoding='utf8')
        for target in re.findall(r'\]\(([^)]+)\)',text):
            if target.startswith(('http://','https://','#')):continue
            local=target.split('#')[0]
            if local and not (p.parent/local).exists():broken.append((name,local))
    assert not broken,broken
    result={'passed':True,'required_G1_reports':required,'episode_score_and_schedule_reaudited':True,
        'prior_run_source_files_hash_verified':len(source['source_sha256']),
        'seed_level_sample_size_rows':len(sample['comparisons']),'new_seed_trajectories':0,
        'new_G1_RunId':None,'old_simulation_and_papers_unchanged':True,
        'decision':'B - statistical problem exists; method increment is insufficient'}
    (PKG/'g1_delivery_validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
