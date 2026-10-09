"""Unadopted material is evidence, not a pixel-test aesthetic certificate."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import unittest

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from hair_boundary import harmonic_rgb
import review_hair as hair
import review_review_v2 as parent
import build_review


class BoundarySolve(unittest.TestCase):
    def test_uniform_color_offset_reconciles_to_linear_parent_and_preserves_alpha(self):
        y,x = np.mgrid[:27,:31]
        before = np.empty((27,31,4),dtype=np.uint8)
        before[...,:3] = np.stack([80+x,90+y,100+x+y],axis=2)
        before[...,3] = (x*7+y*3)%256
        material = before.copy()
        material[...,:3] += np.array([10,15,20],dtype=np.uint8)
        domain = np.zeros((27,31),dtype=bool)
        domain[3:24,4:27] = True
        after,diagnostic = harmonic_rgb(before,material,domain)
        np.testing.assert_array_equal(after,before)
        self.assertLessEqual(diagnostic['relativeResidual'],1.1e-8)
        self.assertGreater(diagnostic['iterations'],0)

    def test_interior_strand_is_kept_when_boundary_already_matches(self):
        before = np.full((24,29,4),160,dtype=np.uint8)
        before[...,3] = 254
        material = before.copy()
        material[6:18,13:16,:3] = [120,100,80]
        domain = np.zeros((24,29),dtype=bool)
        domain[3:21,4:25] = True
        after,diagnostic = harmonic_rgb(before,material,domain)
        np.testing.assert_array_equal(after,material)
        np.testing.assert_array_equal(after[~domain],before[~domain])
        self.assertEqual(diagnostic['iterations'],0)

    def test_invalid_edge_domain_parameters_and_unconverged_solve_are_rejected(self):
        before = np.full((24,29,4),160,dtype=np.uint8)
        material = before.copy()
        material[...,:3] = 190
        domain = np.zeros((24,29),dtype=bool)
        domain[3:21,4:25] = True
        illegal = domain.copy()
        illegal[0,5] = True
        for mask in (illegal,domain.astype(np.uint8),domain[:4]):
            with self.assertRaises(ValueError):
                harmonic_rgb(before,material,mask)
        for kwargs in (dict(tolerance=float('nan')),dict(tolerance=True),dict(max_iterations=True),dict(max_iterations=2)):
            with self.assertRaises(ValueError):
                harmonic_rgb(before,material,domain,**kwargs)

    def test_empty_domain_is_exact_identity(self):
        before = np.arange(8*9*4,dtype=np.uint8).reshape(8,9,4)
        after,diagnostic = harmonic_rgb(before,255-before,np.zeros((8,9),dtype=bool))
        np.testing.assert_array_equal(after,before)
        self.assertEqual(diagnostic['iterations'],0)


class HairStudy(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base,cls.parent_spec,cls.raw = parent.inputs()
        cls.pose,cls.allowed,cls.preserved = parent.localized_pose(cls.base,cls.raw,cls.parent_spec)
        cls.spec = hair.specification()
        cls.results = {method:hair.repair(cls.pose,cls.parent_spec,cls.allowed,cls.preserved,method=method)
                       for method in cls.spec['compositingMethods']}
        cls.meta = json.loads((hair.OUT/'build.json').read_text())

    def test_both_experiments_preserve_every_parent_alpha_byte_and_protected_foreground(self):
        before = np.asarray(self.pose)
        expected_counts = {'bounded-feather':32881,'harmonic-rgb':32754}
        for method,(pose,allowed,protected,_,_) in self.results.items():
            with self.subTest(method=method):
                after = np.asarray(pose)
                changed = np.any(after!=before,axis=2)
                np.testing.assert_array_equal(after[~allowed],before[~allowed])
                np.testing.assert_array_equal(after[protected],before[protected])
                np.testing.assert_array_equal(after[...,3],before[...,3])
                self.assertFalse((allowed & ~self.allowed).any())
                self.assertEqual(int(changed.sum()),expected_counts[method])
                self.assertEqual(self.meta['methods'][method]['changedPixels'],expected_counts[method])
                self.assertEqual(self.meta['methods'][method]['outsidePermissionChangedPixels'],0)
                for x0,y0,x1,y1 in [(455,250,775,465),(433,1015,611,1226),(616,1015,795,1226),
                                     (440,635,610,735)]:
                    np.testing.assert_array_equal(after[y0:y1,x0:x1],before[y0:y1,x0:x1])

    def test_generated_crop_changes_clothing_but_none_of_those_pixels_are_adopted(self):
        before = np.asarray(self.pose)
        for pose,_,protected,mapped,_ in self.results.values():
            self.assertGreater(int((np.any(np.asarray(mapped)!=before,axis=2)&protected).sum()),0)
            np.testing.assert_array_equal(np.asarray(pose)[protected],before[protected])
        self.assertEqual(hair.load_generated().size,(1024,1536))
        self.assertEqual(self.spec['sourceCrop'],[680,540,1000,1020])
        self.assertEqual(1024/320,1536/480)
        self.assertEqual(hashlib.sha256((hair.OUT/'generated.png').read_bytes()).hexdigest().upper(),hair.GENERATED_SHA)

    def test_saved_pose_and_frame_are_exactly_reproducible_but_not_accepted(self):
        for method,(pose,_,_,_,_) in self.results.items():
            with Image.open(hair.OUT/f'{method}-pose.png') as saved:
                self.assertEqual(saved.convert('RGBA').tobytes(),pose.tobytes())
            self.assertEqual(hashlib.sha256(pose.tobytes()).hexdigest().upper(),self.meta['methods'][method]['poseRGBAHash'])
            with Image.open(hair.OUT/f'{method}-frame.png') as saved:
                self.assertEqual(hashlib.sha256(saved.convert('RGBA').tobytes()).hexdigest().upper(),
                                 self.meta['methods'][method]['frameRGBAHash'])
            self.assertFalse(self.meta['methods'][method]['adopted'])
        self.assertEqual(self.meta['visualAcceptance'],'not-accepted')
        for key in ('activeAtlasChanged','adopted','fullCropRedrawAccepted','handOrSleeveRepaintAccepted',
                    'facialGeometryRepair','installableFullAtlas','installed'):
            self.assertFalse(self.meta[key])

    def test_changed_parent_registration_permission_and_acceptance_claims_are_rejected(self):
        shifted = self.pose.copy()
        shifted.putpixel((800,800),(1,2,3,254))
        with self.assertRaises(ValueError):
            hair.repair(shifted,self.parent_spec,self.allowed,self.preserved)
        for key,value in [('sourceCrop',[680,530,1000,1020]),('rawCanvas',[1536,1024]),
                          ('hairPolygon',[[750,580],[950,650],[930,990]]),('adopted',True),
                          ('activePreviewSelected',True),('handOrSleeveRepaintAccepted',True)]:
            bad = copy.deepcopy(self.spec)
            bad[key] = value
            with self.assertRaises(ValueError):
                hair.repair(self.pose,self.parent_spec,self.allowed,self.preserved,spec=bad)
        bad_parent = copy.deepcopy(self.parent_spec)
        bad_parent['foregroundRightArmPolygon'] = [[500,680],[580,680],[550,740]]
        with self.assertRaises(ValueError):
            hair.repair(self.pose,bad_parent,self.allowed,self.preserved)
        with self.assertRaises(ValueError):
            hair.repair(self.pose,self.parent_spec,np.ones_like(self.allowed),self.preserved)
        with self.assertRaises(ValueError):
            hair.repair(self.pose,self.parent_spec,self.allowed,np.zeros_like(self.preserved))
        with self.assertRaises(ValueError):
            hair.repair(self.pose,self.parent_spec,self.allowed,self.preserved,method='promote-anyway')

    def test_rejected_old_pose_generation_and_studies_are_not_active_inputs(self):
        failed = json.loads((ROOT/'candidates/phase5/review-hair-v1/decision.json').read_text())
        self.assertFalse(failed['adopted'])
        self.assertNotEqual(failed['generatedSha256'],hair.GENERATED_SHA)
        self.assertEqual(build_review.art_inputs.__module__,'review_review_v5')
        active = json.loads((build_review.OUT/'build.json').read_text())
        self.assertEqual(active['rightArmCompositionVersion'],'review-art-v5')
        self.assertFalse(active['newArtworkGenerated'])
        self.assertEqual(self.meta['activeCompositionVersionAtExperiment'],'review-art-v2')


if __name__ == '__main__':
    unittest.main()
