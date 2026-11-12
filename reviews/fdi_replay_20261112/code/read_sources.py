"""Preserve and page-extract primary sources for the FDI/Replay review.

No Zotero database is written. Original attachments are read-only.
Third-party PDFs/full texts stay in the ignored literature_review directory.
"""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
from pypdf import PdfReader

ROOT=Path(__file__).resolve().parents[3]
LOCAL=ROOT/'literature_review/fdi_replay_reread_20261112'
PUBLIC=ROOT/'reviews/fdi_replay_20261112'
SOURCES={
 'yang2014':('10.1016/j.automatica.2014.05.025','Stochastic sensor activation for distributed state estimation'),
 'yang2019':('10.1016/j.automatica.2018.12.027','Distributed filtering under false data injection'),
 'zhou2022':('10.1016/j.automatica.2021.110151','Security analysis and defense strategy of distributed'),
 'wen2018':('10.1016/j.dsp.2018.03.002','Distributed Kalman filtering for robust state estimation'),
 'zhang2024':('10.1049/ell2.13156','Temporal convex combination-based secure'),
 'peng2025':('10.1109/JSEN.2025.3581080','Robust Secure Distributed Estimation Based on Statistical'),
 'guzey2026':('10.1016/j.simpat.2026.103318','Trust-aware distributed tracking using SISMF'),
 'wang2026':('10.1109/TASE.2025.3649048','Secure State Estimation Against Sparse Sensor'),
 'zhang2026':('10.1016/j.jfranklin.2026.108914','Distributed secure state estimation for cyber-physical systems A residual'),
 'ge2026':('10.1109/TCYB.2026.3721072','Optimal Stealthy Attack Design for Distributed Consensus'),
 'su2022':('10.1109/JSYST.2021.3123617','Distributed Secure State Estimation for Cyber-Physical Systems Against Replay'),
 'huang2024':('10.1109/TCYB.2022.3209820','Security Analysis of Distributed Consensus Filtering Under Replay'),
 'nozal2022':('10.1109/LCSYS.2021.3082309','Trust-Based Distributed State Estimation in the Presence'),
 'qian2023':('10.1109/TAC.2023.3234453','Event-Triggered Distributed State Estimation A Conditional'),
 'qiu2019':('10.1109/TIE.2018.2840510','A Tradeoff Approach for Optimal Event-Triggered Fault'),
 'liang2023':('10.1109/TIM.2022.3216674','Event-Triggered Distributed Attack Detection and Fault Diagnosis'),
}


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
 LOCAL.mkdir(parents=True,exist_ok=False)
 (PUBLIC/'sources').mkdir(parents=True,exist_ok=True)
 attachments=list((Path.home()/'Zotero/storage').rglob('*.pdf'))
 rows={}
 for key,(doi,term) in SOURCES.items():
  matches=[p for p in attachments if term.casefold() in p.name.casefold()]
  if not matches:
   rows[key]={'doi':doi,'status':'MISSING','search_term':term};print(key,'MISSING');continue
  # Prefer the previously cited attachment when duplicates exist, without deleting others.
  preferred={'guzey2026':'QLEYB5IL','zhou2022':'PBDILFDC','wang2026':'HD7VU3WL'}.get(key)
  chosen=next((p for p in matches if p.parent.name==preferred),matches[0])
  before=sha(chosen); dest=LOCAL/(key+'.pdf');shutil.copy2(chosen,dest)
  reader=PdfReader(dest)
  pages=[p.extract_text() or '' for p in reader.pages]
  layout=[p.extract_text(extraction_mode='layout') or '' for p in reader.pages]
  for name,texts in [('plain',pages),('layout',layout)]:
   (LOCAL/(key+'_'+name+'.txt')).write_text('\n'.join(f'\n===== PDF PAGE {i+1} =====\n'+t for i,t in enumerate(texts)),encoding='utf8')
  assert before==sha(chosen)==sha(dest)
  rows[key]={'doi':doi,'status':'FULLTEXT_AVAILABLE','pdf_pages':len(pages),
             'sha256':before,'local_preserved_pdf':dest.relative_to(ROOT).as_posix(),
             'original_attachment_modified':False,'downloaded_by_agent_this_round':False,
             'duplicate_attachments_seen':len(matches),
             'duplicate_hashes':list(dict.fromkeys(sha(p) for p in matches)),
             'extraction':'pypdf plain and layout, 1-based PDF page markers',
             'reading_status':'AVAILABLE; actual reading locators documented separately'}
  print(key,len(pages),before[:12],pages[0][:130].replace('\n',' '))
 # Existing local sources outside Zotero, with the same preservation policy.
 for key,path,doi in [
  ('liang2019',ROOT/'literature_review/pdf/Liang_2019_Trust_based_distributed_Kalman_filtering.pdf','10.1016/j.inffus.2018.04.002'),
  ('mitra_aoi',ROOT/'literature_review/pdf/Mitra_AoI.pdf','10.1109/TAC.2021.3130882')]:
  dest=LOCAL/(key+'.pdf');shutil.copy2(path,dest);reader=PdfReader(dest)
  for mode in ('plain','layout'):
   texts=[(p.extract_text(extraction_mode='layout') if mode=='layout' else p.extract_text()) or '' for p in reader.pages]
   (LOCAL/(key+'_'+mode+'.txt')).write_text('\n'.join(f'\n===== PDF PAGE {i+1} =====\n'+t for i,t in enumerate(texts)),encoding='utf8')
  rows[key]={'doi':doi,'status':'FULLTEXT_AVAILABLE','pdf_pages':len(reader.pages),'sha256':sha(dest),
             'local_preserved_pdf':dest.relative_to(ROOT).as_posix(),'original_attachment_modified':False,
             'downloaded_by_agent_this_round':False,'reading_status':'AVAILABLE; locators documented separately'}
  print(key,len(reader.pages))
 (PUBLIC/'sources/fulltext_index.json').write_text(json.dumps({'created_utc':datetime.now(timezone.utc).isoformat(),
 'sources':rows,'no_new_paper_downloads':True,'original_zotero_database_modified':False},ensure_ascii=False,indent=2),encoding='utf8')


if __name__=='__main__':main()
