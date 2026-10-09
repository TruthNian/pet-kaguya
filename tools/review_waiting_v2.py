"""Current held waiting: original hand/face with a bounded complete sleeve."""
import json
import numpy as np
from canonical import ROOT,load_canonical,clean_cutout
import review_waiting as parent
import review_waiting_sleeve as cloth
from review_wave import native_frame

OUT=ROOT/'candidates/phase5/waiting-art-v2'
GENERATED_SHA=parent.GENERATED_SHA  # The original hand source did not change.
load_generated=parent.load_generated
specification=parent.specification


def localized_pose(mother,raw,spec):
    before,allowed,hand=parent.localized_pose(mother,raw,spec)
    _,mapped=cloth.inputs()
    pose,cloth_allowed,protected,_=cloth.compose(before,mapped)
    if np.any(cloth_allowed&hand):
        raise ValueError('Waiting sleeve cannot repaint or move the held hand')
    return pose,allowed|cloth_allowed,hand


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    mother=load_canonical()
    pose,allowed,hand=localized_pose(mother,load_generated(),specification())
    before=cloth.parent()
    pose.save(OUT/'pose.png');frame=native_frame(pose);frame.save(OUT/'frame.png')
    a,b,c=np.asarray(mother),np.asarray(pose),np.asarray(before)
    meta=json.loads((parent.OUT/'build.json').read_text(encoding='utf-8'))
    meta.update(parentCompositionVersion='waiting-art-v1',compositionVersion='waiting-art-v2',
        parentPoseRGBAHash=cloth.PARENT_HASH,poseRGBAHash=cloth.rgba_hash(pose),frameRGBAHash=cloth.rgba_hash(frame),
        clothCompositionVersion='waiting-sleeve-v1',clothGeneratedSha256=cloth.GENERATED_SHA,
        newArtworkGenerated=True,handRGBAExactFromV1=bool(np.array_equal(b[hand],c[hand])),
        changedPixelsFromV1=int(np.any(b!=c,axis=2).sum()),
        alphaChangedPixelsFromV1=int((b[...,3]!=c[...,3]).sum()),
        boundedChangedPixels=int(np.any(a!=b,axis=2).sum()),
        boundedChangedPixelsOutsidePatch=int((np.any(a!=b,axis=2)&~allowed).sum()),
        alphaCleanup=clean_cutout(pose)[1],
        adoptedIntoDevelopmentOnly=True,clothOnlyPixelChangeClaimed=False,cleanSemanticMatteClaimed=False,
        placementLimitation='Complete raised garment plus limited contour-side occlusion backing. '
            'Face and original held hand unchanged; alpha changes are allowed only within the recorded garment envelope. '
            'Hard shadows, fold scale, wrist/cape contour integration and full aesthetics remain unapproved. '
            'No enter/exit motion or installed host change.')
    (OUT/'build.json').write_text(json.dumps(meta,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(meta,indent=2))


if __name__=='__main__':main()
