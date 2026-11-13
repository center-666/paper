"""Deterministic interface checks only; no Monte Carlo or attack experiment."""
from pathlib import Path
import hashlib, json
import numpy as np
import receiver_gls_writeback as m

edges=np.array([[0,1],[1,0],[1,2],[2,1],[2,3],[3,2],[3,4],[4,3],[4,0],[0,4]])
event=m.Reception(0,0)
state_response=np.zeros((3,5,2,2)); state_response[2]=np.eye(2)
raw_response=np.broadcast_to(np.eye(2),(10,2,2)).copy()
gain=np.array([[1.,0.,0.,0.],[0.,1.,0.,0.]])
candidate=m.Candidate(event,state_response,raw_response,gain,np.eye(2))
fit=m.FittedGLS(1,0,1,np.zeros(4),(candidate,),(event,),1.,2,2)
decision=m.attribute(fit,np.array([[2.,1.],[0.,0.]]),[event])
assert decision.event==event and decision.score==5. and np.array_equal(decision.theta,[2.,1.])
assert m.attribute(fit,np.zeros((2,2)),[event]) is None
packets,transmissions=m.deliver_command(decision,edges,1,5)
assert len(packets)==5 and len(transmissions)==4
assert sum(x['payload_bytes'] for x in transmissions)==84
assert max(x['round'] for x in transmissions)==2
for node in range(5):
 ids=np.flatnonzero(edges[:,1]==node)
 state,cache=m.apply_local_writeback(node,np.zeros(2),np.zeros((len(ids),2)),ids,
                                      packets[node],candidate,1,edges)
 assert np.array_equal(state,[-2.,-1.])
 assert np.array_equal(cache,np.tile([-2.,-1.],(len(ids),1)))
try:
 m.attribute(fit,np.zeros((2,2)),[])
 raise AssertionError('missing reception was accepted')
except ValueError: pass
try:
 m.apply_local_writeback(1,np.zeros(2),np.zeros((1,2)),[1],packets[1],candidate,1,edges)
 raise AssertionError('foreign cache was accepted')
except ValueError: pass
out=Path(__file__).resolve().parents[1]/'results/g1r_local_interface_unit_20261113_v1'
out.mkdir(exist_ok=False)
source=Path(m.__file__)
result={'scope':'deterministic synthetic interface checks; no replay or statistical experiment',
 'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
 'checks':['GLS attribution','no-alarm path','missing reception rejection','four-edge command delivery',
           'serialized packet lengths','local state and owned-cache writeback','foreign cache rejection'],
 'extra_payload_bytes':sum(x['payload_bytes'] for x in transmissions),
 'control_rounds':max(x['round'] for x in transmissions),
 'transmissions':transmissions,'not_verified':['fitted real-data false-alarm rate','unknown-event localization accuracy',
 'attacked closed-loop recovery','latency and failure of control communication']}
(out/'unit.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
print(json.dumps(result,indent=2))
