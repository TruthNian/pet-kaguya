"""Identity, contact and discrete-time proofs; not motion/aesthetic approval."""
import hashlib
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
from canonical import load_canonical, clean_cutout, camera, ACCEPTED_SHA
from build_idle import coordinates, render, sample
from leg_material import inverse_kinematics, leg_coordinates
import refine_leg_composition as leg
import locomotion_render as sampling
import hop_contact
import build_jumping as jumping
import review_arm_backing as backing
from protocol import DURATIONS


class HiddenBacking(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = load_canonical()
        cls.spec = backing.specification()
        cls.plate, cls.allowed = backing.localized_backing(cls.source, backing.load_generated(), cls.spec)

    def test_outside_and_preserved_foreground_are_exact_source_pixels(self):
        a, b = np.asarray(self.source), np.asarray(self.plate)
        self.assertTrue(np.array_equal(a[~self.allowed], b[~self.allowed]))
        self.assertGreater(np.count_nonzero(np.any(a != b, axis=2)), 50000)
        for x0, y0, x1, y1 in self.spec['protectedRects']:
            self.assertTrue(np.array_equal(a[y0:y1,x0:x1], b[y0:y1,x0:x1]))
        mask = Image.new('L', self.source.size)
        for polygon in self.spec['preservedForegroundPolygons']:
            ImageDraw.Draw(mask).polygon(polygon, fill=255)
        selected = np.asarray(mask) > 0
        self.assertFalse(self.allowed[selected].any())
        self.assertTrue(np.array_equal(a[selected], b[selected]))

    def test_patch_cannot_repaint_face_even_with_a_bad_polygon(self):
        bad = dict(self.spec, armFootprintPolygon=[[450,240],[780,240],[780,475],[450,475]])
        with self.assertRaises(ValueError):
            backing.localized_backing(self.source, backing.load_generated(), bad)

    def test_saved_plate_is_rebuildable_and_not_a_pet_pose_or_arm_rig(self):
        metadata = json.loads((backing.OUT/'build.json').read_text())
        with Image.open(backing.OUT/'backing.png') as image:
            self.assertEqual(image.convert('RGBA').tobytes(), self.plate.tobytes())
        self.assertEqual(metadata['backingRGBAHash'], hashlib.sha256(self.plate.tobytes()).hexdigest().upper())
        self.assertEqual(metadata['boundedChangedPixelsOutsidePatch'], 0)
        self.assertEqual(metadata['camera'], camera(clean_cutout(self.source)[0]))
        self.assertFalse(metadata['articulatedArmBuilt'] or metadata['animationBuilt']
                         or metadata['fullRedrawAccepted'] or metadata['installed'] or metadata['installableFullAtlas'])
        self.assertEqual(metadata['visualAcceptance'], 'pending')
        self.assertIn('not a pet pose', metadata['role'])


class Hop(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source, cls.cleanup, cls.transform, cls.regions, cls.masks, cls.motion, cls.poses = jumping.inputs()
        cls.data,cls.material=jumping.contact_inputs()
        cls.frames = [hop_contact.render(cls.material,pose,cls.transform,cls.regions,cls.masks) for pose in cls.poses]
        cls.old_frames = [render(cls.source,pose,cls.transform,cls.regions,cls.masks) for pose in cls.poses]
        cls.metadata = json.loads((jumping.OUT/'build.json').read_text())

    def test_flight_samples_and_real_holds_define_contact_not_continuous_playback(self):
        self.assertEqual(self.metadata['durationsMs'], DURATIONS[4])
        self.assertEqual(self.metadata['totalDurationMs'], 840)
        self.assertEqual(self.metadata['actionDurationMs'], 2520)
        self.assertEqual(self.metadata['groundedFrames'], [0,4])
        self.assertEqual([p.get('flightTimeMs') for p in self.poses[1:4]], [70,210,350])
        np.testing.assert_allclose(self.metadata['actorOffsetsPx'], [0,-20/9,-4,-20/9,0], atol=1e-12)
        self.assertEqual(self.metadata['heightApprovalScope'],'hop-height-development-basis-only')
        self.assertEqual(self.metadata['heightVisualApproval'],'approved-as-development-basis')
        self.assertFalse(self.metadata['nativeInterpolation'])

    def test_previous_height_field_reference_face_and_shoes_are_rigid_not_current_contact_proof(self):
        scale = self.transform['scale']
        for pose in self.poses:
            x0,y0,x1,y1 = self.regions['protectedFace']
            yy, xx = np.mgrid[y0:y1, x0:x1].astype(float)
            # Inverse sampling starts in actor coordinates, not a refit camera.
            world_y = yy+pose['actorY']/scale
            sx,sy = coordinates(xx, world_y-pose['actorY']/scale, pose, self.transform, self.regions, self.masks)
            np.testing.assert_allclose(sx,xx,atol=1e-12)
            np.testing.assert_allclose(sy-world_y,-(pose['actorY']+pose['bodyY'])/scale,atol=1e-12)
            for x0,y0,x1,y1 in self.regions['shoeProtectedRects']:
                yy,xx = np.mgrid[y0:y1,x0:x1].astype(float)
                sx,sy = coordinates(xx,yy,pose,self.transform,self.regions,self.masks)
                self.assertTrue(np.array_equal(sx,xx) and np.array_equal(sy,yy))

    def test_previous_height_field_crop_and_current_source_camera_have_not_been_refitted(self):
        zero = render(self.source, dict(bodyY=0,earAngle=0,hairAngle=0), self.transform,self.regions,self.masks)
        for index in (0,4):
            for box in [(73,181,93,199),(101,181,120,199)]:
                self.assertEqual(self.old_frames[index].crop(box).tobytes(),zero.crop(box).tobytes())
        self.assertEqual(self.metadata['camera'],camera(self.source))
        self.assertEqual(self.metadata['sourceSha256'],ACCEPTED_SHA)

    def test_frames_strip_alpha_and_metadata_rebuild(self):
        with Image.open(jumping.OUT/'strip.webp') as strip:
            self.assertEqual(strip.size,(1536,208))
            for index,frame in enumerate(self.frames):
                with Image.open(jumping.OUT/f'frame-{index}.png') as saved:
                    self.assertEqual(saved.convert('RGBA').tobytes(),frame.tobytes())
                self.assertEqual(strip.crop((index*192,0,(index+1)*192,208)).convert('RGBA').tobytes(),frame.tobytes())
                self.assertEqual(hashlib.sha256(frame.tobytes()).hexdigest().upper(),self.metadata['frameHashes'][index])
                pixels = np.asarray(frame)
                self.assertFalse(pixels[0,:,3].any() or pixels[-1,:,3].any() or pixels[:,0,3].any() or pixels[:,-1,3].any())
                self.assertFalse(((pixels[...,3]==0) & np.any(pixels[...,:3]!=0,axis=2)).any())
            self.assertIsNone(strip.crop((960,0,1536,208)).getbbox())
        self.assertFalse(self.metadata['facialGeometryRepair'] or self.metadata['installed'] or self.metadata['installableFullAtlas'])
        self.assertEqual(self.metadata['visualMotionApproval'],'pending')

    def test_previous_height_field_reference_keeps_original_jacobian_requirement(self):
        y,x = np.mgrid[10:1260:5,80:1130:5].astype(float)
        for pose in self.poses:
            xp,yp = coordinates(x+.1,y,pose,self.transform,self.regions,self.masks)
            xm,ym = coordinates(x-.1,y,pose,self.transform,self.regions,self.masks)
            ux,uy = coordinates(x,y+.1,pose,self.transform,self.regions,self.masks)
            vx,vy = coordinates(x,y-.1,pose,self.transform,self.regions,self.masks)
            determinant = ((xp-xm)*(uy-vy)-(ux-vx)*(yp-ym))/.04
            self.assertGreater(float(determinant.min()),.95)

    def test_gif_preserves_native_held_schedule(self):
        with Image.open(jumping.OUT/'native-timing.gif') as gif:
            holds = []
            for index in range(gif.n_frames):
                gif.seek(index)
                holds.append(gif.info['duration'])
        self.assertEqual(holds,DURATIONS[4])

    def test_current_face_samples_have_exact_rigid_body_translation(self):
        x0,y0,x1,y1=self.regions['protectedFace']
        yy,xx=np.mgrid[y0:y1:3.7,x0:x1:4.1]
        expected=sample(self.material['source'],xx,yy)
        for pose in self.poses:
            # Actor-local sample; camera separately inverts the actual flight.
            y=yy+pose['bodyY']/self.transform['scale']
            actual=hop_contact.sample_pose(self.material,xx,y,pose,self.transform,self.regions,self.masks)
            np.testing.assert_allclose(actual,expected,rtol=0,atol=1e-10)

    def test_current_neutral_is_exact_without_material_bypass_and_air_cels_are_exact(self):
        zero=dict(grounded=True,actorY=0,bodyY=0,earAngle=0,hairAngle=0)
        actual=hop_contact.render(self.material,zero,self.transform,self.regions,self.masks)
        reference=render(self.source,zero,self.transform,self.regions,self.masks)
        self.assertEqual(actual.tobytes(),reference.tobytes())
        self.assertTrue(self.metadata['originalAirCelsRGBAExact'])
        # Valid material changes must still be observable in a neutral pose.
        changed=dict(self.material,data=dict(self.material['data'],layers=[p.copy() for p in self.material['data']['layers']]))
        paint=changed['data']['layers'][0]
        yy,xx=np.where((paint[...,3]>200)&(paint[...,0]<paint[...,3]-1))
        y,x=int(yy[0]),int(xx[0]);paint[y,x,0]+=1
        x0,y0,_,_=self.data['box']
        point=hop_contact.sample_pose(changed,np.array([x+x0]),np.array([y+y0]),zero,self.transform,self.regions,self.masks)
        self.assertGreater(float(abs(point[0,0]-self.material['source'][y+y0,x+x0,0])),.9)

    def test_air_material_difference_is_zero_after_support_repair_not_full_identity_approval(self):
        changed=[];maximum=[]
        for i in (1,2,3):
            legacy=render(self.source,self.poses[i],self.transform,self.regions,self.masks)
            diff=np.abs(np.asarray(legacy,dtype=int)-np.asarray(self.frames[i],dtype=int))
            changed.append(int(np.any(diff,axis=2).sum()));maximum.append(int(diff.max()))
            self.assertLessEqual(maximum[-1],1)
        self.assertEqual(changed,self.metadata['heightFieldAirChangedPixels'])
        self.assertEqual(maximum,self.metadata['heightFieldAirMaximumChannelDifference'])
        self.assertEqual(changed,[0,0,0])
        self.assertEqual(maximum,[0,0,0])
        self.assertFalse(self.metadata['airMaterialIdentityProven'])
        self.assertEqual(self.metadata['airComparisonScope'],
                         'same-current-poses-height-field-counterfactual-not-frozen-8px')

    def test_current_grounded_joint_targets_bend_without_stretch_or_moving_either_ankle(self):
        scale=self.transform['scale']
        for index in (0,4):
            pose=self.poses[index];root=np.array([0,pose['bodyY']/scale])
            for bone in self.data['spec']['legs']:
                hip,knee,ankle,lengths=inverse_kinematics(bone,0,-root[1])
                original=[np.asarray(bone[name]) for name in ('anchor','knee','ankle')]
                expected=[np.linalg.norm(original[1]-original[0]),np.linalg.norm(original[2]-original[1])]
                np.testing.assert_allclose([np.linalg.norm(knee-hip),np.linalg.norm(ankle-knee)],expected,rtol=0,atol=1e-10)
                np.testing.assert_allclose(ankle+root,bone['ankle'],rtol=0,atol=1e-12)
                self.assertGreater(abs(knee[0]-original[1][0]),5)
                self.assertGreater((knee[0]-original[1][0])*(-bone['bendSign']),0)
        self.assertEqual(self.metadata['jointEvidenceDecimalPlaces'],9)
        self.assertEqual(self.metadata['contactRigJoints'],[hop_contact.joint_evidence(self.data,p,self.transform) for p in self.poses])

    def test_current_grounded_shoe_material_coordinates_and_inner_colors_not_background_rectangles(self):
        yy,xx=np.mgrid[1040:1220:3.7,435:790:4.1]
        x0,y0,_,_=self.data['box'];reference=sample(self.material['source'],xx,yy)
        for index in (0,4):
            pose=self.poses[index];current=hop_contact.key(pose,self.transform['scale'])
            qx,qy=sampling.source_coordinates(xx,yy,current)
            for bone,offset in zip(self.data['spec']['legs'],sampling.relative_offsets(current,1)):
                sx,sy=leg_coordinates(qx,qy,bone,*offset)
                np.testing.assert_allclose(sx,xx,rtol=0,atol=1e-10)
                np.testing.assert_allclose(sy,yy,rtol=0,atol=1e-10)
            weights=[sample(beta,xx-x0,yy-y0) for beta in self.material['data']['occlusions']]
            actual=hop_contact.sample_pose(self.material,xx,yy,pose,self.transform,self.regions,self.masks)
            for weight,other in zip(weights,reversed(weights)):
                inner=(weight==1)&(other==0)
                self.assertGreater(int(inner.sum()),100)
                np.testing.assert_allclose(actual[inner],reference[inner],rtol=0,atol=1e-10)
        # Rabbit shoes' native inner paint: excludes the moving hair fringe
        # present in the old right bounding rectangle, not a whole-edge claim.
        zero=render(self.source,dict(bodyY=0,earAngle=0,hairAngle=0),self.transform,self.regions,self.masks)
        for index in (0,4):
            for box in ((73,181,93,199),(101,181,113,199)):
                self.assertEqual(self.frames[index].crop(box).tobytes(),zero.crop(box).tobytes())

    def test_current_two_link_inverse_projection_is_continuous_nonfolding_and_keeps_previous_floor(self):
        yy,xx=np.mgrid[937:1027:2.5,460:745:5.1]
        for pose in self.poses:
            current=hop_contact.key(pose,self.transform['scale'])
            for bone,offset in zip(self.data['spec']['legs'],sampling.relative_offsets(current,1)):
                xp,yp=leg_coordinates(xx+.01,yy,bone,*offset)
                xm,ym=leg_coordinates(xx-.01,yy,bone,*offset)
                ux,uy=leg_coordinates(xx,yy+.01,bone,*offset)
                vx,vy=leg_coordinates(xx,yy-.01,bone,*offset)
                determinant=((xp-xm)*(uy-vy)-(ux-vx)*(yp-ym))/.0004
                self.assertGreater(float(determinant.min()),.95)
                _,knee,ankle,_=inverse_kinematics(bone,*offset)
                for ring in (bone['anchor'],knee,ankle):
                    sx,sy=leg_coordinates(np.array([ring[0]]),np.array([ring[1]-.000001]),bone,*offset)
                    tx,ty=leg_coordinates(np.array([ring[0]]),np.array([ring[1]+.000001]),bone,*offset)
                    self.assertLess(float(np.hypot(tx-sx,ty-sy)[0]),.00001)

    def test_comparison_is_actual_old_height_field_and_no_approval_is_inherited(self):
        proof=json.loads((jumping.OUT/'contact-proof.json').read_text())
        with Image.open(jumping.OUT/proof['file']) as strip:
            for index,frame in enumerate(self.old_frames):
                self.assertEqual(strip.crop((index*192,0,(index+1)*192,208)).convert('RGBA').tobytes(),frame.tobytes())
        self.assertEqual(proof['airCelsRGBAExact'],[a.tobytes()==self.frames[i].tobytes() for i,a in zip((1,2,3),self.old_frames[1:4])])
        self.assertEqual(proof['airChangedPixels'],self.metadata['heightFieldAirChangedPixels'])
        self.assertEqual(proof['airMaximumChannelDifference'],self.metadata['heightFieldAirMaximumChannelDifference'])
        self.assertEqual(proof['candidateFrameHashes'],self.metadata['frameHashes'])
        for field,value in proof['contract'].items():self.assertEqual(value,self.metadata[field])
        self.assertFalse(proof['visualApprovalInherited'] or proof['installed'] or proof['installableFullAtlas'])
        self.assertFalse(self.metadata['strategyApprovalInheritedFromLocomotion'] or self.metadata['artistLayerRecoveryClaimed']
                         or self.metadata['newArtworkGenerated'] or self.metadata['physicalBalanceProven']
                         or self.metadata['continuousLandingProven'])
        self.assertEqual(self.metadata['strategyUserApproval'],'pending')

    def test_material_reuse_does_not_read_locomotion_direction_approval(self):
        with patch.object(leg,'strategy_decision',side_effect=AssertionError('locomotion approval must not be inherited')):
            data=leg.material_inputs()
        self.assertEqual(data['spec']['sourceSha256'],ACCEPTED_SHA)
        with patch.object(leg,'strategy_decision',side_effect=ValueError('guard retained')):
            with self.assertRaises(ValueError):leg.inputs()

    def test_invalid_contact_pose_cannot_create_a_floating_compression_or_expanded_motion(self):
        valid=self.poses[0]
        for field,value in (('actorY',True),('actorY',1),('actorY',-9),('bodyY',-.1),('bodyY',.9),
                            ('bodyY',float('nan')),('earAngle',.21),('hairAngle',.09),
                            ('grounded',1),('grounded',False)):
            with self.subTest(field=field,value=value):
                with self.assertRaises(ValueError):hop_contact.key(dict(valid,**{field:value}),self.transform['scale'])
        with self.assertRaises(ValueError):hop_contact.key(dict(self.poses[1],bodyY=.1),self.transform['scale'])
        for scale in (True,0,-1,float('inf'),'1'):
            with self.assertRaises(ValueError):hop_contact.key(valid,scale)


if __name__ == '__main__':
    unittest.main()
