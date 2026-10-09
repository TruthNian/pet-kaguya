"""Causal 2-D support/actor geometry and direct filtering, not aesthetic scores."""
import copy
import json
from pathlib import Path
import sys
import unittest

import numpy as np
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import locomotion_render as render
import refine_leg_composition as leg
import leg_material as geometry
import build_locomotion as run
from canonical import clean_cutout,camera
from build_idle import sample
from occlusion_material import condition
from review_wave import native_frame


class DirectLocomotion(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data=leg.inputs()
        cls.material=render.prepare(cls.data,cls.data['mother'])
        cls.motion=json.loads((ROOT/'sources/canonical/locomotion-motion.json').read_text(encoding='utf-8'))
        cls.transform=camera(clean_cutout(cls.data['mother'])[0])

    def test_visible_backing_normalization_obeys_a_known_fractional_neutral_equation(self):
        source=np.array([[[50,30,20,255],[100,100,100,255]]]*2,dtype=np.uint8)
        backing=np.array([[[0,0,0,255],[255,255,255,255]]]*2,dtype=float)
        p,beta=condition(source.astype(float),backing,np.array([[.25,1.]]*2))
        tiny=dict(self.data,mother=Image.fromarray(source),box=(0,0,2,2),background=backing,
                  layers=[p,np.zeros_like(p)],occlusions=[beta,np.zeros_like(beta)])
        m=render.prepare(tiny,tiny['mother']); k=dict(rootSourcePx=[0,0],left=[0,0],right=[0,0])
        x,y=np.array([.5]),np.array([.5])
        expected=np.array([[75,65,60,255.]])
        actual=render.evaluate(m,x,y,k,1,rebase_roundoff=False)
        np.testing.assert_allclose(actual,expected,atol=1e-12,rtol=0)
        naive=render.evaluate(m,x,y,k,1,normalized_backing=False,rebase_roundoff=False)
        self.assertGreater(float(np.max(abs(naive-expected))),40)

    def test_optional_source_field_warps_paint_occlusion_and_backing_together(self):
        source=np.array([[[50,30,20,255],[100,100,100,255]]]*2,dtype=np.uint8)
        backing=np.array([[[0,0,0,255],[255,255,255,255]]]*2,dtype=float)
        paint,beta=condition(source.astype(float),backing,np.array([[.25,1.]]*2))
        data=dict(self.data,mother=Image.fromarray(source),box=(0,0,2,2),background=backing,
                  layers=[paint,np.zeros_like(paint)],occlusions=[beta,np.zeros_like(beta)])
        material=render.prepare(data,data['mother'])
        key=dict(rootSourcePx=[0,0],left=[0,0],right=[0,0])
        actual=render.evaluate(material,np.array([.5]),np.array([.5]),key,1,
            source_fields=lambda x,y:(x+.25,y+.1),rebase_roundoff=False)
        np.testing.assert_allclose(actual,[[87.5,82.5,80,255]],atol=1e-12,rtol=0)

    def test_fractional_full_material_neutral_and_native_reference_not_a_source_shortcut(self):
        m=self.material;k=dict(rootSourcePx=[0,0],left=[0,0],right=[0,0])
        x,y=render.integration_coordinates(self.transform)
        reference=sample(m['source'],x,y)
        raw=render.evaluate(m,x,y,k,1,rebase_roundoff=False)
        np.testing.assert_allclose(raw,reference,atol=1e-10,rtol=0)
        np.testing.assert_array_equal(render.evaluate(m,x,y,k,1),reference)
        self.assertEqual(render.render(m,k,1,self.transform).tobytes(),native_frame(self.data['mother']).tobytes())
        evidence=render.neutral_evidence(m,self.data['mother'],self.transform)
        self.assertTrue(evidence['directSamplerNeutralRGBAExact'])
        self.assertEqual(evidence['directSamplerNeutralChangedPixels'],0)
        naive=render.render(m,k,1,self.transform,normalized_backing=False)
        self.assertNotEqual(naive.tobytes(),native_frame(self.data['mother']).tobytes())
        # Perturb valid material even at zero geometry: the output must change.
        changed=dict(m,data=dict(m['data'],layers=[p.copy() for p in m['data']['layers']]))
        p=changed['data']['layers'][0]
        yy,xx=np.where((p[...,3]>200)&(p[...,0]<p[...,3]-1))
        u,v=int(yy[0]),int(xx[0]); p[u,v,0]+=1
        x0,y0,_,_=self.data['box']
        point=render.evaluate(changed,np.array([x0+v]),np.array([y0+u]),k,1)
        self.assertGreater(float(abs(point[0,0]-m['source'][y0+u,x0+v,0])),.9)

    def test_root_heads_and_clothes_translate_without_scale_rotate_or_camera_refit(self):
        yy,xx=np.mgrid[100:936:31,130:1080:29].astype(float)
        for key in self.motion['keyframes']:
            rx,ry=key['rootSourcePx']
            sx,sy=render.source_coordinates(xx+rx,yy+ry,key)
            np.testing.assert_array_equal(sx,xx);np.testing.assert_array_equal(sy,yy)
        self.assertAlmostEqual(12*self.transform['scale'],1.9)
        self.assertAlmostEqual(1.5*self.transform['scale'],.2375)
        decision=json.loads((ROOT/'sources/canonical/locomotion-amplitude-decision-20261009.json').read_text(encoding='utf-8'))
        self.assertEqual(decision['sourceSha256'],self.data['spec']['sourceSha256'])
        self.assertEqual(decision['answer'],'摆幅合适，继续改善落脚衔接（建议）')
        self.assertEqual(decision['scope'],'horizontal-root-amplitude-only')
        self.assertTrue(decision['horizontalRootAmplitudeApproved'])
        self.assertEqual(decision['maximumHorizontalRootSourcePx'],self.motion['maximumRootTranslationSourcePx'][0])
        self.assertAlmostEqual(decision['maximumHorizontalRootSourcePx']*self.transform['scale'],decision['maximumHorizontalRootOutputPx'])
        for key in ('rootTimingApproved','landingApproved','allMotionApproved','sideViewAuthorized',
                    'faceGeometryChangeAuthorized','installedHostChangeAuthorized'):
            self.assertFalse(decision[key])

    def test_support_side_not_travel_direction_and_relative_ik_keeps_world_contacts(self):
        for direction in (-1,1):
            for key in self.motion['keyframes']:
                root=np.asarray(key['rootSourcePx'])
                if key['support']==['right']:self.assertGreater(root[0],0)
                if key['support']==['left']:self.assertLess(root[0],0)
                for bone,offset in zip(self.data['spec']['legs'],render.relative_offsets(key,direction)):
                    a,knee,ankle,lengths=geometry.inverse_kinematics(bone,*offset)
                    np.testing.assert_allclose([np.linalg.norm(knee-a),np.linalg.norm(ankle-knee)],lengths,atol=1e-10,rtol=0)
                    expected=np.asarray(bone['ankle'])+[key[bone['name']][0]*direction,key[bone['name']][1]]
                    np.testing.assert_allclose(ankle+root,expected,atol=1e-12,rtol=0)
                    if bone['name'] in key['support']:np.testing.assert_array_equal(ankle+root,bone['ankle'])

    def test_world_shoe_inverse_cancels_fractional_root_and_retains_original_color(self):
        yy,xx=np.mgrid[1040:1220:5,438:756:5].astype(float)
        data=self.material['data'];x0,y0,_,_=data['box']
        for direction in (-1,1):
            for key in self.motion['keyframes']:
                qx,qy=render.source_coordinates(xx,yy,key)
                offsets=render.relative_offsets(key,direction)
                weights=[]
                for bone,offset,beta in zip(data['spec']['legs'],offsets,data['occlusions']):
                    sx,sy=geometry.leg_coordinates(qx,qy,bone,*offset)
                    dx,dy=key[bone['name']];dx*=direction
                    np.testing.assert_allclose(sx,xx-dx,atol=1e-10,rtol=0)
                    np.testing.assert_allclose(sy,yy-dy,atol=1e-10,rtol=0)
                    weights.append(sample(beta,sx-x0,sy-y0))
                actual=render.evaluate(self.material,xx,yy,key,direction)
                reference=sample(self.material['source'],xx,yy)
                for index,bone in enumerate(data['spec']['legs']):
                    if bone['name'] not in key['support']:continue
                    inner=(weights[index]==1)&(weights[1-index]==0)
                    self.assertGreater(int(inner.sum()),100)
                    np.testing.assert_allclose(actual[inner],reference[inner],atol=1e-10,rtol=0)

    def test_nonzero_sampling_rebase_changes_only_float_roundoff_and_motion_is_not_frozen(self):
        key=self.motion['keyframes'][2]
        yy,xx=np.mgrid[930:1230:3,420:815:3].astype(float)
        raw=render.evaluate(self.material,xx,yy,key,1,rebase_roundoff=False)
        rebased=render.evaluate(self.material,xx,yy,key,1)
        self.assertLess(float(np.max(abs(raw-rebased))),1e-10)
        original=sample(self.material['source'],xx,yy)
        self.assertGreater(int(np.any(abs(rebased-original)>1,axis=-1).sum()),1000)

    def test_actual_relative_ring_projection_remains_continuous_and_nonfolding(self):
        yy,xx=np.mgrid[937:1026:3,460:745:5].astype(float)
        for direction in (-1,1):
            for key in self.motion['keyframes']:
                for bone,offset in zip(self.data['spec']['legs'],render.relative_offsets(key,direction)):
                    xp,yp=geometry.leg_coordinates(xx+.01,yy,bone,*offset)
                    xm,ym=geometry.leg_coordinates(xx-.01,yy,bone,*offset)
                    txp,typ=geometry.leg_coordinates(xx,yy+.01,bone,*offset)
                    txm,tym=geometry.leg_coordinates(xx,yy-.01,bone,*offset)
                    jac=((xp-xm)*(typ-tym)-(txp-txm)*(yp-ym))/.0004
                    self.assertGreater(float(jac.min()),.5)

    def test_invalid_root_direction_range_and_unreachable_planted_leg_are_rejected(self):
        for root in ([13,1],[-8,1],[8,-1],[True,1],[8,float('nan')]):
            bad=copy.deepcopy(self.motion);bad['keyframes'][1]['rootSourcePx']=root
            with self.assertRaises(ValueError):run.validate_motion(bad)
        bad=copy.deepcopy(self.motion);bad['keyframes'][3]['rootSourcePx']=[12,0]
        with self.assertRaises(ValueError):run.validate_motion(bad)


if __name__=='__main__':unittest.main()
