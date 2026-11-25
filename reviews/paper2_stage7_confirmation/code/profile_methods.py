"""Ancillary timing replay on primary confirmation IDs 0..3; no new samples."""
from concurrent.futures import ProcessPoolExecutor
from decimal import Decimal
import time
import numpy as np
from engine import (TASK,MODEL,Online,VectorRecord,ScoredGrid,TIMES,GRID,A,ZERO,
                    point_output,choose_point,simulate,elementary_cache,trigger_cache)
from exact_linear import add,matmul,matrix,asfloat,update,transpose
from run import read,save,warmup,CASES

class PointOnly:
    def __init__(self,h):
        self.h=Decimal(h)
        self.record=VectorRecord(MODEL)
        self.P=self.record.P
        self.point=np.zeros(2)
        self.b=0.
        self.monitor=np.zeros(2)

    def step(self,frame):
        t,sent,r,u=frame
        core=self.record
        post,km,tm=update(self.P,core.C,core.R+(0 if sent else 1/core.Z))
        K=np.array(asfloat(km)).ravel()
        self.monitor=A@self.monitor+K*(u if sent else r)
        self.point=np.array(asfloat(matmul(tm,core.A)))@self.point+(K*self.b if sent else 0.)
        if t<=TIMES[-1]:
            core.append(sent,repr(u) if sent else None,repr(r))
            self.P=core.P
        else:
            self.P=add(matmul(matmul(core.A,post),transpose(core.A)),core.Q)
        sec=None
        if t in TIMES:
            tick=time.perf_counter()
            grid=ScoredGrid(core)
            _,p,b=choose_point(grid,GRID)
            self.point,self.b=(p,float(b)) if grid.score>self.h else (np.zeros(2),0.)
            sec=time.perf_counter()-tick
        self.point,a=point_output(self.monitor,self.point)
        return a,sec

def replay(index):
    reg=read(TASK/"registration.json")
    data=read(TASK/"results/confirmation"/f"strong_early-{index:04d}.json")
    public,truth=simulate(reg["seed"],list(CASES).index("strong_early"),index,.25,50)
    rows=[]
    for method in (("M1","M3") if index%2==0 else ("M3","M1")):
        warmup()
        elementary_cache.cache_clear()
        trigger_cache.cache_clear()
        wall,cpu=time.perf_counter(),time.process_time()
        obj=PointOnly(reg["thresholds"]["M1"]) if method=="M1" else Online({})
        acts,qs=[],[]
        for frame in public:
            if method=="M1":
                act,sec=obj.step(frame)
            else:
                actions,q,_,_,_=obj.step(frame)
                act=actions["M3"][0]
                sec=q["seconds"] if q else None
            acts.append(act)
            if sec is not None:
                qs.append(sec)
        duration=time.perf_counter()-wall
        cpu=time.process_time()-cpu
        loss=sum(float((truth[t]+np.array(acts[t],float))@(truth[t]+np.array(acts[t],float))) for t in range(50,562))
        assert abs(loss-data["metrics"][method]["loss"])<2e-8
        rows.append(dict(id=data["id"],method=method,seconds=duration,cpu=cpu,query_s=qs,loss=loss))
    return rows

if __name__=="__main__":
    with ProcessPoolExecutor(max_workers=4) as pool:
        values=[v for row in pool.map(replay,range(4)) for v in row]
    save(TASK/"results/engineering_replay.json", values)
    print([(r["id"],r["method"],round(r["seconds"],2)) for r in values])
