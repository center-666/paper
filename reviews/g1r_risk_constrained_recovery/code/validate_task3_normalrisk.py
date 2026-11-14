"""Read-only mathematical delivery checks, apart from a new verification JSON."""
from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path
import re

import numpy as np
from scipy.integrate import quad
from scipy.special import erfc

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parents[1]
RUN = HERE/"results/g1r_task3_normalrisk_20261114_r01"
SOURCES = HERE/"sources/task3_normalrisk_20261114"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    freeze=json.loads((RUN/'frozen_plan.json').read_text(encoding='utf-8'))
    result=json.loads((RUN/'summary.json').read_text(encoding='utf-8'))
    moments=json.loads((RUN/'normal_risk_moments.json').read_text(encoding='utf-8'))
    assert all(sha(ROOT/p)==h for p,h in freeze['source_sha256'].items())
    with np.load(ROOT/freeze['plan']['input_matrices'],allow_pickle=False) as data:
        C=data['e0_loading']@data['eta_loading'].T
        assert np.allclose(C,moments['C_0_eta'],atol=1e-15)
        B=np.linalg.solve(data['Sigma_eta'],C.T).T
        Sm=C@B.T
        assert np.allclose(Sm,moments['Sigma_m'],atol=1e-15)
        P0=data['e0_loading']@data['e0_loading'].T
        assert np.linalg.eigvalsh(P0-Sm)[0]>0
    lo,hi=np.linalg.eigvalsh(Sm)
    alpha,risk,q=result['alpha'],result['normal_risk_budget_R'],result['tail_integration']['quantile']
    # Independent stop-loss representation, rather than truncated moment.
    def excess(phi):
        v=hi*np.cos(phi)**2+lo*np.sin(phi)**2
        return np.sqrt(np.pi*v/2)*erfc(q/np.sqrt(2*v))
    val,err=quad(excess,0,np.pi/2,epsabs=1e-13,epsrel=1e-12)
    dual=alpha*q+2/np.pi*val
    assert abs(dual-result['c_alpha'])<1e-12
    for coeff,cap in [('c_old_Cauchy','U_old'),('c_conditional_Cauchy','U_conditional_Cauchy'),('c_alpha','U_new')]:
        c,U=result[coeff],result[cap]
        assert np.isclose(alpha*U*U+2*c*U,risk,atol=1e-14)
    assert result['U_old']<result['U_required_for_one_percent_gain']<result['U_conditional_Cauchy']
    assert result['U_conditional_Cauchy']<result['U_new_discretization_bracket'][0]<=result['U_new']
    assert result['case_decision']=='B'
    assert result['new_trajectories']==0 and result['seeds_used']==[]
    for p in RUN.glob('*.json'):
        json.loads(p.read_text(encoding='utf-8'))
    for p in [HERE/'code/exact_normal_risk_refinement.py',Path(__file__)]:
        tree=ast.parse(p.read_text(encoding='utf-8'))
        calls={node.func.id for node in ast.walk(tree) if isinstance(node,ast.Call) and isinstance(node.func,ast.Name)}
        assert not calls.intersection({'simulate','generate_data','default_rng'})
    protected=json.loads((SOURCES/'protected_before.json').read_text(encoding='utf-8'))
    changed=[p for p,h in protected.items() if not (ROOT/p).is_file() or sha(ROOT/p)!=h]
    assert changed==['reviews/g1r_risk_constrained_recovery/EXECUTIVE_SUMMARY.md'],changed
    for p in [HERE/'09_exact_normal_risk_refinement.md',HERE/'EXECUTIVE_SUMMARY.md']:
        for link in re.findall(r'\]\(([^)]+)\)',p.read_text(encoding='utf-8')):
            if link.startswith(('https:','http:','#')):
                continue
            assert (p.parent/link.split('#')[0]).resolve().exists(),(p,link)
    validation={
        'result':'PASS','task_scope':'Task3 only; no v2 protocol, E2/E3 or action-specific optimizer',
        'validator_source_sha256':sha(__file__),
        'frozen_source_and_input_hashes':True,'normal_moments_reconstructed':True,
        'independent_stop_loss_c_alpha':dual,'stop_loss_vs_polar_absolute_difference':abs(dual-result['c_alpha']),
        'stop_loss_integral_error_estimate':2/np.pi*err,
        'risk_root_equations':True,
        'case_B_already_established_by_conditional_Cauchy_without_tail_integration':True,
        'prior_tracked_files':len(protected),'changed_existing_files':changed,
        'all_other_old_files_unchanged':True,'new_trajectories':0,'seeds_used':[],
        'numerical_bounds_note':'No formal directed-rounding arithmetic claimed; case B does not rely on tight tail quadrature',
    }
    output=SOURCES/'verification.json'
    assert not output.exists()
    output.write_text(json.dumps(validation,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps(validation))


if __name__=='__main__':
    main()
