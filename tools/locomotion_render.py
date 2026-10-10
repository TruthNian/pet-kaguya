"""Direct source-material sampling with a rigid root and world-pinned feet.

This is a frontal 2-D puppet, not inferred mass or artist-layer recovery.
The root is an actor translation; it does not refit the camera or the face.
"""
import numpy as np
from PIL import Image

from build_idle import sample, SUPERSAMPLE
from canonical import clean_cutout
from leg_material import premult, leg_coordinates
from occlusion_material import over
from protocol import WIDTH, HEIGHT
import locomotion_follow as follow
from material_support import LEGACY, ZERO, sample_local


def prepare(data, source, follow_fields=None, *, local_support=LEGACY):
    """Keep known backing separate from the hidden-backing estimate.

    A separately bilinear-filtered P, beta and B does not in general retain
    S=P+(1-beta)B at fractional coordinates. Normalize the *visible backing*
    contribution before filtering, like unassociating a coverage-weighted
    texture. Where no backing was visible, use the existing hidden estimate.
    This is an edge-filtering convention, not newly observed hidden pixels.
    """
    if local_support not in (LEGACY,ZERO):
        raise ValueError('Unknown local material support version')
    cleaned, _ = clean_cutout(source)
    source_pixels = premult(cleaned)
    backing = source_pixels.copy()
    visibility = np.ones(backing.shape[:2], dtype=float)
    x0,y0,x1,y1 = data['box']
    # Apply the existing transparency-only cleanup to original material,
    # not to a moved/quantized raster. Otherwise faint source dust reappears.
    removed=(np.asarray(cleaned)[y0:y1,x0:x1,3]==0)&(np.asarray(source)[y0:y1,x0:x1,3]>0)
    local_backing=data['background'].copy(); local_backing[removed]=0
    paints=[p.copy() for p in data['layers']]
    occlusions=[b.copy() for b in data['occlusions']]
    for paint,beta in zip(paints,occlusions):
        paint[removed]=0; beta[removed]=0
    data=dict(data,layers=paints,occlusions=occlusions)
    backing[y0:y1,x0:x1] = local_backing
    beta = np.sum(occlusions, axis=0)
    if np.any(beta > 1+1e-10):
        raise ValueError('Original leg occlusions must be disjoint')
    visibility[y0:y1,x0:x1] = np.maximum(0,1-beta)
    return dict(data=data, backing=backing, visibility=visibility,
                visibleBacking=backing*visibility[...,None],source=source_pixels,
                followFields=follow_fields,localFilterSupport=local_support)


def relative_offsets(key, direction):
    root = np.asarray(key['rootSourcePx'],dtype=float)
    return [(key[name][0]*direction-root[0], key[name][1]-root[1])
            for name in ('left','right')]


def source_coordinates(x,y,key):
    # Exact rigid translation for head, face, clothes, ornaments and backing.
    rx,ry = key['rootSourcePx']
    return x-rx,y-ry


