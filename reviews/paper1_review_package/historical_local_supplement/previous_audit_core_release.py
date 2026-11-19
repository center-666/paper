"""Check preserved scientific results and the core-proof manuscript revision."""
from pathlib import Path
from collections import Counter
import hashlib,json,re

P=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
PAT=re.compile(r'\\begin\{(equation\*?|align\*?|gather\*?|multline\*?)\}.*?\\end\{\1\}|\\\[.*?\\\]',re.S)
def walk(name,seen=None):
    seen=set() if seen is None else seen
    if name in seen:return []
    seen.add(name);out=[name]
    for t in re.findall(r'\\input\{([^}]+)\}',(P/name).read_text(encoding='utf-8')):
        out+=walk(t if t.endswith('.tex') else t+'.tex',seen)
    return out
def bib(s):
    s=s.split(r'\end{thebibliography}')[0]
    return {m[1]:re.sub(r'\s+','',m[2]) for m in re.finditer(r'\\bibitem\{([^}]+)\}(.*?)(?=\\bibitem\{|\Z)',s,re.S)}

def main():
    inp=json.loads((P/'core_input_manifest.json').read_text(encoding='utf-8'))
    old=Path(inp['previous_directory']);old_n=0
    if old.is_dir():
        for f,h in inp['input_files'].items():assert sha(old/f)==h,f
        old_n=len(inp['input_files'])
    base=json.loads((P/'copyedit_baseline.json').read_text(encoding='utf-8'))
    core=re.findall(r'\\begin\{theorem\}.*?\\end\{theorem\}',(P/'theory.tex').read_text(encoding='utf-8'),re.S)
    assert len(core)==1 and hashlib.sha256(core[0].encode()).hexdigest()==base['core_theorem_sha256']
    for f,h in base['unchanged_data_code'].items():
        if f not in ['references.tex','references_additions.tex']:assert sha(P/f)==h,f
    previous_bib=bib((P/'provenance/references.tex').read_text(encoding='utf-8'))
    current_bib=bib((P/'references.tex').read_text(encoding='utf-8'))
    assert len(previous_bib)==28 and len(current_bib)==30
    for key,val in previous_bib.items():assert current_bib[key]==val,key
    originals=['theory.tex','record_design.tex','finite_sample.tex','vector_proof.tex','scalar_counterexample.tex',
        'validation_appendix.tex','numerical.tex','statistical_extension.tex','statistical_numerical.tex','label_refinement.tex']
    blocks=Counter(re.sub(r'\s+','',m.group()) for f in originals for m in PAT.finditer((P/f).read_text(encoding='utf-8')))
    assert blocks==Counter(base['display_math']) and sum(blocks.values())==62
    build=json.loads((P/'build_check.json').read_text(encoding='utf-8'));assert build['passed']
    for f,h in build['source_sha256'].items():assert sha(P/f)==h,f
    warnings={}
    for stem,row in build['documents'].items():
        assert sha(P/(stem+'.pdf'))==row['pdf_sha256']
        log=(P/(stem+'.log')).read_text(encoding='utf-8',errors='replace')
        warnings[stem]=[s for s in log.splitlines() if re.search(r'Overfull|Underfull|LaTeX Warning|Package \S+ Warning|Missing character',s)]
    assert not any(warnings.values()),warnings
    record=json.loads((P/'record_study/results.json').read_text(encoding='utf-8'))
    assert record['passed'] and sha(P/'record_study/mh_record_conditions.py')==record['script_sha256']
    for f,h in record['source_sha256'].items():
        target=P/'provenance'/f if f=='theory.tex' else P/f
        assert sha(target)==h,f
    inputs=sorted(set(walk('paper.tex')+walk('supplement.tex')+walk('graphical.tex')))
    labels=[m for f in inputs for m in re.findall(r'\\label\{([^}]+)\}',(P/f).read_text(encoding='utf-8'))]
    assert len(labels)==len(set(labels))
    result=dict(passed=True,date='2026-10-20',pages={s:r['pages'] for s,r in build['documents'].items()},
        core_theorem_unchanged=True,original_62_math_blocks_unchanged=True,original_data_code_unchanged=True,
        original_28_reference_entries_preserved=True,references=30,new_metadata_only_references=2,
        previous_files_verified=old_n,warnings=warnings,new_simulations=False,formal_verification=False,
        unresolved_fulltext_neighbors=['10.1002/rnc.5967','10.1109/JAS.2025.125381'],
        numerical_provenance_note='Stored experiment theory source is preserved in provenance/theory.tex; values unchanged.',
        pdf_sha256={s:r['pdf_sha256'] for s,r in build['documents'].items()},
        source_sha256={f:sha(P/f) for f in inputs})
    (P/'core_release_audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if not k.endswith('sha256')},ensure_ascii=True,indent=2))

if __name__=='__main__':main()
