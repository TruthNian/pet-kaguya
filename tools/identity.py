"""Static identity candidate, before animation.

No translated donor face/skin is composited. Expression lines are small,
deterministic edits on the same face. Front poses share that head plate;
side-running poses retain their own projection and are not face-swapped.
These are review candidates, not a claim of anatomical or aesthetic approval.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from prepare_identity import load_source, SOURCE_HASH
from protocol import WIDTH, HEIGHT, NAMES, crop

ROOT = Path(__file__).resolve().parents[1]
Y, X = np.mgrid[:HEIGHT,:WIDTH]
SIZE = (WIDTH,HEIGHT)


def shape(points, feather=0.):
    im = Image.new('L',SIZE,0)
    ImageDraw.Draw(im).polygon(points,fill=255)
    return im.filter(ImageFilter.GaussianBlur(feather)) if feather else im


def mouth_mask():
    # This is INSIDE the reviewed face, above its chin at y=75..77.
    im = Image.new('L',SIZE,0)
    ImageDraw.Draw(im).ellipse((89,63,105,73),fill=255)
    return im


def skin_bridge(image, mask, left=88, right=106):
    """Fill a small feature with same-face skin, interpolated from its sides.

    Not a general inpainting method. Callers must supply a bounded interior
    mask and verify that the side samples are skin, not hair/eyelashes.
    """
    a = np.asarray(image).copy()
    original = a.copy()
    m = np.asarray(mask)/255.
    yy,xx = np.where(m>0)
    for y in np.unique(yy):
        xs = xx[yy==y]
        t = ((xs-left)/(right-left))[:,None]
        rgb = original[y,left,:3]*(1-t)+original[y,right,:3]*t
        weight = m[y,xs,None]
        a[y,xs,:3] = np.rint(original[y,xs,:3]*(1-weight)+rgb*weight).astype('uint8')
    return Image.fromarray(a)


def stroke(image, points, color, width=1.):
    """Antialias the new line only; do NOT resample the original artwork."""
    factor = 8
    layer = Image.new('RGBA',(WIDTH*factor,HEIGHT*factor))
    ImageDraw.Draw(layer).line([(round(x*factor),round(y*factor)) for x,y in points],
                              fill=(*color,255),width=round(width*factor),joint='curve')
    layer = layer.resize(SIZE,Image.Resampling.LANCZOS)
    result = image.copy()
    result.alpha_composite(layer)
    result.putalpha(image.getchannel('A'))
    return result


def quiet_face(original):
    im = skin_bridge(original,mouth_mask())
    # A closed, restrained smile. Colour is sampled from the source mouth.
    color = tuple(int(v) for v in np.asarray(original)[65,94,:3])
    return stroke(im,[(94.,68.0),(96.,69.0),(98.,69.4),(100.,69.0),(101.,68.0)],color,.85)


def sad_face(original):
    im = skin_bridge(original,mouth_mask())
    # Rejected experiment: flattening eyelids read as sleepy and erased the
    # source's eye-line character. Keep the eyes/irises exactly unchanged.
    a = np.asarray(original)
    # A worried visible brow, edited inside forehead skin. The other brow is
    # hidden by the fringe and must not be invented on top of the hair.
    brow = shape([(104,39),(110,39),(118,42),(118,44),(110,43),(104,42)])
    im = skin_bridge(im,brow,left=102,right=120)
    brow_color = tuple(int(v) for v in a[42,115,:3])
    im = stroke(im,[(105.,40.5),(108.,40.0),(112.,41.0),(117.,43.0)],brow_color,.9)
    color = tuple(int(v) for v in a[65,94,:3])
    im = stroke(im,[(95.,69.5),(97.,68.5),(99.,68.5),(101.,69.5)],color,.85)
    im.putalpha(original.getchannel('A'))
    return im


def head_mask():
    # Head AND ears are one plate here: erase the old crown/ornament instead of
    # leaving residual donor pixels outside an interior face patch. Boundaries
    # end in back hair/collar, not through eyes or the jawline. Foreground arms
    # must be restored explicitly. Not a universal mask for side projections.
    mask=shape([(0,0),(191,0),(191,78),(175,98),(151,98),(130,83),
                (113,82),(85,82),(65,83),(45,98),(20,98),(0,78)],.65)
    a=np.asarray(mask).copy()
    a[:75,:]=255
    return Image.fromarray(a)


def front_pose(body,head,foreground=None):
    im = Image.composite(head,body,head_mask())
    if foreground is not None:
        im = Image.composite(body,im,foreground)
    # Alpha at the head boundary comes from the composited plate, not a forced
    # copy of body alpha. Transparent RGB is canonicalized, never filled black.
    a = np.asarray(im).copy()
    a[a[...,3]==0,:3] = 0
    return Image.fromarray(a)


def static_masters(source=None):
    source = source if source is not None else load_source()
    original = crop(source,0,0)
    quiet = quiet_face(original)
    sad = sad_face(original)
    # The chin-touching hand is foreground, including its dark contour.
    hand = shape([(76,79),(78,75),(83,75),(88,78),(91,85),(87,95),(75,95)])
    waiting = front_pose(crop(source,7,1),quiet,hand)
    processing = front_pose(crop(source,7,0),quiet)
    wave_arm = shape([(40,26),(50,22),(60,26),(64,41),(59,62),(61,76),
                      (70,91),(65,105),(34,107),(29,84),(37,59),(43,43)])
    waving = front_pose(crop(source,3,1),quiet,wave_arm)
    # r8c3's bowed head/neck is too low for this frontal plate: it left a strip
    # of the old face below the new chin. Use the upright inspecting gesture.
    review_hand = shape([(82,85),(86,79),(91,72),(98,71),(100,75),
                         (95,80),(95,87),(91,96),(82,96)])
    review = front_pose(crop(source,8,2),quiet,review_hand)
    return [quiet,crop(source,1,0),crop(source,2,0),waving,quiet,sad,
            waiting,processing,review]


def composite(image,bg):
    out = Image.new('RGBA',image.size,bg)
    out.alpha_composite(image)
    return out.convert('RGB')


def review_panels(masters,out):
    previous = Image.open(ROOT/'baseline/phase3/spritesheet.webp').convert('RGBA')
    rows = [0,5,6,7,3,8]
    for width in [80,113,192,224]:
        height = round(width*HEIGHT/WIDTH)
        board = Image.new('RGB',(len(rows)*(width+16),2*(height+32)),'#23252b')
        d = ImageDraw.Draw(board)
        for version in range(2):
            for i,row in enumerate(rows):
                im = crop(previous,row,0) if version==0 else masters[row]
                im = im.resize((width,height),Image.Resampling.NEAREST)
                x,y=i*(width+16),version*(height+32)
                board.paste(composite(im,'#23252b'),(x+8,y+24))
                d.text((x+2,y+3),f'{"phase3" if version==0 else "static4"} {NAMES[row]}',fill='white')
        board.save(out/f'static-comparison-{width}px.png')
    # Same crop/scale, no face-by-face bounding-box fitting.
    face = Image.new('RGB',(6*352,2*320+48),'#23252b')
    d = ImageDraw.Draw(face)
    for version in range(2):
        for i,row in enumerate(rows):
            im = crop(previous,row,0) if version==0 else masters[row]
            im = im.crop((52,20,140,100)).resize((352,320),Image.Resampling.NEAREST)
            x,y=i*352,version*344
            face.paste(composite(im,'#23252b'),(x,y+24))
            d.text((x+3,y+3),f'{"phase3" if version==0 else "static4"} {NAMES[row]}',fill='white')
    face.save(out/'static-faces.png')


def main():
    out = ROOT/'candidates/phase4/static'
    out.mkdir(parents=True,exist_ok=True)
    masters = static_masters()
    for name,im in zip(NAMES,masters):
        im.save(out/f'{name}.png')
    review_panels(masters,out)
    metadata = dict(sourceSha256=SOURCE_HASH,phase='static identity review; animation not rebuilt',
                    frontHeadSource=[0,0],frontBodySources={'waiting':[7,1],'running':[7,0],
                                                          'waving':[3,1],'review':[8,2]},
                    expressionMethod='bounded same-face skin bridge and procedural mouth/brow lines; eyes unchanged',
                    donorFaceCompositing=False,globalFramingScale=1.,rgbQuantizationStep=None,
                    automaticChecksDoNotProveBeauty=True,
                    userDirectionAgreement='original front idle proportions; closed smile; mild failed; chin-touching waiting',
                    userVisualApproval='rejected: user reports bad Phase 4 faces and clothing; Phase 3 has different problems',
                    approvedForAnimation=False,
                    frameHashes={name:hashlib.sha256(im.tobytes()).hexdigest().upper()
                                 for name,im in zip(NAMES,masters)})
    (out/'review.json').write_text(json.dumps(metadata,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in metadata.items() if k!='frameHashes'},indent=2))


if __name__ == '__main__':
    main()
