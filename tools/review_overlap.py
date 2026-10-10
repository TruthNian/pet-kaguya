"""A bounded static overlap study; no action/atlas/installation substitution."""
import hashlib
import json
import argparse
import numpy as np
from PIL import Image,ImageDraw,ImageFilter
from canonical import ACCEPTED_SHA,load_canonical
from guide_review_overlap import OUT,BOX,SIDE
from guide_review_hands_pair import parent,PARENT_HASH
from review_wave import native_frame
from review_review_v2 import comparison
from review_waiting import grid

GENERATED_SHA='4ACA513583BF6BD69B642D5A656E97386E3B890CD2BBD861A96B6A4A98AAB6EE'
RAW_SIZE=(1254,1254)
# Inspected union of old/new hands and immediate cuffs, not a skin threshold.
FIRST_POLYGON=[(418,638),(450,625),(517,629),(530,650),(612,672),(624,738),
         (638,778),(605,795),(532,772),(500,766),(429,823),(402,821),
         (425,738),(425,698)]
# Existing belt/pendant, red bow and visible hair are not editable cloth.
FIRST_PROTECTED=[[(521,575),(695,575),(695,655),(526,662)],
           [(610,663),(695,654),(695,825),(638,825),(630,757),(608,748)],
           [(385,575),(452,575),(450,609),(479,610),(480,634),(453,642),(440,629)]]
SECOND_POLYGON=[(458,632),(506,632),(520,650),(530,664),(566,684),(599,690),
         (611,709),(625,744),(635,780),(619,786),(603,769),(584,752),
         (522,760),(483,752),(453,750),(418,811),(407,824),(396,824),
         (399,810),(410,779),(421,750),(432,723),(438,698),(445,666)]
PROTECTED=[FIRST_PROTECTED[0],
           [(640,660),(695,660),(695,825),(644,825),(642,744),(624,736),
            (614,727),(607,716),(605,704),(612,690),(625,679)],
           FIRST_PROTECTED[2]]
FIRST_POSE_HASH='C92586E3B68041F6590447847150D79A1065777930E6FD8A2CFF36CEBC687DE1'
SECOND_POSE_HASH='BDEB711C0596C45F00706248B10C55BF7809D69B9026AF0198A5BA2EDCC91CE4'
POSE_HASH='F4A43E5B7A3DFC23D89206E148C073CDA38317303CCDDEB17BC3CB49061B09F0'
POLYGON=[(440,632),(516,632),(532,660),(610,660),(627,688),(644,733),
         (645,784),(625,797),(603,774),(573,763),(492,764),(467,778),
         (443,804),(420,819),(395,819),(404,793),(416,766),(429,736),
         (436,710),(439,682)]


def inputs():
    before=parent();path=OUT/'generated.png'
    if hashlib.sha256(path.read_bytes()).hexdigest().upper()!=GENERATED_SHA:
        raise ValueError('Overlap study needs its immutable actual generated output')
    with Image.open(path) as image:raw=image.convert('RGBA')
    if raw.size!=RAW_SIZE:raise ValueError('The measured square output changed')
    projected=raw.convert('RGBa').resize((SIDE,SIDE),Image.Resampling.LANCZOS).convert('RGBA')
    mapped=before.copy();mapped.paste(projected.crop((0,0,310,250)),BOX[:2])
    return before,mapped


def masks(before,first=False,second=False):
    if first and second:raise ValueError('Choose a single composition stage')
    polygon=FIRST_POLYGON if first else SECOND_POLYGON if second else POLYGON
    boundaries=FIRST_PROTECTED if first else PROTECTED
    mask=Image.new('L',before.size);ImageDraw.Draw(mask).polygon(polygon,fill=255)
    protection=Image.new('L',before.size)
    for boundary in boundaries:ImageDraw.Draw(protection).polygon(boundary,fill=255)
    allowed=np.asarray(mask)>0;protected=np.asarray(protection)>0
    allowed&=~protected
    # Permission itself, not just changed pixels, must exclude face/shoes and crop padding.
    budget=np.zeros(allowed.shape,bool);budget[575:825,385:695]=True
    if np.any(allowed&~budget):raise ValueError('Overlap permission escaped the face-free crop')
    weight=np.asarray(mask.filter(ImageFilter.GaussianBlur(1.5)),dtype=float)/255
    weight[~allowed]=0
    return allowed,protected,weight


