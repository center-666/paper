from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import fitz


ROOT = Path(__file__).resolve().parents[3]
ZOTERO = Path(r"C:\Users\zhongxin\Zotero\storage")
OUT = Path(__file__).resolve().parents[1] / "sources"
TARGETS = {
    "zhang2022": "Detecting stealthy integrity attacks in a class of nonlinear cyber",
    "zhang2023": "Passive Attack Detection for a Class of Stealthy Intermittent Integrity Attacks",
    "sun2025": "On attack detection and identification for the cyber",
    "caballero2025": "Distributed estimation for uncertain systems subject to measurement quantization",
    "yang2014": "Stochastic sensor activation for distributed state estimation",
    "yang2019": "Yang 等 - 2019 - Distributed filtering under false data injection attacks",
    "zhou2022": "Security analysis and defense strategy of distributed filtering",
}
LOCAL = {
    "tabatabaei2025": ROOT / "第二篇小论文/第二篇小论文/韧性恢复/references/cross_domain_20261008/partial_identification/Tabatabaei2025_SecureStateOutput.pdf",
    "deghat2019": Path(__file__).resolve().parents[1] / "sources/deghat2019_arxiv.pdf",
}


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    OUT.mkdir(parents=True, exist_ok=True)
    found: dict[str, Path] = {}
    for path in ZOTERO.rglob("*.pdf"):
        for key, needle in TARGETS.items():
            if needle.casefold() in path.name.casefold():
                found[key] = path
    found.update({key: path for key, path in LOCAL.items() if path.exists()})
    manifest = {}
    for key, path in sorted(found.items()):
        doc = fitz.open(path)
        pages = []
        for index, page in enumerate(doc, start=1):
            text = page.get_text("text")
            pages.append(f"\n\n===== PDF PAGE {index} =====\n{text}")
        dest = OUT / f"{key}.txt"
        dest.write_text("".join(pages), encoding="utf-8")
        manifest[key] = {
            "source_path": str(path),
            "pages": len(doc),
            "sha256": digest(path),
            "text_path": str(dest.relative_to(OUT.parent)),
        }
    (OUT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
