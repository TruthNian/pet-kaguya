"""Face-free hidden-hair plate study; never a replacement character pose."""
import hashlib
import json
import sys

import numpy as np
from PIL import Image

from canonical import ROOT, ACCEPTED_SHA, load_canonical
from arm_material import project_fixed_crop

OUT = ROOT/'candidates/phase5/source-arm-backing-v2'
BOX = (200, 500, 712, 1012)
PROMPT = """Use case: precise-object-edit
Asset type: hidden-background plate for a layered 2D sprite, NOT a finished character pose.
Input images: Image 1 is the edit target, a square 512x512 face-free crop of the approved sprite.
Primary request: Remove ONLY the viewer-left arm, its hand, and its long green sleeve with the cream cuff and red upper-arm cloth. Fill the removed area with the continuing golden hair that lies behind the sleeve and hand. The existing hand is at the left middle of the crop; the green sleeve hangs down the left-middle. Remove the old dark sleeve/hand outline and its antialias fringe too.
Style/medium: Match the existing softly shaded anime illustration, curved fine golden strands and painterly highlights/shadows, not flat yellow.
Constraints: Keep the exact square crop, scale, placement and camera. Preserve the already visible golden hair, its existing outer silhouette, light and strand direction. Preserve the shoulder cape at the top, cream/gold front hair lock, moon ornament, red torso/dress at the right and all other existing material. Continue nearby hair shading naturally across the newly revealed area. Preserve genuine transparency outside the original silhouette. No face, new arm, new hand, new sleeve, text, watermark or other elements. Do not recenter, enlarge or redesign anything.
"""


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def prepare():
    OUT.mkdir(parents=True, exist_ok=True)
    crop = load_canonical().crop(BOX)
    crop.save(OUT/'input.png')
    (OUT/'prompt.txt').write_text(PROMPT, encoding='utf-8')
    record = dict(sourceSha256=ACCEPTED_SHA, sourceCrop=list(BOX),
        inputSha256=digest(OUT/'input.png'), inputSize=list(crop.size),
        editMode='built-in image_gen', role='hidden hair only',
        wholeRedrawAdopted=False, adopted=False, installed=False)
    (OUT/'input.json').write_text(json.dumps(record, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(record, indent=2))


def load_projected():
    record = json.loads((OUT/'input.json').read_text(encoding='utf-8'))
    if record['sourceSha256'] != ACCEPTED_SHA or record['sourceCrop'] != list(BOX):
        raise ValueError('Hidden plate source/camera changed')
    expected = json.loads((OUT/'generated.json').read_text(encoding='utf-8'))
    if digest(OUT/'generated.png') != expected['sha256']:
        raise ValueError('Generated plate differs from its archived hash')
    with Image.open(OUT/'generated.png') as image:
        raw = image.convert('RGBA')
    return project_fixed_crop(load_canonical(), raw, expected['size'], BOX)


def main():
    mother = load_canonical()
    projected = load_projected()
    # An unbounded generated crop is diagnostic only. The source-arm study
    # uses it solely within its estimated old-arm mask, retains mother alpha,
    # and restores known source outside that mask/protected geometry.
    projected.save(OUT/'projected-NOT-a-pose.png')
    a, b = np.asarray(mother), np.asarray(projected)
    print(json.dumps(dict(rawChangedPixels=int(np.any(a != b, axis=2).sum()),
        uniformCropProjection=True, adopted=False, installableFullAtlas=False), indent=2))


if __name__ == '__main__':
    prepare() if '--prepare' in sys.argv else main()
