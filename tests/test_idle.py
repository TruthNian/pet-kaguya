"""Actual idle rig checks; not a naturalness/cuteness certificate."""
import hashlib
import json
from pathlib import Path
import sys
import unittest

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
from canonical import load_canonical, clean_cutout, camera, ACCEPTED_SHA
from build_idle import specification, region_masks, coordinates, render
from protocol import DURATIONS


class Idle(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original = load_canonical()
        cls.source, cls.cleanup = clean_cutout(cls.original)
        cls.transform = camera(cls.source)
        cls.regions, cls.motion = specification()
        cls.masks = region_masks(cls.regions)
        cls.metadata = json.loads((ROOT/'candidates/phase5/idle/build.json').read_text())
        cls.frames = [render(cls.source, p, cls.transform, cls.regions, cls.masks) for p in cls.motion['keyframes']]

    def test_cleanup_does_not_threshold_away_painted_outline_or_touch_source(self):
        before, after = np.asarray(self.original), np.asarray(self.source)
        self.assertTrue(np.array_equal(before[before[..., 3] > 8], after[before[..., 3] > 8]))
        removed = (before[..., 3] > 0) & (after[..., 3] == 0)
        self.assertLessEqual(int(before[..., 3][removed].max()), 8)
        self.assertEqual(hashlib.sha256((ROOT/'sources/canonical/artwork.png').read_bytes()).hexdigest().upper(), ACCEPTED_SHA)
        self.assertGreater(self.cleanup['distantVeryFaintPixelsRemoved'], 0)

    def test_face_is_exact_rigid_translation_not_a_local_shape_warp(self):
        x0, y0, x1, y1 = self.regions['protectedFace']
        yy, xx = np.mgrid[y0:y1, x0:x1].astype(float)
        for pose in self.motion['keyframes']:
            sx, sy = coordinates(xx, yy, pose, self.transform, self.regions, self.masks)
            self.assertTrue(np.array_equal(sx, xx))
            self.assertTrue(np.allclose(sy-yy, -pose['bodyY']/self.transform['scale'], atol=1e-12))

    def test_each_entire_shoe_is_fixed_not_just_lowest_pixel(self):
        for x0, y0, x1, y1 in self.regions['shoeProtectedRects']:
            yy, xx = np.mgrid[y0:y1, x0:x1].astype(float)
            for pose in self.motion['keyframes']:
                sx, sy = coordinates(xx, yy, pose, self.transform, self.regions, self.masks)
                self.assertTrue(np.array_equal(sx, xx))
                self.assertTrue(np.array_equal(sy, yy))
        # Interiors remain bit-identical after actual coverage sampling too.
        for frame in self.frames:
            for box in [(73, 181, 93, 199), (101, 181, 120, 199)]:
                self.assertEqual(frame.crop(box).tobytes(), self.frames[0].crop(box).tobytes())

    def test_all_authored_poses_have_positive_sampled_jacobian(self):
        yy, xx = np.mgrid[10:1260:5, 80:1130:5].astype(float)
        for pose in self.motion['keyframes']:
            sxp, syp = coordinates(xx+.1, yy, pose, self.transform, self.regions, self.masks)
            sxm, sym = coordinates(xx-.1, yy, pose, self.transform, self.regions, self.masks)
            txp, typ = coordinates(xx, yy+.1, pose, self.transform, self.regions, self.masks)
            txm, tym = coordinates(xx, yy-.1, pose, self.transform, self.regions, self.masks)
            determinant = ((sxp-sxm)*(typ-tym)-(txp-txm)*(syp-sym))/.04
            self.assertGreater(float(determinant.min()), .95)

    def test_saved_native_poses_schedule_padding_and_terminal_hold(self):
        self.assertEqual(self.metadata['durationsMs'], DURATIONS[0])
        self.assertEqual(self.metadata['totalDurationMs'], 6600)
        self.assertEqual(self.metadata['camera'], self.transform)
        self.assertEqual(self.metadata['alphaCleanup'], self.cleanup)
        self.assertEqual(self.frames[0].tobytes(), self.frames[-1].tobytes())
        self.assertNotEqual(self.frames[0].tobytes(), self.frames[2].tobytes())
        self.assertEqual(self.metadata['visualMotionApproval'], 'pending')
        self.assertFalse(self.metadata['installableFullAtlas'])
        self.assertEqual(self.metadata['statesInThisArtifact'], ['idle'])
        with Image.open(ROOT/'candidates/phase5/idle/strip.webp') as strip:
            for i, frame in enumerate(self.frames):
                with Image.open(ROOT/f'candidates/phase5/idle/frame-{i}.png') as png:
                    self.assertEqual(frame.tobytes(), png.convert('RGBA').tobytes())
                self.assertEqual(hashlib.sha256(frame.tobytes()).hexdigest().upper(), self.metadata['frameHashes'][i])
                self.assertEqual(frame.tobytes(), strip.crop((i*192, 0, (i+1)*192, 208)).convert('RGBA').tobytes())
                rgba = np.asarray(frame)
                self.assertFalse(rgba[0, :, 3].any() or rgba[-1, :, 3].any() or rgba[:, 0, 3].any() or rgba[:, -1, 3].any())
                self.assertFalse(((rgba[..., 3] == 0) & np.any(rgba[..., :3] != 0, axis=2)).any())

    def test_gif_holds_match_actual_native_timing_not_a_fast_loop(self):
        with Image.open(ROOT/'candidates/phase5/idle/native-timing.gif') as gif:
            self.assertEqual(gif.n_frames, 6)
            durations = []
            for i in range(gif.n_frames):
                gif.seek(i)
                durations.append(gif.info['duration'])
            self.assertEqual(durations, DURATIONS[0])


if __name__ == '__main__':
    unittest.main()
