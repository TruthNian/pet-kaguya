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

    def test_actual_centres_and_next_cycle_contact_use_the_real_asymmetric_hold_times(self):
        steps=reference(self.motion['landingReference'],DURATIONS[1])
        self.assertEqual([(s['peakReferenceMs'],s['approachReferenceMs'],s['contactReferenceMs']) for s in steps],
                         [(300,420,480),(780,950,1060)])
        self.assertEqual([(s['takeoffReferenceMs'],s['riseReferenceMs']) for s in steps],[(120,180),(600,660)])
        self.assertEqual([s['approachWeightFraction'] for s in steps],[[7,27],[3751,10976]])
        self.assertEqual([s['approachOffsetSourcePx'] for s in steps],
                         [[1.296296296296,-1.944444444444],[1.708728134111,-2.563092201166]])
        for step in steps:
            self.assertEqual(step['riseWeightFraction'],[7,27])
            self.assertEqual(step['riseOffsetSourcePx'],[1.296296296296,-1.944444444444])
            self.assertEqual(step['contactOffsetSourcePx'],[0,0])

    def test_saved_keyframes_descend_before_contact_and_keep_the_existing_height_and_root_amplitude(self):
        keys=self.motion['keyframes']
        for foot,indices in (('left',(1,2,3,4)),('right',(5,6,7,0))):
            rise,peak,approach,contact=[keys[i][foot] for i in indices]
            self.assertEqual(peak,[5,-7.5]); self.assertEqual(contact,[0,0])
            self.assertLess(peak[1],rise[1]); self.assertLess(rise[1],0)
            self.assertLess(peak[1],approach[1]);self.assertLess(approach[1],contact[1])
            self.assertLess(abs(contact[1]-approach[1]),abs(approach[1]-peak[1]))
        self.assertEqual([k['rootSourcePx'] for k in keys],
                         [[0,0],[8,1],[12,1.5],[8,1],[0,0],[-8,1],[-12,1.5],[-8,1]])
        self.assertEqual(keys[0],keys[4]); self.assertNotEqual(keys[0],keys[-1])
        self.assertEqual(self.motion['durationsMs'],[120]*7+[220])
        self.assertFalse(self.motion['nativeInterpolation'])

    def test_saved_metadata_reports_rising_pose_and_real_last_step_not_continuous_motion(self):
        for state in ('run_right','run_left'):
            meta=json.loads((ROOT/'candidates/phase5'/state/'build.json').read_text(encoding='utf-8'))
            self.assertTrue(meta['landingApproachAdded'])
            self.assertTrue(meta['landingReferenceIsNotHostInterpolation'])
            self.assertNotIn('takeoffRampMissing',meta)
            self.assertTrue(meta['risingPoseAdded'])
            self.assertFalse(meta['continuousTakeoffProven'])
            self.assertFalse(meta['continuousLandingProven'])
            self.assertEqual(meta['landingReference'],reference(self.motion['landingReference'],DURATIONS[1]))
            self.assertEqual(meta['lastVerticalLandingStepSourcePx'],[1.944444444444,2.563092201166])
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

    def test_pose_budget_contains_rise_peak_approach_and_opposite_support_in_each_half(self):
        keys=self.motion['keyframes']
        for foot,other,indices,contact in [('left','right',(1,2,3),4),('right','left',(5,6,7),0)]:
            for i in indices:
                self.assertEqual(keys[i]['support'],[other])
                self.assertEqual(keys[i][other],[0,0])
                self.assertLess(keys[i][foot][1],0)
            self.assertEqual(keys[contact]['support'],['left','right'])
        # A cyclic transition is included; omitting it would hide the right
        # contact. Compare coordinates, not a supposed aesthetic score.
        largest_root=max(abs(keys[(i+1)%8]['rootSourcePx'][0]-k['rootSourcePx'][0]) for i,k in enumerate(keys))
        largest_foot=max(abs(keys[(i+1)%8][foot][1]-k[foot][1]) for foot in ('left','right') for i,k in enumerate(keys))
        self.assertEqual(largest_root,8)
        self.assertAlmostEqual(largest_foot,5.555555555556,places=12)
        self.assertLess(largest_root,12);self.assertLess(largest_foot,7.5) # Earlier committed design.


if __name__=='__main__':unittest.main()
