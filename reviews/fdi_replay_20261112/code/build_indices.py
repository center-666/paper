"""Build a self-contained locator CSV and BibTeX from checked Crossref records."""
import csv
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
PUB=ROOT/'reviews/fdi_replay_20261112'

LOCATORS={
 'yu2025':('IEEE Signal Processing Letters 32:1930-1934','pp.1931-34, detector (2)-(3), reflection (4), node-based strategy (5)-(6), dynamic encoding (7), Theorems 1-3.','direct state-estimate packet attack; stronger than historical-packet-only attacker'),
 'xing2025':('IEEE Transactions on Information Forensics and Security 20:4541-4550','pp.4542-44 system/attack (6)-(9), Lemmas 1-3, Theorem 1; pp.4545-47 optimal/suboptimal covariance attacks, Theorems 1-2.','historical innovation manipulation, not a replay-only state packet'),
 'yang2014':('Automatica 50(8):2070-2076','pp.2071-72, Eqs.(1)-(11), gain (9); pp.2073-76, Assumptions 2-3, Lemma 7, Theorem 1, LMI bound.','shared-state stochastic Bernoulli activation; honest operation'),
 'yang2019':('Automatica 102:34-44','pp.36-37, Sec.2.1-2.3 Eqs.(3)-(13), random protector; pp.38-40, Theorems 3,6,7 and stability analysis.','direct FDI on estimate+innovation packets; protects distributed filter'),
 'zhou2022':('Automatica 138:110151','PDF pp.2-3, Sec.2 Eqs.(3)-(9); p.4 Theorem 1 (rank/nullspace); pp.4-6 Eqs.(20)-(40), stochastic protector, Theorems 2-3.','estimate-packet FDI; local measurement residual; random exponential gate'),
 'wen2018':('Digital Signal Processing 78:92-97','PDF pp.93-95, Sec.2-3 Eqs.(8)-(18), K-means state/covariance clusters, Eqs.(11),(14)-(16), Algorithm 1; pp.95-96 experiments.','neighbors exchange estimate and covariance; clustered trusted-set fusion'),
 'zhang2024':('Electronics Letters 60(6), e13156','PDF pp.1-3, model (1)-(4), Assumption A1, temporal reference (5)-(6), adaptive GMCC (7)-(8), threshold test (10), simulations.','diffusion RLS parameter estimation; not dynamic state estimate cache'),
 'peng2025':('IEEE Sensors Journal 25(15):29966-29981','pp.29967-70 model/BCMCC; pp.29971-73 spatial-temporal reference (22)-(26), threshold and adaptive kernel (29)-(37); pp.29975 complexity.','diffusion parameter estimation, input noise and impulsive interference'),
 'guzey2026':('Simulation Modelling Practice and Theory 152:103318','pp.103321-24 NIS/LLR (14)-(21), hysteresis, WLS/IRLS (26)-(33); pp.103324-25 Assumptions 3.1-3.3, Lemma 3.1, Theorem 3.2; pp.103326-28 Monte Carlo and ablations.','SISMF bearing tracking; centralized fusion center; hold-last Replay'),
 'wang2026':('IEEE TASE 23:2091-2099','pp.2092-94 Eqs.(1)-(8), Assumptions 1-3, Algorithm 1; pp.2095-96 Theorems 1-4; pp.2097-99 simulation.','stacked local measurements, sparse sensor attacks, adaptive saturation'),
 'zhang2026':('Journal of the Franklin Institute 363(13):108914','PDF pp.2-4 Eqs.(1)-(7), residual exchange/map, detector (6); pp.6-8 Theorems 2-4, bias vs real-time attacker/watermark.','neighbor residual packets, heterogeneous measurement dimensions'),
 'ge2026':('IEEE Transactions on Cybernetics, 1-13','pp.2-4 attack model (6)-(9), Assumptions 1-2, Lemma 1, Theorem 1; pp.5-8 Theorems 1-3, covariance relaxation and PGD; pp.9-12 experiments.','historical innovations, KLD stealth and attack synthesis'),
 'su2022':('IEEE Systems Journal 16(4):5720-5728','pp.5721-23 replay threat, tag assumptions and detection; pp.5723-27 distributed observer stability; p.5722 Remark 2 on unmodifiable labels.','multisensor measurement Replay; intact packet labels assumed'),
 'huang2024':('IEEE Transactions on Cybernetics 54(6):3526-3539','pp.3528-30 model, periodic measurement Replay and residual-KL; pp.3530-34 stable-system covariance; pp.3531-32 unstable-system detection conditions/Theorems 5-7.','measurement-history Replay, not state-estimate-packet Replay'),
 'nozal2022':('IEEE Control Systems Letters 6:506-511','pp.507-09 multi-hop observable subspaces, trust regions and hysteresis; pp.509-10 CQLF/LMI robust observer design; pp.510-11 HIL.','multi-hop subspace trust and recovery'),
 'qian2023':('IEEE Transactions on Automatic Control 68(10):6361-6368','pp.6362-64 event-conditioned update, Assumption 2, Lemmas 1-2, Theorems 1-2; p.6368 Appendix C.','event-triggered filtering without an attack model'),
 'qiu2019':('IEEE Transactions on Industrial Electronics 66(3):2111-2121','pp.2112-14 event-triggering error bound (2)-(7), residual/filter setup (8)-(14); pp.2116-17 LMIs (19)-(21), Algorithm 1.','event-triggered fault detection; time-varying threshold'),
 'liang2023':('IEEE Transactions on Instrumentation and Measurement 72:3520111','PDF pp.2-4 system/event rule (12)-(18), UIO Theorem 1; pp.5-7 Theorem 2, Algorithm 1, H-infinity tradeoff.','continuous-time MAS, held neighbor outputs and UIO detection'),
 'mitra_aoi':('IEEE Transactions on Automatic Control 67(12):6349-6365','Author manuscript Sec.VI, Algorithm 2: freshness-index Byzantine extension, adversarial time-stamp and trimming.','time-varying graph, AoI can be falsified'),
 'liang2019':('Information Fusion 46:44-50','PDF pp.50-55, trust-based distributed Kalman update, trust/fusion rules, attacks and simulation.','trust-weighted neighbor fusion'),
 'mitra2019':('Automatica 108:108487','Author manuscript Theorems 1-7: f-local Byzantine resilience, unstable eigenmode detectability, MEDAG/source sets and robust graph conditions.','arbitrary Byzantine node behavior; stronger attacker than link payload substitution'),
 'he2019':('2019 IEEE CDC, 5344-5349','Author manuscript Assumptions 1-4; sparse/local observation; SIU update (5)-(10); Theorem 1 and observation redundancy condition.','unstable dynamics, sensor attacks, consensus and saturated innovation'),
 'chen2019':('IEEE Transactions on Automatic Control 64(9):3772-3779','Sec.II model and sparse support; Proposition 1 and subsequent correctable-error/sparse-observability propositions.','sensor observation errors, finite-horizon error correction'),
 'fawzi2014':('IEEE Transactions on Automatic Control 59(6):1454-1467','Secure estimation/control conditions; sparse observability and adversarial reconstruction results.','foundational adversarial estimation/decoding conditions'),
 'wangyu2026':('Scientific Reports, article in press','System model, trusted connected dominating set, TRDE Algorithm 1, Theorems 1-2, secure-node assumptions and simulation.','nonlinear parameter estimation; explicit trusted infrastructure'),
 'solowjow2020':('2018 Annual American Control Conference, 6506-6512','Exact/approximate inter-communication-time learning triggers, Theorems 1-2 and Hoeffding-bound event threshold.','communication-interval statistics for model learning, not attacks'),
 'tunga2018':('2018 Annual American Control Conference, 1752-1757','Sec.II static chi-square/CUSUM; Sec.III Theorem 1 window false-alarm tuning; Sec.IV worst-case steady-state deviation, Propositions 1-2.','single-system sensor residual tests; strong sequential baseline'),
 'berman2014':('2014 IEEE/ION Position, Location and Navigation Symposium, 1008-1013','Secs.I-III innovation outlier gate and rejection-induced behavior; Sec.IV single-sided gate and multi-filter recovery.','Kalman measurement outlier recovery, not network Replay'),
}


