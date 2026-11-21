"""Scalar feedback-phase research core; no real network or device interfaces."""
from __future__ import annotations

import math
import numpy as np
from numpy.polynomial.legendre import leggauss
from scipy.special import ndtr


def quantize(m, delta, phase=0.0):
    return phase + 2.0 * delta * np.floor((np.asarray(m)-phase+delta)/(2.0*delta))


def constants(model):
    p, r, a = (model[k] for k in ("P0", "R", "A"))
    k = p/(p+r)
    return k, a*k, a*a*p*r/(p+r)+model["Q"]+r


def phase_response(d, delta, V, order=32):
    nodes, weights = leggauss(order)
    d = np.asarray(d)
    result = np.zeros_like(d, dtype=float)
    for node, weight in zip(nodes, weights):
        result += .5*weight*np.exp(-(d-delta*node)**2/(2.0*V))
    return result


def phase_deficit(d, delta, V, order=32):
    """Stable F(0)-F(d); integrate paired +- offsets to remove odd terms."""
    nodes, weights = leggauss(order)
    d = np.asarray(d)
    result = np.zeros_like(d, dtype=float)
    for node, weight in zip(nodes, weights):
        e = delta*node
        t = d*e/V
        # cosh(t)-1 = 2*sinh(t/2)^2 avoids cancellation at tiny d.
        result += .5*weight*np.exp(-e*e/(2*V)) * (
            -np.expm1(-d*d/(2*V))
            -np.exp(-d*d/(2*V))*2*np.sinh(t/2)**2)
    return result


def log_density(u, model):
    variance = model["P0"]+model["R"]
    u = np.asarray(u)
    with np.errstate(divide="ignore", invalid="ignore"):
        return (-.5*np.log(2*np.pi*variance)-u*u/(2*variance)
                +np.log(-np.expm1(-.5*model["Z"]*u*u)))


def attack(disclosed, sent, sign_uniform, accept_uniform, model, delta, b,
           kind, reference_phase):
    """Inputs exclude hidden state, next true measurement, and future phase.

    The caller supplies zero reference for postcommit, and actual revealed phase
    for public_phase. True values on silent paths are replaced by NaN first.
    """
    _, lam, _ = constants(model)
    u = np.where(sent, disclosed, 0.0)
    center = quantize(lam*u, delta, reference_phase)
    if kind == "bounded_sign":
        return np.where(sent, np.where(sign_uniform < .5, b, -b), 0.0)
    if kind == "cell_sign":
        eta = min(b, delta/(2*abs(lam)))
        eligible = sent & (np.abs(lam*u-center) < delta/2)
        return np.where(eligible, np.where(sign_uniform < .5, eta, -eta), 0.0)
    if kind != "balanced_reflection":
        raise ValueError(kind)
    proposed = 2*center/lam-u
    valid = sent & (np.abs(proposed-u) < b)
    # Avoid the half-open endpoint where reflection could move to the next cell.
    valid &= np.abs(lam*u-center) < delta
    lu, lt = log_density(u, model), log_density(proposed, model)
    probability = np.zeros_like(u, dtype=float)
    good = valid & np.isfinite(lu) & np.isfinite(lt)
    probability[good] = np.exp(np.minimum(0.0, lt[good]-lu[good]))
    return np.where(valid & (accept_uniform < probability), proposed-u, 0.0)


