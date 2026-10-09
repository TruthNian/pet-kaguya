"""Specific geometry/editor evidence, not approval of the rough motion."""
import hashlib
import json
from pathlib import Path
import sys
import unittest

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import review_source_arm as arm
import review_source_backing as plate


class SourceArmStudy(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = arm.materials(background_override=plate.load_projected())
        cls.poses = [arm.pose(cls.data,angle) for angle in arm.ANGLES]

    def test_zero_angle_reconstructs_with_the_same_material_and_valid_rgb(self):
        data = self.data
        beta = data['beta'][...,None]
        source = np.asarray(data['mother'])
        expected = data['foreground']+(1-beta)*np.asarray(data['background'])[...,:3]
        np.testing.assert_allclose(expected,source[...,:3],atol=1e-9,rtol=0)
        self.assertTrue((data['foreground']>=-1e-9).all())
        self.assertTrue((data['foreground']<=255*beta+1e-9).all())
        self.assertEqual(self.poses[0][0].tobytes(),data['mother'].tobytes())
        self.assertEqual(self.poses[-1][0].tobytes(),data['mother'].tobytes())
        np.testing.assert_array_equal(np.asarray(data['background'])[data['beta']==0],
                                      source[data['beta']==0])

    def test_motion_preserves_alpha_and_all_protected_source_pixels(self):
        a = np.asarray(self.data['mother'])
        for image,metadata in self.poses:
            b = np.asarray(image)
            np.testing.assert_array_equal(a[...,3],b[...,3])
            np.testing.assert_array_equal(a[~self.data['allowed']],b[~self.data['allowed']])
            np.testing.assert_array_equal(a[self.data['protected']],b[self.data['protected']])
            self.assertEqual(metadata['changedOutsidePermission'],0)
            self.assertGreaterEqual(metadata['minimumForwardJacobian'],.90)
            self.assertLessEqual(metadata['maximumInverseErrorSourcePx'],1e-5)
        # Previously missed old-hem antialiasing, not a claim of clean matte.
        self.assertGreater(self.data['beta'][982,350],0)
        self.assertGreater(self.data['beta'][983,346],0)

    def test_palm_rotation_length_and_fixed_attachment_are_independently_checked(self):
        x = np.array([300.,342.,356.]);y = np.array([745.,743.,743.])
        ex,ey = arm.ELBOW
        for angle in arm.ANGLES:
            theta = np.radians(angle)
            expected_x = ex+(x-ex)*np.cos(theta)-(y-ey)*np.sin(theta)
            expected_y = ey+(x-ex)*np.sin(theta)+(y-ey)*np.cos(theta)
            px,py = arm.forward(x,y,angle)
            np.testing.assert_allclose(px,expected_x,atol=1e-10,rtol=0)
            np.testing.assert_allclose(py,expected_y,atol=1e-10,rtol=0)
            for point in (arm.SHOULDER,arm.ELBOW):
                sx,sy = arm.forward(np.array([point[0]]),np.array([point[1]]),angle)
                np.testing.assert_array_equal([sx[0],sy[0]],point)
            self.assertAlmostEqual(np.hypot(px[-1]-ex,py[-1]-ey),
                                   np.hypot(arm.WRIST[0]-ex,arm.WRIST[1]-ey),places=9)

    def test_upper_cuff_is_not_wholly_rigid_and_invalid_motion_fails_closed(self):
        x,y = np.array([314.]),np.array([678.])
        ex,ey = arm.ELBOW;theta = np.radians(6.)
        expected = [ex+(x[0]-ex)*np.cos(theta)-(y[0]-ey)*np.sin(theta),
                    ey+(x[0]-ex)*np.sin(theta)+(y[0]-ey)*np.cos(theta)]
        px,py = arm.forward(x,y,6.)
        self.assertGreater(np.hypot(px[0]-expected[0],py[0]-expected[1]),.1)
        for angle in (True,np.nan,np.inf,-7,9):
            with self.assertRaises(ValueError): arm.forward(x,y,angle)
        with self.assertRaises(ValueError): arm.materials(background_override=Image.new('RGBA',(2,2)))

    def test_saved_four_cels_and_real_holds_are_isolated_unapproved_artifacts(self):
        folder = ROOT/'candidates/phase5/wave-source-rig-v2'
        metadata = json.loads((folder/'build.json').read_text(encoding='utf-8'))
        self.assertEqual(metadata['durationsMs'],[140,140,140,280])
        self.assertEqual(metadata['totalDurationMs'],700)
        self.assertEqual(metadata['repeatBeforeIdle'],3)
        self.assertFalse(metadata['palmAndCuffShareRotation'])
        for key in ('adopted','activeAtlasChanged','installableFullAtlas','installed',
                    'facialGeometryRepair','cleanLayerRecoveryClaimed','articulatedArmBuilt','nativeInterpolation'):
            self.assertFalse(metadata[key])
        self.assertEqual(metadata['visualMotionApproval'],'pending')
        with Image.open(arm.OUT/'failed-incomplete-aa-pose.png') as fixture:
            self.assertEqual(arm.rgba_hash(fixture.convert('RGBA')),arm.FAILED_AA_RGBA)
        for i,(image,measure) in enumerate(self.poses):
            with Image.open(folder/f'pose-{i}.png') as saved:
                self.assertEqual(saved.convert('RGBA').tobytes(),image.tobytes())
            self.assertEqual(metadata['measurements'][i],measure)
        with Image.open(folder/'strip.webp') as image:
            self.assertEqual(image.size,(1536,208))
            self.assertIsNone(image.convert('RGBA').crop((768,0,1536,208)).getbbox())
        with Image.open(folder/'native-timing.gif') as gif:
            holds=[]
            for i in range(gif.n_frames):
                gif.seek(i);holds.append(gif.info['duration'])
            self.assertEqual(holds,[140,140,140,280])
            self.assertEqual(gif.info['loop'],0) # QA loop, NOT native three-cycle proof.

    def test_real_gimp_save_reopen_preserves_visible_neutral_material(self):
        folder = ROOT/'sources/editor/source-arm'
        raw = (folder/'kaguya-source-arm.xcf').read_bytes()
        self.assertTrue(raw.startswith(b'gimp xcf '))
        self.assertEqual(hashlib.sha256(raw).hexdigest().upper(),
                         '550EDDF01152CDD27C699B6C7B3C886CAA6FE0986567C36AE839F4127D0A79F4')
        with Image.open(folder/'gimp-export.png') as image: a=np.asarray(image.convert('RGBA'))
        with Image.open(folder/'gimp-reopened-export.png') as image: b=np.asarray(image.convert('RGBA'))
        np.testing.assert_array_equal(a,b)
        source = np.asarray(self.data['mother'])
        visible = (source[...,3]>0)|(a[...,3]>0)
        np.testing.assert_array_equal(a[visible],source[visible])
        changed = np.any(a!=source,axis=2)
        self.assertEqual(int(changed.sum()),859)
        self.assertTrue((source[...,3][changed]==0).all())
        self.assertTrue((a[changed]==0).all())
        metadata = json.loads((folder/'editor-check.json').read_text(encoding='utf-8'))
        self.assertTrue(metadata['projectReopened'])
        self.assertEqual(len(metadata['layers']),5)
        self.assertEqual(sum(layer['hasMask'] for layer in metadata['layers']),2)
        self.assertFalse(metadata['nativeDesktopPaintingClaimed'])
        self.assertFalse(metadata['cleanRigClaimed'])


if __name__=='__main__': unittest.main()
