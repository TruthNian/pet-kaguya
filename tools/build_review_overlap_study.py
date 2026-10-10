"""Unadopted low-overlap hands, with the exact existing review held-motion contract."""
import hashlib
import json

import numpy as np
from PIL import Image

from canonical import ROOT, ACCEPTED_SHA, clean_cutout
import build_review
import build_gaze as gaze
import review_overlap as art
from build_idle import render, coordinates
from animation_output import write_animation
from protocol import DURATIONS

OUT = art.OUT/'animation'
REFERENCE = ROOT/'sources/reference/review-held-v6'
PURPOSE = 'isolate-review-held-hands-and-cuffs'
POSE_HASH = 'F4A43E5B7A3DFC23D89206E148C073CDA38317303CCDDEB17BC3CB49061B09F0'


def rgba_hash(image):
    return hashlib.sha256(image.tobytes()).hexdigest().upper()


def inputs():
    old = build_review.inputs()
    baseline = json.loads((REFERENCE/'contract.json').read_text(encoding='utf-8'))
    manifest = json.loads((REFERENCE/'manifest.json').read_text(encoding='utf-8'))
    if (manifest['referencePurpose'] != PURPOSE
            or hashlib.sha256((REFERENCE/manifest['file']).read_bytes()).hexdigest().upper()
                != manifest['fileSha256']):
        raise ValueError('Frozen actual review strip changed')
    if [rgba_hash(frame) for frame in old['frames']] != baseline['frameHashes']:
        raise ValueError('Review baseline is not the exact frozen six actual cels')
    with Image.open(REFERENCE/manifest['file']) as strip:
        for i, frame in enumerate(old['frames']):
            if strip.convert('RGBA').crop((192*i,0,192*(i+1),208)).tobytes() != frame.tobytes():
                raise ValueError('Frozen review image and recorded frame hashes disagree')
    for key, value in [('sourceSha256',ACCEPTED_SHA),('durationsMs',DURATIONS[8]),
                       ('camera',old['transform']),('focusOffsetSourcePx',[0,5]),
                       ('repeatBeforeIdle',3),('nativeRow',8),('state','review')]:
        if baseline[key] != value:
            raise ValueError('Review source/camera/holds/gaze contract changed')
    before, mapped = art.inputs()
    if before.tobytes() != old['armPose'].tobytes():
        raise ValueError('Overlap candidate does not begin at the actual review v6 source pose')
    pose, allowed, protected, _ = art.compose(before,mapped)
    if rgba_hash(pose) != POSE_HASH:
        raise ValueError('Static overlap source candidate changed without review')
    layers = gaze.layers(old['mother'],gaze.load_generated(),gaze.specification())
    focused = gaze.pose(pose,layers,*old['motion']['focusOffsetSourcePx'])
    a,b = np.asarray(old['focused']),np.asarray(focused)
    if np.any(np.any(a!=b,axis=2)&~allowed) or not np.array_equal(a[...,3],b[...,3]):
        raise ValueError('Hand study changed an eye/face or source pixel outside hand/cuff permission')
    # Probe every permitted source sample, not merely selected wrist points.
    # Existing secondary fields must leave both versions' held hands fixed.
    yy,xx = np.where(allowed)
    x,y = xx.astype(float),yy.astype(float)
    displacement = []
    for key in old['motion']['keyframes']:
        sx,sy = coordinates(x,y,key,old['transform'],old['regions'],old['masks'])
        displacement.append(float(np.max(np.hypot(sx-x,sy-y))))
    if any(value != 0 for value in displacement):
        raise ValueError('Old ear/hair fields deform the new held hand/cuff permission')
    source = clean_cutout(focused)[0]
    rendered, frames = {}, []
    for key in old['motion']['keyframes']:
        cache_key = tuple(key[name] for name in ('bodyY','earAngle','hairAngle'))
        if cache_key not in rendered:
            rendered[cache_key] = render(source,key,old['transform'],old['regions'],old['masks'])
        frames.append(rendered[cache_key])
    changes = []
    for old_frame,frame in zip(old['frames'],frames):
        a,b = np.asarray(old_frame),np.asarray(frame)
        changed = np.any(a!=b,axis=2)
        yy,xx = np.where(changed)
        # Full face/eyes, hair tips and feet stay exact even after filtering.
        budget = np.zeros(changed.shape,bool)
        budget[90:145,55:110] = True
        if np.any(changed&~budget) or not np.array_equal(a[...,3],b[...,3]):
            raise ValueError('Native changes escaped the hand/cuff RGB budget or altered coverage')
        changes.append(dict(changedPixels=int(changed.sum()),alphaChangedPixels=0,
            bounds=None if not len(xx) else [int(xx.min()),int(yy.min()),int(xx.max()+1),int(yy.max()+1)]))
    return dict(old=old,baseline=baseline,pose=pose,focused=focused,allowed=allowed,
        protected=protected,frames=frames,changes=changes,displacement=displacement)


