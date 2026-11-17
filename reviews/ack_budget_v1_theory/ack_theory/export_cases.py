"""Export every integer audit case for independent review; no simulation/RNG."""
from __future__ import annotations
import gzip
import hashlib
import itertools
import json
from pathlib import Path

from model import cost_neutral_boundary, frontier, history_is_legal, m_star, safe_wait_boundary
from attack_oracle import brute_causal_minimax, brute_frontier, brute_guarantees

OUT = Path(__file__).resolve().parents[1]/"data"


def enumerate_records():
    for L in range(2,11):
        for B in range(L):
            for k in range(1,5):
                for D in range(k,k+5):
                    for hist_bits in itertools.product((0,1), repeat=k-1):
                        H={i+1 for i,b in enumerate(hist_bits) if b}
                        if not history_is_legal(H,L,B,1,D):
                            continue
                        base=m_star(H,L,B,k,D)
                        game=brute_causal_minimax(H,L,B,k,D)
                        assert base==game
                        curve=frontier(H,L,B,k,D)
                        for bits in itertools.product((0,1),repeat=D-k+1):
                            S={k+i for i,b in enumerate(bits) if b}
                            windows=[]
                            for t in range(k,D+1):
                                u=sum(t-L+1<=h<=t for h in H)
                                n=sum(t-L+1<=s<=t for s in S)
                                windows.append({"end":t,"U":u,"N":n,"U_plus_N":u+n})
                            predicted=max(w["U_plus_N"] for w in windows)>B
                            # Independent enumeration of all block/allow vectors.
                            slots=sorted(S); legal=all_blocked=0
                            for action in itertools.product((0,1),repeat=len(slots)):
                                chosen={t for t,b in zip(slots,action) if b}
                                blocks=H|chosen
                                if all(sum(t-L+1<=b<=t for b in blocks)<=B for t in range(k,D+1)):
                                    legal+=1
                                    if all(action):all_blocked+=1
                            oracle_guarantees=(all_blocked==0)
                            assert predicted==oracle_guarantees
                            yield {"L":L,"B":B,"k":k,"D":D,"history":sorted(H),
                                   "opportunities":slots,"windows":windows,
                                   "theory_guarantees":predicted,
                                   "enumerated_legal_attack_vectors":legal,
                                   "enumerated_all_blocked_vectors":all_blocked,
                                   "oracle_guarantees":oracle_guarantees,"T1_match":True,
                                   "theory_minimax_attempts":base,"bellman_minimax_attempts":game,
                                   "T2_match":True,"continuous_frontier":curve,
                                   "safe_wait_boundary":safe_wait_boundary(H,L,B,k,D),
                                   "cost_neutral_boundary":cost_neutral_boundary(H,L,B,k,D)}


def main():
    OUT.mkdir(exist_ok=True)
    target=OUT/"all_exhaustive_cases.jsonl.gz"
    count=0
    # Fixed mtime keeps the archive reproducible.
    with target.open("wb") as raw:
        with gzip.GzipFile(filename="",mode="wb",fileobj=raw,mtime=0) as archive:
            for rec in enumerate_records():
                archive.write((json.dumps(rec,sort_keys=True,separators=(",",":"))+"\n").encode())
                count+=1
    assert count==40858,count
    supplemental=OUT/"long_horizon_boundary_cases.jsonl.gz"
    extra=0
    with supplemental.open("wb") as raw:
        with gzip.GzipFile(filename="",mode="wb",fileobj=raw,mtime=0) as archive:
            for L in range(2,11):
                for B in range(L):
                    k=L+1
                    D=k+L+1
                    histories=[set(), set(range(max(1,k-B),k)),
                               set(range(1,min(B+1,k)))]
                    for H in {tuple(sorted(h)) for h in histories}:
                        assert history_is_legal(H,L,B,1,D)
                        options=[set(),set(range(k,D+1)),set(range(k,D+1,2)),
                                 {k,D},set(range(D-B,D+1))]
                        theory_m=m_star(H,L,B,k,D)
                        game=brute_causal_minimax(H,L,B,k,D)
                        curve=frontier(H,L,B,k,D)
                        assert theory_m==game and curve==brute_frontier(H,L,B,k,D)
                        for S in {tuple(sorted(s)) for s in options}:
                            windows=[{"end":t,
                                      "U":sum(t-L+1<=h<=t for h in H),
                                      "N":sum(t-L+1<=s<=t for s in S)}
                                     for t in range(k,D+1)]
                            pred=any(w["U"]+w["N"]>B for w in windows)
                            oracle=brute_guarantees(H,S,L,B,k,D)
                            assert pred==oracle
                            rec={"L":L,"B":B,"k":k,"D":D,"history":list(H),
                                 "opportunities":list(S),"windows":windows,
                                 "theory_guarantees":pred,"oracle_guarantees":oracle,
                                 "T1_match":True,"theory_minimax_attempts":theory_m,
                                 "bellman_minimax_attempts":game,"continuous_frontier":curve}
                            archive.write((json.dumps(rec,sort_keys=True,separators=(",",":"))+"\n").encode())
                            extra+=1
    print(json.dumps({"status":"PASS","records":count,"compressed_bytes":target.stat().st_size,
                      "sha256":hashlib.sha256(target.read_bytes()).hexdigest(),
                      "long_horizon_records":extra,"long_horizon_sha256":hashlib.sha256(supplemental.read_bytes()).hexdigest()}))


if __name__=="__main__":
    main()