def bib(key,meta):
 authors=meta.get('author') or []
 author=' and '.join((a.get('family','')+', '+a.get('given','')).strip(', ') for a in authors)
 title=(meta.get('title') or [''])[0]
 date=meta.get('published',{}).get('date-parts',[[None]])[0];year=date[0]
 journal=(meta.get('container-title') or [''])[0]
 fields={'author':author,'title':title,'year':year,'journal':journal,'volume':meta.get('volume'),'number':meta.get('issue'),'pages':meta.get('page'),'doi':meta.get('DOI'),'url':('https://doi.org/'+meta['DOI']) if meta.get('DOI') else None}
 kind='inproceedings' if key in {'he2019','solowjow2020','tunga2018','berman2014'} else 'article'
 if kind=='inproceedings':fields['booktitle']=fields.pop('journal')
 body=',\n'.join('  '+k+' = {'+str(v)+'}' for k,v in fields.items() if v not in (None,''))
 return '@'+kind+'{'+key+',\n'+body+'\n}'


def main():
 pub=PUB/'sources';meta=json.loads((pub/'metadata.json').read_text(encoding='utf8'))['records'];index=json.loads((pub/'fulltext_index.json').read_text(encoding='utf8'))['sources']
 records=[];bibitems=[]
 for key,row in index.items():
  m=meta[key].get('metadata',{})
  loc,scope=LOCATORS[key][1:]
  records.append({'key':key,'title':(m.get('title') or [''])[0],'doi':row['doi'],'verified_metadata':meta[key]['status'],'fulltext_pages':row['pdf_pages'],'reading_locators':loc,'scope_warning':scope,'source_sha256':row['sha256']})
  bibitems.append(bib(key,m))
 with (pub/'reading_locators.csv').open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(records[0]));w.writeheader();w.writerows(records)
 (pub/'references.bib').write_text('\n\n'.join(bibitems)+'\n',encoding='utf8')
 # Publish only workspace-relative ignored paths, never absolute home paths.
 for key,row in index.items():
  row['local_preserved_pdf']='literature_review/fdi_replay_reread_20261112/'+key+'.pdf'
  row.pop('local_pdf',None);row.pop('source_original_path',None)
 (pub/'fulltext_index.json').write_text(json.dumps({'source_count':len(index),'sources':index,'third_party_pdfs_not_in_public_package':True,'user_supplied_pdfs':['yu2025','xing2025']},ensure_ascii=False,indent=2),encoding='utf8')
 print('INDEXED',len(records),'BIBTEX',len(bibitems))


if __name__=='__main__':main()
