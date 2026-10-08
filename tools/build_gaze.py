"""Sixteen gaze poses: fixed eyes/face/body, translated original iris pixels.

The inverse composite estimates an iris matte, not a new eye shape. Missing
sclera comes from bounded generated backing. Neutral reconstruction is tested
through the same physical, nonnegative premultiplied layers, not a special case.
"""
import hashlib
import json
import math
from collections import deque

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from canonical import ROOT, ACCEPTED_SHA, load_canonical, clean_cutout, camera
from build_idle import specification as idle_specification, region_masks, render, sample
from review_waiting import grid

ART = ROOT/'candidates/phase5/eye-backing-v1'
OUT = ROOT/'candidates/phase5/look'
GENERATED_SHA = '684BA98301B8BD4F204581E77CDE1586528D0EC7B1804C5CFC4ADB5E1EF2B61A'


def specification():
    spec = json.loads((ROOT/'sources/canonical/gaze-rig.json').read_text(encoding='utf-8'))
    validate_rig(spec)
    return spec


def validate_rig(spec):
    if (spec['sourceSha256'] != ACCEPTED_SHA or spec['canvas'] != [1205,1306]
            or not spec['faceShapeLocked'] or spec['irisShapeWarpAllowed']
            or spec['bodyRotationAllowed'] or spec['directions'] != 16
            or spec['installableFullAtlas'] or spec['visualAcceptance'] != 'pending'):
        raise ValueError('Gaze violates locked mother/eye shape/candidate boundary')
    if (len(spec['maximumDisplacementSourcePx'])!=2
            or any(not math.isfinite(v) or v <= 0 or v > limit for v,limit in zip(spec['maximumDisplacementSourcePx'], [12,7]))):
        raise ValueError('Gaze displacement exceeds the inspected range')
    expected = [('viewer_left',[465,280,587,397],[470,289,578,390]),
                ('viewer_right',[636,263,761,386],[644,276,753,375])]
    if len(spec['eyes'])!=2:
        raise ValueError('Gaze needs the two original eyes, not duplicated or mirrored art')
    for eye,(name,box,bounds) in zip(spec['eyes'],expected):
        if eye['name']!=name or eye['box']!=box:
            raise ValueError('Eye extraction identity/location changed')
        x0,y0,x1,y1 = bounds
        for key in ('aperturePolygon','irisPolygon'):
            if any(not (x0<=x<x1 and y0<=y<y1) for x,y in eye[key]):
                raise ValueError('Eye permission cannot extend into brows, mouth, jaw or body')


def load_generated():
    path = ART/'generated.png'
    if hashlib.sha256(path.read_bytes()).hexdigest().upper() != GENERATED_SHA:
        raise ValueError('Hidden eye backing source changed')
    with Image.open(path) as image:
        result = image.convert('RGBA')
    if result.size != (1205,1306):
        raise ValueError('Eye backing canvas differs; no face fitting allowed')
    return result


def polygon_mask(eye, key):
    x0,y0,x1,y1 = eye['box']
    result = Image.new('L', (x1-x0,y1-y0))
    ImageDraw.Draw(result).polygon([(x-x0,y-y0) for x,y in eye[key]], fill=255)
    return result


def convex_hull(points):
    points = sorted(set(points))
    if len(points) < 3:
        raise ValueError('No visible iris colour contour')
    def cross(a,b,c):
        return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
    lower,upper = [],[]
    for sequence,chain in [(points,lower),(reversed(points),upper)]:
        for point in sequence:
            while len(chain)>1 and cross(chain[-2],chain[-1],point)<=0:
                chain.pop()
            chain.append(point)
    return lower[:-1]+upper[:-1]


def visible_iris_mask(original, eye):
    # The authored contour identifies the iris, but is not itself a matte:
    # filling it carried original sclera as a white moving border. Find the
    # coloured/dark contour only inside that semantic gate, then enclose iris
    # highlights. This changes coverage inference, never the RGB eye artwork.
    gate = np.asarray(polygon_mask(eye,'irisPolygon')) > 0
    rgb = original[...,:3].astype(int)
    seeds = gate & ((np.ptp(rgb,axis=2)>=25) | (rgb.min(axis=2)<=165))
    yy,xx = np.where(seeds)
    result = Image.new('L',gate.shape[::-1])
    ImageDraw.Draw(result).polygon(convex_hull(list(zip(xx.tolist(),yy.tolist()))),fill=255)
    return result


