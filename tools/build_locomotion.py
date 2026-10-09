"""Two frontal drag-feedback candidates, fixed source camera and source shoes."""
import hashlib
import json
import math

import numpy as np

from canonical import ROOT, ACCEPTED_SHA,clean_cutout,camera
from leg_material import inverse_kinematics,GENERATED_SHA
from refine_leg_composition import inputs as material_inputs,composite,strategy_decision,DECISION
from build_idle import specification as idle_specification,region_masks,render
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
            or not motion['faceShapeLocked'] or motion['artMirrored'] or motion['bodyTranslationPx'] != 0
            or motion['closedEyeFrames'] != 0 or motion['nativeInterpolation']
            or motion['hostVelocitySynchronization'] or motion['focusOffsetSourcePx'] != [6,0]):
        raise ValueError('Locomotion violates locked front view, native timing or candidate boundary')
    poses = motion['keyframes']
    if len(poses) != 8 or poses[0] != poses[-1]:
        raise ValueError('Locomotion requires eight real holds and an exact looping seam')
    for index,pose in enumerate(poses):
        if set(pose) != {'left','right','support'} or not pose['support']:
            raise ValueError('Locomotion must explicitly retain a support foot')
        expected_support = ['right'] if index in (1,2) else ['left'] if index in (5,6) else ['left','right']
        if pose['support'] != expected_support:
            raise ValueError('Locomotion support sequence changed')
        for name in ('left','right'):
            offset = pose[name]
            if (len(offset) != 2 or any(isinstance(v,bool) or not math.isfinite(v) for v in offset)
                    or not 0 <= offset[0] <= 5 or not -7.5 <= offset[1] <= 0
                    or (name in pose['support'] and offset != [0,0])
                    or (name not in pose['support'] and not offset[1] < 0)):
                raise ValueError('Locomotion may not slide a support foot, stretch range or add flight')


def inputs():
    data = material_inputs()
    motion = json.loads((ROOT/'sources/canonical/locomotion-motion.json').read_text(encoding='utf-8'))
    validate_motion(motion)
    source = data['mother']
    eye_layers = gaze.layers(source,gaze.load_generated(),gaze.specification())
    regions,_ = idle_specification();masks = region_masks(regions)
    transform = camera(clean_cutout(source)[0])
    results = {}
    zero = dict(bodyY=0,earAngle=0,hairAngle=0)
    for state in motion['states']:
        direction = state['direction']
        rendered,poses,frames,joints = {},[],[],[]
        for key in motion['keyframes']:
            offsets = [(key[name][0]*direction,key[name][1]) for name in ('left','right')]
            signature = tuple(offsets)
            if signature not in rendered:
                puppet = composite(data,offsets)
                pose = gaze.pose(puppet,eye_layers,motion['focusOffsetSourcePx'][0]*direction,0)
                frame = render(clean_cutout(pose)[0],zero,transform,regions,masks)
                rendered[signature] = (pose,frame)
            pose,frame = rendered[signature]
            poses.append(pose);frames.append(frame)
            joints.append([inverse_kinematics(leg,*offset)[1].tolist()
                           for leg,offset in zip(data['spec']['legs'],offsets)])
        results[state['state']] = dict(state=state,poses=poses,frames=frames,targetKnees=joints)
    data.update(motion=motion,transform=transform,regions=regions,motionMasks=masks,
                eyeAllowed=gaze.aperture_union(source,eye_layers),results=results)
    return data


def main():
    data = inputs()
    motion = data['motion']
    original = np.asarray(data['mother'])
    allowed = data['eyeAllowed'].copy()
    x0,y0,x1,y1 = data['box'];allowed[y0:y1,x0:x1] = True
    for name,result in data['results'].items():
        out = ROOT/'candidates/phase5'/name
        frames = result['frames']
        for pose,frame in zip(result['poses'],frames):
            if np.any(np.any(np.asarray(pose) != original,axis=2)&~allowed):
                raise ValueError('Locomotion touched face/body outside eye/lower-leg permission')
            rgba = np.asarray(frame)
            if rgba[0,:,3].any() or rgba[-1,:,3].any() or rgba[:,0,3].any() or rgba[:,-1,3].any():
                raise ValueError('Locomotion touches a cell edge')
        write_animation(out,frames,DURATIONS[result['state']['nativeRow']])
        result['poses'][2].save(out/'left-lifted-pose.png')
        result['poses'][6].save(out/'right-lifted-pose.png')
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
            wholeCuffAndShoeRigidlyTranslated=True,bodyTranslationPx=0,bodyPulse=False,ornamentFlash=False,
            focusOffsetSourcePx=[6*result['state']['direction'],0],artMirrored=False,
            camera=data['transform'],sameSourceCoordinateCamera=True,facialGeometryRepair=False,
            sourceFaceExceptEyeAperturesFixed=True,closedEyeFrames=0,nativeInterpolation=False,
            loopSeamRGBAExact=frames[0].tobytes()==frames[-1].tobytes(),
            uniqueCels=len(set(frame.tobytes() for frame in frames)),
            frameHashes=[hashlib.sha256(frame.tobytes()).hexdigest().upper() for frame in frames],
            method='conditioned source leg RGBA and separate moving occlusion; 2-D joint hypothesis with C1 ring displacement; fixed face and original iris shift',
            legCompositionVersion='leg-material-v2',neutralLegCompositorRGBAExact=True,
            neutralLegCompositorNativeRGBAExact=True,sourceAlphaAndOcclusionSeparated=True,
            artistLayerRecoveryClaimed=False,inferredMatte=True,fullRedrawAccepted=False,
            generatedFromRejectedSources=False,installableFullAtlas=False,installed=False,
            unresolved=motion['limitations'])
        (out/'build.json').write_text(json.dumps(metadata,indent=2)+'\n',encoding='utf-8')
        print(json.dumps(dict(state=name,uniqueCels=metadata['uniqueCels'],
                             maximumFootLiftOutputPx=metadata['maximumFootLiftOutputPx'],
                             visualMotionApproval='pending',installed=False)))


if __name__ == '__main__':
    main()
