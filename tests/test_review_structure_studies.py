"""Physical pixel invariants and truthful limits, never an aesthetic score."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import unittest

import numpy as np
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import review_structure as structure
import review_hand as naive
import review_hand_v2 as conditioned


class StructureStudy(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.parent,cls.spec,cls.mapped=structure.inputs()
        cls.pose,cls.allowed,cls.protected=structure.localized_pose(cls.parent,cls.spec,cls.mapped)

    def test_surface_patch_and_complete_alpha_preserve_the_recorded_exterior(self):
        a,b=np.asarray(self.parent),np.asarray(self.pose)
        np.testing.assert_array_equal(a[~self.allowed],b[~self.allowed])
        np.testing.assert_array_equal(a[self.protected],b[self.protected])
        np.testing.assert_array_equal(a[...,3],b[...,3])
        self.assertEqual(int(np.any(a!=b,axis=2).sum()),36907)
        for x0,y0,x1,y1 in [(455,250,775,465),(855,580,958,1000),(433,1015,795,1226)]:
            np.testing.assert_array_equal(a[y0:y1,x0:x1],b[y0:y1,x0:x1])

    def test_saved_study_and_raw_non_adoption_are_real(self):
        with Image.open(structure.OUT/'pose.png') as image:self.assertEqual(image.convert('RGBA').tobytes(),self.pose.tobytes())
        meta=json.loads((structure.OUT/'build.json').read_text())
        decision=json.loads((structure.OUT/'decision.json').read_text())
        self.assertEqual(meta['rawMappedChangedPixelsOutsidePermission'],312345)
        self.assertFalse(meta['adopted']);self.assertFalse(decision['adopted'])
        self.assertFalse(meta['activeAtlasChanged']);self.assertFalse(meta['installed'])
        self.assertTrue(meta['parentAlphaPreserved'])
        with Image.open(structure.OUT/'detail.png') as image:self.assertEqual(image.size,(990,225))

    def test_foreground_permissions_and_provenance_cannot_be_silently_changed(self):
        for key,value in [('fullRedrawAccepted',True),('handPolygons',[[[455,250],[600,260],[550,400]]]),
                          ('backgroundHairChanged',True),('installed',True)]:
            spec=copy.deepcopy(self.spec);spec[key]=value
            with self.assertRaises(ValueError):structure.localized_pose(self.parent,spec,self.mapped)


class ConditionedHand(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.parent,cls.background=naive.inputs()
        cls.pose,cls.allowed,cls.protected,cls.beta,cls.matrix=conditioned.compact(cls.parent,cls.background)

    def test_measured_neutral_reconstruction_is_exact_not_a_clean_matte_claim(self):
        neutral,_,_,_,_=conditioned.compact(self.parent,self.background,1,1)
        self.assertEqual(neutral.tobytes(),self.parent.tobytes())
        meta=json.loads((conditioned.OUT/'build.json').read_text())
        self.assertEqual(meta['neutralChangedPixels'],0);self.assertEqual(meta['neutralMaximumRGBAError'],0)
        self.assertTrue(meta['sourceMatteEstimated']);self.assertFalse(meta['adopted'])
        naive_meta=json.loads((naive.OUT/'build.json').read_text())
        self.assertEqual(naive_meta['neutralMaximumRGBAError'],61)

    def test_compact_pose_retains_original_alpha_upper_hand_cuff_and_exterior(self):
        a,b=np.asarray(self.parent),np.asarray(self.pose)
        np.testing.assert_array_equal(a[~self.allowed],b[~self.allowed])
        np.testing.assert_array_equal(a[self.protected],b[self.protected])
        np.testing.assert_array_equal(a[...,3],b[...,3])
        self.assertEqual(int(np.any(a!=b,axis=2).sum()),5140)
        np.testing.assert_allclose(np.linalg.eigvalsh(self.matrix),[.85,1.08],atol=1e-14)
        self.assertTrue(np.isfinite(self.beta).all());self.assertGreaterEqual(self.beta.min(),0);self.assertLessEqual(self.beta.max(),1)

    def test_incompatible_background_source_or_shape_is_rejected(self):
        bad=self.background.copy();bad.putpixel((550,705),(1,2,3,253))
        with self.assertRaises(ValueError):conditioned.compact(self.parent,bad)
        bad_parent=self.parent.copy();bad_parent.putpixel((550,705),(1,2,3,253))
        with self.assertRaises(ValueError):conditioned.compact(bad_parent,self.background)
        for values in [(float('nan'),1.08),(.7,1.08),(.85,1.2)]:
            with self.assertRaises(ValueError):conditioned.compact(self.parent,self.background,*values)

    def test_saved_pose_is_reproducible_without_active_art_promotion(self):
        with Image.open(conditioned.OUT/'pose.png') as image:self.assertEqual(image.convert('RGBA').tobytes(),self.pose.tobytes())
        meta=json.loads((conditioned.OUT/'build.json').read_text())
        self.assertEqual(hashlib.sha256(self.pose.tobytes()).hexdigest().upper(),meta['poseRGBAHash'])
        for key in ('adopted','activeAtlasChanged','animationBuilt','installableFullAtlas','installed','newArtworkGenerated'):
            self.assertFalse(meta[key])
        self.assertEqual(meta['parentCompositionVersion'],'review-art-v3')


if __name__=='__main__':unittest.main()
