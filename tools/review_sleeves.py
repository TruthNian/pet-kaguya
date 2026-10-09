"""Complete connected cloth-surface study; not automatic pose adoption.

Reuse the archived face-free artwork. Follow the currently painted green
cloth instead of arbitrary interior polygons that transect crease paths.
This color/geometry mask is inspected patch permission, not a recovered rig.
"""
from collections import deque
import hashlib
import json

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from canonical import ROOT, ACCEPTED_SHA, load_canonical
from review_structure import inputs as material_inputs, GENERATED_SHA
from review_review_v2 import specification as right_spec, comparison
from review_arm_backing import specification as left_spec
from review_wave import native_frame

OUT = ROOT/'candidates/phase5/review-sleeves-v1'
PARENT_HASH = '6A92ACB8FF75F2F77F639ECFF402C1B3AA796AFB88362E66589F850E0C535B49'
ENVELOPES = [
    [(334,678),(369,660),(418,635),(454,620),(449,657),(441,699),
     (427,752),(406,809),(387,858),(373,824),(348,779),(341,737)],
    [(701,639),(746,632),(781,650),(810,691),(818,744),(832,805),
     (851,864),(838,883),(797,857),(755,834),(713,804),(677,776),
     (643,750),(616,736),(596,694),(634,677),(666,657)],
]
SEEDS = [(377,740),(782,753)]


def rgba_hash(image):
    return hashlib.sha256(image.tobytes()).hexdigest().upper()


def inputs():
    load_canonical()
    with Image.open(ROOT/'candidates/phase5/review-art-v4/pose.png') as image:
        parent = image.convert('RGBA')
    if rgba_hash(parent) != PARENT_HASH:
        raise ValueError('Sleeve study requires the current unclipped-hand parent')
    _, _, mapped = material_inputs()
    return parent, mapped


def component(binary, seed):
    x,y = seed
    if not binary[y,x]:
        raise ValueError('Recorded cloth seed is no longer within green material')
    found = np.zeros(binary.shape,dtype=bool)
    found[y,x] = True
    queue = deque([(x,y)])
    while queue:
        x,y = queue.popleft()
        for nx,ny in ((x-1,y),(x+1,y),(x,y-1),(x,y+1)):
            if (0<=nx<binary.shape[1] and 0<=ny<binary.shape[0]
                    and binary[ny,nx] and not found[ny,nx]):
                found[ny,nx] = True
                queue.append((nx,ny))
    return found


def fill_holes(binary):
    """Fill only enclosed gaps; exterior remains exterior."""
    exterior = np.zeros(binary.shape,dtype=bool)
    queue = deque()
    for x in range(binary.shape[1]):
        for y in (0,binary.shape[0]-1):
            if not binary[y,x] and not exterior[y,x]:
                exterior[y,x] = True
                queue.append((x,y))
    for y in range(binary.shape[0]):
        for x in (0,binary.shape[1]-1):
            if not binary[y,x] and not exterior[y,x]:
                exterior[y,x] = True
                queue.append((x,y))
    while queue:
        x,y = queue.popleft()
        for nx,ny in ((x-1,y),(x+1,y),(x,y-1),(x,y+1)):
            if (0<=nx<binary.shape[1] and 0<=ny<binary.shape[0]
                    and not binary[ny,nx] and not exterior[ny,nx]):
                exterior[ny,nx] = True
                queue.append((nx,ny))
    return ~exterior


