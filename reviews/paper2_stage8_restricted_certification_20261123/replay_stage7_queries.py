"""Paired full-domain vs restricted recertification on saved Stage 7 traces."""
from __future__ import annotations
import json, math, time
from fractions import Fraction as F
from pathlib import Path
import sys

import numpy as np

HERE=Path(__file__).resolve().parent
STAGE6=HERE.parent/"paper2_stage6_vector_correction_20261122"
STAGE7=HERE.parent/"paper2_stage7_fixed_amplitude_20261122"
sys.path.insert(0,str(STAGE6));sys.path.insert(0,str(STAGE7));sys.path.insert(0,str(HERE))

from vector_record import VectorRecord
from exact_linear import matrix,update,matmul,add,transpose
from direction_cache_corrected import CorrectedFastEnvelope
from restricted_certification import certify_direction_restricted


def read(path):return json.loads(Path(path).read_text(encoding="utf8"))


def select_episodes():
    protocol=read(STAGE7/"fresh_protocol.json")
    selected=[]
    for path in sorted((STAGE7/"results"/"fresh_confirmation").glob("b0.25_episode*.json")):
        row=read(path)
        successes=row["successful_certificates"]
        if len(successes)<2:continue
        target=successes[-1]
        if not any(int(c["time"])<int(target["time"]) for c in successes):
            continue
        target_query=next(q for q in row["certificate_queries"]
            if q.get("certified") and int(q["time"])==int(target["time"])
            and q["level"]==target["level"] and q["direction"]==target["direction"])
        selected.append((row,target,target_query))
    return protocol,selected


def run_episode(archive,target,target_query,protocol,model):
    b=archive["b"];index=archive["episode"]
    t_target=int(target["time"]);t0=protocol["attack_start"]
    rngs=[np.random.default_rng(s) for s in np.random.SeedSequence(
        [protocol["seed"],protocol["attack_strengths"].index(b),index]).spawn(3)]
    phys,events,phase=rngs
    A=np.array(model["A"],float);C=np.array(model["C"],float)
    Q=np.array(model["Q"],float);R=float(model["R"]);Z=float(model["Z"])
    delta=float(model["quantization_half_width"])
    Af,Cf,Qf=(matrix(model[k]) for k in ("A","C","Q"))
    record=VectorRecord(model);envelope=CorrectedFastEnvelope(model)
    P=matrix(model["P0_prior"])
    error=np.linalg.cholesky(np.array(model["P0_prior"],float))@phys.normal(size=2)
    prior_success=[c for c in archive["successful_certificates"]
                   if int(c["time"])<t_target or
                   (int(c["time"])==t_target and c is not target)]
    by_time={}
    for cert in prior_success:by_time.setdefault(int(cert["time"]),[]).append(cert)
    target_record=None
    for t in range(t_target+1):
        v=math.sqrt(R)*phys.normal()
        w=np.linalg.cholesky(Q)@phys.normal(size=2)
        r=0. if t==0 else delta*(2*phase.random()-1)
        y=float((C@error).item()+v)
        sent=bool(events.random()>math.exp(-.5*Z*(y-r)**2))
        attack_input=b if sent and t>=t0 else 0.
        post,Kmat,T=update(P,Cf,F(model["R"])+(F(0) if sent else 1/F(model["Z"])))
        Fmat=matmul(T,Af)
        envelope.advance(sent)
        record.append(sent,None if not sent else repr(float(y+attack_input)),repr(float(r)))
        Kfloat=np.asarray([float(row[0]) for row in Kmat])
        post_error=error-Kfloat*(y+attack_input) if sent else error-Kfloat*r
        P=add(matmul(matmul(Af,post),transpose(Af)),Qf)
        error=A@post_error+w
        for cert in by_time.get(t,[]):
            envelope.add_certificate(tuple(F(x) for x in cert["direction"]),F(cert["z"]))
        if t==t_target:
            target_record=record
    if target_record is None or not envelope.bounds:
        raise AssertionError("The target lacks a prior retained envelope")

    direction=tuple(F(x) for x in target_query["direction"])
    z=str(target_query["target_support"])
    epsilon=str(protocol["confidence_failure"])
    nodes=int(protocol["max_refinement_nodes_per_query"])
    tick=time.perf_counter()
    full_eval_before=target_record.stats["likelihood_evaluations"]
    full_segments_before=target_record.stats["segments_tested"]
    full=target_record.certify_direction(direction,z,epsilon=epsilon,max_nodes=nodes)
    full_seconds=time.perf_counter()-tick
    full_evaluations=target_record.stats["likelihood_evaluations"]-full_eval_before
    full_segments=target_record.stats["segments_tested"]-full_segments_before
    tick=time.perf_counter()
    restricted=certify_direction_restricted(target_record,direction,z,envelope.bounds,
        epsilon=epsilon,bmax=str(model["attack_amplitude_cap"]),max_nodes=nodes)
    restricted_seconds=time.perf_counter()-tick
    restricted_evaluations=target_record.stats["likelihood_evaluations"]-full_eval_before-full_evaluations
    restricted_segments=restricted["segments_tested"]
    tick=time.perf_counter()
    witnessed=certify_direction_restricted(target_record,direction,z,envelope.bounds,
        epsilon=epsilon,bmax=str(model["attack_amplitude_cap"]),max_nodes=nodes,
        require_witness=True)
    witnessed_seconds=time.perf_counter()-tick
    witnessed_evaluations=(target_record.stats["likelihood_evaluations"]-
        full_eval_before-full_evaluations-restricted_evaluations)
    return {"episode":index,"time":t_target,"level":target["level"],
        "prior_certificate_count":len(prior_success),"retained_onsets":len(envelope.bounds),
        "full":full,"restricted":restricted,"restricted_with_witness":witnessed,
        "full_seconds":full_seconds,
        "restricted_seconds":restricted_seconds,
        "restricted_with_witness_seconds":witnessed_seconds,
        "full_likelihood_evaluations":full_evaluations,
        "full_segments_tested":full_segments,
        "restricted_likelihood_evaluations":restricted_evaluations,
        "restricted_segments_tested":restricted_segments,
        "witnessed_likelihood_evaluations":witnessed_evaluations,
        "speedup":full_seconds/max(restricted_seconds,1e-12),
        "decision_match":full["certified"]==restricted["certified"],
        "witnessless_matches_witnessed":restricted["certified"]==witnessed["certified"] and
            restricted["correction"]==witnessed["correction"],
        "certificate_matches_original":full["certified"]==target_query["certified"],
        "restricted_matches_original":restricted["certified"]==target_query["certified"],
        "source_certified":bool(target_query["certified"])}


