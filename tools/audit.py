from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from protocol import ATLAS_SIZE, COUNTS, DURATIONS, HEIGHT, NAMES, WIDTH, crop

ROOT=Path(__file__).resolve().parents[1]


def signature(a):
    f=a.astype(float)/255
    return np.concatenate((f[...,:3]*f[...,3:4],f[...,3:4]),axis=2)


def pair(a,b):
    delta=np.abs(signature(a)-signature(b))
    va,vb=a[...,3]>32,b[...,3]>32
    ca=np.argwhere(va).mean(axis=0)
    cb=np.argwhere(vb).mean(axis=0)
    return dict(changedPixelPct=round(float((delta.max(axis=2)>2/255).mean()*100),4),
                premultipliedRgbMae=round(float(delta[...,:3].mean()*255),4),
                silhouetteXorPct=round(float((va^vb).sum()/max(1,(va|vb).sum())*100),4),
                centroidShiftPx=round(float(np.linalg.norm(ca-cb)),4),
                exactlyEqual=bool(np.array_equal(a,b)))


def composite(im,bg):
    out=Image.new('RGBA',im.size,bg)
    out.alpha_composite(im)
    return out.convert('RGB')


def analyze(path):
    im=Image.open(path).convert('RGBA')
    arr=np.asarray(im)
    result=dict(sha256=hashlib.sha256(path.read_bytes()).hexdigest().upper(),
                bytes=path.stat().st_size,size=list(im.size),decodedRgbaBytes=arr.size,
                transparentRgbResidue=int(((arr[...,3]==0)&np.any(arr[...,:3]!=0,axis=2)).sum()),
                missing=[],unexpected=[],borderContacts=[],sequences={})
    for row,count in enumerate(COUNTS):
        for col in range(8):
            a=np.asarray(crop(im,row,col))
            visible=a[...,3]>0
            if col<count and not visible.any(): result['missing'].append([row,col])
            if col>=count and visible.any(): result['unexpected'].append([row,col])
            if visible[0,:].any() or visible[-1,:].any() or visible[:,0].any() or visible[:,-1].any():
                result['borderContacts'].append([row,col])
    for row,durations in enumerate(DURATIONS):
        frames=[np.asarray(crop(im,row,col)) for col in range(len(durations))]
        pairs=[pair(a,frames[(i+1)%len(frames)]) for i,a in enumerate(frames)]
        result['sequences'][NAMES[row]]=dict(
            uniqueFrames=len({hashlib.sha256(a.tobytes()).hexdigest() for a in frames}),
            durationsMs=durations,cycleMs=sum(durations),
            nominalPoseUpdatesPerSecond=round(len(frames)*1000/sum(durations),4),
            maxChangedPixelPct=max(p['changedPixelPct'] for p in pairs),
            meanChangedPixelPct=round(float(np.mean([p['changedPixelPct'] for p in pairs])),4),
            maxCentroidShiftPx=max(p['centroidShiftPx'] for p in pairs),
            allSilhouettesExactlyEqual=all(np.array_equal(frames[0][...,3],a[...,3]) for a in frames),
            pairs=pairs)
    result['directions']=[pair(np.asarray(crop(im,9+i//8,i%8)),
                               np.asarray(crop(im,9+((i+1)%16)//8,(i+1)%8))) for i in range(16)]
    return result


def galleries(atlas,out,prefix):
    for label,bg in [('dark','#20232a'),('light','#f1f0ee')]:
        panel=Image.new('RGB',(8*WIDTH,11*(HEIGHT+20)),bg)
        d=ImageDraw.Draw(panel)
        color='white' if label=='dark' else 'black'
        for row,name in enumerate(NAMES):
            for col in range(8):
                x,y=col*WIDTH,row*(HEIGHT+20)
                panel.paste(composite(crop(atlas,row,col),bg),(x,y+20))
                d.text((x+3,y+2),f'{name} {col}',fill=color)
        panel.save(out/f'{prefix}-{label}.webp','WEBP',quality=95)
    for row,durations in enumerate(DURATIONS):
        frames=[composite(crop(atlas,row,col),'#20232a') for col in range(len(durations))]
        frames[0].save(out/f'{prefix}-{NAMES[row]}.gif',save_all=True,
                       append_images=frames[1:],duration=durations,loop=0,disposal=2,optimize=False)


def comparison(old,new,out):
    for size in [80,113,192,224]:
        h=round(size*HEIGHT/WIDTH)
        panel=Image.new('RGB',(9*(size+14),2*(h+32)),'#20232a')
        d=ImageDraw.Draw(panel)
        for version,atlas in enumerate([old,new]):
            for row,name in enumerate(NAMES[:9]):
                x,y=row*(size+14),version*(h+32)
                im=crop(atlas,row,0).resize((size,h),Image.Resampling.NEAREST)
                panel.paste(composite(im,'#20232a'),(x+7,y+22))
                d.text((x+2,y+2),f'{"old" if version==0 else "new"} {name}',fill='white')
        panel.save(out/f'comparison-{size}px.png')


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',type=Path,default=ROOT/'qa')
    args=parser.parse_args()
    args.output.mkdir(parents=True,exist_ok=True)
    oldpath=ROOT/'baseline/phase2/spritesheet.webp'
    newpath=ROOT/'pet/spritesheet.webp'
    old=Image.open(oldpath).convert('RGBA')
    new=Image.open(newpath).convert('RGBA')
    result=dict(baseline=analyze(oldpath),candidate=analyze(newpath),
                note='Image differences are diagnostics, not naturalness scores. All previews are simulations, not native application screenshots.')
    (args.output/'comparison.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    galleries(new,args.output,'candidate')
    comparison(old,new,args.output)
    # Small targeted sequence for manual judgement, never cropped face alone.
    for row in [0,1,3,4,5,6,7,8]:
        count=len(DURATIONS[row])
        panel=Image.new('RGB',(count*WIDTH,HEIGHT+24),'#20232a')
        d=ImageDraw.Draw(panel)
        for col in range(count):
            panel.paste(composite(crop(new,row,col),'#20232a'),(col*WIDTH,24))
            d.text((col*WIDTH+3,3),f'{col} {DURATIONS[row][col]} ms',fill='white')
        panel.save(args.output/f'{NAMES[row]}-sequence.png')
    print(json.dumps({version:{k:v for k,v in obj.items() if k not in ['sequences','directions']}
                      for version,obj in result.items() if isinstance(obj,dict)},indent=2))


if __name__=='__main__': main()
