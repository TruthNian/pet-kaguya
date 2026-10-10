"""Eight native failed poses from locked v3 + strictly bounded expression."""
import hashlib
import json

from canonical import ROOT, ACCEPTED_SHA, load_canonical, clean_cutout, camera
from build_idle import specification as idle_specification, region_masks, render
from review_failed import specification as expression_specification, load_generated, localized_pose, GENERATED_SHA
from animation_output import write_animation
from protocol import DURATIONS

OUT = ROOT/'candidates/phase5/failed'


def specification():
    motion = json.loads((ROOT/'sources/canonical/failed-motion.json').read_text(encoding='utf-8'))
    if (motion['durationsMs'] != DURATIONS[5] or len(motion['keyframes']) != 8
            or not motion['faceShapeLocked'] or motion['closedEyeFrames'] != 0
            or motion['visualMotionApproval'] != 'pending'):
        raise ValueError('Failed candidate source/schedule/approval changed')
    return motion


def inputs():
    mother = load_canonical()
    source, _ = localized_pose(mother, load_generated(), expression_specification())
    source, cleanup = clean_cutout(source)
    transform = camera(clean_cutout(mother)[0])  # Mother camera, NOT per-state fitting.
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
        method='bounded mouth/brow art; authored native poses with rigid face/upper-body settling and pinned shoes',
        sampling='3x coverage integration from high-resolution source, one terminal Lanczos downsample',
        visualMotionApproval='pending', installableFullAtlas=False, installed=False,
        keyframes=motion['keyframes'],
        frameHashes=[hashlib.sha256(frame.tobytes()).hexdigest().upper() for frame in frames],
        unresolved=['Current mouth/brow artwork and complete motion lack human visual approval.',
                    'The current mouth line is shorter than the mother smile; 80px expression cues remain weak.',
                    'Short repeating native holds and upper-body settling do not prove articulated leaning or smooth arbitrary exits.',
                    'Native-host loading/performance and final release/install acceptance remain unverified.'])
    (OUT/'build.json').write_text(json.dumps(metadata, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({key:value for key,value in metadata.items() if key!='frameHashes'}, indent=2))


if __name__ == '__main__':
    main()
