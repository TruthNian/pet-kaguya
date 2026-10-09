"""Causal held-input response and source ownership, not visual approval."""
import copy
import json
from pathlib import Path
import sys
import unittest

import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import locomotion_follow as follow
from build_idle import sample


class FollowThrough(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.motion=json.loads((ROOT/'sources/canonical/locomotion-motion.json').read_text())
        cls.regions=json.loads((ROOT/'sources/canonical/regions.json').read_text())
        cls.weights=follow.fields(cls.regions,cls.motion['followThrough'])

    def test_stationary_input_has_no_autonomous_oscillation(self):
        for value in (0,13,-7):
            p=follow.periodic_lag([value]*8,[120]*7+[220],160,.25)
            np.testing.assert_allclose(p['offsetsSourcePx'],0,rtol=0,atol=1e-12)
        self.assertEqual(follow.periodic_lag([0,8,-8],[120,120,220],160,0)['offsetsSourcePx'],[0,0,0])

    def test_translation_and_reversal_invariance_do_not_mirror_art(self):
        xs=[p['rootSourcePx'][0] for p in self.motion['keyframes']]
        ds=self.motion['durationsMs']
        p=follow.periodic_lag(xs,ds,160,.25)['offsetsSourcePx']
        np.testing.assert_allclose(follow.periodic_lag([x+10 for x in xs],ds,160,.25)['offsetsSourcePx'],p,rtol=0,atol=1e-12)
        np.testing.assert_allclose(follow.periodic_lag([-x for x in xs],ds,160,.25)['offsetsSourcePx'],-np.array(p),rtol=0,atol=1e-12)

    def test_periodic_solution_matches_independent_small_step_integration(self):
        xs=[p['rootSourcePx'][0] for p in self.motion['keyframes']]
        ds=self.motion['durationsMs']; tau=160; gain=.25
        p=follow.periodic_lag(xs,ds,tau,gain)
        self.assertAlmostEqual(p['initialStateSourcePx'],p['endStateSourcePx'],places=10)
        # Forward-Euler convergence, independent of the analytic recurrence.
        state=0.; observed=[]; dt=.02
        for cycle in range(6):
            observed=[]
            for x,d in zip(xs,ds):
                for tick in range(round(d/dt)):
                    if tick==round(d/(2*dt)):observed.append(gain*(state-x))
                    state+=(x-state)*dt/tau
        np.testing.assert_allclose(observed,p['offsetsSourcePx'],rtol=0,atol=.0001)

    def test_real_final_hold_and_previous_motion_change_the_response(self):
        p=follow.profile(self.motion)
        hair=p['hair']['offsetsSourcePx']
        self.assertLess(hair[1],0);self.assertGreater(hair[5],0)
        self.assertLess(hair[0],0);self.assertGreater(hair[4],0)
        symmetric=copy.deepcopy(self.motion);symmetric['durationsMs']=[120]*8
        self.assertNotEqual(follow.profile(symmetric)['hair']['offsetsSourcePx'],hair)
        for part in p.values():
            self.assertLessEqual(max(abs(v) for v in part['offsetsSourcePx']),2.1)

    def test_protected_face_front_legs_and_shoes_are_exact_not_blur_tail_assumptions(self):
        rects=[self.regions['protectedFace'],self.motion['followThrough']['protectedHeadRect'],self.motion['followThrough']['protectedFrontRect'],
               self.motion['followThrough']['protectedLegRect'],*self.regions['shoeProtectedRects']]
        for weight in self.weights.values():
            self.assertGreater(float(weight.max()),.9)
            self.assertTrue(np.isfinite(weight).all());self.assertGreaterEqual(float(weight.min()),0)
            self.assertLessEqual(float(weight.max()),1)
            for x0,y0,x1,y1 in rects:
                yy,xx=np.mgrid[y0:y1:2.5,x0:x1:2.5]
                np.testing.assert_array_equal(sample(weight,xx,yy),0)

    def test_actual_nonzero_inverse_field_is_bounded_and_nonfolding(self):
        yy,xx=np.mgrid[20:1270:3,100:1100:3].astype(float)
        p=follow.profile(self.motion)
        for index in range(8):
            key=dict(followSourcePx={name:part['offsetsSourcePx'][index] for name,part in p.items()})
            sx,sy=follow.coordinates(xx,yy,key,self.weights)
            np.testing.assert_array_equal(sy,yy)
            self.assertGreater(float(np.max(abs(sx-xx))),.02)
            self.assertLessEqual(float(np.max(abs(sx-xx))),2.1)
            xp,_=follow.coordinates(xx+.01,yy,key,self.weights)
            xm,_=follow.coordinates(xx-.01,yy,key,self.weights)
            self.assertGreater(float(((xp-xm)/.02).min()),.85)

    def test_invalid_model_or_ownership_overclaim_is_rejected(self):
        for tau,gain in ((0,.25),(-1,.25),(True,.25),(float('nan'),.25),(160,1.1),(160,True)):
            with self.assertRaises(ValueError):follow.periodic_lag([0,8],[120,220],tau,gain)
        for xs,ds in (([],[]),([0],[0]),([float('nan')],[120]),([0,8],[120])):
            with self.assertRaises(ValueError):follow.periodic_lag(xs,ds,160,.25)
        for key,value in (('boundary','live-physics'),('protectedFrontRect',[450,450,700,700]),
                          ('protectedHeadRect',[455,250,775,465]),
                          ('sample','continuous'),('maximumTipOffsetSourcePx',10)):
            bad=copy.deepcopy(self.motion);bad['followThrough'][key]=value
            with self.assertRaises(ValueError):follow.profile(bad)


if __name__=='__main__':unittest.main()
