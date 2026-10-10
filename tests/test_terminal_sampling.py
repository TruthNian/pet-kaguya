"""Small filter-arithmetic checks; unadopted historical research is not a current-artwork gate."""
from pathlib import Path
import sys
import unittest

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
import terminal_sampling as sampling


class TerminalFilter(unittest.TestCase):
    def test_float_filter_matches_independent_64_bit_reference(self):
        rng = np.random.default_rng(173)
        alpha = rng.uniform(0, 255, (39, 45, 1))
        pixels = np.concatenate((rng.uniform(0, 1, (39, 45, 3))*alpha, alpha), axis=2)
        actual = sampling.filtered_float(pixels, (15, 13))
        expected = sampling.reference64(pixels, (15, 13))
        self.assertLess(float(np.abs(actual-expected).max()), 2e-5)
        actual8 = np.asarray(sampling.floating(pixels, (15, 13)), dtype=int)
        expected8 = np.asarray(sampling.rgba8(expected), dtype=int)
        difference = np.abs(actual8-expected8)
        self.assertLessEqual(int(difference.max()), 1)
        # Float32 filter rounding can cross a final half-integer. Check the
        # actual real-valued unassociation difference, not false RGBA equality.
        def straight(filtered):
            result = sampling.constrain(filtered)
            np.divide(result[..., :3]*255, result[..., 3:4], out=result[..., :3], where=result[..., 3:4]>0)
            return result
        actual_straight, expected_straight = straight(actual), straight(expected)
        self.assertLess(float(np.abs(actual_straight-expected_straight).max()), 4e-5)
        crossed = difference > 0
        self.assertTrue(np.all(np.abs(expected_straight[crossed]-(np.floor(expected_straight[crossed])+.5))<4e-5))

    def test_uniform_material_and_transparent_rgb_are_not_darkened(self):
        pixels = np.empty((36, 36, 4), dtype=float)
        pixels[..., 3] = 128
        pixels[..., :3] = np.array([251, 169, 63])*128/255
        result = np.asarray(sampling.floating(pixels, (12, 12)))
        self.assertTrue(np.all(result == [251, 169, 63, 128]))
        pixels[:] = 0
        self.assertFalse(np.asarray(sampling.floating(pixels, (12, 12))).any())

    def test_thin_coloured_coverage_has_lower_composited_not_hidden_rgb_error(self):
        yy, xx = np.mgrid[:33, :39]
        alpha = .25+(xx/38)*2.5+(yy/32)*1.25
        pixels = np.concatenate((np.array([249, 166, 57])[None, None, :]*alpha[..., None]/255,
                                 alpha[..., None]), axis=2)
        oracle = sampling.reference64(pixels, (13, 11))
        old = sampling.composite_error(sampling.legacy(pixels, (13, 11)), oracle)
        new = sampling.composite_error(sampling.floating(pixels, (13, 11)), oracle)
        self.assertLess(new['compositedMeanAbsoluteError'], old['compositedMeanAbsoluteError'])

    def test_invalid_input_fails_without_mutation_and_filter_overshoot_is_bounded(self):
        good = np.zeros((9, 9, 4)); before = good.copy()
        for value in (np.array([1.]), np.zeros((9, 9, 3)), np.full((9, 9, 4), np.nan),
                      np.full((9, 9, 4), -1), np.full((9, 9, 4), 256)):
            with self.assertRaises(ValueError): sampling.floating(value)
        invalid = good.copy(); invalid[..., 0] = 1
        with self.assertRaises(ValueError): sampling.floating(invalid)
        sampling.floating(good, (3, 3))
        self.assertTrue(np.array_equal(before, good))
        extreme = np.array([[[-3, 8, 280, 270], [9, -3, 1, -1]]], dtype=float)
        self.assertTrue(np.array_equal(np.asarray(sampling.rgba8(extreme)), [[[0, 8, 255, 255], [0, 0, 0, 0]]]))



if __name__ == '__main__': unittest.main()
