"""Independent scalar k=0 quadrature of Appendix B's full two-step record law.

No manuscript calculation modules are imported. Both the silent atom and the
continuous payload pair are integrated. Numerical diagnostics only: finite-box
floating-point quadrature is not a rigorous interval proof or a vector-TV test.
"""
from pathlib import Path
import hashlib,json,math
import numpy as np
from scipy.special import roots_legendre

A,P0,Q,R,Z=.8,.8,.05,.2,2.
S=P0+R; K=P0/S; Ps=P0-P0*P0/S; Sp=A*A*Ps+Q+R
sh=(1+Z*S)**-.5; ph=1-sh; T=1/(1/S+Z); u=A*K
F1=math.sqrt(2/math.pi)*(1/math.sqrt(S)+sh/math.sqrt(T))
F2=2*(1/S+sh/T);a=u*u*Z
Cpm=(F2+4*F1*math.sqrt(a/math.e)+2*ph*a)/4
amps=[.025,.05,.1]
Lz=10*math.sqrt(S)+max(amps);Le=10*math.sqrt(Sp)
def phi(x,var):return np.exp(-x*x/(2*var))/math.sqrt(2*math.pi*var)
def f(x):return phi(x,S)*(-np.expm1(-Z*x*x/2))
def calculate(order):
    grid,weight=roots_legendre(order)
    z=Lz*grid;wz=Lz*weight;e=Le*grid;we=Le*weight
    pe=phi(e,Sp)
    def law(t):
        d=-t*u;fz=f(z-t);g=np.exp(-Z*(e+d)**2/2)
        atom_probability=float(np.dot(we,pe*g))
        exact=(1+Z*Sp)**-.5*math.exp(-d*d/(2*(1/Z+Sp)))
        assert abs(atom_probability-exact)<2e-12
        return fz*atom_probability,np.outer(fz,pe*(1-g))
    s0,c0=law(0.)
    def total(s,c):return float(np.dot(wz,s)+wz@c@we)
    def tv(s,c):return .5*float(np.dot(wz,np.abs(s))+wz@np.abs(c)@we)
    rows=[]
    for eta in amps:
        sp,cp=law(eta);sm,cm=law(-eta)
        ds=(sp+sm)/2-s0;dc=(cp+cm)/2-c0
        mass=total((sp+sm)/2,(cp+cm)/2)
        mixed=tv(ds,dc)
        public=.5*(tv(sp-s0,cp-c0)+tv(sm-s0,cm-c0))
        delta_event=abs(float(np.dot(wz,ds)))
        assert abs(mass-ph)<2e-12
        assert delta_event<=mixed+1e-12 and mixed<=public+1e-12
        assert mixed<Cpm*eta**2
        rows.append(dict(eta=eta,mixed_full_TV=mixed,TV_over_eta_squared=mixed/eta**2,
                         visible_sign_TV=public,event_TV=delta_event,
                         analytic_TV_upper=Cpm*eta**2,mass_residual=abs(mass-ph),
                         signed_total_mass_difference=total(ds,dc)))
    return rows
levels={str(n):calculate(n) for n in (128,256,512)}
changes=[]
for coarse,fine in zip(levels['256'],levels['512']):
    relative=abs(fine['mixed_full_TV']-coarse['mixed_full_TV'])/fine['mixed_full_TV']
    assert relative<.003
    changes.append(relative)
# All constituent laws are dominated by shifted Gaussian z and Gaussian e.
# Outside the chosen box, a union bound gives at most 4 Phi(-10).
# This analytic tail estimate has floating-point evaluation; no interval claim.
tail=2*math.erfc(10/math.sqrt(2))
result=dict(passed=True,scope='Independent scalar k=0 diagnostic of the joint record kernel; no production imports.',
            parameters=dict(A=A,P0=P0,Q=Q,R=R,Z=Z,k=0),C_pm=Cpm,
            rectangle_halfwidths=dict(z=Lz,e=Le),gaussian_tail_bound_float=tail,
            quadrature=levels,relative_change_256_to_512=changes,
            no_monte_carlo=True,rigorous_interval_verification=False,
            code_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
Path(__file__).with_suffix('.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
print(json.dumps(dict(passed=True,C_pm=Cpm,rows=levels['512'],relative_changes=changes),indent=2))
