"""Wave source/occlusion/real-hold checks; not an aesthetic certificate."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import unittest

import numpy as np
from PIL import Image, ImageDraw

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from canonical import ACCEPTED_SHA,clean_cutout,camera
import review_wave as art
import review_arm_backing as backing
import build_waving as wave
from protocol import DURATIONS


class Wave(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mother,cls.motion,cls.poses,cls.frames=wave.inputs()
        cls.metadata=json.loads((wave.OUT/'build.json').read_text())

    def test_bounded_art_keeps_all_outside_pixels_and_protected_parts(self):
        original=np.asarray(self.mother)
        guard=backing.specification()
        foreground=Image.new('L',self.mother.size)
        for polygon in guard['preservedForegroundPolygons']:
            ImageDraw.Draw(foreground).polygon(polygon,fill=255)
        for kind in ('middle','peak'):
            out,spec,raw=art.inputs(kind)
            pose,allowed=art.localized_pose(self.mother,raw,spec)
            pixels=np.asarray(pose)
            self.assertTrue(np.array_equal(original[~allowed],pixels[~allowed]))
            protected=np.asarray(foreground)>0
            self.assertTrue(np.array_equal(original[protected],pixels[protected]))
            for x0,y0,x1,y1 in guard['protectedRects']:
                self.assertTrue(np.array_equal(original[y0:y1,x0:x1],pixels[y0:y1,x0:x1]))
            self.assertGreater(np.any(original!=pixels,axis=2).sum(),10000)

    def test_corrupt_foreground_cannot_touch_the_face(self):
        _,spec,raw=art.inputs('peak')
        bad=copy.deepcopy(spec)
        bad['foregroundPolygon']=[[450,240],[780,240],[780,475],[450,475]]
        with self.assertRaises(ValueError):
            art.localized_pose(self.mother,raw,bad)

    def test_three_cels_use_four_holds_not_artificial_unique_frames(self):
        self.assertEqual(self.metadata['sequence'],['middle','peak','middle','relaxed'])
        self.assertEqual(self.frames[0].tobytes(),self.frames[2].tobytes())
        self.assertEqual(len(set(f.tobytes() for f in self.frames)),3)
        self.assertEqual(self.metadata['durationsMs'],DURATIONS[3])
        self.assertEqual(self.metadata['totalDurationMs'],700)
        self.assertEqual(self.metadata['actionDurationMs'],2100)
        self.assertEqual(self.metadata['repeatBeforeIdle'],3)

    def test_rest_is_canonical_native_cel_and_idle_entry(self):
        rest=art.native_frame(self.mother)
        self.assertEqual(self.frames[-1].tobytes(),rest.tobytes())
        with Image.open(ROOT/'candidates/phase5/idle/frame-0.png') as first:
            self.assertEqual(self.frames[-1].tobytes(),first.convert('RGBA').tobytes())
        self.assertTrue(self.metadata['canonicalRestRGBAExact'])
        self.assertEqual(self.metadata['camera'],camera(clean_cutout(self.mother)[0]))

    def test_saved_art_and_frames_match_rebuild_and_lossless_row(self):
        for kind in ('middle','peak'):
            out,spec,raw=art.inputs(kind)
            with Image.open(out/'pose.png') as saved:
                self.assertEqual(saved.convert('RGBA').tobytes(),self.poses[kind].tobytes())
        with Image.open(wave.OUT/'strip.webp') as strip:
            self.assertEqual(strip.size,(1536,208))
            for index,frame in enumerate(self.frames):
                with Image.open(wave.OUT/f'frame-{index}.png') as saved:
                    self.assertEqual(saved.convert('RGBA').tobytes(),frame.tobytes())
                self.assertEqual(strip.crop((index*192,0,(index+1)*192,208)).convert('RGBA').tobytes(),frame.tobytes())
                self.assertEqual(self.metadata['frameHashes'][index],hashlib.sha256(frame.tobytes()).hexdigest().upper())
            self.assertIsNone(strip.crop((768,0,1536,208)).getbbox())

    def test_transparent_pixels_and_edges_are_clean(self):
        for frame in self.frames:
            pixels=np.asarray(frame)
            self.assertFalse(pixels[0,:,3].any() or pixels[-1,:,3].any()
                             or pixels[:,0,3].any() or pixels[:,-1,3].any())
            self.assertFalse(((pixels[...,3]==0)&np.any(pixels[...,:3]!=0,axis=2)).any())

    def test_native_face_other_arm_and_shoes_stay_exact(self):
        rest=self.frames[-1]
        for frame in self.frames:
            # Conservative output boxes away from the bounded wave support.
            for box in ((73,47,122,81),(115,120,150,138),(72,180,122,202)):
                self.assertEqual(frame.crop(box).tobytes(),rest.crop(box).tobytes())

    def test_gif_native_holds_are_not_a_fast_loop(self):
        with Image.open(wave.OUT/'native-timing.gif') as gif:
            holds=[]
            for index in range(gif.n_frames):
                gif.seek(index)
                holds.append(gif.info['duration'])
        self.assertEqual(holds,DURATIONS[3])

    def test_candidate_boundary_and_no_rig_or_visual_overclaim(self):
        self.assertEqual(self.metadata['sourceSha256'],ACCEPTED_SHA)
        for key in ('installed','installableFullAtlas','facialGeometryRepair',
                    'fullRedrawAccepted','articulatedArmBuilt','nativeInterpolation','wholeBodyRotation'):
            self.assertFalse(self.metadata[key])
        self.assertEqual(self.metadata['visualMotionApproval'],'pending')
        self.assertEqual(self.metadata['bodyTranslationPx'],0)
        self.assertGreaterEqual(len(self.metadata['unresolved']),4)


if __name__=='__main__':
    unittest.main()
