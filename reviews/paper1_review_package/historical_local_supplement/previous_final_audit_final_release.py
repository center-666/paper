"""Check release consistency; mathematical review reports are separate."""
from pathlib import Path
import hashlib,json,re
P=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
MATH=re.compile(r'\\begin\{(equation\*?|align\*?|gather\*?|multline\*?)\}.*?\\end\{\1\}|\\\[.*?\\\]',re.S)
DECL=re.compile(r'\\begin\{(theorem|lemma|proposition|remark|corollary)\}.*?\\end\{\1\}',re.S)
def strip_title(s):
    return re.sub(r'(\\begin\{(?:theorem|lemma|proposition|remark|corollary)\})(?:\[[^\]]*\])?',r'\1',s)
def bib(s):
    s=re.sub(r'\\paperdoi\{([^}]+)\}',lambda m:r'\url{https://doi.org/'+m[1]+'}',s)
    s=s.split(r'\end{thebibliography}')[0]
    return {m[1]:re.sub(r'\s+','',m[2]) for m in re.finditer(r'\\bibitem\{([^}]+)\}(.*?)(?=\\bibitem\{|\Z)',s,re.S)}
def main():
    baseline=json.loads((P/'final_scientific_baseline.json').read_text(encoding='utf-8'))
    inp=json.loads((P/'final_input_manifest.json').read_text(encoding='utf-8'))
    old=Path(inp['previous_directory']); previous=0
    if old.is_dir():
        for name,digest in inp['input_files'].items():assert sha(old/name)==digest,name
        previous=len(inp['input_files'])
    for name,digest in baseline['unchanged_files'].items():assert sha(P/name)==digest,name
    retained=declarations=0
    for name,row in baseline['tex'].items():
        s=(P/name).read_text(encoding='utf-8')
        actual=[m[0] for m in MATH.finditer(s)]
        expected=row['math']
        if name=='vector_proof.tex':
            changed=[x for x in expected if r'm_k^+=m_k^-+K_hz,\qquad' in x]
            assert len(changed)==1
            kept=[x for x in expected if x not in changed]
            extras=[x for x in actual if x not in kept]
            assert len(extras)==2,extras
            assert any(r'\widetilde y_k&=m+z' in x for x in extras)
            assert any(r'\mu_{\rm pre}(d\zeta)' in x for x in extras)
            assert [x for x in actual if x in kept]==kept
            retained+=len(kept)
        else:
            assert actual==expected,name
            retained+=len(expected)
        now=[strip_title(m[0]) for m in DECL.finditer(s)]
        assert now==[strip_title(x) for x in row['declarations']],name
        declarations+=len(now)
        assert re.findall(r'\\label\{([^}]+)\}',s)==row['labels'],name
    assert bib((P/'references.tex').read_text(encoding='utf-8'))==bib(baseline['reference_source'])
    def tikz(s):return re.search(r'\\begin\{tikzpicture\}.*?\\end\{tikzpicture\}',s,re.S)[0]
    assert tikz((P/'protocol-figure.tex').read_text(encoding='utf-8'))==tikz((P/'figures/fig01_protocol.tex').read_text(encoding='utf-8'))
    build=json.loads((P/'build_check.json').read_text(encoding='utf-8'))
    assert build['passed'] and not build['draft']
    warning={}
    for stem,row in build['documents'].items():
        assert sha(P/(stem+'.pdf'))==row['pdf_sha256']
        log=(P/(stem+'.log')).read_text(encoding='utf-8',errors='replace')
        warning[stem]=[l for l in log.splitlines() if re.search(r'Overfull|Underfull|LaTeX Warning|Package \S+ Warning|Missing character',l)]
        assert '??' not in (P/(stem+'_extracted.txt')).read_text(encoding='utf-8')
    errors={s:[x for x in lines if not x.startswith('Underfull')] for s,lines in warning.items()}
    assert not any(errors.values()),errors
    # Two mild bibliography spacing notes were visually checked on page 8.
    notes={s:[x for x in lines if x.startswith('Underfull')] for s,lines in warning.items()}
    assert notes=={'paper':['Underfull \\hbox (badness 1496) in paragraph at lines 94--98','Underfull \\hbox (badness 1102) in paragraph at lines 168--174'],'supplement':[],'graphical':[]},notes
    for name,digest in build['source_sha256'].items():assert sha(P/name)==digest,name
    replay=json.loads((P/'review_checks/joint_kernel_independent.json').read_text(encoding='utf-8'))
    assert replay['passed'] and replay['code_sha256']==sha(P/'review_checks/joint_kernel_independent.py')
    result=dict(passed=True,date='2026-10-21',previous_files_verified=previous,unchanged_files=len(baseline['unchanged_files']),unchanged_display_blocks=retained,declaration_bodies_preserved=declarations,proof_display_expansions=1,added_pre_history_integral=1,core_theorem_conditions_and_conclusion_unchanged=True,experiment_code_and_data_unchanged=True,references=30,reference_metadata_unchanged=True,new_experiments=False,existing_scalar_diagnostic_replayed=True,formal_verification=False,pages={s:r['pages'] for s,r in build['documents'].items()},pdf_sha256={s:r['pdf_sha256'] for s,r in build['documents'].items()},warnings=warning)
    (P/'final_release_audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
