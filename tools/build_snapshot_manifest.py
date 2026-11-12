"""Verify curated manuscript snapshots against the preserved source trees."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAPER1_SOURCE = Path("第二篇小论文/第二篇小论文/韧性恢复/latex_ecust_20261102")
PAPER1_COPY = Path("papers/latex_ecust_20261102")
ACK_ROOT = Path("第二篇小论文/第二篇小论文/韧性恢复/fusion_network_20261104")
ACK_COPY = Path("papers/paper2_ack_budget_deadline")
PAPER1_EXCLUDED_DIRS = {"fulltext_review"}
PAPER1_EXCLUDED_FILES = {
    "build.ps1", "package_manifest.json", "verify_package.py",
    "submission_review/library_registration.json"
}
PAPER1_BUILD_FILES = {"README.md", "build.py", "build.ps1"}
GENERATED_SUFFIXES = {".aux", ".log", ".spl", ".synctex.gz"}
PAPER1_ROOT_FILES = {
    "abstract_cn.tex", "abstract_en.tex", "assemble_references.py", "build.py",
    "build.ps1", "conclusion.tex", "damage_figure.tex", "damage_table_float.tex",
    "ecust-layout.tex", "ecust_release_audit.json", "ecust_visual_review.json",
    "english_abstract.tex", "experiments.py", "finite_sample.tex", "graphical.pdf",
    "graphical.tex", "graphical_abstract.tex", "introduction.tex", "label_refinement.tex",
    "main_joint_kernel.tex", "math_typography_check.json", "metadata.tex", "numerical.tex",
    "paper-style.tex", "paper.pdf", "paper.tex", "paper_submission.pdf",
    "paper_submission.tex", "physical_check.py", "plot_review.py", "prepare_ecust_math.py",
    "protocol-figure.tex", "README.md", "record_condition_appendix.tex",
    "record_condition_figure.tex", "record_condition_numerical.tex", "record_design.tex",
    "record_reproduction_check.json", "record_requirements.txt", "references.tex",
    "references_additions.tex", "references_base.tex", "scalar_counterexample.tex",
    "statistical_extension.tex", "statistical_numerical.tex", "supplement.pdf",
    "supplement.tex", "theory.tex", "validation_appendix.tex", "vector_core.py",
    "vector_proof.tex"
}
PAPER1_DIR_EXTENSIONS = {
    "ecust_typeset": {".tex"},
    "figures": {".tex", ".pdf"},
    "final_review": {".md"},
    "record_study": {".py", ".csv", ".json", ".md"},
    "vector_data": {".csv", ".json", ".tex"}
}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    records = []
    for copied in sorted((ROOT / PAPER1_COPY).rglob("*")):
        if not copied.is_file():
            continue
        relative = copied.relative_to(ROOT / PAPER1_COPY)
        relative_posix = relative.as_posix()
        if "__pycache__" in relative.parts or copied.suffix.lower() in {".pyc", ".pyo"}:
            continue
        if relative.parent == Path("."):
            if copied.name not in PAPER1_ROOT_FILES:
                continue
        elif relative.parts[0] in PAPER1_DIR_EXTENSIONS:
            if copied.suffix.lower() not in PAPER1_DIR_EXTENSIONS[relative.parts[0]]:
                continue
        else:
            continue
        if relative_posix in PAPER1_EXCLUDED_FILES:
            continue
        if any(part in PAPER1_EXCLUDED_DIRS for part in relative.parts):
            continue
        if copied.name == "README.md" and relative.parent.as_posix().startswith("previous_"):
            continue
        if copied.suffix.lower() in GENERATED_SUFFIXES or copied.name.endswith(("_build.txt", "_extracted.txt")):
            continue
        source = ROOT / PAPER1_SOURCE / relative
        assert source.is_file(), f"No original source for snapshot file: {relative}"
        source_hash, copy_hash = digest(source), digest(copied)
        curated = relative_posix in PAPER1_BUILD_FILES
        if not curated:
            assert source_hash == copy_hash, f"Snapshot differs from original: {relative}"
        records.append({"paper": "paper1_stochastic_trigger_damage",
                        "repo_path": copied.relative_to(ROOT).as_posix(),
                        "source_path": (PAPER1_SOURCE / relative).as_posix(),
                        "bytes": copied.stat().st_size,
                        "source_sha256": source_hash,
                        "snapshot_sha256": copy_hash,
                        "curated_for_repository": curated,
                        "curation_note": ("Repository-specific setup/status documentation" if relative_posix == "README.md"
                                           else "Portable TeX executable lookup; original frozen source is unchanged locally"
                                           if relative_posix in {"build.py", "build.ps1"} else None)})

    ack_manifest = {
        "manuscript": ACK_ROOT / "ack_major_revision_20261109",
        "research/全阶段成果审查与冻结结论.md": ACK_ROOT / "ack_final_asset_audit_20261109/全阶段成果审查与冻结结论.md",
        "research/定理级文献对照.md": ACK_ROOT / "ack_final_asset_audit_20261109/定理级文献对照.md",
        "research/核心定理链_终核与引用版本.md": ACK_ROOT / "ack_final_asset_audit_20261109/核心定理链_终核与引用版本.md",
        "research/大修审阅与匹配误差检验_结果及路线判断.md": ACK_ROOT / "ack_accuracy_matched_20261109/大修审阅与匹配误差检验_结果及路线判断.md",
        "research/近邻补核与贡献边界.md": ACK_ROOT / "ack_accuracy_matched_20261109/近邻补核与贡献边界.md"
    }
    for copied in sorted((ROOT / ACK_COPY).rglob("*")):
        relative_candidate = copied.relative_to(ROOT / ACK_COPY)
        if (not copied.is_file() or copied.name == "README.md"
                or relative_path_is_research(copied, ROOT / ACK_COPY)
                or "__pycache__" in relative_candidate.parts
                or copied.suffix.lower() in {".pyc", ".pyo"}):
            continue
        relative = copied.relative_to(ROOT / ACK_COPY).as_posix()
        if relative.startswith("manuscript/"):
            source = ack_manifest["manuscript"] / Path(relative).relative_to("manuscript")
        else:
            assert relative in ack_manifest, f"Unregistered ACK snapshot file: {relative}"
            source = ack_manifest[relative]
        source = ROOT / source
        assert source.is_file(), f"No original source for ACK file: {relative}"
        source_hash, copy_hash = digest(source), digest(copied)
        assert source_hash == copy_hash, f"ACK snapshot differs from original: {relative}"
        records.append({"paper": "paper2_ack_budget_deadline",
                        "repo_path": copied.relative_to(ROOT).as_posix(),
                        "source_path": source.relative_to(ROOT).as_posix(),
                        "bytes": copied.stat().st_size,
                        "source_sha256": source_hash,
                        "snapshot_sha256": copy_hash})

    curated_research = ROOT / ACK_COPY / "research/RESEARCH_SUMMARY.md"
    if curated_research.is_file():
        source_paths = [
            ACK_ROOT / "ack_final_asset_audit_20261109/全阶段成果审查与冻结结论.md",
            ACK_ROOT / "ack_final_asset_audit_20261109/核心定理链_终核与引用版本.md",
            ACK_ROOT / "ack_accuracy_matched_20261109/大修审阅与匹配误差检验_结果及路线判断.md"
        ]
        records.append({"paper": "paper2_ack_budget_deadline",
                        "repo_path": curated_research.relative_to(ROOT).as_posix(),
                        "source_material": [
                            {"path": path.as_posix(), "sha256": digest(ROOT / path)}
                            for path in source_paths
                        ],
                        "bytes": curated_research.stat().st_size,
                        "snapshot_sha256": digest(curated_research),
                        "curated_for_repository": True,
                        "curation_note": "Condensed public summary derived from frozen audit, theorem-chain and matched-baseline reports"})

    manifest = {"generated_by": "tools/build_snapshot_manifest.py",
                "generated_from_local_frozen_sources": True,
                "third_party_fulltexts_copied": False,
                "files": records}
    target = ROOT / "papers/snapshot_manifest.json"
    target.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"files_verified": len(records),
                      "bytes": sum(row["bytes"] for row in records),
                      "manifest": target.relative_to(ROOT).as_posix()}, ensure_ascii=False))


def relative_path_is_research(path: Path, ack_copy: Path) -> bool:
    return "research" in path.relative_to(ack_copy).parts


if __name__ == "__main__":
    main()
