"""Independent deterministic R1--R3 checks for the batched V2 receiver."""
from fractions import Fraction
import json
from pathlib import Path
import sys
import unittest

import numpy as np


PACKAGE = Path(__file__).resolve().parents[1]
STAGE6 = PACKAGE.parent / 'paper2_stage6_vector_correction_20261122'
sys.path.insert(0, str(PACKAGE / 'code'))
from receiver import V2Filter, decide


def rational(values):
    return np.vectorize(Fraction, otypes=[object])(values)


def exact_reference(config, pattern, start, end, bias):
    """Independent Joseph update on a tiny, fixed sensor-log fixture."""
    A, C, Q, P = [rational(config[k]) for k in ('A', 'C', 'Q', 'P0_prior')]
    r, z = Fraction(config['R']), Fraction(config['Z'])
    mean = rational([0, 0])
    response = rational([0, 0])
    identity = rational(np.eye(2, dtype=int))
    for t, bit in enumerate(pattern):
        center = Fraction(1 - 2*(t % 2), 256)
        source = Fraction(2*t - 5, 8)
        active = start <= t < end
        sent = bit == '1'
        noise = r if sent else r+1/z
        prior = mean
        innovation_var = (C @ P @ C.T)[0, 0]+noise
        gain = P @ C.T / innovation_var
        transition = identity - gain @ C
        measurement = source - bias*active if sent else center
        mean = prior + gain[:, 0]*(measurement-(C @ prior)[0])
        P = transition @ P @ transition.T + (gain @ gain.T)*noise
        response = transition @ response + gain[:, 0]*int(sent and active)
        yield mean, P, response, center, source
        P = A @ P @ A.T + Q
        mean = A @ mean
        response = A @ response


