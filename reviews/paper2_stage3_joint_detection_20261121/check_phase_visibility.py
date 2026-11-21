"""Deterministic validation of hidden-phase center and index kernels."""
import json,math
from pathlib import Path
import numpy as np
from scipy.integrate import quad
from phase_visibility import (codeword_intervals,center_kernel,index_kernel,
    phase_only_event_kl,center_phase_only_event_kl)

HERE=Path(__file__).resolve().parent
p=json.loads((HERE/"protocol.json").read_text(encoding="utf8"))
checks=[]
max_mass=0.;max_projection=0.;max_silent_event_share=0.
for model in p["models"]:
    delta=model["delta"];Z=model["Z"];S=.35
    for mean in (-3.3*delta,0.,.2*delta,.8*delta,delta,1.7*delta,4*delta):
        cells=codeword_intervals(mean,delta)
        assert abs(sum(x["phase_hi"]-x["phase_lo"] for x in cells)-2*delta)<1e-13
        for cell in cells:
            assert -delta-1e-13<=cell["r_lo"]<cell["r_hi"]<=delta+1e-13
            w=(cell["phase_hi"]-cell["phase_lo"])/(2*delta)
            for d,b in ((0.,0.),(-.03,.05),(-.15,.25)):
                bound=12*math.sqrt(S)+abs(b)+2*delta
                sentmass=quad(lambda u:float(index_kernel(S,S,d,b,cell["r_lo"],cell["r_hi"],Z,u)),
                              -bound,bound,points=[b+cell["r_lo"],b+cell["r_hi"]],
                              epsabs=2e-12,limit=300)[0]
                total=float(index_kernel(S,S,d,b,cell["r_lo"],cell["r_hi"],Z))+sentmass
                max_mass=max(max_mass,abs(total-1.))
        # Index-projected kernel and full center phase average are identical
        # after the actual codeword label is marginalized.
        for u in (-.4,-.02,.1,.7):
            for d,b in ((0.,0.),(-.03,.05),(-.15,.25)):
                idx=sum((c["phase_hi"]-c["phase_lo"])/(2*delta)*
                        float(index_kernel(S,S,d,b,c["r_lo"],c["r_hi"],Z,u)) for c in cells)
                center=quad(lambda r:float(center_kernel(S,S,d,b,r,Z,u)),
                            -delta,delta,epsabs=1e-13,epsrel=1e-12)[0]/(2*delta)
                max_projection=max(max_projection,abs(idx-center))
        idxsilent=sum((c["phase_hi"]-c["phase_lo"])/(2*delta)*
                      float(index_kernel(S,S,-.03,.05,c["r_lo"],c["r_hi"],Z)) for c in cells)
        centerSilent=quad(lambda r:float(center_kernel(S,S,-.03,.05,r,Z)),
                          -delta,delta,epsabs=1e-13)[0]/(2*delta)
        max_silent_event_share=max(max_silent_event_share,abs(idxsilent-centerSilent))
        checks.append({"model":model["id"],"mean_offset_over_delta":mean/delta,
                       "index_cells":len(cells)})
    local_orders=[]
    for b in (.01,.005,.0025):
        aligned=phase_only_event_kl(0.,delta,b,S,Z)
        split=phase_only_event_kl(.5*delta,delta,b,S,Z)
        center=center_phase_only_event_kl(delta,b,S,Z)
        local_orders.append({"model":model["id"],"shift":b,
            "aligned_codeword_KL":aligned,"aligned_KL_over_b2":aligned/b**2,
            "aligned_KL_over_b4":aligned/b**4,
            "split_codeword_KL":split,"split_KL_over_b2":split/b**2,
            "exact_center_KL":center,"exact_center_KL_over_b2":center/b**2})
    checks[-1]["local_information_order_checks"]=local_orders
    # phase-mean identity: summing center conditional event likelihood
    # recovers the old phase-marginal probability.
    for d in (0.,.03,.1):
        phaseavg=quad(lambda r:float(center_kernel(S,S,d,0.,r,Z)),
                      -delta,delta,epsabs=1e-13)[0]/(2*delta)
        V=S+1/Z
        from scipy.special import ndtr
        analytic=(1/math.sqrt(1+Z*S))*math.sqrt(2*math.pi*V)/(2*delta)*(
            ndtr((delta-d)/math.sqrt(V))-ndtr((-delta-d)/math.sqrt(V)))
        assert abs(phaseavg-analytic)<1e-12
out={"status":"PASS","performance_random_samples_generated":False,
     "max_center_to_codeword_projection_error":max_projection,
     "max_codeword_kernel_normalization_error":max_mass,
     "max_silent_event_projection_error":max_silent_event_share,
     "local_order_note":"KL ratios are deterministic fixed-kernel diagnostics, not trajectory power estimates.",
     "checks":checks}
(HERE/"phase_visibility_checks.json").write_text(json.dumps(out,indent=2)+"\n",encoding="utf8",newline="\n")
print(json.dumps({k:out[k] for k in ("status","max_center_to_codeword_projection_error",
      "max_codeword_kernel_normalization_error","max_silent_event_projection_error")},indent=2))
