"""Read-only verification or explicit sealing of the P53/P6 review package."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

PACKAGE = Path(__file__).resolve().parents[1]
REPO = PACKAGE.parents[2]
BASE = "320744ea77e3f8637980d083e3365d255ac3bb79"
PREFIX = PACKAGE.relative_to(REPO).as_posix()
OLD = [
    "reviews/ack_budget_v1_theory", "papers/paper2_ack_budget_deadline",
    "simulation/engine.py", "simulation/model.py", "simulation/config.json",
]
HISTORICAL = Path(
    r"C:\Users\zhongxin\shixidoc\mypaper\第二篇小论文\第二篇小论文\韧性恢复\fusion_network_20261104")
SOURCES = [
    ("research_lead_review", Path(
        r"C:\Users\zhongxin\.codex\attachments\37077500-7993-4b5f-ab0b-4b21f2619544\Pasted text.txt")),
    ("calendar_engine_read_only", HISTORICAL/"ack_calendar_validation_20261108"/"engine.py"),
    ("original_fixed_config", HISTORICAL/"ack_paired_feasibility_20261107"/"运行前固定.json"),
    ("historical_local_instructions", HISTORICAL/"AGENTS.md"),
    ("historical_goal_record", HISTORICAL/"研究目标_长期约束.md"),
    ("prior_freeze_review", HISTORICAL/"ack_final_asset_audit_20261109"/"全阶段成果审查与冻结结论.md"),
    ("prior_correlation_boundary", HISTORICAL/"neighbor_correlation_gate_20261106"/"邻居信息相关性_可见评价与Gaussian增益路线收束.md"),
]


def git(*args):
    return subprocess.check_output(["git", "-C", str(REPO), *args])


def sha(data):
    return hashlib.sha256(data).hexdigest()


def write(path, obj):
    path.write_bytes((json.dumps(obj, ensure_ascii=False, indent=2)+"\n").encode())


def protected():
    changes = git("diff", "--name-only", BASE, "--", ".",
                  f":(exclude){PREFIX}/**").decode("utf-8").strip()
    assert not changes, changes
    records = []
    for item in git("ls-tree", "-r", "-z", BASE, "--", *OLD).split(b"\0"):
        if not item:
            continue
        meta, name = item.split(b"\t", 1)
        oid = meta.decode().split()[2]
        path = name.decode("utf-8")
        original = git("cat-file", "blob", oid)
        current = (REPO/path).read_bytes()
        assert current == original, path
        records.append(dict(path=path, git_blob=oid, bytes=len(current),
                            sha256=sha(current)))
    return dict(baseline=BASE, count=len(records), files=records,
                all_tracked_files_outside_package_unchanged=True)


def sources():
    for source_label, archived_name in [
        ("research_lead_review", "research_lead_review.txt"),
        ("prior_correlation_boundary", "prior_correlation_boundary.md"),
    ]:
        original = next(path for label, path in SOURCES if label == source_label)
        assert original.read_bytes() == (PACKAGE/"data"/archived_name).read_bytes()
    return dict(files=[dict(label=label, path=str(path),
                           bytes=path.stat().st_size, sha256=sha(path.read_bytes()))
                       for label, path in SOURCES])


def files():
    return {p.relative_to(PACKAGE).as_posix():
            dict(bytes=p.stat().st_size, sha256=sha(p.read_bytes()))
            for p in sorted(PACKAGE.rglob("*"))
            if p.is_file() and p.name != "integrity_manifest.json"}


def links():
    # Historical evidence copies retain their original relative links.
    checked = 0
    for p in PACKAGE.glob("*.md"):
        raw = p.read_text(encoding="utf-8")
        assert "\ufffd" not in raw, p
        for target in re.findall(r"\]\(([^)]+)\)", raw):
            if target.startswith("http"):
                continue
            assert (p.parent/target.split("#")[0]).exists(), (p.name, target)
            checked += 1
    return checked


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seal", action="store_true")
    parser.add_argument("--local-sources", action="store_true",
                        help="Also hash original external files; optional on another machine")
    args = parser.parse_args()
    frozen = protected()
    count = links()
    manifest = PACKAGE/"integrity_manifest.json"
    if args.seal:
        write(PACKAGE/"data"/"source_manifest.json", sources())
        write(PACKAGE/"data"/"protected_assets.json", frozen)
        write(manifest, dict(baseline=BASE, algorithm="SHA256",
                             excludes=["integrity_manifest.json"], files=files()))
    else:
        assert json.loads((PACKAGE/"data"/"protected_assets.json").read_text(encoding="utf-8")) == frozen
        assert json.loads(manifest.read_text(encoding="utf-8"))["files"] == files()
    if args.local_sources:
        assert json.loads((PACKAGE/"data"/"source_manifest.json").read_text(encoding="utf-8")) == sources()
    print(json.dumps(dict(status="PASS", frozen_files=frozen["count"],
                          package_files=len(files()), report_links=count,
                          original_local_sources_checked=args.seal or args.local_sources)))


if __name__ == "__main__":
    main()
