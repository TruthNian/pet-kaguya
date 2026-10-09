"""Source-derived repair, alpha-exclusion root cause and active wiring."""
import hashlib
import json
from pathlib import Path
import sys
import unittest

import numpy as np
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from canonical import load_canonical
import repair_review_hair_holes as holes
import review_review_v5 as art
import build_review


class VisibleHairHoles(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with Image.open(ROOT/'candidates/phase5/review-art-v4/pose.png') as image:
            cls.before=image.convert('RGBA')
        cls.after,cls.holes,cls.visible,cls.protected=holes.repair(cls.before)
        cls.source=np.asarray(load_canonical())

    def test_actual_alpha_exclusion_not_color_or_hidden_strand_problem(self):
        before=np.asarray(self.before)
        self.assertEqual(int(self.holes.sum()),12)
        self.assertEqual(int(self.visible.sum()),2943)
        self.assertTrue(np.all(before[...,3][self.holes]==239))
        self.assertTrue(np.all(self.source[...,3][self.holes]>=240))
        # Counterfactual old gate removes exactly these real source pixels.
        self.assertEqual(int((self.visible & (before[...,3]>=240)).sum()),2931)
        for x,y in ((907,815),(907,817),(910,820)):
            self.assertTrue(self.holes[y,x])
            self.assertEqual(self.after.getpixel((x,y)),tuple(self.source[y,x]))

    def test_source_rgba_exact_including_opacity_and_every_other_pixel_unchanged(self):
        before,after=np.asarray(self.before),np.asarray(self.after)
        np.testing.assert_array_equal(after[self.visible],self.source[self.visible])
        np.testing.assert_array_equal(after[~self.holes],before[~self.holes])
        np.testing.assert_array_equal(after[self.protected],before[self.protected])
        self.assertFalse(np.any(self.holes & self.protected))
        self.assertEqual(int(np.any(before!=after,axis=2).sum()),12)
        self.assertEqual(int((before[...,3]!=after[...,3]).sum()),12)

    def test_saved_new_composition_and_active_builder_keep_original_hand_and_source(self):
        with Image.open(art.OUT/'pose.png') as image:
            self.assertEqual(image.convert('RGBA').tobytes(),self.after.tobytes())
        metadata=json.loads((art.OUT/'build.json').read_text(encoding='utf-8'))
        self.assertEqual(metadata['compositionVersion'],'review-art-v5')
        self.assertEqual(metadata['poseRGBAHash'],hashlib.sha256(self.after.tobytes()).hexdigest().upper())
        self.assertEqual(metadata['changedOutsideSourceHoles'],0)
        self.assertEqual(metadata['restoredSourceHolePixels'],12)
        self.assertEqual(metadata['knownSourceHairRestoredPixels'],2943)
        self.assertEqual(build_review.art_inputs.__module__,'review_review_v6')
        active=json.loads((build_review.OUT/'build.json').read_text(encoding='utf-8'))
        self.assertEqual(active['rightArmCompositionVersion'],'review-art-v6')
        actual=np.asarray(build_review.inputs()['armPose'])
        np.testing.assert_array_equal(actual[self.visible],self.source[self.visible])
        self.assertTrue(active['observedHairAlphaHolesRestored'])
        self.assertEqual(active['visualMotionApproval'],'pending')
        for key in ('facialGeometryRepair','newArtworkGenerated','hiddenHairReconstructionClaimed',
                    'cleanLayerRecoveryClaimed','installableFullAtlas','installed'):
            self.assertFalse(metadata[key])

    def test_uninspected_parent_or_non_rgba_rejected_without_modification(self):
        changed=self.before.copy()
        changed.putpixel((907,815),(1,2,3,238))
        original=changed.tobytes()
        with self.assertRaises(ValueError):holes.repair(changed)
        self.assertEqual(changed.tobytes(),original)
        with self.assertRaises(ValueError):holes.repair(self.before.convert('RGB'))


if __name__=='__main__':unittest.main()
