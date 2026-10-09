"""Current cloth edit limits/provenance; not an aesthetic certificate."""
import hashlib
import json
from pathlib import Path
import sys
import unittest
import numpy as np
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import review_cloth_v2 as cloth
import review_review_v6 as art
from review_sleeves import rgba_hash


class CurrentCloth(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base,cls.mapped=cloth.inputs()
        cls.pose,cls.allowed,cls.protected,cls.weight,_,cls.parts=cloth.compose(cls.base,cls.mapped)

    def test_only_connected_cloth_changes_hands_alpha_head_and_outline_exact(self):
        a,b=np.asarray(self.base),np.asarray(self.pose)
        np.testing.assert_array_equal(a[~self.allowed],b[~self.allowed])
        np.testing.assert_array_equal(a[self.protected],b[self.protected])
        np.testing.assert_array_equal(a[...,3],b[...,3])
        for x0,y0,x1,y1 in ((455,250,775,465),(432,626,622,739),(510,568,713,665)):
            np.testing.assert_array_equal(a[y0:y1,x0:x1],b[y0:y1,x0:x1])
        self.assertEqual(int(np.any(a!=b,axis=2).sum()),26025)
        self.assertEqual(self.parts,[11508,15058])
        self.assertFalse(np.asarray(self.weight)[~self.allowed].any())

    def test_actual_square_framing_and_raw_noncloth_redraw_are_not_hidden(self):
        with Image.open(cloth.OUT/'generated.png') as image:self.assertEqual(image.size,(1254,1254))
        self.assertEqual(hashlib.sha256((cloth.OUT/'generated.png').read_bytes()).hexdigest().upper(),cloth.GENERATED_SHA)
        for x,y in ((299,500),(960,600),(600,499),(600,1040)):
            self.assertEqual(self.base.getpixel((x,y)),self.mapped.getpixel((x,y)))
        meta=json.loads((cloth.OUT/'build.json').read_text(encoding='utf-8'))
        self.assertEqual(meta['rawChangedPixelsOutsidePermission'],322704)
        self.assertEqual(meta['changedOutsidePermission'],0)
        self.assertTrue(meta['newArtworkGenerated'])
        self.assertTrue(meta['adoptedIntoDevelopmentOnly'])
        self.assertEqual(meta['visualAcceptance'],'pending')
        self.assertFalse(meta['installed'])

    def test_changed_inputs_are_rejected_and_saved_v6_is_actual_local_edit(self):
        for which in (0,1):
            args=[self.base.copy(),self.mapped.copy()]
            args[which].putpixel((782,753),(1,2,3,255))
            with self.assertRaises(ValueError):cloth.compose(*args)
        with Image.open(art.OUT/'pose.png') as image:self.assertEqual(image.convert('RGBA').tobytes(),self.pose.tobytes())
        meta=json.loads((art.OUT/'build.json').read_text(encoding='utf-8'))
        self.assertEqual(meta['poseRGBAHash'],rgba_hash(self.pose))
        self.assertTrue(meta['handsRGBAExactFromV5'])
        self.assertFalse(meta['handsAndSleevesRGBAExact'])
        self.assertEqual(meta['changedPixelsFromV5'],26025)

    def test_current_gimp_project_was_reopened_and_exports_match_visible_rgba(self):
        folder=ROOT/'sources/editor/review-sleeves-v2'
        data=(folder/'kaguya-review-sleeves.xcf').read_bytes()
        self.assertTrue(data.startswith(b'gimp xcf '))
        self.assertEqual(hashlib.sha256(data).hexdigest().upper(),
                         'D14740AC19D212F46C7FDA73DC01780ED03B70ECA5B1D4C6E4AE04B1E5493B73')
        with Image.open(folder/'gimp-export.png') as image:export=np.asarray(image.convert('RGBA'))
        with Image.open(folder/'gimp-reopened-export.png') as image:reopened=np.asarray(image.convert('RGBA'))
        expected=np.asarray(self.pose);visible=(expected[...,3]>0)|(export[...,3]>0)
        np.testing.assert_array_equal(export,reopened)
        np.testing.assert_array_equal(export[visible],expected[visible])
        differences=np.any(export!=expected,axis=2)
        self.assertEqual(int(differences.sum()),859)
        self.assertTrue((expected[differences,3]==0).all())
        self.assertTrue((export[differences]==0).all())
        metadata=json.loads((folder/'editor-check.json').read_text(encoding='utf-8'))
        self.assertTrue(metadata['projectReopened'])
        self.assertEqual(metadata['parentCompositionVersion'],'review-art-v5')
        self.assertEqual(len(metadata['layers']),4)
        self.assertEqual(sum(layer['hasMask'] for layer in metadata['layers']),2)
        for key in ('nativeDesktopPaintingClaimed','cleanRigClaimed','installedPetChanged'):
            self.assertFalse(metadata[key])


if __name__=='__main__':unittest.main()
