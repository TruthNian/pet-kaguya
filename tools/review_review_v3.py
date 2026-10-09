"""Keep the v2 gesture, restore known hair, reconcile only unknown interior."""
import hashlib
import json

import numpy as np
from PIL import Image,ImageDraw

from canonical import ROOT,ACCEPTED_SHA,load_canonical,clean_cutout,camera
import review_review_v2 as parent
from restore_review_known_hair import restore,specification,shared_edges
from review_wave import native_frame

OUT = ROOT/'candidates/phase5/review-art-v3'
GENERATED_SHA = parent.GENERATED_SHA


def inputs():
    return parent.inputs()


def localized_pose(base,raw,spec):
    pose,allowed,preserved = parent.localized_pose(base,raw,spec)
    revised,_,_,_,_ = restore(pose,spec,allowed,preserved)
    return revised,allowed,preserved


def main():
    base,spec,raw = inputs()
    previous,allowed,preserved = parent.localized_pose(base,raw,spec)
    pose,restoration,protected,known,unknown = restore(previous,spec,allowed,preserved)
    pose.save(OUT/'pose.png')
    for name,mask in [('allowed-mask',allowed),('restoration-mask',restoration),('known-source-mask',known),
                      ('unknown-interior-mask',unknown),('protected-foreground-mask',protected)]:
        Image.fromarray(mask.astype(np.uint8)*255).save(OUT/f'{name}.png')
    frame = native_frame(pose)
    frame.save(OUT/'frame.png')
    frames = [native_frame(load_canonical()),native_frame(previous),frame]
    for width in (80,113,192,224):
        parent.comparison(frames,width,['mother v3','before v2','source restore']).save(OUT/f'contact-{width}px.png')
    board = Image.new('RGB',(660,480),'#23252b')
    draw = ImageDraw.Draw(board)
    for i,(image,label) in enumerate(zip([load_canonical(),previous,pose],['mother v3','before v2','source restore'])):
        tile = Image.new('RGBA',(220,450),'#23252b')
        tile.alpha_composite(image.crop((760,570,980,1020)))
        board.paste(tile.convert('RGB'),(220*i,30))
        draw.text((220*i+5,7),label,fill='white')
    board.save(OUT/'detail.png')
    direct,_,_,_,_ = restore(previous,spec,allowed,preserved,reconcile=False)
    diagnostic = Image.new('RGB',(660,480),'#23252b')
    draw = ImageDraw.Draw(diagnostic)
    for i,(image,label) in enumerate(zip([previous,direct,pose],['before v2','direct copy NO','coupled boundary'])):
        tile = Image.new('RGBA',(220,450),'#23252b')
        tile.alpha_composite(image.crop((760,570,980,1020)))
        diagnostic.paste(tile.convert('RGB'),(220*i,30))
        draw.text((220*i+5,7),label,fill='white')
    diagnostic.save(OUT/'failed-direct-copy-detail.png')
    before,after,old = np.asarray(base),np.asarray(pose),np.asarray(previous)
    changed = np.any(before!=after,axis=2)
    delta = np.any(old!=after,axis=2)
    with Image.open(ROOT/'candidates/phase5/review-art-v1/pose.png') as image:
        v1 = np.asarray(image.convert('RGBA'))
    definition = specification()
    metadata = dict(sourceSha256=ACCEPTED_SHA,generatedSha256=GENERATED_SHA,generatedSource=spec['generatedSource'],
        leftArmGeneratedSha256=parent.LEFT_SHA,role=definition['role'],rawCanvas=spec['rawCanvas'],
        sourceCrop=spec['sourceCrop'],cropProjection=spec['cropProjection'],newArtworkGenerated=False,
        parentCompositionVersion='review-art-v2',compositionVersion='review-art-v3',
        parentPoseRGBAHash=hashlib.sha256(previous.tobytes()).hexdigest().upper(),
        boundedRightArmChangedPixels=int(changed.sum()),boundedRightArmChangedPixelsOutsidePatch=int((changed&~allowed).sum()),
        rawMappedCropChangedPixelsOutsidePatch=int((np.any(before!=np.asarray(raw),axis=2)&~allowed).sum()),
        changedPixelsFromV1=int(np.any(v1!=after,axis=2).sum()),changedPixelsFromV2=int(delta.sum()),
        knownSourceHairRestoredPixels=int(known.sum()),unknownHairInteriorPixels=int(unknown.sum()),
        knownUnknownSharedBoundaryEdges=shared_edges(known,unknown),
        unknownHairRGBChangedPixels=int((np.any(old[...,:3]!=after[...,:3],axis=2)&unknown).sum()),
        restoredAlphaPixels=int((old[...,3]!=after[...,3]).sum()),knownSourceHairRGBAExact=True,
        directCopyAloneAccepted=False,erodedUnknownDomainAccepted=False,
        paintedHairAlphaContinuityEstimated=True,knownHairAlphaMedian=definition['hiddenAlphaNominalValue'],
        poseRGBAHash=hashlib.sha256(pose.tobytes()).hexdigest().upper(),
        frameRGBAHash=hashlib.sha256(frame.tobytes()).hexdigest().upper(),
        originalHeadFaceRGBAExact=True,sourceForegroundPlatesPreserved=True,heldRightArmRGBAExact=True,
        camera=camera(clean_cutout(load_canonical())[0]),sameSourceCoordinateCamera=True,
        fullRedrawAccepted=False,facialGeometryRepair=False,articulatedArmBuilt=False,animationBuilt=False,
        visualAcceptance='pending',strategyUserApproval='pending',installableFullAtlas=False,installed=False,
        placementLimitation='Known hair is source RGBA, but source foreground pixel-plates are not clean layers. Hidden RGB/alpha continuity is estimated, not recovered strand topology. Hand volumes, angular sleeve folds, remaining hair/plate seams, small-scale cues and state transitions remain unapproved.')
    (OUT/'build.json').write_text(json.dumps(metadata,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(metadata,indent=2))


if __name__ == '__main__':
    main()
