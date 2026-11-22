"""Deterministic exploratory minimization of bounded joint-kernel features.
No optimization output is itself a global certificate.
"""
import json
from pathlib import Path
import sys
import numpy as np
from scipy.optimize import minimize

HERE=Path(__file__).resolve().parent
PREV=HERE.parent/"paper2_stage4_certified_correction_20261122"
sys.path.insert(0,str(PREV))
from compute_separation_bounds import constants
from check_certificate import MODELS

FREQUENCIES=np.array([1.,2.,3.,4.,5.,6.,8.])


def feature(S,z,a):
    omega=FREQUENCIES
    den=1+2*S;V=S+.5
    G=np.exp(-z*z/(2*V))/np.sqrt(den)
    return np.exp(1j*omega*a)*(np.exp(-S*omega**2/2+1j*omega*z)
           -G*np.exp(-S/den*omega**2/2+1j*omega*z/den))


def objective(x,gap):
    S,z1,z2=x
    return np.max(np.abs(feature(S,z1,gap)-feature(S,z2,0.)))**2/8


def main():
    rows=[]
    for model in MODELS:
        c=constants(model)
        slo=float(c["smin"].lo);shi=float(c["smax"].hi)
        zlo=-float(c["Dprior"].hi)-float(model["delta"]);zhi=float(model["delta"])
        bounds=[(slo,shi),(zlo,zhi),(zlo,zhi)]
        for gap in (.15,.2,.25):
            best=None
            for S in (slo,(slo+shi)/2,shi):
                for z1 in (zlo,(zlo+zhi)/2,zhi):
                    for z2 in (zlo,zhi):
                        r=minimize(lambda x:objective(x,gap),[S,z1,z2],bounds=bounds,
                                   method="Powell",options={"maxiter":300,"xtol":1e-10,"ftol":1e-10})
                        if best is None or r.fun<best.fun:best=r
            rows.append({"model":model["id"],"amplitude_gap":gap,
                         "exploratory_min_feature_gap":float(best.fun),
                         "argmin":best.x.tolist(),"box":bounds})
    out={"random_samples_generated":False,"is_global_certificate":False,
         "frequencies":FREQUENCIES.tolist(),"rows":rows}
    (HERE/"fourier_exploration.json").write_text(json.dumps(out,indent=2)+"\n",encoding="utf8")
    for r in rows:print(r)

if __name__=="__main__":main()
