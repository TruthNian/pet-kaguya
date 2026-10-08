"""Native waiting holds; a stable hand-cheek relationship, no false entry/exit."""
import hashlib
import json
import math

import numpy as np

from canonical import ROOT,ACCEPTED_SHA,load_canonical,clean_cutout,camera
import review_waiting as art
from build_idle import specification as idle_specification,region_masks,render
from animation_output import write_animation
from protocol import DURATIONS

OUT = ROOT/'candidates/phase5/waiting'


def validate_motion(motion):
    if (motion['sourceSha256'] != ACCEPTED_SHA or motion['state'] != 'waiting'
            or motion['nativeRow'] != 6 or motion['durationsMs'] != DURATIONS[6]
            or motion['repeatBeforeIdle'] != 3 or not motion['faceShapeLocked']
            or motion['closedEyeFrames'] != 0 or motion['bodyPulse'] or motion['nativeInterpolation']
            or motion['handStrategy'] != 'held-chin-contact' or motion['strategyUserApproval'] != 'pending'
            or motion['visualMotionApproval'] != 'pending'):
        raise ValueError('Waiting violates the locked source/native clock/unapproved strategy boundary')
    poses = motion['keyframes']
    if len(poses)!=6 or poses[0]!=poses[-1]:
        raise ValueError('Waiting needs six holds and an exact loop seam')
    for pose in poses:
        if (set(pose)!={'bodyY','earAngle','hairAngle'} or pose['bodyY']!=0
                or any(isinstance(v,bool) or not math.isfinite(v) for v in pose.values())
                or abs(pose['earAngle'])>.15 or abs(pose['hairAngle'])>.02):
            raise ValueError('Waiting cannot move the cheek/hand contact or add excessive fields')


def inputs():
    mother = load_canonical()
    pose,allowed,hand = art.localized_pose(mother,art.load_generated(),art.specification())
    motion = json.loads((ROOT/'sources/canonical/waiting-motion.json').read_text(encoding='utf-8'))
    validate_motion(motion)
    transform = camera(clean_cutout(mother)[0])
    regions,_ = idle_specification()
    masks = region_masks(regions)
    source = clean_cutout(pose)[0]
    rendered,frames = {},[]
    for keyframe in motion['keyframes']:
        key = tuple(keyframe[name] for name in ('bodyY','earAngle','hairAngle'))
        if key not in rendered:
            rendered[key] = render(source,keyframe,transform,regions,masks)
        frames.append(rendered[key])
    return dict(mother=mother,pose=pose,allowed=allowed,hand=hand,motion=motion,
                transform=transform,regions=regions,masks=masks,frames=frames)


def main():
    data = inputs()
    frames,motion = data['frames'],data['motion']
    for frame in frames:
        pixels = np.asarray(frame)
        if pixels[0,:,3].any() or pixels[-1,:,3].any() or pixels[:,0,3].any() or pixels[:,-1,3].any():
            raise ValueError('Waiting touches a cell edge')
    write_animation(OUT,frames,DURATIONS[6])
    metadata = dict(sourceSha256=ACCEPTED_SHA,source='sources/canonical/artwork.png',
        handGeneratedSha256=art.GENERATED_SHA,state='waiting',nativeRow=6,statesInThisArtifact=['waiting'],
        durationsMs=DURATIONS[6],totalDurationMs=sum(DURATIONS[6]),repeatBeforeIdle=3,
        actionDurationMs=3*sum(DURATIONS[6]),closedEyeFrames=0,bodyPulse=False,bodyTranslationPx=0,
        camera=data['transform'],sameSourceCoordinateCamera=True,
        handStrategy=motion['handStrategy'],strategyUserApproval='pending',
        cheekHandContactFixed=True,sourceFaceOutsideHandOcclusionFixed=True,
        loopSeamRGBAExact=frames[0].tobytes()==frames[-1].tobytes(),
        uniqueCels=len(set(frame.tobytes() for frame in frames)),
        frameHashes=[hashlib.sha256(frame.tobytes()).hexdigest().upper() for frame in frames],
        method='bounded original waiting key pose held with small non-face ear/hair response; no entry/exit simulation',
        sampling='same canonical camera, 3x coverage from high-resolution pose and one terminal Lanczos downsample',
        facialGeometryRepair=False,fullRedrawAccepted=False,articulatedArmBuilt=False,
        animationBuilt=True,nativeInterpolation=False,visualMotionApproval='pending',
        installableFullAtlas=False,installed=False,unresolved=motion['limitations'])
    (OUT/'build.json').write_text(json.dumps(metadata,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(metadata,indent=2))


if __name__ == '__main__':
    main()
