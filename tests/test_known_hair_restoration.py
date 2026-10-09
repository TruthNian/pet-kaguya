"""Source anchors and actual graph coupling, not an aesthetic score."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import unittest

import numpy as np
from PIL import Image,ImageFilter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import restore_review_known_hair as restoration
import review_review_v2 as parent
import review_review_v3 as current
from canonical import load_canonical


class KnownHair(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base,cls.parent_spec,cls.raw = parent.inputs()
        cls.parent,cls.parent_allowed,cls.preserved = parent.localized_pose(cls.base,cls.raw,cls.parent_spec)
        cls.pose,cls.allowed,cls.protected,cls.known,cls.unknown = restoration.restore(
            cls.parent,cls.parent_spec,cls.parent_allowed,cls.preserved)
        cls.definition = restoration.specification()
        cls.meta = json.loads((current.OUT/'build.json').read_text())

    def test_known_source_rgba_remains_exact_after_unknown_boundary_solve(self):
        source,after = np.asarray(load_canonical()),np.asarray(self.pose)
        np.testing.assert_array_equal(after[self.known],source[self.known])
        self.assertEqual(int(self.known.sum()),2931)
        self.assertEqual(int(np.median(source[...,3][self.known])),253)
        self.assertFalse((self.known & self.unknown).any())
        self.assertEqual(self.meta['knownSourceHairRestoredPixels'],2931)

    def test_unknown_domain_actually_touches_the_known_anchors_without_a_dead_ring(self):
        self.assertEqual(restoration.shared_edges(self.known,self.unknown),490)
        # A former inward erosion silently left an old-pixel fence between
        # anchors and the solve. It converged numerically but got no RGB RHS.
        eroded = np.asarray(Image.fromarray(self.unknown.astype(np.uint8)*255).filter(ImageFilter.MinFilter(3)))>0
        self.assertEqual(restoration.shared_edges(self.known,eroded),0)
        changed = np.any(np.asarray(self.parent)[...,:3]!=np.asarray(self.pose)[...,:3],axis=2)
        self.assertEqual(int((changed & self.unknown).sum()),19729)
        self.assertEqual(self.meta['knownUnknownSharedBoundaryEdges'],490)
        self.assertEqual(int(self.unknown.sum()),31552)

    def test_no_current_foreground_original_face_shoe_or_outside_pixels_change(self):
        before,after = np.asarray(self.parent),np.asarray(self.pose)
        np.testing.assert_array_equal(after[~self.allowed],before[~self.allowed])
        np.testing.assert_array_equal(after[self.protected],before[self.protected])
        self.assertFalse((self.allowed & ~self.parent_allowed).any())
        for x0,y0,x1,y1 in [(455,250,775,465),(433,1015,611,1226),(616,1015,795,1226),
                             (440,635,610,735)]:
            np.testing.assert_array_equal(after[y0:y1,x0:x1],before[y0:y1,x0:x1])
        self.assertEqual(int(np.any(before!=after,axis=2).sum()),30117)
        self.assertEqual(int((before[...,3]!=after[...,3]).sum()),27784)
        # Inspected old sleeve/hand defects remain retired, not restored.
        for x,y in [(885,930),(876,966),(933,734),(887,801),(839,611)]:
            self.assertFalse(self.known[y,x])
            self.assertNotEqual(self.pose.getpixel((x,y)),load_canonical().getpixel((x,y)))

    def test_incompatible_source_pose_masks_and_overclaims_are_rejected(self):
        bad_pose = self.parent.copy()
        bad_pose.putpixel((905,880),(1,2,3,253))
        with self.assertRaises(ValueError):
            restoration.restore(bad_pose,self.parent_spec,self.parent_allowed,self.preserved)
        for key,value in [('knownHairPolygon',[[455,250],[775,250],[600,460]]),
                          ('unknownHairPolygon',[[800,float('nan')],[820,680],[850,720]]),
                          ('hiddenAlphaNominalValue',255),('handOrSleeveRepaintAllowed',True),
                          ('cleanLayerRecoveryClaimed',True),('hiddenHairReconstructionClaimed',True),
                          ('installed',True)]:
            bad = copy.deepcopy(self.definition)
            bad[key] = value
            with self.assertRaises(ValueError):
                restoration.restore(self.parent,self.parent_spec,self.parent_allowed,self.preserved,definition=bad)
        with self.assertRaises(ValueError):
            restoration.restore(self.parent,self.parent_spec,np.ones_like(self.parent_allowed),self.preserved)
        with self.assertRaises(ValueError):
            restoration.restore(self.parent,self.parent_spec,self.parent_allowed,np.zeros_like(self.preserved))

    def test_saved_pose_provenance_and_unapproved_scope_are_exact(self):
        with Image.open(current.OUT/'pose.png') as image:
            self.assertEqual(image.convert('RGBA').tobytes(),self.pose.tobytes())
        self.assertEqual(hashlib.sha256(self.pose.tobytes()).hexdigest().upper(),self.meta['poseRGBAHash'])
        with Image.open(current.OUT/'known-source-mask.png') as image:
            np.testing.assert_array_equal(np.asarray(image)>0,self.known)
        self.assertEqual(self.meta['compositionVersion'],'review-art-v3')
        self.assertEqual(self.meta['parentCompositionVersion'],'review-art-v2')
        self.assertEqual(self.meta['visualAcceptance'],'pending')
        self.assertEqual(self.meta['strategyUserApproval'],'pending')
        for key in ('newArtworkGenerated','animationBuilt','fullRedrawAccepted','facialGeometryRepair',
                    'articulatedArmBuilt','installableFullAtlas','installed'):
            self.assertFalse(self.meta[key])
        self.assertTrue(self.meta['knownSourceHairRGBAExact'])
        self.assertTrue(self.meta['paintedHairAlphaContinuityEstimated'])


if __name__ == '__main__':
    unittest.main()
