"""Compare visible-hair-only constraints with the historical all-edge solve.

An occluder is not an observation of the hidden hair. Keep the current v4
pose, alpha, hands and sleeves; replace RGB only in the already annotated
unknown hair. This estimates continuity, not missing strand topology.
"""
import hashlib
import json

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from canonical import ROOT, ACCEPTED_SHA, load_canonical
from visible_hair_boundary import solve
from review_wave import native_frame
from review_review_v2 import comparison

OUT = ROOT/'candidates/phase5/review-hair-boundary-v1'
PARENT_HASH = '6A92ACB8FF75F2F77F639ECFF402C1B3AA796AFB88362E66589F850E0C535B49'
MATERIAL_HASH = '8618A3A73301ED7A3B29D63983878159C7B35D39BA33E465186584C539E32570'
BOX = (775, 569, 960, 1002)


def rgba_hash(image):
    return hashlib.sha256(image.tobytes()).hexdigest().upper()


def recorded_diagnostics(diagnostics):
    # Convergence uses the actual residual in solve(). This is only portable
    # JSON display precision, not a weaker solver tolerance or pixel rounding.
    return dict(diagnostics, relativeResidual=float(f"{diagnostics['relativeResidual']:.5g}"),
                residualDisplaySignificantDigits=5)


def inputs():
    source = load_canonical()
    with Image.open(ROOT/'candidates/phase5/review-art-v4/pose.png') as image:
        parent = image.convert('RGBA')
    with Image.open(ROOT/'candidates/phase5/review-art-v2/pose.png') as image:
        material = image.convert('RGBA')
    if rgba_hash(parent) != PARENT_HASH or rgba_hash(material) != MATERIAL_HASH:
        raise ValueError('Hair-boundary comparison requires the exact recorded poses')
    masks = {}
    for key, filename in (('known', 'known-source-mask'), ('unknown', 'unknown-interior-mask'),
                          ('protected', 'protected-foreground-mask')):
        with Image.open(ROOT/f'candidates/phase5/review-art-v3/{filename}.png') as image:
            masks[key] = np.asarray(image.convert('L')) > 0
    known, unknown, protected = (masks[key] for key in ('known', 'unknown', 'protected'))
    if (known.shape != (1306, 1205) or int(known.sum()) != 2931 or int(unknown.sum()) != 31552
            or np.any(known & unknown) or np.any((known | unknown) & protected)
            or not np.array_equal(np.asarray(parent)[known], np.asarray(source)[known])):
        raise ValueError('Hair permission or actually observed mother pixels changed')
    x0, y0, x1, y1 = BOX
    exterior = unknown.copy()
    exterior[y0+1:y1-1, x0+1:x1-1] = False
    if exterior.any():
        raise ValueError('Unknown hair exceeds the interior solve crop')
    return parent, material, masks


def anchored_unknown(known, unknown):
    """Leave disconnected unknown islands alone; never invent an anchor."""
    x0, y0, x1, y1 = BOX
    domain, observed = unknown[y0:y1, x0:x1], known[y0:y1, x0:x1]
    seen = np.zeros(domain.shape, dtype=bool)
    eligible = np.zeros_like(seen)
    components = []
    for sy, sx in zip(*np.nonzero(domain)):
        if seen[sy, sx]:
            continue
        stack = [(int(sy), int(sx))]
        seen[sy, sx] = True
        points, anchors = [], 0
        while stack:
            y, x = stack.pop()
            points.append((y, x))
            for ny, nx in ((y-1,x), (y+1,x), (y,x-1), (y,x+1)):
                if not (0 <= ny < domain.shape[0] and 0 <= nx < domain.shape[1]):
                    continue
                anchors += int(observed[ny, nx])
                if domain[ny, nx] and not seen[ny, nx]:
                    seen[ny, nx] = True
                    stack.append((ny, nx))
        yy, xx = np.asarray(points).T
        if anchors:
            eligible[yy, xx] = True
        components.append(dict(pixels=len(points), observedAnchorEdges=anchors,
                               box=[int(xx.min()+x0),int(yy.min()+y0),int(xx.max()+x0+1),int(yy.max()+y0+1)]))
    result = np.zeros(unknown.shape, dtype=bool)
    result[y0:y1, x0:x1] = eligible
    return result, components


def revise(parent, material, known, unknown):
    """No foreground/exterior values enter the hidden RGB equation."""
    x0, y0, x1, y1 = BOX
    before = np.asarray(parent)
    eligible, components = anchored_unknown(known, unknown)
    if not eligible.any():
        raise ValueError('No unknown hair component has a real source anchor')
    revised, diagnostics = solve(before[y0:y1, x0:x1], np.asarray(material)[y0:y1, x0:x1],
                                 eligible[y0:y1, x0:x1], known[y0:y1, x0:x1])
    diagnostics['components'] = components
    result = before.copy()
    result[y0:y1, x0:x1] = revised
    if (not np.array_equal(result[~unknown], before[~unknown])
            or not np.array_equal(result[..., 3], before[..., 3])):
        raise ValueError('Hair-only RGB solve changed the exterior or alpha')
    return Image.fromarray(result), diagnostics, eligible


