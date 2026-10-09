"""Restore observed source hair excluded by the generated parent's alpha.

Source visibility and foreground geometry determine restoration permission.
The current patch's defective opacity must not veto real source evidence.
This is exact source RGBA restoration, not inpainting or hidden-layer recovery.
"""
import hashlib

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from canonical import ROOT, load_canonical, bounded_masks
import review_review_v2 as arm
from restore_review_known_hair import specification as restoration_specification

PARENT_HASH = '6A92ACB8FF75F2F77F639ECFF402C1B3AA796AFB88362E66589F850E0C535B49'
def repair(pose):
    before = np.asarray(pose)
    if (pose.mode != 'RGBA' or pose.size != (1205,1306)
            or hashlib.sha256(pose.tobytes()).hexdigest().upper() != PARENT_HASH):
        raise ValueError('Source-hole repair requires the inspected unchanged v4 composition')
    source = np.asarray(load_canonical())
    spec, restoration = arm.specification(), restoration_specification()
    foreground = Image.new('L',pose.size)
    draw = ImageDraw.Draw(foreground)
    draw.polygon(spec['foregroundRightArmPolygon'],fill=255)
    for polygon in spec['preservedForegroundPolygons']:
        draw.polygon(polygon,fill=255)
    protected = np.asarray(foreground.filter(ImageFilter.MaxFilter(13)))>0
    parent_allowed = bounded_masks(pose.size,
        [spec['oldRightArmPolygon'],spec['foregroundRightArmPolygon']],spec['edgeFeatherSourcePx'])[0]
    domain = Image.new('L',pose.size)
    ImageDraw.Draw(domain).polygon(restoration['knownHairPolygon'],fill=255)
    visible = (np.asarray(domain)>0) & parent_allowed & ~protected
    visible &= source[...,3] >= restoration['fullyPaintedAlphaMinimum']
    with Image.open(ROOT/'candidates/phase5/review-art-v3/known-source-mask.png') as image:
        previous_known = np.asarray(image.convert('L'))>0
    if np.any(previous_known & ~visible) or not np.array_equal(before[previous_known],source[previous_known]):
        raise ValueError('Source-hole repair changed the existing source observation boundary')
    holes = visible & ~previous_known
    # Each newly restored pixel has a real visible source, not a guessed RGB.
    # The omitted parent's sub-threshold alpha is the defect, not permission.
    if not holes.any() or np.any(before[...,3][holes] >= 240):
        raise ValueError('Restoration additions are not the inspected alpha-excluded holes')
    result = before.copy()
    result[holes] = source[holes]
    if not np.array_equal(result[~holes],before[~holes]) or np.any(holes & protected):
        raise ValueError('Source-hole repair changed the foreground or exterior')
    return Image.fromarray(result),holes,visible,protected
