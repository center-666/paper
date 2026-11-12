"""Apply reversible bold-italic formatting to the manuscript's vectors and matrices."""
from pathlib import Path
import hashlib
import json
import re

HERE = Path(__file__).resolve().parent
source = (HERE / "paper.tex").read_text(encoding="utf-8")
REGION = re.compile(
    r"\$[^$]*?\$|\\begin\{(equation\*?|align\*?|gather\*?)\}.*?\\end\{\1\}|\\\[.*?\\\]",
    re.S,
)
PROTECT = re.compile(
    r"\\(?:label|ref|eqref|text|operatorname|mathrm|textrm|mathcal|mathbb|begin|end)\{[^{}]*\}"
    r"|\\rm\s*[A-Za-z]+|_\{\\mathsf Kv\}|_\\eta|\\mathsf K"
)
TOKEN = re.compile(r"\\[A-Za-z]+|[A-Za-z]")
INDEX = re.compile(r"(?:[_^](?:\{[^{}]*\}|\\[A-Za-z]+|[A-Za-z0-9*+-])){0,2}")
count = 0


def format_region(match):
    global count
    text = match[0]
    protected = []

    def save(item):
        protected.append(item[0])
        return f"§{len(protected)-1}§"

    text = PROTECT.sub(save, text)

    def format_token(token):
        global count
        symbol = token[0]
        tail = text[token.end():]
        indices = INDEX.match(tail)[0]
        coordinate = "(r)" in indices
        bold = symbol in ["A", "Q", "F", "J", "M", "H", "S", "I", "C", "K"]
        if symbol == "J" and text[:token.start()].endswith(r"\widehat "):
            bold = False
        elif symbol == "D":
            bold = tail.startswith("_c")
        elif symbol in ["x", "c", "d", "e", r"\upsilon", "w"]:
            bold = bool(indices) and not coordinate
        elif symbol == r"\eta":
            bold = tail.startswith("_k")
        elif symbol == "v":
            bold = tail.startswith("_k")
        elif symbol == "Z":
            bold = tail.startswith("_") or text[:token.start()].endswith(r"\bar ")
        elif symbol == "g":
            bold = True
        elif symbol == "p":
            bold = not tail.startswith("_")
        elif symbol == "q":
            bold = not tail.startswith("_")
        elif symbol == "h":
            bold = tail.startswith(r"_\theta")
        elif symbol == r"\sigma":
            bold = tail.startswith("§")  # Protected RMS indices, _eta or _{K v}.
        if bold:
            count += 1
            return r"{\bm{" + symbol + "}}"
        return symbol

    text = TOKEN.sub(format_token, text)
    for index, value in enumerate(protected):
        if value == r"\mathsf K":
            value = r"{\bm{\mathsf K}}"
            count += 1
        text = text.replace(f"§{index}§", value)
    return text


result = REGION.sub(format_region, source)
restored = result.replace(r"{\bm{\mathsf K}}", r"\mathsf K")
restored = re.sub(r"\{\\bm\{(\\[A-Za-z]+|[A-Za-z])\}\}", r"\1", restored)
assert restored == source
(HERE / "paper_typeset.tex").write_text(result, encoding="utf-8")
out = {
    "bold_symbols": count,
    "reversible_without_mathematical_token_changes": True,
    "source_sha256": hashlib.sha256(source.encode()).hexdigest(),
    "typeset_sha256": hashlib.sha256(result.encode()).hexdigest(),
    "scope": "Matrix/vector typography, with scalar coordinate components retained in ordinary math italic.",
}
(HERE / "数学排版核查.json").write_text(json.dumps(out, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
print(json.dumps(out, ensure_ascii=False))