def run_episode_arrays(model, data, delta, b, protocol, kind):
    """Two times, target t=0; next actual payload is always unmodified."""
    k, lam, variance = constants(model)
    zparam = model["Z"]
    x0, u, y1 = data["x0"], data["y0"], data["y1"]
    send0 = data["u0"] > np.exp(-.5*zparam*u*u)
    phase = np.zeros_like(u) if protocol == "fixed" else delta*(2*data["phase_u"]-1)
    reference = phase if protocol == "public_phase" else np.zeros_like(u)
    action = (np.zeros_like(u) if kind == "healthy" else
              attack(np.where(send0,u,np.nan), send0, data["sign_u"],
                     data["accept_u"], model, delta, b, kind, reference))
    received = np.where(send0,u+action,0.0)
    prior1 = lam*received
    center = quantize(prior1,delta,phase)
    clean_center = quantize(lam*np.where(send0,u,0.0),delta,phase)
    next_silent = data["u1"] <= np.exp(-.5*zparam*(y1-center)**2)
    clean_next_silent = data["u1"] <= np.exp(-.5*zparam*(y1-clean_center)**2)
    factor = 1/np.sqrt(1+zparam*variance)
    v = variance+1/zparam
    p0 = factor*np.exp(-(prior1-center)**2/(2*v))
    ptrue = factor*np.exp(-(lam*u-center)**2/(2*v))
    p0post=np.where(send0,model["P0"]*model["R"]/(model["P0"]+model["R"]),
        model["P0"]*(model["R"]+1/model["Z"])/(model["P0"]+model["R"]+1/model["Z"]))
    sigma1=model["A"]**2*p0post+model["Q"]+model["R"]
    V1=sigma1+1/model["Z"]
    phase_centered=(np.sqrt(2*np.pi*V1)/(2*delta)*
        (ndtr(delta/np.sqrt(V1))-ndtr(-delta/np.sqrt(V1))))
    phase_factor=1/np.sqrt(model["Z"]*V1)
    nu=phase_factor*phase_centered
    # This event-only score is the phase-marginal witness. It uses gamma_1 and
    # the target event/covariance label, never a continuous measurement.
    event_score=1.0-next_silent/nu
    # Conditional comparator uses the received target value and actual center.
    conditional_score=np.where(send0,p0-next_silent,0.0)
    clean_post = k*np.where(send0,u,0.0)
    post = k*received
    true_damage = (x0-post)**2-(x0-clean_post)**2
    formula_damage = k*k*action*action
    return {
        "action":action,"event_score":event_score,"conditional_score":conditional_score,
        "send0":send0,"send1":~next_silent,
        "center":center,"phase":phase,"received":received,
        "p0":p0,"ptrue":ptrue,"prior1":prior1,
        "healthy_mse":(x0-clean_post)**2,"target_mse":(x0-post)**2,
        "damage_paired":true_damage,"damage_conditional":formula_damage,
        "same_next_code":center==clean_center,
        "same_next_event":next_silent==clean_next_silent,
    }


def conformal_threshold(values, alpha=.01):
    values=np.asarray(values)
    rank=math.ceil((len(values)+1)*(1-alpha))
    return float(np.partition(values,rank-1)[rank-1]) if rank<=len(values) else math.inf


def wilson(events, n):
    z=1.959963984540054
    phat=events/n
    den=1+z*z/n
    middle=(phat+z*z/(2*n))/den
    radius=z*np.sqrt(phat*(1-phat)/n+z*z/(4*n*n))/den
    return [float(max(0,middle-radius)),float(min(1,middle+radius))]


