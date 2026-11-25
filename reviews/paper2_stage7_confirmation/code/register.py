"""Compute and persist the design before using any confirmation seed."""
from __future__ import annotations
import json, math, platform, subprocess, sys
from decimal import Decimal
from statistics import mean,stdev
from pathlib import Path
import numpy as np
import scipy
from engine import TASK, STAGE6, STAGE7
from run import CASES, DEV_SEED, digest, read, save

def main():
    target=TASK/"registration.json"
    if target.exists() or (TASK/"results/confirmation").exists():
        raise FileExistsError("Use the already registered design")
    thresholds=read(TASK/"results/cutoffs.json")["thresholds"]
    rows=[read(p) for p in sorted((TASK/"results/development").glob("*.json"))]
    early=[r for r in rows if r["group"]=="strong_early"]
    assert len(early)==6 and len(rows)==10
    cpu={g:mean(r["cpu"] for r in rows if r["group"]==g) for g in CASES}
    differences=[[],[]]
    for r in early:
        m=r["metrics"]
        differences[0].append(m["M2"]["loss"]-m["M3"]["loss"])
        gain=sum(q["point_gain_in_window"] for q in r["queries"]
                 if Decimal(q["score"])>Decimal(thresholds["M1"]))
        differences[1].append(m["M0"]["loss"]-gain-m["M3"]["loss"])
    sd=list(map(stdev,differences))
    sizes=[math.ceil(((1.96+.84)*s)**2) for s in sd]
    monitor=mean(r["metrics"]["M0"]["loss"] for r in early)
    # Allocate under a four-core-hour planning envelope; retain complete
    # trajectories to the fixed counts even if machine time fluctuates.
    counts={"health":48,"weak_early":8,"weak_late":8,"strong_late":10}
    fixed=sum(cpu[g]*n for g,n in counts.items())
    available=int((4*3600-fixed)/cpu["strong_early"])
    counts["strong_early"]=max(12,min(max(sizes),available))
    boot=np.random.default_rng(202611251715)
    centered=[np.array(d)-np.mean(d) for d in differences]
    powers=[]
    from scipy.stats import t
    n=counts["strong_early"]
    for d in centered:
        x=boot.choice(d,(10000,n),replace=True)
        powers.append(float(np.mean(1+x.mean(axis=1)>t.ppf(.975,n-1)*x.std(axis=1,ddof=1)/math.sqrt(n))))
    review=TASK.parent
    paths=list((TASK/"code").glob("*.py"))+list((TASK/"config").glob("*.json"))
    paths += [TASK/"results"/s for s in ("cutoffs.json","audit.json","development_point_calibration.json")]
    paths += list((TASK/"results/development").glob("*.json"))
    paths += [STAGE6/f for f in ("model.json","exact_linear.py","vector_record.py","pilot_v2.py","projection.py")]
    paths += [STAGE7/f for f in ("fresh_protocol.json","fresh_confirmation.py","fixed_amplitude.py","direction_cache_corrected.py")]
    paths += [review/"paper2_stage4_certified_correction_20261122"/"interval_arithmetic.py",
              review/"paper2_stage5_certification_acceleration_20261122"/"strong_concavity.py"]
    head=subprocess.check_output(["git","rev-parse","HEAD"],cwd=TASK,text=True).strip()
    from engine import TIMES
    data=dict(baseline="f0b23fd9499a7cfc2386ce1363a2059ece59a3a4",source_commit=head,
              versions=[sys.version,np.__version__,scipy.__version__],
              platform=platform.platform(),processor="Intel Core Ultra 9 285H",rng="NumPy PCG64/SeedSequence.spawn(3)",
              inputs={p.relative_to(review).as_posix():digest(p) for p in paths},
              seed=202611251701,development_seed=DEV_SEED,calibration_seed=202611251702,
              case_order=list(CASES),cases=CASES,counts=counts,thresholds=thresholds,workers=4,
              stop="one completed result per registered (case,index); retain errors and rerun same ID",
              result_directory="results/confirmation",horizon=[0,607],queries=TIMES,
              attack_window="k through k+511 inclusive",healthy_window=[50,561],
              healthy_endpoint="any nonzero actual binary64 output displacement on 0..607",
              audit=dict(abs_tol=2e-8,rel_tol=2e-10,action_cap="1",useful_actual_gain="1/1600",
                         coverage_budget=".001",node_limit=64,levels=[".025",".05",".1"]),
              max_planned_core_hours=4,dev_cpu_seconds=cpu,
              projected_core_hours=sum(cpu[g]*n for g,n in counts.items())/3600,
              desired_effect=1.,dev_monitor_loss=monitor,effect_percent=100/monitor,
              development_differences=differences,development_sd=sd,required_n=sizes,
              bootstrap_design_power_at_effect_one=powers,
              planning_sensitivity={str(delta):[math.ceil(((1.96+.84)*s/delta)**2) for s in sd]
                                    for delta in (.5,1,2)},
              planning_note="six paired development paths; other cell timings use one path each; first and second comparisons share M3",
              controls="all workers use one numerical thread, one 8-step discarded warm-up; pure interval call caches cleared per trajectory",
              test_order=["positive two-sided 95% paired t lower bound M2-M3 in strong_early",
                          "then positive two-sided 95% paired t lower bound M1-M3 in strong_early"],
              alpha=.05,ci="trajectory t; 10000 percentile bootstrap using whole independent paths, seed 202611251714; other cells descriptive",
              health_equivalence="M1 minus M3 paired any-action rate; difference of two 97.5% two-sided exact binomial intervals strictly within [-.01,.01]",
              secondary="equal weight of four attack cells, no pooling healthy with attacks",
              figure_selection="lowest episode ID in primary cell with a shared successful first certificate; truncate immediately before next scheduled query; all first-certificate curves alongside",
              decisions={"method":"both ordered contrasts positive + healthy equivalence + clean numerical diagnostics",
                         "mechanism":"first contrast positive + mean useful duration extended in primary cell + clean numerical diagnostics",
                         "pending":"otherwise or incomplete or unresolved implementation failure"})
    save(target,data)
    print({k:data[k] for k in ("counts","development_sd","required_n","projected_core_hours","bootstrap_design_power_at_effect_one")})
if __name__=="__main__":
    main()
