"""Small end-to-end checks against scalar replay and frozen output-window semantics."""
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

import numpy as np

PACKAGE = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(PACKAGE/'code'),str(PACKAGE.parent/'paper2_stage12_trsr_oracle_20261124')]
from trsr import Filter, Packet
from receiver import V2Filter
import run_oracle_pilot as pilot


class OracleRunnerChecks(unittest.TestCase):
    def test_scalar_replication_and_delays(self):
        cfg = json.loads(pilot.MODEL.read_text(encoding='utf8'))
        batch = V2Filter(cfg)
        scalar = Filter({**cfg,'P0':cfg['P0_prior']})
        # Fixed arithmetic fixtures replace all random generators. This only tests
        # receiver evaluation and publication logic, not a stochastic performance claim.
        horizon,start,length = 12,3,2
        stop = start+length
        t = np.arange(stop+horizon,dtype=float)
        truth = np.column_stack((.02*t,-.1+.007*t))[:,None,:]
        y = np.asarray([.45*(-1)**k+.01*k for k in range(len(t))])[:,None]
        ctr_offset = (.004*np.sin(t))[:,None]
        toss = np.where((t.astype(int)%4)==1,0.,.999)[:,None]
        bias = -.25
        with patch.object(pilot,'exogenous',return_value=(truth,y,ctr_offset,toss)):
            data,_,example = pilot.make_batch(batch,0,7,1,start,length,bias,horizon,2,.012)
        self.assertEqual(data['checkpoint'],2)
        for run,b in enumerate([bias,0.]):
            M = R = oracle = scalar.initial
            anchor_m = None
            for i in range(len(t)):
                c = float(scalar.C@M.mean+ctr_offset[i,0])
                sent = bool(toss[i,0]>np.exp(-.5*scalar.Z*(y[i,0]-c)**2))
                active = start<=i<stop
                payload = y[i,0]+b*active if sent else None
                packet = Packet(c,payload)
                m,_ = scalar.update(M,packet)
                r,_ = scalar.update(R,packet,erase=active)
                o,_ = scalar.update(oracle,Packet(c,None if payload is None else payload-b*active))
                if i==data['checkpoint']:
                    anchor_m = m.mean.copy()
                if run==0:
                    self.assertEqual(example[i]['sent'], int(sent))
                    self.assertAlmostEqual(example[i]['center'],c)
                if i>=stop:
                    d=m.mean-o.mean
                    h=m.mean-r.mean
                    q=h@scalar.W@h
                    lam=0 if q==0 else min(1.,max(0.,h@scalar.W@d/q))
                    rollback=np.linalg.matrix_power(scalar.A,i-data['checkpoint'])@anchor_m
                    estimates=[m.mean,rollback,r.mean,m.mean-.5*h,m.mean-lam*h,o.mean]
                    for j,est in enumerate(estimates):
                        err=est-truth[i,0]
                        loss=err@scalar.W@err
                        expected_cond=d@scalar.W@d-(est-o.mean)@scalar.W@(est-o.mean)
                        self.assertAlmostEqual(data['loss'][i-stop,run,j],loss)
                        self.assertAlmostEqual(data['conditional'][i-stop,run,j],expected_cond)
                        if run==0:
                            observed=[example[i][f'M{j}_x0'],example[i][f'M{j}_x1']]
                            np.testing.assert_allclose(observed,est,rtol=0,atol=2e-14)
                M,R,oracle=scalar.predict(m),scalar.predict(r),scalar.predict(o)
        rows,_=pilot.reduce_windows(data,7,length,bias,start,1,[0,2,5],4,horizon)
        for row in rows:
            begin=row['delay'] if row['window']=='activation64' else 0
            end=begin+row['post_steps']
            arm=int(row['condition']=='sham')
            for j in range(6):
                expected=sum(data['loss'][i,arm,j if i>=row['delay'] else 0] for i in range(begin,end))
                self.assertAlmostEqual(row[f'M{j}_loss'],expected)
                if end<=row['delay']:
                    self.assertEqual(row[f'M{j}_actions'],0)
            if arm:
                self.assertEqual(row['M4_gain'],0.)
                self.assertEqual(row['M5_actions'],0)


if __name__=='__main__':
    unittest.main(verbosity=2)
