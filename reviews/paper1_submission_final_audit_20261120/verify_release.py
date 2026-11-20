"""Read-only checks and release manifests; never build or simulate."""
from pathlib import Path
import ast
import hashlib
import json
import re

import pymupdf as fitz
from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PAPER = ROOT / "papers/paper1_submission_20261120"


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    before = json.loads((HERE / "protected_before.json").read_text(encoding="utf-8"))
    changes = [rel for rel, digest in before["files"].items()
               if not (ROOT / rel).is_file() or sha(ROOT / rel) != digest]
    assert not changes, changes
    build = json.loads((PAPER / "build_validation.json").read_text(encoding="utf-8"))
    assert build["status"] == "PASS" and not build["warnings"]
    assert sha(PAPER / "paper.pdf") == build["pdf_sha256"]
    for rel, digest in build["tex_sources"].items():
        assert sha(PAPER / rel) == digest, rel

    # Check the actual recursively included TeX, not unused historic sources.
    def expand(path):
        content = path.read_text(encoding="utf-8")
        return re.sub(r"\\input\{([^}]+)\}",
                      lambda m: expand(PAPER / (m[1] + ".tex")), content)

    tex = expand(PAPER / "paper.tex")
    assert "??" not in tex and "\ufffd" not in tex
    labels = re.findall(r"\\label\{([^}]+)\}", tex)
    assert len(labels) == len(set(labels))
    refs = re.findall(r"\\(?:ref|eqref)\{([^}]+)\}", tex)
    assert set(refs) <= set(labels), set(refs) - set(labels)
    cites = []
    for m in re.finditer(r"\\cite\{([^}]+)\}", tex):
        for key in m[1].split(","):
            if key not in cites:
                cites.append(key)
    bibliography = re.findall(r"\\bibitem\{([^}]+)\}", tex)
    assert cites == bibliography, (cites, bibliography)
    assert len(bibliography) == 13
    assert len(re.findall(r"\\begin\{theorem\}", tex)) == 2
    assert len(re.findall(r"\\begin\{proposition\}", tex)) == 1
    assert "L_{\\rm cert}" not in tex and "Cayley" not in tex
    assert tex.count(r"\begin{table}") + tex.count(r"\begin{figure}") == tex.count(r"\bicaption{")

    # Reversibility of vector/matrix font wrappers.
    typography = json.loads((PAPER / "typography_validation.json").read_text(encoding="utf-8"))
    for name, info in typography.items():
        source = (PAPER / "sections" / (name + ".tex")).read_text(encoding="utf-8")
        formatted = (PAPER / "typeset" / (name + ".tex")).read_text(encoding="utf-8")
        restored = re.sub(r"\{\\bm\{(\\[A-Za-z]+|[A-Za-z])\}\}", r"\1", formatted)
        assert restored == source and info["source_sha256"] == hashlib.sha256(source.encode()).hexdigest()

    for path in PAPER.glob("*.py"):
        ast.parse(path.read_text(encoding="utf-8"))
    # The plot renderer differs only in its destination, title wording and manifest.
    old_renderer = (ROOT / "reviews/paper1_e1_scalar_execution/code/present_e1.py").read_text(encoding="utf-8")
    new_renderer = (PAPER / "render_evidence.py").read_text(encoding="utf-8")
    old_curves = old_renderer.split("rows=json.loads")[1].split("fig.suptitle")[0]
    new_curves = new_renderer.split("rows=json.loads")[1].split("fig.suptitle")[0]
    assert old_curves == new_curves
    figure_manifest = json.loads((PAPER / "figures/manifest.json").read_text(encoding="utf-8"))
    frozen_summary = ROOT / "reviews/paper1_e1_scalar_execution/results/e1_20261119_v1/analysis/summary.json"
    assert figure_manifest["input_summary_sha256"] == sha(frozen_summary)

    cn_src = (PAPER / "paper.tex").read_text(encoding="utf-8")
    cn = cn_src.split(r"\noindent\textbf{摘\quad 要：}")[1].split(r"\smallskip")[0]
    en = (PAPER / "english_abstract.tex").read_text(encoding="utf-8").split("Abstract:}")[1].split(r"\smallskip")[0]
    cn_chars = len(re.findall(r"[\u4e00-\u9fff]", cn))
    en_words = len(en.split())
    assert 190 <= cn_chars <= 270 and 250 <= en_words <= 300, (cn_chars, en_words)
    graphical_words = len((PAPER / "graphical_abstract.tex").read_text(encoding="utf-8").split(r"\noindent")[1].split())
    assert graphical_words < 50

    doc = fitz.open(PAPER / "paper.pdf")
    previews = HERE / "rendered"
    previews.mkdir(exist_ok=True)
    pages = []
    thumbs = []
    fulltext = ""
    for i, page in enumerate(doc):
        text = page.get_text()
        fulltext += text + "\n"
        outside = [list(b[:4]) for b in page.get_text("blocks")
                   if b[0] < 0 or b[1] < 0 or b[2] > page.rect.width + 1 or b[3] > page.rect.height + 1]
        assert not outside, (i + 1, outside)
        assert len(text) > 100, i + 1
        for link in page.get_links():
            if link["kind"] == fitz.LINK_GOTO:
                assert 0 <= link["page"] < len(doc)
        pages.append({"page": i + 1, "characters": len(text), "out_of_page": outside})
        pix = page.get_pixmap(matrix=fitz.Matrix(.65, .65))
        im = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        thumb = Image.new("RGB", (im.width, im.height + 22), "#dddddd")
        thumb.paste(im, (0, 22))
        ImageDraw.Draw(thumb).text((5, 3), f"Page {i+1}", fill="black")
        thumbs.append(thumb)
        if i in [0, 3, 5, 7, 8, 11, 12, len(doc) - 1]:
            page.get_pixmap(matrix=fitz.Matrix(1.4, 1.4)).save(previews / f"final_page_{i+1:02}.png")
    for banned in ["??", "Frozen scalar", "讨论稿", "CONDITIONAL GO", "Lcert"]:
        assert banned not in fulltext, banned
    sheet = Image.new("RGB", (4 * thumbs[0].width, ((len(thumbs) + 3) // 4) * thumbs[0].height), "#aaaaaa")
    for i, im in enumerate(thumbs):
        sheet.paste(im, ((i % 4) * im.width, (i // 4) * im.height))
    sheet.save(previews / "final_contact.png")
    (HERE / "pdf_text.txt").write_text(fulltext, encoding="utf-8")

    links_checked = 0
    for directory in [PAPER, HERE]:
        for path in directory.glob("*.md"):
            for link in re.findall(r"\]\(([^)]+)\)", path.read_text(encoding="utf-8")):
                if "://" in link or link in ["release_manifest.json", "delivery_validation.json"]:
                    continue
                assert (path.parent / link.split("#")[0]).exists(), (path.name, link)
                links_checked += 1

    result = {
        "status": "PASS",
        "scope": "Content freeze; administrative metadata incomplete by user instruction",
        "base_commit": before["base_commit"],
        "protected_files": len(before["files"]),
        "protected_changes": changes,
        "pages": len(doc),
        "pdf_sha256": sha(PAPER / "paper.pdf"),
        "tex_labels": len(labels), "defined_references_checked": len(refs),
        "cited_references": len(cites),
        "chinese_abstract_han_characters": cn_chars,
        "english_abstract_words": en_words,
        "graphical_abstract_words": graphical_words,
        "reversible_typography": "PASS",
        "plot_curve_code_unchanged": True,
        "plot_input_summary_sha256": sha(frozen_summary),
        "new_simulations": False,
        "bootstrap_rerun": False,
        "online_submission": False,
        "missing_metadata": ["authors", "affiliations", "corresponding_author_email", "funding", "classification_code"],
        "official_style_sha256": "5a0301fecb1fd645da6d45be4c57eb4c8a34590c3092f3d130a8ddd776627913",
        "latest_online_guideline_check": "Download page reachable; instructions/list API timed out; prior official DOCX re-read",
        "hard_build_warnings": build["warnings"],
        "other_engine_or_spacing_warnings": build["other_engine_or_spacing_warnings"],
        "local_links_checked": links_checked,
        "page_checks": pages,
    }
    (HERE / "delivery_validation.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    allowed = {".tex", ".py", ".json", ".md", ".pdf", ".png"}
    frozen = {p.relative_to(PAPER).as_posix(): sha(p)
              for p in sorted(PAPER.rglob("*")) if p.is_file()
              and p.suffix in allowed and p.name != "release_manifest.json" and "__pycache__" not in p.parts}
    (PAPER / "release_manifest.json").write_text(json.dumps({
        "active_manuscript": "paper.pdf", "status": "CONTENT_FROZEN_METADATA_PENDING",
        "sha256": frozen, "new_simulations": False, "submitted": False,
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({k: result[k] for k in ["status", "protected_files", "pages", "pdf_sha256", "cited_references", "chinese_abstract_han_characters", "english_abstract_words"]}, ensure_ascii=True))


if __name__ == "__main__":
    main()
