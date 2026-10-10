"""Accepted mouth-only development basis; no full-motion or host approval."""
import hashlib
import json
import numpy as np
from PIL import Image, ImageDraw
from canonical import ROOT, ACCEPTED_SHA, bounded_masks, load_canonical, clean_cutout, camera
from guide_failed_mouth import OUT, BOX, SIDE, parent, line_diagnostic
import review_failed
from review_wave import native_frame
from review_review_v2 import comparison

GENERATED_SHA = '695E3EC9867FB8A8A919E203E607A19D0E3A0AA7D469BDEA847B6E56397F3082'
RAW_SIZE = (1254, 1254)
POLYGON = [(589,393),(645,393),(645,414),(589,414)]
DECISION = 'sources/canonical/failed-mouth-decision-20261010.json'


def decision():
    record = json.loads((ROOT/DECISION).read_text(encoding='utf-8'))
    if (record['scope'] != 'mouth-line-development-basis-only'
            or record['mouthGeneratedSha256'] != GENERATED_SHA
            or any(record[key] is not False for key in ('fullMotionApproved',
                'faceGeometryChangeApproved','hostChangeApproved','installationApproved'))):
        raise ValueError('Mouth approval cannot silently expand beyond its actual scope')
    return record


def rgba_hash(image):
    return hashlib.sha256(image.tobytes()).hexdigest().upper()


def inputs():
    before = parent()
    path = OUT / 'generated.png'
    if hashlib.sha256(path.read_bytes()).hexdigest().upper() != GENERATED_SHA:
        raise ValueError('Frozen raw mouth artwork changed')
    with Image.open(path) as image:
        raw = image.convert('RGBA')
    if raw.size != RAW_SIZE:
        raise ValueError('Actual raw square dimensions changed; never object-fit the line')
    square = raw.convert('RGBa').resize((SIDE, SIDE), Image.Resampling.LANCZOS).convert('RGBA')
    mapped = before.copy()
    mapped.paste(square.crop((0, 0, BOX[2]-BOX[0], BOX[3]-BOX[1])), BOX[:2])
    return before, mapped


def compose(before, mapped):
    expected_before, expected_mapped = inputs()
    if rgba_hash(before) != rgba_hash(expected_before) or rgba_hash(mapped) != rgba_hash(expected_mapped):
        raise ValueError('Cannot silently change the recorded parent or fixed crop')
    allowed, weight, _ = bounded_masks(before.size, [POLYGON], 1.5)
    a, b = np.asarray(before), np.asarray(mapped)
    if np.any(b[...,3][allowed] == 0):
        raise ValueError('Missing skin coverage inside the inspected mouth permission')
    result = a.copy()
    rgb = np.rint(a[...,:3].astype(float)*(1-weight[...,None]) + b[...,:3]*weight[...,None])
    result[allowed,:3] = np.clip(rgb[allowed], 0, 255).astype(np.uint8)
    # Alpha from the raw artwork is retained in generated.png but not copied:
    # this is internal line artwork, not a new foreground silhouette.
    return Image.fromarray(result), allowed, Image.fromarray(np.rint(weight*255).astype(np.uint8))


def main():
    decision()
    before, mapped = inputs()
    pose, allowed, weight = compose(before, mapped)
    pose.save(OUT/'pose.png')
    mapped.save(OUT/'mapped-material.png')
    Image.fromarray(allowed.astype(np.uint8)*255).save(OUT/'allowed-mask.png')
    weight.save(OUT/'blend-weight.png')
    mother = load_canonical()
    frames = [native_frame(image) for image in (mother,before,pose)]
    frames[-1].save(OUT/'frame.png')
    for width in (80,113,192,224):
        comparison(frames,width,['locked mother','old mouth','accepted mouth basis']).save(OUT/f'contact-{width}px.png')
    box = (420,195,790,475)
    board = Image.new('RGB',(1110,310),'#252830')
    draw = ImageDraw.Draw(board)
    for i,(label,source) in enumerate(zip(['locked mother','old mouth','accepted mouth basis'],[mother,before,pose])):
        tile = Image.new('RGBA',(370,280),'#ededed')
        tile.alpha_composite(source.crop(box))
        board.paste(tile.convert('RGB'),(370*i,30))
        draw.text((370*i+6,8),label,fill='white')
    board.save(OUT/'detail.png')
    a,b,c = np.asarray(before),np.asarray(pose),np.asarray(mapped)
    changed = np.any(a!=b,axis=2)
    metadata = dict(sourceSha256=ACCEPTED_SHA,parentPoseRGBAHash=rgba_hash(before),
        generatedSha256=GENERATED_SHA,rawCanvas=list(RAW_SIZE),sourceCrop=list(BOX),
        wholeSquareProjection=True,objectBoundsFitting=False,permissionPolygon=POLYGON,
        edgeFeatherSourcePx=1.5,allowedPixels=int(allowed.sum()),changedPixels=int(changed.sum()),
        changedOutsidePermission=int((changed&~allowed).sum()),alphaChangedPixels=int((a[...,3]!=b[...,3]).sum()),
        rawChangesOutsidePermission=int((np.any(a!=c,axis=2)&~allowed).sum()),
        oldMouthLineDiagnostic=line_diagnostic(before),acceptedMouthLineDiagnostic=line_diagnostic(pose),
        originalSmileLineDiagnostic=line_diagnostic(mother),diagnosticDefinesPermission=False,
        poseRGBAHash=rgba_hash(pose),frameRGBAHash=rgba_hash(frames[-1]),
        camera=camera(clean_cutout(mother)[0]),sameSourceCoordinateCamera=True,
        facialGeometryRepair=False,newFaceGeometry=False,eyesBrowsJawCostumeRGBAExact=True,
        newArtworkGenerated=True,generatedAlphaRetainedInRaw=True,alphaAdopted=False,
        fullRedrawAccepted=False,adopted=True,adoptionScope='mouth-line-development-basis-only',
        userDecision=DECISION,mouthLineVisualApproval='approved-as-development-basis',
        visualAcceptance='mouth-only; full-motion-pending',installed=False,installableFullAtlas=False,
        generationMode='built-in imagegen',prompt='candidates/phase5/failed-mouth-v2/prompt.txt',
        limitation='Changes RGB throughout the bounded internal mouth patch, including nearby skin; '
            'not literally only brown-line pixels. Original width/stroke style are visual targets, '
            'not guaranteed by prompt or threshold diagnostics. Mouth approval does not approve '
            'full action, transitions, small-size legibility, installation or FPS/resolution gain.')
    for x0,y0,x1,y1 in review_failed.specification()['eyeProtectedRects']:
        if allowed[y0:y1,x0:x1].any():
            raise ValueError('The recorded mouth permission overlaps a protected eye')
    if metadata['changedOutsidePermission'] or metadata['alphaChangedPixels']:
        raise ValueError('Mouth artwork escaped RGB-only permission')
    (OUT/'build.json').write_text(json.dumps(metadata,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(metadata,indent=2))


if __name__ == '__main__':
    main()
