"""Lossless neutral arithmetic is not clean leg anatomy or approved gait."""
import hashlib
import json
from pathlib import Path
import sys
import unittest
import numpy as np
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import refine_leg_composition as leg
import leg_material as legacy
from build_idle import sample
from review_wave import native_frame
from occlusion_material import over


class ConditionedLegs(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.data=leg.inputs()

    def test_same_material_reconstructs_entire_rgba_and_native_cel_without_shortcut(self):
        data=self.data;result=data['background'].copy()
        for paint,beta in zip(data['layers'],data['occlusions']):result=over(paint,beta,result)
        source=legacy.premult(data['mother'].crop(data['box']))
        np.testing.assert_allclose(result,source,rtol=0,atol=1e-10)
        neutral=leg.composite(data,[(0,0),(0,0)])
        self.assertEqual(neutral.tobytes(),data['mother'].tobytes())
        self.assertEqual(native_frame(neutral).tobytes(),native_frame(data['mother']).tobytes())

    def test_nonzero_pose_keeps_fixed_upper_body_and_the_planted_shoe(self):
        data=self.data;source=np.asarray(data['mother'])
        x0,y0,x1,y1=data['box'];y,x=np.mgrid[y0:y1,x0:x1].astype(float)
        for dx in (-5.,5.):
            image=np.asarray(leg.composite(data,[(dx,-7.5),(0,0)]))
            permission=np.zeros(source.shape[:2],dtype=bool);permission[y0:y1,x0:x1]=True
            np.testing.assert_array_equal(image[~permission],source[~permission])
            sx,sy=legacy.leg_coordinates(x,y,data['spec']['legs'][0],dx,-7.5)
            other=sample(data['occlusions'][0],sx-x0,sy-y0)
            planted=(data['occlusions'][1]==1)&(other==0)&(y>=1026)
            self.assertGreater(np.count_nonzero(planted),5000)
            np.testing.assert_array_equal(image[y0:y1,x0:x1][planted],source[y0:y1,x0:x1][planted])
            self.assertGreater(np.count_nonzero(np.any(source!=image,axis=2)),500)

    def test_all_two_materials_are_valid_and_disjoint_in_the_original_pose(self):
        p,q=self.data['occlusions']
        self.assertFalse(np.any((p>0)&(q>0)))
        for paint,beta in zip(self.data['layers'],self.data['occlusions']):
            self.assertTrue(np.isfinite(paint).all());self.assertTrue(np.isfinite(beta).all())
            self.assertTrue((paint>=0).all())
            self.assertTrue((paint[...,:3]<=paint[...,3:4]+1e-8).all())
            self.assertTrue((paint[...,3]<=255*beta+1e-8).all())
        with self.assertRaises(ValueError):leg.composite(self.data,[(0,0)])

    def test_saved_actual_pose_hashes_and_honest_development_only_boundaries(self):
        meta=json.loads((leg.OUT/'build.json').read_text(encoding='utf-8'))
        images=[self.data['mother'],legacy.composite(legacy.inputs(),[(0,0),(0,0)]),
                leg.composite(self.data,[(0,0),(0,0)]),leg.composite(self.data,[(5,-7.5),(0,0)]),
                leg.composite(self.data,[(0,0),(5,-7.5)])]
        for name,image,digest in zip(['mother','old-neutral','new-neutral','left-lifted','right-lifted'],images,meta['poseHashes']):
            with Image.open(leg.OUT/(name+'.png')) as saved:self.assertEqual(saved.convert('RGBA').tobytes(),image.tobytes())
            self.assertEqual(hashlib.sha256(image.tobytes()).hexdigest().upper(),digest)
        for key in ('neutralRestRGBAExact','neutralNativeRGBAExact','neutralFromSameMaterialNotSourceShortcut',
                    'sourceAlphaAndOcclusionSeparated','estimatedMatte','usedByDevelopmentLocomotion','developmentAtlasChanged'):
            self.assertTrue(meta[key])
        for key in ('artistLayerRecoveryClaimed','newArtworkGenerated','facialGeometryRepair','visualApprovalClaimed','installed','installableFullAtlas'):
            self.assertFalse(meta[key])
        self.assertEqual(meta['visualMotionApproval'],'pending')
        self.assertEqual(meta['strategyUserApproval'],'approved')
        self.assertEqual(meta['strategyApprovalScope'],'front-held-small-steps-only')
        self.assertEqual(meta['neutralNativeMaximumPremultRGBAError'],0)


if __name__=='__main__':unittest.main()
