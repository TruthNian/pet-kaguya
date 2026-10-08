"""Bounded regression checks; not an aesthetic acceptance oracle."""
import hashlib
import json
from pathlib import Path
import sys
import unittest

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from prepare_identity import load_source, SOURCE_HASH
from identity import static_masters, quiet_face, sad_face, head_mask
from protocol import ATLAS_SIZE, NAMES, crop


class Identity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = load_source()
        cls.original = crop(cls.source,0,0)
        cls.masters = static_masters(cls.source)

    def test_pre_expression_source_is_archived_and_immutable(self):
        self.assertEqual(self.source.size,ATLAS_SIZE)
        manifest=json.loads((ROOT/'sources/pre-expression/manifest.json').read_text())
        self.assertEqual(manifest['sha256'],SOURCE_HASH)
        self.assertEqual((ROOT/'sources/pre-expression/spritesheet.webp').stat().st_size,manifest['bytes'])
        self.assertEqual(hashlib.sha256((ROOT/'baseline/phase3/spritesheet.webp').read_bytes()).hexdigest().upper(),
                         '238C9ECEC64AB39B6F9CE04B9795E107996C1F97E06BA20B5E5A723EC940E3F1')

    def test_quiet_expression_cannot_change_chin_costume_or_outline(self):
        original=np.asarray(self.original)
        candidate=np.asarray(quiet_face(self.original))
        allowed=np.zeros(original.shape[:2],bool)
        allowed[63:74,89:106]=True
        self.assertTrue(np.array_equal(original[~allowed],candidate[~allowed]))
        self.assertTrue(np.array_equal(original[...,3],candidate[...,3]))
        self.assertTrue(np.array_equal(original[74:85],candidate[74:85]))

    def test_failed_preserves_eyes_chin_and_identity_outside_bounded_expression(self):
        original=np.asarray(self.original)
        candidate=np.asarray(sad_face(self.original))
        allowed=np.zeros(original.shape[:2],bool)
        allowed[63:74,89:106]=True
        allowed[37:47,102:121]=True
        self.assertTrue(np.array_equal(original[~allowed],candidate[~allowed]))
        self.assertTrue(np.array_equal(original[47:63,70:125],candidate[47:63,70:125]))
        self.assertTrue(np.array_equal(original[74:85],candidate[74:85]))
        self.assertTrue(np.array_equal(original[...,3],candidate[...,3]))

    def test_front_poses_share_pixels_in_reviewed_head_interior(self):
        master=np.asarray(self.masters[0])
        # No deformation/scale/blur is allowed in this face interior. Hand
        # occlusion is lower than this region and is tested separately.
        for row in [3,6,7,8]:
            self.assertTrue(np.array_equal(master[43:69,75:121],
                                           np.asarray(self.masters[row])[43:69,75:121]),f'face interior row {row}')
            # The chin-touching hand legitimately occludes the left chin; it
            # must not be required to match unobstructed face pixels there.
            start=90 if row==6 else (101 if row==8 else 83)
            self.assertTrue(np.array_equal(master[70:78,start:111],
                                           np.asarray(self.masters[row])[70:78,start:111]),f'visible chin row {row}')
            self.assertTrue(np.array_equal(master[10:41,114:137],
                                           np.asarray(self.masters[row])[10:41,114:137]),f'moon ornament row {row}')

    def test_waiting_hand_remains_in_foreground(self):
        donor=np.asarray(crop(self.source,7,1))
        candidate=np.asarray(self.masters[6])
        self.assertTrue(np.array_equal(donor[78:90,79:86],candidate[78:90,79:86]))

    def test_side_projections_are_not_front_face_swapped_or_mirrored(self):
        for row in [1,2]:
            self.assertTrue(np.array_equal(np.asarray(crop(self.source,row,0)),np.asarray(self.masters[row])))

    def test_saved_candidates_are_reproducible_rgba_and_unclipped(self):
        for row,im in enumerate(self.masters):
            saved=Image.open(ROOT/f'candidates/phase4/static/{NAMES[row]}.png').convert('RGBA')
            a=np.asarray(saved)
            self.assertTrue(np.array_equal(a,np.asarray(im)))
            self.assertFalse(a[0,:,3].any() or a[-1,:,3].any() or a[:,0,3].any() or a[:,-1,3].any())
            self.assertFalse(((a[...,3]==0)&np.any(a[...,:3]!=0,axis=2)).any())


if __name__ == '__main__':
    unittest.main()
