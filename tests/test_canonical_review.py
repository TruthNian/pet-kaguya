"""Review integrity only; no test here certifies face shape or cuteness."""
import hashlib
import json
from pathlib import Path
import sys
import unittest

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
from prepare_identity import load_source
from protocol import crop
from review_jaw import shared_previews, edit_diagnostics


class CanonicalReview(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out = ROOT/'candidates/phase4/canonical-v3'
        cls.before = Image.open(ROOT/'candidates/phase4/canonical-v2/artwork.png').convert('RGBA')
        cls.after = Image.open(cls.out/'artwork.png').convert('RGBA')
        cls.original = crop(load_source(), 0, 0)
        cls.metadata = json.loads((cls.out/'review.json').read_text())

    def test_generation_outputs_are_archived_without_overwriting(self):
        for folder, expected in [('canonical-v2', 'A627FC599B76025E767682991027AAA3A0E96DF26465C86BD5E077E65A39394A'),
                                 ('canonical-v3', '65401EFDFEF0205D0CEA30AD08A0F14911C20B1B83468DBB6B3619E7DC89430A')]:
            path = ROOT/f'candidates/phase4/{folder}/artwork.png'
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest().upper(), expected)
            self.assertTrue(path.with_name('prompt.txt').is_file())

    def test_preview_uses_identical_transform_not_per_face_fitting(self):
        (a, b), transform = shared_previews(self.before, self.before, self.original)
        self.assertEqual(a.tobytes(), b.tobytes())
        self.assertFalse(transform['independentSubjectOrFaceFitting'])
        self.assertFalse(transform['artworkAlphaModified'])

    def test_saved_previews_and_diagnostics_are_reproducible(self):
        frames, transform = shared_previews(self.before, self.after, self.original)
        self.assertEqual(transform, self.metadata['sharedPreviewTransform'])
        for frame, filename in zip(frames, ['before-front.png', 'front.png']):
            saved = Image.open(self.out/filename).convert('RGBA')
            self.assertEqual(frame.tobytes(), saved.tobytes())
            self.assertEqual(frame.size, (192, 208))
            pixels = np.asarray(frame)
            self.assertFalse(((pixels[..., 3] == 0) & np.any(pixels[..., :3] != 0, axis=2)).any())
        self.assertEqual(edit_diagnostics(self.before, self.after), self.metadata['editDiagnostics'])

    def test_mother_approval_does_not_hide_edit_drift_or_claim_completed_animation(self):
        self.assertFalse(self.metadata['editDiagnostics']['exactlyJawOnly'])
        self.assertGreater(self.metadata['editDiagnostics']['outsideROIChangedPixels'], 0)
        self.assertTrue(self.metadata['adoptedForAnimation'])
        self.assertTrue(self.metadata['approvalDoesNotMeanCompletedAnimation'])
        for flag in ['animationBuilt', 'installed', 'nativeResolutionChanged']:
            self.assertFalse(self.metadata[flag])

    def test_accepted_source_is_v3_and_cannot_fallback_to_rejected_faces(self):
        decision = json.loads((ROOT/'sources/canonical/manifest.json').read_text(encoding='utf-8'))
        self.assertEqual(decision['candidate'], 'canonical-v3')
        self.assertEqual(decision['sha256'], self.metadata['artworkSha256'])
        self.assertTrue(decision['approvedAsMotherPose'])
        self.assertTrue(decision['faceShapeLocked'])
        self.assertFalse(decision['facialGeometryRepairAllowed'])
        self.assertFalse(decision['fallbackToRejectedCandidatesAllowed'])
        source = ROOT/decision['artwork']
        self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest().upper(), decision['sha256'])
        with Image.open(source) as source_image:
            self.assertEqual(source_image.size, tuple(decision['dimensions']))


if __name__ == '__main__':
    unittest.main()
