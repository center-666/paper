"""Independent audit of persisted pilot statistics (run via unittest discovery)."""
import csv
import gzip
import hashlib
import json
from pathlib import Path
import unittest

import numpy as np
from scipy.stats import t


PACKAGE = Path(__file__).resolve().parents[1]
RESULT = PACKAGE/'results'/'oracle_v1'


class StoredPilotChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not (RESULT/'manifest.json').exists():
            raise unittest.SkipTest('Archived Oracle pilot has not been run')
        cls.manifest = json.loads((RESULT/'manifest.json').read_text())
        cls.summary = json.loads((RESULT/'summary.json').read_text())
        with gzip.open(RESULT/'episodes.csv.gz','rt',encoding='utf8',newline='') as src:
            cls.rows = list(csv.DictReader(src))

    def test_sources_and_trial_completeness(self):
        for name,digest in self.manifest['sha256'].items():
            paths = [p for p in (RESULT/name,PACKAGE/name,PACKAGE/'code'/name,
                           PACKAGE.parent/'paper2_stage6_vector_correction_20261122'/name) if p.exists()]
            self.assertEqual(len(paths),1,name)
            self.assertEqual(hashlib.sha256(paths[0].read_bytes()).hexdigest(),digest,name)
        self.assertEqual(self.manifest['independent_pairs'],1600)
        self.assertEqual(self.manifest['attack_sham_trajectories'],3200)
        self.assertEqual(self.manifest['failures'],0)
        self.assertEqual(len(self.rows),48000)
        key = ['condition','delay','window','cell','episode']
        self.assertEqual(len({tuple(r[k] for k in key) for r in self.rows}),48000)
        cases = [(-.25,20),(-.25,60),(-.10,20),(-.10,60),(.10,20),(.10,60),(.25,20),(.25,60)]
        for r in self.rows:
            b,duration = cases[int(r['cell'])]
            self.assertEqual((float(r['matched_b']),int(r['duration'])),(b,duration))
            self.assertEqual(float(r['b']),b if r['condition']=='attack' else 0.)
            self.assertEqual((int(r['start']),int(r['checkpoint']),int(r['stop'])),(80,70,80+duration))
            self.assertLess(int(r['episode']),200)
            self.assertGreaterEqual(int(r['episode']),0)
            self.assertEqual(r['status'],'ok')
            delay = int(r['delay'])
            self.assertIn(delay,(0,5,20,60,128))
            horizon = 512 if r['window']=='stop512' else 64
            eligible = horizon if r['window']=='activation64' else max(0,horizon-delay)
            self.assertEqual(int(r['eligible']),eligible)
            self.assertEqual(sum(int(r[x]) for x in ('weight_zero','partial','full')),eligible)
            for m in ('M0','M1','M2','M3','M4','M5'):
                self.assertTrue(np.isclose(float(r['M0_loss'])-float(r[m+'_loss']),
                                           float(r[m+'_gain']),rtol=1e-11,atol=5e-11))
                if not eligible or (r['condition']=='sham' and m in ('M4','M5')):
                    self.assertEqual(float(r[m+'_gain']),0.)
                    self.assertEqual(int(r[m+'_actions']),0)
            self.assertGreaterEqual(float(r['M4_conditional']),-1e-11)
            self.assertLessEqual(float(r['M4_conditional']),float(r['available_oracle_energy'])+1e-11)

    def test_paired_statistics_and_efficiency(self):
        by_key = {}
        for r in self.rows:
            key = f"{r['condition']}/{r['delay']}/{r['window']}"
            by_key.setdefault(key,[[] for _ in range(8)])[int(r['cell'])].append(r)
        self.assertEqual(set(by_key),set(self.summary))
        for key,samples in by_key.items():
            summary = self.summary[key]
            for group,rows in enumerate(samples):
                self.assertEqual(len(rows),200)
                e = sum(float(r['oracle_energy']) for r in rows)
                realized = sum(float(r['M4_conditional']) for r in rows)
                frac = summary['cells'][str(group)]['opportunity_captured']
                if e:
                    self.assertAlmostEqual(realized/e,frac)
                else:
                    self.assertIsNone(frac)
            for method in ('M0','M1','M2','M3','M4','M5'):
                stats = summary['overall'][method]
                for metric in ('gain','conditional','loss'):
                    a=np.array([[float(r[method+'_'+metric]) for r in rows] for rows in samples])
                    gm=np.mean(a,axis=1)
                    group_se=np.std(a,axis=1,ddof=1)/np.sqrt(a.shape[1])
                    se=np.linalg.norm(group_se)/8
                    df=(a.shape[1]-1)*sum(group_se**2)**2/sum(group_se**4) if se else np.inf
                    ci=np.mean(gm)+np.array([-1,1])*t.ppf(.975,df)*se
                    np.testing.assert_allclose([stats[metric]['mean'],stats[metric]['se'],*stats[metric]['t95']],
                                               [np.mean(gm),se,*ci],rtol=1e-11,atol=1e-12)
                all_rows=[r for rows in samples for r in rows]
                self.assertAlmostEqual(np.mean([float(r[method+'_gain'])<0 for r in all_rows]),stats['loss_increase_fraction'])
                self.assertAlmostEqual(np.mean([int(r[method+'_actions'])==0 for r in all_rows]),stats['no_action_fraction'])


if __name__=='__main__':
    unittest.main(verbosity=2)
