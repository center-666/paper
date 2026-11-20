"""Integrity and document checks; does not run a simulation or certify proofs."""
from pathlib import Path
import hashlib
import json
import re
import subprocess

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[1]

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    before=json.loads((HERE/"protected_before.json").read_text(encoding="utf-8"))
    checks=[]
    def ck(name,passed,**details):
        checks.append(dict(name=name,passed=bool(passed),**details))
    changed=[n for n,h in before["files"].items() if not (REPO/n).is_file() or sha(REPO/n)!=h]
    ck("all_preexisting_assets_unchanged",not changed,count=len(before["files"]),changed=changed)
    algebra=json.loads((HERE/"algebra_validation.json").read_text(encoding="utf-8"))
    ck("deterministic_algebra_PASS",algebra["status"]=="PASS",checks=len(algebra["checks"]))
    for p in HERE.glob("*.md"):
        s=p.read_text(encoding="utf-8")
        links=re.findall(r"\]\(([^)]+)\)",s)
        broken=[link for link in links if not link.startswith(("http:","https:","#"))
                and not (p.parent/link).exists() and link!="delivery_validation.json"]
        ck("document/"+p.name,s.count(r"\(")==s.count(r"\)") and
           s.count(r"\[")==s.count(r"\]") and "\ufffd" not in s and not broken,
           broken_links=broken)
    for n in ["01_recursion_and_horizon_bounds.md","02_silence_viability_and_sustained_witness.md"]:
        s=(HERE/n).read_text(encoding="utf-8")
        tags=re.findall(r"\\tag\{(\d+)\}",s)
        ck("equation_numbering/"+n,tags==[str(i) for i in range(1,18)])
        ck("no_unresolved_draft_marker/"+n,r"\ge?" not in s and "TODO" not in s)
    staged=subprocess.check_output(["git","diff","--cached","--name-only","-z"],cwd=REPO,encoding="utf-8").split("\0")
    prefix=HERE.relative_to(REPO).as_posix()+"/"
    wrong=[n for n in staged if n and not n.startswith(prefix)]
    ck("task_only_staging",not wrong,unexpected=wrong)
    result={
        "status":"PASS" if all(c["passed"] for c in checks) else "FAIL",
        "base_commit":before["base_commit"],"checks":checks,
        "scope":"Document integrity and exact-example arithmetic, not formal verification or independent review",
        "mathematical_scope":"Q>0 uniform upper bound; explicit persistent pathwise witness only at A=1,Q>0",
        "novelty":"OPEN","TSIPN_2026_fulltext":"OPEN","simulations_run":False,
        "new_random_samples":0,"formal_manuscript_modified":False,
        "files_sha256":{p.relative_to(HERE).as_posix():sha(p) for p in sorted(HERE.rglob("*"))
            if p.is_file() and p.name!="delivery_validation.json" and "__pycache__" not in p.parts},
    }
    (HERE/"delivery_validation.json").write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",
                                               encoding="utf-8",newline="\n")
    print(json.dumps({"status":result["status"],"checks":len(checks),
                      "failures":[c for c in checks if not c["passed"]]},ensure_ascii=True))
    if result["status"]!="PASS":raise SystemExit(1)

if __name__=="__main__":main()
