"""Exploratory exact event-count analysis on frozen test inputs; no new RNG."""
from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np
from scipy.stats import binom,binomtest

from core import constants,run_episode_arrays

HERE=Path(__file__).resolve().parent
RUN=HERE/"results/run_v1"


def wilson(k,n):
    z=1.959963984540054
    p=k/n
    den=1+z*z/n
    mid=(p+z*z/(2*n))/den
    rad=z*np.sqrt(p*(1-p)/n+z*z/(4*n*n))/den
    return [float(max(0,mid-rad)),float(min(1,mid+rad))]


def critical(n,p,alpha=.01):
    lo,hi=-1,n
    while lo+1<hi:
        mid=(lo+hi)//2
        if binom.cdf(mid,n,p)<=alpha:
            lo=mid
        else:
            hi=mid
    return lo, (float(binom.cdf(lo,n,p)) if lo>=0 else 0.0)


def main():
    protocol=json.loads((HERE/"protocol.json").read_text(encoding="utf8"))
    quadrature=json.loads((HERE/"deterministic_tv_checks.json").read_text(encoding="utf8"))
    rows=[]
    for model in protocol["models"]:
        delta=model["legacy_delta"]
        inp=np.load(RUN/(model["id"]+"_test_inputs.npz"))
        data={k:inp[k] for k in inp.files}
        k_gain,lam,s1=constants(model)
        V=s1+1/model["Z"]
        nu_send=(1/np.sqrt(model["Z"]*V)*
            np.sqrt(2*np.pi*V)/(2*delta)*
            (0.5*(1+__import__('math').erf(delta/np.sqrt(2*V)))-
             0.5*(1+__import__('math').erf(-delta/np.sqrt(2*V)))))
        tvrow=[r for r in quadrature if r["model"]==model["id"] and
               r["delta"]==delta and r["innovation_order_per_piece"]==64][0]
        p_send=tvrow["target_send_mass"]
        p_attack=nu_send-tvrow["event_bits_tv"]/p_send
        n_plan=__import__('math').ceil(((2.3263478740408408*np.sqrt(nu_send*(1-nu_send))+
            .8416212335729143*np.sqrt(p_attack*(1-p_attack)))/(nu_send-p_attack))**2)
        for setting in ["fixed","public_phase","postcommit_phase"]:
            healthy=run_episode_arrays(model,data,delta,protocol["b"],setting,"healthy")
            attacks={name:run_episode_arrays(model,data,delta,protocol["b"],setting,name)
                     for name in protocol["attacks"]}
            n=int(np.sum(healthy["send0"]))
            p0=nu_send if setting!="fixed" else None
            # send1 is the send event; the Bernoulli success under test is silence.
            k0=int(np.sum(healthy["send0"] & ~healthy["send1"]))
            for name,values in attacks.items():
                ka=int(np.sum(values["send0"] & ~values["send1"]))
                row={"model":model["id"],"delta":delta,"protocol":setting,"attack":name,
                    "analysis":"exploratory replay on frozen test inputs; no new random draws",
                    "target_send_count":n,"target_send_rate":n/len(data["x0"]),
                    "healthy_next_silence_count_given_send":k0,
                    "attack_next_silence_count_given_send":ka,
                    "attack_conditional_silence_rate":ka/n,
                    "attack_conditional_silence_wilson95":wilson(ka,n)}
                if p0 is not None:
                    row.update({"analytic_healthy_probability":float(p0),
                        "healthy_exact_lower_tail_p":float(binomtest(k0,n,p0,alternative="less").pvalue),
                        "attack_exact_lower_tail_p":float(binomtest(ka,n,p0,alternative="less").pvalue),
                        "one_sided_alpha01_critical_count":critical(n,p0)[0],
                        "conditional_type1_bound":critical(n,p0)[1]})
                if setting=="postcommit_phase" and name=="balanced_reflection":
                    row.update({"phase_integrated_alternative_probability":float(p_attack),
                        "event_bit_tv_for_reflection":tvrow["event_bits_tv"],
                        "conditional_effect":float(nu_send-p_attack),
                        "planned_target_send_samples_1pct_80pct_normal":n_plan,
                        "planned_episodes_1pct_80pct_normal":int(np.ceil(n_plan/p_send)),
                        "planning_is_not_power_guarantee":True})
                rows.append(row)
    out=HERE/"results/run_v1/exploratory_event_binomial.json"
    out.write_text(json.dumps(rows,ensure_ascii=False,indent=2,allow_nan=False)+"\n",
                   encoding="utf8",newline="\n")
    print(json.dumps(rows,ensure_ascii=False,indent=2))


if __name__=="__main__":
    main()
