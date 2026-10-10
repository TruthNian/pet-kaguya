"""Exact current atlas, historical encoding isolation and rejected-art boundary."""
import hashlib
import json
import io
from pathlib import Path
import sys
import unittest
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import build_global_review as global_review
import inspect_review_hands_pair as study
from protocol import ATLAS_SIZE

PREVIOUS_RGBA='89D096DF28D82B7F9DBC103D6A840D0A2D805E02461A308AFA2C7D7B01E4AE42'


class EncodingAndRejectedStudy(unittest.TestCase):
    def test_actual_global_changes_only_accepted_mouth_and_height_and_keeps_exact_current_rows(self):
        with Image.open(global_review.OUT/'spritesheet.webp') as image:actual=image.convert('RGBA')
        # The encoding receipt is an immutable old-payload experiment, not a
        # permanent ban on approved artwork. Restore only the exact archived
        # old mouth and 8px hop rows: every other decoded byte must still match.
        historical = actual.copy()
        with Image.open(ROOT/'sources/reference/failed-mouth-v1/failed.webp') as image:
            historical.paste(image.convert('RGBA'),(0,5*208))
        with Image.open(ROOT/'sources/reference/jumping-height-8px/jumping.webp') as image:
            historical.paste(image.convert('RGBA'),(0,4*208))
        self.assertEqual(hashlib.sha256(historical.tobytes()).hexdigest().upper(),PREVIOUS_RGBA)
        self.assertNotEqual(actual.tobytes(),historical.tobytes())
        expected,_,_,_=global_review.assemble()
        self.assertEqual(actual.tobytes(),expected.tobytes())
        meta=json.loads((global_review.OUT/'build.json').read_text())
        self.assertEqual(meta['atlasRGBAHash'],hashlib.sha256(actual.tobytes()).hexdigest().upper())
        self.assertEqual(meta['encoding']['quality'],100)
        self.assertEqual(meta['encoding']['method'],6)
        self.assertTrue(meta['encoding']['lossless'])
        self.assertTrue(meta['encoding']['exact'])
        self.assertEqual(meta['decodedTextureBytes'],14057472)
        self.assertEqual(meta['visualAcceptance'],'pending')
        self.assertFalse(meta['installed'])
        receipt=json.loads((ROOT/'qa/lossless-encoding-20261010.json').read_text())
        self.assertEqual(receipt['global']['rgbaHash'],PREVIOUS_RGBA)
        self.assertEqual(receipt['global']['decodedTextureBytes'],14057472)
        baseline=receipt['global']['baseline']
        chosen=next(row for row in receipt['global']['measurements'] if row[:2]==[6,100])
        self.assertEqual(baseline[1],80)
        self.assertEqual(baseline[2]-chosen[2],receipt['global']['savedEncodedBytes'])
        self.assertFalse(receipt['visualImprovementClaimed'])
        self.assertFalse(receipt['hostPerformanceMeasured'])

    def test_encoder_keeps_hidden_rgb_partial_alpha_and_native_dimensions(self):
        source=Image.new('RGBA',ATLAS_SIZE)
        for xy,rgba in [((0,0),(231,67,18,0)),((191,207),(13,234,56,1)),
                        ((900,1000),(245,17,31,127)),((1535,2287),(121,22,250,255))]:
            source.putpixel(xy,rgba)
        encoded=global_review.encode_atlas(source)
        with Image.open(io.BytesIO(encoded)) as image:
            self.assertEqual(image.size,ATLAS_SIZE)
            self.assertEqual(image.convert('RGBA').tobytes(),source.tobytes())
        for bad in (Image.new('RGBA',(192,208)),Image.new('RGB',ATLAS_SIZE)):
            with self.assertRaises(ValueError):global_review.encode_atlas(bad)

    def test_failed_hand_edit_is_fixed_crop_without_face_and_is_not_an_active_pose(self):
        before,mapped=study.inputs()
        with Image.open(study.OUT/'raw-mapped-NOT-adopted.png') as image:
            self.assertEqual(image.convert('RGBA').tobytes(),mapped.tobytes())
        with Image.open(study.OUT/'edit-target.png') as image:target=image.convert('RGBA')
        self.assertEqual(target.size,(275,275))
        self.assertEqual(target.crop((0,0,275,220)).tobytes(),before.crop(study.BOX).tobytes())
        self.assertIsNone(target.crop((0,220,275,275)).getbbox())
        self.assertEqual(before.crop((0,0,1205,585)).tobytes(),mapped.crop((0,0,1205,585)).tobytes())
        meta=json.loads((study.OUT/'build.json').read_text())
        for key in ('adopted','activeAtlasChanged','installed','animationBuilt','anatomyImprovementProven',
                    'originalMoonMotifRemovalAllowed','faceIncluded','facialGeometryRepair'):
            self.assertFalse(meta[key])
        self.assertIn('waist crescent',meta['correctedSourceFact'])
        self.assertEqual(meta['generatedSha256'],study.GENERATED_SHA)
        current=json.loads((ROOT/'candidates/phase5/review/build.json').read_text())
        self.assertEqual(current['rightArmCompositionVersion'],'review-art-v6')
        self.assertTrue(current['heldHandsUnchangedFromV5'])


if __name__=='__main__':unittest.main()
