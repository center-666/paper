"""Single-receiver joint e-process; no simulator or attack labels required.

The caller supplies existing local prediction variance, center offset, event
bit, and the actually received innovation. Call once for every event, including
silence. This component reports an alarm; it does not alter an estimator.
"""
from __future__ import annotations

import math
import numpy as np
from scipy.special import logsumexp


class JointReceiverDetector:
    def __init__(self,A:float,R:float,Z:float,strengths=(.05,.1,.25),
                 weights=None,alpha:float=.01):
        self.A,self.R,self.Z=float(A),float(R),float(Z)
        self.b=np.asarray(strengths,dtype=float)
        if weights is None:
            weights=np.full(self.b.size,1/self.b.size)
        weights=np.asarray(weights,dtype=float)
        if not (math.isfinite(self.A) and math.isfinite(self.R) and math.isfinite(self.Z)
                and 0<alpha<1 and R>0 and Z>0 and self.b.ndim==1 and
                self.b.size>0 and np.all(np.isfinite(self.b)) and np.all(self.b>0)
                and weights.shape==self.b.shape and np.all(weights>0)
                and abs(float(weights.sum())-1)<1e-12):
            raise ValueError("Invalid candidate or model parameters")
        self.log_pi=np.log(weights)
        self.d=np.zeros(self.b.shape)
        self.log_mass=np.full(self.b.shape,-np.inf)
        self.n=0
        self.log_threshold=math.log(1/alpha)
        self.first_alarm_time=None
        self.log_e=0.

    @staticmethod
    def _log_h(x,Z):
        with np.errstate(divide="ignore"):
            return np.log(-np.expm1(-.5*Z*x*x))

    def observe(self,*,sent:bool,innovation:float|None,
                prediction_variance:float,center_offset:float):
        """Return evidence after the current event, before output commitment.

        innovation is received_payload minus the receiver's prior prediction.
        It must be None on silence. center_offset is feedback_center minus
        that same prediction. The first invocation is physical time zero.
        """
        P,r=float(prediction_variance),float(center_offset)
        if not math.isfinite(P) or P<=0 or not math.isfinite(r):
            raise ValueError("Invalid prediction covariance or center")
        if sent:
            if innovation is None or not math.isfinite(float(innovation)):
                raise ValueError("A real send requires a finite received innovation")
            u=float(innovation);S=P+self.R
            factor=(u*(self.b+self.d)-.5*(self.b+self.d)**2)/S+(
                self._log_h(u-self.b-r,self.Z)-self._log_h(u-r,self.Z))
            K=P/(P+self.R)
        else:
            if innovation is not None:
                raise ValueError("There is no received payload on silence")
            factor=(r*self.d-.5*self.d*self.d)/(P+self.R+1/self.Z)
            K=P/(P+self.R+1/self.Z)
        if np.isnan(factor).any():
            raise FloatingPointError("Indeterminate continuous-density ratio")
        n=self.n+1
        log_w=-math.log(n)-math.log(n+1)
        self.log_mass=np.logaddexp(self.log_mass,log_w)+factor
        self.log_e=float(np.logaddexp(logsumexp(self.log_mass+self.log_pi),-math.log(n+1)))
        alarm=self.log_e>=self.log_threshold
        if alarm and self.first_alarm_time is None:
            self.first_alarm_time=self.n
        self.d=self.A*((1-K)*self.d-(K*self.b if sent else 0.))
        self.n=n
        return {"time":n-1,"log_evidence":self.log_e,
                "alarm_now":alarm,"first_alarm_time":self.first_alarm_time}
