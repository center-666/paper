"""Exact frontier reduction versus raw ACK/physical-window scheduling game."""
from functools import lru_cache
from itertools import product, permutations
from pathlib import Path
import csv
import hashlib
import json
import random
import shutil
import time

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "simulation/checks/2026-11-12_shared_channel_deadline_screen"
PLAN = ROOT / "simulation/shared_channel_deadline_plan_20261112.json"
INF = 10**6


def options(B, histories, n):
    ans = []
    for b, h in zip(B, histories):
        opts = []
        for r in range(1, min(b+1, n)+1):
            times = [t for t in range(n) if sum(h[t:]) + r > b]
            if times:
                opts.append((r, max(times)))
        ans.append(opts)
    return ans


def edf_schedule(selected, n):
    seq = [i for i in sorted(range(len(selected)), key=lambda i: (selected[i][1],i))
           for _ in range(selected[i][0])]
    finish = 0
    for i in sorted(range(len(selected)), key=lambda i: (selected[i][1],i)):
        finish += selected[i][0]
        if finish > selected[i][1]+1:
            return None
    return tuple(seq) if len(seq) <= n else None


def reduction(B, histories, n):
    best = INF; chosen = None; schedule = None
    opts = options(B, histories, n)
    for selected in product(*opts):
        cost = sum(r for r, _ in selected)
        if cost >= best:
            continue
        seq = edf_schedule(selected, n)
        if seq is not None:
            best, chosen, schedule = cost, selected, seq
    return best, chosen, schedule


def shift(histories, attempted, blocked):
    return tuple(h[1:]+(int(blocked and i==attempted),) for i,h in enumerate(histories))


def raw_game(B, histories, n, policy=None):
    """No U/frontier in state transitions: consume actual sliding suffix budget."""
    m = len(B); complete = (1<<m)-1

    @lru_cache(None)
    def V(t, h, done):
        if done == complete:
            return 0
        if t == n:
            return INF
        if policy is None:
            actions = [-1] + [i for i in range(m) if not (done>>i)&1]
        else:
            actions = [policy(t,h,done)]
        best = INF
        for i in actions:
            if i == -1:
                value = V(t+1, shift(h,-1,False), done)
            else:
                value = 1 + V(t+1, shift(h,i,False), done|(1<<i))
                if sum(h[i]) < B[i]:
                    value = max(value, 1+V(t+1, shift(h,i,True), done))
            best = min(best, value, INF)
        return best
    return V(0, histories, 0), V.cache_info().currsize


def greedy_rule(B, n, priority):
    order = {v:i for i,v in enumerate(priority)}
    def policy(t, h, done):
        choices = []
        for i, (b, hist) in enumerate(zip(B,h)):
            if (done>>i)&1: continue
            remaining = n-t
            first = next((a for a in range(remaining) if sum(hist[a:])+a+1>b), None)
            if first is None:
                choices.append((n+1,order[i],i));continue
            r = first+1
            latest = max(a for a in range(remaining) if sum(hist[a:])+r>b)
            choices.append((t+latest,order[i],i))
        return min(choices)[-1]
    return policy


def fixed_rule(sequence):
    # Skip slots allocated to tasks that have already succeeded; keep future slots fixed.
    def policy(t,h,done):
        if t>=len(sequence): return -1
        i=sequence[t]
        return -1 if (done>>i)&1 else i
    return policy


