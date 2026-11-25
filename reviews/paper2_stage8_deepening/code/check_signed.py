"""Check the actual online record against the uncompressed likelihood implementation."""
from bisect import bisect_left
from decimal import Decimal as D
from fractions import Fraction as F
import numpy as np
from experiment import SignedRecord, MODEL, record, evaluate, Methods, I, ROOT, save, read
from vector_record import VectorRecord
from signed_certify import restrict
from pilot_v2 import exact_mid

def check():
    full=VectorRecord(MODEL)
    signed=SignedRecord(MODEL,D(".35"))
    mirror=SignedRecord(MODEL,D(".35"))
    # Include silent prefixes, consecutive sends and late onsets.
    count=0
    for t in range(36):
        sent=t%5 in (2,3)
        u=D(".21")+D(t)*D(".007") if sent else None
        r=D(".001")
        for rec,sgn in [(full,1),(signed,1),(mirror,-1)]:
            rec.append(sent,str(sgn*u) if sent else None,str(sgn*r))
        if t in (0,6,17,35):
            view=signed.view()
            reflected=mirror.view()
            for b in [D("-.35"),D("-.07"),D(0),D(".07"),D(".35")]:
                original=full.all_likelihoods(I.exact(b))
                compressed=view.all_likelihoods(I.exact(b))
                other=reflected.all_likelihoods(I.exact(-b))
                for k,score in enumerate(original):
                    i=bisect_left(signed.send_times,k)
                    mapped=compressed[i] if i<len(compressed) else I.exact(0)
                    assert score==mapped
                    if i<len(compressed):
                        assert mapped==other[i]
                        assert full.candidates[k]["H"]==view.candidates[i]["H"]
                    count+=1
            assert not (signed.ref.hi<mirror.ref.lo or mirror.ref.hi<signed.ref.lo)
    for q in (I(D("-.41"),D("-.39")),I(D("-.01"),D(".40")),I.exact(0),I.exact(".4")):
        domain=(F(-1,4),F(1,4))
        reduced=restrict(domain,q,F(1,20))
        for i in range(-25,26):
            b=F(i,100)
            if max(b*F(q.lo),b*F(q.hi))>=F(1,20):
                assert reduced and reduced[0]<=b<=reduced[1]
    # Honest nonzero signed injections and control are applied to physical states.
    # Flipping the physical origin around the deterministic controlled trajectory
    # negates innovations while preserving the trigger probability and schedule.
    from experiment import control,A,B
    frames,states=record(202611252823,7,0,.35)
    neg=[]; neg_states=[]; forced=np.zeros(2)
    for frame,x in zip(frames,states):
        t,s,c,u=frame
        neg.append([t,s,2*forced[0]-c,2*forced[0]-u if s else None])
        neg_states.append(2*forced-x)
        forced=A@forced+B@control(t)
    p=evaluate(frames,states,.35,D(".35"),"0")
    n=evaluate(neg,neg_states,-.35,D(".35"),"0")
    mirror_error=max(abs(p["metrics"][m]["loss"]-n["metrics"][m]["loss"]) for m in p["metrics"])
    assert mirror_error<1e-9
    assert [q["direction"] for q in p["queries"]]==[
            [str(-F(x)) for x in q["direction"]] if q["direction"] else None for q in n["queries"]]
    assert not any(r["miss"] or r["violations"] or r["cap_bad"] for r in (p,n))
    save(ROOT/"results/signed_checks.json",dict(full_likelihood_parity_checks=count,
          mirrored_loss_error=mirror_error,direct_error_max=max(p["max_error"],n["max_error"]),
          exact_signed_grid_and_response_mirror=True,endpoint_checks=True))
if __name__=="__main__":
    check()