class ReceiverChecks(unittest.TestCase):
    def setUp(self):
        self.config = json.loads((STAGE6/'model.json').read_text(encoding='utf8'))
        self.model = V2Filter(self.config)

    def assert_close(self, actual, expected, tol=2e-13):
        np.testing.assert_allclose(actual, np.asarray(expected, dtype=float),
                                   rtol=0, atol=tol)

    def test_r1_window_response_and_corrected_mean(self):
        for pattern in ('000000', '111111', '010110', '101001'):
            for start, end in ((0,1), (1,4), (4,6)):
                for bias in (Fraction('-0.25'), Fraction('0'), Fraction('0.1')):
                    with self.subTest(pattern=pattern, window=(start,end), bias=bias):
                        monitor, cov = self.model.initial(1)
                        H, Hstart, Hend = (np.zeros_like(monitor) for _ in range(3))
                        reference = exact_reference(self.config, pattern, start, end, bias)
                        for t, (mean, P, response, center, observed) in enumerate(reference):
                            sent = np.array([pattern[t] == '1'])
                            payload = np.array([float(observed) if sent[0] else np.nan])
                            post, pcov, K = self.model.update(monitor, cov,
                                                              np.array([float(center)]), payload)
                            H = self.model.response(H, K, sent, start <= t < end)
                            Hstart = self.model.response(Hstart, K, sent, t >= start)
                            Hend = self.model.response(Hend, K, sent, t >= end)
                            self.assert_close(Hstart-Hend, H)
                            self.assert_close(H[0], response)
                            self.assert_close(post[0]-float(bias)*H[0], mean)
                            self.assert_close(pcov[0], P)
                            monitor, cov = self.model.predict(post, pcov)

    def test_r2_replay_uses_only_visible_prefix(self):
        # Include a clean send before the suspected interval, an in-window
        # silence, two erased sends, and a subsequent clean send.
        centers = np.array([.01,-.02,.04,.01,.08,-.03])[:, None]
        payloads = np.array([.3,np.nan,.5,-.2,.1,np.nan])[:, None]
        initial = self.model.initial(1)
        def replay(c, y, k=1, end=4):
            return self.model.replay(-1, *initial, c, y, k, end)
        expected = replay(centers,payloads)
        for t in (2,3):
            altered = payloads.copy()
            altered[t] += 1
            for got,want in zip(replay(centers,altered), expected):
                np.testing.assert_array_equal(got,want)
        altered = centers.copy()
        altered[1] += .75
        self.assertFalse(np.allclose(replay(altered,payloads)[0],expected[0]))
        altered = payloads.copy()
        altered[4] -= .5
        self.assertFalse(np.allclose(replay(centers,altered)[0],expected[0]))
        clean_post,clean_cov,_ = self.model.update(*initial, centers[0], payloads[0])
        later = self.model.replay(0,clean_post,clean_cov,centers,payloads,1,4)
        for a,b in zip(later,expected):
            self.assert_close(a,b)
        with self.assertRaises(ValueError):
            self.model.replay(1,clean_post,clean_cov,centers,payloads,1,4)
        # Different future logs coincide at any common earlier prefix.
        altered = payloads.copy()
        altered[4:] = 12.
        for a,b in zip(replay(centers[:4],altered[:4]),replay(centers[:4],payloads[:4])):
            np.testing.assert_array_equal(a,b)

    def test_r2_empty_window_and_all_erased(self):
        centers = np.array([[.02],[-.05],[.07]])
        payloads = np.array([[.32],[.0625],[-.175]])
        mean,cov = self.model.initial(1)
        full_mean, full_cov = mean,cov
        open_mean, open_cov = mean,cov
        for c,y in zip(centers,payloads):
            post,pcov,_ = self.model.update(full_mean,full_cov,c,y)
            full_mean,full_cov = self.model.predict(post,pcov)
            open_mean,open_cov = self.model.predict(open_mean,open_cov)
        for output, expected in zip(self.model.replay(-1,mean,cov,centers,payloads,1,1),
                                    (full_mean,full_cov)):
            self.assert_close(output,expected)
        for output, expected in zip(self.model.replay(-1,mean,cov,centers,payloads,0,3),
                                    (open_mean,open_cov)):
            self.assert_close(output,expected)

    def test_r3_clipped_optimum_and_paid_action(self):
        W = np.array([[1.4,.2],[.2,2.1]])
        h = np.array([.75,-.5])
        monitor = np.array([[2.,-.72]])
        steps = np.linspace(0,1,8193)
        # Endpoint boxes, full rejection, partial and full recovery, health,
        # a zero-projection candidate, and a signed uncertain set.
        for scales in ((-.25,.25), (0.,.8), (.375,.7), (1.,1.2), (1.4,1.6)):
            ds = np.stack([s*h for s in scales])
            pub,weight,reported,rejected = decide(monitor,monitor-h,ds[None],W)
            self.assertFalse(bool(rejected[0]))
            action = (monitor-pub)[0]
            risk_diffs = np.array([v@W@v - (v-action)@W@(v-action) for v in ds])
            self.assert_close(reported, [min(risk_diffs)])
            self.assertGreaterEqual(reported[0], -1e-14)
            q = h@W@h
            proj = (ds@W@h).min()
            grid_gain = np.max(2*steps*proj-steps**2*q)
            self.assert_close(weight,[np.clip(scales[0],0,1)])
            self.assertLessEqual(abs(reported[0]-grid_gain), q*(1/8192)**2+2e-14)
        # The recovery state, covariance and physical truth are not optimizer inputs.
        for dirs in (np.zeros((1,1,2)),np.empty((1,0,2)),np.full((1,1,2),np.nan)):
            pub,lam,gain,_ = decide(monitor,monitor,dirs,W)
            np.testing.assert_array_equal(pub,monitor)
            self.assert_close(lam,[0])
            self.assert_close(gain,[0])

    def test_r3_actual_floating_displacement(self):
        # Coupled output coordinates can round differently. The gain attached
        # to the candidate must apply to the actual published vector.
        monitor = np.array([[2.**53,1.]])
        recovery = monitor-np.array([[2.,1.]])
        d = np.array([[[.8,.2]]])
        W = np.eye(2)
        pub,_,reported,_ = decide(monitor,recovery,d,W)
        a = (monitor-pub)[0]
        gain = 2*a@d[0,0] - a@a
        self.assert_close(reported,[gain])
        self.assertGreaterEqual(gain,0)


if __name__ == '__main__':
    unittest.main(verbosity=2)
