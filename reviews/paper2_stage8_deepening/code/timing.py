"""Four prespecified paired timing replays, one standalone method at a time."""
import hashlib
from concurrent.futures import ProcessPoolExecutor
import time
import numpy as np
from experiment import Methods,ROOT,D,read,save
from engine import elementary_cache,trigger_cache

def replay(args):
    g,i=args
    reg=read(ROOT/"registration.json")
    ident=f"{g}-{i:02d}"
    row=read(ROOT/"results/confirmation"/(ident+".json"))
    timing=[]
    for m in (("M1","M3") if i==0 else ("M3","M1")):
        frames=row["public"]
        warm=Methods(D(reg["strong"]),reg["threshold"],m)
        for frame in frames[:8]:
            warm.step(frame)
        elementary_cache.cache_clear()
        trigger_cache.cache_clear()
        hash_act=hashlib.sha256()
        queries=[]
        start=time.perf_counter()
        cpu=time.process_time()
        method=Methods(D(reg["strong"]),reg["threshold"],m)
        for frame in frames:
            a,q,_,_=method.step(frame)
            hash_act.update(np.asarray(a[m][0],dtype=">f8").tobytes())
            if q:
                queries.append(q["seconds"])
        seconds=time.perf_counter()-start
        cpu=time.process_time()-cpu
        assert hash_act.hexdigest()==row["actions_sha256"][m]
        timing.append(dict(id=ident,method=m,seconds=seconds,cpu=cpu,query_seconds=queries,
                           identical=True))
    return timing
if __name__=="__main__":
    tasks=[(g,i) for g in ("strong_positive","strong_negative") for i in (0,1)]
    with ProcessPoolExecutor(4) as pool:
        save(ROOT/"results/timing.json",[r for rs in pool.map(replay,tasks) for r in rs])