def compose(before,mapped,first=False,second=False):
    if (before.mode!='RGBA' or before.size!=(1205,1306) or mapped.mode!='RGBA'
            or mapped.size!=before.size or hashlib.sha256(before.tobytes()).hexdigest().upper()!=PARENT_HASH):
        raise ValueError('Overlap composition requires the immutable parent and registered RGBA material')
    allowed,protected,weight=masks(before,first,second)
    a,b=np.asarray(before),np.asarray(mapped)
    if not first:
        # Both hands are painted within the existing costume silhouette, not
        # new exposed exterior pixels. Repaint RGB; keep parent alpha exact.
        # The generated RGBA file remains immutable, not flattened/rewritten.
        if np.any(allowed&((a[...,3]==0)|(b[...,3]==0))):
            raise ValueError('Interior repaint cannot invent RGB in absent material')
        if not second and np.any(allowed&((a[...,3]<240)|(b[...,3]<240))):
            raise ValueError('Interior repaint cannot treat the transparent crop edge as costume texture')
        result=a.copy()
        mixed=a[...,:3]*(1-weight[...,None])+b[...,:3]*weight[...,None]
        result[...,:3][allowed]=np.clip(np.rint(mixed[allowed]),0,255).astype(np.uint8)
        return Image.fromarray(result),allowed,protected,weight
    # Preserve and reproduce the first failed composition, including its
    # unintended 20747 alpha changes and overly broad bow protection.
    af,bf=a.astype(float),b.astype(float)
    af[...,:3]*=af[...,3:4]/255;bf[...,:3]*=bf[...,3:4]/255
    out=af*(1-weight[...,None])+bf*weight[...,None]
    np.divide(out[...,:3]*255,out[...,3:4],out=out[...,:3],where=out[...,3:4]>0)
    result=a.copy();result[allowed]=np.clip(np.rint(out[allowed]),0,255).astype(np.uint8)
    return Image.fromarray(result),allowed,protected,weight


def development_pose(before):
    """Select existing hand/cuff pixels, without rewriting historical approval."""
    metadata=json.loads((OUT/'build.json').read_text(encoding='utf-8'))
    digest=lambda image:hashlib.sha256(image.tobytes()).hexdigest().upper()
    if (digest(before)!=PARENT_HASH or metadata['parentPoseRGBAHash']!=PARENT_HASH
            or metadata['sourceSha256']!=ACCEPTED_SHA or metadata['poseRGBAHash']!=POSE_HASH
            or hashlib.sha256((OUT/'generated.png').read_bytes()).hexdigest().upper()!=GENERATED_SHA):
        raise ValueError('Selected overlap source or parent changed')
    with Image.open(OUT/'static-candidate.png') as image:pose=image.convert('RGBA')
    if pose.size!=before.size or digest(pose)!=POSE_HASH:
        raise ValueError('Expected the actual selected static hand/cuff pixels')
    allowed,protected,_=masks(before)
    a,b=np.asarray(before),np.asarray(pose)
    if np.any(np.any(a!=b,axis=2)&~allowed) or not np.array_equal(a[...,3],b[...,3]):
        raise ValueError('Hand selection changed protected pixels or alpha')
    return pose,allowed,protected