def quadrature_effect(model,delta,b,kind,order=24,phase_order=64):
    """Unconditional target episode moments for fixed/postcommit protocols.

    Integrates the true sending subdensity, legal attack random kernel, and
    next Bernoulli event. It is a planning calculation, not detector input.
    """
    k,lam,var=constants(model)
    V=var+1/model["Z"]
    s=1/np.sqrt(model["Z"]*V)
    sd=np.sqrt(model["P0"]+model["R"])
    limit=10*sd
    width=2*delta/abs(lam)
    cuts=[-limit,0.0,limit]
    # Split at cell boundaries, center, central-half boundaries, and peak gate.
    for j in range(-int(limit/width)-2,int(limit/width)+3):
        c=j*width
        cuts.extend([c-width/2,c-width/4,c,c+width/4,c+width/2,
                     c-b/2,c+b/2])
    cuts=np.unique([c for c in cuts if -limit<=c<=limit])
    nodes,weights=leggauss(order)
    left,right=cuts[:-1,None],cuts[1:,None]
    u=((left+right)/2+(right-left)/2*nodes).ravel()
    integration_weights=((right-left)/2*weights).ravel()
    mass=integration_weights*np.exp(log_density(u,model))
    if kind == "cell_sign":
        center=quantize(lam*u,delta)
        gate=np.abs(lam*u-center)<delta/2
        eta=min(b,delta/(2*abs(lam)))
        moves=[(np.where(gate,eta,0),np.full_like(u,.5)),
               (np.where(gate,-eta,0),np.full_like(u,.5))]
    elif kind == "balanced_reflection":
        proposed=2*quantize(lam*u,delta)/lam-u
        valid=np.abs(proposed-u)<b
        ratio=np.exp(np.minimum(0,log_density(proposed,model)-log_density(u,model)))
        prob=np.where(valid,ratio,0.0)
        moves=[(proposed-u,prob),(np.zeros_like(u),1-prob)]
    elif kind == "bounded_sign":
        moves=[(np.full_like(u,b),np.full_like(u,.5)),
               (np.full_like(u,-b),np.full_like(u,.5))]
    else:
        moves=[(np.zeros_like(u),np.ones_like(u))]
    phase_nodes,phase_weights=leggauss(phase_order)
    out={p:{"mean":0.0,"second_moment":0.0,"event_mean":0.0,
            "event_second_moment":0.0,"conditional_damage":0.0,
            "nonzero_action_probability":0.0} for p in ("fixed","postcommit_phase")}
    # If the target is silent, no attack is applied. Its next-phase mean
    # silence probability depends only on the silent-update covariance label.
    Pquiet=model["P0"]*(model["R"]+1/model["Z"])/(model["P0"]+model["R"]+1/model["Z"])
    Vquiet=model["A"]**2*Pquiet+model["Q"]+model["R"]+1/model["Z"]
    nuquiet=1/np.sqrt(model["Z"]*Vquiet)*phase_response(0,delta,Vquiet,phase_order)
    psilent=1/np.sqrt(1+model["Z"]*(model["P0"]+model["R"]))
    out["postcommit_phase"]["event_second_moment"] += psilent*(1/nuquiet-1)
    for action,weight in moves:
        aweights=mass*weight
        z=u+action
        shift=-lam*action
        signal=s*phase_deficit(shift,delta,V,phase_order)
        out["postcommit_phase"]["mean"]+=float(aweights@signal)
        mean_public=lam*z
        center=quantize(mean_public,delta)
        p0=s*np.exp(-(mean_public-center)**2/(2*V))
        pa=s*np.exp(-(lam*u-center)**2/(2*V))
        out["fixed"]["mean"]+=float(aweights@(p0-pa))
        out["fixed"]["second_moment"]+=float(aweights@(pa*(1-pa)+(p0-pa)**2))
        second=np.zeros_like(u)
        for node,w in zip(phase_nodes,phase_weights):
            error=delta*node
            p0=s*np.exp(-error**2/(2*V))
            pa=s*np.exp(-(shift-error)**2/(2*V))
            second+=w*.5*(pa*(1-pa)+(p0-pa)**2)
        out["postcommit_phase"]["second_moment"]+=float(aweights@second)
        nu=s*phase_response(0,delta,V,phase_order)
        ptrue=s*phase_response(shift,delta,V,phase_order)
        out["postcommit_phase"]["event_mean"]+=float(aweights@(1-ptrue/nu))
        out["postcommit_phase"]["event_second_moment"]+=float(
            aweights@(1-2*ptrue/nu+ptrue/(nu*nu)))
        for p in out:
            out[p]["conditional_damage"]+=float(aweights@(k*k*action*action))
            out[p]["nonzero_action_probability"]+=float(aweights@(action!=0))
    for p,v in out.items():
        v["variance"]=max(0,v["second_moment"]-v["mean"]**2)
        v["event_variance"]=max(0,v["event_second_moment"]-v["event_mean"]**2)
        v["integration_order"]=order
        v["phase_order"]=phase_order
        v["gaussian_truncation_sd"]=10
        v["omitted_sending_mass_bound"]=math.erfc(10/math.sqrt(2))
    return out
