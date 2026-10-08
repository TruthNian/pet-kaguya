"""Six native processing holds, awake gaze, no rapid body/ornament pulse."""
import hashlib
import json
import math

import numpy as np

from canonical import ROOT, ACCEPTED_SHA, clean_cutout, camera
from arm_material import localized_arm_pose
from review_processing import inputs as art_inputs, GENERATED_SHA
from build_idle import specification as idle_specification, region_masks, render
import build_gaze as gaze
from animation_output import write_animation
from protocol import DURATIONS

OUT = ROOT/'candidates/phase5/processing'


def validate_motion(motion, gaze_spec):
    if (motion['sourceSha256'] != ACCEPTED_SHA or motion['nativeState'] != 'running'
            or motion['state'] != 'processing' or motion['nativeRow'] != 7
            or motion['durationsMs'] != DURATIONS[7] or motion['repeatBeforeIdle'] != 3
            or not motion['faceShapeLocked'] or motion['closedEyeFrames'] != 0
            or motion['bodyPulse'] or motion['ornamentFlash'] or motion['nativeInterpolation']
            or motion['visualMotionApproval'] != 'pending'):
        raise ValueError('Processing violates locked source/native timing/candidate boundary')
    offset = motion['focusOffsetSourcePx']
    if (len(offset) != 2 or any(isinstance(v, bool) or not math.isfinite(v)
            or abs(v) > limit for v, limit in zip(offset, gaze_spec['maximumDisplacementSourcePx']))):
        raise ValueError('Processing gaze exceeds the inspected iris range')
    keyframes = motion['keyframes']
    if len(keyframes) != 6 or keyframes[0] != keyframes[-1]:
        raise ValueError('Processing needs six native holds and an exact looping seam')
    for frame in keyframes:
        if (set(frame) != {'bodyY', 'earAngle', 'hairAngle'} or frame['bodyY'] != 0
                or any(isinstance(v, bool) or not math.isfinite(v) for v in frame.values())
                or abs(frame['earAngle']) > .20 or abs(frame['hairAngle']) > .02):
            raise ValueError('Processing cannot add body pulse, actor motion or excessive ear/hair fields')


def inputs():
    mother, art_spec, generated = art_inputs()
    arm_pose, arm_allowed = localized_arm_pose(mother, generated, art_spec)
    gaze_spec = gaze.specification()
    motion = json.loads((ROOT/'sources/canonical/processing-motion.json').read_text(encoding='utf-8'))
    validate_motion(motion, gaze_spec)
    eye_layers = gaze.layers(mother, gaze.load_generated(), gaze_spec)
    focused = gaze.pose(arm_pose, eye_layers, *motion['focusOffsetSourcePx'])
    eye_allowed = gaze.aperture_union(mother, eye_layers)
    changed = np.any(np.asarray(focused) != np.asarray(arm_pose), axis=2)
    if (np.any(changed & ~eye_allowed)
            or not np.array_equal(np.asarray(focused)[...,3], np.asarray(arm_pose)[...,3])):
        raise ValueError('Processing gaze changed the face outline, alpha or a non-eye pixel')
    transform = camera(clean_cutout(mother)[0])  # Never fit to the changed arm bounds.
    regions, _ = idle_specification()
    masks = region_masks(regions)
    source = clean_cutout(focused)[0]
    rendered = {}
    frames = []
    for pose in motion['keyframes']:
        key = tuple(pose[name] for name in ('bodyY', 'earAngle', 'hairAngle'))
        if key not in rendered:
            rendered[key] = render(source, pose, transform, regions, masks)
        frames.append(rendered[key])
    return dict(mother=mother, armPose=arm_pose, armAllowed=arm_allowed,
                focused=focused, eyeAllowed=eye_allowed, motion=motion,
                transform=transform, regions=regions, masks=masks, frames=frames)


def main():
    data = inputs()
    frames, motion = data['frames'], data['motion']
    for frame in frames:
        pixels = np.asarray(frame)
        if pixels[0,:,3].any() or pixels[-1,:,3].any() or pixels[:,0,3].any() or pixels[:,-1,3].any():
            raise ValueError('Processing touches a cell edge')
    write_animation(OUT, frames, DURATIONS[7])
    data['focused'].save(OUT/'focused-pose.png')
    metadata = dict(sourceSha256=ACCEPTED_SHA, source='sources/canonical/artwork.png',
        handGeneratedSha256=GENERATED_SHA, eyeBackingGeneratedSha256=gaze.GENERATED_SHA,
        state='processing', nativeState='running', nativeRow=7, statesInThisArtifact=['processing'],
        durationsMs=DURATIONS[7], totalDurationMs=sum(DURATIONS[7]), repeatBeforeIdle=3,
        actionDurationMs=3*sum(DURATIONS[7]), closedEyeFrames=0, bodyPulse=False, ornamentFlash=False,
        bodyTranslationPx=0, focusOffsetSourcePx=motion['focusOffsetSourcePx'],
        camera=data['transform'], sameSourceCoordinateCamera=True,
        focusedEyeAlphaPreservedExactly=True, sourceFaceExceptEyeAperturesFixed=True,
        sourceCapeAndForegroundLockPreserved=True, loopSeamRGBAExact=frames[0].tobytes()==frames[-1].tobytes(),
        uniqueCels=len(set(frame.tobytes() for frame in frames)),
        frameHashes=[hashlib.sha256(frame.tobytes()).hexdigest().upper() for frame in frames],
        method='bounded gathered-hand cel, original iris translation and very small ear/hair fields; body held',
        sampling='new arm first uses fixed-crop uniform source projection; shared canonical camera, 3x coverage and terminal Lanczos downsample',
        fullRedrawAccepted=False, articulatedArmBuilt=False, facialGeometryRepair=False,
        generatedFromRejectedSources=False, nativeInterpolation=False,
        visualMotionApproval='pending', installableFullAtlas=False, installed=False,
        unresolved=motion['limitations'])
    (OUT/'build.json').write_text(json.dumps(metadata, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(metadata, indent=2))


if __name__ == '__main__':
    main()
