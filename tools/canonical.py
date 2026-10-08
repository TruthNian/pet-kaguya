"""Authoritative source guard and conservative transparency-only cleanup."""
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
ACCEPTED_SHA = '65401EFDFEF0205D0CEA30AD08A0F14911C20B1B83468DBB6B3619E7DC89430A'


def load_canonical():
    decision = json.loads((ROOT/'sources/canonical/manifest.json').read_text(encoding='utf-8'))
    if not (decision['approvedAsMotherPose'] and decision['faceShapeLocked']):
        raise ValueError('No approved locked mother pose')
    if decision['fallbackToRejectedCandidatesAllowed'] or decision['facialGeometryRepairAllowed']:
        raise ValueError('Production cannot fallback or repair facial geometry')
    if decision['artwork'] != 'sources/canonical/artwork.png' or decision['sha256'] != ACCEPTED_SHA:
        raise ValueError('Selected source differs from the explicit v3 decision')
    path = ROOT/decision['artwork']
    if hashlib.sha256(path.read_bytes()).hexdigest().upper() != ACCEPTED_SHA:
        raise ValueError('Selected source bytes changed')
    with Image.open(path) as image:
        rgba = image.convert('RGBA')
    if rgba.size != (1205, 1306):
        raise ValueError('Selected source dimensions changed')
    return rgba


def clean_cutout(image):
    """Remove ONLY distant <=8/255 alpha dust; retain all stronger pixels.

    Four source pixels of antialias fringe next to stronger painted content
    are retained. This is not binary thresholding of the character outline.
    """
    pixels = np.asarray(image.convert('RGBA')).copy()
    alpha = pixels[..., 3]
    core = Image.fromarray((alpha > 8).astype(np.uint8)*255)
    nearby = np.asarray(core.filter(ImageFilter.MaxFilter(9))) > 0
    dust = (alpha > 0) & (alpha <= 8) & ~nearby
    removed_alpha = int(alpha[dust].astype(np.uint64).sum())
    pixels[dust] = 0
    invisible_color = (pixels[..., 3] == 0) & np.any(pixels[..., :3] != 0, axis=2)
    invisible_count = int(np.count_nonzero(invisible_color))
    pixels[pixels[..., 3] == 0, :3] = 0
    return Image.fromarray(pixels), dict(distantVeryFaintPixelsRemoved=int(np.count_nonzero(dust)),
        removedOpacitySum=removed_alpha, maximumRemovedAlpha=8, retainedFringeRadius=4,
        paintedPixelsAboveAlpha8PreservedExactly=True, transparentRGBPixelsCleared=invisible_count,
        sourceFileModified=False, faceShapeModified=False)


def camera(image):
    alpha = np.asarray(image)[..., 3] > 8
    yy, xx = np.where(alpha)
    box = [int(xx.min()), int(yy.min()), int(xx.max()+1), int(yy.max()+1)]
    # Same physical camera for every pose. 12 px top reserve for a later hop;
    # floor y=202, chosen from full visible geometry, not faint-alpha noise.
    scale = 190/(box[3]-box[1])
    return dict(scale=scale, x=96-(box[0]+box[2])*scale/2,
                y=202-box[3]*scale, visibleBBox=box, floor=202,
                topReserve=12, cell=[192, 208])


def static_frame(image, transform=None):
    transform = transform or camera(image)
    scale = transform['scale']
    # A uniform camera resize, not independently normalized head/body parts.
    size = (round(image.width*scale), round(image.height*scale))
    reduced = image.convert('RGBa').resize(size, Image.Resampling.LANCZOS).convert('RGBA')
    frame = Image.new('RGBA', (192, 208))
    frame.alpha_composite(reduced, (round(transform['x']), round(transform['y'])))
    pixels = np.asarray(frame).copy()
    pixels[pixels[..., 3] == 0, :3] = 0
    return Image.fromarray(pixels)
