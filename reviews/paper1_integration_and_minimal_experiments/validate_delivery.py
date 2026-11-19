"""Check new integration artifacts and byte hashes; never run simulations."""
from pathlib import Path
import hashlib
import json
import re
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PAPER = ROOT/"papers/paper1_trusted_record_integration_20261119"


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    protected = json.loads((HERE/"protected_before.json").read_text(encoding="utf-8"))
    for entry in protected["files"]:
        assert sha(ROOT/entry["path"]) == entry["sha256"], entry["path"]
    existing_changes = subprocess.check_output(
        ["git","diff",protected["baseline"],"--name-only","--diff-filter=MDRT"],
        cwd=ROOT).decode("utf-8")
    assert not existing_changes, existing_changes
    protocol = json.loads((HERE/"experiment_protocol.json").read_text(encoding="utf-8"))
    assert protocol["status"] == "DESIGN_ONLY_NOT_RUN"
    assert protocol["new_simulation_results_exist"] is False
    assert protocol["branch_runs_max"] == 73728
    assert protocol["independent_base_paths"] == 4096
    for model in protocol["models"]:
        c = model["design_constants"]
        assert all(0 < d <= c["delta_star"] for d in c["delta_grid"])
        assert all(0 < a <= protocol["b"] for a in c["eta_grid"])
    evidence = json.loads((HERE/"saved_evidence.json").read_text(encoding="utf-8"))
    for entry in evidence["summary"]:
        assert sha(ROOT/entry["source"]) == entry["source_sha256"]
    alltex = "\n".join(p.read_text(encoding="utf-8") for p in PAPER.rglob("*.tex"))
    labels = re.findall(r"\\label\{([^}]+)\}", alltex)
    assert len(labels) == len(set(labels))
    bibkeys = set(re.findall(r"\\bibitem\{([^}]+)\}", alltex))
    for citation in re.findall(r"\\cite\{([^}]+)\}", alltex):
        assert set(citation.split(",")) <= bibkeys, citation
    for ref in re.findall(r"\\(?:eqref|ref)\{([^}]+)\}", alltex):
        assert ref in labels, ref
    links = []
    for folder in (HERE, PAPER):
        for p in folder.rglob("*.md"):
            text = p.read_text(encoding="utf-8")
            assert "\ufffd" not in text
            for target in re.findall(r"\]\(([^)]+)\)",text):
                if target.startswith(("https://","http://")):
                    continue
                path = p.parent/target.split("#")[0]
                assert path.name=="delivery_validation.json" or path.exists(), (p,target)
                links.append({"file":p.relative_to(ROOT).as_posix(),"target":target})
    build = json.loads((PAPER/"build_validation.json").read_text(encoding="utf-8"))
    assert build["pdf_sha256"] == sha(PAPER/"paper.pdf")
    assert not build["warnings"], build["warnings"]
    import pymupdf
    doc = pymupdf.open(PAPER/"paper.pdf")
    pdftext = "\n".join(page.get_text() for page in doc)
    assert "??" not in pdftext
    assert "尚未执行" in pdftext
    # Runtime code is compile/design-only; source inspection is not a proof check.
    result = {
        "baseline":protected["baseline"], "protected_files_verified":len(protected["files"]),
        "protected_unchanged":True, "old_files_modified":False,
        "latex_pages":len(doc), "local_links":links,
        "new_simulations":0, "old_experiments_rerun":False,
        "checks":["byte SHA256 of protected files","only added paths in Git",
                  "design and count consistency","reused source hashes",
                  "citations, labels, local links","successful PDF typesetting"],
        "limits":"This is structural and artifact validation, not new theorem certification or new experiment validation.",
        "files":[{"path":p.relative_to(ROOT).as_posix(),"sha256":sha(p),"bytes":p.stat().st_size}
                 for folder in (HERE,PAPER) for p in sorted(folder.rglob("*"))
                 if p.is_file() and p.suffix not in {".aux",".log",".out"}
                 and p.name!="delivery_validation.json"],
    }
    (HERE/"delivery_validation.json").write_text(
        json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({k:v for k,v in result.items() if k not in {"files","local_links"}},
                     ensure_ascii=True,indent=2))


if __name__=="__main__":
    main()
