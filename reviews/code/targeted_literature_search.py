"""Narrow bibliographic search for the audited theorem; not a novelty oracle."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
from urllib.parse import urlencode

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'literature_review/round2_20261112/search'
QUERIES=[
 'stochastic event triggered estimation stealthy attacks performance bounds',
 'randomized event triggered estimation total variation stealthiness damage',
 'event triggered state estimation attack causal information history',
 'stochastic event estimation compromised sensors detectability performance',
]


def one(item):
 i,q=item;url='https://api.crossref.org/works?'+urlencode({'query':q,'rows':12,
 'filter':'from-pub-date:2024-01-01,until-pub-date:2026-11-12',
 'select':'DOI,title,author,published,container-title,volume,issue,page,URL'})
 p=OUT/f'q{i}.json';r=subprocess.run(['curl.exe','--silent','--show-error','-L','--max-time','25',
 '-o',str(p),'-w','%{http_code} %{url_effective}',url],capture_output=True,text=True)
 row={'query':q,'url':url,'response':r.stdout,'exit_code':r.returncode}
 try:
  items=json.loads(p.read_text(encoding='utf8'))['message']['items']
  row['results']=[{k:v.get(k) for k in ('DOI','title','published','container-title')} for v in items]
 except Exception as e:row['error']=str(e)
 return row


if __name__=='__main__':
 OUT.mkdir(parents=True,exist_ok=False)
 results=list(ThreadPoolExecutor(max_workers=2).map(one,enumerate(QUERIES,1)))
 dest=ROOT/'reviews/artifacts/targeted_search_index.json'
 dest.write_text(json.dumps({'accessed_utc':datetime.now(timezone.utc).isoformat(),
  'publication_cutoff':'2026-11-12','scope':'four narrow Crossref queries; not exhaustive; title hits are not theorem evidence',
  'queries':results},ensure_ascii=False,indent=2),encoding='utf8')
 for r in results:
  print('QUERY',r['query'],r.get('error',''))
  for v in r.get('results',[]):print(v['DOI'],v['title'])