def study(parent, mapped, continuous=True):
    if rgba_hash(parent)!=PARENT_HASH:
        raise ValueError('Cannot replace the current parent silently')
    _, expected = inputs()
    if rgba_hash(mapped)!=rgba_hash(expected):
        raise ValueError('Cannot replace archived cloth material silently')
    a,b = np.asarray(parent),np.asarray(mapped)
    rgb = a[...,:3].astype(np.int16)
    # Keep dark internal green creases too, not just bright flat cloth. This
    # test is still color evidence, not semantic layer recovery.
    green = ((rgb[...,1]-rgb[...,0]>=-4) & (rgb[...,1]-rgb[...,2]>12)
             & (rgb.max(axis=2)>60) & (a[...,3]>0))
    raw = b[...,:3].astype(np.int16)
    raw_green = ((raw[...,1]-raw[...,0]>=-8) & (raw[...,1]-raw[...,2]>10))
    protected = Image.new('L',parent.size)
    draw = ImageDraw.Draw(protected)
    for points in left_spec()['preservedForegroundPolygons']+right_spec()['preservedForegroundPolygons']:
        draw.polygon(points,fill=255)
    # Both complete hands remain untouched, including the restored fingertips.
    draw.rectangle((432,626,621,738),fill=255)
    draw.rectangle((510,568,712,664),fill=255)
    protection = np.asarray(protected)>0
    allowed = np.zeros(green.shape,dtype=bool)
    parts = []
    for envelope,seed in zip(ENVELOPES,SEEDS):
        mask = Image.new('L',parent.size)
        ImageDraw.Draw(mask).polygon(envelope,fill=255)
        envelope_mask = np.asarray(mask)>0
        cloth = component(green & envelope_mask & ~protection,seed)
        if continuous:
            # Close narrow crease cuts and enclosed color islands before
            # selecting a single cloth surface. Do this on a small crop, not
            # the full 1.57M-pixel canvas. Geometry/foreground protection is
            # re-applied afterwards; morphology is not extra permission.
            points = np.asarray(envelope)
            x0,y0 = points.min(axis=0)-6
            x1,y1 = points.max(axis=0)+7
            crop = Image.fromarray(cloth[y0:y1,x0:x1].astype(np.uint8)*255)
            closed = crop.filter(ImageFilter.MaxFilter(9)).filter(ImageFilter.MinFilter(9))
            cloth[y0:y1,x0:x1] = fill_holes(np.asarray(closed)>0)
            cloth &= envelope_mask & ~protection
        # A shared crease domain, not scattered independent interior patches.
        allowed |= cloth if continuous else cloth & raw_green
        parts.append(int(cloth.sum()))
    hard = Image.fromarray(allowed.astype(np.uint8)*255)
    # Inward edge ramp: no color leaks into hair, cuffs or accessories.
    inner = hard.filter(ImageFilter.MinFilter(5))
    weights = np.asarray(inner.filter(ImageFilter.GaussianBlur(1.0))).copy()
    weights[~allowed] = 0
    # All changed pixels retain the existing alpha, including sleeve outline.
    result = a.copy()
    w = weights.astype(np.float64)/255
    mixed = np.rint(a[...,:3]*(1-w[...,None])+b[...,:3]*w[...,None]).astype(np.uint8)
    result[allowed,:3] = mixed[allowed]
    material = b.copy()
    material[...,3] = a[...,3]
    return Image.fromarray(result),allowed,protection,Image.fromarray(weights),Image.fromarray(material),parts


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    parent,mapped = inputs()
    failed,failed_allowed,_,_,_,_ = study(parent,mapped,continuous=False)
    failed.save(OUT/'failed-pixel-selection.png')
    Image.fromarray(failed_allowed.astype(np.uint8)*255).save(OUT/'failed-pixel-mask.png')
    pose,allowed,protected,weight,material,parts = study(parent,mapped)
    for name,image in [('pose',pose),('blend-weight',weight),('mapped-cloth',material),
                       ('allowed-mask',Image.fromarray(allowed.astype(np.uint8)*255)),
                       ('protected-mask',Image.fromarray(protected.astype(np.uint8)*255))]:
        image.save(OUT/(name+'.png'))
    frames = [native_frame(parent),native_frame(mapped),native_frame(pose)]
    frames[-1].save(OUT/'frame.png')
    for width in (80,113,192,224):
        comparison(frames,width,['current v4','raw NOT adopted','whole-surface study']).save(OUT/f'contact-{width}px.png')
    detail = Image.new('RGB',(1200,305),'#23252b')
    draw = ImageDraw.Draw(detail)
    for i,(image,label) in enumerate(zip([parent,mapped,pose],['current v4','raw NOT adopted','connected-cloth study'])):
        tile = Image.new('RGBA',(600,405),'#ededed')
        tile.alpha_composite(image.crop((300,575,900,980)))
        detail.paste(tile.resize((400,270),Image.Resampling.LANCZOS).convert('RGB'),(400*i,30))
        draw.text((400*i+4,9),label,fill='white')
    detail.save(OUT/'detail.png')
    a,b = np.asarray(parent),np.asarray(pose)
    changed = np.any(a!=b,axis=2)
    meta = dict(sourceSha256=ACCEPTED_SHA,parentCompositionVersion='review-art-v4',parentPoseRGBAHash=PARENT_HASH,
        materialGeneratedSha256=GENERATED_SHA,materialSource='candidates/phase5/review-structure-v1/generated.png',
        newArtworkGenerated=False,sourceCrop=[300,500,960,1040],canvas=[1205,1306],
        envelopes=ENVELOPES,seeds=SEEDS,connectedClothPixels=parts,allowedPixels=int(allowed.sum()),
        changedPixels=int(changed.sum()),changedOutsidePermission=int((changed&~allowed).sum()),
        parentAlphaPreserved=bool(np.array_equal(a[...,3],b[...,3])),
        protectedForegroundRGBAExact=bool(np.array_equal(a[protected],b[protected])),
        poseRGBAHash=rgba_hash(pose),frameRGBAHash=rgba_hash(frames[-1]),
        maskMethod='Connected cloth, 4px closing and enclosed-gap fill; recorded envelope/protection re-applied; 2px erosion and 1px Gaussian inward ramp',
        failedPixelSelectionRetained=True,
        isolatedCreaseSurfacePolygons=False,cleanLayerRecoveryClaimed=False,handScaled=False,
        facialGeometryRepair=False,articulatedArmBuilt=False,animationBuilt=False,
        visualAcceptance='pending',adopted=False,activeAtlasChanged=False,installed=False,
        limitation='Same-coordinate whole cloth color study, not registered cloth geometry or complete seam/volume approval. '
            'Color-derived permission is not a clean semantic matte; preserved boundary lines can still disagree with new folds.')
    (OUT/'build.json').write_text(json.dumps(meta,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(meta,indent=2))


if __name__=='__main__':
    main()
