"""Single-factor/source/timing evidence, not a naturalness score or acceptance."""
import hashlib
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

import numpy as np
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import study_hop_height as study
from build_idle import sample
import hop_contact
import build_jumping as jumping
from protocol import DURATIONS


class HopHeight(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        (cls.source,cls.transform,cls.regions,cls.masks,cls.parent,
         cls.material,cls.before,cls.after)=study.inputs()
        cls.old=study.render_frames(cls.material,cls.before,cls.transform,cls.regions,cls.masks)
        cls.new=study.render_frames(cls.material,cls.after,cls.transform,cls.regions,cls.masks)
        cls.meta=json.loads((study.OUT/'build.json').read_text(encoding='utf-8'))

    def test_only_three_flight_offsets_change_and_no_contact_pose_or_schedule_changes(self):
        self.assertEqual(self.meta['durationsMs'],DURATIONS[4])
        for i,(a,b) in enumerate(zip(self.before,self.after)):
            self.assertEqual({**a,'actorY':b['actorY']},b)
            self.assertEqual(b['actorY'],a['actorY'] if i in (0,4) else a['actorY']/2)
        np.testing.assert_allclose([p['actorY'] for p in self.after],[0,-20/9,-4,-20/9,0],atol=1e-12)
        for a,b in ((8,0),(8,8),(4,4),(8,float('nan')),(True,4)):
            with self.assertRaises(ValueError):study.changed_poses(self.before,a,b)
        bad=[dict(p) for p in self.before];bad[0]['grounded']=False
        with self.assertRaises(ValueError):study.changed_poses(bad)

    def test_baseline_rebuilds_actual_cels_and_grounded_cels_remain_exact(self):
        self.assertEqual([study.rgba_hash(f) for f in self.old],self.parent['frameHashes'])
        self.assertEqual(self.meta['baselineFrameHashes'],self.parent['frameHashes'])
        self.assertEqual(self.meta['baselineKeyframes'],self.before)
        self.assertEqual(self.meta['keyframes'],self.after)
        for i in (0,4):self.assertEqual(self.old[i].tobytes(),self.new[i].tobytes())
        for i in (1,2,3):self.assertNotEqual(self.old[i].tobytes(),self.new[i].tobytes())

    def test_saved_native_pixels_hashes_blank_columns_alpha_and_gif_holds_rebuild(self):
        with Image.open(study.OUT/'strip.webp') as strip:
            self.assertEqual(strip.size,(1536,208))
            for i,frame in enumerate(self.new):
                with Image.open(study.OUT/f'frame-{i}.png') as saved:
                    self.assertEqual(saved.convert('RGBA').tobytes(),frame.tobytes())
                self.assertEqual(strip.crop((i*192,0,(i+1)*192,208)).convert('RGBA').tobytes(),frame.tobytes())
                self.assertEqual(study.rgba_hash(frame),self.meta['frameHashes'][i])
                a=np.asarray(frame)
                self.assertFalse(a[0,:,3].any() or a[-1,:,3].any() or a[:,0,3].any() or a[:,-1,3].any())
                self.assertFalse(((a[...,3]==0)&np.any(a[...,:3]!=0,axis=2)).any())
            self.assertIsNone(strip.crop((960,0,1536,208)).getbbox())
        with Image.open(study.OUT/'native-timing.gif') as gif:
            holds=[]
            for i in range(gif.n_frames):gif.seek(i);holds.append(gif.info['duration'])
            self.assertEqual(holds,DURATIONS[4])

    def test_face_material_has_rigid_camera_translation_without_new_geometry(self):
        x0,y0,x1,y1=self.regions['protectedFace']
        yy,xx=np.mgrid[y0:y1:4.7,x0:x1:5.3]
        expected=sample(self.material['source'],xx,yy)
        scale=self.transform['scale']
        for pose in self.after[1:4]:
            world_y=yy*scale+self.transform['y']+pose['actorY']
            actor_y=(world_y-self.transform['y']-pose['actorY'])/scale
            actual=hop_contact.sample_pose(self.material,xx,actor_y,pose,self.transform,self.regions,self.masks)
            np.testing.assert_allclose(actual,expected,rtol=0,atol=1e-10)

    def test_only_height_is_adopted_without_artwork_host_or_performance_claims(self):
        for name in ('adopted','activeAtlasChanged','currentJumpingCelsRGBAExact'):
            self.assertIs(self.meta[name],True)
        self.assertEqual(self.meta['adoptionScope'],'hop-height-development-basis-only')
        self.assertEqual(self.meta['userDecision'],jumping.HEIGHT_DECISION)
        for name in ('installed','installableFullAtlas','newArtworkGenerated',
                     'facialGeometryRepair','nativeInterpolation','continuousLandingProven','physicalBalanceProven'):
            self.assertIs(self.meta[name],False)
        self.assertEqual(self.meta['visualMotionApproval'],'pending')
        self.assertEqual(self.meta['strategyUserApproval'],'pending')
        self.assertEqual(self.meta['candidateApexOutputPx'],4)
        with Image.open(ROOT/'candidates/phase5/global/spritesheet.webp') as atlas:
            with Image.open(ROOT/'candidates/phase5/jumping/strip.webp') as active:
                self.assertEqual(atlas.crop((0,4*208,1536,5*208)).convert('RGBA').tobytes(),
                                 active.convert('RGBA').tobytes())
                with Image.open(study.OUT/'strip.webp') as accepted:
                    self.assertEqual(active.convert('RGBA').tobytes(),accepted.convert('RGBA').tobytes())
        # Unrelated future art improvements must not be blocked by freezing
        # the whole atlas to this turn's historical hash.
        self.assertEqual(hashlib.sha256((ROOT/'sources/canonical/artwork.png').read_bytes()).hexdigest().upper(),
                         self.meta['sourceSha256'])

    def test_frozen_reference_and_narrow_decision_reject_broad_or_changed_height_claims(self):
        with Image.open(study.REFERENCE/'jumping.webp') as saved:
            for i,frame in enumerate(self.old):
                self.assertEqual(saved.crop((i*192,0,(i+1)*192,208)).convert('RGBA').tobytes(),frame.tobytes())
        manifest=json.loads((study.REFERENCE/'manifest.json').read_text())
        self.assertEqual(hashlib.sha256((study.REFERENCE/'jumping.webp').read_bytes()).hexdigest().upper(),
                         manifest['fileSha256'])
        self.assertFalse(manifest['visualApprovalInherited'])
        decision=jumping.height_decision()
        for key in ('fullMotionApproved','faceGeometryChangeApproved','hostChangeApproved','installationApproved'):
            with patch.object(jumping.json,'loads',return_value={**decision,key:True}):
                with self.assertRaises(ValueError):jumping.height_decision()
        motion=jumping.specification()[0]
        wrong=json.loads(json.dumps(motion));wrong['flightModel']['apexOutputPx']=8
        with patch.object(jumping,'height_decision',return_value=decision), patch.object(jumping.json,'loads',return_value=wrong):
            with self.assertRaises(ValueError):jumping.specification()


if __name__ == '__main__':unittest.main()
