from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
lit = ROOT / "01_literature_gap.md"
text = lit.read_text(encoding="utf-8")
text = text.replace(chr(8) + "arzeta_i", r"\barzeta_i")
text = text.replace(chr(9) + "ilde y", r"\tilde y")
lit.write_text(text, encoding="utf-8")
for path in sorted(list(ROOT.rglob("*.md")) + list(ROOT.rglob("*.py"))):
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        bad = [(index, ord(char)) for index, char in enumerate(line)
               if ord(char) < 32]
        if bad:
            print(f"{path}:{line_no}: {bad}: {line!r}")
