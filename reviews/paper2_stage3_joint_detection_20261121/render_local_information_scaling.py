"""Deterministic fixed-history KL scaling illustration; no performance samples."""
from __future__ import annotations

from decimal import Decimal, localcontext
import hashlib
import json
from pathlib import Path

import numpy as np

from check_joint_reference import MODELS, all_send_riccati, fisher, joint_kl, silent

HERE=Path(__file__).resolve().parent


def decimal_event_kl(S,Z,h,b):
    with localcontext() as ctx:
        ctx.prec=80
        one=Decimal(1)
        S,Z,h,b=(Decimal.from_float(float(v)) for v in (S,Z,h,b))
        V=S+one/Z
        p0=one/(one+Z*S).sqrt()
        p1=p0*(-h*h*b*b/(2*V)).exp()
        return float(p1*(p1/p0).ln()+(one-p1)*((one-p1)/(one-p0)).ln())


def main():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.ticker import NullFormatter
    plt.rcParams.update({"font.family":"DejaVu Sans","font.size":10,"pdf.fonttype":42,
                         "axes.spines.top":False,"axes.spines.right":False})
    amplitudes=np.array([.0025,.005,.01,.025,.05])
    h=-.5
    rows=[]
    fig,axes=plt.subplots(1,2,figsize=(10.5,4.5),constrained_layout=True)
    for ax,model in zip(axes,MODELS):
        P=all_send_riccati(model)
        S=P+model["R"]
        V=S+1/model["Z"]
        p0=silent(P,model["R"],model["Z"],0.,0.)
        I=fisher(P,model["R"],model["Z"],0.,h)["joint_Fisher"]
        event_coefficient=p0*h**4/(8*V*V*(1-p0))
        joint_values=[]
        event_values=[]
        for b in amplitudes:
            joint,error=joint_kl(P,model["R"],model["Z"],0.,h,float(b))
            event=decimal_event_kl(S,model["Z"],h,b)
            quadratic=I*b*b/2
            quartic=event_coefficient*b**4
            if not (0 < event < joint):
                raise AssertionError("Event projection information cannot exceed joint information")
            joint_values.append(joint);event_values.append(event)
            rows.append({"model":model["id"],"prior_variance":P,"center_residual":0.,
                         "candidate_prior_bias_over_b":h,"b":float(b),
                         "joint_KL":joint,"joint_quadrature_error_estimate":error,
                         "joint_Fisher_local_b2_over_2":quadratic,
                         "joint_to_local_ratio":joint/quadratic,
                         "phase_conditioned_event_KL":event,
                         "symmetric_event_leading_b4":quartic,
                         "event_to_local_ratio":event/quartic})
        ax.loglog(amplitudes,joint_values,"o-",color="#0072B2",label="Joint event + payload KL")
        ax.loglog(amplitudes,.5*I*amplitudes**2,"--",color="#0072B2",alpha=.65,label="Joint local Fisher term")
        ax.loglog(amplitudes,event_values,"s-",color="#D55E00",label="Event-only KL, fixed r = 0")
        ax.loglog(amplitudes,event_coefficient*amplitudes**4,"--",color="#D55E00",alpha=.65,
                  label="Symmetric event local term")
        ax.set(title=f"{model['id']}: fixed P = {P:.6f}, d = -b/2",
               xlabel="Payload shift b",ylabel="One-observation KL (nats)")
        ax.set_xticks(amplitudes,["0.0025","0.005","0.01","0.025","0.05"])
        ax.xaxis.set_minor_formatter(NullFormatter())
        ax.set_ylim(6e-13,5e-3)
        ax.grid(which="major",alpha=.2)
        ax.legend(fontsize=8,loc="best")
    fig.suptitle("Deterministic local kernel check: fixed history and center",fontsize=12)
    folder=HERE/"figures"
    folder.mkdir(exist_ok=True)
    for ext in ("pdf","png"):
        fig.savefig(folder/("04_local_information_scaling."+ext),dpi=180)
    plt.close(fig)
    output={"status":"PASS","performance_random_samples_generated":False,
        "purpose":"Deterministic local-kernel illustration, not an experiment on sequential detection power.",
        "conditioning":"P fixed at all-send Riccati prior, r=0, d=-b/2, same current observation kernel.",
        "event_curve_is_phase_conditioned_not_phase_averaged":True,
        "event_b4_curve_not_claimed_for_arbitrary_nonzero_r":True,
        "fixed_center_curve_does_not_attribute_gain_to_phase_randomization":True,
        "reference_source_sha256":hashlib.sha256((HERE/"check_joint_reference.py").read_bytes()).hexdigest(),
        "script_sha256":hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "rows":rows}
    (HERE/"local_information_scaling_checks.json").write_text(
        json.dumps(output,indent=2,allow_nan=False)+"\n",encoding="utf8")
    print(json.dumps({"status":"PASS","rows":len(rows),
        "max_joint_local_relative_error":max(abs(r["joint_to_local_ratio"]-1) for r in rows),
        "performance_random_samples_generated":False}))


if __name__=="__main__":
    main()
