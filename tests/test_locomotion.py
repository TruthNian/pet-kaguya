"""Drag-feedback, estimated layers and global QA; not visual acceptance."""
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
import build_locomotion as run
import leg_material as art
import build_global_review as global_review
from canonical import ACCEPTED_SHA,clean_cutout,camera
from protocol import DURATIONS,COUNTS,WIDTH,HEIGHT
from review_wave import native_frame


class Locomotion(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = run.inputs()

    def test_fixed_raw_crop_and_source_hash_not_object_fit_or_face_redraw(self):
        data = self.data
        self.assertEqual(hashlib.sha256((art.OUT/'generated.png').read_bytes()).hexdigest().upper(),art.GENERATED_SHA)
        self.assertEqual(data['spec']['rawCanvas'],[1269,1239])
        self.assertLess(abs(1239/(1269/420)-410),1)
        for x,y in [(399,850),(820,900),(600,849),(600,1260),(615,400)]:
            self.assertEqual(data['mother'].getpixel((x,y)),data['mapped'].getpixel((x,y)))
        self.assertEqual(data['transform'],camera(clean_cutout(data['mother'])[0]))

    def test_material_source_is_actual_foreground_rgba_times_estimated_coverage(self):
        source = art.premult(self.data['mother'].crop(self.data['box']))
        for layer,mask in zip(self.data['layers'],self.data['masks']):
            np.testing.assert_array_equal(layer,source*np.asarray(mask,dtype=float)[...,None]/255)
            self.assertGreater(np.count_nonzero(np.asarray(mask)==255),10000)
            self.assertTrue(np.isfinite(layer).all())
            self.assertFalse((layer[...,:3]>layer[...,3:4]+1e-9).any())

    def test_neutral_is_same_compositor_and_honestly_not_lossless(self):
        neutral = art.composite(self.data,[(0,0),(0,0)])
        with Image.open(art.OUT/'neutral-reconstruction.png') as saved:
            self.assertEqual(saved.convert('RGBA').tobytes(),neutral.tobytes())
        a,b = np.asarray(self.data['mother']),np.asarray(neutral)
        self.assertFalse(np.array_equal(a,b))
        x0,y0,x1,y1 = self.data['box']
        permission = np.zeros(a.shape[:2],dtype=bool)
        permission[y0:y1,x0:x1] = self.data['allowed']
        np.testing.assert_array_equal(a[~permission],b[~permission])
        np.testing.assert_array_equal(a[:936],b[:936])
        alpha_error = np.abs(a[...,3].astype(int)-b[...,3].astype(int))
        self.assertLessEqual(int(alpha_error.max()),64)
        native_a,native_b = native_frame(self.data['mother']),native_frame(neutral)
        error = np.abs(art.premult(native_a)-art.premult(native_b))
        meta = json.loads((art.OUT/'build.json').read_text())
        self.assertFalse(meta['losslessNeutralDecomposition'])
        self.assertEqual(meta['neutralNativeMaximumPremultRGBAError'],round(float(error.max()),9))
        self.assertEqual(meta['neutralNativeMeanAbsolutePremultRGBAError'],round(float(error.mean()),9))
        self.assertGreater(float(error.max()),0)
        self.assertLessEqual(float(error.max()),20)  # Narrow technical regression guard, not aesthetic approval.

    def test_permissions_reject_face_or_unbounded_source_even_for_identity_art(self):
        for key,value in [('sourceSha256','bad'),('rawCanvas',[1269,1238]),
                          ('editBudget',[425,200,810,1240]),('fullRedrawAccepted',True),
                          ('losslessNeutralDecomposition',True),('inferredMatte',False),
                          ('faceShapeLocked',False),('visualAcceptance','approved')]:
            bad = copy.deepcopy(self.data['spec']);bad[key] = value
            with self.assertRaises(ValueError):art.validate_specification(bad)
        for points in [[[535,400],[550,950],[530,1000]],[[420,936],[550,950],[530,1000]],
                       [[535,float('nan')],[550,950],[530,1000]]]:
            bad = copy.deepcopy(self.data['spec']);bad['legs'][0]['foregroundPolygon'] = points
            with self.assertRaises(ValueError):art.validate_specification(bad)

    def test_puppet_joint_lengths_and_planted_feet_are_actual_math_not_only_metadata(self):
        data = self.data
        yy,xx = np.mgrid[1026:1240:3,430:790:3].astype(float)
        for state in data['motion']['states']:
            direction = state['direction']
            for key in data['motion']['keyframes']:
                for leg in data['spec']['legs']:
                    dx,dy = key[leg['name']];dx *= direction
                    anchor,knee,ankle,lengths = art.inverse_kinematics(leg,dx,dy)
                    np.testing.assert_allclose([np.linalg.norm(knee-anchor),np.linalg.norm(ankle-knee)],lengths,atol=1e-10,rtol=0)
                    sx,sy = art.leg_coordinates(xx,yy,leg,dx,dy)
                    lower = yy >= ankle[1]
                    np.testing.assert_array_equal(sx[lower],(xx-dx)[lower])
                    np.testing.assert_array_equal(sy[lower],(yy-dy)[lower])
                    if leg['name'] in key['support']:
                        np.testing.assert_array_equal(sx,xx);np.testing.assert_array_equal(sy,yy)
        with self.assertRaises(ValueError):art.inverse_kinematics(data['spec']['legs'][0],0,100)

    def test_continuous_ring_seams_monotone_vertical_map_and_positive_inverse_jacobian(self):
        data = self.data
        yy,xx = np.mgrid[937:1026:2,460:745:3].astype(float)
        for leg in data['spec']['legs']:
            for dx,dy in [(0,0),(2.5,-3.75),(5,-7.5),(-5,-7.5)]:
                _,knee,ankle,_ = art.inverse_kinematics(leg,dx,dy)
                for point,original in [(knee,leg['knee']),(ankle,leg['ankle'])]:
                    sy = art.leg_coordinates(np.array([point[0]]),np.array([point[1]]),leg,dx,dy)
                    np.testing.assert_allclose([float(sy[0][0]),float(sy[1][0])],original,rtol=0,atol=1e-10)
                    below = art.leg_coordinates(np.array([point[0]]),np.array([point[1]-.000001]),leg,dx,dy)
                    above = art.leg_coordinates(np.array([point[0]]),np.array([point[1]+.000001]),leg,dx,dy)
                    self.assertLess(max(abs(float(a[0]-b[0])) for a,b in zip(below,above)),.00001)
                xp,yp = art.leg_coordinates(xx+.01,yy,leg,dx,dy)
                xm,ym = art.leg_coordinates(xx-.01,yy,leg,dx,dy)
                txp,typ = art.leg_coordinates(xx,yy+.01,leg,dx,dy)
                txm,tym = art.leg_coordinates(xx,yy-.01,leg,dx,dy)
                determinant = ((xp-xm)*(typ-tym)-(txp-txm)*(yp-ym))/.0004
                self.assertGreater(float(determinant.min()),.5)

    def test_all_pose_face_except_original_eye_apertures_and_upper_body_are_fixed(self):
        data = self.data;original = np.asarray(data['mother'])
        allowed = data['eyeAllowed'].copy();allowed[936:1240,425:810] = True
        for name,result in data['results'].items():
            first = np.asarray(result['frames'][0])
            for pose,frame in zip(result['poses'],result['frames']):
                pixels = np.asarray(pose)
                np.testing.assert_array_equal(pixels[~allowed],original[~allowed])
                np.testing.assert_array_equal(pixels[:936,:,3],original[:936,:,3])
                np.testing.assert_array_equal(np.asarray(frame)[:154],first[:154])
            self.assertEqual(result['frames'][0].tobytes(),result['frames'][-1].tobytes())
            self.assertEqual(len(set(frame.tobytes() for frame in result['frames'])),5)
        self.assertFalse(np.array_equal(np.asarray(data['results']['run_right']['poses'][0]),
                                       np.asarray(data['results']['run_left']['poses'][0])))

    def test_eight_saved_cels_actual_native_holds_no_border_or_invisible_rgb(self):
        for name,result in self.data['results'].items():
            out = ROOT/'candidates/phase5'/name
            meta = json.loads((out/'build.json').read_text())
            with Image.open(out/'strip.webp') as strip:
                self.assertEqual(strip.size,(1536,208))
                for index,frame in enumerate(result['frames']):
                    self.assertEqual(strip.crop((index*192,0,(index+1)*192,208)).convert('RGBA').tobytes(),frame.tobytes())
                    with Image.open(out/f'frame-{index}.png') as saved:
                        self.assertEqual(saved.convert('RGBA').tobytes(),frame.tobytes())
                    self.assertEqual(hashlib.sha256(frame.tobytes()).hexdigest().upper(),meta['frameHashes'][index])
                    a = np.asarray(frame)
                    self.assertFalse(a[0,:,3].any() or a[-1,:,3].any() or a[:,0,3].any() or a[:,-1,3].any())
                    self.assertFalse(((a[...,3]==0)&np.any(a[...,:3]!=0,axis=2)).any())
            with Image.open(out/'native-timing.gif') as gif:
                duration = 0
                for index in range(gif.n_frames):gif.seek(index);duration += gif.info['duration']
                self.assertEqual(duration,1060)
            self.assertEqual(meta['durationsMs'],DURATIONS[result['state']['nativeRow']])
            self.assertEqual(meta['uninterruptedRowDurationMs'],3180)
            for key in ('hostVelocitySynchronization','screenWorldNoSlipProven','artMirrored',
                        'losslessNeutralDecomposition','installed','installableFullAtlas','facialGeometryRepair'):
                self.assertFalse(meta[key])
            self.assertTrue(meta['actualDragReleaseCanInterruptAnyCel'])
            self.assertEqual(meta['strategyUserApproval'],'pending')
            self.assertEqual(meta['visualMotionApproval'],'pending')

    def test_invalid_motion_no_support_foot_sliding_side_face_or_authority_overclaim(self):
        for key,value in [('sourceSha256','bad'),('durationsMs',[100]*8),('artMirrored',True),
                          ('faceShapeLocked',False),('projection','side-view'),('bodyTranslationPx',.1),
                          ('nativeInterpolation',True),('hostVelocitySynchronization',True),
                          ('visualMotionApproval','approved'),('strategyUserApproval','approved')]:
            bad = copy.deepcopy(self.data['motion']);bad[key] = value
            with self.assertRaises(ValueError):run.validate_motion(bad)
        for pose in [dict(left=[0,0],right=[0,0],support=[]),dict(left=[5,-8],right=[0,0],support=['right']),
                     dict(left=[5,-7.5],right=[1,0],support=['right']),
                     dict(left=[True,-7.5],right=[0,0],support=['right'])]:
            bad = copy.deepcopy(self.data['motion']);bad['keyframes'][2] = pose
            with self.assertRaises(ValueError):run.validate_motion(bad)

    def test_local_host_evidence_does_not_fake_live_drag_or_wait_for_landing(self):
        contract = json.loads((ROOT/'sources/canonical/host-drag-contract.json').read_text())
        facts = contract['facts']
        self.assertIn('no installed app write or live drag recording',contract['method'])
        self.assertFalse(facts['spriteVelocityInput'])
        self.assertFalse(facts['dragEndAlwaysIdle'])
        self.assertFalse(facts['dragEndWaitsForLandingCel'])
        self.assertEqual(facts['runDurationsMs'],DURATIONS[1])
        self.assertEqual(len(contract['memberSha256']),64)

    def test_global_qa_atlas_every_row_exact_not_installable_or_accepted(self):
        expected,summaries,_,_ = global_review.assemble()
        with Image.open(global_review.OUT/'spritesheet.webp') as saved:
            atlas = saved.convert('RGBA')
            self.assertEqual(atlas.tobytes(),expected.tobytes())
        meta = json.loads((global_review.OUT/'build.json').read_text())
        self.assertEqual(meta['atlasRGBAHash'],hashlib.sha256(atlas.tobytes()).hexdigest().upper())
        self.assertEqual(meta['actionRows'],summaries)
        self.assertEqual(meta['decodedTextureBytes'],14057472)
        self.assertTrue(meta['atlasCoverageComplete'])
        self.assertFalse(meta['allStateTransitionsAccepted'])
        self.assertFalse(meta['hostIntegrationVerified'])
        self.assertFalse(meta['installableFullAtlas']);self.assertFalse(meta['installed'])
        self.assertFalse((global_review.OUT/'pet.json').exists())
        for row,count in enumerate(COUNTS):
            for col in range(8):
                frame = atlas.crop((col*WIDTH,row*HEIGHT,(col+1)*WIDTH,(row+1)*HEIGHT))
                self.assertEqual(frame.getbbox() is not None,col < count)
        self.assertEqual(atlas.crop((0,0,192,208)).tobytes(),atlas.crop((1152,0,1344,208)).tobytes())


if __name__ == '__main__':
    unittest.main()
