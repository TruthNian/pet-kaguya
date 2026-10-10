"""Actual lowered-wave pixels, not a visual approval or native FPS claim."""
import json
from pathlib import Path
import sys
import unittest

import numpy as np
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import study_wave_amplitude as study


class LoweredField(unittest.TestCase):
    def test_hand_translation_is_rigid_and_attachment_is_fixed(self):
        yy,xx=np.mgrid[545:660:2.3,295:426:2.1]
        px,py=study.forward(xx,yy,55)
        np.testing.assert_array_equal(px,xx)
        np.testing.assert_allclose(py,yy+55,rtol=0,atol=1e-12)
        yy,xx=np.mgrid[545:850:3.1,520:527:1.1]
        px,py=study.forward(xx,yy,55)
        np.testing.assert_array_equal(px,xx);np.testing.assert_array_equal(py,yy)

    def test_fractional_inverse_is_exact_and_area_preserved_not_shape_claimed(self):
        yy,xx=np.mgrid[545:1001:2.7,250:527:2.3]
        for amount in (0,20,55):
            sx,sy,error=study.inverse(xx,yy,amount)
            px,py=study.forward(sx,sy,amount)
            np.testing.assert_allclose(px,xx,rtol=0,atol=1e-12)
            np.testing.assert_allclose(py,yy,rtol=0,atol=1e-12)
            self.assertLess(error,1e-10)
            a,b=study.forward(xx,yy+.01,amount)
            c,d=study.forward(xx,yy-.01,amount)
            np.testing.assert_allclose((b-d)/.02,1,rtol=0,atol=1e-9)
        for bad in (-1,56,float('nan'),True):
            with self.assertRaises(ValueError):study.forward(xx,yy,bad)


class ActualWave(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.data=study.inputs()

    def test_zero_offset_reconstructs_frozen_old_peak_from_same_material(self):
        parent=json.loads((ROOT/study.REFERENCE/'contract.json').read_text())
        self.assertEqual(study.rgba_hash(study.native_frame(self.data['neutral'])),parent['frameHashes'][1])
        self.assertEqual(self.data['neutralMeasure']['changedOutsidePermission'],0)
        # First run cleared these invisible out-of-scope source RGB values.
        a=np.asarray(self.data['mother']);b=np.asarray(self.data['neutral'])
        self.assertEqual(a[565,270].tolist(),[1,0,0,0])
        np.testing.assert_array_equal(a[565,270],b[565,270])

    def test_cloth_repair_cannot_repaint_estimated_palm_or_locked_foreground(self):
        data=self.data;a=np.asarray(data['lowered']);b=np.asarray(data['repaired'])
        np.testing.assert_array_equal(a[data['handMask']],b[data['handMask']])
        np.testing.assert_array_equal(a[data['data']['protected']],b[data['data']['protected']])
        changed=np.any(a!=b,axis=2)
        self.assertGreater(int(changed.sum()),10000)
        self.assertFalse(np.any(changed&~data['repairAllowed']))
        self.assertTrue(data['repairMeasure']['handProtectionEstimated'])
        self.assertGreater(data['repairMeasure']['oldBrightRedClothExcludedFromHandProtection'],0)
        self.assertNotEqual(data['failedRepair'].tobytes(),data['repaired'].tobytes())

    def test_actual_four_holds_only_replace_peak_and_use_saved_pixels(self):
        data=self.data;meta=json.loads((study.OUT/'build.json').read_text())
        for i,frame in enumerate(data['frames']):
            with Image.open(study.OUT/f'frame-{i}.png') as saved:
                self.assertEqual(saved.convert('RGBA').tobytes(),frame.tobytes())
            self.assertEqual(study.rgba_hash(frame),meta['frameHashes'][i])
            if i!=1:self.assertEqual(data['baseline'][i].tobytes(),frame.tobytes())
        self.assertNotEqual(data['baseline'][1].tobytes(),data['frames'][1].tobytes())
        self.assertEqual(data['frames'][0].tobytes(),data['frames'][2].tobytes())
        self.assertEqual(data['frames'][3].tobytes(),study.native_frame(data['mother']).tobytes())
        self.assertAlmostEqual(meta['handLoweringNativePx'],55*.15833333333333333)
        self.assertEqual(meta['durationsMs'],[140,140,140,280])

    def test_actual_native_changes_stay_in_arm_window_and_only_basis_approved(self):
        a,b=np.asarray(self.data['baseline'][1]),np.asarray(self.data['frames'][1])
        allowed=np.zeros(a.shape[:2],dtype=bool);allowed[88:173,37:86]=True
        np.testing.assert_array_equal(a[~allowed],b[~allowed])
        meta=json.loads((study.OUT/'build.json').read_text())
        self.assertTrue(meta['amplitudeDirectionUserApproved'])
        self.assertEqual(meta['visualMotionApproval'],'pending')
        self.assertTrue(meta['adopted']);self.assertTrue(meta['activeAtlasChanged'])
        self.assertEqual(meta['adoptionScope'],'waving-lower-amplitude-development-basis-only')
        self.assertEqual(meta['userDecision'],study.ADOPTION)
        for key in ('installableFullAtlas','installed','nativeInterpolation'):
            self.assertFalse(meta[key])

    def test_approved_peak_and_other_holds_are_exact_current_production_pixels(self):
        current=json.loads((ROOT/'candidates/phase5/waving/build.json').read_text())
        meta=json.loads((study.OUT/'build.json').read_text())
        self.assertEqual(current['frameHashes'],meta['frameHashes'])
        self.assertEqual(current['frameHashes'][1],study.APPROVED_PEAK)
        self.assertTrue(meta['currentWavingCelsRGBAExact'])
        with Image.open(ROOT/'candidates/phase5/waving/strip.webp') as saved:
            strip=saved.convert('RGBA')
        for i,frame in enumerate(self.data['frames']):
            self.assertEqual(strip.crop((192*i,0,192*(i+1),208)).tobytes(),frame.tobytes())

    def test_entire_global_atlas_only_replaces_the_approved_peak_cell(self):
        # Replacing just the new peak with the frozen old cel must reproduce
        # the exact pre-adoption atlas, including look rows/unused columns.
        with Image.open(ROOT/'candidates/phase5/global/spritesheet.webp') as saved:
            atlas=saved.convert('RGBA')
        self.assertEqual(atlas.crop((192,624,384,832)).tobytes(),self.data['frames'][1].tobytes())
        atlas.paste(self.data['baseline'][1],(192,624))
        self.assertEqual(study.rgba_hash(atlas),
            '1E1D25A012688E96CC1D4A59AD96696145B52DB7E7C9DAEF39AF9273A2128786')


if __name__=='__main__':unittest.main()
