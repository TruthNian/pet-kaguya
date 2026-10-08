"""Localized wave cels over one bounded backing; never a full art/rig claim."""
import hashlib
import json

import numpy as np
from PIL import Image, ImageDraw

from canonical import ROOT, ACCEPTED_SHA, load_canonical, bounded_artwork, clean_cutout, camera
from review_arm_backing import localized_backing, load_generated as backing_art, specification as backing_spec
from review_waiting import comparison, grid
from build_idle import specification as idle_specification, region_masks, render

ART = {
    'peak': ('wave-art-v2', '0EF5AB97408BA1822AE62BF7532E04F7890D2DB51DE5E1EE5CDA229245D3886C'),
    'middle': ('wave-art-middle-v2', 'FD46154D7C426B74E0F1F02EC0A0783F2B9398D71BB534634506783D18FB6955'),
}
BUDGETS = {'peak':[295,545,525,835],'middle':[270,560,525,835]}


def inputs(kind):
    folder, expected = ART[kind]
    out = ROOT/'candidates/phase5'/folder
    spec = json.loads((out/'patch.json').read_text(encoding='utf-8'))
    if (spec['sourceSha256'] != ACCEPTED_SHA or spec['generatedSha256'] != expected
            or spec['canvas'] != [1205, 1306] or spec['fullRedrawAccepted']
            or spec['newFaceGeometryAllowed'] or spec['installableFullAtlas'] or spec['installed']
            or spec['editBudget'] != BUDGETS[kind]):
        raise ValueError('Wave cel violates canonical identity/candidate boundary')
    polygon = np.array(spec['foregroundPolygon'])
    x0,y0,x1,y1 = spec['editBudget']
    if (not len(polygon)>=3 or not np.isfinite(polygon).all()
            or np.any(polygon[:,0]<x0) or np.any(polygon[:,0]>x1)
            or np.any(polygon[:,1]<y0) or np.any(polygon[:,1]>y1)):
        raise ValueError('Wave silhouette exceeds its explicit arm-only budget')
    path = out/'generated.png'
    if hashlib.sha256(path.read_bytes()).hexdigest().upper() != expected:
        raise ValueError('Wave cel source changed')
    with Image.open(path) as image:
        generated = image.convert('RGBA')
    if kind=='middle':
        if (generated.size!=(971,1619) or spec['rawCanvas']!=[971,1619]
                or spec['sourceCrop']!=[250,500,550,1000]):
            raise ValueError('Wave crop uses another framing; no object refitting allowed')
        # Locked crop registration, NOT independently fitted arm/head bounds.
        # The generator enlarged the crop. Width and height use the SAME
        # inverse scale; the extra 0.206 source px at its bottom is clipped.
        # Premultiplied bilinear avoids invented transparent-edge RGB.
        ratio=971/300
        crop=generated.convert('RGBa').transform((300,500),Image.Transform.AFFINE,
            (ratio,0,0,0,ratio,0),Image.Resampling.BILINEAR).convert('RGBA')
        mapped=load_canonical()
        mapped.paste(crop,(250,500))
        generated=mapped
    elif generated.size != (1205,1306):
        raise ValueError('Wave cel uses another camera; no refitting allowed')
    return out,spec,generated


def localized_pose(mother, generated, spec):
    backing_definition = backing_spec()
    backing, backing_allowed = localized_backing(mother,backing_art(),backing_definition)
    pose, foreground_allowed, _ = bounded_artwork(backing,generated,
        [spec['foregroundPolygon']],spec['edgeFeatherSourcePx'])
    foreground = Image.new('L',mother.size)
    for polygon in backing_definition['preservedForegroundPolygons']:
        ImageDraw.Draw(foreground).polygon(polygon,fill=255)
    protected = np.asarray(foreground)>0
    original,pixels = np.asarray(mother),np.asarray(pose).copy()
    pixels[protected] = original[protected]
    allowed = (backing_allowed|foreground_allowed)&~protected
    changed = np.any(original!=pixels,axis=2)
    if np.any(changed&~allowed):
        raise ValueError('Wave repainted outside bounded old/new arm regions')
    for x0,y0,x1,y1 in backing_definition['protectedRects']:
        if np.any(changed[y0:y1,x0:x1]):
            raise ValueError('Wave touched protected face/cape/body/shoes')
    return Image.fromarray(pixels),allowed


def native_frame(pose):
    mother = clean_cutout(load_canonical())[0]
    regions,_ = idle_specification()
    return render(clean_cutout(pose)[0],dict(bodyY=0,earAngle=0,hairAngle=0),
                  camera(mother),regions,region_masks(regions))


def main():
    mother = load_canonical()
    for kind in ART:
        out,spec,raw = inputs(kind)
        pose,allowed = localized_pose(mother,raw,spec)
        pose.save(out/'pose.png')
        Image.fromarray(allowed.astype(np.uint8)*255).save(out/'allowed-mask.png')
        frame = native_frame(pose)
        frame.save(out/'frame.png')
        frames = [native_frame(mother),native_frame(raw),frame]
        for width in (80,113,192,224):
            comparison(frames,width,f'bounded {kind} cel').save(out/f'contact-{width}px.png')
        diagnostic = ROOT/'work/wave-inspection'/kind
        diagnostic.mkdir(parents=True,exist_ok=True)
        for name,image in [('source',mother),('raw',raw),('bounded',pose)]:
            grid(image,(225,500,550,1010)).save(diagnostic/f'{name}-grid.png')
        changed = np.any(np.asarray(mother)!=np.asarray(pose),axis=2)
        metadata = dict(sourceSha256=ACCEPTED_SHA,generatedSha256=spec['generatedSha256'],
            role=spec['role'],boundedChangedPixels=int(changed.sum()),
            boundedChangedPixelsOutsidePatch=int((changed&~allowed).sum()),
            rawChangedPixelsOutsidePatch=int((np.any(np.asarray(mother)!=np.asarray(raw),axis=2)&~allowed).sum()),
            poseRGBAHash=hashlib.sha256(pose.tobytes()).hexdigest().upper(),
            frameRGBAHash=hashlib.sha256(frame.tobytes()).hexdigest().upper(),
            sameSourceCoordinateCamera=True,camera=camera(clean_cutout(mother)[0]),
            facialGeometryRepair=False,sourceCapeAndForegroundLockPreserved=True,
            fullRedrawAccepted=False,articulatedArmBuilt=False,animationBuilt=False,
            visualAcceptance='pending',installableFullAtlas=False,installed=False,
            cropProjection=spec.get('cropProjection'),rawCanvas=spec.get('rawCanvas',[1205,1306]),
            placementLimitation=spec['placementLimitation'])
        (out/'build.json').write_text(json.dumps(metadata,indent=2)+'\n',encoding='utf-8')
        print(json.dumps(metadata,indent=2))


if __name__=='__main__':
    main()
