from __future__ import annotations
from dataclasses import asdict
from pathlib import Path
import json
import time
import subprocess
import numpy as np

from .authorization_guard import require, bindings
from .config_loader import public_model
from .online_proposal import OnlineInput, propose
from .scenario_builder import ScenarioBuilder
from .offline_evaluator import evaluate
from .storage import write, digest, persist_proposal, manifest, verify_manifest
from .execution_state import Checkpoint, mark, fail, require_resumable_or_complete
from .statistics_reporter import summarize, resample_indices
from .independent_statistics import compare as independent_compare
from .integrity_checker import validate_rows


class BatchRunner:
    def __init__(self,config,receipt,out,*,resume=False):
        self.config=config; self.receipt=receipt; self.out=Path(out).resolve(); self.resume=resume

    def run(self):
        # All authorization checks precede directory creation and model/data generation.
        require(self.config,self.receipt)
        if self.out.exists() and not self.resume: raise FileExistsError('E3 Run already exists; no overwrite')
        if self.resume and not self.out.is_dir(): raise FileNotFoundError('resume requires original Run')
        identity={'run_id':self.out.name,'authorization_id':self.receipt.authorization_id,
                  'owner':self.receipt.owner,'authorization_file_sha256':self.receipt.file_sha256,
                  'bindings':dict(self.receipt.bindings)}
        metadata={**identity,'experiment_config_sha256':self.config.config_sha256,
                  'E2_dependency_bindings':dict(self.config.dependencies),'E3_only':True,
                  'environment_fingerprint':dict(self.config.shared.environment_fingerprint)}
        self.out.mkdir(parents=True,exist_ok=True)
        context={'stage':'initialize','group':None,'seed':None,'event':None,'age':None,'method':None}
        started=time.perf_counter()
        try:
            if self.resume:
                require_resumable_or_complete(self.out,self.config)
                if json.loads((self.out/'config.json').read_text())!=metadata:
                    raise ValueError('resume authorization/config differs')
            else:
                write(self.out/'config.json',metadata)
                source={'git_head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=self.config.root if hasattr(self.config,'root') else Path.cwd(),text=True).strip(),
                        'git_branch':subprocess.check_output(['git','branch','--show-current'],cwd=self.config.root if hasattr(self.config,'root') else Path.cwd(),text=True).strip(),
                        'bindings':dict(self.receipt.bindings),'environment':dict(self.config.shared.environment_fingerprint),
                        'E2_dependency_sha256':dict(self.config.dependencies)}
                write(self.out/'source_environment.json',source)
                mark(self.out,'RUNNING',**context)
            cp=Checkpoint(self.out,identity)
            public=public_model(self.config); builder=ScenarioBuilder(self.config,public,self.receipt)
            all_rows=[]; batch_files=[]
            for group,seeds in [('normal',self.config.normal_seeds),('attack',self.config.attack_seeds)]:
                for batch_start in range(0,len(seeds),20):
                    require(self.config,self.receipt)
                    batch=seeds[batch_start:batch_start+20]; batch_rows=[]
                    for seed in batch:
                        context.update(stage='seed',group=group,seed=seed,event=None,age=None,method=None)
                        key=f'{group}:{seed}'; shard=self.out/'seeds'/f'{group}_{seed}.json'
                        if cp.done(key):
                            batch_rows.extend(json.loads(shard.read_text())['rows']); continue
                        ctx=builder.prepare(seed)
                        clean=builder.case(ctx,group)
                        persisted={}; files=[]
                        # All methods' healthy proposals are immutable before offline truth evaluation.
                        for method in self.config.methods:
                            context.update(stage='healthy_proposal',method=method)
                            online=OnlineInput(clean.z,public,self.config.shared.thresholds[method],method)
                            p=persist_proposal(self.out/'online'/f'{group}_{seed}_healthy_{method}.json',propose(online))
                            persisted[method]=p; files.append(p.path)
                        rows=[evaluate(clean.truth,persisted[m],persisted[m],cap=self.config.shared.protocol['U_common']) for m in self.config.methods]
                        if group=='attack':
                            for event in self.config.events:
                                for age in self.config.ages:
                                    context.update(stage='replay',event=list(event),age=age)
                                    case=builder.case(ctx,group,event,age)
                                    attack_proposals={}
                                    for method in self.config.methods:
                                        context.update(stage='attack_proposal',method=method)
                                        online=OnlineInput(case.z,public,self.config.shared.thresholds[method],method)
                                        p=persist_proposal(self.out/'online'/f'attack_{seed}_{event[0]}_{event[1]}_{age}_{method}.json',propose(online))
                                        attack_proposals[method]=p; files.append(p.path)
                                    for method in self.config.methods:
                                        context.update(stage='offline_evaluation',method=method)
                                        rows.append(evaluate(case.truth,attack_proposals[method],persisted[method],cap=self.config.shared.protocol['U_common']))
                        expected=3 if group=='normal' else 75
                        if len(rows)!=expected: raise ValueError('incomplete E3 seed, no replacement allowed')
                        validate_rows(self.config,rows)
                        context.update(stage='seed_write')
                        write(shard,{'group':group,'seed':seed,'rows':rows}); files.append(shard)
                        cp.complete(key,files); batch_rows.extend(rows)
                    path=self.out/f'{group}_batch_{batch_start//20:02d}.json'
                    write(path,{'group':group,'seeds':list(batch),'rows':batch_rows}); batch_files.append(path)
                    all_rows.extend(batch_rows)
            context.update(stage='statistics',seed=None,method=None,event=None,age=None)
            cp.verify()
            # Same saved seed rows, separate read path. Bootstrap uses a single shared seed-index array.
            from_disk=[]
            for path in sorted((self.out/'seeds').glob('*.json')):
                from_disk.extend(json.loads(path.read_text())['rows'])
            validate_rows(self.config,from_disk)
            require(self.config,self.receipt)
            indices=resample_indices(self.config.bootstrap_seed,len(self.config.attack_seeds),self.config.bootstrap_resamples)
            stats=summarize(self.config,all_rows,indices=indices,formal=True,receipt=self.receipt)
            disk_stats=summarize(self.config,from_disk,indices=indices,formal=True,receipt=self.receipt)
            if stats!=disk_stats: raise ValueError('E3 independent disk statistics differ')
            independent=independent_compare(self.config,from_disk,indices,stats)
            write(self.out/'statistics.json',stats)
            write(self.out/'statistics_audit.json',{'disk_recompute_match':True,'rows':len(from_disk),'seed_count':len(cp.completed),
                'batches':len(batch_files),'independent_vector_bootstrap_audit':independent,
                'wall_seconds_this_process':time.perf_counter()-started})
            context.update(stage='finalize')
            mark(self.out,'COMPLETED',**context)
            manifest(self.out,{'scope':'E3','E3_executed':True,'run_id':self.out.name})
            verify_manifest(self.out)
            return stats
        except BaseException as exc:
            fail(self.out,exc,context)
            raise
