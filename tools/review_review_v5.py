"""Current hand composition with exact restoration of visible hair holes."""
import hashlib
import json

import numpy as np
from PIL import Image, ImageDraw

from canonical import ROOT, ACCEPTED_SHA, load_canonical
import review_review_v4 as parent
from repair_review_hair_holes import repair, PARENT_HASH
from review_review_v2 import comparison
from review_wave import native_frame

OUT = ROOT/'candidates/phase5/review-art-v5'
GENERATED_SHA = parent.GENERATED_SHA


def inputs():
    return parent.inputs()


def localized_pose(base,raw,spec):
    before,allowed,preserved = parent.localized_pose(base,raw,spec)
    pose,holes,_,_ = repair(before)
    return pose,allowed|holes,preserved


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    base,spec,raw = inputs()
    before,parent_allowed,_ = parent.localized_pose(base,raw,spec)
    pose,holes,visible,protected = repair(before)
    pose.save(OUT/'pose.png')
    frame = native_frame(pose)
    frame.save(OUT/'frame.png')
    for name,mask in (('source-hole',holes),('visible-source',visible),('protected',protected)):
        Image.fromarray(mask.astype(np.uint8)*255).save(OUT/f'{name}-mask.png')
    for width in (80,113,192,224):
        comparison([native_frame(load_canonical()),native_frame(before),frame],width,
                   ['mother v3','v4 alpha holes','v5 source restore']).save(OUT/f'contact-{width}px.png')
    board = Image.new('RGB',(750,330),'#23252b')
    draw = ImageDraw.Draw(board)
    for i,(image,label) in enumerate(((load_canonical(),'visible mother hair'),(before,'v4 alpha holes'),(pose,'v5 exact source RGBA'))):
        tile = Image.new('RGBA',(50,60),'#ededed')
        tile.alpha_composite(image.crop((885,795,935,855)))
        board.paste(tile.resize((250,300),Image.Resampling.NEAREST).convert('RGB'),(i*250,30))
        draw.text((i*250+5,8),label,fill='white')
    board.save(OUT/'detail.png')
    a,b = np.asarray(before),np.asarray(pose)
    changed = np.any(a!=b,axis=2)
    from_base = np.any(np.asarray(base)!=b,axis=2)
    with Image.open(ROOT/'candidates/phase5/review-art-v1/pose.png') as image:
        first = np.asarray(image.convert('RGBA'))
    meta = json.loads((parent.OUT/'build.json').read_text(encoding='utf-8'))
    meta.update(parentCompositionVersion='review-art-v4',compositionVersion='review-art-v5',
        parentPoseRGBAHash=PARENT_HASH,sourceSha256=ACCEPTED_SHA,
        role='restore visible source hair excluded by current-patch alpha threshold',
        poseRGBAHash=hashlib.sha256(pose.tobytes()).hexdigest().upper(),
        frameRGBAHash=hashlib.sha256(frame.tobytes()).hexdigest().upper(),
        restoredSourceHolePixels=int(holes.sum()),observedSourceHairPixels=int(visible.sum()),
        changedPixelsFromV4=int(changed.sum()),alphaChangedPixelsFromV4=int((a[...,3]!=b[...,3]).sum()),
        changedOutsideSourceHoles=int((changed&~holes).sum()),
        boundedRightArmChangedPixels=int(from_base.sum()),
        boundedRightArmChangedPixelsOutsidePatch=int((from_base&~(parent_allowed|holes)).sum()),
        changedPixelsFromV1=int(np.any(first!=b,axis=2).sum()),
        knownSourceHairRestoredPixels=int(visible.sum()),
        sourceHoleRGBAExact=bool(np.array_equal(b[holes],np.asarray(load_canonical())[holes])),
        handsAndSleevesRGBAExact=True,facialGeometryRepair=False,newArtworkGenerated=False,
        hiddenHairReconstructionClaimed=False,cleanLayerRecoveryClaimed=False,
        visualAcceptance='pending',installableFullAtlas=False,installed=False,
        placementLimitation='Only observed hair alpha-exclusion holes restored exactly from the mother. '
            'Foreground pixel-plate boundaries are not clean recovered layers. '
            'Hidden strand/sleeve/hand aesthetics and full gesture naturalness remain unapproved.')
    # These old measured values describe v4, not the new composition.
    meta.pop('changedPixelsFromV3',None)
    meta.pop('handContourAlphaChangedPixels',None)
    meta.pop('unknownHairRGBChangedPixels',None)
    meta['sourceHairCompositionVersion'] = 'review-art-v5'
    meta['precedingSourceHairRestoration'] = 'candidates/phase5/review-art-v3/build.json'
    meta['precedingHandContourRepair'] = 'candidates/phase5/review-art-v4/build.json'
    (OUT/'build.json').write_text(json.dumps(meta,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(meta,indent=2))


if __name__=='__main__':
    main()
