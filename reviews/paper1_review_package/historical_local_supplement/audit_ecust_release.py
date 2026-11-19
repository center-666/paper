"""Check scientific-content preservation and PDF completeness after copyediting.

This is a consistency check, not a new proof audit or a simulation run.
"""
from pathlib import Path
import hashlib,json,re,subprocess,xml.etree.ElementTree as ET
from urllib.parse import unquote

P=Path(__file__).resolve().parent
OLD=P.parent/'latex_final_audit_20261020'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
MATH=re.compile(r'\\begin\{(equation\*?|align\*?|gather\*?|multline\*?)\}.*?\\end\{\1\}|\\\[.*?\\\]',re.S)
DECL=re.compile(r'\\begin\{(theorem|lemma|proposition|remark|corollary)\}.*?\\end\{\1\}',re.S)
def norm(s):return re.sub(r'\s+','',s)
def mathnorm(s):
    # Ignore only presentation changes, keeping all algebraic tokens and labels.
    for token in [r'\begin{aligned}',r'\end{aligned}',r'\quad',r'\qquad',r'\bigl',r'\bigr',r'\\','&']:
        s=s.replace(token,'')
    return norm(s)
def bib(s):
    s=s.split(r'\end{thebibliography}')[0]
    result={}
    for m in re.finditer(r'\\bibitem\{([^}]+)\}(.*?)(?=\\bibitem\{|\Z)',s,re.S):
        body=m[2]
        ds=re.search(r'https://doi.org/([^}\s]+)|\\paperdoi\{([^}]+)\}',body)
        doi=next((x for x in ds.groups() if x),None) if ds else None
        body=re.sub(r'DOI:\s*\\paperdoi\{[^}]+\}\.','',body)
        # DOI titles in this reference list contain no nested braces.
        body=re.sub(r'\\href\{https://doi.org/[^}]+\}\{([^{}]*)\}',r'\1',body)
        result[m[1]]={'text':norm(body),'doi':doi}
    return result

manifest=json.loads((P/'ecust_input_manifest.json').read_text(encoding='utf-8'))
# Verify all source-release files against the captured input hashes.
files=manifest.get('input_files',manifest.get('files'))
if files is None:
    print('Manifest keys:',list(manifest));raise AssertionError('Input manifest schema')
for name,digest in files.items():
    assert sha(OLD/name)==digest,name

tex=['theory.tex','main_joint_kernel.tex','record_design.tex','numerical.tex',
     'record_condition_numerical.tex','conclusion.tex','vector_proof.tex',
     'scalar_counterexample.tex','validation_appendix.tex','label_refinement.tex',
     'record_condition_appendix.tex','statistical_extension.tex','finite_sample.tex','statistical_numerical.tex']
blocks=declarations=0
for name in tex:
    before=(OLD/name).read_text(encoding='utf-8');after=(P/name).read_text(encoding='utf-8')
    b=[mathnorm(m[0]) for m in MATH.finditer(before)];a=[mathnorm(m[0]) for m in MATH.finditer(after)]
    assert a==b,('display mathematics',name);blocks+=len(a)
    b=[norm(m[0]) for m in DECL.finditer(before)];a=[norm(m[0]) for m in DECL.finditer(after)]
    assert a==b,('formal declaration',name);declarations+=len(a)
    assert sorted(re.findall(r'\\label\{([^}]+)\}',before))==sorted(re.findall(r'\\label\{([^}]+)\}',after)),('labels',name)
base=json.loads((P/'final_scientific_baseline.json').read_text(encoding='utf-8'))
copyedited={'build.py','conclusion.tex','damage_figure.tex','damage_table_float.tex','figures/graphical_summary.tex','graphical.tex','graphical_abstract.tex','main_joint_kernel.tex','paper.tex','record_condition_figure.tex'}
frozen={name:digest for name,digest in base['unchanged_files'].items() if name not in copyedited}
for name,digest in frozen.items():assert sha(P/name)==digest,name
assert bib((OLD/'references.tex').read_text(encoding='utf-8'))==bib((P/'references.tex').read_text(encoding='utf-8'))
for name in ['references_base.tex','references_additions.tex']:
    assert sha(P/name)==sha(OLD/name)
supp=['supplement.tex','vector_proof.tex','scalar_counterexample.tex','validation_appendix.tex',
      'label_refinement.tex','record_condition_appendix.tex','statistical_extension.tex','finite_sample.tex','statistical_numerical.tex']