def main():
    protocol,selected=select_episodes()
    model=read(STAGE6/"model.json")
    rows=[]
    for archive,target,query in selected:
        result=run_episode(archive,target,query,protocol,model)
        rows.append(result)
        print("restricted replay",result["episode"],"t",result["time"],
              "onsets",result["retained_onsets"],"full/restricted",result["full"]["reason"],
              result["restricted"]["reason"],"seconds",round(result["full_seconds"],3),
              round(result["restricted_seconds"],3),flush=True)
    out={"status":"PASS" if all(r["decision_match"] and r["certificate_matches_original"] and
        r["restricted_matches_original"] and r["witnessless_matches_witnessed"] for r in rows) else "MISMATCH",
        "episodes":len(rows),"independent_random_samples":False,
        "source_seed":protocol["seed"],"queries":rows,
        "mean_full_seconds":sum(r["full_seconds"] for r in rows)/max(len(rows),1),
        "mean_restricted_seconds":sum(r["restricted_seconds"] for r in rows)/max(len(rows),1),
        "mean_restricted_with_witness_seconds":sum(r["restricted_with_witness_seconds"] for r in rows)/max(len(rows),1),
        "mean_speedup":sum(r["speedup"] for r in rows)/max(len(rows),1),
        "sum_full_likelihood_evaluations":sum(r["full_likelihood_evaluations"] for r in rows),
        "sum_restricted_likelihood_evaluations":sum(r["restricted_likelihood_evaluations"] for r in rows),
        "sum_witnessed_likelihood_evaluations":sum(r["witnessed_likelihood_evaluations"] for r in rows),
        "limitation":"These are repeated certification queries on frozen Stage 7 records; no new performance trajectories are generated."}
    (HERE/"restricted_replay_results.json").write_text(json.dumps(out,indent=2)+"\n",
        encoding="utf8",newline="\n")
    print(json.dumps({k:v for k,v in out.items() if k!="queries"},indent=2))


if __name__=="__main__":main()
