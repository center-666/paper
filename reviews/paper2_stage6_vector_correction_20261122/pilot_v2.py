"""Frozen small recovery feasibility experiment; truth remains in evaluator."""
from __future__ import annotations
import os
for key in ("OPENBLAS_NUM_THREADS","OMP_NUM_THREADS","MKL_NUM_THREADS"):os.environ[key]="1"
import argparse,hashlib,json,time
from pathlib import Path
from fractions import Fraction as F
from decimal import Decimal,localcontext
from concurrent.futures import ProcessPoolExecutor,as_completed
import numpy as np
from vector_record import VectorRecord,I,D
from exact_linear import matrix,matmul,transpose,update,inverse,asfloat
from projection import inner

HERE=Path(__file__).resolve().parent


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(path,data):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(data,indent=2,allow_nan=False)+"\n",encoding="utf8",newline="\n")
def frozen():
    data=json.loads((HERE/"freeze_v2.json").read_text(encoding="utf8"))
    for name,digest in data["inputs"].items():
        assert sha(HERE/name)==digest,"Frozen input changed: "+name


def exact_mid(box):
    with localcontext() as c:
        c.prec=50
        return (box.lo+box.hi)/2


def choose_point(record,grid):
    best_score=D(0);best_k=None;best_b=D(0)
    for b in grid:
        values=record.all_likelihoods(I.exact(str(b)))
        for k,value in enumerate(values):
            score=exact_mid(value)
            if score>best_score:best_score,best_k,best_b=score,k,D(str(b))
    if best_k is None:return None,np.zeros(2),D(0)
    H=np.array([float(exact_mid(x)) for x in record.candidates[best_k]["H"]])
    point=float(best_b)*H
    norm=np.max(np.abs(point))
    if norm<1e-14:return None,point,best_b
    direction=tuple(F(format(x/norm,".6f")) for x in point)
    if direction==(0,0):return None,point,best_b
    return direction,point,best_b


def transport(certificate,Fmat,K,sent,bmax):
    if certificate is None:return None
    d,z=certificate
    inverse_t=transpose(inverse(Fmat))
    moved=matmul(inverse_t,[[x] for x in d])
    moved=tuple(row[0] for row in moved)
    injection=sum(moved[i]*K[i][0] for i in range(2))*bmax if sent else F(0)
    support=z+min(F(0),injection)
    if support<=0:return None
    scale=max(abs(x) for x in moved)
    if not scale:return None
    return tuple(x/scale for x in moved),support/scale


def correction(certificate,cap):
    if certificate is None:return np.zeros(2),0.
    d,z=certificate;norm=sum(x*x for x in d)
    action=tuple(z/norm*x for x in d)
    l1=sum(abs(x) for x in action)
    if l1>cap:action=tuple(x*cap/l1 for x in action)
    # For an inward scaling, guarantee remains at least squared action norm.
    return np.array([float(x) for x in action]),float(sum(x*x for x in action))


