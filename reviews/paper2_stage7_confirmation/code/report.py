"""Rebuild every confirmation table and figure from the registered episode rows."""
from __future__ import annotations
import csv
from collections import Counter,defaultdict
import hashlib
import json
import math
from pathlib import Path
import numpy as np
from scipy.stats import beta,t
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from run import CASES,TASK,digest,read,save

OUT=TASK/"reports"
REG=read(TASK/"registration.json")
METHODS=("M0","h0","q95","q99","M1","reject","M2","M3","O")
GATES=("h0","q95","q99","M1","reject")
GROUPS=tuple(CASES)
BOOT=202611251714

def table(name,rows):
    with (OUT/(name+".csv")).open("w",encoding="utf-8-sig",newline="") as stream:
        writer=csv.DictWriter(stream,fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

def interval(values):
    x=np.asarray(values,float)
    m=float(x.mean())
    half=float(t.ppf(.975,x.size-1)*x.std(ddof=1)/math.sqrt(x.size))
    return m,m-half,m+half

def cp(k,n,alpha=.05):
    return (float(beta.ppf(alpha/2,k,n-k+1)) if k else 0.,
            float(beta.ppf(1-alpha/2,k+1,n-k)) if k<n else 1.)

def describe_times(x):
    return dict(n=len(x),p50=float(np.median(x)),p95=float(np.quantile(x,.95)),max=float(np.max(x)))

def inputs():
    folder=TASK/"results/confirmation"
    ids={f"{g}-{i:04d}" for g,n in REG["counts"].items() for i in range(n)}
    paths=sorted(folder.glob("*.json"))
    actual={p.stem for p in paths}
    if actual!=ids:
        raise SystemExit(f"Incomplete confirmation: {len(actual & ids)}/{len(ids)}. Missing: {sorted(ids-actual)}")
    rows=[read(p) for p in paths]
    assert len({r["history_sha256"] for r in rows})==len(rows)
    for p,r in zip(paths,rows):
        assert r["id"]==p.stem and r["identity"]==digest(TASK/"registration.json")
        assert r["phase"]=="confirmation" and r["seed"]==REG["seed"]
        assert r["group"]==p.stem.rsplit("-",1)[0] and r["episode"]==int(p.stem.rsplit("-",1)[1])
        assert [q["t"] for q in r["queries"]]==REG["queries"] and len(r["bounds"])==608
        assert len(set(q["prefix"] for q in r["queries"]))==4 and set(r["metrics"])==set(METHODS)
        assert all(math.isfinite(m["loss"]) for m in r["metrics"].values())
        assert abs(r["metrics"]["O"]["conditional"]-r["opportunity"])<1e-7
    return rows

def paired_tables(rows):
    individual,groups,comparisons=[],[],[]
    rng=np.random.default_rng(BOOT)
    for g,(b,k) in CASES.items():
        cell=[r for r in rows if r["group"]==g]
        for m in METHODS:
            obs=[]
            for r in cell:
                v=r["metrics"][m]
                obs.append(dict(id=r["id"],group=g,method=m,loss=v["loss"],
                    realized_gain=r["metrics"]["M0"]["loss"]-v["loss"],conditional_gain=v["conditional"],
                    certified_bound=v["certified"],opportunity=r["opportunity"],nonzero_608=v["nonzero"],
                    first_nonzero=v["first_nonzero"],first_in_window=v["first_in_window"],
                    preattack_steps=v["preattack"],useful_or_point_active_steps=v["useful_steps"],
                    endpoint=v["endpoint"],energy_608=v["energy"],fallback_608=v["fallback"]))
            individual.extend(obs)
            def values(key):
                return np.asarray([o[key] for o in obs])
            gain,lo,hi=interval(values("realized_gain"))
            num=float(values("conditional_gain").sum())
            den=float(values("opportunity").sum())
            delay=[o["first_in_window"]-k for o in obs if o["first_in_window"] is not None]
            n=len(obs)
            groups.append(dict(group=g,method=m,n=n,loss=float(values("loss").mean()),
                gain=gain,gain_lo=lo,gain_hi=hi,conditional=num/n,
                mean_cert=values("certified_bound").mean() if m in ("M2","M3") else None,
                numerator=num,denominator=den,recovery_share=num/den if den else None,
                first_success=len(delay),first_success_denominator=n,
                median_delay_among_successes=float(np.median(delay)) if delay and b else None,
                mean_useful_or_active_steps=float(values("useful_or_point_active_steps").mean()),
                useful_at_endpoint=int(values("endpoint").sum()),
                preattack_episodes=int((values("preattack_steps")>0).sum()),
                active_608=int((values("nonzero_608")>0).sum()),mean_energy_608=float(values("energy_608").mean()),
                fallback_steps=int(values("fallback_608").sum())))
        for j in ("M2","M1","h0","q95","q99","reject"):
            x=np.array([r["metrics"][j]["loss"]-r["metrics"]["M3"]["loss"] for r in cell])
            mean,low,high=interval(x)
            bot,top=np.quantile(rng.choice(x,(10000,len(x)),replace=True).mean(axis=1),[.025,.975])
            comparisons.append(dict(group=g,comparison="M3_vs_"+j,n=len(x),difference=mean,
                    low=low,high=high,bootstrap_low=bot,bootstrap_high=top,
                    percent_of_monitor=100*mean/np.mean([r["metrics"]["M0"]["loss"] for r in cell])))
    table("paired_trajectories",individual)
    table("method_by_case",groups)
    table("paired_comparisons",comparisons)
    equal=[]
    for j in ("M2","M1"):
        samples=[np.array([r["metrics"][j]["loss"]-r["metrics"]["M3"]["loss"] for r in rows if r["group"]==g])
                 for g,(b,_) in CASES.items() if b]
        boot=np.mean([rng.choice(x,(10000,len(x))).mean(axis=1) for x in samples],axis=0)
        low,high=np.quantile(boot,[.025,.975])
        equal.append(dict(comparison="M3_vs_"+j,four_cell_mean=np.mean([x.mean() for x in samples]),
                          stratified_boot_low=low,stratified_boot_high=high))
    table("equal_weight_attacks",equal)
    return groups,comparisons

def health_table(rows):
    health=[r for r in rows if r["group"]=="health"]
    n=len(health)
    result=[]
    for method in (*GATES,"M2"):
        a=np.array([r["metrics"][method]["nonzero"]>0 for r in health])
        b=np.array([r["metrics"]["M3"]["nonzero"]>0 for r in health])
        plus,minus=int((a & ~b).sum()),int((~a & b).sum())
        lp,up=cp(plus,n,.025)
        lm,um=cp(minus,n,.025)
        lo,hi=lp-um,up-lm
        la,ua=cp(int(a.sum()),n)
        lb,ub=cp(int(b.sum()),n)
        result.append(dict(method=method,n=n,method_active=int(a.sum()),m3_active=int(b.sum()),
               method_rate=a.mean(),method_lo=la,method_hi=ua,m3_rate=b.mean(),m3_lo=lb,m3_hi=ub,
               only_method=plus,only_m3=minus,both=int((a&b).sum()),neither=int((~a&~b).sum()),
               diff=(plus-minus)/n,lo=lo,hi=hi,equivalent=bool(lo>-.01 and hi<.01)))
    table("health_paired",result)
    return result

def costs_and_queries(rows):
    queries,per_trace,aggregate,fail=[],[],[],[]
    reasons=defaultdict(Counter)
    for r in rows:
        for q in r["queries"]:
            if any(s["certified"] for s in q["levels"]):
                outcome="positive_certificate"
            elif float(q["zero_log_cutoff"]["hi"])<=0:
                outcome="zero_compatible"
            else:
                outcome="unresolved"
            reasons[r["group"]][outcome]+=1
            for s in q["levels"] or [{}]:
                queries.append(dict(id=r["id"],group=r["group"],t=q["t"],prefix=q["prefix"],
                    score=q["score"],onset=q["onset"],b=q["amplitude"],direction=q["direction"],
                    M1_enabled=Decimal(q["score"])>Decimal(REG["thresholds"]["M1"]),
                    cutoff_lo=q["zero_log_cutoff"]["lo"],cutoff_hi=q["zero_log_cutoff"]["hi"],
                    level=s.get("level"),target=s.get("target"),nodes=s.get("nodes"),
                    status=s.get("reason","NO_POINT_DIRECTION"),outcome=outcome,
                    joint_query_s=q["seconds"],point_query_s=q["point_seconds"]))
        per_trace.append(dict(id=r["id"],group=r["group"],cpu=r["cpu"],seconds=r["seconds"],
            **describe_times([q["seconds"] for q in r["queries"]]),**r["breakdown"]))
    for g in (*GROUPS,"all"):
        group=[r for r in rows if r["group"]==g or g=="all"]
        for scope in ("all","first_scheduled","later_scheduled","first_success","after_first_success"):
            for key in ("joint","point","additional_certificate"):
                values=[]
                for r in group:
                    qs=r["queries"]
                    first=next((i for i,q in enumerate(qs) if any(l["certified"] for l in q["levels"])),None)
                    for i,q in enumerate(qs):
                        if scope=="first_scheduled" and i!=0 or scope=="later_scheduled" and i==0: continue
                        if scope=="first_success" and first!=i: continue
                        if scope=="after_first_success" and (first is None or i<=first): continue
                        values.append({"joint":q["seconds"],"point":q["point_seconds"],
                                       "additional_certificate":q["seconds"]-q["point_seconds"]}[key])
                aggregate.append(dict(group=g,phase=scope,cost=key,trajectories=len(group),
                                      **(describe_times(values) if values else dict(n=0,p50=None,p95=None,max=None))))
        if g!="all":
            trace_reasons=Counter()
            for r in group:
                trace_reasons.update({item["outcome"] for item in queries if item["id"]==r["id"]})
            for outcome in ("positive_certificate","zero_compatible","unresolved"):
                fail.append(dict(group=g,outcome=outcome,queries=reasons[g][outcome],query_total=len(group)*4,
                                 trajectories_ever=trace_reasons[outcome],trajectory_total=len(group),
                                 unscheduled_steps=len(group)*604))
    table("query_log",queries)
    table("cost_per_trajectory",per_trace)
    table("query_cost",aggregate)
    table("query_outcomes",fail)
    return aggregate,fail

from decimal import Decimal

def figures(rows,means,health):
    fig,ax=plt.subplots(figsize=(7,4),layout="constrained")
    for g in ("strong_early","strong_late","weak_early","weak_late"):
        x=[next(o["method_rate"] for o in health if o["method"]==m) for m in GATES]
        y=[next(v["gain"] for v in means if v["group"]==g and v["method"]==m) for m in GATES]
        color=ax.plot(np.array(x)*100,y,"o-",label=g)[0].get_color()
        y3=next(v["gain"] for v in means if v["group"]==g and v["method"]=="M3")
        ax.scatter([100*health[0]["m3_rate"]],[y3],marker="*",s=100,color=color)
    ax.axhline(0,color="0.65",lw=0.7)
    ax.set(xlabel="Healthy episodes with any emitted action (%)",ylabel="Mean 512-step realized loss reduction",
           title="Point gates (circles) and M3 (stars)")
    ax.legend(fontsize=8)
    fig.savefig(OUT/"tradeoff.png",dpi=170);plt.close(fig)
    group=sorted([r for r in rows if r["group"]=="strong_early"],key=lambda r:r["episode"])
    curves=[]
    records=[]
    for r in group:
        q=next((q for q in r["queries"] if any(l["certified"] for l in q["levels"])),None)
        if q:
            t0=q["t"]
            stop=min(next((t for t in REG["queries"] if t>t0),562),562)
            curve=r["bounds"][t0:stop]
            curves.append((r["id"],np.array(curve)))
            records.extend(dict(id=r["id"],time=t0+i,lag=i,M2=b[0],M3=b[1]) for i,b in enumerate(curve))
    fig,axes=plt.subplots(1,2,figsize=(9,3.7),layout="constrained")
    if records:
        table("first_certificate_curves",records)
        label,curve=curves[0]
        for j,name in enumerate(("M2","M3")):
            axes[0].plot(curve[:,j],label=name)
        axes[0].set_title(label+" after shared first certificate",fontsize=9)
        axes[0].legend()
    else:
        axes[0].text(.1,.5,"No shared certificate")
    all_bounds=np.array([r["bounds"] for r in group]).mean(axis=0)
    for j,name in enumerate(("M2","M3")):
        axes[1].plot(np.arange(50,562),all_bounds[50:562,j],label=name)
    axes[1].set_title(f"All {len(group)} primary episodes, including zeros",fontsize=9)
    for ax,xlabel in zip(axes,("Lag (steps)","Absolute step")):
        ax.axhline(.000625,color="black",lw=.7,linestyle=":")
        ax.set(xlabel=xlabel,ylabel="Audited one-step lower bound")
    fig.savefig(OUT/"persistence.png",dpi=170);plt.close(fig)
    return curves[0][0] if curves else None

def main():
    OUT.mkdir(exist_ok=True)
    rows=inputs()
    groups,comparisons=paired_tables(rows)
    health=health_table(rows)
    costs,fail=costs_and_queries(rows)
    rep=figures(rows,groups,health)
    primary=[c for c in comparisons if c["group"]=="strong_early"][:2]
    m3,m2=[next(g for g in groups if g["group"]=="strong_early" and g["method"]==m) for m in ("M3","M2")]
    risk=sum(r["risk_violations"] for r in rows)
    valid=not risk and all(r["max_direct_error"]<2.1e-8 for r in rows)
    mechanism=valid and primary[0]["low"]>0 and m3["mean_useful_or_active_steps"]>m2["mean_useful_or_active_steps"]
    matched=next(h for h in health if h["method"]=="M1")["equivalent"]
    decision=("支持方法论文" if mechanism and primary[1]["low"]>0 and matched
              else "支持限定工况下的机理与可校正性分析" if mechanism else "证据待补")
    metrics=dict(decision=decision,n=len(rows),primary=primary,health=next(h for h in health if h["method"]=="M1"),
        cpu_hours=sum(r["cpu"] for r in rows)/3600,first_curve=rep,
        direct_error_max=max(r["max_direct_error"] for r in rows),coverage_missed_steps=sum(r["coverage_missed_steps"] for r in rows),
        risk_violations=risk,legacy_fallback_steps=sum(r["legacy_fallback_steps"] for r in rows),
        numerical_fallback_steps={m:sum(r["metrics"][m]["fallback"] for r in rows) for m in ("M2","M3")},
        error_records=len(list((TASK/"results/confirmation/errors").glob("*.json"))))
    save(OUT/"decision.json",metrics)
    print(json.dumps(metrics,ensure_ascii=False,default=float))
if __name__=="__main__":
    main()
