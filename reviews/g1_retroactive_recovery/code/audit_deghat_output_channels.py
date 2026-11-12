from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

import numpy as np
from scipy import stats

ROOT = Path(__file__).resolve().parents[3]
BRANCH = Path(__file__).resolve().parents[1]
RUN = BRANCH / "results" / "g1r_deghat_output_channels_20261112_02"


def load_csv(path):
    with path.open(newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def ci(x):
    a=np.asarray(x,float)
    half=stats.t.ppf(.975,len(a)-1)*a.std(ddof=1)/np.sqrt(len(a))
    return {"n":len(a),"mean":float(a.mean()),"ci95":[float(a.mean()-half),float(a.mean()+half)]}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    rows=load_csv(RUN/"per_seed.csv")
    lookup={(r["scenario"],r["window"],int(r["seed"])):r for r in rows}
    comps=[]
    for scenario in ("single_step","replay_packet"):
        for window in ("full_prefix","post_cache"):
            local=f"{window}_local"
            aug=f"{window}_augmented"
            seeds=sorted(s for sc,w,s in lookup if sc==scenario and w==local)
            for field in ("receiver_excess_after","network_excess_after"):
                diffs=[float(lookup[scenario,aug,s][field])-float(lookup[scenario,local,s][field]) for s in seeds]
                comps.append({"scenario":scenario,"window":window,"augmented_minus_local":field,
                              "paired_difference":ci(diffs),"positive_favors_local_only":True})
    normal=load_csv(RUN/"normal_audit.csv")
    fpr={name:float(np.mean([r["false_correction"]=="True" for r in normal if r["window"]==name]))
         for name in sorted({r["window"] for r in normal})}
    summary={"run_id":RUN.name,"paired_output_channel_comparisons":comps,
             "normal_false_correction_rates":fpr,
             "source_hashes":{p.name:sha(p) for p in [
                 BRANCH/"code/compare_deghat_outputs.py",
                 BRANCH/"code/minimal_recovery_screen.py",
                 ROOT/"simulation/engine.py",ROOT/"simulation/model.py",
                 RUN/"config.json"]},
             "claim_scope":"descriptive paired seed analysis; same oracle event localization and fixed schedule"}
    (RUN/"audit_summary.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(summary,ensure_ascii=False,indent=2))


if __name__=="__main__":
    main()
