"""Build the anonymous v5 manuscript PDF and editable Word file from its Markdown source."""
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
SOURCE = ROOT / "manuscript_submission_v5.md"
PANDOC = get_pandoc_path()

PREAMBLE = r"""\documentclass[a4paper,UTF8,fontset=windows,zihao=5]{ctexart}
\usepackage[left=18mm,right=18mm,top=22mm,bottom=22mm,columnsep=7mm]{geometry}
\usepackage{amsmath,amssymb,array,booktabs,longtable,calc,graphicx,setspace,hyperref}
\usepackage{fontspec,multicol}
\setmainfont{Times New Roman}
\hypersetup{hidelinks,pdfauthor={},pdftitle={基于幅值区间的事件触发偏置补偿方法}}
\setcounter{secnumdepth}{-1}
\newcounter{none}
\ctexset{section={format=\centering\heiti\zihao{3},beforeskip=10pt,afterskip=5pt},subsection={format=\heiti\zihao{4},beforeskip=7pt,afterskip=3pt},subsubsection={format=\heiti\zihao{-4},beforeskip=5pt,afterskip=2pt}}
\setstretch{1.12}
\raggedcolumns
\setlength{\columnsep}{7mm}
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
    # Each spread combines full-width exhibits with balanced columns of related text.
    # Splitting the Markdown before conversion keeps captions and notes in both outputs.
    def take(start, end):
        return text[text.index(start):text.index(end)].strip()

    def columns(md):
        return "\n" + r"\begin{multicols}{2}" + "\n" + convert(md, "latex") + r"\end{multicols}" + "\n"

    def exhibit(number, kind):
        marker = f"**{kind}{number}　"
        lines = text[text.index(marker):].splitlines()
        caption, translation = [line.strip("*\\").strip() for line in lines[:2]]
        start = text.index(marker)
        if kind == "图":
            asset = re.findall(r"!\[\]\(([^)]+)\)", text[:start])[-1]
            note = lines[3] if len(lines) > 3 and lines[3].startswith("注：") else ""
            max_height = ".45" if number == 2 else ".30"
            graphic = (r"\includegraphics[width=.96\linewidth,height=" + max_height
                       + r"\textheight,keepaspectratio]{"
                       + str(Path(asset).with_suffix(".pdf")).replace("\\", "/") + "}")
            return (r"\noindent\begin{minipage}{\textwidth}\centering " + graphic + r"\par\small "
                    + convert(caption + "\n\n" + translation, "latex")
                    + r"\par\raggedright\footnotesize " + convert(note, "latex") + r"\end{minipage}\par")
        rows = []
        for line in lines[3:]:
            if not line.startswith("|"):
                break
            if re.fullmatch(r"[|:\- ]+", line):
                continue
            cells = [convert(x.strip(), "latex").strip() for x in line.strip("|").split("|")]
            rows.append(" & ".join(cells))
        table_size = r"\scriptsize"
        cell_sep = "1pt" if number == 2 else "2.5pt"
        return (r"\noindent\begin{minipage}{\textwidth}\centering" + table_size + " "
                + convert(caption + "\n\n" + translation, "latex") + r"\par\smallskip "
                + r"\setlength{\tabcolsep}{" + cell_sep + r"}\renewcommand{\arraystretch}{1.17}"
                + r"\begin{tabular*}{\linewidth}{@{\extracolsep{\fill}}l" + "r"*(len(cells)-1)
                + r"@{}}\toprule " + rows[0] + r"\\\midrule "
                + r"\\".join(rows[1:]) + r"\\\bottomrule\end{tabular*}\end{minipage}\par")

    def figure(n):
        return exhibit(n, "图")

    def table(n):
        return exhibit(n, "表")

    def before_figure(start, stem):
        return take(start, "![](submission_evidence/v5_figures/" + stem)

    title, rest = text.split("\n", 1)
    front = r"\begin{center}{\heiti\zihao{2} " + title[2:] + r"}\end{center}" + convert(rest[:rest.index("## 1")], "latex")
    english = take("## Interval-", "## 参考文献")
    english_title, english_rest = english.split("\n", 1)
    english_block = (r"\begin{minipage}{\textwidth}\centering"
                     + r"\heiti\zihao{3} " + english_title[3:] + r"\par\medskip"
                     + r"\small\setstretch{1.15}\raggedright "
                     + convert(english_rest, "latex")
                     + r"\end{minipage}")
    ref_text = text[text.index("## 参考文献"):]
    theory = take("## 4　", "## 6　")
    pages = [
        front + columns(take("## 1　", "## 2　")),
        columns(take("## 2　", "![](submission_evidence/v5_figures/architecture.png)"))
        + figure(1) + columns(take("## 3　", "## 4　")),
        columns(theory),
        columns(take("## 6　", "**表1　")) + table(1),
        columns(take("在36条健康轨迹中", "为对应理论条件"))
        + columns(take("为对应理论条件", "![](submission_evidence/v5_figures/state_error_and_events.png)"))
        + figure(2)
        + columns(take("图3将", "![](submission_evidence/v5_figures/separation.png)")),
        figure(3)
        + columns(take("### 6.2　", "**表2　")) + table(2)
        + columns(take("在强偏置早起点组", "## 6.3　")),
        columns(take("## 6.3　", "![](submission_evidence/v5_figures/robustness_2panel.png)"))
        + figure(4)
        + columns(take("## 7　", "## Interval-")),
        r"\clearpage" + english_block + r"{\footnotesize\setstretch{0.98}\setlength{\parindent}{0pt}\setlength{\parskip}{0.2pt}\setlength{\columnsep}{5mm}\interlinepenalty=10000\sloppy " + columns(ref_text) + "}",
    ]
    body = ("\n\\medskip\n".join(pages[:5]) + "\n\\clearpage\n"
            + "\n\\medskip\n".join(pages[5:]))
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
    sec.left_margin, sec.right_margin = Cm(1.8), Cm(1.8)
    sec.top_margin = sec.bottom_margin = Cm(2.2)
    initial_cols = sec._sectPr.find(qn("w:cols"))
    if initial_cols is None:
        initial_cols = OxmlElement("w:cols")
        sec._sectPr.append(initial_cols)
    initial_cols.set(qn("w:num"), "2")
    initial_cols.set(qn("w:space"), "397")
    normal = doc.styles["Normal"]
    set_fonts(normal, "宋体", 10.5)
    normal.paragraph_format.line_spacing = Pt(14)
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
    for paragraph in doc.paragraphs:
        if paragraph.text.startswith(("图", "Fig.", "表", "Table", "算法", "Algorithm")):
            paragraph.paragraph_format.keep_with_next = True
        if paragraph.text.startswith("注："):
            paragraph.paragraph_format.keep_together = True
    algorithm_active = False
    for paragraph in doc.paragraphs:
        if paragraph.text.startswith("算法1"):
            algorithm_active = True
            edge = "top"
        elif algorithm_active and paragraph.text.startswith("输入"):
            edge = "top"
        elif algorithm_active and paragraph.text.startswith("输出 ") and "回写" in paragraph.text:
            edge = "bottom"
            algorithm_active = False
        else:
            if paragraph.style.name.startswith("Heading"):
                algorithm_active = False
            continue
        borders = OxmlElement("w:pBdr")
        rule = OxmlElement("w:" + edge)
        rule.set(qn("w:val"), "single")
        rule.set(qn("w:sz"), "6")
        borders.append(rule)
        paragraph._p.get_or_add_pPr().append(borders)
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
                    if end + 1 < len(children) and "".join(children[end + 1].itertext()).startswith("注："):
                        end += 1
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
        cols.set(qn("w:space"), "397")
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
    final_cols.set(qn("w:space"), "397")

    doc.save(SOURCE.with_suffix(".docx"))


if __name__ == "__main__":
    text = SOURCE.read_text(encoding="utf8")
    with TemporaryDirectory(prefix="paper2-typeset-") as work:
        make_pdf(text, Path(work))
        make_word(text, Path(work))
