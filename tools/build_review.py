"""Native review holds: bounded low hands and downward original iris motion."""
import hashlib
import json
import math

import numpy as np

from canonical import ROOT, ACCEPTED_SHA, load_canonical, clean_cutout, camera
from review_review_v6 import inputs as art_inputs, localized_pose, GENERATED_SHA
from review_cloth_v2 import GENERATED_SHA as CLOTH_SHA
from review_processing import GENERATED_SHA as LEFT_SHA
from build_idle import specification as idle_specification, region_masks, render
import build_gaze as gaze
import eye_motion
from animation_output import write_animation
from protocol import DURATIONS
from held_timing import validate_decision

OUT = ROOT/'candidates/phase5/review'


def validate_motion(motion, gaze_spec):
    validate_decision(motion)
    if (motion['sourceSha256'] != ACCEPTED_SHA or motion['state'] != 'review'
            or motion['nativeRow'] != 8 or motion['durationsMs'] != DURATIONS[8]
            or motion['repeatBeforeIdle'] != 3 or not motion['faceShapeLocked']
            or motion['closedEyeFrames'] != 0 or motion['bodyPulse'] or motion['ornamentFlash']
            or motion['handStrategy'] != 'two-low-hands-held' or motion['nativeInterpolation']
            or motion['strategyUserApproval'] != 'pending' or motion['visualMotionApproval'] != 'pending'):
        raise ValueError('Review violates source/native timing/unapproved candidate boundary')
    offset = motion['focusOffsetSourcePx']
    if (len(offset) != 2 or any(isinstance(v, bool) or not math.isfinite(v)
            or abs(v) > limit for v, limit in zip(offset, gaze_spec['maximumDisplacementSourcePx']))
            or offset[0] != 0 or offset[1] <= 0):
        raise ValueError('Review needs bounded downward original-iris displacement')
    frames = motion['keyframes']
    if len(frames) != 6 or frames[0] != frames[-1]:
        raise ValueError('Review needs six native holds and an exact looping seam')
    for pose in frames:
        if (set(pose) != {'bodyY', 'earAngle', 'hairAngle'} or pose['bodyY'] != 0
                or any(isinstance(v, bool) or not math.isfinite(v) for v in pose.values())
                or abs(pose['earAngle']) > .15 or abs(pose['hairAngle']) > .02):
            raise ValueError('Review cannot add body pulse or excessive ear/hair fields')


def inputs(*, corrected_gaze=True):
    mother = load_canonical()
    base, spec, raw = art_inputs()
    arm_pose, arm_allowed, preserved = localized_pose(base, raw, spec)
    gaze_spec = gaze.specification(corrected=corrected_gaze)
    motion = json.loads((ROOT/'sources/canonical/review-motion.json').read_text(encoding='utf-8'))
    validate_motion(motion, gaze_spec)
    eye_layers = eye_motion.layers(mother,corrected=corrected_gaze)
    focused = eye_motion.pose(arm_pose,eye_layers,*motion['focusOffsetSourcePx'],corrected=corrected_gaze)
    eye_allowed = gaze.aperture_union(mother, eye_layers)
    changed = np.any(np.asarray(focused) != np.asarray(arm_pose), axis=2)
    if (np.any(changed & ~eye_allowed)
            or not np.array_equal(np.asarray(focused)[...,3], np.asarray(arm_pose)[...,3])):
        raise ValueError('Review changed the face shape, alpha or a non-eye pixel')
    transform = camera(clean_cutout(mother)[0])
    regions, _ = idle_specification()
    masks = region_masks(regions)
    source = clean_cutout(focused)[0]
    rendered, frames = {}, []
    for pose in motion['keyframes']:
        key = tuple(pose[name] for name in ('bodyY', 'earAngle', 'hairAngle'))
        if key not in rendered:
            rendered[key] = render(source, pose, transform, regions, masks)
        frames.append(rendered[key])
    return dict(mother=mother, base=base, armPose=arm_pose, armAllowed=arm_allowed,
                preserved=preserved, focused=focused, eyeAllowed=eye_allowed, motion=motion,
                transform=transform, regions=regions, masks=masks, frames=frames,
                eyeOffsets=eye_motion.offsets(*motion['focusOffsetSourcePx'],corrected=corrected_gaze))


def main():
    data = inputs()
    frames, motion = data['frames'], data['motion']
    for frame in frames:
        pixels = np.asarray(frame)
        if pixels[0,:,3].any() or pixels[-1,:,3].any() or pixels[:,0,3].any() or pixels[:,-1,3].any():
            raise ValueError('Review touches a cell edge')
    write_animation(OUT, frames, DURATIONS[8])
    data['focused'].save(OUT/'focused-pose.png')
    metadata = dict(sourceSha256=ACCEPTED_SHA, source='sources/canonical/artwork.png',
        rightHandGeneratedSha256=GENERATED_SHA, leftHandGeneratedSha256=LEFT_SHA,
        rightArmCompositionVersion='review-art-v6', newArtworkGenerated=True,
        clothCompositionVersion='review-sleeves-v2',clothGeneratedSha256=CLOTH_SHA,
        heldHandsUnchangedFromV5=True,clothAlphaPreservedExactly=True,
        observedHairAlphaHolesRestored=True,
        originalLowerHandContourRestored=True,handScaled=False,
        knownSourceHairRGBAExact=True,paintedHairAlphaContinuityEstimated=True,
        **eye_motion.descriptor(), state='review', nativeRow=8,
        statesInThisArtifact=['review'], durationsMs=DURATIONS[8], totalDurationMs=sum(DURATIONS[8]),
        repeatBeforeIdle=3, actionDurationMs=3*sum(DURATIONS[8]), closedEyeFrames=0,
        bodyPulse=False, ornamentFlash=False, bodyTranslationPx=0,
        handStrategy=motion['handStrategy'], strategyUserApproval='pending',
        heldTimingUserDecision=motion['heldTimingUserDecision'], heldTimingAcceptedTemporarily=True,
        focusOffsetSourcePx=data['eyeOffsets'],legacyFocusIntentSourcePx=motion['focusOffsetSourcePx'], camera=data['transform'],
        sameSourceCoordinateCamera=True, focusedEyeAlphaPreservedExactly=True,
        sourceFaceExceptEyeAperturesFixed=True, sourceForegroundPlatesPreserved=True,
        loopSeamRGBAExact=frames[0].tobytes()==frames[-1].tobytes(),
        uniqueCels=len(set(frame.tobytes() for frame in frames)),
        frameHashes=[hashlib.sha256(frame.tobytes()).hexdigest().upper() for frame in frames],
        method='bounded two-low-hands cel, quieter original-eye texture flow and very small ear/hair fields; body held',
        sampling='new right/left arm each first uses fixed-crop source projection; shared canonical camera, 3x coverage and terminal Lanczos downsample',
        fullRedrawAccepted=False, articulatedArmBuilt=False, facialGeometryRepair=False,
        animationBuilt=True, generatedFromRejectedSources=False, nativeInterpolation=False,
        visualMotionApproval='pending', installableFullAtlas=False, installed=False,
        unresolved=motion['limitations'])
    (OUT/'build.json').write_text(json.dumps(metadata, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(metadata, indent=2))


if __name__ == '__main__':
    main()
