"""Accepted eight-cel mouth basis against frozen exact prior failed cels."""
import hashlib
import json
import numpy as np
from PIL import Image
from canonical import ROOT, ACCEPTED_SHA, clean_cutout
from guide_failed_mouth import OUT as ART_OUT
import review_failed_mouth as mouth
import build_failed
from build_idle import render
from animation_output import write_animation
from protocol import DURATIONS

OUT = ART_OUT / 'animation'
REFERENCE = ROOT/'sources/reference/failed-mouth-v1'


def inputs():
    mouth.decision()
    original, _, transform, regions, masks, motion = build_failed.reference_inputs()
    before, mapped = mouth.inputs()
    pose, allowed, _ = mouth.compose(before, mapped)
    source = clean_cutout(pose)[0]
    old_frames, frames = [], []
    for key in motion['keyframes']:
        old_frames.append(render(original,key,transform,regions,masks))
        frames.append(render(source,key,transform,regions,masks))
    active = json.loads((build_failed.OUT/'build.json').read_text(encoding='utf-8'))
    baseline = json.loads((REFERENCE/'contract.json').read_text(encoding='utf-8'))
    manifest = json.loads((REFERENCE/'manifest.json').read_text(encoding='utf-8'))
    if hashlib.sha256((REFERENCE/manifest['file']).read_bytes()).hexdigest().upper() != manifest['fileSha256']:
        raise ValueError('Frozen old-mouth strip changed')
    if [mouth.rgba_hash(frame) for frame in old_frames] != baseline['frameHashes']:
        raise ValueError('Baseline is not the exact archived prior failed row')
    if [mouth.rgba_hash(frame) for frame in frames] != active['frameHashes']:
        raise ValueError('Accepted-mouth preview differs from actual current failed row')
    if active['keyframes'] != motion['keyframes'] or baseline['keyframes'] != motion['keyframes']:
        raise ValueError('Baseline native poses do not match the current contract')
    return dict(before=before,pose=pose,allowed=allowed,source=source,transform=transform,
                regions=regions,masks=masks,motion=motion,frames=frames,oldFrames=old_frames,
                active=active,baseline=baseline)


def main():
    data = inputs()
    write_animation(OUT,data['frames'],DURATIONS[5])
    changes = []
    for old,new in zip(data['oldFrames'],data['frames']):
        a,b = np.asarray(old),np.asarray(new)
        changed = np.any(a!=b,axis=2)
        yy,xx = np.where(changed)
        if np.any(a[...,3]!=b[...,3]):
            raise ValueError('Internal mouth trial changed actual native coverage')
        changes.append(dict(changedPixels=int(changed.sum()),alphaChangedPixels=0,
            bounds=None if not len(xx) else [int(xx.min()),int(yy.min()),int(xx.max()+1),int(yy.max()+1)]))
    metadata = dict(sourceSha256=ACCEPTED_SHA,state='failed',previewVariant='failed_mouth',nativeRow=5,
        source='sources/canonical/artwork.png',mouthArt='candidates/phase5/failed-mouth-v2',
        mouthGeneratedSha256=mouth.GENERATED_SHA,parentPoseRGBAHash=mouth.rgba_hash(data['before']),
        candidatePoseRGBAHash=mouth.rgba_hash(data['pose']),camera=data['transform'],
        durationsMs=DURATIONS[5],keyframes=data['motion']['keyframes'],repeatBeforeIdle=3,
        totalDurationMs=sum(DURATIONS[5]),actionDurationMs=3*sum(DURATIONS[5]),
        baselineFrameHashes=data['baseline']['frameHashes'],
        frameHashes=[mouth.rgba_hash(frame) for frame in data['frames']],changesFromFrozenOldMouth=changes,
        referencePurpose='isolate-internal-mouth-rgb-only',baselineActualCelsReconstructedExactly=True,
        sourceAlphaPreservedExactly=True,nativeAlphaPreservedExactly=True,
        bodyEarHairPosesUnchanged=True,sameSourceCoordinateCamera=True,
        closedEyeFrames=0,facialGeometryRepair=False,newFaceGeometry=False,
        nativeInterpolation=False,newArtworkGenerated=True,animationBuilt=True,
        adopted=True,adoptionScope='mouth-line-development-basis-only',
        mouthLineVisualApproval='approved-as-development-basis',userDecision=mouth.DECISION,
        currentFailedCelsRGBAExact=True,visualMotionApproval='pending',
        installableFullAtlas=False,installed=False,
        limitations=['Eight real holds, no new native state, no added interpolation or host changes.',
            'Internal mouth RGB includes nearby skin. Eyes/brows/jaw/costume and all source alpha remain exact.',
            'Line width is 46 source pixels by the recorded diagnostic, not the requested mother width of 54.',
            'Mouth line accepted as development basis only. Small-size legibility, brows, full motion and transitions remain unapproved.'])
    (OUT/'build.json').write_text(json.dumps(metadata,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(metadata,indent=2))


if __name__ == '__main__':
    main()
