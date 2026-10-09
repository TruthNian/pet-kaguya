"""Native pose selection for approach/contact, never a continuous-motion claim."""
import copy
import json
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from locomotion_landing import reference
from protocol import DURATIONS


class LandingApproach(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.motion=json.loads((ROOT/'sources/canonical/locomotion-motion.json').read_text(encoding='utf-8'))

    def test_actual_centres_and_contact_starts_give_the_independent_seven_over_twentyseven_weight(self):
        steps=reference(self.motion['landingReference'],DURATIONS[1])
        self.assertEqual([(s['peakReferenceMs'],s['approachReferenceMs'],s['contactReferenceMs']) for s in steps],
                         [(180,300,360),(660,780,840)])
        for step in steps:
            self.assertEqual(step['approachWeightFraction'],[7,27])
            self.assertEqual(step['approachOffsetSourcePx'],[1.296296296296,-1.944444444444])
            self.assertEqual(step['contactOffsetSourcePx'],[0,0])

    def test_saved_keyframes_descend_before_contact_and_keep_the_existing_height_and_root_amplitude(self):
        keys=self.motion['keyframes']
        for foot,indices in (('left',(1,2,3)),('right',(5,6,7))):
            peak,approach,contact=[keys[i][foot] for i in indices]
            self.assertEqual(peak,[5,-7.5]); self.assertEqual(contact,[0,0])
            self.assertLess(peak[1],approach[1]);self.assertLess(approach[1],contact[1])
            self.assertLess(abs(contact[1]-approach[1]),abs(approach[1]-peak[1]))
            self.assertAlmostEqual(abs(contact[1]-approach[1])/7.5,7/27,places=12)
        self.assertEqual([k['rootSourcePx'] for k in keys],
                         [[0,0],[8,1],[12,1.5],[6,1.5],[-6,1.5],[-8,1],[-12,1.5],[0,0]])
        self.assertEqual(self.motion['durationsMs'],[120]*7+[220])
        self.assertFalse(self.motion['nativeInterpolation'])

    def test_saved_metadata_reports_real_last_step_without_claiming_smooth_takeoff_or_landing(self):
        for state in ('run_right','run_left'):
            meta=json.loads((ROOT/'candidates/phase5'/state/'build.json').read_text(encoding='utf-8'))
            self.assertTrue(meta['landingApproachAdded'])
            self.assertTrue(meta['landingReferenceIsNotHostInterpolation'])
            self.assertTrue(meta['takeoffRampMissing'])
            self.assertFalse(meta['continuousLandingProven'])
            self.assertEqual(meta['landingReference'],reference(self.motion['landingReference'],DURATIONS[1]))
            self.assertEqual(meta['lastVerticalLandingStepSourcePx'],[1.944444444444]*2)
            self.assertEqual(meta['maximumFootLiftOutputPx'],1.1875)
            self.assertEqual(meta['visualMotionApproval'],'pending')

    def test_false_curves_phases_peak_scales_and_illegal_time_slots_are_rejected(self):
        spec=self.motion['landingReference']
        for key,value in [('curve','continuous-native-interpolation'),('sampleTimes','uniform-new-fps'),
                          ('peakOffsetSourcePx',[10,-15]),('offsetDecimalPlaces',6),('steps',[])]:
            bad=copy.deepcopy(spec);bad[key]=value
            with self.assertRaises(ValueError):reference(bad,DURATIONS[1])
        for timing in ([120]*7,[120]*7+[0],[120]*7+[True],[120]*7+[220.5]):
            with self.assertRaises(ValueError):reference(spec,timing)


if __name__=='__main__':unittest.main()
