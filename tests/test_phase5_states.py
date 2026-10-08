"""Bounded new artwork and actual failed poses; not an aesthetic certificate."""
import hashlib
import json
from pathlib import Path
import sys
import unittest

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
from canonical import load_canonical, clean_cutout, camera, bounded_artwork, ACCEPTED_SHA
import review_waiting as waiting
import review_failed as failed
from build_failed import inputs
from build_idle import coordinates, render
from protocol import DURATIONS


class Patches(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = load_canonical()
        cls.wait_spec, cls.fail_spec = waiting.specification(), failed.specification()
        cls.wait, cls.wait_allowed, cls.foreground = waiting.localized_pose(cls.source, waiting.load_generated(), cls.wait_spec)
        cls.fail, cls.fail_allowed = failed.localized_pose(cls.source, failed.load_generated(), cls.fail_spec)

    def test_both_patches_preserve_every_outside_rgba_pixel(self):
        original = np.asarray(self.source)
        for pose, allowed in [(self.wait, self.wait_allowed), (self.fail, self.fail_allowed)]:
            self.assertTrue(np.array_equal(original[~allowed], np.asarray(pose)[~allowed]))
            self.assertTrue(np.any(original[allowed] != np.asarray(pose)[allowed]))

    def test_waiting_face_only_allows_foreground_hand_occlusion(self):
        a, b = np.asarray(self.source), np.asarray(self.wait)
        protected = np.zeros(self.wait_allowed.shape, dtype=bool)
        protected[200:470, 425:815] = True
        self.assertFalse(self.wait_allowed[200:429, 425:815].any())
        self.assertTrue(np.array_equal(a[protected & ~self.foreground], b[protected & ~self.foreground]))
        self.assertFalse(self.wait_allowed[1015:].any())
        self.assertTrue(np.array_equal(a[:, 600:], b[:, 600:]))
        # Known original lowered-hand location is replaced; not proof of anatomy.
        self.assertFalse(np.array_equal(a[745, 310], b[745, 310]))

    def test_failed_preserves_eyes_jaw_chin_and_entire_costume(self):
        a, b = np.asarray(self.source), np.asarray(self.fail)
        for x0, y0, x1, y1 in self.fail_spec['eyeProtectedRects']:
            self.assertFalse(self.fail_allowed[y0:y1, x0:x1].any())
            self.assertTrue(np.array_equal(a[y0:y1, x0:x1], b[y0:y1, x0:x1]))
        self.assertFalse(self.fail_allowed[420:].any())
        self.assertTrue(np.array_equal(a[420:], b[420:]))
        self.assertFalse(self.fail_allowed[:, :505].any() or self.fail_allowed[:, 746:].any())

    def test_eye_overlap_and_independent_camera_change_are_rejected(self):
        bad = dict(self.fail_spec, expressionPolygons=self.fail_spec['expressionPolygons']+[[[640,275],[780,275],[780,375],[640,375]]])
        with self.assertRaises(ValueError):
            failed.localized_pose(self.source, failed.load_generated(), bad)
        with self.assertRaises(ValueError):
            bounded_artwork(self.source, Image.new('RGBA', (100, 100)), self.fail_spec['expressionPolygons'], 1.5)

    def test_saved_localized_poses_and_candidate_status_match_actual_source(self):
        for module, pose in [(waiting, self.wait), (failed, self.fail)]:
            metadata = json.loads((module.OUT/'build.json').read_text())
            with Image.open(module.OUT/'pose.png') as saved:
                self.assertEqual(pose.tobytes(), saved.convert('RGBA').tobytes())
            self.assertEqual(hashlib.sha256(pose.tobytes()).hexdigest().upper(), metadata['poseRGBAHash'])
            self.assertEqual(metadata['boundedChangedPixelsOutsidePatch'], 0)
            self.assertEqual(metadata['camera'], camera(clean_cutout(self.source)[0]))
            self.assertFalse(metadata['animationBuilt'] or metadata['installed'] or metadata['fullRedrawAccepted'])
            self.assertEqual(metadata['visualAcceptance'], 'pending')
        self.assertEqual(hashlib.sha256((ROOT/'sources/canonical/artwork.png').read_bytes()).hexdigest().upper(), ACCEPTED_SHA)


class FailedMotion(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source, cls.cleanup, cls.transform, cls.regions, cls.masks, cls.motion = inputs()
        cls.frames = [render(cls.source, pose, cls.transform, cls.regions, cls.masks) for pose in cls.motion['keyframes']]
        cls.out = ROOT/'candidates/phase5/failed'
        cls.metadata = json.loads((cls.out/'build.json').read_text())

    def test_actual_schedule_and_partial_candidate_boundary(self):
        self.assertEqual(self.metadata['durationsMs'], DURATIONS[5])
        self.assertEqual(self.metadata['totalDurationMs'], 1220)
        self.assertEqual(self.metadata['actionDurationMs'], 3660)
        self.assertEqual(self.metadata['repeatBeforeIdle'], 3)
        self.assertEqual(self.metadata['statesInThisArtifact'], ['failed'])
        self.assertEqual(self.metadata['sourceSha256'], ACCEPTED_SHA)
        self.assertEqual(self.metadata['expressionGeneratedSha256'], failed.GENERATED_SHA)
        self.assertFalse(self.metadata['facialGeometryRepair'] or self.metadata['installableFullAtlas'] or self.metadata['installed'])
        self.assertEqual(self.metadata['visualMotionApproval'], 'pending')

    def test_face_geometry_is_rigid_and_both_entire_shoes_are_pinned(self):
        x0, y0, x1, y1 = self.regions['protectedFace']
        yy, xx = np.mgrid[y0:y1, x0:x1].astype(float)
        for pose in self.motion['keyframes']:
            sx, sy = coordinates(xx, yy, pose, self.transform, self.regions, self.masks)
            self.assertTrue(np.array_equal(sx, xx))
            self.assertTrue(np.allclose(sy-yy, -pose['bodyY']/self.transform['scale'], atol=1e-12))
            for x0, y0, x1, y1 in self.regions['shoeProtectedRects']:
                y, x = np.mgrid[y0:y1, x0:x1].astype(float)
                sx, sy = coordinates(x, y, pose, self.transform, self.regions, self.masks)
                self.assertTrue(np.array_equal(sx, x) and np.array_equal(sy, y))
        for frame in self.frames:
            for box in [(73,181,93,199), (101,181,120,199)]:
                self.assertEqual(frame.crop(box).tobytes(), self.frames[0].crop(box).tobytes())

    def test_actual_authored_fields_do_not_fold(self):
        y, x = np.mgrid[10:1260:5, 80:1130:5].astype(float)
        for pose in self.motion['keyframes']:
            sxp, syp = coordinates(x+.1,y,pose,self.transform,self.regions,self.masks)
            sxm, sym = coordinates(x-.1,y,pose,self.transform,self.regions,self.masks)
            txp, typ = coordinates(x,y+.1,pose,self.transform,self.regions,self.masks)
            txm, tym = coordinates(x,y-.1,pose,self.transform,self.regions,self.masks)
            determinant = ((sxp-sxm)*(typ-tym)-(txp-txm)*(syp-sym))/.04
            self.assertGreater(float(determinant.min()), .95)

    def test_all_saved_frames_and_shared_camera_are_exactly_rebuildable(self):
        self.assertEqual(self.metadata['camera'], camera(clean_cutout(load_canonical())[0]))
        with Image.open(self.out/'strip.webp') as strip:
            self.assertEqual(strip.size, (1536,208))
            for index, frame in enumerate(self.frames):
                with Image.open(self.out/f'frame-{index}.png') as saved:
                    self.assertEqual(saved.convert('RGBA').tobytes(), frame.tobytes())
                self.assertEqual(strip.crop((index*192,0,(index+1)*192,208)).convert('RGBA').tobytes(), frame.tobytes())
                self.assertEqual(hashlib.sha256(frame.tobytes()).hexdigest().upper(), self.metadata['frameHashes'][index])
                rgba = np.asarray(frame)
                self.assertFalse(rgba[0,:,3].any() or rgba[-1,:,3].any() or rgba[:,0,3].any() or rgba[:,-1,3].any())
                self.assertFalse(((rgba[...,3] == 0) & np.any(rgba[...,:3] != 0, axis=2)).any())

    def test_gif_time_keeps_native_holds_even_if_palette_identical_holds_merge(self):
        with Image.open(self.out/'native-timing.gif') as gif:
            actual = []
            for index in range(gif.n_frames):
                gif.seek(index)
                actual.append(gif.info['duration'])
        self.assertEqual(sum(actual), 1220)
        cursor = 0
        for hold in actual:
            combined = 0
            while combined < hold and cursor < len(DURATIONS[5]):
                combined += DURATIONS[5][cursor]
                cursor += 1
            self.assertEqual(combined, hold)
        self.assertEqual(cursor, 8)


if __name__ == '__main__':
    unittest.main()
