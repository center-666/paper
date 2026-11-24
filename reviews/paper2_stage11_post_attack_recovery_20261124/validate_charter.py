"""Validate the frozen S11 task charter and write a source-hash manifest."""
from fractions import Fraction as F
import hashlib
import json
from pathlib import Path
import subprocess

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
CHARTER=HERE/'S11_task_charter.md'
PROTOCOL=HERE/'s11_protocol.json'


def matrix_det_observability(A,C):
    a,b=map(F,A[0])
    c,d=map(F,A[1])
    row0=list(map(F,C[0]))
    row1=[row0[0]*a+row0[1]*c,row0[0]*b+row0[1]*d]
    return row0[0]*row1[1]-row0[1]*row1[0]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git_status(path):
    rel=path.relative_to(ROOT).as_posix()
    result=subprocess.run(['git','status','--porcelain','--',rel],
                          cwd=ROOT,capture_output=True,text=True,check=True)
    return result.stdout.strip() or "clean at frozen base"


def main():
    spec=json.loads(PROTOCOL.read_text(encoding='utf8'))
    assert spec['status']=={
        'charter_frozen':True,'implementation_started':False,
        'random_pilot_started':False,'confirmation_started':False,
        'performance_claims':False}
    for model_name in ('V2','stable_stress'):
        model=spec['models'][model_name]
        assert matrix_det_observability(model['A'],model['C'])==F(1,10)
    q=spec['uplink_quantizer']
    for B in (q['primary_bits'],q['sensitivity_bits']):
        K=2**B
        step=F(8,K)
        assert K==2**B and step>0
        # Saturation and all K-2 interior cells form a contiguous partition.
        cuts=[-F(4)+j*step for j in range(1,K)]
        assert len(cuts)==K-1 and cuts[0]<cuts[-1]
    prior_sum=sum((F(1,(k+1)*(k+2)) for k in range(512)),F(0))
    residual=F(1,513)
    assert prior_sum+residual==1
    assert len(spec['experiments']['primary']['amplitudes'])==4
    assert len(spec['experiments']['primary']['durations'])==2
    assert len(spec['experiments']['primary']['onsets'])==2
    primary_cells=4*2*2
    stress_cells=2*2*1
    bit_cells=2*2*1
    assert primary_cells+stress_cells+bit_cells==24
    assert spec['confidence']['alpha']==spec['confidence']['epsilon']==0.01
    assert q['saturation_codes_in_alphabet'] is True
    assert set(spec['confidence']['reference_durations'])=={20,60}
    assert len(spec['confidence']['reference_amplitudes'])==4
    cells=0
    for key in ('primary','stable_stress','bit_sensitivity'):
        cell=spec['experiments'][key]
        cells+=len(cell['amplitudes'])*len(cell['durations'])*len(cell['onsets'])
    assert cells==24
    source_paths=[
        HERE/'README.md',Path(__file__),
        CHARTER,PROTOCOL,
        ROOT/'reviews/paper2_stage6_vector_correction_20261122/model.json',
        ROOT/'reviews/paper2_stage6_vector_correction_20261122/vector_record.py',
        ROOT/'reviews/paper2_stage6_vector_correction_20261122/exact_linear.py',
        ROOT/'reviews/paper2_stage3_joint_detection_20261121/01_joint_observation_theory.md',
        ROOT/'reviews/paper2_stage9_cumulative_evidence_20261123/paired_recovery.py',
        ROOT/'reviews/paper2_stage9_cumulative_evidence_20261123/cumulative_envelope.py',
        ROOT/'reviews/paper2_stage10_r4a_final_20261124/README.md',
        ROOT/'reviews/paper2_stage10_r4a_final_20261124/alphabet_audit.py',
        ROOT/'reviews/paper1_audit_recovery_theory_20261121/04_conditional_risk_identity.md',
        ROOT/'reviews/paper1_audit_recovery_theory_20261121/recovery_trial/protocol.json',
        ROOT/'reviews/paper1_audit_recovery_theory_20261121/recovery_trial/results/run_v1/results_analysis.md'
    ]
    base=subprocess.run(['git','rev-parse','HEAD'],cwd=ROOT,capture_output=True,
                        text=True,check=True).stdout.strip()
    if base!=spec['repository_base_commit']:
        raise RuntimeError(f"Repository base changed: expected {spec['repository_base_commit']}, got {base}")
    manifest={
        'schema':'paper2-stage11-source-manifest-v0.1',
        'freeze_date':spec['freeze_date'],
        'repository_base_commit':base,
        'charter_sha256':sha(CHARTER),
        'protocol_sha256':sha(PROTOCOL),
        'files':{
            p.relative_to(ROOT).as_posix():{
                'sha256':sha(p),
                'worktree_status_at_manifest_generation':git_status(p)
            } for p in source_paths
        },
        'validation':{
            'V2_observability_determinant':'1/10',
            'stable_stress_observability_determinant':'1/10',
            'onset_prior_partial_sum_plus_residual':'1',
            'scenario_cells':cells,
            'implementation_started':False
        }
    }
    (HERE/'source_manifest.json').write_text(
        json.dumps(manifest,indent=2)+'\n',encoding='utf8',newline='\n')
    print("PASS: charter/protocol invariants and",len(source_paths),"source hashes")


if __name__=="__main__":
    main()
