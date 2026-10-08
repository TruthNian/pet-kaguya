"""Estimated source leg mattes and a strictly bounded hidden backing.

The flattened mother has non-opaque paint. Source-over of its cut-out legs
and an inferred background is NOT a lossless neutral decomposition. Measure
that failure; do not special-case zero motion to conceal it.
"""
import hashlib
import json
import math

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from canonical import ROOT, ACCEPTED_SHA, load_canonical
from arm_material import project_fixed_crop
from build_idle import sample

OUT = ROOT/'candidates/phase5/leg-backing-v1'
GENERATED_SHA = 'F4DB57340CF910C3F5A773BEFF3345823C42FBCFFEBD44C12F7E00990EACD93A'


def validate_specification(spec):
    if (spec['sourceSha256'] != ACCEPTED_SHA or spec['generatedSha256'] != GENERATED_SHA
            or spec['sourceCrop'] != [400,850,820,1260] or spec['rawCanvas'] != [1269,1239]
            or spec['editBudget'] != [425,936,810,1240] or spec['maskSupersample'] != 4
            or spec['foregroundMarginSourcePx'] != 3
            or spec['backingExpansionSourcePx'] != 0 or spec['backingFeatherSourcePx'] != 0
            or not spec['inferredMatte'] or spec['losslessNeutralDecomposition']
            or not spec['faceShapeLocked'] or spec['fullRedrawAccepted']
            or spec['visualAcceptance'] != 'pending'):
        raise ValueError('Leg material violates source, crop, permission or candidate boundary')
    if [leg['name'] for leg in spec['legs']] != ['left','right']:
        raise ValueError('Leg material requires two separately named source legs')
    x0,y0,x1,y1 = spec['editBudget']
    for leg in spec['legs']:
        points = np.asarray(leg['foregroundPolygon'],dtype=float)
        if (points.ndim != 2 or points.shape[1] != 2 or len(points) < 3
                or not np.isfinite(points).all() or (points[:,0] < x0+2).any()
                or (points[:,0] > x1-2).any() or (points[:,1] < y0).any()
                or (points[:,1] > y1-2).any()):
            raise ValueError('Leg matte exceeds the explicit lower-body permission')
        for key in ('anchor','knee','ankle'):
            point = np.asarray(leg[key],dtype=float)
            if (point.shape != (2,) or not np.isfinite(point).all()
                    or not x0 < point[0] < x1 or not y0 <= point[1] < 1030):
                raise ValueError('Invalid puppet joint')
        if not y0 == leg['anchor'][1] < leg['knee'][1] < leg['ankle'][1] < 1030:
            raise ValueError('Leg rings must lie below the protected dress hem')
        if leg['bendSign'] not in (-1,1):
            raise ValueError('Invalid puppet bend branch')


def premult(image):
    pixels = np.asarray(image,dtype=float)
    pixels[..., :3] *= pixels[...,3:4]/255
    return pixels


def unpremult(pixels):
    result = pixels.copy()
    np.divide(result[..., :3]*255,result[...,3:4],out=result[..., :3],where=result[...,3:4] > 0)
    result[result[...,3] == 0,:3] = 0
    return Image.fromarray(np.clip(np.rint(result),0,255).astype(np.uint8))


