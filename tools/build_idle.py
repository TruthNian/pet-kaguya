"""Actual native six-pose idle from ONLY the accepted mother pose.

Face geometry is an exact rigid translation in source coordinates. Modest
non-face fields act only on authored visible ear/hair regions. This is not
a complete layered skeleton and cannot supply missing arm/gait artwork.
"""
import hashlib
import json
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from canonical import ROOT, ACCEPTED_SHA, load_canonical, clean_cutout, camera
from protocol import DURATIONS, WIDTH, HEIGHT
from animation_output import write_animation

OUT = ROOT/'candidates/phase5/idle'
SUPERSAMPLE = 3


def smooth(start, end, value):
    t = np.clip((value-start)/(end-start), 0., 1.)
    return t*t*(3-2*t)


def specification():
    regions = json.loads((ROOT/'sources/canonical/regions.json').read_text(encoding='utf-8'))
    motion = json.loads((ROOT/'sources/canonical/idle-motion.json').read_text(encoding='utf-8'))
    if regions['sourceSha256'] != ACCEPTED_SHA or regions['canvas'] != [1205, 1306]:
        raise ValueError('Rig is not authored for the selected mother pose')
    if motion['durationsMs'] != DURATIONS[0] or len(motion['keyframes']) != 6:
        raise ValueError('Native idle schedule changed')
    if not motion['faceShapeLocked'] or motion['closedEyeFrames'] != 0:
        raise ValueError('Face or slow blink policy changed')
    return regions, motion


def region_masks(regions):
    masks = {}
    for region in regions['regions']:
        mask = Image.new('L', tuple(regions['canvas']))
        ImageDraw.Draw(mask).polygon(region['polygon'], fill=255)
        # Blur only the coordinate influence; not the artwork pixels.
        masks[region['name']] = np.asarray(mask.filter(ImageFilter.GaussianBlur(10)), dtype=float)/255
    return masks


def sample(array, x, y):
    height, width = array.shape[:2]
    inside = (x >= 0) & (y >= 0) & (x <= width-1) & (y <= height-1)
    clipped_x, clipped_y = np.clip(x, 0, width-1), np.clip(y, 0, height-1)
    ix, iy = np.floor(clipped_x).astype(int), np.floor(clipped_y).astype(int)
    nx, ny = np.minimum(ix+1, width-1), np.minimum(iy+1, height-1)
    fx, fy = clipped_x-ix, clipped_y-iy
    if array.ndim == 3:
        fx, fy, inside = fx[..., None], fy[..., None], inside[..., None]
    return ((array[iy, ix]*(1-fx)+array[iy, nx]*fx)*(1-fy)
            +(array[ny, ix]*(1-fx)+array[ny, nx]*fx)*fy)*inside


def coordinates(x, y, pose, transform, regions, masks):
    # Constant over head/face/torso. Only the lower visible legs accommodate
    # a <=0.5 output-pixel breath, reaching zero before the shoe collars.
    body_weight = 1-smooth(*regions['bodyTransition'], y)
    source_x = x.copy()
    source_y = y-pose['bodyY']/transform['scale']*body_weight
    for region in regions['regions']:
        angle = pose['earAngle'] if region['name'].startswith('ear_') else pose['hairAngle']
        # Mirrored response, never mirrored character art or moon ornament.
        if region['name'].endswith('right'):
            angle = -angle
        angle = math.radians(-angle)
        px, py = region['pivot']
        radius = np.hypot(x-px, y-py)
        weight = sample(masks[region['name']], x, y)*smooth(*region['ramp'], radius)
        # These semantic exclusions are exact, not Gaussian tail assumptions.
        # No nearby hair field may deform a face or rabbit-shoe pixel.
        for x0, y0, x1, y1 in [regions['protectedFace'], *regions['shoeProtectedRects']]:
            distance = np.maximum.reduce([x0-x, x-x1, y0-y, y-y1, np.zeros_like(x)])
            weight *= smooth(0, 24, distance)
        rx = (x-px)*math.cos(angle)-(y-py)*math.sin(angle)+px-x
        ry = (x-px)*math.sin(angle)+(y-py)*math.cos(angle)+py-y
        source_x += rx*weight
        source_y += ry*weight
    return source_x, source_y


def render(image, pose, transform, regions, masks):
    # One geometry evaluation from full-resolution source; a 3x integration
    # grid then one shared terminal downsample, never low-res frame recycling.
    yy, xx = np.mgrid[:HEIGHT*SUPERSAMPLE, :WIDTH*SUPERSAMPLE].astype(float)
    x = ((xx+.5)/SUPERSAMPLE-transform['x'])/transform['scale']-.5
    y = ((yy+.5)/SUPERSAMPLE-transform['y'])/transform['scale']-.5
    sx, sy = coordinates(x, y, pose, transform, regions, masks)
    pixels = np.asarray(image, dtype=float)
    pixels[..., :3] *= pixels[..., 3:4]/255
    sampled = sample(pixels, sx, sy)
    np.divide(sampled[..., :3]*255, sampled[..., 3:4], out=sampled[..., :3], where=sampled[..., 3:4] > 0)
    sampled[sampled[..., 3] == 0, :3] = 0
    high = Image.fromarray(np.clip(np.rint(sampled), 0, 255).astype(np.uint8))
    frame = high.convert('RGBa').resize((WIDTH, HEIGHT), Image.Resampling.LANCZOS).convert('RGBA')
    rgba = np.asarray(frame).copy()
    rgba[rgba[..., 3] == 0, :3] = 0
    return Image.fromarray(rgba)


def main():
    image, cleanup = clean_cutout(load_canonical())
    regions, motion = specification()
    transform = camera(image)
    masks = region_masks(regions)
    frames = [render(image, pose, transform, regions, masks) for pose in motion['keyframes']]
    write_animation(OUT, frames, DURATIONS[0], {6: 0})  # Native legacy extra idle cell.
    metadata = dict(sourceSha256=ACCEPTED_SHA, source='sources/canonical/artwork.png',
        state='idle', generatedFromRejectedSources=False, facialGeometryRepair=False,
        closedEyeFrames=0, durationsMs=DURATIONS[0], totalDurationMs=sum(DURATIONS[0]),
        method='authored native holds; rigid face/upper-body breath, local non-face ear/hair fields',
        sampling='3x coverage integration from high-resolution source, one terminal Lanczos downsample',
        camera=transform, alphaCleanup=cleanup, visualMotionApproval='pending',
        statesInThisArtifact=['idle'], installableFullAtlas=False, installed=False,
        frameHashes=[hashlib.sha256(frame.tobytes()).hexdigest().upper() for frame in frames],
        missingArtwork=regions['missingArtwork'])
    (OUT/'build.json').write_text(json.dumps(metadata, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({k:v for k,v in metadata.items() if k!='frameHashes'}, indent=2))


if __name__ == '__main__':
    main()