def exterior_sclera(original, iris_mask, aperture):
    """Known light eye-white connected to the exterior, not iris catchlights.

    A convex envelope can contain white sclera even where its coverage is 1.
    Classifying only its feathered edge therefore carried that white rim. The
    topology distinguishes enclosed highlights from exterior eye-white. Do not
    use generated-white colour agreement as a condition: its shadow may differ,
    causing a real white surface to be misclassified as a moving opaque rim.
    This remains an estimate, not recovered ground-truth segmentation.
    """
    rgb = original[...,:3].astype(int)
    light = (rgb.min(axis=2)>180) & (np.ptp(rgb,axis=2)<45) & aperture
    exterior = light & (np.asarray(iris_mask)==0)
    yy,xx = np.where(exterior)
    queue = deque(zip(yy.tolist(),xx.tolist()))
    while queue:
        y,x = queue.popleft()
        for ny,nx in ((y-1,x),(y+1,x),(y,x-1),(y,x+1)):
            if (0<=ny<light.shape[0] and 0<=nx<light.shape[1]
                    and light[ny,nx] and not exterior[ny,nx]):
                exterior[ny,nx] = True
                queue.append((ny,nx))
    return exterior


def layers(source, generated, spec):
    validate_rig(spec)
    if source.size != generated.size or source.size != tuple(spec['canvas']):
        raise ValueError('Eye sources must share the original camera canvas')
    results = []
    for eye in spec['eyes']:
        original = np.asarray(source.crop(tuple(eye['box'])))
        new = np.asarray(generated.crop(tuple(eye['box'])))
        aperture = np.asarray(polygon_mask(eye,'aperturePolygon')) > 0
        iris_mask = visible_iris_mask(original,eye)
        support = np.asarray(iris_mask.filter(ImageFilter.MaxFilter(2*spec['backingMarginSourcePx']+1))) > 0
        support &= aperture
        if np.any(original[...,3][support] < 250) or np.any(new[...,3][support] < 250):
            raise ValueError('Eye backing must lie inside the nearly opaque face surface')
        # The AI mother itself has alpha 252..254 in these interiors, NOT 255.
        # Compose the eye's material colours on that surface; keep its original
        # coverage separately and exactly. Never fit/replace face alpha from AI.
        s = original[...,:3].astype(float)/255
        b = s.copy()
        b[support] = new[...,:3][support]/255
        soft = np.asarray(iris_mask.filter(ImageFilter.GaussianBlur(spec['irisEdgeBlurSourcePx'])),dtype=float)/255
        # Known light sclera around the iris is already authored. Preserve it,
        # instead of moving a generated white halo with the iris. White iris
        # highlights inside the matte core remain foreground, not eye backing.
        light = (original[...,:3].min(axis=2)>210) & (np.ptp(original[...,:3].astype(int),axis=2)<38)
        edge_highlight = np.zeros(support.shape,dtype=bool)
        x0,y0,_,_ = eye['box']
        for hx0,hy0,hx1,hy1 in eye['edgeHighlightRects']:
            edge_highlight[hy0-y0:hy1-y0,hx0-x0:hx1-x0] = True
        edge_highlight &= light & support
        keep = exterior_sclera(original,iris_mask,aperture) & ~edge_highlight
        b[keep] = s[keep]
        # Physical source-over inversion. This minimum alpha guarantees that
        # every foreground premultiplied channel lies in [0, alpha], without
        # signed correction overlays or clipping an impossible colour.
        difference = s-b
        lower = np.zeros_like(s)
        np.divide(difference,1-b,out=lower,where=difference>0)
        darker = np.zeros_like(s)
        np.divide(-difference,b,out=darker,where=difference<0)
        minimum = np.maximum(lower,darker).max(axis=2)
        alpha = np.maximum(soft,minimum)*support
        alpha[keep] = 0  # Known sclera is not a moving iris component.
        alpha[edge_highlight] = 1  # Authored bright reflection at the iris rim.
        premult = s-b*(1-alpha[...,None])
        premult[~support] = 0
        if (premult.min() < -1e-12 or (premult-alpha[...,None]).max() > 1e-12
                or alpha.min() < 0 or alpha.max() > 1+1e-12):
            raise ValueError('Iris matte cannot reconstruct with physical RGBA layers')
        foreground = np.dstack([np.clip(premult,0,1),np.clip(alpha,0,1)])
        results.append(dict(eye=eye,original=original,background=b,aperture=aperture,
                            support=support,foreground=foreground,knownSclera=keep))
    return results


