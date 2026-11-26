"""Build the anonymous review PDF and editable Word file from the shared source."""
# /// script
# dependencies = ["pypandoc-binary>=1.15", "python-docx>=1.1"]
# ///
from pathlib import Path
from tempfile import TemporaryDirectory
import re
import subprocess

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt
from pypandoc import get_pandoc_path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "manuscript_submission_v1.md"
PANDOC = get_pandoc_path()

PREAMBLE = r"""\documentclass[a4paper,UTF8,fontset=windows,zihao=5]{ctexart}
\usepackage[left=18mm,right=20mm,top=20mm,bottom=20mm]{geometry}
\usepackage{amsmath,amssymb,array,booktabs,longtable,calc,graphicx,setspace,hyperref}
\usepackage{fontspec}
\setmainfont{Times New Roman}
\hypersetup{hidelinks,pdfauthor={},pdftitle={随机事件触发远程估计中持续载荷偏置的条件风险校正}}
\setcounter{secnumdepth}{-1}
\newcounter{none}
\ctexset{section={format=\centering\heiti\zihao{3}},subsection={format=\heiti\zihao{4}},subsubsection={format=\heiti\zihao{-4}}}
\setstretch{1.5}
\setlength{\parindent}{2em}
\setlength{\parskip}{0pt}
\setlength{\LTpre}{2pt}
\setlength{\LTpost}{4pt}
\setlength{\emergencystretch}{2em}
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
    # Keep bilingual captions on the same page as their diagrams.
    pat = r"\\pandocbounded\{\\includegraphics\[keepaspectratio\]\{([^}]+)\}\}\s*\\textbf\{(图[^}\n]+)\}\\\\\s*\\textbf\{(Fig\.[^}\n]+)\}"
    def figure(m):
        file = Path(m[1]).with_suffix(".pdf").as_posix()
        return (r"\begin{center}\begin{minipage}{\linewidth}\centering" + "\n"
                + r"\includegraphics[width=.89\linewidth,height=.31\textheight,keepaspectratio]{"+file+"}\n"
                + r"\par\small "+m[2]+r"\\ "+m[3]+r"\end{minipage}\end{center}")
    body = re.sub(pat, figure, body)
    body = re.sub(r"\\pandocbounded\{\\includegraphics\[keepaspectratio\]\{([^}]+)\}\}",
                  lambda m: r"\begin{center}\includegraphics[width=.72\linewidth]{"
                  +Path(m[1]).with_suffix(".pdf").as_posix()+r"}\end{center}", body)
    body = body.replace(r"\textbf{表", r"\filbreak\noindent\textbf{表")
    body = body.replace(r"\begin{longtable}",r"{\small\setstretch{1.05}\begin{longtable}")
    body = body.replace(r"\end{longtable}",r"\end{longtable}}")
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
    doc.save(SOURCE.with_suffix(".docx"))


if __name__ == "__main__":
    text = SOURCE.read_text(encoding="utf8")
    with TemporaryDirectory(prefix="paper2-typeset-") as work:
        make_pdf(text, Path(work))
        make_word(text, Path(work))
