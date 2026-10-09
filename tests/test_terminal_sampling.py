"""Filter arithmetic and complete actual-cel isolation, not visual approval."""
import hashlib
import json
from pathlib import Path
import sys
import unittest

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
import terminal_sampling as sampling
import study_terminal_sampling as study
from canonical import ACCEPTED_SHA


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


class ActualCoverage(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.meta = json.loads((study.OUT/'build.json').read_text(encoding='utf-8'))
        with Image.open(study.OUT/'spritesheet.webp') as image: cls.atlas = image.convert('RGBA')
        with Image.open(ROOT/'candidates/phase5/global/spritesheet.webp') as image: cls.old = image.convert('RGBA')

    def test_all_actual_cels_and_only_the_unused_native_idle_slot_are_replaced(self):
        self.assertEqual(self.meta['sourceSha256'], ACCEPTED_SHA)
        self.assertEqual(self.meta['coverage'], dict(actionStates=9, lookDirections=16,
                          actualTimedActionCels=57, comparedCels=73))
        self.assertEqual(study.digest(self.atlas), self.meta['candidateAtlasRGBAHash'])
        self.assertEqual(study.digest(self.old), self.meta['baselineAtlasRGBAHash'])
        records = []
        touched = np.zeros((2288, 1536), dtype=bool)
        for name in study.STATES+['look']:
            entry = self.meta['states'][name]
            active = study.metadata(name)
            self.assertEqual(entry['legacyFrameHashes'], active['frameHashes'])
            self.assertEqual(entry['camera'], active['camera'])
            self.assertEqual(entry['durationsMs'], active.get('durationsMs'))
            for i, record in enumerate(entry['cels']):
                row = 9+i//8 if name == 'look' else study.STATES.index(name)
                box = ((i%8)*192, row*208, (i%8+1)*192, (row+1)*208)
                touched[box[1]:box[3], box[0]:box[2]] = True
                self.assertEqual(study.digest(self.atlas.crop(box)), record['candidateRGBAHash'])
                self.assertEqual(study.digest(self.old.crop(box)), record['legacyRGBAHash'])
                self.assertLess(record['candidateError']['compositedMeanAbsoluteError'],
                                record['legacyError']['compositedMeanAbsoluteError'])
                self.assertLess(record['float32FilterMaximumError'], 4e-5)
                records.append(record)
        touched[:208, 6*192:7*192] = True
        self.assertEqual(self.atlas.crop((6*192, 0, 7*192, 208)).tobytes(), self.atlas.crop((0, 0, 192, 208)).tobytes())
        self.assertTrue(np.array_equal(np.asarray(self.atlas)[~touched], np.asarray(self.old)[~touched]))
        self.assertEqual(len(records), 73)
        self.assertAlmostEqual(self.meta['meanLegacyCompositedError'],
                               np.mean([r['legacyError']['compositedMeanAbsoluteError'] for r in records]))

    def test_no_art_geometry_fps_memory_or_adoption_claim(self):
        self.assertEqual(self.atlas.size, (1536, 2288))
        self.assertEqual(self.meta['decodedBytes'], 14057472)
        self.assertTrue(self.meta['allLegacyCelsReconstructedExactly'])
        self.assertTrue(self.meta['geometryAndSourcePixelsUnchanged'])
        self.assertTrue(self.meta['allCelsLowerMeanCompositedError'])
        for key in ('oracleIsAestheticProof', 'hostResolutionChanged', 'hostFpsChanged',
                    'nativeTimingsChanged', 'sourcePrecompositionRemoved', 'nativeUpscalingChanged',
                    'activeAtlasChanged', 'adopted', 'installableFullAtlas', 'installed'):
            self.assertFalse(self.meta[key], key)
        self.assertEqual(self.meta['visualApproval'], 'pending')

    def test_hop_closure_uses_its_own_material_and_all_three_renderer_hooks_rebuild(self):
        jobs, _ = study.jobs()
        # A first-run late-binding defect used run_left's gaze/follow material
        # in jumping. Verify the actual callback route after all jobs are built.
        for name, index in [('idle', 2), ('jumping', 0), ('run_left', 6), ('review', 0), ('look', 15)]:
            frame, record = study.compare(name, index, jobs[name][index],
                                        self.meta['states'][name]['legacyFrameHashes'][index])
            self.assertEqual(record, self.meta['states'][name]['cels'][index])
            row = 9+index//8 if name == 'look' else study.STATES.index(name)
            self.assertEqual(frame.tobytes(), self.atlas.crop(((index%8)*192, row*208,
                                   (index%8+1)*192, (row+1)*208)).tobytes())


if __name__ == '__main__': unittest.main()