def inputs():
    spec = json.loads((ROOT/'sources/canonical/leg-material.json').read_text(encoding='utf-8'))
    validate_specification(spec)
    path = OUT/'generated.png'
    if hashlib.sha256(path.read_bytes()).hexdigest().upper() != GENERATED_SHA:
        raise ValueError('Generated hidden leg backing changed')
    with Image.open(path) as opened:
        raw = opened.convert('RGBA')
    mother = load_canonical()
    mapped = project_fixed_crop(mother,raw,spec['rawCanvas'],spec['sourceCrop'])
    box = tuple(spec['editBudget'])
    x0,y0,x1,y1 = box
    size = (x1-x0,y1-y0)
    ss = spec['maskSupersample']
    masks = []
    source = premult(mother.crop(box))
    layers = []
    for leg in spec['legs']:
        high = Image.new('L',(size[0]*ss,size[1]*ss))
        points = [((x-x0)*ss,(y-y0)*ss) for x,y in leg['foregroundPolygon']]
        ImageDraw.Draw(high).polygon(points,fill=255)
        # Coverage estimate, not a color-key pretending to recover true layers.
        mask = high.resize(size,Image.Resampling.BOX).filter(ImageFilter.MaxFilter(2*spec['foregroundMarginSourcePx']+1))
        masks.append(mask)
        layers.append(source*np.asarray(mask,dtype=float)[...,None]/255)
    union = Image.fromarray(np.maximum.reduce([np.asarray(mask) for mask in masks]))
    # Do not fill previously empty inter-leg space merely because a polygon
    # margin reaches it. This is a hidden plate, not a new visible hairstyle.
    source_coverage = source[...,3]/255
    allowed = (np.asarray(union) > 0) & (source_coverage > 0)
    # Padding the backing beyond the foreground caused a visible recolored
    # hair/outline rim in the neutral reconstruction. Adopt new backing only
    # under full foreground coverage; keep the existing visible hair outside.
    weight = (np.asarray(union) == 255)*allowed
    mapped_pixels = premult(mapped.crop(box))
    # A raw AI crop can put opaque hair on an originally translucent edge.
    # Bound that edge coverage rather than creating a new opaque hair rim.
    ratio = np.ones(source_coverage.shape)
    np.divide(source[...,3],mapped_pixels[...,3],out=ratio,where=mapped_pixels[...,3] > 0)
    mapped_pixels *= np.minimum(1,ratio)[...,None]
    background = source*(1-weight[...,None])+mapped_pixels*weight[...,None]
    return dict(mother=mother,spec=spec,box=box,mapped=mapped,masks=masks,
                layers=layers,background=background,allowed=allowed)


def inverse_kinematics(leg,dx,dy):
    """A 2-D puppet hypothesis, not recovered anatomy or 3-D projection."""
    anchor,knee,ankle = [np.asarray(leg[key],dtype=float) for key in ('anchor','knee','ankle')]
    lengths = [float(np.linalg.norm(knee-anchor)),float(np.linalg.norm(ankle-knee))]
    target = ankle+np.array([dx,dy])
    vector = target-anchor
    distance = float(np.linalg.norm(vector))
    if not abs(lengths[0]-lengths[1]) < distance <= sum(lengths):
        raise ValueError('Puppet foot target is unreachable; do not stretch bones')
    along = (lengths[0]**2-lengths[1]**2+distance**2)/(2*distance)
    height = math.sqrt(max(0,lengths[0]**2-along**2))
    unit = vector/distance
    perpendicular = np.array([-unit[1],unit[0]])
    target_knee = np.round(anchor+unit*along+perpendicular*height*leg['bendSign'],12)
    return anchor,target_knee,target,lengths


def leg_coordinates(x,y,leg,dx,dy):
    anchor,knee,ankle,_ = inverse_kinematics(leg,dx,dy)
    original = [np.asarray(leg[key],dtype=float) for key in ('anchor','knee','ankle')]
    targets = [anchor,knee,ankle]
    sx,sy = x-dx,y-dy  # Entire cuff/rabbit shoe is one rigid translation.
    for index in range(2):
        a,b = targets[index:index+2]
        oa,ob = original[index:index+2]
        if b[1] <= a[1]:
            raise ValueError('Leg projection folded a ring')
        active = (y >= a[1]) & (y < b[1])
        # C1 displacement between joint rings. A piecewise-linear silhouette
        # produced visibly angular calves; invert this monotone smooth field
        # instead, while still pinning the top and translating the whole shoe.
        length = ob[1]-oa[1]
        delta0,delta1 = a[1]-oa[1],b[1]-ob[1]
        if 1+min(0,delta1-delta0)*1.5/length <= .5:
            raise ValueError('Leg smooth projection compresses/folds a ring')
        q = np.clip((y-a[1])/(b[1]-a[1]),0,1)
        for _ in range(6):
            weight = q*q*(3-2*q)
            value = oa[1]+length*q+delta0+(delta1-delta0)*weight
            derivative = length+(delta1-delta0)*6*q*(1-q)
            q = np.clip(q-(value-y)/derivative,0,1)
        weight = q*q*(3-2*q)
        sx = np.where(active,x-((a[0]-oa[0])*(1-weight)+(b[0]-ob[0])*weight),sx)
        sy = np.where(active,oa[1]+q*length,sy)
    above = y < anchor[1]
    return np.where(above,x,sx),np.where(above,y,sy)


