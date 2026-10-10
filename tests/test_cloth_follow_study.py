"""Bounded original-source secondary motion is not an aesthetic verdict."""
import copy
import json
from pathlib import Path
import sys
import unittest

import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import cloth_follow_study as study
import locomotion_follow as follow
import locomotion_render as renderer
from build_idle import sample


class SleeveField(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.weight=study.influence([1205,1306])
        cls.motion=json.loads((ROOT/'sources/canonical/locomotion-motion.json').read_text())

    def test_compact_support_and_protected_rectangles_are_exact(self):
        self.assertTrue(np.isfinite(self.weight).all())
        self.assertEqual(self.weight.min(),0)
        self.assertGreater(self.weight.max(),.9)
        self.assertLessEqual(self.weight.max(),1)
        yy,xx=np.mgrid[:1306,:1205]
        inside=np.zeros_like(xx,dtype=bool)
        for part in study.SPEC['ellipses']:
            cx,cy=part['center'];rx,ry=part['radii']
            inside|=((xx-cx)/rx)**2+((yy-cy)/ry)**2<1
        np.testing.assert_array_equal(self.weight[~inside],0)
        for x0,y0,x1,y1 in study.SPEC['protectedRects']:
            yy,xx=np.mgrid[y0:y1:2.3,x0:x1:2.7]
            np.testing.assert_array_equal(sample(self.weight,xx,yy),0)

    def test_stationary_input_has_no_cloth_oscillation(self):
        for root in (0,10,-10):
            value=follow.periodic_lag([root]*8,self.motion['durationsMs'],study.SPEC['timeConstantMs'],study.SPEC['gain'])
            np.testing.assert_allclose(value['offsetsSourcePx'],0,rtol=0,atol=1e-12)

    def test_real_220ms_hold_and_periodic_state_are_retained(self):
        value=study.response(self.motion)
        self.assertAlmostEqual(value['initialStateSourcePx'],value['endStateSourcePx'],places=10)
        self.assertLessEqual(max(abs(v) for v in value['offsetsSourcePx']),study.SPEC['maximumOffsetSourcePx'])
        roots=[k['rootSourcePx'][0] for k in self.motion['keyframes']]
        other=follow.periodic_lag(roots,[120]*8,study.SPEC['timeConstantMs'],study.SPEC['gain'])
        self.assertNotEqual(other['offsetsSourcePx'],value['offsetsSourcePx'])

    def test_nonzero_inverse_field_is_bounded_and_nonfolding(self):
        yy,xx=np.mgrid[790:1020:2.,270:950:2.]
        for amount in study.response(self.motion)['offsetsSourcePx']:
            key=dict(followSourcePx={'cloth':amount});weights={'cloth':self.weight}
            sx,sy=follow.coordinates(xx,yy,key,weights)
            np.testing.assert_array_equal(sy,yy)
            self.assertGreater(float(np.max(abs(sx-xx))),.1)
            self.assertLessEqual(float(np.max(abs(sx-xx))),study.SPEC['maximumOffsetSourcePx'])
            xp,_=follow.coordinates(xx+.01,yy,key,weights)
            xm,_=follow.coordinates(xx-.01,yy,key,weights)
            self.assertGreater(float(((xp-xm)/.02).min()),.8)

    def test_source_and_ownership_cannot_silently_change(self):
        with self.assertRaises(ValueError):study.influence([192,208])
        bad=copy.deepcopy(study.SPEC);bad['protectedRects']=[]
        with self.assertRaises(ValueError):study.influence([1205,1306],bad)


class ActualSleeveStudy(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.data=study.inputs()

    def test_actual_native_changes_are_bounded_without_false_opaque_claim(self):
        for result in self.data['results'].values():
            for old,new,difference in zip(result['baseline'],result['frames'],result['differences']):
                a,b=np.asarray(old),np.asarray(new)
                allowed=np.zeros(a.shape[:2],dtype=bool)
                allowed[132:174,42:71]=True;allowed[132:174,120:153]=True
                np.testing.assert_array_equal(a[~allowed],b[~allowed])
                self.assertGreater(difference['changedRGBPixels'],0)
                self.assertEqual(difference['changedAlphaPixels'],int((a[...,3]!=b[...,3]).sum()))
                self.assertEqual(difference['maximumAlphaDifference'],int(np.abs(a[...,3].astype(int)-b[...,3].astype(int)).max()))
        # The first hypothesis wrongly assumed these original interiors opaque.
        a=np.asarray(self.data['data']['mother'])
        self.assertEqual(int(a[875,304,3]),253)
        self.assertEqual(int(a[924,373,3]),252)

    def test_zero_additional_response_reconstructs_current_and_does_not_touch_gait(self):
        data=self.data['data']
        for name,result in self.data['results'].items():
            parent=data['results'][name]
            for i in (0,2,6,7):
                key=dict(result['keys'][i],followSourcePx={**result['keys'][i]['followSourcePx'],'cloth':0})
                actual=renderer.render(result['material'],key,parent['state']['direction'],data['transform'])
                self.assertEqual(actual.tobytes(),result['baseline'][i].tobytes())
            for before,after in zip(parent['renderKeys'],result['keys']):
                self.assertEqual({k:v for k,v in after.items() if k!='followSourcePx'},
                                 {k:v for k,v in before.items() if k!='followSourcePx'})
                self.assertEqual({k:v for k,v in after['followSourcePx'].items() if k!='cloth'},before['followSourcePx'])

    def test_generated_artifact_exposes_real_alpha_and_unapproved_boundaries(self):
        metadata=json.loads((study.OUT/'build.json').read_text())
        for key in ('adopted','activeAtlasChanged','installed','installableFullAtlas','physicalClothSimulation',
                    'cleanClothLayersRecovered','nativeInterpolation','liveDragLagInitialization'):
            self.assertIs(metadata[key],False)
        self.assertEqual(metadata['visualMotionApproval'],'pending')
        self.assertEqual(metadata['specificMotionUserApproval'],'pending')
        for name,result in self.data['results'].items():
            entry=metadata['states'][name]
            self.assertEqual(entry['parentFrameHashes'],result['parent']['frameHashes'])
            self.assertEqual(entry['frameHashes'],[study.rgba_hash(f) for f in result['frames']])
            self.assertEqual(entry['differences'],result['differences'])
            self.assertEqual(entry['allNativeAlphaExact'],all(d['changedAlphaPixels']==0 for d in result['differences']))


if __name__=='__main__':unittest.main()
