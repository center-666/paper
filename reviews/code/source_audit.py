"""Fetch bibliographic metadata / extract local PDFs without changing originals.

python -X utf8 reviews/code/source_audit.py --metadata
python -X utf8 reviews/code/source_audit.py --extract
PDFs and extracted full text remain in the ignored literature_review tree.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[2]
LOCAL=ROOT/'literature_review/round2_20261112'
ART=ROOT/'reviews/artifacts'
REFS={
 'han2015':'10.1109/TAC.2015.2406975',
 'pasqualetti2013':'10.1109/TAC.2013.2266831',
 'bai_auto2017':'10.1016/j.automatica.2017.04.047',
 'bai_tac2017':'10.1109/TAC.2017.2714903',
 'guo2025':'10.1016/j.automatica.2025.112463',
 'vanstraalen2025':'10.1109/CDC57313.2025.11312582',
 'shang2022':'10.1109/TAC.2021.3071948',
 'cheng2020':'10.1109/TAC.2019.2956021',
 'xu2026':'10.1016/j.automatica.2026.113256',
 'deng2026':'10.1109/TIFS.2026.3676946',
 'shang2026':'10.1109/JAS.2025.125381'
}


def fetch(item):
 key,doi=item; p=LOCAL/(key+'_crossref_checked.json')
 url='https://api.crossref.org/works/'+doi
 r=subprocess.run(['curl.exe','--silent','--show-error','-L','--max-time','25',
                   '-o',str(p),'-w','%{http_code} %{url_effective}',url],
                   capture_output=True,text=True)
 row={'doi':doi,'requested_url':url,'response':r.stdout,'exit_code':r.returncode,
      'accessed_utc':datetime.now(timezone.utc).isoformat()}
 try:
  obj=json.loads(p.read_text(encoding='utf8'))['message']
  row.update(metadata={k:obj.get(k) for k in ('DOI','title','author','container-title','volume','issue','page','article-number','published')})
  row['status']='METADATA_VERIFIED'
 except Exception as exc:row.update(status='UNVERIFIED',error=str(exc))
 return key,row


def metadata():
 LOCAL.mkdir(parents=True,exist_ok=True); ART.mkdir(parents=True,exist_ok=True)
 p=ART/'bibliography_metadata.json'
 if p.exists():raise FileExistsError(p)
 result=dict(ThreadPoolExecutor(max_workers=3).map(fetch,REFS.items()))
 p.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
 for k,v in result.items():
  m=v.get('metadata',{}); print(k,v['status'],m.get('volume'),m.get('page'),m.get('title'))


def extract():
 from pypdf import PdfReader
 files={
 'han2015':'broad_topic_review_20261009/communication_security/Han2015_StochasticSchedule.pdf',
 'pasqualetti2013':'academic_expansion_20261015/pasqualetti2013.pdf',
 'bai_auto2017':'academic_expansion_20261015/bai2017.pdf',
 'guo2025':'direct_neighbors_fulltext_20261012/Guo2025_OptimalStochasticEventAttack.pdf',
 'vanstraalen2025':'trigger_adversarial_20261009/literature/vanStraalen2025_TimeFingerprint.pdf',
 'shang2022':'trigger_fulltext_review_20261010/Shang2022_WorstCase.pdf',
 'xu2026':'trigger_fulltext_review_20261010/Xu2026_StabilityBoundary.pdf',
 'cheng2020':'direct_neighbors_fulltext_20261012/Cheng2020_EventBasedStealthyAttack.pdf',
 'deng2026':'trigger_protocol_value_20261010/DengLi2026_Insider.pdf',
 'shang2026':'trigger_adversarial_20261009/root_neighbors/Shang2026_SingleDimEncryption.pdf'
 }
 base=next(ROOT.rglob('academic_expansion_20261015')).parent
 LOCAL.mkdir(parents=True,exist_ok=True); ART.mkdir(parents=True,exist_ok=True)
 result={}
 for k,rel in files.items():
  p=base/rel; reader=PdfReader(p)
  # Plain mode includes rotated text that layout mode may discard.
  texts=[page.extract_text() or '' for page in reader.pages]
  tp=LOCAL/(k+'_plainpages.txt')
  tp.write_text('\n'.join(f'\n===== PDF PAGE {i+1} =====\n'+t for i,t in enumerate(texts)),encoding='utf8')
  result[k]={'doi':REFS[k],'local_pdf':p.relative_to(ROOT).as_posix(),
             'pdf_pages':len(texts),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),
             'text_local_only':tp.relative_to(ROOT).as_posix(),
             'new_pdf_download_this_round':False}
  print(k,len(texts))
 dest=ART/'fulltext_source_index.json'
 if dest.exists():raise FileExistsError(dest)
 dest.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')


if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--metadata',action='store_true');ap.add_argument('--extract',action='store_true');a=ap.parse_args()
 if a.metadata:metadata()
 if a.extract:extract()
