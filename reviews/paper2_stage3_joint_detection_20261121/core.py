"""Joint event/payload tests, conditional on the actual trusted feedback center."""
from __future__ import annotations

import numpy as np
from scipy.special import ndtr, logsumexp

NAMES=("E0_previous_event_mixture","E1_phase_event_mixture",
       "R0_selected_innovation_mixture","R1_biasaware_innovation_mixture",
       "P1_conditional_payload_mixture","J1_joint_mixture","J0_joint_from_start")


def quant(x, delta, phase):
    return phase+2*delta*np.floor((x-phase+delta)/(2*delta))


def log_trigger(v, Z):
    with np.errstate(divide="ignore",invalid="ignore"):
        return np.log(-np.expm1(-.5*Z*v*v))


def silent_probability(P, d, r, model):
    S=P+model["R"]
    V=S+1/model["Z"]
    return np.exp(-.5*(d-r)**2/V)/np.sqrt(1+model["Z"]*S)


def phase_mean(Ppost, D, model):
    A,Q,R,Z,delta=(model[k] for k in ("A","Q","R","Z","delta"))
    V=1/Z+A*A*Ppost+Q+R
    root=np.sqrt(V)
    return np.sqrt(2*np.pi/Z)/(2*delta)*(
        ndtr((delta-A*D)/root)-ndtr((-delta-A*D)/root))


def log_factors(P, r, sent, received_innovation, d, b, model):
    """Predictable d,b may be arrays; u is visible only on true sends.

    Silent entries are mathematically ignored; never clamp a density zero.
    Null/alternative send densities vanish at isolated zero-measure points.
    """
    S=P+model["R"]
    u=np.where(sent, received_innovation, 0.)
    p0=silent_probability(P,0.,r,model)
    p1=silent_probability(P,d,r,model)
    log_silent_ratio=((r*d)-.5*d*d)/(S+1/model["Z"])
    log_send_event=np.log1p(-p1)-np.log1p(-p0)
    log_event=np.where(sent,log_send_event,log_silent_ratio)
    with np.errstate(invalid="ignore"):
        send_joint=(u*(b+d)-.5*(b+d)**2)/S + (
            log_trigger(u-b-r,model["Z"])-log_trigger(u-r,model["Z"]))
    joint=np.where(sent,send_joint,log_silent_ratio)
    payload=np.where(sent,send_joint-log_send_event,0.)

    def tilt(theta):
        tilted_silent=silent_probability(P,S*theta,r,model)
        log_M=.5*S*theta**2+np.log1p(-tilted_silent)-np.log1p(-p0)
        return np.where(sent,theta*u-log_M,0.)

    residual=tilt(b/S)
    residual_aware=tilt((b+d)/S)
    return log_event,residual,residual_aware,payload,joint


class JointDetectors:
    """No truth, attack onset, or actual amplitude is an online argument."""
    def __init__(self,count,model,strengths,weights,alpha):
        self.model=model
        self.b=np.asarray(strengths)[:,None]
        self.log_pi=np.log(np.asarray(weights))[:,None]
        self.threshold=np.log(1/alpha)
        self.d=np.zeros((len(strengths),count))
        # Five phase/continuous kernels, sharing start weights but not evidence.
        self.log_mass=np.full((5,len(strengths),count),-np.inf)
        self.log_joint_from_start=np.zeros((len(strengths),count))
        self.old_mass=np.full((len(strengths),count),-np.inf)
        self.tau=np.full((len(NAMES),count),-1,dtype=np.int32)
        self.maximum_log_e=np.full((len(NAMES),count),-np.inf)
        self.prev_nu=None
        self.prev_q=None

    def step(self,t,P,r,sent,received_innovation):
        factors=log_factors(P[None,:],r[None,:],sent[None,:],
                            received_innovation[None,:],self.d,self.b,self.model)
        factors=np.stack(factors)
        if np.isnan(factors).any():
            raise FloatingPointError("Indeterminate density ratio at an exact zero")
        n=t+1
        log_w=-np.log(float(n))-np.log(float(n+1))
        self.log_mass=np.logaddexp(self.log_mass,log_w)+factors
        log_e=np.logaddexp(logsumexp(self.log_mass+self.log_pi[None,:,:],axis=1),
                          -np.log(float(n+1)))
        self.log_joint_from_start+=factors[-1]
        log_zero=logsumexp(self.log_joint_from_start+self.log_pi,axis=0)
        if t:
            Y=(~sent)[None,:]
            nu=self.prev_nu[None,:]
            q=self.prev_q
            old_factor=np.where(Y,np.log1p((q-nu)/nu),np.log1p((nu-q)/(1-nu)))
            old_weight=-np.log(float(t))-np.log(float(t+1))
            self.old_mass=np.logaddexp(self.old_mass,old_weight)+old_factor
            log_old=np.logaddexp(logsumexp(self.old_mass+self.log_pi,axis=0),
                                -np.log(float(t+1)))
        else:
            log_old=np.zeros(P.shape)
        stats=np.vstack((log_old,log_e,log_zero))
        self.maximum_log_e=np.maximum(self.maximum_log_e,stats)
        newly=(self.tau<0)&(stats>=self.threshold)
        self.tau[newly]=t

    def advance(self,Ppost,K,sent):
        self.d=self.model["A"]*((1-K)*self.d-sent*K*self.b)
        self.prev_nu=phase_mean(Ppost,0.,self.model)
        candidate=phase_mean(Ppost[None,:],-K[None,:]*self.b,self.model)
        self.prev_q=np.where(sent[None,:],candidate,self.prev_nu[None,:])


def update_error(error,P,r,v,sent,action,model):
    Ri=np.where(sent,model["R"],model["R"]+1/model["Z"])
    K=P/(P+Ri)
    post=np.where(sent,(1-K)*error-K*(v+action),error-K*r)
    return post,P*(1-K),K
