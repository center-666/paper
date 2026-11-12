"""Check precise DOI metadata; keep failed requests distinct from absence."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[3]
PUB=ROOT/'reviews/fdi_replay_20261112/sources'
LOCAL=ROOT/'literature_review/fdi_replay_reread_20261112/metadata'


def one(item):
 key,doi=item;url='https://api.crossref.org/works/'+doi;p=LOCAL/(key+'.json')
 r=subprocess.run(['curl.exe','--silent','--show-error','-L','--max-time','25',
                   '-o',str(p),'-w','%{http_code}',url],capture_output=True,text=True)
 out={'doi':doi,'url':url,'response_status':r.stdout,'exit_code':r.returncode}
 try:
  m=json.loads(p.read_text(encoding='utf8'))['message']
  assert m['DOI'].casefold()==doi.casefold()
  out.update(status='VERIFIED_METADATA',metadata={k:m.get(k) for k in
      ('DOI','title','author','container-title','volume','issue','page','article-number','published','published-online','published-print')})
 except Exception as e:out.update(status='UNVERIFIED',error=str(e))
 return key,out


if __name__=='__main__':
 LOCAL.mkdir(parents=True,exist_ok=False)
 sources=json.loads((PUB/'fulltext_index.json').read_text(encoding='utf8'))['sources']
 dois={k:v['doi'] for k,v in sources.items()}
 dois.update(yu2025='10.1109/LSP.2025.3564886',xing2025='10.1109/TIFS.2025.3564063')
 result=dict(ThreadPoolExecutor(max_workers=2).map(one,dois.items()))
 (PUB/'metadata.json').write_text(json.dumps({'accessed_utc':datetime.now(timezone.utc).isoformat(),'records':result},ensure_ascii=False,indent=2),encoding='utf8')
 for key,row in result.items():
  m=row.get('metadata',{});print(key,row['status'],m.get('volume'),m.get('page'),m.get('title'))
