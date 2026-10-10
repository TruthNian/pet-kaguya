"""Narrow approved mouth basis and exact native adoption, not full approval."""
import hashlib
import json
from pathlib import Path
import sys
import unittest
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import guide_failed_mouth as guide
import review_failed_mouth as art
import build_failed_mouth_study as study
import review_failed
from unittest.mock import patch
from canonical import ACCEPTED_SHA,load_canonical
from protocol import DURATIONS


class FailedMouth(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = study.inputs()
        cls.meta = json.loads((guide.OUT/'build.json').read_text(encoding='utf-8'))
        cls.animation = json.loads((study.OUT/'build.json').read_text(encoding='utf-8'))

    def test_fixed_full_square_projection_does_not_fit_the_mouth_or_include_whole_face(self):
        mother,before = load_canonical(),guide.parent()
        for filename,source in [('edit-guide.png',before),('width-reference.png',mother)]:
            with Image.open(guide.OUT/filename) as image:
                self.assertEqual(image.size,(100,100))
                self.assertEqual(image.convert('RGBA').tobytes(),guide.square(source).tobytes())
                self.assertIsNone(image.crop((0,60,100,100)).getbbox())
        self.assertEqual(guide.BOX,(570,370,670,430))
        with Image.open(guide.OUT/'generated.png') as image:
            self.assertEqual(image.size,art.RAW_SIZE)
        self.assertEqual(hashlib.sha256((guide.OUT/'generated.png').read_bytes()).hexdigest().upper(),art.GENERATED_SHA)
        self.assertTrue(self.meta['wholeSquareProjection'])
        self.assertFalse(self.meta['objectBoundsFitting'])

    def test_mouth_permission_keeps_every_outside_rgb_and_all_alpha_exact(self):
        data = self.data
        a,b = np.asarray(data['before']),np.asarray(data['pose'])
        np.testing.assert_array_equal(a[~data['allowed']],b[~data['allowed']])
        np.testing.assert_array_equal(a[...,3],b[...,3])
        self.assertEqual(int(data['allowed'].sum()),1254)
        self.assertEqual(int(np.any(a!=b,axis=2).sum()),self.meta['changedPixels'])
        receipt = json.loads((ROOT/'qa/failed-mouth-adoption-20261010.json').read_text(encoding='utf-8'))
        self.assertEqual(art.rgba_hash(data['pose']),receipt['sourceRGBAHash'])
        for x0,y0,x1,y1 in review_failed.specification()['eyeProtectedRects']:
            self.assertFalse(data['allowed'][y0:y1,x0:x1].any())
            np.testing.assert_array_equal(a[y0:y1,x0:x1],b[y0:y1,x0:x1])
        np.testing.assert_array_equal(a[:393],b[:393])
        np.testing.assert_array_equal(a[415:],b[415:])

    def test_unrecorded_parent_and_material_changes_are_rejected(self):
        before,mapped = art.inputs()
        bad = mapped.copy();bad.putpixel((610,400),(0,255,0,255))
        with self.assertRaises(ValueError):art.compose(before,bad)
        bad = before.copy();bad.putpixel((610,400),(0,255,0,255))
        with self.assertRaises(ValueError):art.compose(bad,mapped)

    def test_all_eight_saved_cels_rebuild_and_native_changes_stay_near_the_mouth(self):
        data,meta = self.data,self.animation
        with (Image.open(study.OUT/'strip.webp') as strip,
              Image.open(study.REFERENCE/'failed.webp') as old_strip,
              Image.open(ROOT/'candidates/phase5/failed/strip.webp') as current_strip,
              Image.open(ROOT/'candidates/phase5/global/spritesheet.webp') as global_atlas):
            for i,(old,new,change) in enumerate(zip(data['oldFrames'],data['frames'],meta['changesFromFrozenOldMouth'])):
                with Image.open(study.OUT/f'frame-{i}.png') as saved:
                    self.assertEqual(new.tobytes(),saved.convert('RGBA').tobytes())
                box = (i*192,0,(i+1)*192,208)
                self.assertEqual(old.tobytes(),old_strip.crop(box).convert('RGBA').tobytes())
                self.assertEqual(new.tobytes(),strip.crop(box).convert('RGBA').tobytes())
                self.assertEqual(new.tobytes(),current_strip.crop(box).convert('RGBA').tobytes())
                self.assertEqual(new.tobytes(),global_atlas.crop((i*192,5*208,(i+1)*192,6*208)).convert('RGBA').tobytes())
                self.assertEqual(art.rgba_hash(new),meta['frameHashes'][i])
                a,b = np.asarray(old),np.asarray(new)
                np.testing.assert_array_equal(a[...,3],b[...,3])
                changed = np.any(a!=b,axis=2)
                self.assertEqual(int(changed.sum()),change['changedPixels'])
                near = np.zeros(changed.shape,dtype=bool);near[66:79,89:108] = True
                self.assertFalse((changed&~near).any())
                self.assertFalse(b[0,:,3].any() or b[-1,:,3].any() or b[:,0,3].any() or b[:,-1,3].any())
            self.assertEqual(strip.size,(1536,208))
            receipt = json.loads((ROOT/'qa/failed-mouth-adoption-20261010.json').read_text(encoding='utf-8'))
            self.assertEqual(art.rgba_hash(global_atlas.convert('RGBA')),receipt['newAtlasRGBAHash'])
            self.assertEqual([c['changedPixels'] for c in meta['changesFromFrozenOldMouth']],receipt['nativeChangedPixelsPerCel'])
        self.assertEqual(meta['durationsMs'],DURATIONS[5])
        self.assertEqual(meta['keyframes'],data['active']['keyframes'])
        self.assertEqual(meta['baselineFrameHashes'],data['baseline']['frameHashes'])
        self.assertEqual(meta['frameHashes'],data['active']['frameHashes'])
        self.assertEqual(meta['actionDurationMs'],3660)
        self.assertEqual(meta['camera'],data['active']['camera'])
        with Image.open(study.OUT/'native-timing.gif') as gif:
            durations=[]
            for i in range(gif.n_frames):
                gif.seek(i);durations.append(gif.info['duration'])
            self.assertEqual(sum(durations),1220)

    def test_diagnostics_and_narrow_adoption_do_not_claim_original_width_or_legibility(self):
        self.assertEqual(guide.line_diagnostic(self.data['before']),self.meta['oldMouthLineDiagnostic'])
        self.assertEqual(guide.line_diagnostic(self.data['pose']),self.meta['acceptedMouthLineDiagnostic'])
        width = lambda record:record['bounds'][2]-record['bounds'][0]
        self.assertEqual(width(self.meta['oldMouthLineDiagnostic']),37)
        self.assertEqual(width(self.meta['acceptedMouthLineDiagnostic']),46)
        self.assertEqual(width(self.meta['originalSmileLineDiagnostic']),54)
        self.assertFalse(self.meta['diagnosticDefinesPermission'])
        for metadata in (self.meta,self.animation):
            self.assertEqual(metadata['sourceSha256'],ACCEPTED_SHA)
            self.assertTrue(metadata['adopted'])
            self.assertEqual(metadata['adoptionScope'],'mouth-line-development-basis-only')
            self.assertEqual(metadata['mouthLineVisualApproval'],'approved-as-development-basis')
            for field in ('installed','installableFullAtlas','facialGeometryRepair'):
                self.assertFalse(metadata[field],field)
        self.assertTrue(self.animation['currentFailedCelsRGBAExact'])
        self.assertEqual(self.animation['visualMotionApproval'],'pending')
        self.assertTrue(self.animation['nativeAlphaPreservedExactly'])

    def test_user_mouth_decision_cannot_silently_approve_face_motion_host_or_install(self):
        decision = art.decision()
        for field in ('fullMotionApproved','faceGeometryChangeApproved','hostChangeApproved','installationApproved'):
            expanded = dict(decision,**{field:True})
            with patch.object(art.json,'loads',return_value=expanded):
                with self.assertRaises(ValueError):art.decision()
        self.assertEqual(decision['answer'],'新嘴线更自然，采用为开发基础（建议）')


if __name__=='__main__':unittest.main()
