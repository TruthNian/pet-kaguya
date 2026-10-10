"""Frozen rigid-v2 layer proofs, not tests of the later accepted surface model."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import unittest

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import build_gaze as gaze
from build_idle import render
from canonical import ACCEPTED_SHA, clean_cutout
FROZEN=ROOT/'sources/reference/gaze-rigid-v2'


class Gaze(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source,cls.generated,cls.spec,cls.layers,cls.camera,cls.regions,cls.masks = gaze.inputs()
        cls.allowed = gaze.aperture_union(cls.source,cls.layers)
        cls.poses = [gaze.pose(cls.source,cls.layers,*gaze.offsets(i,cls.spec)) for i in range(16)]
        cls.zero = dict(bodyY=0,earAngle=0,hairAngle=0)
        cls.neutral = render(clean_cutout(cls.source)[0],cls.zero,cls.camera,cls.regions,cls.masks)
        cls.frames = [render(clean_cutout(p)[0],cls.zero,cls.camera,cls.regions,cls.masks) for p in cls.poses]
        cls.meta = json.loads((FROZEN/'build.json').read_text())

    def test_neutral_reconstruction_uses_physical_layers_without_a_shortcut(self):
        self.assertEqual(gaze.pose(self.source,self.layers,0,0).tobytes(),self.source.tobytes())
        for layer in self.layers:
            f = layer['foreground']
            self.assertGreaterEqual(float(f.min()),0)
            self.assertLessEqual(float(f.max()),1)
            self.assertLessEqual(float((f[...,:3]-f[...,3:4]).max()),1e-12)
            rgb = layer['background']*(1-f[...,3:4])+f[...,:3]
            np.testing.assert_array_equal(np.rint(rgb*255).astype(np.uint8),layer['original'][...,:3])

    def test_exterior_white_inside_a_filled_hull_is_not_a_moving_highlight(self):
        # Regress the visually discovered halo: full envelope coverage does not
        # make every white pixel an iris reflection. Connected exterior white
        # must stay fixed, while a separated catchlight remains foreground.
        source = np.full((13,13,4),255,dtype=np.uint8)
        source[3:10,3:10,:3] = [150,40,60]
        source[3:5,3:5,:3] = 255
        source[6,6,:3] = 255
        envelope = Image.new('L',(13,13))
        ImageDraw.Draw(envelope).rectangle((2,2,10,10),fill=255)
        known = gaze.exterior_sclera(source,envelope,np.ones((13,13),dtype=bool))
        self.assertTrue(known[3,3])
        self.assertFalse(known[6,6])
        for layer in self.layers:
            self.assertTrue(layer['knownSclera'].any())
            np.testing.assert_array_equal(layer['foreground'][layer['knownSclera'],3],0)
            np.testing.assert_array_equal(layer['background'][layer['knownSclera']],layer['original'][layer['knownSclera'],:3]/255)

    def test_every_direction_preserves_original_alpha_and_all_non_eye_pixels(self):
        original = np.asarray(self.source)
        for pose in self.poses:
            new = np.asarray(pose)
            np.testing.assert_array_equal(new[...,3],original[...,3])
            np.testing.assert_array_equal(new[~self.allowed],original[~self.allowed])
        # Independent landmarks: brows/lashes, mouth, chin and entire costume.
        for x,y in [(535,250),(530,290),(695,273),(450,334),(773,320),(615,400),(610,447),(615,610),(550,380),(683,370)]:
            self.assertFalse(self.allowed[y,x])
            for pose in self.poses:
                np.testing.assert_array_equal(np.asarray(pose)[y,x],original[y,x])

    def test_fixed_native_face_body_and_shoes_outside_resampling_eye_halos(self):
        allowed = np.zeros((208,192),dtype=bool)
        allowed[49:73,72:96] = True
        allowed[47:72,100:125] = True
        original = np.asarray(self.neutral)
        for frame in self.frames:
            np.testing.assert_array_equal(np.asarray(frame)[~allowed],original[~allowed])

    def test_clockwise_cardinals_and_original_pupil_texture_are_translated_not_warped(self):
        for index,expected in [(0,(0,-7)),(4,(12,0)),(8,(0,7)),(12,(-12,0))]:
            dx,dy = gaze.offsets(index,self.spec)
            np.testing.assert_allclose((dx,dy),expected,atol=1e-12)
            # These interior pixels have full iris matte and remain inside the
            # eye in all cardinal poses. RGB moves; face coverage stays fixed.
            for x,y in [(534,336),(693,322)]:
                np.testing.assert_array_equal(np.asarray(self.poses[index])[y+round(dy),x+round(dx),:3],np.asarray(self.source)[y,x,:3])

    def test_portable_offsets_have_defined_precision_not_runtime_trig_tail_bits(self):
        expected = [(0,-7),(4.592201188381,-6.467156727579),(8.485281374239,-4.949747468306),
            (11.086554390135,-2.678784026556),(12,0),(11.086554390135,2.678784026556),
            (8.485281374239,4.949747468306),(4.592201188381,6.467156727579),(0,7),
            (-4.592201188381,6.467156727579),(-8.485281374239,4.949747468306),
            (-11.086554390135,2.678784026556),(-12,0),(-11.086554390135,-2.678784026556),
            (-8.485281374239,-4.949747468306),(-4.592201188381,-6.467156727579)]
        self.assertEqual([gaze.offsets(i,self.spec) for i in range(16)],expected)
        self.assertEqual(self.meta['sourceOffsetsPx'],[list(p) for p in expected])
        self.assertEqual(self.meta['sourceOffsetDecimalPlaces'],12)

    def test_saved_sixteen_frames_rows_and_neutral_are_exactly_rebuildable(self):
        with Image.open(FROZEN/'neutral.png') as image:
            self.assertEqual(image.convert('RGBA').tobytes(),self.neutral.tobytes())
        with Image.open(ROOT/'candidates/phase5/idle/frame-0.png') as image:
            self.assertEqual(image.convert('RGBA').tobytes(),self.neutral.tobytes())
        with Image.open(FROZEN/'strip.webp') as strip:
            self.assertEqual(strip.size,(1536,416))
            for i,frame in enumerate(self.frames):
                x,y = i%8*192,i//8*208
                self.assertEqual(strip.crop((x,y,x+192,y+208)).convert('RGBA').tobytes(),frame.tobytes())
                self.assertEqual(hashlib.sha256(frame.tobytes()).hexdigest().upper(),self.meta['frameHashes'][i])
                a = np.asarray(frame)
                self.assertFalse(a[0,:,3].any() or a[-1,:,3].any() or a[:,0,3].any() or a[:,-1,3].any())
                self.assertFalse(((a[...,3]==0)&np.any(a[...,:3]!=0,axis=2)).any())

    def test_bad_geometry_and_invalid_direction_are_rejected(self):
        for index in (-1,16,.5,True,None):
            with self.assertRaises(ValueError):
                gaze.offsets(index,self.spec)
        bad = copy.deepcopy(self.spec)
        bad['eyes'][0]['aperturePolygon'].append([610,447])
        with self.assertRaises(ValueError):
            gaze.layers(self.source,self.generated,bad)
        bad = copy.deepcopy(self.spec)
        bad['eyes'].reverse()
        with self.assertRaises(ValueError):
            gaze.validate_rig(bad)
        bad = copy.deepcopy(self.spec)
        bad['maximumDisplacementSourcePx'][0] = float('nan')
        with self.assertRaises(ValueError):
            gaze.validate_rig(bad)
        with self.assertRaises(ValueError):
            gaze.layers(self.source,Image.new('RGBA',(100,100)),self.spec)

    def test_eye_backing_and_partial_status_are_not_claimed_as_a_new_face_or_full_pet(self):
        art_meta = json.loads((gaze.ART/'build.json').read_text())
        self.assertGreater(art_meta['rawChangedPixelsOutsideEyeApertures'],0)
        self.assertEqual(art_meta['boundedChangedPixelsOutsideEyeApertures'],0)
        self.assertTrue(art_meta['neutralReconstructionUsesSameLayers'])
        self.assertTrue(art_meta['originalSourceAlphaPreservedExactly'])
        self.assertFalse(art_meta['fullRedrawAccepted'])
        self.assertEqual(self.meta['sourceSha256'],ACCEPTED_SHA)
        self.assertEqual(self.meta['directionCount'],16)
        self.assertEqual(self.meta['sourceGeometryRevision'],'observed-eye-opening-v2')
        self.assertEqual(self.meta['nativeRows'],[9,10])
        for key in ('bodyRotated','artMirrored','irisShapeWarp','facialGeometryRepair','originalSourceModified','installed','installableFullAtlas'):
            self.assertFalse(self.meta[key])
        self.assertEqual(self.meta['visualAcceptance'],'pending')


if __name__ == '__main__':
    unittest.main()
