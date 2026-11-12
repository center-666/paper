"""Small analytic diagnostics for the literature review; no estimator study.

Each case runs independently; outputs never overwrite existing files.
These calculations do not establish publication novelty or method superiority.
"""
import argparse
import json
import math
from pathlib import Path
import numpy as np
from scipy.integrate import quad
from scipy.special import expit
from scipy.stats import chi2, norm

ROOT=Path(__file__).resolve().parents[3]


def replay():
 A=np.array([[1.01,.1],[0,.98]]);old=np.array([1.2,-.7]);new=np.array([1.3,-.65])
 rows=[]
 for current_gap,source_gap in [(3,3),(3,1)]:
  left=new-np.linalg.matrix_power(A,current_gap)@old
  hist=new-np.linalg.matrix_power(A,source_gap)@old
  mismatch=(np.linalg.matrix_power(A,source_gap)-np.linalg.matrix_power(A,current_gap))@old
  assert np.allclose(left,hist+mismatch)
  rows.append({'current_gap':current_gap,'source_gap':source_gap,'temporal_replay_residual':left.tolist(),
               'historical_normal_residual':hist.tolist(),'gap_mismatch_term':mismatch.tolist()})
 return {'status':'PROVED_ALGEBRA_WITH_NUMERIC_CHECK','rows':rows,
         'limitation':'matched intervals remove only the mismatch term; do not imply full record indistinguishability'}


def reflection():
 own=np.array([.4,-.2]);neighbor=np.array([1.,.7]);precision=np.array([[2.,.3],[.3,1.]])
 reflected=2*own-neighbor;d=neighbor-own
 original=float(d@precision@d);attacked=float((reflected-own)@precision@(reflected-own))
 assert np.isclose(original,attacked,rtol=1e-14,atol=1e-14)
 return {'status':'PROVED_ALGEBRA_WITH_NUMERIC_CHECK','own':own.tolist(),'neighbor':neighbor.tolist(),
 'reflected':reflected.tolist(),'normal_statistic':original,'attacked_statistic':attacked,
 'required_attacker_data':'current receiver and sender estimates; unavailable current receiver values cannot be silently assumed',
 'limitation':'same statistic preserves the original alarm event, not guaranteed acceptance on every noisy sample'}


def temporal_fdi():
 A=np.diag([1.01,.98]);previous=np.array([.5,-.3]);gap=5
 current=np.linalg.matrix_power(A,gap)@previous
 delta=current-np.linalg.matrix_power(A,gap)@previous
 constant=previous-np.linalg.matrix_power(A,gap)@previous
 assert np.linalg.norm(delta)==0
 return {'status':'PROVED_ALGEBRA_WITH_NUMERIC_CHECK','dynamic_consistent_increment':delta.tolist(),
 'constant_bias_temporal_increment':constant.tolist(),
 'limitation':'attack switch boundary and local measurement evidence may still reveal the attack'}


def covariance_floor():
 cache_var,measurement_var,bias=1.,.2,.3
 rows=[{'prefix_length':L,'variance_of_mean':cache_var+measurement_var/L,
        'bias_noncentrality':bias*bias/(cache_var+measurement_var/L)} for L in [1,2,8,32,1000]]
 return {'status':'PROVED_FOR_SIMPLIFIED_MODEL','model':'A=C=1, Q=0; independent cache error and fresh measurement noises; no event selection',
 'rows':rows,'limitation':'uncertainty from the shared cached estimate does not vanish by averaging later measurements'}


def correlated_window():
 threshold=float(chi2.ppf(.95,2));corr=.5
 fn=lambda theta:math.exp(-threshold/(2*((1+corr)*math.cos(theta)**2+(1-corr)*math.sin(theta)**2)))
 tail,err=quad(fn,0,2*math.pi,epsabs=1e-13,epsrel=1e-13)
 tail/=2*math.pi
 return {'status':'PROVED_STRUCTURE_QUADRATURE_VALUE','normal_marginal':'each component N(0,1)',
 'attack':'z_t^a=(z_t+z_{t-1})/sqrt(2), z_t iid N(0,1)',
 'lag1_correlation':corr,'two_step_energy_threshold':threshold,'nominal_window_alarm_probability':.05,
 'attacked_window_alarm_probability':tail,'quadrature_error_reported':err/(2*math.pi),
 'window_variance_nominal':4.,'window_variance_attacked':4*(1+corr*corr),
 'limitation':'one-step marginal matching does not imply a same-law sliding-window statistic'}


