"""Fixed-canvas projection of a face-free current-pose cloth edit.

Only connected sleeve interiors are paint authority. The generator's other
redrawn pixels are explicitly rejected, not passed off as an exact local edit.
"""
import hashlib
import json
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from canonical import ROOT, ACCEPTED_SHA
from guide_review_cloth import OUT, BOX, PARENT_HASH, parent
from review_sleeves import cloth_permission, rgba_hash
from review_review_v2 import comparison
from review_wave import native_frame

GENERATED_SHA='41BAC8EC07B2EF55B9E89382CAA4B5FE1A34F105377E12DADEE291FEF48CB678'
RAW_SIZE=(1254,1254)  # Measured saved output, not the prompt's requested size.


def inputs():
    base=parent()
    path=OUT/'generated.png'
    if hashlib.sha256(path.read_bytes()).hexdigest().upper()!=GENERATED_SHA:
        raise ValueError('Archived cloth material changed')
    with Image.open(path) as image:raw=image.convert('RGBA')
    if raw.size!=RAW_SIZE:
        raise ValueError('Whole square framing changed; object fitting is forbidden')
    # Uniform whole-canvas scale, including the transparent bottom padding.
    square=raw.convert('RGBa').resize((660,660),Image.Resampling.LANCZOS).convert('RGBA')
    mapped=base.copy()
    mapped.paste(square.crop((0,0,660,540)),BOX[:2])
    return base,mapped


def compose(base,mapped):
    _,expected_mapped=inputs()
    if rgba_hash(base)!=PARENT_HASH or rgba_hash(mapped)!=rgba_hash(expected_mapped):
        raise ValueError('Cloth composition inputs are not the recorded crop')
    allowed,protected,parts=cloth_permission(base)
    hard=Image.fromarray(allowed.astype(np.uint8)*255)
    weights=np.asarray(hard.filter(ImageFilter.MinFilter(5)).filter(ImageFilter.GaussianBlur(1))).copy()
    weights[~allowed]=0
    a,b=np.asarray(base),np.asarray(mapped)
    # Cloth material must cover the permission; never import transparency holes.
    # The original cloth is not uniformly opaque (minimum core alpha 228).
    # Measured raw core alpha is >=249, with at most 2 units less coverage
    # than its parent. Reject missing material / greater core coverage loss;
    # do not mistake those 39 semiopaque pixels for actual holes.
    if (np.any((b[...,3]==0)&(weights>0)) or np.any(
            (b[...,3].astype(int)<a[...,3].astype(int)-2)&(weights==255))):
        raise ValueError('Generated cloth does not cover the continuous paint domain')
    w=weights.astype(np.float64)/255
    result=a.copy()
    mixed=np.rint(a[...,:3]*(1-w[...,None])+b[...,:3]*w[...,None]).astype(np.uint8)
    result[allowed,:3]=mixed[allowed]
    material=b.copy();material[...,3]=a[...,3]
    return Image.fromarray(result),allowed,protected,Image.fromarray(weights),Image.fromarray(material),parts


def main():
    base,mapped=inputs()
    pose,allowed,protected,weight,material,parts=compose(base,mapped)
    for name,image in [('pose',pose),('mapped-cloth',material),('blend-weight',weight),
                       ('allowed-mask',Image.fromarray(allowed.astype(np.uint8)*255)),
                       ('protected-mask',Image.fromarray(protected.astype(np.uint8)*255))]:
        image.save(OUT/(name+'.png'))
    frames=[native_frame(base),native_frame(pose)]
    frames[-1].save(OUT/'frame.png')
    for width in (80,113,192,224):
        comparison(frames,width,['current v5','continuous cloth v2']).save(OUT/f'contact-{width}px.png')
    board=Image.new('RGB',(1320,575),'#23252b');draw=ImageDraw.Draw(board)
    for i,(image,label) in enumerate(((base,'current v5'),(pose,'cloth only - same hands / outline'))):
        tile=Image.new('RGBA',(660,540),'#ededed');tile.alpha_composite(image.crop(BOX))
        board.paste(tile.convert('RGB'),(660*i,30));draw.text((660*i+8,10),label,fill='white')
    board.save(OUT/'detail.png')
    a,b,c=np.asarray(base),np.asarray(pose),np.asarray(mapped)
    changed=np.any(a!=b,axis=2);raw_changed=np.any(a!=c,axis=2)
    meta=dict(sourceSha256=ACCEPTED_SHA,parentCompositionVersion='review-art-v5',
        parentPoseRGBAHash=PARENT_HASH,materialGeneratedSha256=GENERATED_SHA,newArtworkGenerated=True,
        rawCanvas=list(RAW_SIZE),sourceCrop=list(BOX),guideCanvas=[660,660],paddingBottomSourcePx=120,
        registration='uniform whole square canvas, no object-bound fitting',
        connectedClothPixels=parts,allowedPixels=int(allowed.sum()),changedPixels=int(changed.sum()),
        rawChangedPixelsOutsidePermission=int((raw_changed&~allowed).sum()),
        changedOutsidePermission=int((changed&~allowed).sum()),parentAlphaPreserved=np.array_equal(a[...,3],b[...,3]),
        protectedForegroundRGBAExact=np.array_equal(a[protected],b[protected]),poseRGBAHash=rgba_hash(pose),
        frameRGBAHash=rgba_hash(frames[-1]),handScaled=False,faceGeometryChanged=False,
        outlineChanged=False,cleanLayerRecoveryClaimed=False,animationBuilt=False,
        visualAcceptance='pending',adopted=True,adoptedIntoDevelopmentOnly=True,
        activeAtlasChanged=True,installed=False,
        limitation='Estimated cloth interiors, not a clean semantic matte or physical fabric simulation; '
                   'outer lines and hands remain the exact current pose; full gesture still unapproved.')
    # NumPy predicates must serialize as ordinary booleans.
    for key in ('parentAlphaPreserved','protectedForegroundRGBAExact'):meta[key]=bool(meta[key])
    (OUT/'build.json').write_text(json.dumps(meta,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(meta,indent=2))


if __name__=='__main__':main()
