"""Repair the incomplete v1 removal footprint, without generating new art.

The original hand/sleeve must be retired before the new foreground can be
composited. v1 confused the new, narrower sleeve with the original footprint.
Keep v1 and its raw source immutable as a regression fixture.
"""
import hashlib
import json

import numpy as np
from PIL import Image, ImageDraw

from canonical import ROOT, ACCEPTED_SHA, bounded_artwork, clean_cutout, camera, load_canonical
from review_review import inputs as v1_inputs, GENERATED_SHA
from review_processing import GENERATED_SHA as LEFT_SHA
from review_waiting import grid
from review_wave import native_frame

OUT = ROOT/'candidates/phase5/review-art-v2'


def comparison(frames,width,labels=None):
    height = round(width*208/192)
    board = Image.new('RGB',(3*(width+20),2*(height+32)),'#23252b')
    draw = ImageDraw.Draw(board)
    for col,(frame,label) in enumerate(zip(frames,labels or ['locked v3','v1 (defect)','v2 (repair)'])):
        for row,background in enumerate(['#23252b','#f1f0ee']):
            tile = Image.new('RGBA',frame.size,background)
            tile.alpha_composite(frame)
            x,y = col*(width+20),row*(height+32)
            board.paste(tile.resize((width,height),Image.Resampling.NEAREST).convert('RGB'),(x+10,y+26))
            draw.text((x+3,y+5),label,fill='white')
    return board


def specification():
    spec = json.loads((OUT/'patch.json').read_text(encoding='utf-8'))
    if (spec['sourceSha256'] != ACCEPTED_SHA or spec['generatedSha256'] != GENERATED_SHA
            or spec['leftArmGeneratedSha256'] != LEFT_SHA
            or spec['generatedSource'] != 'candidates/phase5/review-art-v1/generated.png'
            or spec['canvas'] != [1205,1306] or spec['sourceCrop'] != [450,500,970,1010]
            or spec['rawCanvas'] != [1266,1242] or spec['editBudget'] != [498,570,950,1000]
            or spec['edgeFeatherSourcePx'] != 1.5 or spec['newArtworkGenerated']
            or spec['fullRedrawAccepted'] or spec['newFaceGeometryAllowed']
            or spec['articulatedArmBuilt'] or spec['installableFullAtlas'] or spec['installed']
            or spec['visualAcceptance'] != 'pending' or spec['strategyUserApproval'] != 'pending'):
        raise ValueError('Review repair violates immutable source/local repair boundary')
    x0,y0,x1,y1 = spec['editBudget']
    for key in ('oldRightArmPolygon','foregroundRightArmPolygon'):
        p = np.asarray(spec[key])
        if (p.ndim != 2 or p.shape[1] != 2 or len(p) < 3 or not np.isfinite(p).all()
                or np.any(p[:,0] < x0) or np.any(p[:,0] > x1)
                or np.any(p[:,1] < y0) or np.any(p[:,1] > y1)):
            raise ValueError('Review repair permission exceeds its explicit source budget')
    return spec


def inputs():
    spec = specification()
    base, original, generated = v1_inputs()
    if spec['foregroundRightArmPolygon'] != original['foregroundRightArmPolygon']:
        raise ValueError('This repair must not change the foreground gesture')
    if spec['preservedForegroundPolygons'] != original['preservedForegroundPolygons']:
        raise ValueError('This repair must preserve the same source foreground plates')
    return base, spec, generated


def localized_pose(base, generated, spec):
    # Validate the supplied object, not just the on-disk specification. Keep
    # this API strict even for an identity input whose changed pixels are zero.
    if spec != specification():
        raise ValueError('Review repair specification differs from recorded permission')
    image, allowed, _ = bounded_artwork(base, generated,
        [spec['oldRightArmPolygon'], spec['foregroundRightArmPolygon']], spec['edgeFeatherSourcePx'])
    foreground = Image.new('L',base.size)
    for polygon in spec['preservedForegroundPolygons']:
        ImageDraw.Draw(foreground).polygon(polygon,fill=255)
    preserved = np.asarray(foreground) > 0
    before, after = np.asarray(base), np.asarray(image).copy()
    after[preserved] = before[preserved]
    allowed &= ~preserved
    changed = np.any(after != before,axis=2)
    if np.any(changed & ~allowed):
        raise ValueError('Review repair repainted outside the old/new arm footprint')
    for x0,y0,x1,y1 in [(455,250,775,465),(433,1015,611,1226),(616,1015,795,1226)]:
        if np.any(allowed[y0:y1,x0:x1]) or np.any(changed[y0:y1,x0:x1]):
            raise ValueError('Review repair touched a protected face/shoe')
    return Image.fromarray(after), allowed, preserved


def main():
    base, spec, raw = inputs()
    pose, allowed, preserved = localized_pose(base,raw,spec)
    pose.save(OUT/'pose.png')
    Image.fromarray(allowed.astype(np.uint8)*255).save(OUT/'allowed-mask.png')
    Image.fromarray(preserved.astype(np.uint8)*255).save(OUT/'preserved-foreground-mask.png')
    frame = native_frame(pose)
    frame.save(OUT/'frame.png')
    with Image.open(ROOT/'candidates/phase5/review-art-v1/pose.png') as image:
        previous = image.convert('RGBA')
    frames = [native_frame(load_canonical()),native_frame(previous),frame]
    for width in (80,113,192,224):
        comparison(frames,width).save(OUT/f'contact-{width}px.png')
    diagnostic = ROOT/'work/review-inspection'
    diagnostic.mkdir(parents=True,exist_ok=True)
    grid(pose,(450,500,975,1005)).save(diagnostic/'repaired-grid.png')
    pose.crop((700,550,960,810)).resize((780,780),Image.Resampling.NEAREST).save(diagnostic/'repaired-shoulder.png')
    changed = np.any(np.asarray(base) != np.asarray(pose),axis=2)
    metadata = dict(sourceSha256=ACCEPTED_SHA,generatedSha256=GENERATED_SHA,
        generatedSource=spec['generatedSource'],leftArmGeneratedSha256=LEFT_SHA,
        role=spec['role'],rawCanvas=spec['rawCanvas'],sourceCrop=spec['sourceCrop'],
        cropProjection=spec['cropProjection'],newArtworkGenerated=False,
        boundedRightArmChangedPixels=int(changed.sum()),
        boundedRightArmChangedPixelsOutsidePatch=int((changed & ~allowed).sum()),
        rawMappedCropChangedPixelsOutsidePatch=int((np.any(np.asarray(base)!=np.asarray(raw),axis=2)&~allowed).sum()),
        changedPixelsFromV1=int(np.any(np.asarray(previous)!=np.asarray(pose),axis=2).sum()),
        originalHeadFaceRGBAExact=True,sourceForegroundPlatesPreserved=True,
        poseRGBAHash=hashlib.sha256(pose.tobytes()).hexdigest().upper(),
        frameRGBAHash=hashlib.sha256(frame.tobytes()).hexdigest().upper(),
        camera=camera(clean_cutout(load_canonical())[0]),sameSourceCoordinateCamera=True,
        fullRedrawAccepted=False,facialGeometryRepair=False,articulatedArmBuilt=False,animationBuilt=False,
        visualAcceptance='pending',strategyUserApproval='pending',
        placementLimitation=spec['placementLimitation'],installableFullAtlas=False,installed=False)
    (OUT/'build.json').write_text(json.dumps(metadata,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(metadata,indent=2))


if __name__ == '__main__':
    main()
