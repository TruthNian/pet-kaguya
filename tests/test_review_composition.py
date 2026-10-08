"""Retiring the complete old sleeve is separate from preserving outside RGBA."""
import hashlib
import json
from pathlib import Path
import sys
import unittest

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import review_review as original
import review_review_v2 as repaired
from canonical import bounded_masks


class ReviewComposition(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base,cls.spec,cls.raw = repaired.inputs()
        cls.pose,cls.allowed,cls.preserved = repaired.localized_pose(cls.base,cls.raw,cls.spec)

    def test_historical_v1_is_still_exactly_reproducible(self):
        base,spec,raw = original.inputs()
        pose,allowed,_ = original.localized_pose(base,raw,spec)
        with Image.open(original.OUT/'pose.png') as saved:
            self.assertEqual(saved.convert('RGBA').tobytes(),pose.tobytes())
        changed = np.any(np.asarray(base)!=np.asarray(pose),axis=2)
        self.assertEqual(int(changed.sum()),69679)
        self.assertFalse((changed & ~allowed).any())
        metadata = json.loads((original.OUT/'build.json').read_text())
        self.assertEqual(hashlib.sha256(pose.tobytes()).hexdigest().upper(),metadata['poseRGBAHash'])

    def test_observed_residual_old_sleeve_hand_and_outline_are_fully_retired(self):
        _,weight,_ = bounded_masks(self.base.size,
            [self.spec['oldRightArmPolygon'],self.spec['foregroundRightArmPolygon']],1.5)
        # Actual v1 defects: lower green sleeve, old fingers/outline, shoulder
        # diagonal. Pin these inspected source locations, not a changed count.
        probes = [(885,930),(876,966),(933,734),(887,801),(839,611)]
        with Image.open(original.OUT/'pose.png') as image:
            previous = image.convert('RGBA')
        for x,y in probes:
            with self.subTest(sourcePixel=(x,y)):
                self.assertTrue(self.allowed[y,x])
                self.assertFalse(self.preserved[y,x])
                self.assertEqual(weight[y,x],1)
                self.assertEqual(self.pose.getpixel((x,y)),self.raw.getpixel((x,y)))
                self.assertNotEqual(previous.getpixel((x,y)),self.pose.getpixel((x,y)))

    def test_gesture_does_not_change_to_disguise_the_composition_error(self):
        _,spec,_ = original.inputs()
        self.assertEqual(spec['foregroundRightArmPolygon'],self.spec['foregroundRightArmPolygon'])
        self.assertEqual(spec['preservedForegroundPolygons'],self.spec['preservedForegroundPolygons'])
        with Image.open(original.OUT/'pose.png') as image:
            previous = np.asarray(image.convert('RGBA'))
        # Both held hands lie outside the expanded removal footprint.
        np.testing.assert_array_equal(np.asarray(self.pose)[635:730,440:600],previous[635:730,440:600])
        self.assertFalse(self.spec['newArtworkGenerated'])
        self.assertEqual(self.spec['visualAcceptance'],'pending')

    def test_repair_does_not_add_any_outside_permission_or_face_shoe_edits(self):
        before,after = np.asarray(self.base),np.asarray(self.pose)
        np.testing.assert_array_equal(after[~self.allowed],before[~self.allowed])
        np.testing.assert_array_equal(after[self.preserved],before[self.preserved])
        for x0,y0,x1,y1 in [(455,250,775,465),(433,1015,611,1226),(616,1015,795,1226)]:
            self.assertFalse(self.allowed[y0:y1,x0:x1].any())
            np.testing.assert_array_equal(after[y0:y1,x0:x1],before[y0:y1,x0:x1])


if __name__ == '__main__':
    unittest.main()
