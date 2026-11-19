"""Build the integration discussion draft only. Never run an experiment."""
from pathlib import Path
import hashlib
import json
import re
import shutil
import subprocess

HERE = Path(__file__).resolve().parent


def main():
    executable = shutil.which("xelatex")
    if not executable:
        raise SystemExit("XeLaTeX is required; no build performed.")
    logs = []
    for index in range(2):
        options = ["-disable-installer"] if "miktex" in executable.lower() else []
        run = subprocess.run(
            [executable, *options, "-interaction=nonstopmode", "-halt-on-error",
             "-file-line-error", "paper.tex"],
            cwd=HERE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            timeout=120)
        logs.append(run.stdout.decode("utf-8", errors="replace"))
        if run.returncode:
            print(logs[-1][-6000:])
            raise SystemExit(run.returncode)
    log = (HERE/"paper.log").read_text(encoding="utf-8",errors="replace")
    markers = ["undefined references","undefined on input","multiply defined",
               "Overfull \\hbox","Overfull \\vbox","Missing character",
               "There were undefined citations"]
    warnings = [key for key in markers if key in log]
    match = re.search(r"Output written on .*?\((\d+) pages?",log)
    result = {
        "status":"DISCUSSION_DRAFT_NEW_EXPERIMENTS_NOT_RUN",
        "engine":executable, "pages":int(match.group(1)) if match else None,
        "warnings":warnings,
        "hyperlinks":"DOIs shown as text; clickable source links in repository reports",
        "pdf_sha256":hashlib.sha256((HERE/"paper.pdf").read_bytes()).hexdigest(),
        "tex_sources":{p.relative_to(HERE).as_posix():
                       hashlib.sha256(p.read_bytes()).hexdigest()
                       for p in sorted(HERE.rglob("*.tex"))},
        "experiments_executed":False,
    }
    (HERE/"build_validation.json").write_text(
        json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({k:v for k,v in result.items() if k!="tex_sources"},
                     ensure_ascii=True,indent=2))
    if warnings:
        raise SystemExit("Inspect typesetting warnings before delivery.")


if __name__=="__main__":
    main()
