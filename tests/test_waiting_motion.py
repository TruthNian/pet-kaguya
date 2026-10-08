"""Held waiting contact/occlusion/native-time proofs; not aesthetic approval."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import unittest

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import build_waiting as waiting
import review_waiting as art
from build_idle import coordinates
from canonical import ACCEPTED_SHA,clean_cutout,camera
from protocol import DURATIONS


class WaitingMotion(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = waiting.inputs()
        cls.meta = json.loads((waiting.OUT/'build.json').read_text())

    def test_pose_keeps_all_outside_pixels_and_face_except_hand_occlusion(self):
        data = self.data
        before,after = np.asarray(data['mother']),np.asarray(data['pose'])
        np.testing.assert_array_equal(before[~data['allowed']],after[~data['allowed']])
        x0,y0,x1,y1 = data['regions']['protectedFace']
        face = np.zeros(data['allowed'].shape,dtype=bool)
        face[y0:y1,x0:x1] = True
        np.testing.assert_array_equal(before[face&~data['hand']],after[face&~data['hand']])
        self.assertTrue(np.any(np.any(before!=after,axis=2)&face&data['hand']))

    def test_illegal_hand_permission_rejected_even_when_those_pixels_are_unchanged(self):
        for name,polygon in [('foregroundHandPolygon',[[490,280],[750,280],[750,400],[490,400]]),
                             ('armAndBackingPolygon',[[450,250],[780,250],[780,465],[450,465]])]:
            bad = copy.deepcopy(art.specification())
            bad[name] = polygon
            with self.assertRaises(ValueError):
                art.localized_pose(self.data['mother'],self.data['mother'],bad)

    def test_cheek_and_entire_foreground_hand_have_identity_coordinates(self):
        data = self.data
        x0,y0,x1,y1 = data['regions']['protectedFace']
        face = np.zeros(data['hand'].shape,dtype=bool)
        face[y0:y1,x0:x1] = True
        yy,xx = np.where(face|data['hand'])
        yy,xx = yy.astype(float),xx.astype(float)
        for pose in data['motion']['keyframes']:
            sx,sy = coordinates(xx,yy,pose,data['transform'],data['regions'],data['masks'])
            np.testing.assert_array_equal(sx,xx)
            np.testing.assert_array_equal(sy,yy)
        # Contact must survive actual sampling too, not just rig coordinates.
        for frame in data['frames']:
            self.assertEqual(frame.crop((73,47,122,100)).tobytes(),data['frames'][0].crop((73,47,122,100)).tobytes())

    def test_shoes_body_and_zero_pose_match_the_existing_static_key_pose(self):
        with Image.open(art.OUT/'frame.png') as frame:
            self.assertEqual(frame.convert('RGBA').tobytes(),self.data['frames'][0].tobytes())
        for frame in self.data['frames']:
            for box in ((72,180,122,202),(94,99,123,144),(115,120,143,132)):
                self.assertEqual(frame.crop(box).tobytes(),self.data['frames'][0].crop(box).tobytes())
        self.assertEqual(self.meta['camera'],camera(clean_cutout(self.data['mother'])[0]))

    def test_native_holds_reuse_and_saved_lossless_row_preserve_transparency(self):
        data = self.data
        self.assertEqual(self.meta['durationsMs'],DURATIONS[6])
        self.assertEqual(self.meta['totalDurationMs'],1010)
        self.assertEqual(self.meta['actionDurationMs'],3030)
        self.assertEqual(data['frames'][0].tobytes(),data['frames'][-1].tobytes())
        self.assertEqual(data['frames'][1].tobytes(),data['frames'][4].tobytes())
        self.assertEqual(self.meta['uniqueCels'],4)
        with Image.open(waiting.OUT/'strip.webp') as strip:
            self.assertEqual(strip.size,(1536,208))
            for index,frame in enumerate(data['frames']):
                with Image.open(waiting.OUT/f'frame-{index}.png') as saved:
                    self.assertEqual(saved.convert('RGBA').tobytes(),frame.tobytes())
                self.assertEqual(strip.crop((index*192,0,(index+1)*192,208)).convert('RGBA').tobytes(),frame.tobytes())
                self.assertEqual(hashlib.sha256(frame.tobytes()).hexdigest().upper(),self.meta['frameHashes'][index])
                a = np.asarray(frame)
                self.assertFalse(a[0,:,3].any() or a[-1,:,3].any() or a[:,0,3].any() or a[:,-1,3].any())
                self.assertFalse(((a[...,3]==0)&np.any(a[...,:3]!=0,axis=2)).any())
            self.assertIsNone(strip.crop((1152,0,1536,208)).getbbox())

    def test_sampled_field_jacobian_remains_above_existing_limit(self):
        data = self.data
        yy,xx = np.mgrid[10:1260:5,80:1130:5].astype(float)
        for pose in data['motion']['keyframes']:
            args = (pose,data['transform'],data['regions'],data['masks'])
            xp,yp = coordinates(xx+.1,yy,*args)
            xm,ym = coordinates(xx-.1,yy,*args)
            txp,typ = coordinates(xx,yy+.1,*args)
            txm,tym = coordinates(xx,yy-.1,*args)
            self.assertGreater(float((((xp-xm)*(typ-tym)-(txp-txm)*(yp-ym))/.04).min()),.95)

    def test_gif_matches_exact_time_weighted_quantized_native_holds(self):
        def coalesce(items):
            result = []
            for rgb,hold in items:
                if result and result[-1][0]==rgb:
                    result[-1] = (rgb,result[-1][1]+hold)
                else:
                    result.append((rgb,hold))
            return result
        expected,actual = [],[]
        for frame,hold in zip(self.data['frames'],DURATIONS[6]):
            tile = Image.new('RGBA',frame.size,'#23252b')
            tile.alpha_composite(frame)
            rgb = tile.convert('RGB').convert('P',palette=Image.Palette.ADAPTIVE).convert('RGB')
            expected.append((hashlib.sha256(rgb.tobytes()).hexdigest(),hold))
        with Image.open(waiting.OUT/'native-timing.gif') as gif:
            for index in range(gif.n_frames):
                gif.seek(index)
                actual.append((hashlib.sha256(gif.convert('RGB').tobytes()).hexdigest(),gif.info['duration']))
        self.assertEqual(coalesce(actual),coalesce(expected))
        self.assertEqual(sum(hold for _,hold in actual),1010)

    def test_unapproved_strategy_and_missing_transitions_are_not_claimed_complete(self):
        for key,value in [('sourceSha256','bad'),('nativeRow',7),('durationsMs',[100]*6),
                          ('handStrategy','raise-hold-lower'),('strategyUserApproval','approved'),
                          ('bodyPulse',True),('closedEyeFrames',1),('nativeInterpolation',True)]:
            bad = copy.deepcopy(self.data['motion'])
            bad[key] = value
            with self.assertRaises(ValueError):
                waiting.validate_motion(bad)
        bad = copy.deepcopy(self.data['motion'])
        bad['keyframes'][2]['bodyY'] = .1
        with self.assertRaises(ValueError):
            waiting.validate_motion(bad)
        self.assertEqual(self.meta['sourceSha256'],ACCEPTED_SHA)
        self.assertEqual(self.meta['strategyUserApproval'],'pending')
        self.assertEqual(self.meta['visualMotionApproval'],'pending')
        for key in ('installed','installableFullAtlas','facialGeometryRepair','articulatedArmBuilt','fullRedrawAccepted','bodyPulse','nativeInterpolation'):
            self.assertFalse(self.meta[key])
        self.assertTrue(self.meta['animationBuilt'])
        self.assertGreaterEqual(len(self.meta['unresolved']),5)


if __name__ == '__main__':
    unittest.main()
