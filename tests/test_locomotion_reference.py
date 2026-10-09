"""Actual frozen inputs, not an aesthetic test or future candidate pixel lock."""
import json
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import locomotion_reference as reference
from held_timing import validate_decision, DECISION


class RigidReference(unittest.TestCase):
    def test_frozen_inputs_have_actual_file_bytes_and_all_sixteen_historical_cels(self):
        metadata,strips=reference.load()
        self.assertEqual(metadata['commit'],reference.COMMIT)
        for name,strip in strips.items():
            self.assertEqual(strip.size,(1536,208))
            self.assertEqual(len(metadata['states'][name]['frameHashes']),8)
        self.assertFalse(metadata['visualApprovalInherited'])
        self.assertFalse(metadata['installableFullAtlas']);self.assertFalse(metadata['installed'])

    def test_baseline_pose_and_clock_contracts_match_the_present_comparison_scope_not_new_pixels(self):
        metadata,_=reference.load()
        for name,entry in metadata['states'].items():
            current=json.loads((ROOT/f'candidates/phase5/{name}/build.json').read_text(encoding='utf-8'))
            for key,value in entry['contract'].items():self.assertEqual(current[key],value)
            self.assertNotEqual(current['frameHashes'],entry['frameHashes'])
        self.assertTrue(json.loads((ROOT/'sources/canonical/locomotion-cadence-decision-20261009.json').read_text(encoding='utf-8'))['reviewedHashesAreHistoricalEvidenceNotFuturePixelLocks'])

    def test_held_timing_choice_is_temporary_and_does_not_approve_structure_or_new_host(self):
        decision=json.loads((ROOT/'sources/canonical/held-gesture-boundary-decision-20261009.json').read_text(encoding='utf-8'))
        self.assertEqual(decision['scope'],'temporary-held-timing-boundary-only')
        self.assertEqual(decision['answer'],'暂保留保持姿势，继续优化结构（建议）')
        self.assertTrue(decision['heldTimingAcceptedTemporarily']);self.assertTrue(decision['knownEntryExitJumpsRemain'])
        for key in ('renderedHandStructureApproved','sleeveAndHairSeamsApproved','fullNaturalnessApproved',
                    'allMotionApproved','independentPetHostAuthorized','installedHostChangeAuthorized'):
            self.assertFalse(decision[key])
        for name in ('waiting', 'review'):
            motion=json.loads((ROOT/f'sources/canonical/{name}-motion.json').read_text(encoding='utf-8'))
            validate_decision(motion)
            current=json.loads((ROOT/f'candidates/phase5/{name}/build.json').read_text(encoding='utf-8'))
            self.assertEqual(motion['heldTimingUserDecision'],DECISION)
            self.assertEqual(current['heldTimingUserDecision'],DECISION)
            self.assertTrue(current['heldTimingAcceptedTemporarily'])
            self.assertEqual(current['strategyUserApproval'],'pending')
            self.assertEqual(current['visualMotionApproval'],'pending')
            with self.assertRaises(ValueError):validate_decision(dict(motion,heldTimingUserDecision='invented.json'))


if __name__=='__main__':unittest.main()
