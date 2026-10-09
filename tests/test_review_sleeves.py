"""A continuous cloth mask/export check is not visual pose approval."""
import hashlib
import json
from pathlib import Path
import sys
import unittest

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import review_sleeves as sleeves


class SleeveStudy(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.parent,cls.mapped = sleeves.inputs()
        cls.pose,cls.allowed,cls.protected,cls.weight,cls.material,cls.parts = sleeves.study(cls.parent,cls.mapped)

    def test_current_face_hands_accessories_alpha_and_exterior_are_preserved(self):
        a,b = np.asarray(self.parent),np.asarray(self.pose)
        np.testing.assert_array_equal(a[~self.allowed],b[~self.allowed])
        np.testing.assert_array_equal(a[self.protected],b[self.protected])
        np.testing.assert_array_equal(a[...,3],b[...,3])
        for x0,y0,x1,y1 in [(455,250,775,465),(432,626,622,739),(855,570,980,1020),(433,1015,795,1226)]:
            np.testing.assert_array_equal(a[y0:y1,x0:x1],b[y0:y1,x0:x1])
        self.assertEqual(int(np.any(a!=b,axis=2).sum()),25937)
        self.assertEqual(int(self.allowed.sum()),26566)
        self.assertEqual(self.parts,[11508,15058])
        self.assertFalse(np.any(np.asarray(self.weight)[~self.allowed]))

    def test_changed_parent_material_are_rejected_and_hole_fill_does_not_expand_exterior(self):
        changed = self.parent.copy();changed.putpixel((782,753),(0,0,0,255))
        with self.assertRaises(ValueError):sleeves.study(changed,self.mapped)
        changed = self.mapped.copy();changed.putpixel((782,753),(0,0,0,255))
        with self.assertRaises(ValueError):sleeves.study(self.parent,changed)
        ring = np.zeros((9,9),dtype=bool);ring[2:7,2:7]=True;ring[4,4]=False
        expected = ring.copy();expected[4,4]=True
        np.testing.assert_array_equal(sleeves.fill_holes(ring),expected)
        ring[2:5,4]=False
        np.testing.assert_array_equal(sleeves.fill_holes(ring),ring)

    def test_saved_candidate_and_failed_pixel_mask_are_not_active_or_visual_acceptance(self):
        with Image.open(sleeves.OUT/'pose.png') as image:
            self.assertEqual(image.convert('RGBA').tobytes(),self.pose.tobytes())
        failed,permission,_,_,_,_ = sleeves.study(self.parent,self.mapped,continuous=False)
        with Image.open(sleeves.OUT/'failed-pixel-selection.png') as image:
            self.assertEqual(image.convert('RGBA').tobytes(),failed.tobytes())
        self.assertEqual(int(permission.sum()),25147)
        self.assertEqual(int(np.any(np.asarray(failed)!=np.asarray(self.parent),axis=2).sum()),23463)
        metadata = json.loads((sleeves.OUT/'build.json').read_text(encoding='utf-8'))
        self.assertEqual(metadata['poseRGBAHash'],sleeves.rgba_hash(self.pose))
        for key in ('adopted','activeAtlasChanged','installed','handScaled','facialGeometryRepair',
                    'cleanLayerRecoveryClaimed','articulatedArmBuilt','animationBuilt'):
            self.assertFalse(metadata[key])
        self.assertEqual(metadata['visualAcceptance'],'pending')
        self.assertEqual(metadata['changedOutsidePermission'],0)
        self.assertTrue(metadata['failedPixelSelectionRetained'])

    def test_archived_gimp_project_has_real_reopened_visible_pixel_evidence(self):
        folder = ROOT/'sources/editor/review-sleeves'
        project = (folder/'kaguya-review-sleeves.xcf').read_bytes()
        self.assertTrue(project.startswith(b'gimp xcf '))
        self.assertEqual(hashlib.sha256(project).hexdigest().upper(),
                         '210345F3D75865845DF0A872E25FEEB2E5A537F7300E1ED6E3C7A3EF6BC9341D')
        with Image.open(folder/'gimp-export.png') as image:export=np.asarray(image.convert('RGBA'))
        with Image.open(folder/'gimp-reopened-export.png') as image:reopened=np.asarray(image.convert('RGBA'))
        expected = np.asarray(self.pose)
        np.testing.assert_array_equal(export,reopened)
        visible = (expected[...,3]>0)|(export[...,3]>0)
        np.testing.assert_array_equal(export[visible],expected[visible])
        differences = np.any(export!=expected,axis=2)
        self.assertEqual(int(differences.sum()),859)
        self.assertTrue((expected[...,3][differences]==0).all())
        self.assertTrue((export[differences]==0).all())
        metadata=json.loads((folder/'editor-check.json').read_text(encoding='utf-8'))
        self.assertTrue(metadata['projectReopened'])
        self.assertEqual(metadata['editorVersion'],'3.2.6')
        self.assertEqual(metadata['parentCompositionVersion'],'review-art-v4')
        self.assertEqual(len(metadata['layers']),4)
        self.assertEqual(sum(layer['hasMask'] for layer in metadata['layers']),2)
        for key in ('nativeDesktopPaintingClaimed','cleanRigClaimed','activeAtlasChanged','installedPetChanged'):
            self.assertFalse(metadata[key])


if __name__=='__main__':unittest.main()
