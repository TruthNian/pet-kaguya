"""Actual garment boundaries, immutable hand and integrated cels; not aesthetics."""
import hashlib
import json
from pathlib import Path
import sys
import unittest
import numpy as np
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import review_waiting_sleeve as cloth
import review_waiting_v2 as art
import review_waiting as original
from canonical import load_canonical


class WaitingSleeve(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base,cls.mapped=cloth.inputs()
        cls.pose,cls.allowed,cls.protected,cls.weight=cloth.compose(cls.base,cls.mapped)

    def test_complete_hand_head_torso_and_all_outside_pixels_are_exact(self):
        a,b=np.asarray(self.base),np.asarray(self.pose)
        np.testing.assert_array_equal(a[~self.allowed],b[~self.allowed])
        np.testing.assert_array_equal(a[self.protected],b[self.protected])
        hand=original.masks(original.specification())[2]
        np.testing.assert_array_equal(a[hand],b[hand])
        for x0,y0,x1,y1 in ((0,0,1205,480),(620,480,1205,1306),(0,1000,1205,1306)):
            np.testing.assert_array_equal(a[y0:y1,x0:x1],b[y0:y1,x0:x1])
        self.assertFalse((self.allowed&hand).any())
        self.assertFalse(np.asarray(self.weight)[~self.allowed].any())
        self.assertEqual(int(np.any(a!=b,axis=2).sum()),53583)
        # This is deliberately not an alpha-preserving recolor.
        self.assertEqual(int((a[...,3]!=b[...,3]).sum()),12314)

    def test_exact_fixed_square_mapping_keeps_padding_and_does_not_refit_object(self):
        with Image.open(cloth.OUT/'generated.png') as image:
            raw=image.convert('RGBA')
        self.assertEqual(raw.size,(1254,1254))
        square=raw.convert('RGBa').resize((495,495),Image.Resampling.LANCZOS).convert('RGBA')
        self.assertEqual(self.mapped.crop(cloth.BOX).tobytes(),square.crop((0,0,340,495)).tobytes())
        self.assertEqual(hashlib.sha256((cloth.OUT/'generated.png').read_bytes()).hexdigest().upper(),cloth.GENERATED_SHA)
        for which in (0,1):
            args=[self.base.copy(),self.mapped.copy()]
            args[which].putpixel((300,550),(1,2,3,255))
            with self.assertRaises(ValueError):cloth.compose(*args)

    def test_stitched_flower_failure_is_reproducible_not_erased(self):
        failed,_,_,_=cloth.compose(self.base,self.mapped,legacy_cape=True)
        with Image.open(cloth.OUT/'failed-cape-overlap.png') as image:
            self.assertEqual(image.convert('RGBA').tobytes(),failed.tobytes())
        self.assertEqual(cloth.rgba_hash(failed),'BCEFE68B708E08C6F1E0F0DA8F0F28C28B5B3D976837416CC27E25BBCA0070CE')
        self.assertNotEqual(failed.tobytes(),self.pose.tobytes())
        colors=cloth.cape_overlap_counts(self.base)
        self.assertEqual(colors['failed']['pinkColorPixels'],139)
        self.assertEqual(colors['corrected']['pinkColorPixels'],0)
        self.assertEqual(colors['corrected']['warmColorPixels'],4)
        # Color counts diagnose this mistake; they do not define the selection.
        meta=json.loads((cloth.OUT/'build.json').read_text())
        self.assertFalse(meta['colorDiagnosticIsSemanticSegmentation'])

    def test_current_v2_recomputes_over_original_pose_instead_of_using_full_redraw(self):
        pose,allowed,hand=art.localized_pose(load_canonical(),art.load_generated(),art.specification())
        self.assertEqual(pose.tobytes(),self.pose.tobytes())
        with Image.open(art.OUT/'pose.png') as image:self.assertEqual(image.convert('RGBA').tobytes(),pose.tobytes())
        meta=json.loads((art.OUT/'build.json').read_text())
        self.assertEqual(meta['compositionVersion'],'waiting-art-v2')
        self.assertEqual(meta['changedPixelsFromV1'],53583)
        self.assertEqual(meta['boundedChangedPixelsOutsidePatch'],0)
        self.assertEqual(meta['faceChangesOutsideForegroundHand'],0)
        self.assertTrue(meta['handRGBAExactFromV1'])
        self.assertEqual(meta['visualAcceptance'],'pending')
        for key in ('clothOnlyPixelChangeClaimed','cleanSemanticMatteClaimed','installed','fullRedrawAccepted'):
            self.assertFalse(meta[key])

    def test_actual_six_waiting_cels_are_exactly_the_global_row_not_static_mockups(self):
        folder=ROOT/'candidates/phase5/waiting'
        meta=json.loads((folder/'build.json').read_text())
        self.assertEqual(meta['clothGeneratedSha256'],cloth.GENERATED_SHA)
        self.assertEqual(meta['durationsMs'],[150,150,150,150,150,260])
        self.assertEqual(meta['actionDurationMs'],3030)
        with Image.open(folder/'strip.webp') as image:strip=image.convert('RGBA')
        with Image.open(ROOT/'candidates/phase5/global/spritesheet.webp') as image:atlas=image.convert('RGBA')
        self.assertEqual(atlas.crop((0,6*208,1536,7*208)).tobytes(),strip.tobytes())
        with Image.open(art.OUT/'frame.png') as image:self.assertEqual(strip.crop((0,0,192,208)).tobytes(),image.convert('RGBA').tobytes())
        for index in range(6):
            with Image.open(folder/f'frame-{index}.png') as image:
                cel=image.convert('RGBA')
            self.assertEqual(cel.tobytes(),strip.crop((192*index,0,192*(index+1),208)).tobytes())
            self.assertEqual(cloth.rgba_hash(cel),meta['frameHashes'][index])

    def test_actual_gimp_save_and_reopen_match_visible_rgba_not_fake_layers(self):
        folder=ROOT/'sources/editor/waiting-sleeve'
        data=(folder/'kaguya-waiting-sleeve.xcf').read_bytes()
        self.assertTrue(data.startswith(b'gimp xcf '))
        self.assertEqual(hashlib.sha256(data).hexdigest().upper(),
                         '1971F1687E1CF3FA7E14819A7175C56EB5B5DBB220B70BEA1834F048F860A51A')
        with Image.open(folder/'gimp-export.png') as image:export=np.asarray(image.convert('RGBA'))
        with Image.open(folder/'gimp-reopened-export.png') as image:reopened=np.asarray(image.convert('RGBA'))
        expected=np.asarray(self.pose);visible=(export[...,3]>0)|(expected[...,3]>0)
        np.testing.assert_array_equal(export,reopened)
        np.testing.assert_array_equal(export[visible],expected[visible])
        differences=np.any(export!=expected,axis=2)
        self.assertEqual(int(differences.sum()),859)
        self.assertTrue((expected[differences,3]==0).all())
        self.assertTrue((export[differences]==0).all())
        meta=json.loads((folder/'editor-check.json').read_text())
        self.assertTrue(meta['projectReopened'])
        self.assertEqual(meta['parentCompositionVersion'],'waiting-art-v1')
        self.assertEqual(meta['projectSha256'],hashlib.sha256(data).hexdigest().upper())
        self.assertEqual(len(meta['layers']),4)
        self.assertEqual(sum(layer['hasMask'] for layer in meta['layers']),2)
        self.assertTrue(meta['maskEditingRequiresBaseCompensationRebuild'])
        for key in ('nativeDesktopPaintingClaimed','cleanRigClaimed','installedPetChanged'):
            self.assertFalse(meta[key])


if __name__=='__main__':unittest.main()
