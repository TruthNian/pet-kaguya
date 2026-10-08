"""Identity, contact and discrete-time proofs; not motion/aesthetic approval."""
import hashlib
import json
from pathlib import Path
import sys
import unittest

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
from canonical import load_canonical, clean_cutout, camera, ACCEPTED_SHA
from build_idle import coordinates, render
import build_jumping as jumping
import review_arm_backing as backing
from protocol import DURATIONS


class HiddenBacking(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = load_canonical()
        cls.spec = backing.specification()
        cls.plate, cls.allowed = backing.localized_backing(cls.source, backing.load_generated(), cls.spec)

    def test_outside_and_preserved_foreground_are_exact_source_pixels(self):
        a, b = np.asarray(self.source), np.asarray(self.plate)
        self.assertTrue(np.array_equal(a[~self.allowed], b[~self.allowed]))
        self.assertGreater(np.count_nonzero(np.any(a != b, axis=2)), 50000)
        for x0, y0, x1, y1 in self.spec['protectedRects']:
            self.assertTrue(np.array_equal(a[y0:y1,x0:x1], b[y0:y1,x0:x1]))
        mask = Image.new('L', self.source.size)
        for polygon in self.spec['preservedForegroundPolygons']:
            ImageDraw.Draw(mask).polygon(polygon, fill=255)
        selected = np.asarray(mask) > 0
        self.assertFalse(self.allowed[selected].any())
        self.assertTrue(np.array_equal(a[selected], b[selected]))

    def test_patch_cannot_repaint_face_even_with_a_bad_polygon(self):
        bad = dict(self.spec, armFootprintPolygon=[[450,240],[780,240],[780,475],[450,475]])
        with self.assertRaises(ValueError):
            backing.localized_backing(self.source, backing.load_generated(), bad)

    def test_saved_plate_is_rebuildable_and_not_a_pet_pose_or_arm_rig(self):
        metadata = json.loads((backing.OUT/'build.json').read_text())
        with Image.open(backing.OUT/'backing.png') as image:
            self.assertEqual(image.convert('RGBA').tobytes(), self.plate.tobytes())
        self.assertEqual(metadata['backingRGBAHash'], hashlib.sha256(self.plate.tobytes()).hexdigest().upper())
        self.assertEqual(metadata['boundedChangedPixelsOutsidePatch'], 0)
        self.assertEqual(metadata['camera'], camera(clean_cutout(self.source)[0]))
        self.assertFalse(metadata['articulatedArmBuilt'] or metadata['animationBuilt']
                         or metadata['fullRedrawAccepted'] or metadata['installed'] or metadata['installableFullAtlas'])
        self.assertEqual(metadata['visualAcceptance'], 'pending')
        self.assertIn('not a pet pose', metadata['role'])


class Hop(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source, cls.cleanup, cls.transform, cls.regions, cls.masks, cls.motion, cls.poses = jumping.inputs()
        cls.frames = [render(cls.source, pose, cls.transform, cls.regions, cls.masks) for pose in cls.poses]
        cls.metadata = json.loads((jumping.OUT/'build.json').read_text())

    def test_flight_samples_and_real_holds_define_contact_not_continuous_playback(self):
        self.assertEqual(self.metadata['durationsMs'], DURATIONS[4])
        self.assertEqual(self.metadata['totalDurationMs'], 840)
        self.assertEqual(self.metadata['actionDurationMs'], 2520)
        self.assertEqual(self.metadata['groundedFrames'], [0,4])
        self.assertEqual([p.get('flightTimeMs') for p in self.poses[1:4]], [70,210,350])
        np.testing.assert_allclose(self.metadata['actorOffsetsPx'], [0,-40/9,-8,-40/9,0], atol=1e-12)
        self.assertFalse(self.metadata['nativeInterpolation'])

    def test_face_and_flying_shoes_only_rigidly_translate_never_resize(self):
        scale = self.transform['scale']
        for pose in self.poses:
            x0,y0,x1,y1 = self.regions['protectedFace']
            yy, xx = np.mgrid[y0:y1, x0:x1].astype(float)
            # Inverse sampling starts in actor coordinates, not a refit camera.
            world_y = yy+pose['actorY']/scale
            sx,sy = coordinates(xx, world_y-pose['actorY']/scale, pose, self.transform, self.regions, self.masks)
            np.testing.assert_allclose(sx,xx,atol=1e-12)
            np.testing.assert_allclose(sy-world_y,-(pose['actorY']+pose['bodyY'])/scale,atol=1e-12)
            for x0,y0,x1,y1 in self.regions['shoeProtectedRects']:
                yy,xx = np.mgrid[y0:y1,x0:x1].astype(float)
                sx,sy = coordinates(xx,yy,pose,self.transform,self.regions,self.masks)
                self.assertTrue(np.array_equal(sx,xx) and np.array_equal(sy,yy))

    def test_grounded_shoe_pixels_and_camera_are_identical_to_zero_pose(self):
        zero = render(self.source, dict(bodyY=0,earAngle=0,hairAngle=0), self.transform,self.regions,self.masks)
        for index in (0,4):
            for box in [(73,181,93,199),(101,181,120,199)]:
                self.assertEqual(self.frames[index].crop(box).tobytes(),zero.crop(box).tobytes())
        self.assertEqual(self.metadata['camera'],camera(self.source))
        self.assertEqual(self.metadata['sourceSha256'],ACCEPTED_SHA)

    def test_frames_strip_alpha_and_metadata_rebuild(self):
        with Image.open(jumping.OUT/'strip.webp') as strip:
            self.assertEqual(strip.size,(1536,208))
            for index,frame in enumerate(self.frames):
                with Image.open(jumping.OUT/f'frame-{index}.png') as saved:
                    self.assertEqual(saved.convert('RGBA').tobytes(),frame.tobytes())
                self.assertEqual(strip.crop((index*192,0,(index+1)*192,208)).convert('RGBA').tobytes(),frame.tobytes())
                self.assertEqual(hashlib.sha256(frame.tobytes()).hexdigest().upper(),self.metadata['frameHashes'][index])
                pixels = np.asarray(frame)
                self.assertFalse(pixels[0,:,3].any() or pixels[-1,:,3].any() or pixels[:,0,3].any() or pixels[:,-1,3].any())
                self.assertFalse(((pixels[...,3]==0) & np.any(pixels[...,:3]!=0,axis=2)).any())
            self.assertIsNone(strip.crop((960,0,1536,208)).getbbox())
        self.assertFalse(self.metadata['facialGeometryRepair'] or self.metadata['installed'] or self.metadata['installableFullAtlas'])
        self.assertEqual(self.metadata['visualMotionApproval'],'pending')

    def test_all_fields_keep_positive_jacobian(self):
        y,x = np.mgrid[10:1260:5,80:1130:5].astype(float)
        for pose in self.poses:
            xp,yp = coordinates(x+.1,y,pose,self.transform,self.regions,self.masks)
            xm,ym = coordinates(x-.1,y,pose,self.transform,self.regions,self.masks)
            ux,uy = coordinates(x,y+.1,pose,self.transform,self.regions,self.masks)
            vx,vy = coordinates(x,y-.1,pose,self.transform,self.regions,self.masks)
            determinant = ((xp-xm)*(uy-vy)-(ux-vx)*(yp-ym))/.04
            self.assertGreater(float(determinant.min()),.95)

    def test_gif_preserves_native_held_schedule(self):
        with Image.open(jumping.OUT/'native-timing.gif') as gif:
            holds = []
            for index in range(gif.n_frames):
                gif.seek(index)
                holds.append(gif.info['duration'])
        self.assertEqual(holds,DURATIONS[4])


if __name__ == '__main__':
    unittest.main()
