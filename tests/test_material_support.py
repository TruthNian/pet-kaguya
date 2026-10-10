"""Filter support and bounded pixel evidence, not animation approval."""
import hashlib
import json
from pathlib import Path
import sys
import unittest

import numpy as np
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from build_idle import sample,coordinates
from material_support import LEGACY,ZERO,REFERENCE,sample_local,repair_receipt
import build_jumping as jumping
import hop_contact
import locomotion_render as renderer


class LocalSupport(unittest.TestCase):
    def test_zero_extension_matches_independent_padded_sampler_all_edges_corners_and_far_outside(self):
        rng=np.random.default_rng(615)
        x=np.r_[rng.uniform(-2,7,1000),[-1,-.999,-.5,0,4,4.5,4.999,5,1e200,-1e200]]
        y=np.r_[rng.uniform(-2,6,1000),[-1,-.5,0,3,3.5,3.999,4,0,0,0]]
        # Bound the diagnostic's coordinates before legacy integer casting.
        for shape in ((4,5),(4,5,4)):
            texture=rng.uniform(0,255,shape);before=texture.copy()
            pad=((1,1),(1,1)) + (((0,0),) if len(shape)==3 else ())
            expected=sample(np.pad(texture,pad),np.clip(x,-2,6)+1,np.clip(y,-2,5)+1)
            actual=sample_local(texture,x,y,ZERO)
            np.testing.assert_allclose(actual,expected,rtol=0,atol=1e-12)
            np.testing.assert_array_equal(texture,before)
            # Interior arithmetic and the legacy reconstruction remain exact.
            xx,yy=np.meshgrid(np.linspace(0,4,17),np.linspace(0,3,13))
            np.testing.assert_array_equal(sample_local(texture,xx,yy,ZERO),sample(texture,xx,yy))
            np.testing.assert_array_equal(sample_local(texture,xx,yy,LEGACY),sample(texture,xx,yy))

    def test_partial_coverage_is_not_rejected_or_clamped_to_full_coverage(self):
        texture=np.array([[8.]])
        self.assertEqual(sample_local(texture,np.array([-.5]),np.array([0.]),ZERO)[0],4)
        self.assertEqual(sample_local(texture,np.array([-.5]),np.array([-.5]),ZERO)[0],2)
        self.assertEqual(sample_local(texture,np.array([.5]),np.array([.5]),ZERO)[0],2)
        self.assertEqual(sample_local(texture,np.array([-1.]),np.array([0.]),ZERO)[0],0)
        self.assertEqual(sample_local(texture,np.array([-.5]),np.array([0.]),LEGACY)[0],0)

    def test_unknown_version_nonfinite_coordinates_and_empty_or_wrong_rank_fail(self):
        a=np.ones((2,2))
        for support,x,y in [('unknown',0,0),(ZERO,float('nan'),0),(ZERO,0,float('inf'))]:
            with self.assertRaises(ValueError):sample_local(a,x,y,support)
        for a in (np.ones((0,2)),np.ones(2),np.ones((2,2,2,2))):
            with self.assertRaises(ValueError):sample_local(a,0,0,ZERO)

    def test_actual_three_air_grids_match_source_before_roundoff_rebasing_and_keep_material_observable(self):
        _,_,transform,regions,masks,_,poses=jumping.inputs()
        _,material=jumping.contact_inputs()
        self.assertEqual(material['localFilterSupport'],ZERO)
        for pose in poses[1:4]:
            x,y=renderer.integration_coordinates(transform,actor_y=pose['actorY'])
            tips=dict(bodyY=0,earAngle=pose['earAngle'],hairAngle=pose['hairAngle'])
            fields=lambda xx,yy:coordinates(xx,yy,tips,transform,regions,masks)
            bx,by=fields(x,y)
            raw=renderer.evaluate(material,x,y,hop_contact.key(pose,transform['scale']),1,
                                  source_fields=fields,rebase_roundoff=False)
            np.testing.assert_allclose(raw,sample(material['source'],bx,by),rtol=0,atol=1e-10)
        # No shortcut/cache may hide a valid change to the live paint arrays.
        changed=dict(material,data=dict(material['data'],layers=[p.copy() for p in material['data']['layers']]))
        paint=changed['data']['layers'][0]
        yy,xx=np.where((paint[...,3]>200)&(paint[...,0]<paint[...,3]-1))
        u,v=int(yy[0]),int(xx[0]);paint[u,v,0]+=1
        x0,y0,_,_=changed['data']['box'];zero=poses[2]
        point=hop_contact.sample_pose(changed,np.array([v+x0]),np.array([u+y0]),zero,transform,regions,masks)
        self.assertGreater(abs(point[0,0]-material['source'][u+y0,v+x0,0]),.9)

    def test_frozen_inputs_21_actual_cels_receipts_and_protected_pixels(self):
        manifest=json.loads((REFERENCE/'manifest.json').read_text())
        self.assertEqual(manifest['commit'],'7f58246889fbbcfef788606067a95cf9251e1a87')
        for name,digest in manifest['files'].items():
            self.assertEqual(hashlib.sha256((REFERENCE/name).read_bytes()).hexdigest().upper(),digest)
        self.assertFalse(manifest['installed'] or manifest['visualApprovalInherited'])
        expected={'jumping':([15,18,0,18,0],[[78,154,113,159],[78,152,113,156],None,[78,152,113,156],None]),
                  'run_right':([0,1,0,1,0,0,0,0],[None,[113,156,114,157],None,[113,156,114,157],None,None,None,None]),
                  'run_left':([0,1,0,1,0,0,0,0],[None,[113,156,114,157],None,[113,156,114,157],None,None,None,None])}
        with Image.open(ROOT/'candidates/phase5/global/spritesheet.webp') as atlas:
            for state,(counts,bounds) in expected.items():
                metadata=json.loads((ROOT/f'candidates/phase5/{state}/build.json').read_text())
                baseline=json.loads((REFERENCE/f'{state}.json').read_text())
                # All source, camera, pose, gaze, joints, schedules and approval
                # fields not explicitly measured by this repair are unchanged.
                allowed={'frameHashes','originalAirCelsRGBAExact','heightFieldAirChangedPixels',
                         'heightFieldAirMaximumChannelDifference','localFilterSupport','materialSupportRepair'}
                for key,value in baseline.items():
                    if key not in allowed:self.assertEqual(metadata[key],value,key)
                with Image.open(ROOT/f'candidates/phase5/{state}/strip.webp') as strip:
                    n=len(counts)
                    frames=[strip.crop((i*192,0,(i+1)*192,208)).convert('RGBA') for i in range(n)]
                    self.assertIsNone(strip.crop((n*192,0,1536,208)).getbbox())
                    row=metadata['nativeRow']
                    self.assertEqual(strip.convert('RGBA').tobytes(),atlas.crop((0,row*208,1536,(row+1)*208)).convert('RGBA').tobytes())
                receipt=repair_receipt(state,frames)
                self.assertEqual(metadata['materialSupportRepair'],receipt)
                self.assertEqual([c['changedPixels'] for c in receipt['changes']],counts)
                self.assertEqual([c['bounds'] for c in receipt['changes']],bounds)
                self.assertTrue(receipt['nativeAlphaPreservedExactly'])
                self.assertFalse(receipt['sourceArtworkChanged'] or receipt['geometryChanged']
                                 or receipt['timingChanged'] or receipt['fullMotionApproved'])
                # Reject changing a face, alpha, cel count, or a >1 channel step.
                with self.assertRaises(ValueError):repair_receipt(state,frames[:-1])
                for position,channel,delta in (((90,60),0,1),((90,154),3,1),((90,154),0,10)):
                    changed=[f.copy() for f in frames];rgba=list(changed[0].getpixel(position))
                    rgba[channel]=(rgba[channel]+delta)%256;changed[0].putpixel(position,tuple(rgba))
                    with self.assertRaises(ValueError):repair_receipt(state,changed)


if __name__=='__main__':unittest.main()