def run_one(job):
    stage,bi,index=job
    frozen()
    protocol=json.loads((HERE/"pilot_protocol.json").read_text(encoding="utf8"))
    model=json.loads((HERE/"model.json").read_text(encoding="utf8"))
    b=protocol["attack_strengths"][bi];t0=protocol["attack_start"]
    N=t0+max(protocol["evaluation_windows"])
    path=HERE/"results_v2"/stage/f"b{b:g}_episode{index:03d}.json"
    if path.exists():raise RuntimeError("Output exists")
    rngs=[np.random.default_rng(s) for s in np.random.SeedSequence(
        [protocol[stage+"_seed"],bi,index]).spawn(3)]
    phys,events,phase=rngs
    A=np.array(model["A"],float);C=np.array(model["C"],float)
    Q=np.array(model["Q"],float);R=float(model["R"]);Z=float(model["Z"])
    delta=float(model["quantization_half_width"])
    record=VectorRecord(model)
    error=np.linalg.cholesky(np.array(model["P0_prior"],float))@phys.normal(size=2)
    true_theta=np.zeros(2)
    point=np.zeros(2);point_b=0.;cert=None
    total={name:0. for name in ("monitor","point","certified","oracle","certified_gain",
                                 "conditional_certified_gain","squared_actions","point_gain")}
    timing={name:0. for name in ("maintenance","point_scoring","certificate_search","transport")}
    peak=0.;log=[];snapshots={};first_useful=None;first_nonzero=None;alarm=None
    cover_failures=0;negative_conditional=0;nonzero_outputs=0
    started=time.perf_counter()
    for t in range(N):
        prior=record.P
        v=np.sqrt(R)*phys.normal();w=np.linalg.cholesky(Q)@phys.normal(size=2)
        # r is the full-period uniform reconstruction offset relative to Cm.
        r=0. if t==0 else delta*(2*phase.random()-1)
        y=(C@error).item()+v
        sent=bool(events.random()>np.exp(-.5*Z*(y-r)**2))
        action=b if sent and t>=t0 else 0.
        u=y+action if sent else None
        post,Krat,Trat=update(prior,record.C,record.R+(0 if sent else 1/record.Z))
        Fmat=matmul(Trat,record.A)
        K=np.array(asfloat(Krat)).ravel();T=np.array(asfloat(Trat))
        s=time.perf_counter()
        cert=transport(cert,Fmat,Krat,sent,F(str(protocol["attack_strengths"][-1])))
        point=np.array(asfloat(Fmat))@point+(K*point_b if sent else 0.)
        timing["transport"]+=time.perf_counter()-s
        s=time.perf_counter()
        record.append(sent,None if u is None else repr(float(u)),repr(float(r)))
        timing["maintenance"]+=time.perf_counter()-s
        # Current posterior error/true contamination are offline evaluation only.
        post_error=error-K*(y+action) if sent else error-K*r
        true_theta=T@(A@true_theta)+K*action
        if alarm is None and record.ref.lo>=D(1)/D(str(protocol["detection_alpha"])):alarm=t
        if t in protocol["certification_times"]:
            s=time.perf_counter();direction,point,b_est=choose_point(record,protocol["point_estimator_grid"])
            point_b=float(b_est);timing["point_scoring"]+=time.perf_counter()-s
            if direction is not None:
                for level in protocol["certificate_levels"]:
                    scale=sum(abs(x) for x in direction)
                    target_fraction=F(str(level))*scale
                    with localcontext() as ctx:
                        ctx.prec=50
                        target=D(target_fraction.numerator)/D(target_fraction.denominator)
                    s=time.perf_counter()
                    result=record.certify_direction(direction,str(target),
                        epsilon=str(protocol["confidence_failure"]),max_nodes=protocol["max_refinement_nodes_per_query"])
                    timing["certificate_search"]+=time.perf_counter()-s
                    log.append({"time":t,"level":level,"direction":[str(x) for x in direction],**result})
                    if result["certified"]:
                        proposal=(direction,F(target))
                        new_action,new_gain=correction(proposal,F(str(protocol["output_l1_cap"])))
                        old_action,old_gain=correction(cert,F(str(protocol["output_l1_cap"])))
                        if new_gain>old_gain:cert=proposal
                    else:
                        break
        cert_action,guaranteed=correction(cert,F(str(protocol["output_l1_cap"])))
        if np.sum(np.abs(point))>protocol["output_l1_cap"]:
            point=point*protocol["output_l1_cap"]/np.sum(np.abs(point))
        conditional=2*true_theta@cert_action-cert_action@cert_action
        if cert is not None:
            d,z=cert
            if float(np.array([float(x) for x in d])@true_theta)<float(z)-1e-10:cover_failures+=1
        if conditional<-1e-10:negative_conditional+=1
        if guaranteed>1e-20:
            nonzero_outputs+=1
            if first_nonzero is None:first_nonzero=t
        if guaranteed>=protocol["minimum_relevant_expected_gain"]-1e-12 and first_useful is None:first_useful=t
        if t>=t0:
            losses={"monitor":post_error@post_error,
                    "point":(post_error+point)@(post_error+point),
                    "certified":(post_error+cert_action)@(post_error+cert_action),
                    "oracle":(post_error+true_theta)@(post_error+true_theta)}
            for name,value in losses.items():total[name]+=float(value)
            total["certified_gain"]+=float(losses["monitor"]-losses["certified"])
            total["point_gain"]+=float(losses["monitor"]-losses["point"])
            total["conditional_certified_gain"]+=float(conditional)
            total["squared_actions"]+=guaranteed
        H=t-t0+1
        if H in protocol["evaluation_windows"]:
            snapshots[str(H)]={**total,"current_certified_action_norm":float(np.linalg.norm(cert_action)),
                "current_true_pollution_norm":float(np.linalg.norm(true_theta)),
                "first_useful":first_useful,"first_nonzero":first_nonzero,
                "coverage_violating_steps":cover_failures,
                "negative_conditional_gain_steps":negative_conditional}
        error=A@post_error+w
        peak=max(peak,float(np.linalg.norm(error)))
    output={"stage":stage,"b":b,"episode":index,"snapshots":snapshots,
            "certificate_queries":log,"timing":timing,"total_seconds":time.perf_counter()-started,
            "steps":N,"alarm_time":alarm,"first_useful":first_useful,"first_nonzero":first_nonzero,
            "coverage_violating_steps":cover_failures,"negative_conditional_gain_steps":negative_conditional,
            "nonzero_output_steps":nonzero_outputs,"max_prior_error_norm":peak,
            "record_stats":record.stats,"freeze_sha256":sha(HERE/"freeze_v2.json"),
            "numerics":"exact rational gains/certificate propagation plus Decimal likelihood intervals; floating Gaussian physical generator",
            "full_cost_includes_all_candidate_maintenance":True}
    write(path,output)
    return path.name,output["total_seconds"],total["certified_gain"]


def main():
    parser=argparse.ArgumentParser();parser.add_argument("stage",choices=("screen","final"))
    args=parser.parse_args();frozen()
    p=json.loads((HERE/"pilot_protocol.json").read_text(encoding="utf8"))
    if args.stage=="final" and not (HERE/"results_v2/screen/completion.json").exists():
        raise SystemExit("Complete screen first, do not tune confirmation")
    start=HERE/"results_v2"/args.stage/"start.json"
    if start.exists():raise SystemExit("Run already exists")
    n=p[args.stage+"_episodes_per_case"]
    jobs=[(args.stage,bi,i) for bi in range(3) for i in range(n)]
    write(start,{"jobs":jobs,"workers":p["workers"],"frozen":sha(HERE/"freeze_v2.json")})
    with ProcessPoolExecutor(max_workers=p["workers"]) as pool:
        for f in as_completed([pool.submit(run_one,job) for job in jobs]):
            name,seconds,gain=f.result()
            print(args.stage,name,round(seconds,2),"seconds","MSE_gain",round(gain,6),flush=True)
    write(HERE/"results_v2"/args.stage/"completion.json",{"status":"COMPLETE","episodes":len(jobs)})


if __name__=="__main__":main()
