"""Review missing waiting artwork; never adopt a whole generated redraw."""
import hashlib
import json

import numpy as np
from PIL import Image, ImageDraw

from canonical import ROOT, ACCEPTED_SHA, load_canonical, clean_cutout, camera, bounded_masks, bounded_artwork
from build_idle import specification as idle_specification, region_masks, render

OUT = ROOT/'candidates/phase5/waiting-art-v1'
GENERATED_SHA = '39165C8A937747F6B38CDCC3A2F8CA9CC11787C03EA46856D0E25F69CD111BD2'


def load_generated():
    path = OUT/'generated.png'
    if hashlib.sha256(path.read_bytes()).hexdigest().upper() != GENERATED_SHA:
        raise ValueError('Waiting missing-art source changed')
    with Image.open(path) as image:
        result = image.convert('RGBA')
    if result.size != (1205, 1306):
        raise ValueError('Waiting camera differs; no independent head/body fitting allowed')
    return result


def grid(image, box):
    crop = image.crop(box)
    board = Image.new('RGBA', crop.size, '#ededed')
    board.alpha_composite(crop)
    draw = ImageDraw.Draw(board)
    x0, y0, x1, y1 = box
    for x in range((x0//25+1)*25, x1, 25):
        draw.line((x-x0, 0, x-x0, board.height), fill='#98a2aa88')
        draw.text((x-x0+2, 2), str(x), fill='#243a52')
    for y in range((y0//25+1)*25, y1, 25):
        draw.line((0, y-y0, board.width, y-y0), fill='#98a2aa88')
        draw.text((2, y-y0+2), str(y), fill='#243a52')
    return board.convert('RGB')


def specification():
    spec = json.loads((OUT/'patch.json').read_text(encoding='utf-8'))
    validate_specification(spec)
    return spec


def validate_specification(spec):
    if (spec['sourceSha256'] != ACCEPTED_SHA or spec['generatedSha256'] != GENERATED_SHA
            or spec['canvas'] != [1205, 1306] or spec['fullRedrawAccepted']
            or spec['newFaceGeometryAllowed'] or not spec['facialChangesAllowedOnlyAsForegroundHandOcclusion']
            or spec['visualAcceptance'] != 'pending' or spec['animationBuilt'] or spec['installed']):
        raise ValueError('Waiting patch violates the locked mother-pose decision')
    # Face occlusion is a specific lower-cheek hand, not permission to repaint
    # eyes, mouth or the whole head under the label "foreground hand".
    for name,budget in [('armAndBackingPolygon',(247,473,570,1000)),
                        ('foregroundHandPolygon',(505,429,588,566))]:
        points = np.asarray(spec[name])
        x0,y0,x1,y1 = budget
        if (points.ndim != 2 or points.shape[1] != 2 or len(points)<3
                or not np.isfinite(points).all() or np.any(points[:,0]<x0)
                or np.any(points[:,0]>x1) or np.any(points[:,1]<y0) or np.any(points[:,1]>y1)):
            raise ValueError('Waiting arm/hand permission exceeds its inspected region')


def masks(spec):
    allowed, weight, components = bounded_masks(tuple(spec['canvas']),
        [spec['armAndBackingPolygon'], spec['foregroundHandPolygon']], spec['edgeFeatherSourcePx'])
    return allowed, weight, components[1][0]


def localized_pose(source, generated, spec):
    validate_specification(spec)
    image, allowed, components = bounded_artwork(source, generated,
        [spec['armAndBackingPolygon'], spec['foregroundHandPolygon']], spec['edgeFeatherSourcePx'])
    regions,_ = idle_specification()
    face = np.zeros(allowed.shape,dtype=bool)
    x0,y0,x1,y1 = regions['protectedFace']
    face[y0:y1,x0:x1] = True
    changed = np.any(np.asarray(source)!=np.asarray(image),axis=2)
    if np.any(changed & face & ~components[1][0]):
        raise ValueError('Waiting changed a face pixel outside the foreground hand')
    return image, allowed, components[1][0]


def comparison(frames, width, patch_label='bounded arm patch'):
    height = round(width*208/192)
    board = Image.new('RGB', (3*(width+20), 2*(height+32)), '#23252b')
    draw = ImageDraw.Draw(board)
    labels = ['locked v3', 'raw AI: NOT adopted', patch_label]
    for col, frame in enumerate(frames):
        for row, background in enumerate(['#23252b', '#f1f0ee']):
            tile = Image.new('RGBA', frame.size, background)
            tile.alpha_composite(frame)
            x, y = col*(width+20), row*(height+32)
            board.paste(tile.resize((width, height), Image.Resampling.NEAREST).convert('RGB'), (x+10, y+26))
            draw.text((x+3, y+5), labels[col], fill='white')
    return board


def main():
    source = load_canonical()
    generated = load_generated()
    spec = specification()
    pose, allowed, foreground = localized_pose(source, generated, spec)
    diagnostics = ROOT/'work/waiting-inspection'
    diagnostics.mkdir(parents=True, exist_ok=True)
    box = (225, 400, 630, 1010)
    grid(source, box).save(diagnostics/'source-grid.png')
    grid(generated, box).save(diagnostics/'generated-grid.png')
    grid(pose, box).save(diagnostics/'localized-grid.png')
    pose.save(OUT/'pose.png')
    Image.fromarray(allowed.astype(np.uint8)*255).save(OUT/'allowed-mask.png')
    cleaned, _ = clean_cutout(source)
    transform = camera(cleaned)
    regions, _ = idle_specification()
    rig_masks = region_masks(regions)
    cleaned_pose, cleanup = clean_cutout(pose)
    frame = render(cleaned_pose, dict(bodyY=0, earAngle=0, hairAngle=0), transform, regions, rig_masks)
    frame.save(OUT/'frame.png')
    frames = [render(clean_cutout(image)[0], dict(bodyY=0, earAngle=0, hairAngle=0),
                     transform, regions, rig_masks) for image in [source, generated]]+[frame]
    for width in (80, 113, 192, 224):
        comparison(frames, width).save(OUT/f'contact-{width}px.png')
    a, b = np.asarray(source), np.asarray(generated)
    changed = np.any(a != b, axis=2)
    p = np.asarray(pose)
    outside_changes = int(np.count_nonzero(np.any(a != p, axis=2) & ~allowed))
    face = np.zeros(allowed.shape, dtype=bool)
    x0, y0, x1, y1 = regions['protectedFace']
    face[y0:y1, x0:x1] = True
    face_changes_without_hand = int(np.count_nonzero(np.any(a != p, axis=2) & face & ~foreground))
    metadata = dict(sourceSha256=ACCEPTED_SHA, generatedSha256=GENERATED_SHA,
        cameraDimensionsMatch=True, camera=transform, rawExactUnchangedFraction=float((~changed).mean()),
        rawChangedPixelsOutsidePatch=int(np.count_nonzero(changed & ~allowed)),
        boundedChangedPixels=int(np.count_nonzero(np.any(a != p, axis=2))),
        boundedChangedPixelsOutsidePatch=outside_changes, faceChangesOutsideForegroundHand=face_changes_without_hand,
        poseRGBAHash=hashlib.sha256(p.tobytes()).hexdigest().upper(),
        frameRGBAHash=hashlib.sha256(frame.tobytes()).hexdigest().upper(), alphaCleanup=cleanup,
        sameSourceCoordinateCamera=True, independentHeadFitting=False, facialGeometryRepair=False,
        fullRedrawAccepted=False, visualAcceptance='pending', animationBuilt=False,
        installed=False, installableFullAtlas=False)
    if outside_changes or face_changes_without_hand:
        raise ValueError('Waiting patch repainted protected pixels')
    (OUT/'build.json').write_text(json.dumps(metadata, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(metadata, indent=2))


if __name__ == '__main__':
    main()
