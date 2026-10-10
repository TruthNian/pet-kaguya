"""Eight native failed poses from locked v3 + strictly bounded expression."""
import hashlib
import json

from canonical import ROOT, ACCEPTED_SHA, load_canonical, clean_cutout, camera
from build_idle import specification as idle_specification, region_masks, render
from review_failed import specification as expression_specification, load_generated, localized_pose, GENERATED_SHA
from animation_output import write_animation
from protocol import DURATIONS
import review_failed_mouth as mouth

OUT = ROOT/'candidates/phase5/failed'


def specification(*, frozen_motion=False):
    path='sources/reference/failed-body-before/motion.json' if frozen_motion else 'sources/canonical/failed-motion.json'
    motion = json.loads((ROOT/path).read_text(encoding='utf-8'))
    if (motion['durationsMs'] != DURATIONS[5] or len(motion['keyframes']) != 8
            or not motion['faceShapeLocked'] or motion['closedEyeFrames'] != 0
            or motion['visualMotionApproval'] != 'pending'):
        raise ValueError('Failed candidate source/schedule/approval changed')
    if not frozen_motion and (motion.get('bodyStrategy')!='held-canonical-height-developer-improvement'
            or motion.get('bodyMotionUserApproval')!='pending' or any(pose['bodyY']!=0 for pose in motion['keyframes'])):
        raise ValueError('Current failed body must retain the unapproved calm hold boundary')
    return motion


def reference_inputs(*, frozen_motion=False):
    mother = load_canonical()
    source, _ = localized_pose(mother, load_generated(), expression_specification())
    source, cleanup = clean_cutout(source)
    transform = camera(clean_cutout(mother)[0])  # Mother camera, NOT per-state fitting.
    regions, _ = idle_specification()
    return source, cleanup, transform, regions, region_masks(regions), specification(frozen_motion=frozen_motion)


def inputs():
    mouth.decision()
    before, mapped = mouth.inputs()
    source, _, _ = mouth.compose(before, mapped)
    source, cleanup = clean_cutout(source)
    transform = camera(clean_cutout(load_canonical())[0])
    regions, _ = idle_specification()
    return source, cleanup, transform, regions, region_masks(regions), specification()


def main():
    source, cleanup, transform, regions, masks, motion = inputs()
    frames = [render(source, pose, transform, regions, masks) for pose in motion['keyframes']]
    write_animation(OUT, frames, DURATIONS[5])
    metadata = dict(sourceSha256=ACCEPTED_SHA, expressionGeneratedSha256=GENERATED_SHA,
        source='sources/canonical/artwork.png', expressionPatch='candidates/phase5/failed-art-v1/patch.json',
        state='failed', nativeRow=5, statesInThisArtifact=['failed'], generatedFromRejectedSources=False,
        facialGeometryRepair=False, closedEyeFrames=0, durationsMs=DURATIONS[5], totalDurationMs=sum(DURATIONS[5]),
        repeatBeforeIdle=3, actionDurationMs=3*sum(DURATIONS[5]), camera=transform, alphaCleanup=cleanup,
        method='unchanged mouth/brow source; canonical body height held, tiny existing ear/hair response retained',
        sampling='3x coverage integration from high-resolution source, one terminal Lanczos downsample',
        visualMotionApproval='pending', installableFullAtlas=False, installed=False,
        mouthArt='candidates/phase5/failed-mouth-v2',mouthGeneratedSha256=mouth.GENERATED_SHA,
        mouthPoseRGBAHash=mouth.rgba_hash(mouth.compose(*mouth.inputs())[0]),
        mouthLineVisualApproval='approved-as-development-basis',
        mouthApprovalScope='mouth-line-development-basis-only',mouthUserDecision=mouth.DECISION,
        sourceAlphaPreservedExactly=True,nativeAlphaPreservedExactly=False,bodyEarHairPosesUnchanged=False,
        earHairPosesAndTimingUnchanged=True,newArtworkGeneratedThisIteration=False,
        failedBodyDevelopmentBasis='developer-selected-calm-body-hold',bodyMotionUserApproval='pending',
        bodyHeldAtCanonicalHeight=True,bodyMotionUserApprovalClaimed=False,
        failedBodyReference='sources/reference/failed-body-before',
        loopSeamRGBAExact=frames[0].tobytes()==frames[-1].tobytes(),
        keyframes=motion['keyframes'],
        frameHashes=[hashlib.sha256(frame.tobytes()).hexdigest().upper() for frame in frames],
        unresolved=['Mouth line accepted as development basis only; brows and complete motion remain unapproved.',
                    'The accepted line is 46 source pixels by the diagnostic, below mother smile 54; 80px cues remain weak.',
                    'Body oscillation removed, but fixed native holds, expression cuts and arbitrary exits remain; developer choice is not user motion approval.',
                    'Native-host loading/performance and final release/install acceptance remain unverified.'])
    (OUT/'build.json').write_text(json.dumps(metadata, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({key:value for key,value in metadata.items() if key!='frameHashes'}, indent=2))


if __name__ == '__main__':
    main()
