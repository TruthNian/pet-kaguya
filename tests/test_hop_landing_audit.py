"""Descriptive last-hold tradeoffs are not automatic visual approval."""
import math
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import inspect_hop_landing as audit


class LandingAuditMath(unittest.TestCase):
    def test_zero_landing_reduces_idle_exit_but_increases_the_next_anticipation(self):
        current = audit.root_tradeoff(.25,.8,0)
        zero = audit.root_tradeoff(0,.8,0)
        self.assertAlmostEqual(current['nextAnticipationRootJumpPx'],.55)
        self.assertAlmostEqual(current['finalIdleRootJumpPx'],.25)
        self.assertGreater(zero['nextAnticipationRootJumpPx'],current['nextAnticipationRootJumpPx'])
        self.assertLess(zero['finalIdleRootJumpPx'],current['finalIdleRootJumpPx'])

    def test_one_held_root_cannot_equal_two_distinct_successors(self):
        for i in range(-20,101):
            result = audit.root_tradeoff(i/100,.8,0)
            self.assertGreaterEqual(result['twoExitWorstRootJumpPx'],.4-1e-12)
        self.assertAlmostEqual(audit.root_tradeoff(.4,.8,0)['twoExitWorstRootJumpPx'],.4)
        # Minimax is a coordinate result, not the most natural pose.
        self.assertEqual(audit.root_tradeoff(.4,.8,0)['finalIdleRootJumpPx'],.4)

    def test_nonfinite_non_numeric_and_boolean_inputs_fail(self):
        for value in (math.nan,math.inf,-math.inf,True,'0',None):
            for position in range(3):
                values = [.25,.8,0];values[position] = value
                with self.assertRaises(ValueError):audit.root_tradeoff(*values)


class ActualLandingAudit(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.data = audit.inputs()

    def test_current_five_cels_and_first_idle_are_actual_reconstructed_assets(self):
        self.assertEqual([audit.rgba_hash(f) for f in self.data['original']],self.data['active']['frameHashes'])
        self.assertEqual(self.data['motion']['flightModel']['apexOutputPx'],4)
        self.assertEqual(self.data['poses'][4]['bodyY'],.25)
        self.assertEqual(self.data['variants'][0]['frames'][4].tobytes(),self.data['original'][4].tobytes())

    def test_only_last_compression_changes_and_rigid_face_and_planted_targets_hold(self):
        original = self.data['original']
        for variant in self.data['variants']:
            expected = dict(self.data['poses'][4],bodyY=variant['compression'])
            self.assertEqual(variant['pose'],expected)
            for index in range(4):self.assertEqual(variant['frames'][index].tobytes(),original[index].tobytes())
            self.assertLessEqual(variant['faceRigidPremultError'],1e-10)
            for leg in variant['jointEvidence']:
                self.assertTrue(leg['grounded'])
                for actual,design in zip(leg['actualSegmentLengthsSourcePx'],leg['designSegmentLengthsSourcePx']):
                    self.assertAlmostEqual(actual,design,places=8)
        self.assertEqual(self.data['variants'][0]['changedLanding']['changedRGBAPixels'],0)
        self.assertTrue(all(v['changedLanding']['changedRGBAPixels']>0 for v in self.data['variants'][1:]))

    def test_actual_box_mismatch_is_exposed_not_silently_labelled_exact_shoe_paint(self):
        for variant in self.data['variants'][:3]:
            self.assertTrue(all(box['RGBAExact'] for box in variant['shoeBoxComparison']))
        fourth = self.data['variants'][3]
        self.assertFalse(fourth['shoeBoxComparison'][0]['RGBAExact'])
        self.assertEqual(fourth['shoeBoxComparison'][0]['changedPixels'],1)
        self.assertEqual(fourth['shoeBoxComparison'][0]['changedNativeCoordinates'],[[92,186]])
        self.assertEqual(fourth['shoeBoxComparison'][0]['maximumChannelDifference'],1)
        self.assertTrue(fourth['shoeBoxComparison'][1]['RGBAExact'])
        probe = fourth['shoeSupportProbes'][0]
        for key in ['foregroundCoordinateMaximumDifference','foregroundPaintMaximumDifference','occlusionMaximumDifference']:
            self.assertEqual(probe[key],0)
        self.assertGreater(probe['backingContributionMaximumDifference'],1)
        self.assertLess(probe['residualAfterBackingContribution'],1e-10)
        self.assertTrue(probe['supportReconstructsObservedNativePixels'])
        self.assertTrue(probe['sameBackingRestoresPixel'])


if __name__ == '__main__':unittest.main()
