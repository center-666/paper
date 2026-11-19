"""Verify that the clarity revision preserves the scientific content."""
from pathlib import Path
import hashlib
import json
import re

P = Path(__file__).resolve().parent
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
MATH = re.compile(r"\\begin\{(equation\*?|align\*?|gather\*?|multline\*?)\}.*?\\end\{\1\}|\\\[.*?\\\]", re.S)
DECL = re.compile(r"\\begin\{(theorem|lemma|proposition|remark|corollary)\}.*?\\end\{\1\}", re.S)
EDITABLE = {"paper.tex", "introduction.tex", "theory.tex", "main_joint_kernel.tex",
            "record_design.tex", "numerical.tex", "record_condition_numerical.tex", "conclusion.tex"}


def bib(path):
    s = path.read_text(encoding="utf-8").split(r"\end{thebibliography}")[0]
    return {m[1]: re.sub(r"\s+", "", m[2]) for m in
            re.finditer(r"\\bibitem\{([^}]+)\}(.*?)(?=\\bibitem\{|\Z)", s, re.S)}


def main():
    inp = json.loads((P / "clarity_input_manifest.json").read_text(encoding="utf-8"))
    old = Path(inp["previous_directory"])
    baseline = json.loads((P / "clarity_scientific_baseline.json").read_text(encoding="utf-8"))
    previous_verified = 0
    if old.is_dir():
        for name, digest in inp["input_files"].items():
            assert sha(old / name) == digest, name
        previous_verified = len(inp["input_files"])
    total_math = total_decl = 0
    for name, row in baseline["edited_sources"].items():
        text = (P / name).read_text(encoding="utf-8")
        maths = [m[0] for m in MATH.finditer(text)]
        decls = [m[0] for m in DECL.finditer(text)]
        assert maths == row["display_math"], name
        assert decls == row["declarations"], name
        assert re.findall(r"\\label\{([^}]+)\}", text) == row["labels"], name
        total_math += len(maths)
        total_decl += len(decls)
    for name, digest in baseline["unchanged_files"].items():
        assert sha(P / name) == digest, name
    assert bib(P / "references.tex") == baseline["reference_entries"]
    build = json.loads((P / "build_check.json").read_text(encoding="utf-8"))
    assert build["passed"]
    warnings = {}
    for stem, row in build["documents"].items():
        assert sha(P / (stem + ".pdf")) == row["pdf_sha256"]
        log = (P / (stem + ".log")).read_text(encoding="utf-8", errors="replace")
        warnings[stem] = [line for line in log.splitlines()
                          if re.search(r"Overfull|Underfull|LaTeX Warning|Package \S+ Warning|Missing character", line)]
        assert "??" not in (P / (stem + "_extracted.txt")).read_text(encoding="utf-8")
    assert not any(warnings.values()), warnings
    for name, digest in build["source_sha256"].items():
        assert sha(P / name) == digest, name
    result = dict(
        passed=True, date="2026-10-20", stage="academic prose and explanation revision",
        previous_files_verified=previous_verified,
        display_math_preserved=total_math, declarations_preserved=total_decl,
        core_theorem_unchanged=True, experiment_code_data_unchanged=True,
        unchanged_files_verified=len(baseline["unchanged_files"]),
        reference_entries_unchanged=True, references=len(baseline["reference_entries"]),
        new_simulations=False, new_theoretical_results=False, formal_verification=False,
        pages={s: r["pages"] for s, r in build["documents"].items()}, warnings=warnings,
        pdf_sha256={s: r["pdf_sha256"] for s, r in build["documents"].items()},
        source_sha256=build["source_sha256"])
    (P / "clarity_release_audit.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if not k.endswith("sha256")}, indent=2))


if __name__ == "__main__":
    main()