def write_held_structure():
    """Refresh actual current cels without rerunning the unrelated hair solver."""
    held_frames=[]
    for name in ('idle','waiting','review'):
        folder=ROOT/f'candidates/phase5/{name}'
        metadata=json.loads((folder/'build.json').read_text(encoding='utf-8'))
        with Image.open(folder/'strip.webp') as opened:
            first=opened.convert('RGBA').crop((0,0,192,208))
        if metadata['sourceSha256']!=ACCEPTED_SHA or rgba_hash(first)!=metadata['frameHashes'][0]:
            raise ValueError('Held structure contact must show actual current cels')
        held_frames.append(first)
    comparison(held_frames,224,['current idle','current waiting','current review']).save(OUT/'current-held-structure-224px.png')


def main():
    parent, material, masks = inputs()
    pose, diagnostics, eligible = revise(parent, material, masks['known'], masks['unknown'])
    OUT.mkdir(parents=True, exist_ok=True)
    pose.save(OUT/'pose.png')
    frame = native_frame(pose)
    frame.save(OUT/'frame.png')
    for name, mask in masks.items():
        Image.fromarray(mask.astype(np.uint8)*255).save(OUT/f'{name}-mask.png')
    Image.fromarray(eligible.astype(np.uint8)*255).save(OUT/'eligible-unknown-mask.png')
    ring = np.asarray(Image.fromarray(masks['unknown'].astype(np.uint8)*255)
                      .filter(ImageFilter.MaxFilter(3))) > 0
    unobserved = ring & ~masks['unknown'] & ~masks['known']
    Image.fromarray(unobserved.astype(np.uint8)*255).save(OUT/'excluded-boundary-mask.png')
    frames = [native_frame(load_canonical()), native_frame(parent), frame]
    for width in (80, 113, 192, 224):
        comparison(frames, width, ['mother v3', 'current v4', 'visible anchors only']).save(OUT/f'contact-{width}px.png')
    write_held_structure()
    board = Image.new('RGB', (660, 480), '#23252b')
    draw = ImageDraw.Draw(board)
    for index, (image, label) in enumerate(zip((load_canonical(), parent, pose),
                                              ('mother v3', 'current v4', 'visible anchors only'))):
        tile = Image.new('RGBA', (220, 450), '#ededed')
        tile.alpha_composite(image.crop((760, 570, 980, 1020)))
        board.paste(tile.convert('RGB'), (index*220, 30))
        draw.text((index*220+5, 8), label, fill='white')
    board.save(OUT/'detail.png')
    before, after = np.asarray(parent), np.asarray(pose)
    changed = np.any(before != after, axis=2)
    meta = dict(sourceSha256=ACCEPTED_SHA, parentCompositionVersion='review-art-v4',
        parentPoseRGBAHash=PARENT_HASH, gradientMaterialPoseRGBAHash=MATERIAL_HASH,
        method='gradient-guided RGB offset; observed mother hair Dirichlet, unobserved boundary natural zero-normal offset',
        solverCrop=list(BOX), solver=recorded_diagnostics(diagnostics), observedSourcePixels=int(masks['known'].sum()),
        unknownHairPixels=int(masks['unknown'].sum()), excludedBoundaryPixels=int(unobserved.sum()),
        anchoredUnknownPixels=int(eligible.sum()), unanchoredUnknownPixelsKept=int((masks['unknown'] & ~eligible).sum()),
        changedPixels=int(changed.sum()), changedOutsideUnknown=int((changed & ~masks['unknown']).sum()),
        parentAlphaPreserved=bool(np.array_equal(before[...,3],after[...,3])),
        handsAndSleevesRGBAExact=bool(np.array_equal(before[masks['protected']],after[masks['protected']])),
        knownSourceRGBAExact=bool(np.array_equal(after[masks['known']],np.asarray(load_canonical())[masks['known']])),
        poseRGBAHash=rgba_hash(pose), frameRGBAHash=rgba_hash(frame),
        newArtworkGenerated=False, facialGeometryRepair=False, hiddenStrandTopologyRecovered=False,
        cleanLayerRecoveryClaimed=False, animationBuilt=False, adopted=False,
        activeAtlasChanged=False, visualAcceptance='pending', installableFullAtlas=False, installed=False,
        limitations=['Material strand gradients remain an authored estimate; removing false observations does not reconstruct hidden strand paths.',
                     'A zero-normal offset boundary is a declared regularizer, not an observation of hair color or a guarantee of perfect seam tangents.',
                     'Actual native-scale seams and costume/hand aesthetics require visual inspection before adoption.'])
    (OUT/'build.json').write_text(json.dumps(meta, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(meta, indent=2))


if __name__ == '__main__':
    main()
