"""Build the anonymous v4 manuscript PDF and editable Word file from its Markdown source."""
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
SOURCE = ROOT / "manuscript_submission_v4.md"
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
            graphic = (r"\includegraphics[width=.96\linewidth,height=.30\textheight,keepaspectratio]{"
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
        return (r"\noindent\begin{minipage}{\textwidth}\centering\small "
                + convert(caption + "\n\n" + translation, "latex") + r"\par\smallskip "
                + r"\setlength{\tabcolsep}{3pt}\renewcommand{\arraystretch}{1.17}"
                + r"\begin{tabular*}{\linewidth}{@{\extracolsep{\fill}}l" + "r"*(len(cells)-1)
                + r"@{}}\toprule " + rows[0] + r"\\\midrule "
                + r"\\".join(rows[1:]) + r"\\\bottomrule\end{tabular*}\end{minipage}\par")

    def figure(n):
        return exhibit(n, "图")

    def table(n):
        return exhibit(n, "表")

    def before_figure(start, stem):
        return take(start, "![](submission_evidence/v4_figures/" + stem)

    title, rest = text.split("\n", 1)
    front = r"\begin{center}{\heiti\zihao{2} " + title[2:] + r"}\end{center}" + convert(rest[:rest.index("## 1")], "latex")
    algorithm = convert(take("**算法1", "## 6"), "latex")
    algorithm = algorithm.replace(r"\begin{enumerate}", r"\par\smallskip\hrule\begin{enumerate}")
    core = convert(take("## 5", "**算法1"), "latex")
    law = (r"\begin{multicols}{2}" + core + r"\par\medskip\noindent\begin{minipage}{\columnwidth}\small\hrule\smallskip "
           + algorithm + r"\smallskip\hrule\end{minipage}\end{multicols}")
    pages = [
        front + columns(take("## 1", "## 2")),
        figure(1) + columns(before_figure("## 2", "architecture") + "\n\n" + take("## 3", "两种估计基于")),
        columns(take("两种估计基于", "**证明**　M2")),
        columns(take("**证明**　M2", "## 5")) + law,
        table(1) + columns(take("## 6", "**表1") + "\n\n" + take("健康测试组内", "图2选取")),
        figure(2) + columns(before_figure("图2选取", "state_error") + "\n\n" + before_figure("强正、强负测试序列", "separation")) + figure(3),
        table(2) + columns(take("### 6.2", "**表2") + "\n\n" + take("系统II强晚起点组", "**表3")) + table(3)
        + columns(take("464次", "### 6.4")),
        figure(4) + columns(before_figure("### 6.4", "fig3_mismatch")) + table(4),
        columns(take("## 7", "## Interval")) + convert(take("## Interval", "## 参考文献"), "latex")
        + r"{\small\setstretch{1.05}\interlinepenalty=10000\sloppy " + columns(text[text.index("## 参考文献"):]) + "}",
    ]
    body = "\n\\clearpage\n".join(pages)
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
