"""Five real hop holds: grounded anticipation, three flight poses, landing."""
import hashlib
import json

import numpy as np

from canonical import ROOT, ACCEPTED_SHA, load_canonical, clean_cutout, camera
from build_idle import specification as idle_specification, region_masks, render
from animation_output import write_animation
from protocol import DURATIONS

OUT = ROOT/'candidates/phase5/jumping'


def specification():
    motion = json.loads((ROOT/'sources/canonical/jumping-motion.json').read_text(encoding='utf-8'))
    if (motion['sourceSha256'] != ACCEPTED_SHA or motion['durationsMs'] != DURATIONS[4]
            or len(motion['keyframes']) != 5 or not motion['faceShapeLocked']
            or motion['closedEyeFrames'] != 0 or motion['visualMotionApproval'] != 'pending'):
        raise ValueError('Hop violates locked source/native holds/candidate boundary')
    model = motion['flightModel']
    if (model['airtimeMs'] != sum(DURATIONS[4][1:4]) or model['nativeInterpolation']
            or not 0 < model['apexOutputPx'] <= 8):
        raise ValueError('Hop flight model exceeds the authored camera reserve')
    poses = []
    for index, key in enumerate(motion['keyframes']):
        pose = dict(key)
        if pose['grounded'] != (index in (0, 4)):
            raise ValueError('Hop contact phases changed')
        if pose['grounded']:
            if pose['actorY'] != 0 or not 0 <= pose['bodyY'] <= .8:
                raise ValueError('Grounded hop must pin shoes with only a small leg accommodation')
        else:
            expected = sum(DURATIONS[4][1:index])+DURATIONS[4][index]/2
            if pose['flightTimeMs'] != expected or pose['bodyY'] != 0:
                raise ValueError('Flight must rigidly translate the body at the actual hold midpoint')
            u = expected/model['airtimeMs']
            pose['actorY'] = -4*model['apexOutputPx']*u*(1-u)
        poses.append(pose)
    return motion, poses


def inputs():
    image, cleanup = clean_cutout(load_canonical())
    transform = camera(image)
    regions, _ = idle_specification()
    motion, poses = specification()
    return image, cleanup, transform, regions, region_masks(regions), motion, poses


def main():
    source, cleanup, transform, regions, masks, motion, poses = inputs()
    frames = [render(source, pose, transform, regions, masks) for pose in poses]
    bounds = []
    for frame in frames:
        rgba = np.asarray(frame)
        if rgba[0,:,3].any() or rgba[-1,:,3].any() or rgba[:,0,3].any() or rgba[:,-1,3].any():
            raise ValueError('Hop touches a cell border')
        yy, xx = np.where(rgba[...,3] > 8)
        bounds.append([int(xx.min()), int(yy.min()), int(xx.max()+1), int(yy.max()+1)])
    write_animation(OUT, frames, DURATIONS[4])
    metadata = dict(sourceSha256=ACCEPTED_SHA, source='sources/canonical/artwork.png',
        state='jumping', nativeRow=4, statesInThisArtifact=['jumping'],
        generatedFromRejectedSources=False, facialGeometryRepair=False, closedEyeFrames=0,
        durationsMs=DURATIONS[4], totalDurationMs=sum(DURATIONS[4]),
        repeatBeforeIdle=3, actionDurationMs=3*sum(DURATIONS[4]), camera=transform,
        alphaCleanup=cleanup, actorOffsetsPx=[pose['actorY'] for pose in poses],
        groundedFrames=[index for index, pose in enumerate(poses) if pose['grounded']],
        visibleBoundsAlphaAbove8=bounds, nativeInterpolation=False,
        method='pinned grounded shoes; rigid actor flight from a parabolic model sampled at real hold midpoints; no head/body resizing',
        sampling='3x coverage integration from high-resolution source, one terminal Lanczos downsample',
        visualMotionApproval='pending', installableFullAtlas=False, installed=False,
        frameHashes=[hashlib.sha256(frame.tobytes()).hexdigest().upper() for frame in frames],
        unresolved=motion['limitations'])
    (OUT/'build.json').write_text(json.dumps(metadata, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({key:value for key,value in metadata.items() if key!='frameHashes'}, indent=2))


if __name__ == '__main__':
    main()
