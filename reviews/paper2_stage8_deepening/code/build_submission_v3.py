"""Build the anonymous v3 manuscript PDF and editable Word file from its Markdown source."""
# /// script
# dependencies = ["pypandoc-binary>=1.15", "python-docx>=1.1"]
# ///
from pathlib import Path
from tempfile import TemporaryDirectory
from copy import deepcopy
import re
import subprocess

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt
from pypandoc import get_pandoc_path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "manuscript_submission_v3.md"
PANDOC = get_pandoc_path()

PREAMBLE = r"""\documentclass[a4paper,UTF8,fontset=windows,zihao=5,twocolumn]{ctexart}
\usepackage[left=16mm,right=16mm,top=17mm,bottom=17mm,columnsep=6mm]{geometry}
\usepackage{amsmath,amssymb,array,booktabs,longtable,calc,graphicx,setspace,hyperref}
\usepackage{fontspec}
\setmainfont{Times New Roman}
\hypersetup{hidelinks,pdfauthor={},pdftitle={基于幅值区间的事件触发偏置补偿方法}}
\setcounter{secnumdepth}{-1}
\newcounter{none}
\ctexset{section={format=\centering\heiti\zihao{3},beforeskip=10pt,afterskip=5pt},subsection={format=\heiti\zihao{4},beforeskip=7pt,afterskip=3pt},subsubsection={format=\heiti\zihao{-4},beforeskip=5pt,afterskip=2pt}}
\setstretch{1.48}
\setlength{\parindent}{2em}
\setlength{\parskip}{1.2pt plus .3pt}
\setlength{\LTpre}{2pt}
\setlength{\LTpost}{3pt}
\setlength{\emergencystretch}{2em}
\setlength{\abovedisplayskip}{5pt plus 1pt minus 1pt}
\setlength{\belowdisplayskip}{5pt plus 1pt minus 1pt}
\newcommand{\tightlist}{\setlength{\itemsep}{0pt}\setlength{\parskip}{0pt}}
\begin{document}
"""


def convert(text, fmt, output=None):
    cmd = [PANDOC, "-f", "markdown-implicit_figures-smart", "-t", fmt, "--wrap=none"]
    if output:
        cmd.extend(["-o", str(output)])
    return subprocess.run(cmd, cwd=ROOT, input=text, encoding="utf8", check=True,
                          stdout=subprocess.PIPE).stdout