def main():
    before,mapped=inputs();pose,allowed,protected,weight=compose(before,mapped)
    failed,_,_,_=compose(before,mapped,first=True)
    if hashlib.sha256(failed.tobytes()).hexdigest().upper()!=FIRST_POSE_HASH:
        raise ValueError('Do not erase or reinterpret the first failed cuff composite')
    failed.save(OUT/'failed-first-mask.png')
    second,_,_,_=compose(before,mapped,second=True)
    if hashlib.sha256(second.tobytes()).hexdigest().upper()!=SECOND_POSE_HASH:
        raise ValueError('Keep the second clipped-cuff/moon study reproducible')
    second.save(OUT/'failed-second-mask.png')
    mapped.save(OUT/'raw-mapped.png');pose.save(OUT/'static-candidate.png')
    material=np.asarray(mapped).copy();material[...,3]=np.asarray(before)[...,3]
    Image.fromarray(material).save(OUT/'mapped-material.png')
    grid(before,BOX).save(OUT/'source-grid.png');grid(mapped,BOX).save(OUT/'mapped-grid.png')
    for name,mask in [('allowed-mask',allowed),('protected-mask',protected)]:
        Image.fromarray(mask.astype(np.uint8)*255).save(OUT/f'{name}.png')
    Image.fromarray(np.rint(weight*255).astype(np.uint8)).save(OUT/'blend-weight.png')
    frame=native_frame(pose);frame.save(OUT/'frame.png')
    frames=[native_frame(before),native_frame(mapped),frame]
    for width in (80,113,192,224):
        comparison(frames,width,['current v6','raw NOT adopted','bounded study']).save(OUT/f'contact-{width}px.png')
    detail=Image.new('RGB',(930,275),'#23252b');draw=ImageDraw.Draw(detail)
    for index,(image,label) in enumerate(((before,'current v6'),(mapped,'raw NOT adopted'),(pose,'bounded static study'))):
        tile=Image.new('RGBA',(310,250),'#ededed');tile.alpha_composite(image.crop(BOX))
        detail.paste(tile.convert('RGB'),(310*index,25));draw.text((310*index+4,7),label,fill='white')
    detail.save(OUT/'detail.png')
    a,b=np.asarray(before),np.asarray(pose);changed=np.any(a!=b,axis=2)
    if np.any(changed&~allowed) or np.any(changed&protected):raise ValueError('Protected artwork changed')
    meta=dict(sourceSha256=ACCEPTED_SHA,parentPoseRGBAHash=PARENT_HASH,generatedSha256=GENERATED_SHA,
        rawCanvas=list(RAW_SIZE),sourceCrop=list(BOX),fixedSquareProjection=True,objectBoundsFit=False,
        allowedPolygons=[POLYGON],protectedPolygons=PROTECTED,edgeFeatherSourcePx=1.5,
        allowedSourcePixels=int(allowed.sum()),changedSourcePixels=int(changed.sum()),
        changedAlphaPixels=int((a[...,3]!=b[...,3]).sum()),changedOutsideAllowed=0,
        rawChangesRejectedOutsideAllowed=int((np.any(a!=np.asarray(mapped),axis=2)&~allowed).sum()),
        composition='interior RGB texture repaint; complete parent alpha unchanged',
        parentAlphaMinInsidePermission=int(a[...,3][allowed].min()),
        rawAlphaMinInsidePermission=int(np.asarray(mapped)[...,3][allowed].min()),
        generatedRGBAFilePreserved=True,completeParentAlphaPreserved=True,
        firstFailurePoseRGBAHash=FIRST_POSE_HASH,firstFailureAlphaChangedPixels=20747,
        firstFailure='The initial bow protection included part of the cream cuff and clipped it. '
            'Copying generated alpha also changed opacity inside a locked costume silhouette.',
        secondFailurePoseRGBAHash=SECOND_POSE_HASH,
        secondFailure='An undersized union still clipped the full cuff/moon, and included alpha=35 crop-edge fragments. '
            'Current permission covers whole local objects and stops before transparent padding; alpha>=240 is a material-support guard, not an anatomical matte.',
        poseRGBAHash=hashlib.sha256(pose.tobytes()).hexdigest().upper(),
        frameRGBAHash=hashlib.sha256(frame.tobytes()).hexdigest().upper(),
        faceIncluded=False,facialGeometryRepair=False,handScaled=False,
        originalMoonMotifRemovalAllowed=False,specificPoseUserApproval='pending',
        heldTimingChangeAllowed=False,adopted=False,activeAtlasChanged=False,
        animationBuilt=False,installed=False,installableFullAtlas=False,visualAcceptance='pending',
        limitation='Static same-camera hand/cuff study, without focused-eye motion. '
            'Outer garment integration, hand anatomy, small-size cues and full aesthetics require visual review. '
            'Bounded feathering is not an artist foreground layer or proof that seam lines connect.')
    (OUT/'build.json').write_text(json.dumps(meta,indent=2)+'\n',encoding='utf-8');print(json.dumps(meta,indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--grid-only',action='store_true')
    if parser.parse_args().grid_only:
        before,mapped=inputs()
        grid(before,BOX).save(OUT/'source-grid.png')
        grid(mapped,BOX).save(OUT/'mapped-grid.png')
    else:main()
