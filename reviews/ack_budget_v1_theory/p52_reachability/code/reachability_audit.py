"""P5.2 exact communication automata; no estimator/noise trajectory simulation.

State (a,H): pre-decision anchor age a=k-tau and recent failed-tick ages k-h.
High/low is a symbolic input, not a computed or randomized measurement.
"""
from __future__ import annotations
import argparse
from collections import deque
from functools import lru_cache
import csv
import gzip
import hashlib
import io
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
State = tuple[int, tuple[int, ...]]


def bounds(state: State, B: int, L: int):
    a, H = state
    assert 0 <= B < L and 1 <= a <= B + 1
    assert len(H) == len(set(H)) and all(1 <= x < L for x in H)
    assert len(H) <= B and a not in H
    d = B + 1 - a
    occupancy = [sum(x + j < L for x in H) for j in range(d + 1)]
    front = []
    for s in range(d + 1):
        val = next((m for m in range(1, d-s+2)
                    if occupancy[s+m-1]+m > B), None)
        front.append(val)
    v = front[0]
    assert v is not None, ("infeasible reachable state",state,B,L)
    safe = d - B + occupancy[d]
    star = v - 1
    last = max(j for j in range(star,d+1) if occupancy[j]+v>B)
    cost = last - star
    assert 0 <= cost <= safe <= d
    assert [i for i,vv in enumerate(front) if vv is not None] == list(range(safe+1))
    assert [i for i,vv in enumerate(front) if vv == v] == list(range(cost+1))
    # Exact state-level equivalence: no historical expiry over this interval.
    expired = [x for x in H if x+star<L and x+star+safe>=L]
    assert (safe == cost) == (not expired)
    return dict(s_safe=safe, s_cost=cost, m_star=v, t_star_offset=star,
                U=occupancy, frontier=front, expiring_ages=expired)


def transitions(state: State, B: int, L: int, policy="original"):
    a,H=state
    p=bounds(state,B,L)
    older=tuple(x+1 for x in H if x+1<L)
    # A natural low-deviation anchor never makes an attempt.
    yield "low_anchor", (1,older)
    wait = p["s_safe"]>0 if policy=="original" else p["s_cost"]>0
    if wait:
        yield "high_wait", (a+1,older)
    else:
        yield "high_success", (1,older)
        if len(H)<B:
            yield "high_block", (a+1,(1,)+older)


def graph(B,L,policy):
    root=(1,())
    parent={root:None}
    q=deque([root])
    edges=[]
    while q:
        state=q.popleft()
        for event,dest in transitions(state,B,L,policy):
            edges.append((state,event,dest))
            if dest not in parent:
                parent[dest]=(state,event)
                q.append(dest)
    return parent,edges


def witness(parent,state):
    sequence=[]
    while parent[state] is not None:
        prev,event=parent[state]
        sequence.append(event)
        state=prev
    return list(reversed(sequence))


def absolute_replay(events,B,L,policy):
    """Separate absolute-time execution of the manuscript rule for audit."""
    tau=0
    failures=[]
    rows=[]
    for k,event in enumerate(events,1):
        D=tau+B+1
        active=[h for h in failures if k-L+1<=h<k]
        U_D=sum(D-L+1<=h<k for h in failures)
        n=D-k+1
        ss=n-1-B+U_D
        values=[]
        for s in range(n):
            values.append(next((m for m in range(1,n-s+1)
                                if sum(k+s+m-L<=h<k for h in failures)+m>B),None))
        assert values[0] is not None
        sc=max(s for s,val in enumerate(values) if val==values[0])
        high=event!="low_anchor"
        attempt=high and not ((n>B-U_D+1) if policy=="original" else sc>=1)
        assert attempt == (event in ("high_success","high_block"))
        beta=int(event=="high_block")
        if beta:
            assert len(active)<B
            failures.append(k)
        received=attempt and not beta
        row=dict(k=k,tau_before=tau,D=D,H_before=active,high=high,
                 attempt=attempt,blocked=beta,success=bool(received),
                 s_safe=ss,s_cost=sc,m_star=values[0],event=event)
        if not high or received:
            tau=k
        assert k-tau<=B
        assert all(sum(max(1,t-L+1)<=h<=t for h in failures)<=B
                   for t in range(1,k+1))
        row["tau_after"]=tau
        rows.append(row)
    k=len(events)+1
    endpoint=(k-tau,tuple(sorted(k-h for h in failures if k-h<L)))
    return rows,endpoint


def worst_attempts(state,B,L,policy):
    """Independent finite all-high task tree; a success terminates the task."""
    @lru_cache(None)
    def f(a,H):
        options=dict(transitions((a,H),B,L,policy))
        if "high_wait" in options:
            return f(*options["high_wait"])
        val=1
        if "high_block" in options:
            val=max(val,1+f(*options["high_block"]))
        return val
    return f(*state)


def general_witness(B,L):
    assert B>=2 and L>=B+4
    tau0=L-B-2
    return (["high_block"]+["low_anchor"]*(tau0-1)+["high_wait"]
            +["high_block"]*(B-1)+["high_success"])


def jdump(x):
    return json.dumps(x,ensure_ascii=False,indent=2,allow_nan=False)+"\n"


def csv_text(rows):
    s=io.StringIO(newline="")
    w=csv.DictWriter(s,fieldnames=list(rows[0]),lineterminator="\n")
    w.writeheader();w.writerows(rows)
    return s.getvalue()


