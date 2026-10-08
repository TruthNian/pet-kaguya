"""Same-coordinate review of a requested jaw-only edit; never builds a pet.

One transform is derived from v2 and reused verbatim for v3. Alpha threshold
8 chooses the framing only: it does not erase, clamp, or recolor artwork.
Pixel differences disprove exact preservation, not aesthetic acceptability.
"""
from pathlib import Path
import argparse
import hashlib
import json

import numpy as np
from PIL import Image, ImageDraw
from prepare_identity import load_source
from protocol import WIDTH, HEIGHT, crop
from review_canonical import bbox_alpha, composite

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'candidates/phase4/canonical-v3'
# Broad diagnostic region, not a segmentation mask or license to repaint it.
JAW_ROI = (395, 360, 815, 465)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def shared_previews(before, after, reference):
    box = bbox_alpha(before, 8)
    refbox = bbox_alpha(reference)
    scale = (refbox[3]-refbox[1])/(box[3]-box[1])
    # Keep both entire canvases, including faint pixels; no independent fit.
    common = (max(before.width, after.width), max(before.height, after.height))
    size = (round(common[0]*scale), round(common[1]*scale))
    x = round((refbox[0]+refbox[2])/2-(box[0]+box[2])*scale/2)
    y = round(refbox[3]-box[3]*scale)
    frames = []
    for image in (before, after):
        padded = Image.new('RGBA', common)
        padded.paste(image, (0, 0))
        reduced = padded.convert('RGBa').resize(size, Image.Resampling.LANCZOS).convert('RGBA')
        frame = Image.new('RGBA', (WIDTH, HEIGHT))
        frame.alpha_composite(reduced, (x, y))
        pixels = np.asarray(frame).copy()
        pixels[pixels[..., 3] == 0, :3] = 0
        frames.append(Image.fromarray(pixels))
    return frames, dict(framingAlphaThreshold=8, referenceBBox=list(refbox),
                       v2VisibleBBox=list(box), commonInputCanvas=list(common),
                       uniformScale=scale, paste=[x, y], resizedSize=list(size),
                       independentSubjectOrFaceFitting=False, artworkAlphaModified=False)


def edit_diagnostics(before, after):
    height, width = max(before.height, after.height), max(before.width, after.width)
    arrays = []
    for image in (before, after):
        padded = np.zeros((height, width, 4), dtype=np.uint8)
        padded[:image.height, :image.width] = np.asarray(image)
        arrays.append(padded)
    a, b = arrays
    outside = np.ones((height, width), dtype=bool)
    x0, y0, x1, y1 = JAW_ROI
    outside[y0:y1, x0:x1] = False
    visible = np.maximum(a[..., 3], b[..., 3]) > 64
    checked = visible & outside
    changed = np.any(a != b, axis=2)
    # This is a strict requested-invariant check, not a perceptual score.
    changed_count = int(np.count_nonzero(changed & checked))
    checked_count = int(np.count_nonzero(checked))
    metrics = dict(inputCanvasSizes=[list(before.size), list(after.size)],
                   sameCanvasSize=before.size == after.size, jawDiagnosticROI=list(JAW_ROI),
                   outsideROIAlphaThreshold=64, outsideROICheckedPixels=checked_count,
                   outsideROIChangedPixels=changed_count,
                   outsideROIChangedFraction=changed_count/checked_count,
                   outsideROIMeanAbsoluteRGBA=float(np.abs(a.astype(float)-b.astype(float))[checked].mean()),
                   exactlyJawOnly=before.size == after.size and changed_count == 0,
                   interpretation='strict non-jaw preservation failed; not an aesthetic quality score')
    for name, image in [('v2', before), ('v3', after)]:
        alpha = np.asarray(image)[..., 3]
        metrics[name] = dict(alphaBBoxes={str(t):list(bbox_alpha(image, t)) for t in (0, 8, 64, 128, 240)},
                             veryFaintAlphaPixels=int(np.count_nonzero((alpha > 0) & (alpha <= 8))))
    return metrics


