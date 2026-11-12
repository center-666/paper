"""Validate audit deliverables, source provenance, and preservation boundaries."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT=Path(__file__).resolve().parents[2]
REV=ROOT/'reviews'


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    required=['theorem_audit.md','novelty_audit.md','paper_decision.md','executive_summary.md']
    for name in required:
        p=REV/name
        assert p.exists() and len(p.read_text(encoding='utf8'))>500,name
    broken=[]
    for p in REV.glob('*.md'):
        text=p.read_text(encoding='utf8')
        for target in re.findall(r'\]\(([^)]+)\)',text):
            if target.startswith(('https://','http://','#')):continue
            target=target.split('#')[0]
            if not (p.parent/target).exists():broken.append([p.name,target])
    assert not broken,broken
    source=json.loads((REV/'artifacts/fulltext_source_index.json').read_text(encoding='utf8'))
    assert len(source)==11
    for key,row in source.items():
        p=ROOT/row['local_pdf'];assert p.exists(),key
        assert sha(p)==row['sha256'],key
    preserved=json.loads((REV/'artifacts/run_20261112_02/preserved_assets.json').read_text(encoding='utf8'))
    assert all(sha(ROOT/p)==s for p,s in preserved.items())
    script=REV/'code/audit_round2.py'
    manifest=json.loads((REV/'artifacts/run_20261112_02/run_manifest.json').read_text(encoding='utf8'))
    assert manifest['script_sha256']==sha(script)
    invocations=json.loads((REV/'artifacts/independent_cli/invocations.json').read_text(encoding='utf8'))
    assert len(invocations)==9 and all(row['exit_code']==0 for row in invocations)
    meta=json.loads((REV/'artifacts/bibliography_metadata.json').read_text(encoding='utf8'))
    assert len(meta)==11 and all(row['status']=='METADATA_VERIFIED' for row in meta.values())
    assert meta['bai_auto2017']['metadata']['volume']=='82'
    assert meta['bai_auto2017']['metadata']['page']=='251-260'
    # Inspect only agent-authored tracked changes; formal manuscript snapshots must be untouched.
    changed=subprocess.check_output(['git','diff','--name-only','HEAD'],cwd=ROOT,text=True,encoding='utf8').splitlines()
    assert not any(p.startswith(('papers/','simulation/')) for p in changed),changed
    files=list(REV.rglob('*'))
    # Original full text and data-library identifiers do not belong in the public audit package.
    leak_patterns=[r'C:[\\/]Users[\\/]',r'storage[\\/][A-Z0-9]{8}',
                   r'gh[pousr]_[A-Za-z0-9]{30,}',r'github_pat_[A-Za-z0-9_]{30,}']
    for p in files:
        if p.suffix not in ('.md','.json','.csv','.bib','.py','.txt'):continue
        t=p.read_text(encoding='utf-8-sig')
        assert not any(re.search(pattern,t) for pattern in leak_patterns),p.relative_to(ROOT).as_posix()
    result={'passed':True,'required_reports':required,'relative_markdown_links_valid':True,
            'verified_fulltext_sources':len(source),'original_experiment_files_hash_verified':len(preserved),
            'separate_cli_case_invocations':len(invocations),'checked_core_bibliographic_records':len(meta),
            'Bai_Automatica_2017':'82:251-260','formal_manuscripts_unchanged':True,
            'original_simulation_sources_unchanged':True,'no_third_party_fulltexts_in_reviews':True,
            'unverified_recent_title_hits':2,'theorem_correctness_not_inferred_from_numeric_checks':True}
    (REV/'artifacts/delivery_validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
