"""Current review: v5 hands/hair with continuous, locally painted sleeves."""
import json
import numpy as np
from PIL import Image
from canonical import ROOT
import review_review_v5 as parent
import review_cloth_v2 as cloth
from review_sleeves import rgba_hash
from review_wave import native_frame

OUT=ROOT/'candidates/phase5/review-art-v6'
GENERATED_SHA=parent.GENERATED_SHA  # The right-hand source is unchanged.


def inputs():
    return parent.inputs()


def localized_pose(base,raw,spec):
    before,allowed,preserved=parent.localized_pose(base,raw,spec)
    _,mapped=cloth.inputs()
    pose,cloth_allowed,_,_,_,_=cloth.compose(before,mapped)
    if np.any(cloth_allowed&preserved):
        raise ValueError('Sleeve permission intersects preserved foreground')
    return pose,allowed|cloth_allowed,preserved


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    base,spec,raw=inputs()
    before=cloth.parent()  # compose() checks the recomputed parent against this hash.
    pose,allowed,preserved=localized_pose(base,raw,spec)
    pose.save(OUT/'pose.png');frame=native_frame(pose);frame.save(OUT/'frame.png')
    a,b=np.asarray(base),np.asarray(pose)
    with Image.open(ROOT/'candidates/phase5/review-art-v1/pose.png') as image:first=np.asarray(image.convert('RGBA'))
    meta=json.loads((parent.OUT/'build.json').read_text(encoding='utf-8'))
    for key in ('changedPixelsFromV4','alphaChangedPixelsFromV4','changedOutsideSourceHoles',
                'parentPoseRGBAHash'):meta.pop(key,None)
    meta.update(parentCompositionVersion='review-art-v5',compositionVersion='review-art-v6',
        parentPoseRGBAHash=cloth.PARENT_HASH,poseRGBAHash=rgba_hash(pose),frameRGBAHash=rgba_hash(frame),
        role='continuous sleeve interiors; exact v5 hands, silhouette and alpha',
        clothCompositionVersion='review-sleeves-v2',clothGeneratedSha256=cloth.GENERATED_SHA,
        newArtworkGenerated=True,handsAndSleevesRGBAExact=False,handsRGBAExactFromV5=True,
        alphaRGBAExactFromV5=True,sourceHairCompositionVersion='review-art-v5',
        changedPixelsFromV5=int(np.any(np.asarray(before)!=b,axis=2).sum()),
        boundedRightArmChangedPixels=int(np.any(a!=b,axis=2).sum()),
        boundedRightArmChangedPixelsOutsidePatch=int((np.any(a!=b,axis=2)&~allowed).sum()),
        changedPixelsFromV1=int(np.any(first!=b,axis=2).sum()),
        rawMappedCropChangedPixelsOutsidePatch=int((np.any(a!=np.asarray(raw),axis=2)&~allowed).sum()),
        placementLimitation='Source foreground pixel-plates are not clean recovered mattes. '
            'Sleeve interiors repainted with fixed-crop continuous material; hands/outer lines unchanged. '
            'Full hand-volume/occlusion, boundary integration and entry/exit naturalness remain unapproved.')
    (OUT/'build.json').write_text(json.dumps(meta,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(meta,indent=2))


if __name__=='__main__':main()
