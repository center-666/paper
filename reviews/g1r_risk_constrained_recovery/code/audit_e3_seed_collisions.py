"""Read-only working-tree, archive, array, and reachable Git-blob E3 seed inventory."""
from __future__ import annotations
import argparse
import hashlib
import io
import json
from pathlib import Path
import re
import subprocess
import tarfile
import zipfile
import numpy as np

ROOT=Path(__file__).resolve().parents[3]
SEEDS=set(range(141440000,141440200))|set(range(141450000,141450200))|{141460000}
PAT=re.compile(rb'(?<!\d)(141440\d{3}|141450\d{3}|141460000)(?!\d)')
TEXT={'.json','.jsonl','.csv','.txt','.log','.md','.py','.ps1','.yaml','.yml','.toml','.ini','.tex','.sh'}
ARCHIVES=('.zip','.tar','.tar.gz','.tgz','.7z','.rar')


def inspect(roots, out):
    errors=[]; mentions=[]; collisions=[]; unresolved=[]; inventory=[]
    counts={'workspace_files':0,'numeric_arrays':0,'archives':0,'git_blobs':0}
    def record(seed,where,kind):
        if seed not in SEEDS: return
        item={'seed':seed,'location':where,'kind':kind}
        mentions.append(item)
        if kind=='CONSUMPTION_OR_UNRESOLVED_RESULT': collisions.append(item)
    def arrays(data,where):
        counts['numeric_arrays']+=1
        array=np.load(io.BytesIO(data),allow_pickle=False)
        def check(a,label):
            if a.dtype.kind not in 'iuf': return
            flat=np.asarray(a).ravel()
            chosen=flat[(flat>=141440000)&(flat<=141460000)]
            for s in set(map(int,chosen[np.isfinite(chosen)&(chosen==np.rint(chosen))])) & SEEDS:
                record(s,where+'::'+label,'CONSUMPTION_OR_UNRESOLVED_RESULT')
        if isinstance(array,np.lib.npyio.NpzFile):
            with array:
                for key in array.files: check(array[key],key)
        else: check(array,'array')
    def consume(data,name,where,depth=0):
        lower=name.lower(); suffix=Path(name).suffix.lower()
        # A trajectory may carry its seed only in its folder/member name.
        for seed in set(int(s) for s in PAT.findall(where.encode('utf-8'))) & SEEDS:
            record(seed,where,'CONSUMPTION_OR_UNRESOLVED_RESULT')
        if lower.endswith(('.npz','.npy')):
            arrays(data,where); return
        if lower.endswith(('.zip','.tar','.tar.gz','.tgz','.7z','.rar')):
            if depth>4:
                unresolved.append({'location':where,'reason':'archive nesting exceeds 4'}); return
            counts['archives']+=1
            if lower.endswith(('.7z','.rar')):
                unresolved.append({'location':where,'reason':'no safe native archive reader installed'}); return
            if lower.endswith('.zip'):
                with zipfile.ZipFile(io.BytesIO(data)) as a:
                    for info in a.infolist():
                        if info.is_dir(): continue
                        # Archive member content is fully read, no silent size exclusions.
                        consume(a.read(info),info.filename,where+'!/'+info.filename,depth+1)
            else:
                with tarfile.open(fileobj=io.BytesIO(data),mode='r:*') as a:
                    for info in a:
                        if not info.isfile(): continue
                        with a.extractfile(info) as f: consume(f.read(),info.name,where+'!/'+info.name,depth+1)
            return
        hits=set(int(s) for s in PAT.findall(data)) & SEEDS
        if not hits: return
        if suffix in {'.md','.py','.ps1','.sh','.tex'}:
            kind='DECLARATION_CODE_OR_DOCUMENT'
        elif lower.endswith('protocol_v2.json'):
            kind='DECLARATION_PROTOCOL_RESERVATION'
        elif 'g1r_e3_seed_audit_' in where or 'e3_preparation_config' in where:
            kind='DECLARATION_SEED_AUDIT_OR_CONFIGURATION'
        else: kind='CONSUMPTION_OR_UNRESOLVED_RESULT'
        for seed in hits: record(seed,where,kind)
    for root in roots:
        listing=subprocess.check_output(['rg','--files','--hidden','--no-ignore','-g','!.git/**','-g','!**/.venv/**','-g','!**/__pycache__/**','.'],cwd=root,text=True,encoding='utf-8').splitlines()
        for rel in listing:
            p=root/rel; counts['workspace_files']+=1
            # Explicitly inventory both tracked and ignored/untracked assets.
            if p.suffix.lower() not in TEXT|{'.npz','.npy'} and not p.name.lower().endswith(ARCHIVES): continue
            where=str(p.resolve())
            try:
                raw=p.read_bytes(); inventory.append({'location':where,'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)})
                consume(raw,p.name,where)
            except Exception as exc: errors.append({'location':where,'error':repr(exc)})
    # All reachable objects, not only current main/isolated HEAD snapshots.
    objects=subprocess.check_output(['git','rev-list','--objects','--all'],cwd=ROOT,text=True,encoding='utf-8').splitlines()
    selected=[]
    for line in objects:
        oid,_,name=line.partition(' ')
        if name and (Path(name).suffix.lower() in TEXT|{'.npz','.npy'} or name.lower().endswith(ARCHIVES)):
            selected.append((oid,name))
    proc=subprocess.Popen(['git','cat-file','--batch'],cwd=ROOT,stdin=subprocess.PIPE,stdout=subprocess.PIPE)
    # Sequential streaming prevents materializing the full Git history in RAM.
    for oid,name in selected:
        proc.stdin.write((oid+'\n').encode()); proc.stdin.flush()
        header=proc.stdout.readline().decode().strip().split()
        if len(header)!=3:
            errors.append({'location':oid,'error':'invalid Git object header'}); break
        _,kind,size=header; size=int(size); data=proc.stdout.read(size); proc.stdout.read(1)
        if kind!='blob': continue
        counts['git_blobs']+=1
        try: consume(data,name,'git:'+oid+':'+name)
        except Exception as exc: errors.append({'location':'git:'+oid+':'+name,'error':repr(exc)})
    proc.stdin.close(); proc.wait()
    out.mkdir(parents=True,exist_ok=False)
    (out/'inventory.json').write_bytes((json.dumps(inventory,sort_keys=True)+'\n').encode())
    summary={'status':'PASS_NO_CONSUMPTION_IN_SCANNED_SCOPE' if not collisions and not errors and not unresolved else 'STOP_INCOMPLETE_OR_COLLISION',
        'collision_count':len(collisions),'unresolved_count':len(unresolved),'scan_errors':errors,
        'collisions':collisions,'unresolved':unresolved,'mentions':mentions,'counts':counts,
        'roots':[str(r) for r in roots],'reachable_git_blobs_scanned':True,
        'excluded': ['.git internal storage (reachable blobs scanned separately)','.venv','__pycache__','non-research external drives/backups'],
        'per_seed':[{'seed':s,'group':'bootstrap' if s==141460000 else ('normal' if s<141450000 else 'attack'),
                     'consumption_hits':sum(h['seed']==s for h in collisions)} for s in sorted(SEEDS)],
        'inventory_sha256':hashlib.sha256((out/'inventory.json').read_bytes()).hexdigest(),
        'new_trajectories':0,'formal_E3_executed':False}
    (out/'summary.json').write_bytes((json.dumps(summary,sort_keys=True,indent=2)+'\n').encode())
    print(json.dumps({k:summary[k] for k in ('status','collision_count','unresolved_count','scan_errors','counts')},indent=2))
    return summary


if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('--root',type=Path,action='append',required=True); p.add_argument('--out',type=Path,required=True)
    args=p.parse_args(); inspect([r.resolve() for r in args.root],args.out.resolve())