def gz_lines(rows):
    raw=io.BytesIO()
    with gzip.GzipFile(fileobj=raw,mode="wb",mtime=0,filename="") as z:
        for row in rows:
            z.write((json.dumps(row,sort_keys=True,separators=(",",":"))+"\n").encode())
    return raw.getvalue()


def compute(max_L=14):
    table=[];all_states=[];all_edges=[];witnesses=[];total_states=total_edges=0
    for L in range(2,max_L+1):
        for B in range(L):
            for policy in ("original","cost_neutral"):
                parents,edges=graph(B,L,policy)
                states=sorted(parents)
                ids={s:i for i,s in enumerate(states)}
                gaps=[]
                total_states+=len(states);total_edges+=len(edges)
                for s in states:
                    p=bounds(s,B,L)
                    if p["s_safe"]>p["s_cost"]:
                        gaps.append(s)
                    if policy=="cost_neutral":
                        assert worst_attempts(s,B,L,policy)==p["m_star"]
                    else:
                        assert worst_attempts(s,B,L,policy)==p["frontier"][p["s_safe"]]
                    all_states.append(dict(B=B,L=L,policy=policy,id=ids[s],
                                           anchor_age=s[0],failure_ages=list(s[1]),**p))
                for state,event,dest in edges:
                    assert dest in parents
                    all_edges.append(dict(B=B,L=L,policy=policy,src=ids[state],
                                          event=event,dst=ids[dest]))
                    # Per fixed-anchor task, cost-neutral waiting preserves V;
                    # a legal blocked attempt spends exactly one of V.
                    if policy=="cost_neutral":
                        before=bounds(state,B,L)["m_star"]
                        after=bounds(dest,B,L)["m_star"]
                        if event=="high_wait":assert after==before
                        if event=="high_block":assert after==before-1
                table.append(dict(B=B,L=L,policy=policy,reachable_states=len(states),
                                  transitions=len(edges),strict_gap_states=len(gaps),
                                  max_s_safe=max(bounds(s,B,L)["s_safe"] for s in states),
                                  max_gap=max(bounds(s,B,L)["s_safe"]-bounds(s,B,L)["s_cost"] for s in states)))
                if policy=="original":
                    predicted=B>=2 and L>=B+4
                    assert bool(gaps)==predicted,(B,L,gaps[:1])
                    if gaps:
                        chosen=min(gaps,key=lambda s:(len(witness(parents,s)),s))
                        events=witness(parents,chosen)
                        trace,end=absolute_replay(events,B,L,policy)
                        assert end==chosen
                        witnesses.append(dict(B=B,L=L,shortest_events=events,
                                              absolute_trace=trace,endpoint=chosen,
                                              endpoint_bounds=bounds(chosen,B,L)))
                        general=general_witness(B,L)
                        _,general_end=absolute_replay(general,B,L,policy)
                        pp=bounds(general_end,B,L)
                        assert pp["m_star"]==1 and pp["s_cost"]==0 and pp["s_safe"]>0
    original=[r for r in table if r["policy"]=="original"]
    new=[r for r in table if r["policy"]=="cost_neutral"]
    supplied=["high_block","low_anchor","high_wait","high_block","high_success"]
    trace,end=absolute_replay(supplied,2,6,"original")
    assert end==(1,(2,5)) and bounds(end,2,6)["frontier"]==[1,2,None]
    # Original continues wait/block/success; modified sends successfully at k=6.
    old_trace,_=absolute_replay(supplied+["high_wait","high_block","high_success"],2,6,"original")
    summary=dict(status="PASS",scope="complete finite symbolic communication graph closure, not Monte Carlo",
                 L_range=[2,max_L],budget_range="0..L-1",parameter_pairs=len(original),
                 total_states_both_policies=total_states,total_transitions_both_policies=total_edges,
                 original_total_states=sum(r["reachable_states"] for r in original),
                 cost_neutral_total_states=sum(r["reachable_states"] for r in new),
                 original_strict_gap_parameter_pairs=sum(r["strict_gap_states"]>0 for r in original),
                 original_strict_gap_states=sum(r["strict_gap_states"] for r in original),
                 checked_parameter_characterization="exists a reachable strict gap iff B>=2 and L>=B+4",
                 new_policy_all_states_task_minimax=True,
                 supplied_counterexample=dict(trace=trace,endpoint=end,bounds=bounds(end,2,6),
                                              original_all_high_worst_continuation=old_trace),
                 semantics="low/high free symbolic inputs; plant support argument in report; no new physical trajectories")
    return {"summary.json":jdump(summary).encode(),
            "parameter_summary.csv":csv_text(table).encode(),
            "reachable_states.jsonl.gz":gz_lines(all_states),
            "reachable_transitions.jsonl.gz":gz_lines(all_edges),
            "shortest_gap_witnesses.json":jdump(dict(witnesses=witnesses)).encode()}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--verify",action="store_true")
    args=p.parse_args()
    outputs=compute()
    out=ROOT/"data"
    if args.verify:
        for name,b in outputs.items():
            assert (out/name).read_bytes()==b,name
        print("PASS: all P5.2 integer graph outputs reproduce byte-for-byte")
    else:
        out.mkdir(parents=True,exist_ok=True)
        for name,b in outputs.items():(out/name).write_bytes(b)
        print(jdump(json.loads(outputs["summary.json"])))


if __name__=="__main__":
    main()
