"""Single-factor six-hold hand/cuff study, not an anatomy/visual acceptance test."""
import hashlib
import json
from pathlib import Path
import sys
import unittest

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import build_review_overlap_study as study
from protocol import DURATIONS


class OverlapMotion(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = study.inputs()
        cls.meta = json.loads((study.OUT/'build.json').read_text(encoding='utf-8'))

    def test_source_candidate_focus_and_all_non_hand_pixels_are_exact(self):
        data = self.data
        a,b = np.asarray(data['old']['focused']),np.asarray(data['focused'])
        np.testing.assert_array_equal(a[~data['allowed']],b[~data['allowed']])
        np.testing.assert_array_equal(a[...,3],b[...,3])
        self.assertEqual(int(np.any(a!=b,axis=2).sum()),25459)
        for key in ['pose','focused']:
            file = 'static-candidate.png' if key=='pose' else 'animation/focused-pose.png'
            with Image.open(study.art.OUT/file) as image:
                self.assertEqual(image.convert('RGBA').tobytes(),data[key].tobytes())
        self.assertEqual(study.rgba_hash(data['pose']),study.POSE_HASH)

    def test_all_permitted_hands_are_rigid_under_every_actual_ear_hair_hold(self):
        self.assertEqual(int(self.data['allowed'].sum()),25469)
        self.assertEqual(self.data['displacement'],[0]*6)
        self.assertEqual(self.meta['handCuffMaximumSourceDisplacementPx'],[0]*6)
        self.assertEqual(self.meta['keyframes'],self.data['old']['motion']['keyframes'])
        self.assertEqual(self.meta['focusOffsetSourcePx'],[0,5])

    def test_actual_native_pixels_only_differ_inside_the_measured_hand_cuff_bounds(self):
        deltas = []
        for old,frame in zip(self.data['old']['frames'],self.data['frames']):
            a,b = np.asarray(old),np.asarray(frame)
            changed = np.any(a!=b,axis=2)
            self.assertEqual(int(changed.sum()),844)
            np.testing.assert_array_equal(a[...,3],b[...,3])
            outside = np.ones(changed.shape,bool);outside[105:140,61:104] = False
            self.assertFalse(changed[outside].any())
            deltas.append(b.astype(int)-a.astype(int))
        # The hand delta stays exactly constant: no hidden sleeve wobble.
        for delta in deltas[1:]:np.testing.assert_array_equal(delta,deltas[0])
        self.assertEqual(self.meta['changesFromFrozenReview'],self.data['changes'])

    def test_six_cels_png_strip_hashes_and_two_blank_columns_are_actual(self):
        with Image.open(study.OUT/'strip.webp') as image:
            strip = image.convert('RGBA')
        self.assertEqual(strip.size,(1536,208))
        self.assertIsNone(strip.crop((1152,0,1536,208)).getbbox())
        for i,frame in enumerate(self.data['frames']):
            self.assertEqual(strip.crop((192*i,0,192*(i+1),208)).tobytes(),frame.tobytes())
            with Image.open(study.OUT/f'frame-{i}.png') as image:
                self.assertEqual(image.convert('RGBA').tobytes(),frame.tobytes())
        self.assertEqual(self.meta['frameHashes'],[study.rgba_hash(f) for f in self.data['frames']])
        self.assertEqual(self.data['frames'][0].tobytes(),self.data['frames'][-1].tobytes())

    def test_native_gif_holds_and_three_cycle_duration_are_not_interpolation(self):
        with Image.open(study.OUT/'native-timing.gif') as image:
            holds = []
            for i in range(image.n_frames):
                image.seek(i);holds.append(image.info['duration'])
            self.assertEqual(holds,DURATIONS[8]);self.assertEqual(image.info['loop'],0)
        self.assertEqual(self.meta['totalDurationMs'],1030)
        self.assertEqual(self.meta['actionDurationMs'],3090)
        self.assertFalse(self.meta['nativeInterpolation'])
        self.assertFalse(self.meta['entryExitTransitionsBuilt'])

    def test_frozen_baseline_is_exact_actual_current_review_not_a_counterfactual(self):
        current = json.loads((ROOT/'candidates/phase5/review/build.json').read_text(encoding='utf-8'))
        self.assertEqual(self.data['baseline'],current)
        self.assertEqual(self.meta['baselineFrameHashes'],current['frameHashes'])
        self.assertNotEqual(self.meta['frameHashes'],current['frameHashes'])
        self.assertEqual(self.meta['camera'],current['camera'])

    def test_trial_does_not_promote_pose_or_change_current_atlas_or_mother(self):
        for key in ['adopted','activeAtlasChanged','installed','installableFullAtlas',
                    'cleanLayerRecoveryClaimed','articulatedArmBuilt','facialGeometryRepair']:
            self.assertFalse(self.meta[key])
        self.assertEqual(self.meta['specificPoseUserApproval'],'pending')
        self.assertEqual(self.meta['visualMotionApproval'],'pending')
        with Image.open(ROOT/'candidates/phase5/global/spritesheet.webp') as image:
            self.assertEqual(study.rgba_hash(image.convert('RGBA')),
                '1E1D25A012688E96CC1D4A59AD96696145B52DB7E7C9DAEF39AF9273A2128786')
        self.assertEqual(hashlib.sha256((ROOT/'sources/canonical/artwork.png').read_bytes()).hexdigest().upper(),
            study.ACCEPTED_SHA)


if __name__ == '__main__':unittest.main()