def make_pdf(text, tmp):
    body = convert(text, "latex")
    intro = re.search(r"\\subsection\{1[^}]*引言\}", body)
    if not intro:
        raise RuntimeError("Could not find the first article section in converted LaTeX")
    front = body[:intro.start()]
    body = body[intro.start():]
    front = re.sub(r"^\\section\{[^}]+\}(?:\\label\{[^}]+\})?\s*", "", front)
    title = text.splitlines()[0].removeprefix("# ").strip()
    front = (r"\twocolumn[{\begin{@twocolumnfalse}\begin{center}"
             + r"{\heiti\zihao{2} " + title + r"}\end{center}"
             + r"\setstretch{1.25}\normalsize " + front + r"\end{@twocolumnfalse}}]")
    body = front + "\n" + body

    figure_pat = re.compile(
        r"\\includegraphics\[[^\]]*\]\{([^}]+)\}\s*"
        r"\\textbf\{(图[^}]+)\}\\\\\s*\\textbf\{(Fig\.[^}]+)\}")
    figure_files = {
        "architecture.png": "architecture.pdf",
        "state_error_and_events.png": "state_error_and_events.pdf",
        "separation.png": "separation.pdf",
        "sensitivity.png": "fig3_mismatch_3panel.pdf",
        "fig3_mismatch_3panel.png": "fig3_mismatch_3panel.pdf",
    }
    figure_heights = {
        "architecture.png": ".38\\textheight",
        "state_error_and_events.png": ".34\\textheight",
        "separation.png": ".37\\textheight",
        "sensitivity.png": ".55\\textheight",
        "fig3_mismatch_3panel.png": ".55\\textheight",
    }

    def replace_figure(match):
        name = Path(match.group(1)).name
        if name not in figure_files:
            raise RuntimeError(f"Unexpected figure in article source: {name}")
        file = Path("submission_evidence/v3_figures", figure_files[name]).as_posix()
        height = figure_heights[name]
        chinese_caption = re.sub(r"^图\s*\d+\s*[　 ]*", "", match.group(2))
        english_caption = re.sub(r"^Fig\.\s*\d+\s*", "", match.group(3))
        return (r"\begin{figure*}[!t]\centering"
                + r"\includegraphics[width=.97\textwidth,height=" + height
                + r",keepaspectratio]{" + file + "}"
                + r"\caption{\small " + chinese_caption + r"\quad\emph{"
                + english_caption + r"}}\end{figure*}")

    body = figure_pat.sub(replace_figure, body)

    table_pat = re.compile(
        r"\\textbf\{(表[^}]+)\}\\\\\s*\\textbf\{(Table[^}]+)\}\s*"
        r"\{\s*\\def\\LTcaptype\{none\}.*?"
        r"\\begin\{longtable\}\[\]\{(?P<spec>.*?)\}"
        r"(?P<contents>.*?)\\end\{longtable\}\s*\}", re.S)

    def replace_table(match):
        contents = re.sub(r"\\end(?:firsthead|head|foot|lastfoot)", "", match.group("contents"))
        chinese_caption = re.sub(r"^表\s*\d+\s*[　 ]*", "", match.group(1))
        english_caption = re.sub(r"^Table\s*\d+\s*", "", match.group(2))
        return (r"\begin{table*}[!t]\centering\caption{\small "
                + chinese_caption + r"\quad\emph{" + english_caption + r"}}"
                + r"\resizebox{\textwidth}{!}{\begin{tabular}{"
                + match.group("spec") + "}" + contents + r"\end{tabular}}\end{table*}")

    body, table_count = table_pat.subn(replace_table, body)
    if table_count != 4:
        raise RuntimeError(f"Expected four full-width tables, converted {table_count}")

    english = re.compile(
        r"\\subsection\{Interval-Based Bias Compensation for Event-Triggered Estimation\}"
        r"(?:\\label\{[^}]+\})?\s*(?P<content>.*?)"
        r"(?=\\subsection\{参考文献\})", re.S)
    english_match = english.search(body)
    if not english_match:
        raise RuntimeError("Could not find the complete English title and abstract block")
    english_content = english_match.group("content")
    english_content = re.sub(
        r"\\textbf\{Abstract\}\s*",
        lambda _: r"\textbf{Abstract}\quad ", english_content)
    english_content = re.sub(
        r"\\textbf\{Key words\}\s*",
        lambda _: r"\textbf{Key words}\quad ", english_content)
    english_block = (
        r"\clearpage\twocolumn[\begin{minipage}{.97\textwidth}"
        + r"\centering{\heiti\zihao{3} Interval-Based Bias Compensation for Event-Triggered Estimation}\par"
        + r"\vspace{5pt}\small\setstretch{1.22}\noindent "
        + english_content
        + r"\end{minipage}]" + "\n")
    body = body[:english_match.start()] + english_block + body[english_match.end():]

    references = re.search(r"\\subsection\{参考文献\}(?:\\label\{[^}]+\})?", body)
    if not references:
        raise RuntimeError("Could not find the references section")
    body = (body[:references.start()] + r"{\small\setstretch{1.10}\interlinepenalty=10000\sloppy "
            + body[references.start():] + "\n}")
    tex = tmp / "manuscript.tex"
    tex.write_text(PREAMBLE + body + "\n\\end{document}\n", encoding="utf8")
    for _ in range(2):
        proc = subprocess.run(["xelatex","-halt-on-error","-interaction=batchmode",
                               "-output-directory="+str(tmp),str(tex)],cwd=ROOT,
                              stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
        if proc.returncode:
            log = (tmp/"manuscript.log").read_text(encoding="utf8",errors="replace")
            raise RuntimeError(log[-4500:])
    (ROOT / SOURCE.with_suffix(".pdf").name).write_bytes((tmp/"manuscript.pdf").read_bytes())


def set_fonts(style, east, size):
    style.font.name = "Times New Roman"
    style.font.size = Pt(size)
    fonts = style.element.get_or_add_rPr().rFonts
    fonts.set(qn("w:eastAsia"), east)


def make_word(text, tmp):
    # In Word the number is part of the editable Office Math expression.
    text = re.sub(r"\\tag\{(\d+)\}", r"\\qquad ( \1 )", text)
    raw = tmp / "editable.docx"
    convert(text, "docx", raw)
    doc = Document(raw)
    doc.core_properties.author = ""
    doc.core_properties.title = text.splitlines()[0][2:]
    sec = doc.sections[0]
    sec.page_width, sec.page_height = Cm(21), Cm(29.7)
    sec.left_margin, sec.right_margin = Cm(1.8), Cm(2)
    sec.top_margin = sec.bottom_margin = Cm(2)
    initial_cols = sec._sectPr.find(qn("w:cols"))
    if initial_cols is None:
        initial_cols = OxmlElement("w:cols")
        sec._sectPr.append(initial_cols)
    initial_cols.set(qn("w:num"), "2")
    initial_cols.set(qn("w:space"), "360")
    normal = doc.styles["Normal"]
    set_fonts(normal, "宋体", 10.5)
    normal.paragraph_format.line_spacing = 1.5
    normal.paragraph_format.space_after = Pt(0)
    normal.paragraph_format.first_line_indent = Pt(21)
    for h, size in [(1,16),(2,14),(3,12)]:
        style = doc.styles[f"Heading {h}"]
        set_fonts(style,"黑体",size)
        style.paragraph_format.first_line_indent = Pt(0)
        style.paragraph_format.keep_with_next = True
    for paragraph in doc.paragraphs:
        if paragraph.style.name=="Heading 1":
            paragraph.alignment=WD_ALIGN_PARAGRAPH.CENTER
        if paragraph._p.xpath(".//w:drawing"):
            paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
            paragraph.paragraph_format.first_line_indent = Pt(0)
            paragraph.paragraph_format.keep_with_next = True
        if paragraph.text.startswith(("表","图","算法","[")):
            paragraph.paragraph_format.first_line_indent = Pt(0)
            if re.match(r"^(表|图|算法)\d",paragraph.text):
                paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
                paragraph.paragraph_format.keep_with_next = paragraph.text.startswith("表")
    for image in doc.inline_shapes:
        width = Cm(16)
        image.height = int(image.height * width / image.width)
        image.width = width
    for table in doc.tables:
        borders = OxmlElement("w:tblBorders")
        for side in ("top","bottom","left","right","insideV","insideH"):
            border = OxmlElement("w:"+side)
            border.set(qn("w:val"),"single" if side in ("top","bottom") else "nil")
            border.set(qn("w:sz"),"8")
            borders.append(border)
        table._tbl.tblPr.append(borders)
        for i,row in enumerate(table.rows):
            for cell in row.cells:
                if i==0:
                    borders = OxmlElement("w:tcBorders")
                    edge = OxmlElement("w:bottom")
                    edge.set(qn("w:val"),"single")
                    edge.set(qn("w:sz"),"4")
                    borders.append(edge)
                    cell._tc.get_or_add_tcPr().append(borders)
                for paragraph in cell.paragraphs:
                    pf=paragraph.paragraph_format
                    pf.first_line_indent=Pt(0)
                    pf.line_spacing=1.0
                    pf.space_before=pf.space_after=Pt(1)
                    for run in paragraph.runs:
                        run.font.size=Pt(9)
    # The journal PDF and editable Word file both use two columns. Insert
    # continuous one-column sections around full-width figures and tables.
    body = doc.element.body
    children = list(body.iterchildren())
    index_by_id = {id(node): index for index, node in enumerate(children)}
    wide_blocks = []
    top_paragraphs = [p for p in doc.paragraphs if p._p.getparent() is body]
    for paragraph in top_paragraphs:
        if paragraph._p.xpath(".//w:drawing"):
            start = index_by_id[id(paragraph._p)]
            end = start
            if start + 1 < len(children) and children[start + 1].tag == qn("w:p"):
                following = children[start + 1]
                text_after_image = "".join(following.itertext())
                if "图" in text_after_image or "Fig." in text_after_image:
                    end = start + 1
            wide_blocks.append((start, end))
    for table in doc.tables:
        if table._tbl.getparent() is body:
            table_index = index_by_id[id(table._tbl)]
            start = table_index
            if table_index > 0 and children[table_index - 1].tag == qn("w:p"):
                caption = "".join(children[table_index - 1].itertext())
                if "表" in caption or "Table" in caption:
                    start = table_index - 1
            wide_blocks.append((start, table_index))

    base_sect_pr = deepcopy(body.sectPr)

    def section_marker(column_count):
        marker = OxmlElement("w:p")
        ppr = OxmlElement("w:pPr")
        sect_pr = deepcopy(base_sect_pr)
        sect_type = sect_pr.find(qn("w:type"))
        if sect_type is None:
            sect_type = OxmlElement("w:type")
            sect_pr.insert(0, sect_type)
        sect_type.set(qn("w:val"), "continuous")
        cols = sect_pr.find(qn("w:cols"))
        if cols is None:
            cols = OxmlElement("w:cols")
            sect_pr.append(cols)
        cols.set(qn("w:num"), str(column_count))
        cols.set(qn("w:space"), "360")
        ppr.append(sect_pr)
        marker.append(ppr)
        return marker

    paragraphs = [p for p in doc.paragraphs if p._p.getparent() is body]
    english_start = next((p for p in paragraphs if p.text.startswith("Interval-Based Bias Compensation")), None)
    english_end = next((p for p in paragraphs if p.text.startswith("Key words")), None)
    if english_start is not None and english_end is not None:
        current_children = list(body.iterchildren())
        start_index = next(i for i, node in enumerate(current_children) if node is english_start._p)
        end_index = next(i for i, node in enumerate(current_children) if node is english_end._p)
        wide_blocks.append((start_index, end_index))
        english_start.paragraph_format.page_break_before = True

    for start, end in sorted(wide_blocks, reverse=True):
        body.insert(start, section_marker(2))
        body.insert(end + 2, section_marker(1))

    metadata = next((p for p in doc.paragraphs if p.text.startswith("中图分类号")), None)
    if metadata is not None:
        current_children = list(body.iterchildren())
        metadata_index = next(i for i, node in enumerate(current_children) if node is metadata._p)
        body.insert(metadata_index + 1, section_marker(1))
    final_cols = body.sectPr.find(qn("w:cols"))
    if final_cols is None:
        final_cols = OxmlElement("w:cols")
        body.sectPr.append(final_cols)
    final_cols.set(qn("w:num"), "2")
    final_cols.set(qn("w:space"), "360")

    doc.save(SOURCE.with_suffix(".docx"))


if __name__ == "__main__":
    text = SOURCE.read_text(encoding="utf8")
    with TemporaryDirectory(prefix="paper2-typeset-") as work:
        make_pdf(text, Path(work))
        make_word(text, Path(work))
