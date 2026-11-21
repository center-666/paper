"""Verify the frozen research package and its generated result manifests."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[1]
RUN=HERE/"results/run_v1"


def sha(path:Path)->str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    checks=[]
    def add(name,passed,detail=None):
        checks.append({"name":name,"passed":bool(passed),"detail":detail})

    freeze=json.loads((HERE/"freeze.json").read_text(encoding="utf8"))
    add("protocol_frozen",sha(HERE/"protocol.json")==freeze["protocol_sha256"])
    add("deterministic_tv_frozen",sha(HERE/"deterministic_tv_checks.json")==freeze["deterministic_tv_sha256"])
    for name,digest in freeze["code_sha256"].items():
        add("frozen_code:"+name,sha(HERE/name)==digest)
    preflight=json.loads((HERE/"preflight.json").read_text(encoding="utf8"))
    add("deterministic_preflight_pass",preflight["status"]=="PASS" and all(x["pass"] for x in preflight["checks"]))

    completion=json.loads((RUN/"completion.json").read_text(encoding="utf8"))
    add("experiment_completion",completion["status"]=="PASS" and completion["episode_rows"]==90 and completion["window_rows"]==600)
    protected=json.loads((RUN/"protected_file_check.json").read_text(encoding="utf8"))
    add("protected_worktree_files",protected["pass"] and protected["changed"]==[])
    result_manifest=json.loads((RUN/"result_manifest.json").read_text(encoding="utf8"))
    base_checked=0
    base_ok=True
    for name,digest in result_manifest.items():
        path=RUN/name
        base_checked+=1
        if not path.is_file() or sha(path)!=digest:
            base_ok=False
    add("frozen_run_result_hashes",base_ok,base_checked)

    audit_manifest=json.loads((RUN/"exploratory_audit_manifest.json").read_text(encoding="utf8"))
    audit_ok=(audit_manifest["status"]=="EXPLORATORY_POST_HOC_REPLAY"
              and audit_manifest["frozen_experiment_inputs_reused"]
              and not audit_manifest["new_random_samples_generated"]
              and not audit_manifest["thresholds_modified"]
              and sha(HERE/audit_manifest["script"])==audit_manifest["script_sha256"]
              and sha(RUN/"exploratory_event_binomial.json")==audit_manifest["result_sha256"])
    add("posthoc_replay_manifest",audit_ok)
    for name,digest in audit_manifest["test_input_hashes"].items():
        add("test_input:"+name,sha(RUN/name)==digest)

    tv=json.loads((HERE/"deterministic_tv_checks.json").read_text(encoding="utf8"))
    add("deterministic_tv_positive",len(tv)==18 and all(r["event_bits_tv"]>0 and r["joint_tv_payload_phase_event"]>0 for r in tv))
    delivery={"status":"PASS" if all(x["passed"] for x in checks) else "FAIL",
              "base_commit":freeze["head"],"checks":checks,
              "random_experiment_run":True,"posthoc_replay_new_random_samples":False,
              "manuscript_modified_by_this_task":False}
    (HERE/"delivery_validation.json").write_text(json.dumps(delivery,ensure_ascii=False,indent=2)+"\n",
                                                   encoding="utf8",newline="\n")
    print(json.dumps(delivery,ensure_ascii=False,indent=2))
    if delivery["status"]!="PASS":
        raise SystemExit(1)


if __name__=="__main__":
    main()
