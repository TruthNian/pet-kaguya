"""Observation isolation and saved structure; no beauty or topology score."""
from pathlib import Path
import json
import sys
import unittest

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
import review_hair_boundary as study
from canonical import load_canonical


class HairBoundaryStudy(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.parent, cls.material, cls.masks = study.inputs()
        cls.pose, cls.diagnostics, cls.eligible = study.revise(cls.parent, cls.material,
                                                               cls.masks['known'], cls.masks['unknown'])

    def test_actual_source_known_pixels_and_every_exterior_alpha_hand_and_sleeve_are_exact(self):
        before, after = np.asarray(self.parent), np.asarray(self.pose)
        np.testing.assert_array_equal(after[~self.eligible], before[~self.eligible])
        np.testing.assert_array_equal(after[...,3], before[...,3])
        np.testing.assert_array_equal(after[self.masks['known']], np.asarray(load_canonical())[self.masks['known']])
        np.testing.assert_array_equal(after[self.masks['protected']], before[self.masks['protected']])
        self.assertTrue(np.any(before[self.eligible] != after[self.eligible]))

    def test_disconnected_unknown_islands_are_not_given_invented_observations(self):
        self.assertEqual(int(self.eligible.sum()),31550)
        self.assertEqual(int((self.masks['unknown'] & ~self.eligible).sum()),2)
        self.assertEqual(self.diagnostics['anchors'],490)
        self.assertEqual(sorted(part['pixels'] for part in self.diagnostics['components']),[1,1,31550])
        for x,y in ((852,934),(784,944)):
            self.assertFalse(self.eligible[y,x])
            self.assertEqual(self.parent.getpixel((x,y)),self.pose.getpixel((x,y)))

    def test_hidden_rgb_is_independent_of_changed_unobserved_foreground_or_old_exterior(self):
        # Change every unobserved/exterior pixel in the solve crop. Those
        # colors are never hair observations. Their exterior output remains
        # changed, but they must not affect any solved interior RGB/alpha.
        pixels = np.asarray(self.parent).copy()
        x0,y0,x1,y1 = study.BOX
        unobserved = ~(self.masks['known'] | self.masks['unknown'])[y0:y1,x0:x1]
        pixels[y0:y1,x0:x1][unobserved] = [13,241,7,255]
        altered,_,eligible = study.revise(Image.fromarray(pixels), self.material,
                                         self.masks['known'],self.masks['unknown'])
        np.testing.assert_array_equal(np.asarray(altered)[eligible],np.asarray(self.pose)[eligible])

    def test_declared_residual_and_clipping_are_actual_not_a_silent_exact_layer_claim(self):
        self.assertLessEqual(self.diagnostics['relativeResidual'],1.1e-8)
        self.assertGreater(self.diagnostics['iterations'],0)
        self.assertGreater(self.diagnostics['clippedChannels'],0)
        no_known = np.zeros_like(self.masks['known'])
        with self.assertRaises(ValueError):study.revise(self.parent,self.material,no_known,self.masks['unknown'])

    def test_saved_candidate_is_rebuildable_but_not_active_or_visually_approved(self):
        with Image.open(study.OUT/'pose.png') as image:
            self.assertEqual(image.convert('RGBA').tobytes(),self.pose.tobytes())
        metadata=json.loads((study.OUT/'build.json').read_text(encoding='utf-8'))
        self.assertEqual(metadata['poseRGBAHash'],study.rgba_hash(self.pose))
        self.assertEqual(metadata['solver'],study.recorded_diagnostics(self.diagnostics))
        self.assertEqual(metadata['visualAcceptance'],'pending')
        self.assertTrue(metadata['knownSourceRGBAExact'])
        self.assertTrue(metadata['parentAlphaPreserved'])
        for name in ('newArtworkGenerated','facialGeometryRepair','hiddenStrandTopologyRecovered',
                     'cleanLayerRecoveryClaimed','animationBuilt','adopted','activeAtlasChanged',
                     'installableFullAtlas','installed'):
            self.assertFalse(metadata[name])


if __name__=='__main__':unittest.main()
