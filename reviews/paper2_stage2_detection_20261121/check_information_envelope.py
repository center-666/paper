"""Independent deterministic quadrature/interval audit of the information cap."""
import json
from pathlib import Path
import numpy as np
from numpy.polynomial.legendre import leggauss
from core import silence, bernoulli_kl
from information_upper_bounds import analytic_bounds, binary_power_upper

HERE=Path(__file__).resolve().parent
protocol=json.loads((HERE/"protocol.json").read_text(encoding="utf8"))
nodes,weights=leggauss(80)
checks=[]
for model in protocol["models"]:
    for b in protocol["attack_strengths"]:
        bounds=analytic_bounds(model,b)
        Plo=model["R"]*bounds["send_gain_lower"]
        r0=model["R"]+1/model["Z"]
        p_hi=bounds["prior_variance_upper"]
        Phi=p_hi*r0/(p_hi+r0)
        P=np.linspace(Plo,Phi,101)[None,:]
        D=np.linspace(-bounds["analysis_bias_absolute_upper"],
                      bounds["analysis_bias_absolute_upper"],101)[:,None]
        p=silence(P,D,model)
        nu=silence(P,0.,model)
        value=bernoulli_kl(p,nu)
        upper=bounds["conditional_Bernoulli_KL_upper_per_step"]
        assert np.max(value)<=upper+1e-12
        assert np.min(value)>=-1e-14
        for pp in (Plo,(Plo+Phi)/2,Phi):
            dd=-bounds["analysis_bias_absolute_upper"]
            V=1/model["Z"]+model["A"]**2*pp+model["Q"]+model["R"]
            quad=float(np.dot(weights/2,np.exp(-(model["A"]*dd-model["delta"]*nodes)**2/(2*V))))/np.sqrt(model["Z"]*V)
            cdf=float(silence(pp,dd,model))
            assert abs(quad-cdf)<2e-14
        k=.8*np.log(.8/.01)+.2*np.log(.2/.99)
        assert abs(binary_power_upper(k,.01)-.8)<1e-12
        checks.append({"model":model["id"],"b":b,"grid_points":10201,
                       "largest_KL_on_grid":float(np.max(value)),
                       "analytic_upper":upper,"status":"PASS"})
(HERE/"information_envelope_checks.json").write_text(
    json.dumps({"status":"PASS","random_samples_generated":False,
                "scope":"Grid and independent quadrature validate formulas; analytic proof is separate.",
                "checks":checks},indent=2)+"\n",encoding="utf8")
print(json.dumps({"status":"PASS","cases":len(checks)}))