def analyze(B, histories, n, tag):
    value, selected, seq = reduction(B,histories,n)
    game, states = raw_game(B,histories,n)
    assert game == value, (B,histories,n,game,value)
    local = options(B,histories,n)
    local_cost = INF
    if all(local):
        minimal = tuple(min(opts) for opts in local)
        if edf_schedule(minimal,n) is not None:
            local_cost = sum(r for r,_ in minimal)
    safe_cost = sum(b+1 for b in B)
    if safe_cost>n: safe_cost=INF
    greedy = min(raw_game(B,histories,n,greedy_rule(B,n,p))[0] for p in permutations(range(len(B))))
    row = {"tag":tag,"tasks":len(B),"L":len(histories[0])+1,"n":n,
           "B":json.dumps(B),"histories":json.dumps(histories),
           "raw_game_optimum":None if game>=INF else game,
           "option_optimum":None if value>=INF else value,
           "frozen_local_min_cost":None if local_cost>=INF else local_cost,
           "Bplus1_cost":None if safe_cost>=INF else safe_cost,
           "best_priority_dynamic_EDF_cost":None if greedy>=INF else greedy,
           "state_count":states,
           "gain_over_frozen_local_min":value<local_cost,
           "gain_over_Bplus1":value<safe_cost,
           "gain_over_best_priority_EDF":value<greedy}
    witness = {**row,"selected_options":selected,"planned_sequence":seq}
    if seq is not None:
        implemented,_=raw_game(B,histories,n,fixed_rule(seq))
        assert implemented == value, (witness,implemented)
    return row,witness


def main():
    OUT.mkdir(parents=True,exist_ok=False)
    shutil.copy2(PLAN,OUT/"plan.json")
    shutil.copy2(__file__,OUT/Path(__file__).name)
    (OUT/"registration.json").write_text(json.dumps({
        "plan_sha256":hashlib.sha256(PLAN.read_bytes()).hexdigest(),
        "script_sha256":hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "test_type":"exact enumeration; no random physical estimator trajectories"},indent=2),encoding="utf-8")
    started=time.perf_counter();rows=[];witnesses=[]
    row,collision=analyze((1,1),((0,1),(0,1)),3,"predeclared_collision")
    rows.append(row);witnesses.append(collision)
    for L in range(2,6):
        history_by_B={b:[h for h in product((0,1),repeat=L-1) if sum(h)<=b]
                      for b in range(min(2,L-1)+1)}
        for B in product(history_by_B,repeat=2):
            for h in product(*(history_by_B[b] for b in B)):
                for n in range(1,L+1):
                    row,w=analyze(B,h,n,"exhaustive_two_tasks")
                    rows.append(row)
                    if row["gain_over_best_priority_EDF"] and len(witnesses)<30:witnesses.append(w)
        print(json.dumps({"completed_L":L,"instances":len(rows)}),flush=True)
    rng=random.Random(20261112)
    for k in range(128):
        L=rng.choice((3,4,5,6,7));B=tuple(rng.randrange(min(2,L-1)+1) for _ in range(3))
        hs=[]
        for b in B:
            allh=[h for h in product((0,1),repeat=L-1) if sum(h)<=b]
            hs.append(rng.choice(allh))
        row,w=analyze(B,tuple(hs),rng.randint(1,L),"seeded_three_tasks")
        rows.append(row)
        if row["gain_over_best_priority_EDF"] and len(witnesses)<30:witnesses.append(w)
    with (OUT/"instances.csv").open("w",encoding="utf-8-sig",newline="") as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    result={"passed":True,"instances":len(rows),"finite_optima":sum(r["option_optimum"] is not None for r in rows),
            "reduction_game_mismatches":0,"constructed_schedule_mismatches":0,
            "strict_gains_over_frozen_local_min":sum(r["gain_over_frozen_local_min"] for r in rows),
            "strict_gains_over_Bplus1":sum(r["gain_over_Bplus1"] for r in rows),
            "strict_gains_over_best_priority_EDF":sum(r["gain_over_best_priority_EDF"] for r in rows),
            "elapsed_seconds":time.perf_counter()-started,
            "new_state_estimation_trajectories":0,"theorem_novelty_confirmed":False}
    (OUT/"results.json").write_text(json.dumps(result,indent=2),encoding="utf-8")
    (OUT/"witnesses.json").write_text(json.dumps(witnesses,indent=2),encoding="utf-8")
    print(json.dumps(result,indent=2),flush=True)


if __name__=="__main__":main()
