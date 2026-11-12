"""Validate the review packet and preservation boundaries."""
import csv
import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT=Path(__file__).resolve().parents[3]
PKG=ROOT/'reviews/fdi_replay_20261112'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    required=['README.md','research_digest.md','web_review_packet.md',
              'literature_reading_notes.md','problem_selection.md','project_evidence.md']
    for name in required:
        p=PKG/name
        assert p.exists() and p.stat().st_size>600,p
    loc=list(csv.DictReader((PKG/'sources/reading_locators.csv').open(encoding='utf-8-sig')))
    full=json.loads((PKG/'sources/fulltext_index.json').read_text(encoding='utf8'))
    meta=json.loads((PKG/'sources/metadata.json').read_text(encoding='utf8'))['records']
    refs=(PKG/'sources/references.bib').read_text(encoding='utf8')
    assert full['source_count']==28 and len(full['sources'])==28
    assert len(meta)==28 and len(loc)==28 and refs.count('@article{')+refs.count('@inproceedings{')==28
    for row in loc:
        key=row['key'];s=full['sources'][key]
        assert row['doi'].lower()==s['doi'].lower()==meta[key]['metadata']['DOI'].lower(),key
        assert meta[key]['status']=='VERIFIED_METADATA',key
        assert row['reading_locators'] and row['fulltext_pages'],key
        p=ROOT/'literature_review/fdi_replay_reread_20261112'/(key+'.pdf')
        assert p.exists() and sha(p)==s['sha256'],key
    assert sum(x['pdf_pages'] for x in full['sources'].values())==327
    assert [k for k,v in full['sources'].items() if v.get('new_user_supplied_this_round')]==['yu2025','xing2025']
    assert not any(v.get('downloaded_by_agent_this_round',False) for v in full['sources'].values())
    prior=json.loads((PKG/'sources/prior_result_index.json').read_text(encoding='utf8'))
    assert len(prior)==10
    for item in prior:
        assert sha(ROOT/item['original'])==item['sha256'],item['original']
        copied=PKG/item['preserved_copy']
        assert copied.exists(),item['original']
        assert sha(copied)==item.get('preserved_copy_sha256',item['sha256']),item['original']
    for name in ['replay','reflection','temporal_fdi','covariance_floor','correlated_window',
                 'leaky','gaussian_complement','matrix_order','qian_moment','conditional_reference']:
        hits=list((PKG/'evidence').rglob(name+'.json'));assert hits,name
        for p in hits:
            result=json.loads(p.read_text(encoding='utf8'));assert 'status' in result,name
    # Validate links in authored guide documents; archived prior reports intentionally retain original links.
    broken=[]
    for name in required:
        p=PKG/name;text=p.read_text(encoding='utf8')
        for target in re.findall(r'\]\(([^)]+)\)',text):
            if target.startswith(('https://','http://','#')):continue
            local=target.split('#')[0]
            if local and not (p.parent/local).exists() and local!='sources/delivery_validation.json':
                broken.append((name,local))
    assert not broken,broken
    # Make sure original paper snapshots and simulation sources were untouched.
    changed=subprocess.check_output(['git','diff','--name-only','HEAD'],cwd=ROOT,text=True,encoding='utf8').splitlines()
    assert not any(p.startswith(('papers/','simulation/')) for p in changed),changed
    public_files=[p for p in PKG.rglob('*') if p.is_file()]
    assert not [p for p in public_files if p.suffix.lower()=='.pdf']
    sensitive=[r'C:[\\/]Users[\\/]',r'Zotero/storage/[A-Z0-9]{8}',r'github_pat_[A-Za-z0-9_]{25,}',r'gh[pousr]_[A-Za-z0-9]{25,}']
    for p in public_files:
        if p.suffix.lower() not in {'.md','.json','.csv','.bib','.py'}:continue
        text=p.read_text(encoding='utf-8-sig')
        assert not any(re.search(pattern,text) for pattern in sensitive),p
    report={'passed':True,'primary_reading_reports':required,'primary_fulltext_sources':28,
            'source_pdf_pages':327,'all_doi_metadata_verified':True,'all_source_hashes_verified':True,
            'prior_result_snapshots_verified':len(prior),'standalone_check_cases':10,
            'new_user_supplied_fulltexts':['yu2025','xing2025'],'new_agent_downloaded_pdfs':0,
            'third_party_fulltexts_in_package':False,'original_papers_unchanged':True,
            'original_simulation_sources_unchanged':True,'unverified_direct_fulltext_gaps':0}
    (PKG/'sources/delivery_validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps(report,ensure_ascii=False,indent=2))


if __name__=='__main__':
    main()
