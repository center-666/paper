"""Task 3: saved Gaussian moments, deterministic integration, no sampled paths."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import time

import numpy as np
from scipy.integrate import quad
from scipy.optimize import brentq
from scipy.special import erfc, i0e
from scipy.stats import norm

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(path, value):
    def native(x):
        if isinstance(x, np.ndarray):
            return x.tolist()
        if isinstance(x, np.generic):
            return x.item()
        raise TypeError(type(x).__name__)
    Path(path).write_text(json.dumps(value,default=native,indent=2,allow_nan=False)+"\n",
                          encoding="utf-8",newline="\n")


def amplitude(c, alpha, risk):
    """Stable positive root of alpha U^2+2cU=risk."""
    return risk / (np.sqrt(c*c+alpha*risk)+c)


def polar_tail(eigenvalues, alpha, plan):
    lo, hi = sorted(map(float,eigenvalues))
    assert lo >= 0 and hi >= 0 and 0 < alpha < 1
    if hi == 0:
        return {"quantile":0.,"tail_first_moment":0.,"method":"rank zero"}
    if lo == 0:
        q = np.sqrt(hi)*norm.isf(alpha/2)
        c = np.sqrt(hi*2/np.pi)*np.exp(-q*q/(2*hi))
        return {"quantile":q,"tail_first_moment":c,"method":"rank one half normal"}
    factor = 2/np.pi
    options = {"epsabs":plan["quadrature_epsabs"],"epsrel":plan["quadrature_epsrel"],"limit":200}

    def variance(phi):
        return hi*np.cos(phi)**2+lo*np.sin(phi)**2

    def survival(t):
        v,error = quad(lambda phi:np.exp(-t*t/(2*variance(phi))),0,np.pi/2,**options)
        return factor*v,factor*error

    upper = np.sqrt(hi)*np.sqrt(-2*np.log(alpha))*(1+1e-12)+plan["root_xtol"]
    q,root = brentq(lambda t:survival(t)[0]-alpha,0,upper,
                   xtol=plan["root_xtol"],rtol=plan["root_rtol"],full_output=True)
    mass,mass_error = survival(q)

    def moment_integrand(phi):
        v = variance(phi)
        return q*np.exp(-q*q/(2*v))+np.sqrt(v*np.pi/2)*erfc(q/np.sqrt(2*v))

    c,c_error = quad(moment_integrand,0,np.pi/2,**options)
    c,c_error = factor*c,factor*c_error
    derivative,derivative_error = quad(lambda phi:q/variance(phi)*np.exp(-q*q/(2*variance(phi))),
                                      0,np.pi/2,**options)
    derivative *= factor
    q_error_estimate = ((abs(mass-alpha)+mass_error)/derivative
                        + plan["root_xtol"]+plan["root_rtol"]*abs(q))

    # Independent radial PDF: I0e keeps the Bessel/exponential product stable.
    b = abs(1/lo-1/hi)/4

    def pdf(radius):
        return radius/np.sqrt(hi*lo)*np.exp(-radius*radius/(2*hi))*i0e(b*radius*radius)

    radial_mass,radial_mass_error = quad(pdf,q,np.inf,**options)
    radial_c,radial_c_error = quad(lambda radius:radius*pdf(radius),q,np.inf,**options)

    # variance decreases over a quadrant, yielding monotone Riemann bounds.
    panels = int(plan["monotone_angular_panels"])
    phi = np.linspace(0,np.pi/2,panels+1)
    v = hi*np.cos(phi)**2+lo*np.sin(phi)**2

    def mesh_survival(t,left):
        values = np.exp(-t*t/(2*v))
        return float(np.mean(values[:-1] if left else values[1:]))

    qlow = brentq(lambda t:mesh_survival(t,False)-alpha,0,upper,
                  xtol=plan["root_xtol"],rtol=plan["root_rtol"])
    qhigh = brentq(lambda t:mesh_survival(t,True)-alpha,0,upper,
                   xtol=plan["root_xtol"],rtol=plan["root_rtol"])
    root_pad = plan["root_xtol"]+plan["root_rtol"]*upper
    qlow, qhigh = max(0.,qlow-root_pad), qhigh+root_pad

    def mesh_moment(t,left):
        values = t*np.exp(-t*t/(2*v))+np.sqrt(v*np.pi/2)*erfc(t/np.sqrt(2*v))
        return float(np.mean(values[:-1] if left else values[1:]))

    clow = mesh_moment(qhigh,False)
    chigh = mesh_moment(qlow,True)
    assert qlow <= q <= qhigh
    assert clow <= c <= chigh
    assert abs(radial_c-c) < 1e-10
    assert abs(radial_mass-alpha) < 1e-10
    return {
        "method":"anisotropic 2D Gaussian polar integral + independent Bessel radial integral",
        "quantile":q,"tail_probability_at_quantile":mass,
        "tail_first_moment":c,"root_converged":root.converged,"root_iterations":root.iterations,
        "quadrature_abs_error_estimates":{"probability":mass_error,"moment":c_error,
                                           "radial_probability":radial_mass_error,"radial_moment":radial_c_error},
        "root_local_error_estimate":q_error_estimate,
        "moment_local_total_error_estimate":c_error+q*derivative*q_error_estimate,
        "independent_radial_probability":radial_mass,"independent_radial_moment":radial_c,
        "polar_radial_moment_difference":abs(radial_c-c),
        "monotone_riemann_panels":panels,"quantile_discretization_bracket":[qlow,qhigh],
        "tail_moment_discretization_bracket":[clow,chigh],
        "bracket_note":plan["roundoff_note"],
    }


def exact_special_case_tests(plan):
    alpha = .05
    v = .09
    isotropic = polar_tail([v,v],alpha,plan)
    expected_q = np.sqrt(v)*np.sqrt(-2*np.log(alpha))
    expected_c = expected_q*alpha+np.sqrt(v*np.pi/2)*erfc(expected_q/np.sqrt(2*v))
    assert np.isclose(isotropic["quantile"],expected_q,atol=1e-12)
    assert np.isclose(isotropic["tail_first_moment"],expected_c,atol=1e-12)
    rank_one = polar_tail([0.,.04],alpha,plan)
    a = norm.isf(alpha/2)
    half_normal_tail = .4*norm.pdf(a)
    assert np.isclose(rank_one["tail_first_moment"],half_normal_tail,atol=1e-14)
    assert polar_tail([0.,0.],alpha,plan)["tail_first_moment"] == 0
    return {"isotropic_rayleigh_closed_form":"PASS","rank_one_half_normal":"PASS","rank_zero":"PASS"}


def main(out):
    out = Path(out)
    out.mkdir(parents=True,exist_ok=False)
    started = time.perf_counter()
    plan_path = HERE/"sources/task3_normalrisk_20261114/calculation_plan.json"
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    matrix_path,summary_path = ROOT/plan["input_matrices"],ROOT/plan["input_summary"]
    old_summary = json.loads(summary_path.read_text(encoding="utf-8"))
    source_paths = [Path(__file__),plan_path,matrix_path,summary_path,HERE/"protocol_v1.json"]
    write(out/"frozen_plan.json",{
        "run_id":out.name,"baseline_commit":subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT).decode().strip(),
        "plan":plan,"source_sha256":{p.relative_to(ROOT).as_posix():sha(p) for p in source_paths},
        "new_trajectories":0,"seeds_used":[],
    })
    try:
        with np.load(matrix_path,allow_pickle=False) as data:
            eta,e0 = data['eta_loading'],data['e0_loading']
            S = data['Sigma_eta']
            C = e0@eta.T
            covariance_error = float(np.max(np.abs(S-eta@eta.T)))
            assert covariance_error < 1e-12
            B = np.linalg.solve(S,C.T).T
            Mloading = B@eta
            Sm = C@B.T
            Sm = (Sm+Sm.T)/2
            P0 = e0@e0.T
            coefficient_covariance_error = float(np.max(np.abs(Sm-Mloading@Mloading.T)))
            residual_cross = float(np.max(np.abs((e0-Mloading)@eta.T)))
            reconstruction_errors = [float(np.max(np.abs(
                data['Sigma_e0_z'][k]-data['Sigma_e0_theta'][k]@data['O'][k].T-C)))
                for k in range(len(data['case_edge_r_age']))]
        eigenvalues = np.linalg.eigvalsh(Sm)
        assert eigenvalues[0] > 0
        assert np.linalg.eigvalsh(P0-Sm)[0] > 0
        assert max(reconstruction_errors) < 1e-10
        assert max(coefficient_covariance_error,residual_cross) < 1e-12
        alpha = plan['alpha']
        J0,Ja = old_summary['J0_actual_cached'],old_summary['main_case']['Ja']
        assert np.isclose(J0,np.trace(P0),atol=1e-12)
        risk = plan['normal_R_over_J0']*J0
        old_c = np.sqrt(alpha*J0)
        conditional_cs_c = np.sqrt(alpha*np.trace(Sm))
        tail = polar_tail(eigenvalues,alpha,plan)
        c = tail['tail_first_moment']
        clow,chigh = tail['tail_moment_discretization_bracket']
        assert c <= conditional_cs_c <= old_c
        Uold = amplitude(old_c,alpha,risk)
        Ucs = amplitude(conditional_cs_c,alpha,risk)
        Unew = amplitude(c,alpha,risk)
        Uinterval = [amplitude(chigh,alpha,risk),amplitude(clow,alpha,risk)]
        Ureq = np.sqrt(Ja)*plan['target_relative_attack_gain']/(1+np.sqrt(1-plan['target_relative_attack_gain']))
        assert np.isclose(Uold,old_summary['main_budget']['U'],atol=1e-14)
        for coeff,U in [(old_c,Uold),(conditional_cs_c,Ucs),(c,Unew)]:
            assert np.isclose(alpha*U*U+2*coeff*U,risk,atol=1e-14)
        decision = 'B' if Uinterval[0] >= Ureq else 'A' if Uinterval[1] < Ureq else 'NUMERICALLY_UNRESOLVED'
        write(out/'normal_risk_moments.json',{
            'C_0_eta':C,'Sigma_eta':S,'B_normal_conditional_mean':B,'Sigma_m':Sm,
            'P0':P0,'residual_error_covariance':P0-Sm,'Sigma_m_eigenvalues':eigenvalues,
        })
        checks = {'saved_vs_coefficient_Sigma_eta_absolute_error':covariance_error,
                  'conditional_loading_covariance_absolute_error':coefficient_covariance_error,
                  'unpredictable_error_innovation_cross_absolute':residual_cross,
                  'max_normal_C_reconstructed_from_24_attack_cases_error':max(reconstruction_errors),
                  'Gaussian_degenerate_and_isotropic_tests':exact_special_case_tests(plan),
                  'risk_positive_root_identities':'PASS','old_cap_reproduced':'PASS',
                  'conditional_Cauchy_alone_passes_required_amplitude':bool(Ucs>=Ureq),
                  'new_random_trajectories':0}
        write(out/'checks.json',checks)
        write(out/'summary.json',{
            'run_id':out.name,'case_decision':decision,
            'J0':J0,'Ja_main':Ja,'normal_risk_budget_R':risk,'alpha':alpha,
            'predictable_error_second_moment':float(np.trace(Sm)),
            'predictable_fraction_of_J0':float(np.trace(Sm)/J0),
            'Sigma_m':Sm,'Sigma_m_eigenvalues':eigenvalues,
            'c_old_Cauchy':old_c,'c_conditional_Cauchy':conditional_cs_c,'c_alpha':c,
            'U_old':Uold,'U_conditional_Cauchy':Ucs,'U_new':Unew,
            'U_new_discretization_bracket':Uinterval,
            'U_new_over_U_old':Unew/Uold,'U_required_for_one_percent_gain':Ureq,
            'U_new_over_U_required':Unew/Ureq,
            'remaining_any_capped_action_gain_ceiling':1-max(1-Unew/np.sqrt(Ja),0.)**2,
            'tail_integration':tail,'checks':checks,
            'interpretation':'B means old amplitude exclusion removed only; no actual attack benefit, no v2, no E2/E3',
            'new_trajectories':0,'seeds_used':[],'downloads':0,
            'elapsed_seconds':time.perf_counter()-started,
        })
        print(json.dumps({'case_decision':decision,'c_alpha':c,'U_old':Uold,'U_conditional_Cauchy':Ucs,
                          'U_new':Unew,'U_new_discretization_bracket':Uinterval,'U_required':Ureq,
                          'new_trajectories':0,'elapsed_seconds':time.perf_counter()-started}))
    except Exception as exc:
        write(out/'failure.json',{'type':type(exc).__name__,'message':str(exc),'new_trajectories':0})
        raise


if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--out',required=True)
    main(parser.parse_args().out)
