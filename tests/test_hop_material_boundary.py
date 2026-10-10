"""A source-support diagnosis, not adoption of the padded counterfactual."""
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from inspect_hop_material_boundary import inspect


class HopMaterialBoundary(unittest.TestCase):
    def test_actual_fractional_crop_edge_isolated_by_extending_both_paint_and_occlusion(self):
        result=inspect()
        self.assertEqual(result['affectedHighGridSamples'],82)
        self.assertEqual(result['localMaterialBox'],[425,936,810,1240])
        self.assertEqual(result['affectedOutputGridBBox'],[233,461,339,462])
        y0,y1=result['affectedSourceCoordinateBBox'][1::2]
        self.assertAlmostEqual(y0,935.3245614035088,places=9)
        self.assertEqual(y0,y1)
        self.assertGreater(result['legacyMaximumPremultDifference'],9)
        self.assertLess(result['activeV2MaximumPremultDifference'],1e-10)
        self.assertLess(result['zeroExtendedMaximumPremultDifference'],1e-10)
        self.assertTrue(result['zeroExtendedIdentityWithin1eMinus10'])
        for key in ('activeRendererChanged','installed','artworkChanged','fullMotionApproved'):
            self.assertFalse(result[key])


if __name__=='__main__':unittest.main()
