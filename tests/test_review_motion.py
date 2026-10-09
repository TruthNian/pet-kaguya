"""Review artwork/motion contracts, not an aesthetic acceptance certificate."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import unittest

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
import build_review as review
import review_review_v3 as art
import build_gaze as gaze
from arm_material import project_fixed_crop
from build_idle import coordinates
from canonical import ACCEPTED_SHA, clean_cutout, camera
from protocol import DURATIONS


class Review(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = review.inputs()
        cls.meta = json.loads((review.OUT/'build.json').read_text())
        cls.art_meta = json.loads((art.OUT/'build.json').read_text())

    def test_bounded_right_arm_preserves_base_outside_permission(self):
        data = self.data
        before, after = np.asarray(data['base']), np.asarray(data['armPose'])
        np.testing.assert_array_equal(after[~data['armAllowed']], before[~data['armAllowed']])
        np.testing.assert_array_equal(after[data['preserved']], before[data['preserved']])
        self.assertEqual(int(np.any(before!=after,axis=2).sum()),78805)
        self.assertEqual(self.art_meta['boundedRightArmChangedPixels'],78805)
        self.assertEqual(self.art_meta['changedPixelsFromV1'],30591)
        self.assertEqual(self.art_meta['boundedRightArmChangedPixelsOutsidePatch'],0)
        self.assertEqual(self.art_meta['rawMappedCropChangedPixelsOutsidePatch'],177351)

    def test_unmodified_head_face_and_shoes_are_actual_source_rgba(self):
        source, pose = np.asarray(self.data['mother']), np.asarray(self.data['armPose'])
        for x0,y0,x1,y1 in [(455,250,775,465),(433,1015,611,1226),(616,1015,795,1226)]:
            np.testing.assert_array_equal(pose[y0:y1,x0:x1],source[y0:y1,x0:x1])
            self.assertFalse(self.data['armAllowed'][y0:y1,x0:x1].any())
        self.assertEqual(self.art_meta['sourceSha256'],ACCEPTED_SHA)
        self.assertTrue(self.art_meta['originalHeadFaceRGBAExact'])

    def test_illegal_permissions_rejected_even_if_generated_pixels_are_identity(self):
        base, spec, raw = art.inputs()
        for key, value in [('oldRightArmPolygon',[[450,250],[780,250],[780,475],[450,475]]),
                           ('foregroundRightArmPolygon',[[498,570],[1000,570],[940,1000]]),
                           ('oldRightArmPolygon',[[498,float('nan')],[550,580],[600,590]]),
                           ('newFaceGeometryAllowed',True),('fullRedrawAccepted',True)]:
            bad = copy.deepcopy(spec)
            bad[key] = value
            with self.assertRaises(ValueError):
                art.localized_pose(base,base,bad)

    def test_raw_fixed_crop_has_immutable_registration_not_object_bounds_fit(self):
        base, spec, raw = art.inputs()
        self.assertEqual(spec['rawCanvas'],[1266,1242])
        self.assertEqual(spec['sourceCrop'],[450,500,970,1010])
        ratio = 1266/520
        self.assertLess(abs(1242/ratio-510),1)
        for x,y in [(449,500),(970,700),(600,499),(600,1010)]:
            self.assertEqual(raw.getpixel((x,y)),base.getpixel((x,y)))
        with self.assertRaises(ValueError):
            project_fixed_crop(base,Image.new('RGBA',(1266,1000)),[1266,1000],spec['sourceCrop'])
        self.assertEqual(hashlib.sha256((ROOT/spec['generatedSource']).read_bytes()).hexdigest().upper(),art.GENERATED_SHA)

    def test_saved_static_pose_and_native_frame_are_exactly_rebuilt(self):
        with Image.open(art.OUT/'pose.png') as image:
            self.assertEqual(image.convert('RGBA').tobytes(),self.data['armPose'].tobytes())
        self.assertEqual(hashlib.sha256(self.data['armPose'].tobytes()).hexdigest().upper(),self.art_meta['poseRGBAHash'])
        with Image.open(art.OUT/'frame.png') as image:
            self.assertEqual(hashlib.sha256(image.convert('RGBA').tobytes()).hexdigest().upper(),self.art_meta['frameRGBAHash'])
        self.assertFalse(self.art_meta['animationBuilt'])
        self.assertEqual(self.art_meta['visualAcceptance'],'pending')
        self.assertIn('pixel-plate',self.art_meta['placementLimitation'])

    def test_downward_gaze_changes_only_original_eye_openings_and_keeps_alpha(self):
        data = self.data
        before, after = np.asarray(data['armPose']), np.asarray(data['focused'])
        np.testing.assert_array_equal(after[~data['eyeAllowed']],before[~data['eyeAllowed']])
        np.testing.assert_array_equal(after[...,3],before[...,3])
        self.assertGreater(int(np.any(after!=before,axis=2).sum()),0)
        self.assertEqual(data['motion']['focusOffsetSourcePx'],[0,5])
        for x,y in [(535,250),(530,290),(695,273),(450,334),(773,320),(615,400),(610,447),(615,610)]:
            self.assertFalse(data['eyeAllowed'][y,x])
            np.testing.assert_array_equal(after[y,x],before[y,x])

    def test_face_entire_shoes_and_held_hands_have_identity_coordinates(self):
        data = self.data
        boxes = [data['regions']['protectedFace'], *data['regions']['shoeProtectedRects'],[498,669,608,732]]
        for x0,y0,x1,y1 in boxes:
            yy,xx = np.mgrid[y0:y1,x0:x1].astype(float)
            for pose in data['motion']['keyframes']:
                sx,sy = coordinates(xx,yy,pose,data['transform'],data['regions'],data['masks'])
                np.testing.assert_array_equal(sx,xx)
                np.testing.assert_array_equal(sy,yy)

    def test_sampled_fields_have_positive_jacobian_and_native_body_does_not_pulse(self):
        data = self.data
        yy,xx = np.mgrid[10:1260:5,80:1130:5].astype(float)
        first = data['frames'][0]
        for pose,frame in zip(data['motion']['keyframes'],data['frames']):
            args = (pose,data['transform'],data['regions'],data['masks'])
            xp,yp = coordinates(xx+.1,yy,*args)
            xm,ym = coordinates(xx-.1,yy,*args)
            txp,typ = coordinates(xx,yy+.1,*args)
            txm,tym = coordinates(xx,yy-.1,*args)
            determinant = ((xp-xm)*(typ-tym)-(txp-txm)*(yp-ym))/.04
            self.assertGreater(float(determinant.min()),.95)
            for box in [(73,47,122,81),(70,100,130,145),(72,180,122,202)]:
                self.assertEqual(frame.crop(box).tobytes(),first.crop(box).tobytes())

    def test_saved_six_native_frames_padding_alpha_and_loop_seam(self):
        frames = self.data['frames']
        with Image.open(review.OUT/'focused-pose.png') as saved:
            self.assertEqual(saved.convert('RGBA').tobytes(),self.data['focused'].tobytes())
        with Image.open(review.OUT/'strip.webp') as strip:
            self.assertEqual(strip.size,(1536,208))
            for index,frame in enumerate(frames):
                with Image.open(review.OUT/f'frame-{index}.png') as saved:
                    self.assertEqual(saved.convert('RGBA').tobytes(),frame.tobytes())
                self.assertEqual(strip.crop((index*192,0,(index+1)*192,208)).convert('RGBA').tobytes(),frame.tobytes())
                self.assertEqual(hashlib.sha256(frame.tobytes()).hexdigest().upper(),self.meta['frameHashes'][index])
                pixels = np.asarray(frame)
                self.assertFalse(pixels[0,:,3].any() or pixels[-1,:,3].any() or pixels[:,0,3].any() or pixels[:,-1,3].any())
                self.assertFalse(((pixels[...,3]==0)&np.any(pixels[...,:3]!=0,axis=2)).any())
            self.assertIsNone(strip.crop((1152,0,1536,208)).getbbox())
        self.assertEqual(frames[0].tobytes(),frames[-1].tobytes())
        self.assertEqual(frames[1].tobytes(),frames[4].tobytes())
        self.assertEqual(self.meta['uniqueCels'],4)
        self.assertEqual(self.meta['durationsMs'],DURATIONS[8])
        self.assertEqual(self.meta['totalDurationMs'],1030)
        self.assertEqual(self.meta['actionDurationMs'],3090)

    def test_gif_independent_time_weighted_palette_display_matches_native_holds(self):
        def coalesce(timeline):
            result = []
            for rgb,hold in timeline:
                if result and result[-1][0]==rgb:
                    result[-1] = (rgb,result[-1][1]+hold)
                else:
                    result.append((rgb,hold))
            return result
        with Image.open(review.OUT/'native-timing.gif') as gif:
            actual = []
            for index in range(gif.n_frames):
                gif.seek(index)
                actual.append((hashlib.sha256(gif.convert('RGB').tobytes()).hexdigest(),gif.info['duration']))
        expected = []
        for frame,hold in zip(self.data['frames'],DURATIONS[8]):
            tile = Image.new('RGBA',frame.size,'#23252b')
            tile.alpha_composite(frame)
            rgb = tile.convert('RGB').convert('P',palette=Image.Palette.ADAPTIVE).convert('RGB')
            expected.append((hashlib.sha256(rgb.tobytes()).hexdigest(),hold))
        self.assertEqual(sum(hold for _,hold in actual),1030)
        self.assertEqual(coalesce(actual),coalesce(expected))

    def test_invalid_motion_and_unapproved_full_pet_overclaims_are_rejected(self):
        spec = gaze.specification()
        for key,value in [('sourceSha256','bad'),('nativeRow',1),('state','run_left'),
                          ('durationsMs',[100]*6),('bodyPulse',True),('ornamentFlash',True),
                          ('nativeInterpolation',True),('closedEyeFrames',1),
                          ('handStrategy','approved'),('strategyUserApproval','approved'),
                          ('focusOffsetSourcePx',[13,0]),('focusOffsetSourcePx',[0,float('nan')]),
                          ('focusOffsetSourcePx',[True,5]),('focusOffsetSourcePx',[0,-1])]:
            bad = copy.deepcopy(self.data['motion'])
            bad[key] = value
            with self.assertRaises(ValueError):
                review.validate_motion(bad,spec)
        for pose in [dict(bodyY=.1,earAngle=0,hairAngle=0),dict(bodyY=0,earAngle=.3,hairAngle=0),
                     dict(bodyY=0,earAngle=0,hairAngle=0,actorY=-1)]:
            bad = copy.deepcopy(self.data['motion'])
            bad['keyframes'][2] = pose
            with self.assertRaises(ValueError):
                review.validate_motion(bad,spec)
        self.assertEqual(self.meta['sourceSha256'],ACCEPTED_SHA)
        self.assertEqual(self.meta['camera'],camera(clean_cutout(self.data['mother'])[0]))
        for key in ('installed','installableFullAtlas','facialGeometryRepair','fullRedrawAccepted',
                    'articulatedArmBuilt','nativeInterpolation','bodyPulse','ornamentFlash'):
            self.assertFalse(self.meta[key])
        self.assertTrue(self.meta['animationBuilt'])
        self.assertEqual(self.meta['rightArmCompositionVersion'],'review-art-v3')
        self.assertTrue(self.meta['knownSourceHairRGBAExact'])
        self.assertTrue(self.meta['paintedHairAlphaContinuityEstimated'])
        self.assertFalse(self.meta['newArtworkGenerated'])
        self.assertEqual(self.meta['strategyUserApproval'],'pending')
        self.assertEqual(self.meta['visualMotionApproval'],'pending')
        self.assertGreaterEqual(len(self.meta['unresolved']),6)


if __name__ == '__main__':
    unittest.main()