def evaluate(material, x, y, key, direction, *, normalized_backing=True, rebase_roundoff=True,
             source_fields=None):
    """Evaluate original paint/occlusion at destination points; no posed raster.

    root + (world foot - root) cancels for a planted shoe. Thus a fractional
    root translation cannot introduce an extra moving/softened shoe image.
    The normalized_backing=False route is retained for a regression test of
    the naive fractional neutral-filtering failure, never for production.
    """
    data=material['data']; x0,y0,_,_=data['box']
    qx,qy=source_coordinates(x,y,key)
    if source_fields is not None:
        bx,by = source_fields(qx,qy)
    else:
        bx,by = (follow.coordinates(qx,qy,key,material['followFields'])
                 if material['followFields'] is not None else (qx,qy))
    backing=sample(material['backing'],bx,by)
    if normalized_backing:
        visible=sample(material['visibility'],bx,by)
        known=sample(material['visibleBacking'],bx,by)
        np.divide(known,visible[...,None],out=backing,where=visible[...,None]>1e-12)
    result=backing
    for leg,paint,beta,offset in zip(data['spec']['legs'],data['layers'],data['occlusions'],
                                    relative_offsets(key,direction)):
        sx,sy=leg_coordinates(qx,qy,leg,*offset)
        if source_fields is not None:
            # Apply the same authored source field to paint, occlusion and
            # backing. Warping only B leaves source hair carried by a matte
            # unmoved and breaks the neutral composition at that boundary.
            sx,sy=source_fields(sx,sy)
        support=material['localFilterSupport']
        result=over(sample_local(paint,sx-x0,sy-y0,support),
                    sample_local(beta,sx-x0,sy-y0,support),result)
    if (not np.isfinite(result).all() or np.any(result < -1e-7)
            or np.any(result[...,3] > 255+1e-7)
            or np.any(result[...,:3] > result[...,3:4]+1e-7)):
        raise ValueError('Source-material evaluation produced invalid premultiplied RGBA')
    if rebase_roundoff:
        # Integer channel rounding is discontinuous at exact half levels.
        # Canonicalize only composite roundoff at every pose/coordinate,
        # never return a neutral source raster or skip material evaluation.
        reference=sample(material['source'],bx,by)
        same=np.max(np.abs(result-reference),axis=-1)<1e-10
        result=np.where(same[...,None],reference,result)
    return result


def integration_coordinates(transform, *, actor_y=0):
    yy,xx=np.mgrid[:HEIGHT*SUPERSAMPLE,:WIDTH*SUPERSAMPLE].astype(float)
    return (((xx+.5)/SUPERSAMPLE-transform['x'])/transform['scale']-.5,
            ((yy+.5)/SUPERSAMPLE-transform['y']-actor_y)/transform['scale']-.5)


def quantize(pixels):
    straight=pixels.copy()
    np.divide(straight[...,:3]*255,straight[...,3:4],out=straight[...,:3],where=straight[...,3:4]>0)
    straight[straight[...,3]==0,:3]=0
    return Image.fromarray(np.clip(np.rint(straight),0,255).astype(np.uint8))


def render(material,key,direction,transform,*,normalized_backing=True,terminal=None):
    x,y=integration_coordinates(transform)
    sampled=evaluate(material,x,y,key,direction,normalized_backing=normalized_backing)
    if terminal is not None:
        return terminal(sampled)
    high=quantize(sampled)
    frame=high.convert('RGBa').resize((WIDTH,HEIGHT),Image.Resampling.LANCZOS).convert('RGBA')
    rgba=np.asarray(frame).copy(); rgba[rgba[...,3]==0,:3]=0
    return Image.fromarray(rgba)


def diagnostic_pose(material,key,direction):
    # Full-size inspection only. Native frames NEVER downsample this image.
    height,width=material['backing'].shape[:2]
    output=np.empty((height,width,4),dtype=np.uint8)
    for y0 in range(0,height,64):
        yy,xx=np.mgrid[y0:min(y0+64,height),:width].astype(float)
        output[y0:y0+len(yy)]=np.asarray(quantize(evaluate(material,xx,yy,key,direction)))
    return Image.fromarray(output)


def neutral_evidence(material,source,transform):
    from review_wave import native_frame
    key=dict(rootSourcePx=[0,0],left=[0,0],right=[0,0])
    x,y=integration_coordinates(transform)
    expected=sample(premult(clean_cutout(source)[0]),x,y)
    actual=evaluate(material,x,y,key,1,rebase_roundoff=False)
    within=bool(np.max(np.abs(expected-actual))<1e-10)
    reference=np.asarray(native_frame(source),dtype=int)
    current=np.asarray(render(material,key,1,transform),dtype=int)
    difference=np.abs(reference-current)
    return dict(directSamplerNeutralPremultErrorTolerance=1e-10,
                directSamplerNeutralPremultMatchesWithinTolerance=within,
                directSamplerNeutralRGBAExact=bool(np.array_equal(reference,current)),
                directSamplerNeutralChangedPixels=int(np.any(difference,axis=2).sum()),
                directSamplerNeutralMaximumRGBADifference=int(difference.max()))
