"""Same locked face geometry; bounded expressive line artwork, not a redraw."""
import hashlib
import json

import numpy as np
from PIL import Image

from canonical import ROOT, ACCEPTED_SHA, load_canonical, clean_cutout, camera, bounded_artwork
from build_idle import specification as idle_specification, region_masks, render
from review_waiting import grid, comparison

OUT = ROOT/'candidates/phase5/failed-art-v1'
GENERATED_SHA = 'C11EE42731513A83A3C8B479FC0B2AF1B38895D2244A1115F4D617E33279B70B'


def specification():
    spec = json.loads((OUT/'patch.json').read_text(encoding='utf-8'))
    if (spec['sourceSha256'] != ACCEPTED_SHA or spec['generatedSha256'] != GENERATED_SHA
            or spec['canvas'] != [1205, 1306] or spec['fullRedrawAccepted'] or spec['newFaceGeometryAllowed']):
        raise ValueError('Failed expression violates the locked mother-pose decision')
    return spec


def load_generated():
    path = OUT/'generated.png'
    if hashlib.sha256(path.read_bytes()).hexdigest().upper() != GENERATED_SHA:
        raise ValueError('Failed expression source changed')
    with Image.open(path) as image:
        result = image.convert('RGBA')
    if result.size != (1205, 1306):
        raise ValueError('Failed source camera changed')
    return result


def localized_pose(source, generated, spec):
    result, allowed, _ = bounded_artwork(source, generated, spec['expressionPolygons'], spec['edgeFeatherSourcePx'])
    a, b = np.asarray(source), np.asarray(result)
    for x0, y0, x1, y1 in spec['eyeProtectedRects']:
        if not np.array_equal(a[y0:y1, x0:x1], b[y0:y1, x0:x1]):
            raise ValueError('Expression patch repainted an eye')
    return result, allowed


def main():
    source = load_canonical()
    generated = load_generated()
    spec = specification()
    pose, allowed = localized_pose(source, generated, spec)
    diagnostics = ROOT/'work/failed-inspection'
    diagnostics.mkdir(parents=True, exist_ok=True)
    for name, image in [('source', source), ('generated', generated), ('localized', pose)]:
        grid(image, (420, 195, 790, 475)).save(diagnostics/f'{name}-grid.png')
        plain = Image.new('RGBA', (370, 280), '#ededed')
        plain.alpha_composite(image.crop((420, 195, 790, 475)))
        plain.resize((740, 560), Image.Resampling.NEAREST).save(diagnostics/f'{name}-face.png')
    pose.save(OUT/'pose.png')
    Image.fromarray(allowed.astype(np.uint8)*255).save(OUT/'allowed-mask.png')
    cleaned, _ = clean_cutout(source)
    transform = camera(cleaned)
    regions, _ = idle_specification()
    rig_masks = region_masks(regions)
    frames = [render(clean_cutout(image)[0], dict(bodyY=0, earAngle=0, hairAngle=0),
                     transform, regions, rig_masks) for image in [source, generated, pose]]
    frames[-1].save(OUT/'frame.png')
    for width in (80, 113, 192, 224):
        comparison(frames, width, 'bounded expression').save(OUT/f'contact-{width}px.png')
    a, g, p = np.asarray(source), np.asarray(generated), np.asarray(pose)
    metadata = dict(sourceSha256=ACCEPTED_SHA, generatedSha256=GENERATED_SHA,
        camera=transform, sameSourceCoordinateCamera=True, independentHeadFitting=False,
        rawChangedPixelsOutsidePatch=int(np.count_nonzero(np.any(a != g, axis=2) & ~allowed)),
        boundedChangedPixels=int(np.count_nonzero(np.any(a != p, axis=2))),
        boundedChangedPixelsOutsidePatch=int(np.count_nonzero(np.any(a != p, axis=2) & ~allowed)),
        eyesPreservedExactly=True, jawAndChinPreservedExactly=True, costumePreservedExactly=True,
        poseRGBAHash=hashlib.sha256(p.tobytes()).hexdigest().upper(),
        frameRGBAHash=hashlib.sha256(frames[-1].tobytes()).hexdigest().upper(),
        facialGeometryRepair=False, fullRedrawAccepted=False, visualAcceptance='pending',
        animationBuilt=False, installed=False, installableFullAtlas=False,
        promptInvariantUnproven=['same mouth-line width; generated frown appears shorter than original smile'])
    if metadata['boundedChangedPixelsOutsidePatch']:
        raise ValueError('Failed patch escaped its expression regions')
    (OUT/'build.json').write_text(json.dumps(metadata, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(metadata, indent=2))


if __name__ == '__main__':
    main()
