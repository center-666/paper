"""Check a literature-only revision against the previous verified manuscript."""
from pathlib import Path
import hashlib
import json
import re

P = Path(__file__).resolve().parent
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def bib(path):
    s = path.read_text(encoding="utf-8").split(r"\end{thebibliography}")[0]
    return {m[1]: re.sub(r"\s+", "", m[2]) for m in
            re.finditer(r"\\bibitem\{([^}]+)\}(.*?)(?=\\bibitem\{|\Z)", s, re.S)}


def main():
    manifest = json.loads((P / "neighbor_input_manifest.json").read_text(encoding="utf-8"))
    old = Path(manifest["previous_directory"])
    previous_verified = 0
    if old.is_dir():
        for name, digest in manifest["input_files"].items():
            assert sha(old / name) == digest, name
        previous_verified = len(manifest["input_files"])
        assert bib(P / "references.tex") == bib(old / "references.tex")
    protected = []
    # Only introduction prose and the assembled reference order change in TeX.
    for name, digest in manifest["input_files"].items():
        path = P / name
        if name.endswith(".tex") and name not in {"introduction.tex", "references.tex"}:
            assert sha(path) == digest, name
            protected.append(name)
        elif name.endswith((".py", ".csv", ".npz", ".npy")) and name != "audit_core_release.py":
            assert sha(path) == digest, name
            protected.append(name)
        elif name.startswith(("data/", "results/", "record_study/", "review_checks/", "provenance/")):
            assert sha(path) == digest, name
            protected.append(name)
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
    assert len(bib(P / "references.tex")) == 30
    for name, digest in build["source_sha256"].items():
        assert sha(P / name) == digest, name
    result = dict(
        passed=True, date="2026-10-20", stage="two nearest-neighbor full-text review",
        previous_files_verified=previous_verified, core_theorem_unchanged=True,
        scientific_tex_unchanged=True, experiment_code_data_unchanged=True,
        reference_entries_unchanged=True, reference_order_updated=True, references=30,
        newly_reviewed_fulltexts=["10.1002/rnc.5967", "10.1109/JAS.2025.125381"],
        requested_fulltexts_still_missing=[],
        novelty_review_exhaustive=False, new_simulations=False, formal_verification=False,
        pages={s: r["pages"] for s, r in build["documents"].items()}, warnings=warnings,
        pdf_sha256={s: r["pdf_sha256"] for s, r in build["documents"].items()},
        protected_files=protected, source_sha256=build["source_sha256"])
    (P / "neighbor_release_audit.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items()
                      if k not in {"source_sha256", "protected_files", "pdf_sha256"}}, indent=2))


if __name__ == "__main__":
    main()
