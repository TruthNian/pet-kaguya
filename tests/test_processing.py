"""Processing source/clock/geometry guards, not a visual-acceptance score."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import unittest

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
import build_processing as processing
import build_gaze as gaze
import review_processing as art
import review_arm_backing as backing
from arm_material import localized_arm_pose, project_fixed_crop
from build_idle import coordinates
from canonical import ACCEPTED_SHA, clean_cutout, camera
from protocol import DURATIONS


class Processing(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = processing.inputs()
        cls.meta = json.loads((processing.OUT/'build.json').read_text())

    def test_arm_edit_preserves_source_outside_budget_and_foreground(self):
        source = np.asarray(self.data['mother'])
        pose = np.asarray(self.data['armPose'])
        np.testing.assert_array_equal(pose[~self.data['armAllowed']], source[~self.data['armAllowed']])
        guard = backing.specification()
        protected = Image.new('L', self.data['mother'].size)
        for polygon in guard['preservedForegroundPolygons']:
            ImageDraw.Draw(protected).polygon(polygon, fill=255)
        selected = np.asarray(protected)>0
        np.testing.assert_array_equal(pose[selected], source[selected])
        for x0,y0,x1,y1 in guard['protectedRects']:
            np.testing.assert_array_equal(pose[y0:y1,x0:x1], source[y0:y1,x0:x1])
        self.assertEqual(int(np.any(source!=pose, axis=2).sum()), 64291)

    def test_corrupt_face_edit_and_nonuniform_crop_are_rejected(self):
        mother, spec, raw = art.inputs()
        spec = copy.deepcopy(spec)
        spec['foregroundPolygon'] = [[450,240],[780,240],[780,475],[450,475]]
        with self.assertRaises(ValueError):
            localized_arm_pose(mother, raw, spec)
        for raw, expected in [(Image.new('RGBA',(971,1000)),[971,1000]),
                              (Image.new('RGBA',(971,1619)),[1000,1619])]:
            with self.assertRaises(ValueError):
                project_fixed_crop(mother, raw, expected, [250,500,550,1000])

    def test_fixed_crop_registration_does_not_fit_painted_extents(self):
        # Transparent margins are intentional. A fit-to-character-bounds would
        # move this landmark; independent source coordinates locate it instead.
        mother = Image.new('RGBA',(1205,1306),(10,20,30,255))
        raw = Image.new('RGBA',(971,1619))
        ImageDraw.Draw(raw).rectangle((100,100,160,160),fill=(220,40,60,255))
        mapped = project_fixed_crop(mother, raw, [971,1619], [250,500,550,1000])
        self.assertEqual(mapped.getpixel((290,540)),(220,40,60,255))
        self.assertEqual(mapped.getpixel((270,520)),(0,0,0,0))
        self.assertEqual(mapped.getpixel((249,540)),mother.getpixel((249,540)))
        self.assertEqual(mapped.getpixel((290,1000)),mother.getpixel((290,1000)))

    def test_focus_changes_only_eye_openings_without_changing_alpha_or_face_shape(self):
        before, after = np.asarray(self.data['armPose']), np.asarray(self.data['focused'])
        np.testing.assert_array_equal(after[~self.data['eyeAllowed']], before[~self.data['eyeAllowed']])
        np.testing.assert_array_equal(after[...,3], before[...,3])
        self.assertGreater(int(np.any(after!=before, axis=2).sum()), 0)
        for x,y in [(535,250),(530,290),(695,273),(450,334),(773,320),(615,400),(610,447),(615,610)]:
            self.assertFalse(self.data['eyeAllowed'][y,x])
            np.testing.assert_array_equal(after[y,x], before[y,x])

    def test_face_and_entire_shoes_have_exact_identity_coordinates(self):
        data = self.data
        for box in [data['regions']['protectedFace'], *data['regions']['shoeProtectedRects']]:
            x0,y0,x1,y1 = box
            yy,xx = np.mgrid[y0:y1,x0:x1].astype(float)
            for pose in data['motion']['keyframes']:
                sx,sy = coordinates(xx,yy,pose,data['transform'],data['regions'],data['masks'])
                np.testing.assert_array_equal(sx,xx)
                np.testing.assert_array_equal(sy,yy)

    def test_small_fields_have_positive_sampled_jacobian(self):
        data = self.data
        yy,xx = np.mgrid[10:1260:5,80:1130:5].astype(float)
        for pose in data['motion']['keyframes']:
            args = (pose,data['transform'],data['regions'],data['masks'])
            xp,yp = coordinates(xx+.1,yy,*args)
            xm,ym = coordinates(xx-.1,yy,*args)
            txp,typ = coordinates(xx,yy+.1,*args)
            txm,tym = coordinates(xx,yy-.1,*args)
            determinant = ((xp-xm)*(typ-tym)-(txp-txm)*(yp-ym))/.04
            self.assertGreater(float(determinant.min()),.95)

    def test_native_face_other_hand_waist_and_shoes_do_not_pulse(self):
        first = self.data['frames'][0]
        for frame in self.data['frames']:
            for box in ((73,47,122,81),(115,120,143,132),(88,100,118,143),(72,180,122,202)):
                self.assertEqual(frame.crop(box).tobytes(), first.crop(box).tobytes())

    def test_saved_six_frames_match_lossless_strip_with_clean_padding_and_edges(self):
        frames = self.data['frames']
        with Image.open(processing.OUT/'focused-pose.png') as saved:
            self.assertEqual(saved.convert('RGBA').tobytes(),self.data['focused'].tobytes())
        with Image.open(processing.OUT/'strip.webp') as strip:
            self.assertEqual(strip.size,(1536,208))
            for index,frame in enumerate(frames):
                with Image.open(processing.OUT/f'frame-{index}.png') as saved:
                    self.assertEqual(saved.convert('RGBA').tobytes(),frame.tobytes())
                self.assertEqual(strip.crop((index*192,0,(index+1)*192,208)).convert('RGBA').tobytes(),frame.tobytes())
                self.assertEqual(hashlib.sha256(frame.tobytes()).hexdigest().upper(),self.meta['frameHashes'][index])
                pixels = np.asarray(frame)
                self.assertFalse(pixels[0,:,3].any() or pixels[-1,:,3].any() or pixels[:,0,3].any() or pixels[:,-1,3].any())
                self.assertFalse(((pixels[...,3]==0)&np.any(pixels[...,:3]!=0,axis=2)).any())
            self.assertIsNone(strip.crop((1152,0,1536,208)).getbbox())

    def test_reused_holds_and_loop_seam_do_not_require_six_unique_drawings(self):
        frames = self.data['frames']
        self.assertEqual(frames[0].tobytes(),frames[1].tobytes())
        self.assertEqual(frames[0].tobytes(),frames[-1].tobytes())
        self.assertEqual(self.meta['uniqueCels'],len(set(frame.tobytes() for frame in frames)))
        self.assertEqual(self.meta['uniqueCels'],4)
        self.assertEqual(self.meta['durationsMs'],DURATIONS[7])
        self.assertEqual(self.meta['totalDurationMs'],820)
        self.assertEqual(self.meta['actionDurationMs'],2460)
        self.assertEqual(self.meta['repeatBeforeIdle'],3)

    def test_gif_exposure_matches_every_native_hold_even_when_identical_holds_merge(self):
        # GIF is quantized and can merge identical adjacent frames. Compare
        # time-weighted displayed RGB against native holds, not frame count.
        def coalesce(timeline):
            result = []
            for rgb,hold in timeline:
                if result and result[-1][0]==rgb:
                    result[-1] = (rgb,result[-1][1]+hold)
                else:
                    result.append((rgb,hold))
            return result
        expected = []
        with Image.open(processing.OUT/'native-timing.gif') as gif:
            actual = []
            for index in range(gif.n_frames):
                gif.seek(index)
                actual.append((hashlib.sha256(gif.convert('RGB').tobytes()).hexdigest(),gif.info['duration']))
        self.assertEqual(sum(hold for _,hold in actual),820)
        for frame,hold in zip(self.data['frames'],DURATIONS[7]):
            tile = Image.new('RGBA',frame.size,'#23252b')
            tile.alpha_composite(frame)
            # Independently quantize each native hold, without using decoded
            # GIF samples as a nearest-match oracle. Tiny poses can be more
            # similar than their palette errors, so nearest matching was wrong.
            rgb = tile.convert('RGB').convert('P',palette=Image.Palette.ADAPTIVE).convert('RGB')
            expected.append((hashlib.sha256(rgb.tobytes()).hexdigest(),hold))
        self.assertEqual(coalesce(actual),coalesce(expected))

    def test_invalid_motion_and_full_pet_overclaims_are_rejected(self):
        spec = gaze.specification()
        for key,value in [('sourceSha256','bad'),('nativeRow',1),('nativeState','run_left'),
                          ('durationsMs',[100]*6),('bodyPulse',True),('ornamentFlash',True),
                          ('nativeInterpolation',True),('closedEyeFrames',1),
                          ('focusOffsetSourcePx',[13,0]),('focusOffsetSourcePx',[0,float('nan')]),
                          ('focusOffsetSourcePx',[True,0])]:
            bad = copy.deepcopy(self.data['motion'])
            bad[key] = value
            with self.assertRaises(ValueError):
                processing.validate_motion(bad,spec)
        for pose in [dict(bodyY=.1,earAngle=0,hairAngle=0),dict(bodyY=0,earAngle=.3,hairAngle=0),
                     dict(bodyY=0,earAngle=0,hairAngle=0,actorY=-1)]:
            bad = copy.deepcopy(self.data['motion'])
            bad['keyframes'][2] = pose
            with self.assertRaises(ValueError):
                processing.validate_motion(bad,spec)
        self.assertEqual(self.meta['sourceSha256'],ACCEPTED_SHA)
        self.assertEqual(self.meta['camera'],camera(clean_cutout(self.data['mother'])[0]))
        for key in ('installed','installableFullAtlas','facialGeometryRepair','fullRedrawAccepted',
                    'articulatedArmBuilt','nativeInterpolation','bodyPulse','ornamentFlash'):
            self.assertFalse(self.meta[key])
        self.assertEqual(self.meta['visualMotionApproval'],'pending')
        self.assertGreaterEqual(len(self.meta['unresolved']),5)


if __name__ == '__main__':
    unittest.main()