def offsets(index, spec):
    if not isinstance(index,int) or isinstance(index,bool) or not 0 <= index < 16:
        raise ValueError('Gaze index must be 0..15')
    theta = index*math.tau/16
    x,y = spec['maximumDisplacementSourcePx']
    return x*math.sin(theta),-y*math.cos(theta)


def pose(source, eye_layers, dx, dy):
    if not math.isfinite(dx) or not math.isfinite(dy):
        raise ValueError('Invalid iris displacement')
    result = np.asarray(source).copy()
    for layer in eye_layers:
        x0,y0,x1,y1 = layer['eye']['box']
        yy,xx = np.mgrid[:y1-y0,:x1-x0].astype(float)
        moved = sample(layer['foreground'],xx-dx,yy-dy)
        rgb = layer['background']*(1-moved[...,3:4])+moved[...,:3]
        patch = result[y0:y1,x0:x1]
        selected = layer['aperture']
        patch[...,:3][selected] = np.clip(np.rint(rgb[selected]*255),0,255).astype(np.uint8)
        # Original alpha, eye outline and every pixel outside the opening stay.
    return Image.fromarray(result)


def aperture_union(source, eye_layers):
    allowed = np.zeros((source.height,source.width),dtype=bool)
    for layer in eye_layers:
        x0,y0,x1,y1 = layer['eye']['box']
        allowed[y0:y1,x0:x1] |= layer['aperture']
    return allowed


def backing(source, eye_layers):
    result = np.asarray(source).copy()
    for layer in eye_layers:
        x0,y0,x1,y1 = layer['eye']['box']
        selected = layer['support']
        result[y0:y1,x0:x1,:3][selected] = np.rint(layer['background'][selected]*255).astype(np.uint8)
    return Image.fromarray(result)


def contact(frames, width):
    height = round(width*208/192)
    board = Image.new('RGB',(4*(width+12),8*(height+26)),'#23252b')
    draw = ImageDraw.Draw(board)
    for background_row,bg in enumerate(('#23252b','#f1f0ee')):
        for index,frame in enumerate(frames):
            row,col = divmod(index,4)
            x,y = col*(width+12),(row+4*background_row)*(height+26)
            tile = Image.new('RGBA',frame.size,bg)
            tile.alpha_composite(frame)
            board.paste(tile.resize((width,height),Image.Resampling.NEAREST).convert('RGB'),(x+6,y+23))
            draw.text((x+3,y+3),f'{index}: {index*22.5:g} deg',fill='white')
    return board


def inputs():
    source, generated, spec = load_canonical(), load_generated(), specification()
    eye_layers = layers(source,generated,spec)
    transform = camera(clean_cutout(source)[0])
    regions,_ = idle_specification()
    return source,generated,spec,eye_layers,transform,regions,region_masks(regions)


