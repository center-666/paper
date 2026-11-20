"""Validate report artifacts and frozen assets; no simulation or numerical experiment."""
from pathlib import Path
import hashlib
import json
import re
import subprocess

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    before = json.loads((HERE / "protected_before.json").read_text(encoding="utf-8"))
    changed = [
        name for name, digest in before["files"].items()
        if not (REPO / name).is_file() or sha256(REPO / name) != digest
    ]
    checks = []
    for path in sorted(HERE.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        links = re.findall(r"\]\(([^)]+)\)", text)
        broken = [
            link for link in links if not link.startswith(("http:", "https:", "#"))
            and not (path.parent / link.split("#", 1)[0]).exists()
        ]
        # delivery_validation.json is produced by this invocation.
        broken = [link for link in broken if link != "delivery_validation.json"]
        checks.append({
            "file": path.name,
            "inline_math_balanced": text.count(r"\(") == text.count(r"\)"),
            "display_math_balanced": text.count(r"\[") == text.count(r"\]"),
            "replacement_character_absent": "\ufffd" not in text,
            "broken_relative_links": broken,
        })
    main_report = (HERE / "01_pair_theorem_assessment.md").read_text(encoding="utf-8")
    tags = re.findall(r"\\tag\{(\d+)\}", main_report)
    tags_ok = tags == [str(i) for i in range(1, 24)]
    stage = subprocess.check_output(
        ["git", "diff", "--cached", "--name-only", "-z"], cwd=REPO, encoding="utf-8"
    ).split("\0")
    task_prefix = HERE.relative_to(REPO).as_posix() + "/"
    unexpected_staged = [name for name in stage if name and not name.startswith(task_prefix)]
    doc_ok = all(
        check["inline_math_balanced"] and check["display_math_balanced"]
        and check["replacement_character_absent"] and not check["broken_relative_links"]
        for check in checks
    )
    # This is traceability and structural QA, not machine verification of theorems.
    result = {
        "status": "PASS" if not changed and doc_ok and tags_ok and not unexpected_staged else "FAIL",
        "base_commit": before["base_commit"],
        "scope": "Frozen asset integrity, document syntax, relative links and task-scoped staging only",
        "protected_files_checked": len(before["files"]),
        "protected_files_changed": changed,
        "document_checks": checks,
        "main_equation_tags_1_to_23_unique_and_ordered": tags_ok,
        "unexpected_staged_files": unexpected_staged,
        "independent_mathematical_reviews": ["agent_a_audit.md", "agent_b_audit.md"],
        "merged_report_review": "Root review plus D-agent readback in agent_b_pair_readback.md; missing kernel plus sign and physical-measurement wording corrected; no second C-agent review claimed",
        "novelty_verdict": "OPEN",
        "simulations_run": False,
        "random_samples_generated": False,
        "bootstrap_run": False,
        "manuscript_modified_by_this_task": False,
        "artifact_sha256": {
            path.relative_to(HERE).as_posix(): sha256(path)
            for path in sorted(HERE.rglob("*"))
            if path.is_file() and path.name != "delivery_validation.json"
            and "__pycache__" not in path.parts
        },
    }
    (HERE / "delivery_validation.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8", newline="\n"
    )
    print(json.dumps({
        "status": result["status"],
        "protected_files_checked": result["protected_files_checked"],
        "protected_changes": changed,
        "equation_tags": tags_ok,
        "unexpected_staged": unexpected_staged,
        "document_failures": [c for c in checks if not (
            c["inline_math_balanced"] and c["display_math_balanced"]
            and c["replacement_character_absent"] and not c["broken_relative_links"]
        )],
    }, ensure_ascii=True))
    if result["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
