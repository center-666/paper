"""Deterministic algebra checks for G5; no simulations or new defense."""
from pathlib import Path
import argparse
import hashlib
import json
import math

BASE = Path(__file__).resolve().parents[1]


def main(run_id):
    out = BASE / 'results' / run_id
    out.mkdir(parents=True, exist_ok=False)
    rho, R, P0, k = .9, 1., 1., 1000
    r = rho*rho
    # Exact scalar closed form from Ye (29)-(32), not Monte Carlo.
    gain = 1/(r**k*R/P0 + (1-r**k)/(1-r))
    assert abs(gain-(1-r)) < 1e-12
    # Uniform [0,1] analytic bin probabilities: no empirical histogram.
    entropy = []
    for bins in [10, 100, 1000]:
        q = 1/bins
        h_disc = -bins*q*math.log(q)
        assert abs(h_disc+math.log(q)) < 1e-12
        entropy.append({'bins':bins,'q':q,'probability_of_bin':q,'density':1.,
                        'discrete_entropy':h_disc,'differential_entropy':0.,
                        'corrected_entropy':h_disc+math.log(q)})
    # Two PSD joint moments S1=[[100,10],[10,1]], S2=I.
    cases = [(100.,10.,1.),(1.,0.,1.)]
    totals = lambda g: [p-2*g*c+g*g*d for p,c,d in cases]
    assert totals(0)==[100.,1.] and totals(1)==[81.,2.]
    # The worst total risk is first case, decreasing on [0,1];
    # the worst risk difference is at least g^2 in the second case.
    # Thus the two minimax objectives choose g=1 and g=0 respectively.
    p,V = 1.,3.
    lam = p/(p+V)
    robust_mse=(1-lam)**2*p+lam*lam*V
    assert abs(robust_mse-p*V/(p+V))<1e-12 and robust_mse<p
    # Shared packet noise: A=2, age k=1 and l=2, V=1.
    packet_cross_cov = 2**1*1*2**2
    assert packet_cross_cov==8
    result={'run_id':run_id,'scope':'exact formulas only; no detector, no state trajectories, no Monte Carlo',
      'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
      'ye_gain_limit':{'rho':rho,'r':r,'R':R,'P0':P0,'k':k,'gain':gain,
                      'actual_limit':1-r,'printed_lemma3_limit':1.,
                      'conclusion':'Printed gain-limit statement does not follow from scalar equations (29)-(32); P_k -> 0 remains possible.'},
      'histogram_density_entropy_checks':entropy,
      'total_risk_vs_risk_difference':{'joint_moments':cases,'passive_risks':totals(0),
           'total_minimax_gamma':1.,'total_minimax_risks':totals(1),
           'risk_difference_minimax_gamma':0.,'second_model_is_harmed_by_total_minimax':True},
      'same_law_need_not_preclude_robust_fusion':{'p':p,'total_noise_variance_upper':V,
           'gain':lam,'worst_mse':robust_mse,'baseline_mse':p,
           'required_condition':'independent zero-mean total noise; standard robust estimation, not a proposed new algorithm'},
      'shared_packet_noise':{'A':2,'V':1,'ages':[1,2],'cross_covariance':packet_cross_cov,
           'conclusion':'Cannot replace a cached noisy packet by independent noise on each use.'},
      'radial_counterexample':{'definition':'U~chi2_m, J uniform coordinate, S random sign; z=S*sqrt(U)*e_J, independent U/J/S, m>=2',
           'mean':'0','covariance':'I because E(U)=m and E(e_J e_J^T)=I/m',
           'energy':'||z||^2=U is exactly chi2_m',
           'support':'union of coordinate axes, non-Gaussian',
           'scope':'Refutes inference non-Gaussian residual implies non-chi2 energy, not the stated energy-law premise of Ye Theorem 1.'},
      'all_checks_passed':True}
    (out/'checks.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'run_id':run_id,'passed':True,'simulation_executed':False}))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--run-id',default='2026-11-13_g5_formula_checks_r01')
    a=p.parse_args()
    if Path(a.run_id).name!=a.run_id:raise ValueError('Invalid Run ID')
    main(a.run_id)
