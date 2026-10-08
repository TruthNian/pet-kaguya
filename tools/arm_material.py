"""Shared bounded arm cels over locked backing; no recovered-matte claim."""
import math

import numpy as np
from PIL import Image, ImageDraw

from canonical import bounded_artwork
from review_arm_backing import localized_backing,load_generated as backing_art,specification as backing_spec


def project_fixed_crop(mother,raw,expected_size,box):
    """One uniform crop registration, never fit independently to object bounds."""
    if raw.size!=tuple(expected_size):
        raise ValueError('Arm crop raw canvas differs from the recorded framing')
    x0,y0,x1,y1=box
    width,height=x1-x0,y1-y0
    if not (0<=x0<x1<=mother.width and 0<=y0<y1<=mother.height):
        raise ValueError('Arm crop source rectangle lies outside the mother canvas')
    ratio=raw.width/width
    if not math.isfinite(ratio) or abs(raw.height/ratio-height)>1:
        raise ValueError('Arm crop aspect changed; nonuniform fitting is forbidden')
    crop=raw.convert('RGBa').transform((width,height),Image.Transform.AFFINE,
        (ratio,0,0,0,ratio,0),Image.Resampling.BILINEAR).convert('RGBA')
    mapped=mother.copy()
    mapped.paste(crop,(x0,y0))
    return mapped


def localized_arm_pose(mother,generated,spec):
    definition=backing_spec()
    backing,old_allowed=localized_backing(mother,backing_art(),definition)
    pose,new_allowed,_=bounded_artwork(backing,generated,
        [spec['foregroundPolygon']],spec['edgeFeatherSourcePx'])
    # Reject an illegal permission even if this particular crop happens to
    # contain unchanged source pixels there. A no-op repaint is not authority
    # to include the face/body/shoes in a future arm cel.
    for x0,y0,x1,y1 in definition['protectedRects']:
        if np.any(new_allowed[y0:y1,x0:x1]):
            raise ValueError('Arm cel permission overlaps protected face/cape/body/shoes')
    foreground=Image.new('L',mother.size)
    for polygon in definition['preservedForegroundPolygons']:
        ImageDraw.Draw(foreground).polygon(polygon,fill=255)
    protected=np.asarray(foreground)>0
    original,pixels=np.asarray(mother),np.asarray(pose).copy()
    pixels[protected]=original[protected]
    allowed=(old_allowed|new_allowed)&~protected
    changed=np.any(original!=pixels,axis=2)
    if np.any(changed&~allowed):
        raise ValueError('Arm cel repainted outside the bounded old/new regions')
    for x0,y0,x1,y1 in definition['protectedRects']:
        if np.any(changed[y0:y1,x0:x1]):
            raise ValueError('Arm cel touched protected face/cape/body/shoes')
    return Image.fromarray(pixels),allowed
