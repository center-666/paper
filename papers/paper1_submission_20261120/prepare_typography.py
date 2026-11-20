"""Generate reversible bold-italic notation for vector/matrix sections only.

The scalar extension and scalar experiment keep scalar symbols. Measure kernels,
record variables, scalar certificate constants, and probability weights are
excluded from matrix formatting. Removing each inserted wrapper recovers the
source byte-for-byte (after UTF-8 decoding).
"""
from pathlib import Path
import hashlib
import json
import re

HERE = Path(__file__).resolve().parent
REGION = re.compile(
    r"\$[^$]*?\$|\\begin\{(equation\*?|align\*?|gather\*?|multline\*?)\}.*?\\end\{\1\}|\\\[.*?\\\]",
    re.S,
)
PROTECT = re.compile(
    r"\\(?:label|ref|eqref|text|operatorname|mathrm|textrm|mathcal|mathbb|begin|end)\{[^{}]*\}"
    r"|\\rm\s*[A-Za-z]+|\\(?:mathrm|mathcal|mathbb|textrm)\s+[A-Za-z]"
    r"|(?<![A-Za-z])d(?=[uzr](?![A-Za-z])|\\xi)"
)
TOKEN = re.compile(r"\\[A-Za-z]+|[A-Za-z]")


def main():
    output = HERE / "typeset"
    output.mkdir(exist_ok=True)
    summaries = {}
    for name in ["02_model", "03_exact_feedback", "05_evidence", "appendix_proofs"]:
        source = (HERE / "sections" / (name + ".tex")).read_text(encoding="utf-8")
        # Only exact-feedback sections have vector states. The later extension
        # and experiments are scalar. Display E0 matrices are handled below.
        vector_end = len(source)
        if name == "appendix_proofs":
            vector_end = source.index(r"\section{量化协议")
        count = 0

        def region(match):
            nonlocal count
            content = match[0]
            if match.start() >= vector_end:
                return content
            if name == "05_evidence" and not content.startswith(r"\["):
                return content
            if name == "05_evidence" and r"\begin{bmatrix}" not in content:
                return content
            saved = []

            def protect(m):
                saved.append(m[0])
                return f"§{len(saved)-1}§"

            content = PROTECT.sub(protect, content)

            def token(m):
                nonlocal count
                symbol = m[0]
                tail = content[m.end():]
                before = content[:m.start()]
                bold = symbol in ["A", "P", "Z", "I", "K", "D", r"\Sigma"]
                if symbol == "Q":
                    bold = not (name == "appendix_proofs" and tail.startswith("_"))
                if symbol == "R":
                    bold = (
                        name in ["02_model", "03_exact_feedback", "05_evidence"]
                        and not before.endswith("_")
                        and not re.match(r"_\s*(?:m|\{?§)", tail)
                        and (name != "02_model" or match.start() < source.index(r"\subsection{信息域"))
                        and (name != "03_exact_feedback" or r"\Sigma" in match[0])
                    ) or (name == "appendix_proofs" and not before.endswith("_"))
                if symbol == "H":
                    bold = tail.startswith("(P)")
                if symbol == "W":
                    bold = name == "appendix_proofs" and tail.startswith("_h")
                if symbol in ["x", "y", "m", "d", "a"]:
                    bold = bool(re.match(r"_(?:[tk0]|\{[tk0])", tail))
                if symbol == "z" and name == "02_model":
                    bold = True
                if symbol in ["v", "w"]:
                    bold = bool(re.match(r"_(?:[tk]|\{[tk])", tail))
                    if symbol == "v" and name in ["03_exact_feedback", "appendix_proofs"]:
                        bold = True
                if symbol == r"\mu":
                    bold = tail.startswith("_")
                if name == "appendix_proofs":
                    if symbol in ["S", "T"]:
                        bold = bool(re.match(r"'?_h", tail))
                    if symbol == "c":
                        bold = tail.startswith("_h")
                    if symbol in ["u", "z", "r", "e", r"\xi"]:
                        # Scalar r_t and Euler e are not vector innovations.
                        bold = match.start() > source.index(r"\subsection{单拍") and (symbol in ["u", "z", r"\xi"] or (
                            symbol in ["r", "e"] and not tail.startswith("^")
                        ))
                    if symbol == "m" and tail.startswith("+"):
                        bold = True
                if bold:
                    count += 1
                    return r"{\bm{" + symbol + "}}"
                return symbol

            content = TOKEN.sub(token, content)
            for i, v in enumerate(saved):
                content = content.replace(f"§{i}§", v)
            return content

        result = REGION.sub(region, source)
        restored = re.sub(r"\{\\bm\{(\\[A-Za-z]+|[A-Za-z])\}\}", r"\1", result)
        assert restored == source, f"Non-typographic change in {name}"
        (output / (name + ".tex")).write_text(result, encoding="utf-8", newline="\n")
        summaries[name] = {
            "bold_symbol_count": count,
            "reversible": True,
            "source_sha256": hashlib.sha256(source.encode("utf-8")).hexdigest(),
        }
    (HERE / "typography_validation.json").write_text(
        json.dumps(summaries, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    return summaries


if __name__ == "__main__":
    print(json.dumps(main(), ensure_ascii=True, indent=2))
