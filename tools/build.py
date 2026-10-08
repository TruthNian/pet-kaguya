"""HISTORICAL Phase 3 regression, never the selected v3 production source.

Small, continuous inverse displacement fields avoid cut-out seams. This is a
2-D deformation rig, not a true 3-D skeleton; its limits are documented.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from protocol import ATLAS_SIZE, COUNTS, DURATIONS, HEIGHT, NAMES, WIDTH, crop

ROOT = Path(__file__).resolve().parents[1]
SOURCE_HASH = '71F7E36AD459D99C9DE1AC6033A968CDF4C125EB742FFD5FF19B8E81BBA56EF7'
Y, X = np.mgrid[:HEIGHT, :WIDTH].astype(np.float64)


def smooth(a, b, x):
    t = np.clip((x-a)/(b-a), 0, 1)
    return t*t*(3-2*t)


def polygon(points, blur=4):
    mask = Image.new('L', (WIDTH, HEIGHT), 0)
    ImageDraw.Draw(mask).polygon(points, fill=255)
    return np.asarray(mask.filter(ImageFilter.GaussianBlur(blur)), dtype=float)/255


HEAD = 1-smooth(76, 108, Y)
TORSO = 1-smooth(143, 176, Y)
EAR_L = polygon([(28,91),(26,72),(53,27),(68,24),(61,54),(44,84)])
EAR_R = polygon([(125,24),(142,29),(168,79),(164,96),(145,83),(131,51)])
SHOE_LOCK = smooth(60,68,X)*(1-smooth(134,142,X))*smooth(162,176,Y)
HAIR = smooth(84, 165, Y)*((1-smooth(45,70,X))+smooth(122,148,X))*(1-SHOE_LOCK)
EYES = sum(np.exp(-(((X-x)/8)**4+((Y-55)/9)**4)) for x in [83,111])
EYES = np.clip(EYES,0,1)
WAVE = polygon([(42,24),(60,26),(63,50),(58,72),(72,87),
                (55,109),(34,103),(31,85),(42,53)], blur=5)
FRONT_LEG_R = polygon([(105,141),(128,138),(143,164),(169,189),
                       (158,204),(127,205),(115,171)], blur=6)
BACK_LEG_R = polygon([(91,138),(108,139),(111,155),(97,174),
                      (76,177),(68,162),(82,149)], blur=6)
FRONT_LEG_L = polygon([(62,138),(85,143),(78,170),(64,204),
                       (29,197),(27,174),(52,155)], blur=6)
BACK_LEG_L = polygon([(93,138),(107,138),(125,149),(129,171),
                      (108,176),(88,155)], blur=6)


def rotate_field(dx, dy, mask, pivot, degrees):
    angle = math.radians(degrees)
    px, py = pivot
    # An exact local rigid rotation, smoothly blended outside the limb.
    rx = (X-px)*math.cos(angle)-(Y-py)*math.sin(angle)+px-X
    ry = (X-px)*math.sin(angle)+(Y-py)*math.cos(angle)+py-Y
    return dx+rx*mask, dy+ry*mask


def parameters(row, phase):
    """Continuous periodic rig; phase 0 and phase 1 are exactly equivalent."""
    angle = 2*math.pi*(phase % 1)
    sine = math.sin(angle)
    lag = math.sin(angle-.55)
    p = dict(breath=.7*sine, head_x=.22*sine, tilt=.25*sine,
             ear=.8*lag, hair=.7*math.sin(angle-.9), bow=0., gaze_x=0.,
             gaze_y=0., lift=0., crouch=0., wave=0., stride=0., core=0.)
    if row in [1,2]:
        p.update(breath=-1.2*(1-math.cos(2*angle))/2,
                 head_x=0., tilt=0., ear=1.3*lag,
                 hair=1.5*math.sin(angle-.9), stride=9*sine)
    elif row == 3:
        p.update(wave=5*sine, ear=.6*lag, hair=.5*lag)
    elif row == 4:
        # One gentle hop, never a seated redraw. Anticipation, flight, landing.
        t = phase % 1
        knots = [0., *list(np.cumsum(DURATIONS[4])/sum(DURATIONS[4]))]
        lift = [0., 0., -7., -3., 0., 0.]
        crouch = [1., 1.5, 0., 0., .9, 1.]
        i = min(int(np.searchsorted(knots,t,side='right')-1),4)
        f = smooth(knots[i],knots[i+1],t)
        p.update(lift=lift[i]*(1-f)+lift[i+1]*f,
                 crouch=crouch[i]*(1-f)+crouch[i+1]*f,
                 breath=0., ear=1.4*lag, hair=1.0*lag, head_x=0., tilt=0.)
    elif row == 5:
        envelope = (1-math.cos(angle))/2
        p.update(bow=2.3*envelope, tilt=.25*sine, breath=.35*sine,
                 ear=.6*lag, hair=.5*math.sin(angle-.9), gaze_y=.25)
    elif row == 6:
        p.update(tilt=.65*sine, gaze_x=.3*sine, breath=.65*sine)
    elif row == 7:
        p.update(breath=.8*sine, core=(1-math.cos(angle))/2,
                 ear=.7*lag, hair=.55*math.sin(angle-.9))
    elif row == 8:
        p.update(tilt=1.0+1.0*sine, gaze_x=-.55, gaze_y=.3,
                 breath=.55*sine, ear=.6*lag, hair=.6*math.sin(angle-.9))
    return p


def coordinates(row, phase, direction=None):
    p = parameters(row,phase)
    if direction is not None:
        # Native direction 0=up, 90=right, 180=down, 270=left.
        a = math.radians(direction)
        p.update(breath=0., head_x=1.0*math.sin(a),
                 tilt=1.3*math.sin(a), bow=.65*math.cos(a+math.pi),
                 gaze_x=1.45*math.sin(a), gaze_y=-.75*math.cos(a),
                 ear=.35*math.sin(a), hair=.4*math.sin(a))
    dx = p['head_x']*HEAD+p['hair']*HAIR
    dy = -p['breath']*TORSO+p['bow']*HEAD+p['crouch']*TORSO+p['lift']
    dx,dy = rotate_field(dx,dy,HEAD,(96,79),p['tilt'])
    if row not in [1,2]:
        dx,dy = rotate_field(dx,dy,EAR_L,(60,34),p['ear'])
        dx,dy = rotate_field(dx,dy,EAR_R,(133,34),-p['ear']*.85)
        dx += p['gaze_x']*EYES
        dy += p['gaze_y']*EYES
    if row == 3:
        dx,dy = rotate_field(dx,dy,WAVE,(52,76),p['wave'])
    if row == 1:
        dx,dy = rotate_field(dx,dy,FRONT_LEG_R,(119,143),p['stride'])
        dx,dy = rotate_field(dx,dy,BACK_LEG_R,(98,146),-p['stride']*.8)
    if row == 2:
        dx,dy = rotate_field(dx,dy,FRONT_LEG_L,(70,146),p['stride'])
        dx,dy = rotate_field(dx,dy,BACK_LEG_L,(102,146),-p['stride']*.8)
    # Fixed 3% framing reserve gives a compatible hop headroom. This is not
    # higher resolution and does not create detail. Standing feet are pinned.
    sx = (X-96-dx)/.97+96
    sy = (Y-202-dy)/.97+202
    return sx,sy,p


def resample(image, sx, sy):
    arr = np.asarray(image,dtype=np.float64)/255.
    arr[...,:3] *= arr[...,3:4]
    x0,y0 = np.floor(sx).astype(int),np.floor(sy).astype(int)
    wx,wy = sx-x0,sy-y0
    output = np.zeros((HEIGHT,WIDTH,4),dtype=np.float64)
    for ox,oy,weight in [(0,0,(1-wx)*(1-wy)),(1,0,wx*(1-wy)),
                          (0,1,(1-wx)*wy),(1,1,wx*wy)]:
        xx,yy = x0+ox,y0+oy
        valid = (xx>=0)&(xx<WIDTH)&(yy>=0)&(yy<HEIGHT)
        output[valid] += arr[yy[valid],xx[valid]]*weight[valid,None]
    alpha = output[...,3:4]
    output[...,:3] = np.divide(output[...,:3],alpha,
                             out=np.zeros_like(output[...,:3]),where=alpha>0)
    result = np.clip(np.rint(output*255),0,255).astype(np.uint8)
    result[result[...,3]==0,:3]=0
    return Image.fromarray(result)


def expression_patch(master, donor, offset=(0,0), eyes=True):
    # Only expression features; costume, ornament, skin outline are untouched.
    donor = donor.transform((WIDTH,HEIGHT), Image.Transform.AFFINE,
                            (1,0,-offset[0],0,1,-offset[1]),
                            Image.Resampling.BICUBIC)
    mask = Image.new('L',(WIDTH,HEIGHT),0)
    d = ImageDraw.Draw(mask)
    if eyes:
        d.ellipse((68,43,96,69),fill=255)
        d.ellipse((98,42,128,68),fill=255)
    d.ellipse((87,59,108,77),fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(.6))
    result = Image.composite(donor,master,mask)
    # Expression donors cannot alter source transparency.
    result.putalpha(master.getchannel('A'))
    return result


def masters(atlas):
    idle = crop(atlas,0,0)
    # Existing processing mouth is a quiet smile; align it to idle's mouth.
    quiet = expression_patch(idle,crop(atlas,7,0),eyes=False)
    sad = expression_patch(quiet,crop(atlas,5,0),offset=(3,-20))
    return [quiet,crop(atlas,1,0),crop(atlas,2,0),crop(atlas,3,1),
            quiet,sad,crop(atlas,6,0),crop(atlas,7,0),crop(atlas,8,3)]


def core_pulse(im,amount):
    a = np.asarray(im).copy()
    rgb = a[...,:3].astype(float)
    region = (X>85)&(X<111)&(Y>92)&(Y<112)&(a[...,3]>0)
    teal = region&(rgb[...,1]>rgb[...,0]+12)&(rgb[...,2]>rgb[...,0]+12)
    # Secondary cue, not the only evidence of activity. Do not add a new prop.
    weight = (.06+.20*amount)*teal[...,None]
    a[...,:3] = np.rint(rgb*(1-weight)+np.array([88,232,207])*weight).astype('uint8')
    return Image.fromarray(a)


def render(master,row,phase,direction=None):
    sx,sy,p = coordinates(row,phase,direction)
    im = resample(master,sx,sy)
    if row == 7:
        im = core_pulse(im,p['core'])
    # Normalize run foot contact after leg articulation. Ground y=202 is fixed;
    # the resulting vertical body movement is a 2-D jogging approximation.
    if row in [1,2]:
        a = np.asarray(im)
        ys = np.where((a[...,3]>32)&(Y>153))[0]
        if len(ys):
            shift = 202-int(ys.max())
            translated = Image.new('RGBA',im.size)
            translated.alpha_composite(im,(0,shift))
            im = translated
    # Bound newly resampled RGB precision to the baseline's 4-level grid.
    # Maximum per-channel error <=2; alpha/geometry are not quantized.
    a=np.asarray(im).copy()
    rgb=a[...,:3].astype(np.uint16)
    a[...,:3]=np.minimum(((rgb+2)//4)*4,255).astype(np.uint8)
    a[a[...,3]==0,:3]=0
    return Image.fromarray(a)


def historical_arguments(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--historical-phase3', action='store_true',
                        help='Explicitly opt in to rejected historical regression only')
    parser.add_argument('--out', type=Path,
                        help='Required isolated output subdirectory under repository work/')
    args = parser.parse_args(argv)
    if not args.historical_phase3 or args.out is None:
        parser.error('Historical tool only. Use --historical-phase3 and --out work/<regression>; '
                     'the selected v3 source is built by tools/build_idle.py, not this tool.')
    args.out = args.out.resolve()
    work = (ROOT/'work').resolve()
    if args.out == work or not args.out.is_relative_to(work):
        parser.error('Historical output must be an isolated subdirectory under repository work/; '
                     'pet/, sources/, candidates/ and installed pets cannot be overwritten.')
    return args


def main():
    args = historical_arguments()
    source = ROOT/'baseline/phase2/spritesheet.webp'
    digest = hashlib.sha256(source.read_bytes()).hexdigest().upper()
    if digest != SOURCE_HASH:
        raise SystemExit('Refusing to build: immutable source hash changed')
    atlas = Image.open(source).convert('RGBA')
    if atlas.size != ATLAS_SIZE:
        raise SystemExit('Invalid local v2 source size')
    base = masters(atlas)
    out = Image.new('RGBA',ATLAS_SIZE)
    frames_meta=[]
    for row,durations in enumerate(DURATIONS):
        elapsed=0
        for col,duration in enumerate(durations):
            phase=elapsed/sum(durations)
            im = render(base[row],row,phase)
            out.paste(im,(col*WIDTH,row*HEIGHT))
            frames_meta.append(dict(row=row,col=col,phase=phase,durationMs=duration))
            elapsed+=duration
    out.paste(render(base[0],0,0),(6*WIDTH,0))
    for i in range(16):
        im=render(base[0],0,0,direction=i*22.5)
        out.paste(im,((i%8)*WIDTH,(9+i//8)*HEIGHT))
    args.out.mkdir(parents=True,exist_ok=True)
    dest=args.out/'spritesheet.webp'
    out.save(dest,'WEBP',lossless=True,method=6,exact=True)
    config=json.loads((ROOT/'baseline/phase2/pet.json').read_text(encoding='utf-8'))
    config['description']='A gentle moon-rabbit Kaguya with restrained breathing, ear and hair motion.'
    (args.out/'pet.json').write_text(json.dumps(config,indent=2)+'\n',encoding='utf-8')
    metadata=dict(sourceSha256=digest,outputSha256=hashlib.sha256(dest.read_bytes()).hexdigest().upper(),
                  outputBytes=dest.stat().st_size,atlasSize=list(ATLAS_SIZE),
                  cellSize=[WIDTH,HEIGHT],frames=frames_meta,
                  method='locked original-pixel poses and continuous 2-D deformation fields',
                  generatedArtwork=False,globalFramingScale=.97,rgbQuantizationStep=4,
                  nativeTimingChanged=False,nativeFrameCountChanged=False)
    (args.out/'build.json').write_text(json.dumps(metadata,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in metadata.items() if k!='frames'},indent=2))


if __name__=='__main__':
    main()