def leaky():
 rows=[]
 for lam in [.8,.96,.99]:
  limit=1/(1-lam);rows.append({'lambda':lam,'constant_LLR':1.,'finite_logodds_limit':limit,'trust_limit':float(expit(limit))})
 return {'status':'PROVED_RECURRENCE','rows':rows,
 'general_relation':'E ell_k=lambda^k E ell_0 + mu(1-lambda^k)/(1-lambda)',
 'limitation':'positive/negative expected LLR alone is not an endpoint trust convergence proof when lambda<1'}


def gaussian_complement():
 sig2=1.;nu=1.;accept_mass=(1+2*sig2/nu)**(-.5)
 v=1/(1/sig2+2/nu)
 reject_mass=1-accept_mass
 m2=(sig2-accept_mass*v)/reject_mass
 m4=(3*sig2**2-accept_mass*3*v*v)/reject_mass
 rows=[{'u':u,'kappa_required_for_1minus_exp_equal_exp':-math.log(-math.expm1(-u))-u} for u in [.1,.5,1.,2.]]
 return {'status':'PROVED_DENSITY_IDENTITY','reject_density':'phi_sigma(d)*(1-exp(-d^2/nu))/(1-E exp(-D^2/nu))',
 'reject_conditional_variance':m2,'reject_conditional_fourth_cumulant':m4-3*m2*m2,
 'kappa_values':rows,'limitation':'a difference of Gaussian densities cannot in general be replaced by a single centered Gaussian density'}


def matrix_order():
 B=np.diag([0.,1.]);A=np.diag([1.,1.]);P=np.array([[1.,.9],[.9,1.]])
 difference=A@P@A.T-B@P@B.T
 eig=np.linalg.eigvalsh(difference)
 assert np.all(np.linalg.eigvalsh(A-B)>=0) and eig.min()<0
 return {'status':'PROVED_ALGEBRA_COUNTEREXAMPLE_TO_AN_INFERENCE','A':A.tolist(),'B':B.tolist(),'P':P.tolist(),
 'A_minus_B_PSD':True,'eigenvalues_APAT_minus_BPBT':eig.tolist(),
 'limitation':'not a counterexample to a full paper theorem; disproves only unrestricted order propagation A>=B => APA^T>=BPB^T'}


def qian_moment():
 variance=2.;bound=1.;z=bound/math.sqrt(variance)
 beta=2*z*norm.pdf(z)/(2*norm.cdf(z)-1)
 return {'status':'PROVED_GAUSSIAN_REGRESSION','parameters':{'var_tau':1,'var_epsilon':1,'bound':bound},
 'true_conditional_cross_moment':1-beta,'printed_formula_value':1.,
 'limitation':'the printed equality is distinct from the weaker conservative inequality used later in the paper'}


def conditional_reference():
 # Analytic toy distribution only, NOT a fitted or validated network model.
 # r is a private local innovation; d is neighbor-minus-local prediction.
 # A reflection preserves d^2, but not the correlation between r and d.
 rows=[]
 for correlation in [0.,.25,.5,.8]:
  variance=1-correlation*correlation
  score_variance_attacked=(1+3*correlation*correlation)/variance
  rows.append({'normal_correlation':correlation,
   'state_difference_energy_distribution_unchanged':True,
   'conditional_statistic_normal_mean':1.,
   'conditional_statistic_reflection_mean':score_variance_attacked,
   'KL_joint_reflection_vs_normal':2*correlation*correlation/variance})
 return {'status':'PROVED_FOR_STATED_JOINT_GAUSSIAN_TOY_MODEL',
  'normal_covariance':'[[1,c],[c,1]] for [private local innovation r, neighbor difference d]',
  'reflection':'d -> -d with r unchanged',
  'conditional_statistic':'(d-c*r)^2/(1-c^2)',
  'rows':rows,
  'limitation':'does not prove advantage over Zhou spatial residual, fitted-covariance window tests or adaptive attackers; no network simulation performed'}


CASES={k:v for k,v in globals().copy().items() if k in
 ['replay','reflection','temporal_fdi','covariance_floor','correlated_window','leaky','gaussian_complement','matrix_order','qian_moment','conditional_reference']}


if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--case',choices=list(CASES)+['all'],required=True);ap.add_argument('--output',type=Path,required=True);args=ap.parse_args()
 args.output.mkdir(parents=True,exist_ok=False)
 for key in CASES if args.case=='all' else [args.case]:
  out=CASES[key]();(args.output/(key+'.json')).write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf8');print(key,'saved')
