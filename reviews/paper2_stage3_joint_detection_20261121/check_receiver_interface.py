"""Deterministic equivalence of reusable receiver and frozen research J1."""
import hashlib
import json
from pathlib import Path
import numpy as np
from core import JointDetectors,NAMES
from receiver_detector import JointReceiverDetector

HERE=Path(__file__).resolve().parent
p=json.loads((HERE/"protocol.json").read_text(encoding="utf8"))
errors=[]
for model in p["models"]:
    receiver=JointReceiverDetector(model["A"],model["R"],model["Z"])
    reference=JointDetectors(1,model,p["candidate_strengths"],p["candidate_weights"],p["alpha"])
    P=model["P0"]
    max_error=0.
    for t in range(600):
        sent=(t%5 in (0,3))
        r=model["delta"]*np.sin(t*.37)
        u=.23*np.cos(t*.13)+.11 if sent else None
        result=receiver.observe(sent=sent,innovation=u,prediction_variance=P,center_offset=r)
        reference.step(t,np.array([P]),np.array([r]),np.array([sent]),np.array([u if sent else 0.]))
        # Compute current (not running-maximum) reference evidence directly.
        from scipy.special import logsumexp
        expected=float(np.logaddexp(logsumexp(reference.log_mass[-1,:,0]+reference.log_pi[:,0]),-np.log(t+2)))
        max_error=max(max_error,abs(result["log_evidence"]-expected))
        assert receiver.first_alarm_time==(None if reference.tau[NAMES.index("J1_joint_mixture"),0]<0
                                           else int(reference.tau[NAMES.index("J1_joint_mixture"),0]))
        K=P/(P+model["R"]+(0. if sent else 1/model["Z"]))
        Ppost=P*(1-K)
        reference.advance(np.array([Ppost]),np.array([K]),np.array([sent]))
        assert np.max(np.abs(reference.d[:,0]-receiver.d))<1e-14
        P=model["A"]**2*Ppost+model["Q"]
    assert max_error<5e-12
    errors.append({"model":model["id"],"steps":600,"maximum_log_e_difference":max_error})
receiver=JointReceiverDetector(.82,.2,2.)
try:
    receiver.observe(sent=False,innovation=0.,prediction_variance=.8,center_offset=0.)
    raise AssertionError("Silent fabricated payload was accepted")
except ValueError:
    pass
out={"status":"PASS","performance_random_samples_generated":False,"checks":errors,
     "silent_payload_rejected":True,
     "receiver_source_sha256":hashlib.sha256((HERE/"receiver_detector.py").read_bytes()).hexdigest(),
     "frozen_core_sha256":hashlib.sha256((HERE/"core.py").read_bytes()).hexdigest()}
(HERE/"receiver_interface_checks.json").write_text(json.dumps(out,indent=2)+"\n",encoding="utf8",newline="\n")
print(json.dumps(out,indent=2))