def comparison(images, width, filename, edited_label='v3 jaw try'):
    height = round(width*HEIGHT/WIDTH)
    board = Image.new('RGB', (3*(width+20), 2*(height+28)), '#23252b')
    draw = ImageDraw.Draw(board)
    for row, background in enumerate(('#23252b', '#f1f0ee')):
        for col, (label, image) in enumerate(zip(('original', 'v2 round', edited_label), images)):
            x, y = col*(width+20), row*(height+28)
            draw.text((x+3, y+3), label, fill='white')
            board.paste(composite(image.resize((width, height), Image.Resampling.NEAREST), background), (x+10, y+24))
    board.save(filename)


def main(candidate='canonical-v3'):
    out = ROOT/'candidates/phase4'/candidate
    version = candidate.removeprefix('canonical-')
    before_path = ROOT/'candidates/phase4/canonical-v2/artwork.png'
    after_path = out/'artwork.png'
    before, after = [Image.open(p).convert('RGBA') for p in (before_path, after_path)]
    original = crop(load_source(), 0, 0)
    (v2, v3), transform = shared_previews(before, after, original)
    out.mkdir(parents=True, exist_ok=True)
    v2.save(out/'before-front.png')
    v3.save(out/'front.png')
    for width in (80, 113, 192, 224):
        comparison((original, v2, v3), width, out/f'comparison-{width}px.png', 'v3 jaw try' if version=='v3' else 'v4 generated')
    face_box = (53, 25, 141, 82)
    faces = Image.new('RGB', (3*440, 310), '#23252b')
    draw = ImageDraw.Draw(faces)
    for col, (label, image) in enumerate(zip(('original: shared coordinates', 'v2: rounder lower face', f'{version}: attempted jaw-only edit'), (original, v2, v3))):
        draw.text((col*440+6, 3), label, fill='white')
        faces.paste(composite(image.crop(face_box), '#23252b').resize((440, 285), Image.Resampling.NEAREST), (col*440, 25))
    faces.save(out/'face-comparison.png')
    raw_faces = Image.new('RGB', (900, 250), '#23252b')
    for i, image in enumerate((before, after)):
        raw_faces.paste(composite(image.crop((380, 230, 830, 480)), '#23252b'), (i*450, 0))
    raw_faces.save(out/'raw-face-comparison.png')
    metadata = dict(artworkSha256=sha(after_path), targetV2Sha256=sha(before_path),
                    generationMode='built-in image_gen edit: v2 target + original proportion reference',
                    requestedScope='lower cheeks/jaw only, all other content unchanged',
                    actualScope='small full-figure redraw/resampling; strict non-jaw invariants failed',
                    userFeedbackV2='Looks okay, but is the face too round? (tentative, not final approval)',
                    userApprovalV3='pending', adoptedForAnimation=False, animationBuilt=False,
                    installed=False, nativeResolutionChanged=False, sharedPreviewTransform=transform,
                    editDiagnostics=edit_diagnostics(before, after))
    if version=='v4':
        metadata.pop('userApprovalV3')
        metadata['userApprovalV4']='generated-artwork direction accepted; exact file clarification pending'
        metadata['requestedScope']='more noticeable lower-cheek convergence, soft short chin'
        metadata['actualScope']='small full-figure redraw; requested further cheek convergence not visibly achieved'
    decision_path = ROOT/'sources/canonical/manifest.json'
    if decision_path.is_file():
        decision = json.loads(decision_path.read_text(encoding='utf-8'))
        if decision['candidate']==candidate and decision['sha256']==metadata['artworkSha256']:
            metadata[f'userApproval{version.upper()}']='accepted as mother-pose; face shape locked by explicit user choice'
            metadata['adoptedForAnimation']=True
            metadata['approvalDoesNotMeanCompletedAnimation']=True
    (out/'review.json').write_text(json.dumps(metadata, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(metadata, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--candidate', choices=['canonical-v3', 'canonical-v4'], default='canonical-v3')
    main(parser.parse_args().candidate)
