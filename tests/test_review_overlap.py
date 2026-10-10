"""Static contact/cuff study and genuine editor evidence, not art approval."""
import hashlib
import json
from pathlib import Path
import sys
import unittest
import numpy as np
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import review_overlap as study
from guide_review_overlap import BOX,SIDE,square


class OverlapStudy(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.before,cls.mapped=study.inputs()
        cls.pose,cls.allowed,cls.protected,cls.weight=study.compose(cls.before,cls.mapped)

    def test_actual_fixed_square_input_projection_and_complete_face_exclusion(self):
        with Image.open(study.OUT/'edit-target.png') as image:target=image.convert('RGBA')
        self.assertEqual(target.tobytes(),square(self.before).tobytes())
        self.assertEqual(target.size,(SIDE,SIDE))
        self.assertIsNone(target.crop((0,250,310,310)).getbbox())
        self.assertGreater(BOX[1],465)
        with Image.open(study.OUT/'raw-mapped.png') as image:
            self.assertEqual(image.convert('RGBA').tobytes(),self.mapped.tobytes())

    def test_actual_composite_retains_all_alpha_and_every_outside_pixel(self):
        with Image.open(study.OUT/'static-candidate.png') as image:
            self.assertEqual(image.convert('RGBA').tobytes(),self.pose.tobytes())
        a,b=np.asarray(self.before),np.asarray(self.pose)
        self.assertTrue(np.array_equal(a[...,3],b[...,3]))
        self.assertTrue(np.array_equal(a[~self.allowed],b[~self.allowed]))
        self.assertTrue(np.array_equal(a[self.protected],b[self.protected]))
        self.assertFalse(np.any(self.allowed[:575]))
        self.assertFalse(np.any(self.allowed[825:]))
        self.assertFalse(np.any(self.allowed&self.protected))
        self.assertGreater(int(np.any(a!=b,axis=2).sum()),0)
        neutral,_,_,_=study.compose(self.before,self.before)
        self.assertEqual(neutral.tobytes(),self.before.tobytes())

    def test_both_failed_masks_are_reproducible_and_crop_alpha_fragments_are_rejected(self):
        for kwargs,name,expected in ((dict(first=True),'failed-first-mask.png',study.FIRST_POSE_HASH),
                                    (dict(second=True),'failed-second-mask.png',study.SECOND_POSE_HASH)):
            pose,_,_,_=study.compose(self.before,self.mapped,**kwargs)
            self.assertEqual(hashlib.sha256(pose.tobytes()).hexdigest().upper(),expected)
            with Image.open(study.OUT/name) as image:self.assertEqual(image.convert('RGBA').tobytes(),pose.tobytes())
        bad=self.mapped.copy();bad.putpixel((520,710),(1,2,3,35))
        self.assertTrue(self.allowed[710,520])
        with self.assertRaises(ValueError):study.compose(self.before,bad)
        with self.assertRaises(ValueError):study.compose(self.before,self.mapped.convert('RGB'))
        with self.assertRaises(ValueError):study.compose(self.before,self.mapped,first=True,second=True)

    def test_study_is_not_current_animation_or_approval_and_raw_rgba_remains_immutable(self):
        meta=json.loads((study.OUT/'build.json').read_text())
        for name in ('adopted','activeAtlasChanged','animationBuilt','installed','installableFullAtlas',
                     'faceIncluded','facialGeometryRepair','handScaled','heldTimingChangeAllowed'):
            self.assertFalse(meta[name])
        self.assertTrue(meta['completeParentAlphaPreserved'])
        self.assertEqual(meta['changedAlphaPixels'],0)
        self.assertEqual(meta['specificPoseUserApproval'],'pending')
        self.assertEqual(meta['visualAcceptance'],'pending')
        self.assertEqual(hashlib.sha256((study.OUT/'generated.png').read_bytes()).hexdigest().upper(),study.GENERATED_SHA)
        active=json.loads((ROOT/'candidates/phase5/review/build.json').read_text())
        self.assertEqual(active['rightArmCompositionVersion'],'review-art-v6')
        self.assertFalse(active['heldHandsUnchangedFromV5'])
        self.assertFalse(active['handUserApprovalClaimed'])
        with Image.open(study.OUT/'mapped-material.png') as image:material=np.asarray(image.convert('RGBA'))
        self.assertTrue(np.array_equal(material[...,3],np.asarray(self.before)[...,3]))
        self.assertTrue(np.array_equal(material[...,:3],np.asarray(self.mapped)[...,:3]))

    def test_actual_gimp_project_saved_reopened_and_visible_rgba_exact(self):
        folder=ROOT/'sources/editor/review-overlap'
        meta=json.loads((folder/'editor-check.json').read_text())
        data=(folder/'kaguya-review-overlap.xcf').read_bytes()
        self.assertTrue(data.startswith(b'gimp xcf '))
        self.assertEqual(hashlib.sha256(data).hexdigest().upper(),meta['projectSha256'])
        self.assertTrue(meta['projectReopened'])
        self.assertEqual(meta['parentCompositionVersion'],'review-art-v6')
        self.assertEqual(len(meta['layers']),4)
        self.assertEqual(sum(layer['hasMask'] for layer in meta['layers']),2)
        self.assertFalse(meta['nativeDesktopPaintingClaimed'])
        self.assertFalse(meta['cleanRigClaimed'])
        self.assertFalse(meta['activeAtlasChanged']);self.assertFalse(meta['installedPetChanged'])
        with Image.open(folder/'gimp-export.png') as image:export=np.asarray(image.convert('RGBA'))
        with Image.open(folder/'gimp-reopened-export.png') as image:reopened=np.asarray(image.convert('RGBA'))
        self.assertTrue(np.array_equal(export,reopened))
        expected=np.asarray(self.pose)
        self.assertTrue(np.array_equal(export[...,3],expected[...,3]))
        self.assertTrue(np.array_equal(export[expected[...,3]>0],expected[expected[...,3]>0]))


if __name__=='__main__':unittest.main()
