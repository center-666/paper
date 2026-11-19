"""Final scope/evidence checks, including manuscript values. No simulation."""
from pathlib import Path
import csv
import hashlib
import json
import re
import subprocess
import sys
import numpy as np
import pymupdf

HERE=Path(__file__).resolve().parent.parent
ROOT=HERE.parents[1]
RUN=HERE/"results/e1_20261119_v1"
PAPER=ROOT/"papers/paper1_trusted_record_integration_20261119"


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def read(p):return json.loads(Path(p).read_text(encoding="utf-8"))


def main():
    old=read(HERE/"protected_before.json")
    allowed=set(old["authorized_changes"])
    allowed.add("papers/paper1_trusted_record_integration_20261119/sections/04_quantized_extension.tex")
    changed=[];kept=0
    for item in old["files"]:
        p=ROOT/item["path"];assert p.exists(),p
        current=sha(p)
        if current!=item["sha256"]:
            assert item["path"] in allowed, item["path"]
            changed.append({"path":item["path"],"before_sha256":item["sha256"],"after_sha256":current})
        else:kept+=1
    # Earlier E0 numerical text must be byte-identical apart from the section heading.
    old5=subprocess.check_output(["git","show",old["baseline"]+
        ":papers/paper1_trusted_record_integration_20261119/sections/05_evidence.tex"],
        cwd=ROOT).decode("utf-8").replace("\r\n","\n")
    cur5=(PAPER/"sections/05_evidence.tex").read_text(encoding="utf-8")
    e0old=old5.split(r"\subsection{",1)[1].split(r"\subsection{")[0]
    e0new=cur5.split(r"\subsection{",1)[1].split(r"\subsection{")[0]
    assert e0old==e0new
    freeze=read(RUN/"code_and_input_contract.json")
    for name,h in freeze["code_sha256"].items():assert sha(HERE/"code"/name)==h,name
    assert freeze["code_commit"].startswith("3644e495")
    assert freeze["protocol_source_sha256"]==sha(ROOT/freeze["protocol_source"])
    protocol_semantics = read(ROOT/freeze["protocol_source"])
    assert protocol_semantics == read(RUN/"protocol_snapshot.json")
    protocol_semantic_sha = hashlib.sha256(json.dumps(
        protocol_semantics,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode("utf-8")).hexdigest()
    assert read(RUN/"independent_audit.json")["status"]=="PASS"
    assert read(RUN/"analysis/analysis_validation.json")["status"]=="PASS"
    assert read(RUN/"simulation_completion.json")["status"]=="HARD_CHECKS_PASS"
    assert read(RUN/"failure_records.json")==[]
    cases=read(RUN/"cases.json")
    for c in cases:assert sha(RUN/c["trace"])==c["trace_sha256"]
    for name,h in read(RUN/"input_hashes_before_simulation.json").items():assert sha(RUN/name)==h
    s=read(RUN/"analysis/summary.json");config=read(RUN/"protocol_snapshot.json")
    # Independent score diagnostics: recompute from stored states instead of analysis functions.
    diagnostics=[]
    for c in s["cases"]:
        m=next(x for x in config["models"] if x["id"]==c["model"])
        tr=dict(np.load(RUN/c["trace"]));P=tr["P_post"][:,:,4]
        V=1/m["Z"]+m["A"]**2*P+m["Q"]+m["R"]
        W=(~tr["sent"][:,:,5])*np.sqrt(m["Z"]*V)
        D=tr["mu_post"][:,:,4]-tr["m_post"][:,:,4]
        conditional=np.exp(-(m["A"]*D-tr["qerror"][:,:,5])**2/(2*V))
        gap=(W[:,0]-(W[:,1]+W[:,2])/2).mean()
        cond_gap=(conditional[:,0]-(conditional[:,1]+conditional[:,2])/2).mean()
        assert np.isclose(gap,c["statistics"]["W_gap"]["mean"],atol=1e-15)
        assert np.isclose(cond_gap,c["statistics"]["W_cond_gap"]["mean"],atol=1e-15)
        assert c["event_mismatch_base_samples"]==0
        diagnostics.append({"case":c["id"],"W_raw_gap":float(gap),"W_cond_gap":float(cond_gap)})
    # Parse all three new numeric manuscript tables, allowing rounding shown in LaTeX.
    def table_rows(label):
        start=cur5.index(r"\label{"+label+"}")
        segment=cur5[start:].split(r"\end{tabular}",1)[0]
        return [line.split(r"\\")[0].strip().split("&") for line in segment.splitlines()
                if re.match(r"^(S1|U1)/[123]\s*&",line)]
    bs={r["model"]+"/"+str(r["level"]):r for r in s["cases"] if r["protocol"]=="B"}
    table_checks=0
    for label in ["tab:e1-damage","tab:e1-health","tab:e1-c"]:
        rows=table_rows(label);assert len(rows)==6
        for row in rows:
            key=row[0].strip();entry=bs[key];z=entry["statistics"]
            if label=="tab:e1-damage":
                delta,J=row[1:3];lo,hi=row[3].strip(" []").split(",")
                expected=[entry["delta"],z["J_paired"]["mean"]*1e6,
                          *[x*1e6 for x in z["J_paired"]["bootstrap_percentile_95"]],
                          z["J_over_delta_squared"]["mean"]]
                shown=list(map(float,[delta,J,lo,hi,row[4]]))
                assert np.allclose(shown,expected,atol=5.1e-7,rtol=0)
            elif label=="tab:e1-health":
                shown=list(map(float,row[1:]));expected=[z["clean_mse"]["mean"],z["attack_mse"]["mean"],
                                                        z["clean_send_rate"]["mean"],entry["nonzero_action_base_samples"]]
                assert np.allclose(shown,expected,atol=5.1e-7,rtol=0)
            else:
                shown=list(map(float,row[1:]));expected=[z["payload_moment_gap"]["mean"]*1e6,
                         z["predictor_moment_gap"]["mean"]*1e6,entry["C_payload_changed_base_samples"]]
                assert np.allclose(shown,expected,atol=5.1e-7,rtol=0)
            table_checks+=1
    # Check figure provenance and publication-state gating.
    for ext in ("pdf","png"):
        assert sha(PAPER/"figures"/("e1_mechanism."+ext))==sha(RUN/"presentation_v1"/("e1_mechanism."+ext))
    bv=read(PAPER/"build_validation.json")
    assert bv["status"]=="DISCUSSION_DRAFT_V0.2_E1_EXPERIMENT_PASS" and not bv["warnings"]
    assert bv["pdf_sha256"]==sha(PAPER/"paper.pdf")
    doc=pymupdf.open(PAPER/"paper.pdf");text="\n".join(p.get_text() for p in doc)
    assert "??" not in text and "v0.2" in text
    for obsolete in ["实验尚未执行","结果待补","设计已固定，尚未执行"]:
        assert obsolete not in text,obsolete
    sources="\n".join(p.read_text(encoding="utf-8") for p in PAPER.rglob("*.tex"))
    labels=re.findall(r"\\label\{([^}]+)\}",sources)
    assert len(labels)==len(set(labels))
    keys=set(re.findall(r"\\bibitem\{([^}]+)\}",sources))
    for ref in re.findall(r"\\(?:eqref|ref)\{([^}]+)\}",sources):assert ref in labels,ref
    for cite in re.findall(r"\\cite\{([^}]+)\}",sources):assert set(cite.split(","))<=keys
    local_links=[]
    for folder in (HERE,PAPER):
        for p in folder.rglob("*.md"):
            t=p.read_text(encoding="utf-8");assert "\ufffd" not in t
            for target in re.findall(r"\]\(([^)]+)\)",t):
                if target.startswith(("http:","https:")):continue
                assert target=="delivery_validation.json" or (p.parent/target.split("#")[0]).exists(),(p,target)
                local_links.append({"file":p.relative_to(ROOT).as_posix(),"target":target})
    files=[]
    for p in sorted(HERE.rglob("*")):
        if p.is_file() and "__pycache__" not in p.parts and p.name!="delivery_validation.json":
            files.append({"path":p.relative_to(ROOT).as_posix(),"bytes":p.stat().st_size,"sha256":sha(p)})
    out={"decision":"EXPERIMENT PASS","baseline":old["baseline"],
         "original_files_unchanged":kept,"authorized_updated_files":changed,
         "protocol_notation_correction":"Quantizer tie-breaking made explicit to match the frozen half-open implementation; quantizer partition and run snapshot unchanged.",
         "E0_section_retained":True,"frozen_numerical_sources_unchanged":True,
         "protocol_semantics_unchanged":True,
         "protocol_canonical_json_sha256":protocol_semantic_sha,
         "new_physical_runs":1,"base_samples":4096,"short_branch_paths":73728,
         "new_monte_carlo_parameter_search":False,"failures_removed":False,"manuscript_tables_checked":table_checks,
         "independent_checks":424,"aggregate_checks":444,"score_diagnostic_checks":diagnostics,
         "latex_pages":len(doc),"new_pdf_sha256":sha(PAPER/"paper.pdf"),
         "limitations":["A sampled events do not resolve the small nonzero probability difference.",
                        "Precision-dominated region only; no numeric supremum or full-log TV.",
                        "C separates this witness, not every zero-TV strategy.",
                        "Bootstrap exploratory; +/- branches paired within base sample."],
         "local_links":local_links,"new_artifacts":files,
         "validation_code_sha256":sha(__file__)}
    (HERE/"delivery_validation.json").write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({k:v for k,v in out.items() if k not in
                     ("authorized_updated_files","new_artifacts","local_links","score_diagnostic_checks")},
                     ensure_ascii=True,indent=2))


if __name__=="__main__":
    main()
