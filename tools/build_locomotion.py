"""Two frontal drag-feedback candidates, fixed source camera and source shoes."""
import hashlib
import json
import math

import numpy as np

from canonical import ROOT, ACCEPTED_SHA,clean_cutout,camera
from leg_material import inverse_kinematics,GENERATED_SHA
from refine_leg_composition import inputs as material_inputs,strategy_decision,DECISION
import locomotion_render as renderer
import build_gaze as gaze
from animation_output import write_animation
from protocol import DURATIONS


def validate_motion(motion):
    strategy_decision()
    if (motion['sourceSha256'] != ACCEPTED_SHA
            or motion['states'] != [dict(state='run_right',nativeState='running-right',nativeRow=1,direction=1),
                                    dict(state='run_left',nativeState='running-left',nativeRow=2,direction=-1)]
            or motion['durationsMs'] != DURATIONS[1] or DURATIONS[1] != DURATIONS[2]
            or motion['repeatBeforeIdleIfStateRemainsSelected'] != 3
            or motion['projection'] != 'front-held-alternating-small-steps'
            or motion['strategyUserApproval'] != 'approved' or motion['visualMotionApproval'] != 'pending'
            or motion['strategyUserDecision']!=DECISION or motion['strategyApprovalScope']!='front-held-small-steps-only'
            or not motion['faceShapeLocked'] or motion['artMirrored']
            or motion['rootMotion']!='rigid-actor-translation-in-source-coordinates'
            or motion['maximumRootTranslationSourcePx']!=[12,1.5]
            or motion['secondaryMotion']!='rigid-follow-only; delayed ear/hair response remains missing'
            or motion['closedEyeFrames'] != 0 or motion['nativeInterpolation']
            or motion['hostVelocitySynchronization'] or motion['focusOffsetSourcePx'] != [6,0]):
        raise ValueError('Locomotion violates locked front view, native timing or candidate boundary')
    poses = motion['keyframes']
    if (len(poses) != 8 or poses[0] != poses[-1]
            or poses[0]!=dict(left=[0,0],right=[0,0],rootSourcePx=[0,0],support=['left','right'])):
        raise ValueError('Locomotion requires eight real holds and an exact looping seam')
    for index,pose in enumerate(poses):
        if set(pose) != {'left','right','rootSourcePx','support'} or not pose['support']:
            raise ValueError('Locomotion must explicitly retain a support foot')
        expected_support = ['right'] if index in (1,2) else ['left'] if index in (5,6) else ['left','right']
        if pose['support'] != expected_support:
            raise ValueError('Locomotion support sequence changed')
        root=pose['rootSourcePx']
        if (len(root)!=2 or any(isinstance(v,bool) or not math.isfinite(v) for v in root)
                or abs(root[0])>12 or not 0<=root[1]<=1.5
                or (expected_support==['right'] and not root[0]>0)
                or (expected_support==['left'] and not root[0]<0)):
            raise ValueError('Root motion must be bounded and move toward the supporting side')
        for name in ('left','right'):
            offset = pose[name]
            if (len(offset) != 2 or any(isinstance(v,bool) or not math.isfinite(v) for v in offset)
                    or not 0 <= offset[0] <= 5 or not -7.5 <= offset[1] <= 0
                    or (name in pose['support'] and offset != [0,0])
                    or (name not in pose['support'] and not offset[1] < 0)):
                raise ValueError('Locomotion may not slide a support foot, stretch range or add flight')
    # Test relative leg targets after cancelling the actor root, not merely
    # world foot offsets: a planted leg can otherwise overextend.
    legs=json.loads((ROOT/'sources/canonical/leg-material.json').read_text(encoding='utf-8'))['legs']
    for pose in poses:
        for direction in (-1,1):
            for leg,offset in zip(legs,renderer.relative_offsets(pose,direction)):
                inverse_kinematics(leg,*offset)


def inputs():
    data = material_inputs()
    motion = json.loads((ROOT/'sources/canonical/locomotion-motion.json').read_text(encoding='utf-8'))
    validate_motion(motion)
    source = data['mother']
    eye_layers = gaze.layers(source,gaze.load_generated(),gaze.specification())
    transform = camera(clean_cutout(source)[0])
    results = {}
    for state in motion['states']:
        direction = state['direction']
        original_gaze=gaze.pose(source,eye_layers,motion['focusOffsetSourcePx'][0]*direction,0)
        material=renderer.prepare(data,original_gaze)
        rendered,frames,joints = {},[],[]
        for key in motion['keyframes']:
            offsets = renderer.relative_offsets(key,direction)
            signature = tuple(key['rootSourcePx']),tuple(offsets)
            if signature not in rendered:
                rendered[signature] = renderer.render(material,key,direction,transform)
            frames.append(rendered[signature])
            joints.append([np.round(inverse_kinematics(leg,*offset)[1]+key['rootSourcePx'],12).tolist()
                           for leg,offset in zip(data['spec']['legs'],offsets)])
        results[state['state']] = dict(state=state,frames=frames,targetKnees=joints,
                                      sourceWithGaze=original_gaze,material=material)
    data.update(motion=motion,transform=transform,
                eyeAllowed=gaze.aperture_union(source,eye_layers),results=results)
    return data