for name in supp:assert sha(P/name)==sha(OLD/name),name

build=json.loads((P/'build_check.json').read_text(encoding='utf-8'))
assert build['passed'] and not build['draft']
for name,digest in build['source_sha256'].items():assert sha(P/name)==digest,name
pdfs={};warnings={}
BIN=Path('D:/latex/texlive/2025/bin/windows')
for stem in ['paper','paper_submission','supplement','graphical']:
    assert sha(P/(stem+'.pdf'))==build['documents'][stem]['pdf_sha256']
    bbox=subprocess.check_output([str(BIN/'pdftotext.exe'),'-bbox','-enc','UTF-8',str(P/(stem+'.pdf')),'-'])
    # Poppler emits control-code mappings for a few math delimiters; their boxes
    # are retained and the glyphs are checked in the rendered pages.
    bbox=re.sub(rb'[\x00-\x08\x0b\x0c\x0e-\x1f]',b' ',bbox)
    doc=ET.fromstring(bbox);ns={'h':'http://www.w3.org/1999/xhtml'}
    pages=doc.findall('.//h:page',ns)
    text=(P/(stem+'_extracted.txt')).read_text(encoding='utf-8')
    assert '??' not in text and '\ufffd' not in text
    outside=[]
    for i,page in enumerate(pages):
        for word in page.findall('h:word',ns):
            x0,y0,x1,y1=[float(word.attrib[k]) for k in ['xMin','yMin','xMax','yMax']]
            if x0 < -0.5 or y0 < -0.5 or x1 > float(page.attrib['width'])+.5 or y1 > float(page.attrib['height'])+.5:
                outside.append([i+1,word.text,[x0,y0,x1,y1]])
    assert not outside,(stem,outside)
    if stem in ['paper','paper_submission']:
        # Locate the heading by page, retaining the entire page so that the
        # second-column continuation above the heading is not lost.
        page_text=[' '.join(w.text or '' for w in pg.findall('h:word',ns)) for pg in pages]
        starts=[i for i,t in enumerate(page_text) if '参考文献' in t.replace(' ','')]
        assert len(starts)==1,(stem,starts)
        refs=' '.join(page_text[starts[0]:])
        nums=re.findall(r'\[(\d+)\]',refs)
        assert sorted(map(int,nums))==list(range(1,31)),(stem,nums)
        assert text.count('Abstract:')==1 and text.count('Key words:')==1
        if stem=='paper':
            assert 'Abstract:' in page_text[-1] and 'Key words:' in page_text[-1]
    html=subprocess.check_output([str(BIN/'pdftohtml.exe'),'-xml','-hidden','-i','-stdout','-enc','UTF-8',str(P/(stem+'.pdf'))],stderr=subprocess.DEVNULL).decode('utf-8')
    remote=re.findall(r'<a href="([^"#]+\.pdf)(?:#[^"]*)?"',html)
    for link in remote:assert (P/unquote(link)).is_file(),link
    log=(P/(stem+'.log')).read_text(encoding='utf-8',errors='replace')
    warnings[stem]=[l for l in log.splitlines() if re.search(r'Overfull|Underfull|LaTeX Warning|Package \S+ Warning|Missing character',l)]
    assert not [l for l in warnings[stem] if not l.startswith(('Underfull','Package xeCJK Warning: Redefining CJKfamily'))],warnings[stem]
    pdfs[stem]={'pages':len(pages),'sha256':sha(P/(stem+'.pdf')),'external_link_file_targets_checked':len(remote),'text_outside_page':outside}

protected=Path('E:/硕士毕业论文/研究规划/第一篇小论文/secure distributed safety.tex')
assert sha(protected)=='0d59143f19ee62cdbb95f8207e47ec9cc481bedcda10b3a24398cd5bfa36b609'
result=dict(passed=True,date='2026-11-03',scope='full main-paper copyediting and layout; no new mathematical proof audit',
    old_release_files_verified=len(files),unchanged_display_blocks=blocks,formal_declarations_unchanged=declarations,
    presentation_or_copyediting_exceptions=sorted(copyedited),frozen_scientific_and_supporting_files=len(frozen),supplement_source_files_unchanged=len(supp),
    reference_entries=30,reference_metadata_and_doi_unchanged=True,new_experiments=False,
    original_first_paper_unchanged=True,documents=pdfs,warnings=warnings)
(P/'ecust_release_audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(result,ensure_ascii=False,indent=2))