def composite(data,offsets):
    x0,y0,x1,y1 = data['box']
    yy,xx = np.mgrid[y0:y1,x0:x1].astype(float)
    result = data['background'].copy()
    active = data['allowed'].copy()
    for leg,layer,offset in zip(data['spec']['legs'],data['layers'],offsets):
        sx,sy = leg_coordinates(xx,yy,leg,*offset)
        foreground = sample(layer,sx-x0,sy-y0)
        foreground[foreground[...,3] < 1e-9] = 0
        active |= foreground[...,3] > 0
        result = foreground+result*(1-foreground[...,3:4]/255)
    image = data['mother'].copy()
    pixels = np.asarray(data['mother'].crop(data['box'])).copy()
    pixels[active] = np.asarray(unpremult(result))[active]
    image.paste(Image.fromarray(pixels),(x0,y0))
    return image


def main():
    data = inputs()
    background = data['mother'].copy()
    background.paste(unpremult(data['background']),data['box'][:2])
    background.save(OUT/'bounded-background.png')
    for leg,mask,layer in zip(data['spec']['legs'],data['masks'],data['layers']):
        mask.save(OUT/f"{leg['name']}-estimated-mask.png")
        unpremult(layer).save(OUT/f"{leg['name']}-source-layer.png")
    neutral = composite(data,[(0,0),(0,0)])
    neutral.save(OUT/'neutral-reconstruction.png')
    before,after = np.asarray(data['mother']),np.asarray(neutral)
    changed = np.any(before != after,axis=2)
    box = data['box'];x0,y0,x1,y1 = box
    allowed = np.zeros(changed.shape,dtype=bool)
    allowed[y0:y1,x0:x1] = data['allowed']
    error = np.abs(before.astype(int)-after.astype(int))
    region_error = error[y0:y1,x0:x1]
    visual_error = np.abs(premult(data['mother'].crop(box))-premult(neutral.crop(box)))
    from review_wave import native_frame
    native_original,native_neutral = native_frame(data['mother']),native_frame(neutral)
    native_error = np.abs(premult(native_original)-premult(native_neutral))
    metadata = dict(sourceSha256=ACCEPTED_SHA,generatedSha256=GENERATED_SHA,
        sourceCrop=data['spec']['sourceCrop'],rawCanvas=data['spec']['rawCanvas'],
        editBudget=list(box),cropProjection='uniform width-derived scale; fixed source crop, no object-bounds fit',
        inferredMatte=True,losslessNeutralDecomposition=False,
        originalHeadFaceAndDressAbove936RGBAExact=bool(np.array_equal(before[:936],after[:936])),
        neutralChangedPixels=int(changed.sum()),neutralChangedPixelsOutsideBackingPermission=int((changed&~allowed).sum()),
        neutralLowerBudgetMeanAbsoluteRGBAError=round(float(region_error.mean()),9),
        neutralLowerBudgetMaximumRGBAError=int(region_error.max()),
        neutralLowerBudgetMaximumAlphaError=int(region_error[...,3].max()),
        neutralLowerBudgetMeanAbsolutePremultRGBAError=round(float(visual_error.mean()),9),
        neutralLowerBudgetMaximumPremultRGBAError=round(float(visual_error.max()),9),
        neutralLowerBudgetPremultRGBAError99Percentile=np.round(np.percentile(visual_error,99,axis=(0,1)),9).tolist(),
        neutralNativeMeanAbsolutePremultRGBAError=round(float(native_error.mean()),9),
        neutralNativeMaximumPremultRGBAError=round(float(native_error.max()),9),
        neutralNativeChangedPixels=int(np.any(np.asarray(native_original)!=np.asarray(native_neutral),axis=2).sum()),
        errorStatisticsDecimalPlaces=9,
        fullRedrawAccepted=False,facialGeometryRepair=False,visualAcceptance='pending',
        installableFullAtlas=False,installed=False,
        limitations=['hand-traced silhouette can include or omit hair/antialias at the cut edge',
                     'nonopaque flattened source cannot be declared losslessly recovered into author layers',
                     'background generated crop was redrawn; only bounded old-leg regions adopted',
                     'three-source-pixel foreground margin includes original outlines but may carry adjacent hair fringe',
                     'backing uses only full estimated foreground coverage; residual boundary pixels are not a clean matte',
                     'puppet joint locations and frontal projection are hypotheses, not source anatomy'])
    (OUT/'build.json').write_text(json.dumps(metadata,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(metadata,indent=2))


if __name__ == '__main__':
    main()
