"""Recorded contour restoration and editor artifacts, not aesthetic approval."""
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
import repair_review_hand_outline as contour
import review_review_v4 as current


class HandContour(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.parent,cls.spec,cls.raw = contour.inputs()
        cls.pose,cls.allowed,cls.protected,cls.core,cls.skin = contour.repair(cls.parent,cls.spec,cls.raw)

    def test_original_outline_rgba_is_restored_without_scaling_or_exterior_edits(self):
        before,after,raw = map(np.asarray,(self.parent,self.pose,self.raw))
        np.testing.assert_array_equal(after[self.core],raw[self.core])
        np.testing.assert_array_equal(after[~self.allowed],before[~self.allowed])
        np.testing.assert_array_equal(after[self.protected],before[self.protected])
        self.assertEqual(int(np.any(before!=after,axis=2).sum()),2510)
        self.assertEqual(int((before[...,3]!=after[...,3]).sum()),1598)
        self.assertEqual(int(self.skin.sum()),2866)
        self.assertEqual(int(self.core.sum()),5121)
        for box in [(455,250,775,465),(433,1015,795,1226),(760,570,980,1020)]:
            x0,y0,x1,y1=box
            np.testing.assert_array_equal(after[y0:y1,x0:x1],before[y0:y1,x0:x1])

    def test_changed_raw_parent_or_permission_cannot_be_relabelled_as_same_repair(self):
        raw=self.raw.copy();raw.putpixel((560,700),(255,255,255,252))
        with self.assertRaises(ValueError):contour.repair(self.parent,self.spec,raw)
        parent=self.parent.copy();parent.putpixel((560,700),(255,255,255,252))
        with self.assertRaises(ValueError):contour.repair(parent,self.spec,self.raw)
        bad=copy.deepcopy(self.spec);bad['preservedForegroundPolygons']=[]
        with self.assertRaises(ValueError):contour.repair(self.parent,bad,self.raw)

    def test_active_art_uses_the_repaired_source_contour_without_full_pose_approval(self):
        with Image.open(current.OUT/'pose.png') as image:
            self.assertEqual(image.convert('RGBA').tobytes(),self.pose.tobytes())
        metadata=json.loads((current.OUT/'build.json').read_text(encoding='utf-8'))
        self.assertEqual(metadata['compositionVersion'],'review-art-v4')
        self.assertTrue(metadata['originalLowerHandContourRestored'])
        self.assertFalse(metadata['handScaled']);self.assertFalse(metadata['heldRightArmRGBAExact'])
        self.assertEqual(metadata['visualAcceptance'],'pending')
        self.assertFalse(metadata['installableFullAtlas']);self.assertFalse(metadata['installed'])

    def test_archived_real_gimp_xcf_reopened_export_matches_visible_rgba_exactly(self):
        folder=ROOT/'sources/editor/review-hand'
        project=(folder/'kaguya-review-hand.xcf').read_bytes()
        # This hash ties saved export evidence to the actual reopened project.
        # CI does not install GIMP or re-render XCF; edited projects need replay.
        self.assertTrue(project.startswith(b'gimp xcf '))
        self.assertEqual(hashlib.sha256(project).hexdigest().upper(),
                         'EE76825E3A0E3991AFE09CD503EBD27DE3033B351625D66C4DEAC276ACBD12E3')
        with Image.open(folder/'gimp-export.png') as image:export=np.asarray(image.convert('RGBA'))
        with Image.open(folder/'gimp-reopened-export.png') as image:reopened=np.asarray(image.convert('RGBA'))
        expected=np.asarray(self.pose)
        with Image.open(folder/'failed-normal-over.png') as image:failed=np.asarray(image.convert('RGBA'))
        self.assertEqual(int(np.any(failed!=expected,axis=2).sum()),7231)
        self.assertEqual(int(np.any(failed[self.core]!=np.asarray(self.raw)[self.core],axis=1).sum()),5121)
        np.testing.assert_array_equal(export,reopened)
        visible=(expected[...,3]>0)|(export[...,3]>0)
        np.testing.assert_array_equal(export[visible],expected[visible])
        np.testing.assert_array_equal(export[self.core],np.asarray(self.raw)[self.core])
        different=np.any(export!=expected,axis=2)
        self.assertEqual(int(different.sum()),859)
        self.assertTrue((expected[...,3][different]==0).all())
        self.assertTrue((export[different]==0).all())
        metadata=json.loads((folder/'editor-check.json').read_text(encoding='utf-8'))
        self.assertEqual(metadata['editorVersion'],'3.2.6');self.assertTrue(metadata['projectReopened'])
        self.assertEqual(len(metadata['layers']),4)
        self.assertEqual(sum(layer['hasMask'] for layer in metadata['layers']),2)
        self.assertFalse(metadata['nativeDesktopPaintingClaimed']);self.assertFalse(metadata['cleanRigClaimed'])


if __name__=='__main__':unittest.main()
