"""Bounded hidden arm backing; not a finished pose or an arm-rig proof."""
import hashlib
import json

import numpy as np
from PIL import Image, ImageDraw

from canonical import ROOT, ACCEPTED_SHA, load_canonical, bounded_artwork, clean_cutout, camera
from build_idle import specification as idle_specification, region_masks, render
from review_waiting import comparison, grid

OUT = ROOT/'candidates/phase5/arm-backing-v1'
GENERATED_SHA = '9798CEAFF8B61630A94DCCE0E8533AB87F11BBD2D24936481C94620557ED2B2F'


def specification():
    spec = json.loads((OUT/'patch.json').read_text(encoding='utf-8'))
    if (spec['sourceSha256'] != ACCEPTED_SHA or spec['generatedSha256'] != GENERATED_SHA
            or spec['canvas'] != [1205, 1306] or spec['fullRedrawAccepted']
            or spec['newFaceGeometryAllowed'] or spec['articulatedArmBuilt']
            or spec['installableFullAtlas']):
        raise ValueError('Backing plate violates the locked source or overstates readiness')
    return spec


def load_generated():
    path = OUT/'generated.png'
    if hashlib.sha256(path.read_bytes()).hexdigest().upper() != GENERATED_SHA:
        raise ValueError('Hidden arm backing source changed')
    with Image.open(path) as image:
        result = image.convert('RGBA')
    if result.size != (1205, 1306):
        raise ValueError('Backing plate camera differs; no fitting allowed')
    return result


def localized_backing(source, generated, spec):
    result, allowed, _ = bounded_artwork(source, generated,
        [spec['armFootprintPolygon']], spec['edgeFeatherSourcePx'])
    a, b = np.asarray(source), np.asarray(result).copy()
    foreground = Image.new('L', source.size)
    for polygon in spec['preservedForegroundPolygons']:
        ImageDraw.Draw(foreground).polygon(polygon, fill=255)
    protected = np.asarray(foreground) > 0
    b[protected] = a[protected]
    allowed = allowed & ~protected
    result = Image.fromarray(b)
    changed = np.any(a != b, axis=2)
    if np.any(changed & ~allowed):
        raise ValueError('Hidden backing repainted outside the old arm footprint')
    for x0, y0, x1, y1 in spec['protectedRects']:
        if np.any(changed[y0:y1, x0:x1]):
            raise ValueError('Hidden backing touched protected face/cape/body/shoes')
    return result, allowed


def main():
    source, generated, spec = load_canonical(), load_generated(), specification()
    backing, allowed = localized_backing(source, generated, spec)
    backing.save(OUT/'backing.png')
    Image.fromarray(allowed.astype(np.uint8)*255).save(OUT/'allowed-mask.png')
    diagnostic = ROOT/'work/arm-backing-inspection'
    diagnostic.mkdir(parents=True, exist_ok=True)
    box = (225, 500, 630, 1010)
    for name, image in [('source', source), ('raw', generated), ('bounded', backing)]:
        grid(image, box).save(diagnostic/f'{name}-grid.png')
    transform = camera(clean_cutout(source)[0])
    regions, _ = idle_specification()
    masks = region_masks(regions)
    frames = [render(clean_cutout(image)[0], dict(bodyY=0, earAngle=0, hairAngle=0),
                     transform, regions, masks) for image in [source, generated, backing]]
    frames[-1].save(OUT/'frame.png')
    for width in (80, 113, 192, 224):
        comparison(frames, width, 'technical backing ONLY').save(OUT/f'contact-{width}px.png')
    a, raw, b = np.asarray(source), np.asarray(generated), np.asarray(backing)
    changed = np.any(a != b, axis=2)
    metadata = dict(sourceSha256=ACCEPTED_SHA, generatedSha256=GENERATED_SHA,
        role=spec['role'], camera=transform, sameSourceCoordinateCamera=True,
        rawChangedPixelsOutsidePatch=int(np.count_nonzero(np.any(a != raw, axis=2) & ~allowed)),
        boundedChangedPixels=int(np.count_nonzero(changed)),
        boundedChangedPixelsOutsidePatch=int(np.count_nonzero(changed & ~allowed)),
        backingRGBAHash=hashlib.sha256(b.tobytes()).hexdigest().upper(),
        frameRGBAHash=hashlib.sha256(frames[-1].tobytes()).hexdigest().upper(),
        fullRedrawAccepted=False, facialGeometryRepair=False,
        sourceCapeAndForegroundLockPreserved=True,
        articulatedArmBuilt=False, animationBuilt=False,
        visualAcceptance='pending', installableFullAtlas=False, installed=False,
        limitation='A hidden-background plate only; no clean foreground matte, elbow/wrist layers or neutral reconstruction proof yet.')
    (OUT/'build.json').write_text(json.dumps(metadata, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(metadata, indent=2))


if __name__ == '__main__':
    main()
