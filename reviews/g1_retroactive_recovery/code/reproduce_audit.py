"""Rerun frozen science with a new destination; never create private G2 files.

P1's original script has a fixed output path. The sole AST rewrite replaces that
assignment. The rewrite and original source hash are recorded in the new Run.
"""
from pathlib import Path
import argparse
import ast
import sys
import p0_verified as p0


def p1_entry(out):
    import p1_structural_check as p1
    source = Path(p1.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    main = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "main")
    assignments = [n for n in main.body if isinstance(n, ast.Assign)
                   and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name)
                   and n.targets[0].id == "out"]
    assert len(assignments) == 1, "Refuse an unrecognized output-path rewrite"
    assignments[0].value = ast.Name(id="_reproduction_out", ctx=ast.Load())
    ast.fix_missing_locations(tree)
    ns = dict(vars(p1), _reproduction_out=out)
    exec(compile(tree, str(p1.__file__), "exec"), ns)
    return ns["main"], {"original_source_sha256": p0.digest(p1.__file__),
                        "AST_change": "only main: out assignment replaced by requested Path"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase", choices=("p0", "p1"), required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--check-only", action="store_true", help="check entry wiring without simulation")
    args = parser.parse_args()
    out = args.out.resolve()
    if not out.is_relative_to(p0.BRANCH / "results"):
        parser.error("New Run must stay inside G1-R/results")
    if out.exists():
        parser.error("New Run path already exists; it will not be overwritten")
    original = p0.PROTECTED
    p0.PROTECTED = tuple(p for p in original if (p0.ROOT / p).exists())
    metadata = {"phase": args.phase, "entry_source_sha256": p0.digest(__file__),
                "missing_G2_paths_not_created": sorted(set(original) - set(p0.PROTECTED)),
                "scenarios_seeds_and_equations_changed": False}
    if args.phase == "p0":
        entry = lambda: p0.main(out)
    else:
        entry, mapping = p1_entry(out)
        metadata.update(mapping)
    if args.check_only:
        print("Entry checked; no simulation or output directory created.")
        return
    try:
        entry()
    finally:
        if out.is_dir():
            p0.json_out(out / "reproduction_entry.json", metadata)


if __name__ == "__main__":
    main()
