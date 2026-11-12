"""Prune only generated curated snapshot copies; never touches the source tree."""
from pathlib import Path
from build_snapshot_manifest import ROOT, PAPER1_COPY, PAPER1_ROOT_FILES, PAPER1_DIR_EXTENSIONS


def keep(relative: Path, path: Path) -> bool:
    if relative == Path("snapshot_manifest.json"):
        return True
    if relative.parent == Path("."):
        return path.name in PAPER1_ROOT_FILES
    if "__pycache__" in relative.parts or path.suffix.lower() in {".pyc", ".pyo"}:
        return False
    if relative.parts and relative.parts[0] in PAPER1_DIR_EXTENSIONS:
        return path.suffix.lower() in PAPER1_DIR_EXTENSIONS[relative.parts[0]]
    return False


def main() -> None:
    curated = (ROOT / PAPER1_COPY).resolve()
    project = ROOT.resolve()
    if curated.parent != project / "papers":
        raise RuntimeError(f"Unexpected curated snapshot root: {curated}")
    removed = []
    for path in sorted(curated.rglob("*"), reverse=True):
        if not path.is_file():
            continue
        if not path.resolve().is_relative_to(curated):
            raise RuntimeError(f"Refusing path outside curated snapshot: {path}")
        relative = path.relative_to(curated)
        if not keep(relative, path):
            removed.append(relative.as_posix())
            path.unlink()
    for directory in sorted(curated.rglob("*"), reverse=True):
        if directory.is_dir() and not any(directory.iterdir()):
            directory.rmdir()
    print(f"Removed {len(removed)} non-curated files from the newly-created repository snapshot.")
    for item in removed:
        print(item)


if __name__ == "__main__":
    main()