def main():
    data = inputs()
    old = data['old']
    write_animation(OUT,data['frames'],DURATIONS[8])
    data['focused'].save(OUT/'focused-pose.png')
    metadata = dict(sourceSha256=ACCEPTED_SHA,source='sources/canonical/artwork.png',
        state='review',previewVariant='review_overlap',nativeRow=8,
        handArt='candidates/phase5/review-hands-overlap-v1',handGeneratedSha256=art.GENERATED_SHA,
        parentPoseRGBAHash=rgba_hash(old['armPose']),candidatePoseRGBAHash=rgba_hash(data['pose']),
        focusedPoseRGBAHash=rgba_hash(data['focused']),camera=old['transform'],
        durationsMs=DURATIONS[8],keyframes=old['motion']['keyframes'],repeatBeforeIdle=3,
        totalDurationMs=sum(DURATIONS[8]),actionDurationMs=3*sum(DURATIONS[8]),
        focusOffsetSourcePx=old['motion']['focusOffsetSourcePx'],handStrategy='low-overlapping-hands-held',
        heldTimingUserDecision=old['motion']['heldTimingUserDecision'],heldTimingAcceptedTemporarily=True,
        baselineFrameHashes=data['baseline']['frameHashes'],
        frameHashes=[rgba_hash(frame) for frame in data['frames']],changesFromFrozenReview=data['changes'],
        referencePurpose=PURPOSE,baselineActualCelsReconstructedExactly=True,
        sourceAlphaPreservedExactly=True,nativeAlphaPreservedExactly=True,
        sourceChangesInsideHandCuffPermissionOnly=True,sourceEyeFaceRGBAExactToBaseline=True,
        bodyEarHairPosesUnchanged=True,handCuffMaximumSourceDisplacementPx=data['displacement'],
        sameSourceCoordinateCamera=True,closedEyeFrames=0,facialGeometryRepair=False,newFaceGeometry=False,
        nativeInterpolation=False,animationBuilt=True,newArtworkGeneratedThisBuild=False,
        loopSeamRGBAExact=data['frames'][0].tobytes()==data['frames'][-1].tobytes(),
        specificPoseUserApproval='pending',visualMotionApproval='pending',
        adopted=False,activeAtlasChanged=False,installableFullAtlas=False,installed=False,
        articulatedArmBuilt=False,cleanLayerRecoveryClaimed=False,entryExitTransitionsBuilt=False,
        limitations=['Six held cels only; reuses existing unapproved static hand/cuff artwork.',
            'Same original-iris focus, camera, ear/hair fields, native holds and three-cycle fallback.',
            'Hand/cuff RGB is bounded; original alpha, face/eyes and shoes preserved. Protected visible waist motif is retained; newly occluded parts are not claimed pixel-exact.',
            'No new state, interpolation, natural entry/exit or clean author-layer claim.',
            'Hand anatomy, wrist/cuff continuity and small-size visual quality still need user review.',
            'Temporary held timing acceptance does not approve this hand strategy, full animation or installation.'])
    (OUT/'build.json').write_text(json.dumps(metadata,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(metadata,indent=2))


if __name__ == '__main__':
    main()