def main():
    source,generated,spec,eye_layers,transform,regions,masks = inputs()
    neutral = pose(source,eye_layers,0,0)
    if neutral.tobytes() != source.tobytes():
        raise ValueError('Neutral gaze layers do not reconstruct the complete original RGBA image')
    allowed = aperture_union(source,eye_layers)
    art = backing(source,eye_layers)
    art.save(ART/'backing.png')
    Image.fromarray(allowed.astype(np.uint8)*255).save(ART/'allowed-mask.png')
    diagnostics = ROOT/'work/gaze-inspection'
    diagnostics.mkdir(parents=True,exist_ok=True)
    for name,image in [('source',source),('raw',generated),('backing',art),('neutral',neutral)]:
        grid(image,(420,235,805,410)).resize((770,350)).save(diagnostics/f'{name}-eyes-grid.png')
    for layer in eye_layers:
        pixels = layer['foreground'].copy()
        np.divide(pixels[...,:3],pixels[...,3:4],out=pixels[...,:3],where=pixels[...,3:4]>0)
        pixels[pixels[...,3]==0,:3] = 0
        Image.fromarray(np.clip(np.rint(pixels*255),0,255).astype(np.uint8)).save(ART/f"{layer['eye']['name']}-iris-diagnostic.png")
    OUT.mkdir(parents=True,exist_ok=True)
    poses,frames = [],[]
    zero_pose = dict(bodyY=0,earAngle=0,hairAngle=0)
    neutral_frame = render(clean_cutout(neutral)[0],zero_pose,transform,regions,masks)
    neutral_frame.save(OUT/'neutral.png')
    strip = Image.new('RGBA',(1536,416))
    for index in range(16):
        image = pose(source,eye_layers,*offsets(index,spec))
        if np.any(np.any(np.asarray(image)!=np.asarray(source),axis=2) & ~allowed):
            raise ValueError('Gaze changed a fixed face/body/ornament pixel')
        poses.append(image)
        frame = render(clean_cutout(image)[0],zero_pose,transform,regions,masks)
        frame.save(OUT/f'frame-{index}.png')
        frames.append(frame)
        strip.paste(frame,((index%8)*192,(index//8)*208))
    strip.save(OUT/'strip.webp',lossless=True,exact=True,method=6)
    for width in (80,113,192,224):
        contact(frames,width).save(OUT/f'contact-{width}px.png')
    board = Image.new('RGB',(4*385,4*175),'#ededed')
    draw = ImageDraw.Draw(board)
    for index,image in enumerate(poses):
        x,y = index%4*385,index//4*175
        board.paste(image.crop((420,235,805,410)).convert('RGB'),(x,y))
        draw.text((x+3,y+3),str(index),fill='#344860')
    board.save(OUT/'eyes-contact.png')
    raw_changed = np.any(np.asarray(generated)!=np.asarray(source),axis=2)
    art_metadata = dict(sourceSha256=ACCEPTED_SHA,generatedSha256=GENERATED_SHA,
        role='hidden eye backing only; not a visible pet face',fullRedrawAccepted=False,
        rawChangedPixelsOutsideEyeApertures=int(np.count_nonzero(raw_changed & ~allowed)),
        boundedChangedPixelsOutsideEyeApertures=0,neutralReconstructionRGBAExact=True,
        neutralReconstructionUsesSameLayers=True,diagnosticIrisPNGsAreQuantized=True,
        layerCompositing='nonnegative premultiplied material-colour layers with inverse matte; original face alpha coverage retained exactly',
        originalSourceAlphaPreservedExactly=True,
        facialGeometryRepair=False,eyeOutlineFixed=True,visualAcceptance='pending',installed=False,installableFullAtlas=False)
    (ART/'build.json').write_text(json.dumps(art_metadata,indent=2)+'\n',encoding='utf-8')
    metadata = dict(sourceSha256=ACCEPTED_SHA,eyeBackingGeneratedSha256=GENERATED_SHA,
        state='look',directionCount=16,nativeRows=[9,10],directionZero='up',clockwiseStepDegrees=22.5,
        sourceOffsetsPx=[offsets(index,spec) for index in range(16)],camera=transform,
        bodyRotated=False,artMirrored=False,irisShapeWarp=False,eyeOutlineFixed=True,
        facialGeometryRepair=False,neutralReconstructionRGBAExact=True,originalSourceModified=False,
        onlyEyeAperturesMayChange=True,frameHashes=[hashlib.sha256(frame.tobytes()).hexdigest().upper() for frame in frames],
        neutralFrameHash=hashlib.sha256(neutral_frame.tobytes()).hexdigest().upper(),
        visualAcceptance='pending',installed=False,installableFullAtlas=False,
        limitations=['Iris matte is estimated from visible source pixels, not an authored ground-truth eye layer; fine boundary uncertainty remains.',
                     'Only gaze is changed; no head turn or new native interpolation.',
                     'Small-scale direction legibility and naturalness require visual acceptance.',
                     'Native pointer priority remains unchanged; independent preview is not host integration.'])
    (OUT/'build.json').write_text(json.dumps(metadata,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in metadata.items() if k!='frameHashes'},indent=2))


if __name__ == '__main__':
    main()
