"""Retain v3 hair repair; complete the observed original lower-hand contour."""
import hashlib
import json

import numpy as np
from PIL import Image

from canonical import ROOT
import review_review_v3 as parent
from repair_review_hand_outline import repair, OUT as REPAIR_OUT
from review_review_v2 import comparison
from review_wave import native_frame

OUT = ROOT/'candidates/phase5/review-art-v4'
GENERATED_SHA = parent.GENERATED_SHA


def inputs():
    return parent.inputs()


def localized_pose(base, raw, spec):
    before, allowed, preserved = parent.localized_pose(base, raw, spec)
    pose, correction, protected, _, _ = repair(before, spec, raw)
    if not np.array_equal(preserved, protected):
        raise ValueError('Hand contour repair changed the foreground protection')
    return pose, allowed | correction, preserved


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    base, spec, raw = inputs()
    before, _, _ = parent.localized_pose(base, raw, spec)
    pose, allowed, preserved = localized_pose(base, raw, spec)
    pose.save(OUT/'pose.png')
    Image.fromarray(allowed.astype(np.uint8)*255).save(OUT/'allowed-mask.png')
    Image.fromarray(preserved.astype(np.uint8)*255).save(OUT/'preserved-foreground-mask.png')
    frame = native_frame(pose)
    frame.save(OUT/'frame.png')
    for width in (80,113,192,224):
        comparison([native_frame(base),native_frame(before),frame], width,
                   ['before hand cel','v3 clipped','v4 contour']).save(OUT/f'contact-{width}px.png')
    a,b = np.asarray(base),np.asarray(pose)
    changed = np.any(a!=b,axis=2)
    meta = json.loads((parent.OUT/'build.json').read_text(encoding='utf-8'))
    correction = json.loads((REPAIR_OUT/'build.json').read_text(encoding='utf-8'))
    # Preserve provenance of the preceding hair revision explicitly. Its
    # changed-from-v2 counts must not masquerade as v4 measurements.
    for key in ('changedPixelsFromV2','restoredAlphaPixels'):
        meta.pop(key, None)
    with Image.open(ROOT/'candidates/phase5/review-art-v1/pose.png') as image:
        first = np.asarray(image.convert('RGBA'))
    meta.update(parentCompositionVersion='review-art-v3',compositionVersion='review-art-v4',
                role='restore observed lower-hand contour; retain v3 source-conditioned hair repair',
                parentPoseRGBAHash=hashlib.sha256(before.tobytes()).hexdigest().upper(),
                poseRGBAHash=hashlib.sha256(pose.tobytes()).hexdigest().upper(),
                frameRGBAHash=hashlib.sha256(frame.tobytes()).hexdigest().upper(),
                boundedRightArmChangedPixels=int(changed.sum()),
                boundedRightArmChangedPixelsOutsidePatch=int((changed&~allowed).sum()),
                rawMappedCropChangedPixelsOutsidePatch=int((np.any(a!=np.asarray(raw),axis=2)&~allowed).sum()),
                changedPixelsFromV1=int(np.any(first!=b,axis=2).sum()),
                changedPixelsFromV3=correction['changedPixels'],
                handContourAlphaChangedPixels=correction['alphaChangedPixels'],
                originalLowerHandContourRestored=True,handScaled=False,
                heldRightArmRGBAExact=False,upperForegroundHandRGBAExact=True,
                sourceHairCompositionVersion='review-art-v3',
                handContourRepair='candidates/phase5/review-hand-outline-v1/build.json',
                placementLimitation='Observed contour clipping corrected, without hand scaling. '
                    'Source foreground pixel-plates are not clean recovered mattes. '
                    'Hair boundary remains estimated; sleeve folds, hand-volume/occlusion aesthetics, '
                    'small-scale cues and entry/exit transitions remain unapproved. Not a clean rig.')
    (OUT/'build.json').write_text(json.dumps(meta,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(meta,indent=2))


if __name__ == '__main__':
    main()
