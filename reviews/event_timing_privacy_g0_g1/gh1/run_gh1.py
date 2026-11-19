import json,sys
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[3]; sys.path.insert(0,str(ROOT/'simulation'))
from model import load_model,generate_data
from engine import simulate
m=load_model(ROOT/'simulation/config.json'); T=m.cfg['T']; N=m.cfg['N']; src,dst=m.edges.T

def run(x,y,kind,threshold=0.,period=4):
    S=len(x); hat=np.zeros((S,N,2)); loc=hat.copy(); ls=hat.copy(); ltime=np.full((S,N),-m.cfg['max_interval']); payload=np.zeros((S,len(src),2)); last=np.full((S,len(src)),-1)
    send=np.zeros((S,T,N),bool); thr=send.copy(); timeout=send.copy(); mse=np.zeros(S); secret=np.zeros(S,dtype=np.int8)
    for t in range(T):
        anchor=loc if kind=='local' else hat
        cross=np.sum((anchor-ls)**2,axis=-1)>threshold
        timed=(t-ltime)>=m.cfg['max_interval']
        tx=(np.full((S,N),t%period==0) if kind=='periodic' else cross|timed)
        if t==0: tx[:]=True
        send[:,t]=tx; thr[:,t]=cross if kind!='periodic' else False; timeout[:,t]=timed if kind!='periodic' else False
        ls=np.where(tx[...,None],anchor,ls); ltime=np.where(tx,t,ltime)
        fresh=tx[:,src]; payload=np.where(fresh[...,None],hat[:,src],payload); last=np.where(fresh,t,last)
        age=np.maximum(t-last,0); aligned=np.einsum('seij,sej->sei',m.powers[age],payload)
        consensus=np.zeros_like(hat)
        for e,i in enumerate(dst): consensus[:,i]+=aligned[:,e]-hat[:,i]
        innov=y[:,t]-np.einsum('imn,sin->sim',m.H,hat)
        lnov=y[:,t]-np.einsum('imn,sin->sim',m.H,loc)
        if t==199: secret=(lnov[:,1,0]>0).astype(np.int8)
        hat=hat@m.A.T+np.einsum('imn,sin->sim',m.gains[t],innov)+m.cfg['epsilon']*(consensus@m.A.T)
        loc=loc@m.A.T+np.einsum('imn,sin->sim',m.local_gains[t],lnov)
        if t>=50: mse+=np.sum((hat-x[:,t+1,None,:])**2,axis=(1,2))/(T-50)/N
    return send,thr,timeout,mse,secret

def mi(s,g,h):
    counts=np.zeros((2,8,4)); np.add.at(counts,(s,g,h),1); p=counts/counts.sum(); ph=p.sum(axis=(0,1)); psh=p.sum(axis=1); pgh=p.sum(axis=0); denom=psh[:,None,:]*pgh[None,:,:]; num=p*ph[None,None,:]; ok=p>0
    return float(np.sum(p[ok]*np.log2((num[ok]/denom[ok]))))

def encode(r):
    sends,thr,tmo,mse,s=r; ev=sends[:,:,1]; h=ev[:,198].astype(int)*2+ev[:,199]; g=ev[:,200].astype(int)*4+ev[:,201].astype(int)*2+ev[:,202]; return s,g,h

def rate(r): return float(r[0][:,50:].mean())

def calibrate(x,y,kind,target):
    lo,hi=0.,3.
    for _ in range(13):
        mid=(lo+hi)/2; v=rate(run(x,y,kind,mid));
        if v>target: lo=mid
        else: hi=mid
    return (lo+hi)/2

if __name__=='__main__':
    cal=np.arange(810000,810240); test=np.arange(820000,821500); xc,yc=generate_data(m,cal); target=rate(run(xc,yc,'periodic',period=4)); thresholds={k:calibrate(xc,yc,k,target) for k in ('original','local')}; xt,yt=generate_data(m,test)
    # Check unchanged implementation against engine on same clean input and threshold.
    m.cfg['send_delta_squared']=thresholds['original']; ref=simulate(m,xt[:8],yt[:8],test[:8],method='yang',scenario='clean',collect=False); ours=run(xt[:8],yt[:8],'original',thresholds['original']); assert np.array_equal(ref.sends,ours[0]); assert np.allclose(((ref.estimates[:,51:]-xt[:8,51:,None,:])**2).sum(-1).mean((1,2)),ours[3])
    results={}; saved={}; rng=np.random.default_rng(991); bootstrap=rng.integers(0,len(test),(500,len(test)))
    for k in ('original','local','periodic'):
        r=run(xt,yt,k,thresholds.get(k,0),4); s,g,h=encode(r); raw=mi(s,g,h); boots=np.array([mi(s[ix],g[ix],h[ix]) for ix in bootstrap]); perm=[]
        for _ in range(200):
            sp=s.copy()
            for v in range(4):
                ix=np.flatnonzero(h==v); sp[ix]=rng.permutation(sp[ix])
            perm.append(mi(sp,g,h))
        perm=np.asarray(perm); saved[k]=(s,g,h,r[3])
        thr=r[1][:,50:]; to=r[2][:,50:]; se=r[0][:,50:]; vals={'rate':rate(r),'mse':float(r[3].mean()),'mse_se':float(r[3].std(ddof=1)/np.sqrt(len(test))),'mi_bits_plugin':raw,'mi_ci_percentile':np.quantile(boots,[.025,.975]).tolist(),'permutation_null_mean':float(perm.mean()),'secret_positive_rate':float(s.mean()),'threshold_fraction':float(thr.mean()),'timeout_fraction':float(to.mean()),'overlap_fraction':float((thr&to).mean()),'send_fraction':float(se.mean()),'sample_n':len(test)}; results[k]=vals
    s1,g1,h1,mse1=saved['local']; s0,g0,h0,mse0=saved['original']; paired=np.array([mi(s1[ix],g1[ix],h1[ix])-mi(s0[ix],g0[ix],h0[ix]) for ix in bootstrap]); diff=mse1-mse0
    comparison={'mi_local_minus_original':mi(s1,g1,h1)-mi(s0,g0,h0),'mi_difference_bootstrap_ci':np.quantile(paired,[.025,.975]).tolist(),'mse_local_minus_original':float(diff.mean()),'mse_difference_paired_ci':np.quantile([diff[ix].mean() for ix in bootstrap],[.025,.975]).tolist()}
    out={'comparison':comparison,'config':{'calibration_seeds':[int(cal[0]),int(cal[-1])],'test_seeds':[int(test[0]),int(test[-1])],'target_period':4,'target_rate':target,'thresholds_squared':thresholds,'T':T,'warmup':50,'private':'sign of node 1 local reference innovation component 0 at t=199','history':'node 1 public send bits at t=198,199','outcome':'node 1 send bits at t=200,201,202','bootstrap_repetitions':500,'permutation_repetitions':200,'baseline_engine_agreement_n':8},'results':results}
    (Path(__file__).parent/'gh1_results.json').write_text(json.dumps(out,indent=2),encoding='utf8'); print(json.dumps(out,indent=2))

