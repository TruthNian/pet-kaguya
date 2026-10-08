import hashlib
import json
import sys
import unittest
from pathlib import Path

import numpy as np
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from audit import analyze
from build import SOURCE_HASH, coordinates, masters, render
from protocol import ATLAS_SIZE, COUNTS, DURATIONS, crop


class Assets(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source=Image.open(ROOT/'baseline/phase2/spritesheet.webp').convert('RGBA')
        cls.atlas=Image.open(ROOT/'pet/spritesheet.webp').convert('RGBA')
        cls.base=masters(cls.source)

    def test_baseline_is_immutable(self):
        self.assertEqual(hashlib.sha256((ROOT/'baseline/phase2/spritesheet.webp').read_bytes()).hexdigest().upper(),SOURCE_HASH)

    def test_structure_transparency_and_padding(self):
        result=analyze(ROOT/'pet/spritesheet.webp')
        self.assertEqual(tuple(result['size']),ATLAS_SIZE)
        for key in ['missing','unexpected','borderContacts']:
            self.assertEqual(result[key],[],key)
        self.assertEqual(result['transparentRgbResidue'],0)

    def test_native_schedule_is_preserved(self):
        # Deliberate identical holds are legal. Pixel uniqueness is NOT an
        # animation-quality requirement; inspect the actual schedule instead.
        metadata=json.loads((ROOT/'pet/build.json').read_text(encoding='utf-8'))
        self.assertFalse(metadata['nativeTimingChanged'])
        self.assertFalse(metadata['nativeFrameCountChanged'])
        for row,durations in enumerate(DURATIONS):
            frames=[f for f in metadata['frames'] if f['row']==row]
            self.assertEqual(len(frames),len(durations))
            elapsed=0
            for col,(frame,duration) in enumerate(zip(frames,durations)):
                self.assertEqual(frame['col'],col)
                self.assertEqual(frame['durationMs'],duration)
                self.assertAlmostEqual(frame['phase'],elapsed/sum(durations))
                elapsed+=duration

    def test_no_fold_in_visible_rig(self):
        for row in range(9):
            visible=np.asarray(self.base[row])[...,3]>32
            for i in range(64):
                sx,sy,_=coordinates(row,i/64)
                dxdy,dxdx=np.gradient(sx)
                dydy,dydx=np.gradient(sy)
                determinant=dxdx*dydy-dxdy*dydx
                self.assertGreater(float(determinant[visible].min()),.5,f'excessive compression row {row}, phase {i/64}')

    def test_continuous_periodic_rig(self):
        for row in range(9):
            a=np.asarray(render(self.base[row],row,0))
            b=np.asarray(render(self.base[row],row,1))
            self.assertTrue(np.array_equal(a,b),f'row {row}')

    def test_standing_shoes_are_pinned(self):
        for row in [0,5,6,7,8]:
            # Shoes only; hair and bead ends may move at the same y.
            region=np.asarray(crop(self.atlas,row,0))[178:203,73:126]
            for col in range(1,len(DURATIONS[row])):
                self.assertTrue(np.array_equal(region,np.asarray(crop(self.atlas,row,col))[178:203,73:126]),f'row {row}, col {col}')

    def test_run_contact_is_pinned(self):
        for row in [1,2]:
            for col in range(8):
                a=np.asarray(crop(self.atlas,row,col))
                ys=np.where((a[...,3]>32)&(np.indices(a.shape[:2])[0]>153))[0]
                self.assertEqual(int(ys.max()),202)

    def test_jump_uses_actual_duration_knots_and_lands_on_last_cell(self):
        from build import parameters
        phase=sum(DURATIONS[4][:2])/sum(DURATIONS[4])
        self.assertEqual(parameters(4,phase)['lift'],-7.)
        last=sum(DURATIONS[4][:-1])/sum(DURATIONS[4])
        self.assertEqual(parameters(4,last)['lift'],0.)

    def test_directions_do_not_rotate_shoes_or_flip_identity(self):
        shoe=np.asarray(crop(self.atlas,9,0))[178:203,73:126]
        for i in range(16):
            a=np.asarray(crop(self.atlas,9+i//8,i%8))
            self.assertTrue(np.array_equal(shoe,a[178:203,73:126]),f'direction {i}')
            # Moon ornament remains on viewer-right, not mirrored by left look.
            gold=a[12:42,111:140,:3]
            self.assertGreater(int(((gold[...,0]>150)&(gold[...,1]>95)).sum()),100)

    def test_rebuild_matches_checked_in_pixels(self):
        for row,durations in enumerate(DURATIONS):
            elapsed=0
            for col,duration in enumerate(durations):
                expected=render(self.base[row],row,elapsed/sum(durations))
                self.assertTrue(np.array_equal(np.asarray(expected),np.asarray(crop(self.atlas,row,col))),f'{row},{col}')
                elapsed+=duration


if __name__=='__main__': unittest.main()
