"""Deterministic quadrature for the bounded balanced-reflection witness."""
from __future__ import annotations

import json
from pathlib import Path
import numpy as np
from numpy.polynomial.legendre import leggauss

from core import constants,log_density,quantize

HERE=Path(__file__).resolve().parent


def integrate(model,delta,b,nz=40,ns=64):
    _,lam,S1=constants(model)
    p0=model["P0"]+model["R"]
    V=S1+1/model["Z"]
    sf=1/np.sqrt(1+model["Z"]*S1)
    limit=10*np.sqrt(p0)
    width=2*delta/abs(lam)
    j0=int(np.floor((-limit+width/2)/width))-1
    j1=int(np.ceil((limit-width/2)/width))+1
    zn,zw=leggauss(nz)
    sn,sw=leggauss(ns)
    phases=delta*sn
    phase_weights=sw/2
    tv_joint=0.0
    signed_bits=0.0
    total_send=0.0
    max_cell_quad=0.0
    cell_count=0
    for j in range(j0,j1+1):
        center_input=j*width
        left=max(-limit,center_input-width/2)
        right=min(limit,center_input+width/2)
        if right<=left:
            continue
        cuts=[left,right]
        # Peak truncation and proposal validity change at these cell positions.
        cuts.extend(x for x in [center_input-b/2,center_input+b/2] if left<x<right)
        cuts=sorted(set(cuts))
        cell_value=0.0
        for lo,hi in zip(cuts[:-1],cuts[1:]):
            z=(lo+hi)/2+(hi-lo)/2*zn
            weights=(hi-lo)/2*zw
            reflected=2*center_input-z
            valid=np.abs(reflected-z)<b
            logfz=log_density(z,model)
            logft=log_density(reflected,model)
            alpha=np.zeros_like(z)
            ok=valid & np.isfinite(logfz) & np.isfinite(logft)
            alpha[ok]=np.exp(np.minimum(0,logft[ok]-logfz[ok]))
            fz=np.exp(logfz)
            # The MH balance identity makes this the conditional hidden-input
            # mixture given the received target payload z.
            c=quantize(lam*z[:,None],delta,phases[None,:])
            pz=sf*np.exp(-(lam*z[:,None]-c)**2/(2*V))
            pt=sf*np.exp(-(lam*reflected[:,None]-c)**2/(2*V))
            diff=pz-pt
            phase_abs=(np.abs(diff)@phase_weights)
            phase_signed=(diff@phase_weights)
            contribution=weights*fz*alpha
            tv_piece=float(contribution@phase_abs)
            bit_piece=float(contribution@phase_signed)
            send_piece=float((weights*fz)@np.ones_like(z))
            tv_joint+=tv_piece
            signed_bits+=bit_piece
            total_send+=send_piece
            cell_value+=tv_piece
        max_cell_quad=max(max_cell_quad,cell_value)
        cell_count+=1
    return {
        "joint_tv_payload_phase_event":tv_joint,
        "event_bits_tv":abs(signed_bits),
        "signed_event_probability_difference":signed_bits,
        "target_send_mass":total_send,
        "phase_order":ns,"innovation_order_per_piece":nz,
        "quantizer_cells":cell_count,
        "max_single_cell_joint_contribution":max_cell_quad,
        "identity_delta2_joint":tv_joint/delta**2,
        "identity_delta2_event_bits":abs(signed_bits)/delta**2,
    }


def main():
    protocol=json.loads((HERE/"protocol.json").read_text(encoding="utf8"))
    rows=[]
    for model in protocol["models"]:
        for multiplier in protocol["delta_multipliers"]:
            delta=model["legacy_delta"]*multiplier
            for nz,ns in [(24,32),(40,64),(64,96)]:
                row={"model":model["id"],"delta":delta,"delta_multiplier":multiplier,
                     "b":protocol["b"],**integrate(model,delta,protocol["b"],nz,ns)}
                rows.append(row)
    path=HERE/"deterministic_tv_checks.json"
    path.write_text(json.dumps(rows,indent=2,allow_nan=False)+"\n",encoding="utf8",newline="\n")
    print(json.dumps(rows,indent=2))


if __name__=="__main__":
    main()