def main():
    data = inputs()
    motion = data['motion']
    original = np.asarray(data['mother'])
    for name,result in data['results'].items():
        out = ROOT/'candidates/phase5'/name
        frames = result['frames']
        if not np.array_equal(np.asarray(result['sourceWithGaze'])[~data['eyeAllowed']],original[~data['eyeAllowed']]):
            raise ValueError('The source artwork may change only inside original eye apertures')
        for frame in frames:
            rgba = np.asarray(frame)
            if rgba[0,:,3].any() or rgba[-1,:,3].any() or rgba[:,0,3].any() or rgba[:,-1,3].any():
                raise ValueError('Locomotion touches a cell edge')
        write_animation(out,frames,DURATIONS[result['state']['nativeRow']])
        for index,pose_name in ((2,'left-lifted-pose.png'),(6,'right-lifted-pose.png')):
            renderer.diagnostic_pose(result['material'],motion['keyframes'][index],result['state']['direction']).save(out/pose_name)
        neutral=renderer.neutral_evidence(result['material'],result['sourceWithGaze'],data['transform'])
        if not neutral['directSamplerNeutralPremultMatchesWithinTolerance'] or not neutral['directSamplerNeutralRGBAExact']:
            raise ValueError('Direct source filtering must retain the neutral reference')
        metadata = dict(sourceSha256=ACCEPTED_SHA,source='sources/canonical/artwork.png',
            legBackingGeneratedSha256=GENERATED_SHA,eyeBackingGeneratedSha256=gaze.GENERATED_SHA,
            **{key:result['state'][key] for key in ('state','nativeState','nativeRow')},
            animationBuilt=True,projection=motion['projection'],strategyUserApproval='approved',visualMotionApproval='pending',
            strategyApprovalScope=motion['strategyApprovalScope'],strategyUserDecision=DECISION,
            durationsMs=motion['durationsMs'],totalDurationMs=sum(motion['durationsMs']),
            repeatBeforeIdle=3,uninterruptedRowDurationMs=3*sum(motion['durationsMs']),
            actualDragReleaseCanInterruptAnyCel=True,dragEndTargetIsUnderlyingStateNotNecessarilyIdle=True,
            hostVelocitySynchronization=False,screenWorldNoSlipProven=False,
            supportFeet=[pose['support'] for pose in motion['keyframes']],
            footOffsetsSourcePx=[{leg:[pose[leg][0]*result['state']['direction'],pose[leg][1]]
                                 for leg in ('left','right')} for pose in motion['keyframes']],
            targetKneesSourcePx=result['targetKnees'],maximumFootLiftOutputPx=7.5*data['transform']['scale'],
            wholeCuffAndShoeRigidlyTranslated=True,rootMotion=motion['rootMotion'],
            rootOffsetsSourcePx=[pose['rootSourcePx'] for pose in motion['keyframes']],
            maximumRootTranslationOutputPx=[v*data['transform']['scale'] for v in motion['maximumRootTranslationSourcePx']],
            rootShiftFollowsSupportNotTravelDirection=True,bodyPulse=False,ornamentFlash=False,
            focusOffsetSourcePx=[6*result['state']['direction'],0],artMirrored=False,
            camera=data['transform'],sameSourceCoordinateCamera=True,facialGeometryRepair=False,
            sourceFaceExceptEyeAperturesFixed=True,faceGeometryRigidRootTranslation=True,
            sourceArtworkChangedOutsideEyeApertures=False,closedEyeFrames=0,nativeInterpolation=False,
            loopSeamRGBAExact=frames[0].tobytes()==frames[-1].tobytes(),
            uniqueCels=len(set(frame.tobytes() for frame in frames)),
            frameHashes=[hashlib.sha256(frame.tobytes()).hexdigest().upper() for frame in frames],
            method='direct source-material sampling; rigid root towards support and cancelling planted-shoe displacement; coverage-normalized known backing',
            legSampling='original leg paint and occlusion sampled directly on 3x native integration grid; one terminal Lanczos downsample; no posed leg raster input',
            rootAndLegGeometryCombinedBeforeSampling=True,gazeRemainsSourceSpacePrecomposition=True,
            wholeArtworkSingleSamplingPass=False,
            normalizedKnownBacking=True,diagnosticPosesAreNotFrameInputs=True,
            measuredMassCentre=False,physicalBalanceProven=False,secondaryMotion=motion['secondaryMotion'],
            legCompositionVersion='leg-material-v2',integerSourceMaterialNeutralRGBAExact=True,
            **neutral,roundoffCanonicalizationPremultTolerance=1e-10,
            sourceAlphaAndOcclusionSeparated=True,
            artistLayerRecoveryClaimed=False,inferredMatte=True,fullRedrawAccepted=False,
            generatedFromRejectedSources=False,installableFullAtlas=False,installed=False,
            unresolved=motion['limitations'])
        (out/'build.json').write_text(json.dumps(metadata,indent=2)+'\n',encoding='utf-8')
        print(json.dumps(dict(state=name,uniqueCels=metadata['uniqueCels'],
                             maximumFootLiftOutputPx=metadata['maximumFootLiftOutputPx'],
                             visualMotionApproval='pending',installed=False)))


if __name__ == '__main__':
    main()
