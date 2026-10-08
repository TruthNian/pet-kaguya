"""Compare ONE generated full mother pose, not nine independent redraws.

The model did not obey the requested mouth-only edit. This artwork is a whole
redraw, requiring separate user agreement. Uniform fitting is PREVIEW ONLY;
no installed/pet atlas or original pixel files are touched.
"""
from pathlib import Path
import hashlib
import json

import numpy as np
from PIL import Image, ImageDraw
from prepare_identity import load_source
from protocol import WIDTH, HEIGHT, crop

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'candidates/phase4/canonical-v2'


def bbox_alpha(image,threshold=0):
    a=np.asarray(image)[...,3]>threshold
    ys,xs=np.where(a)
    if not len(xs):raise ValueError('Empty canonical artwork')
    return (int(xs.min()),int(ys.min()),int(xs.max()+1),int(ys.max()+1))


def fit_for_preview(image,reference):
    box=bbox_alpha(image)
    refbox=bbox_alpha(reference)
    bw,bh=box[2]-box[0],box[3]-box[1]
    scale=min((refbox[3]-refbox[1])/bh,(WIDTH-4)/bw,(HEIGHT-4)/bh)
    size=(round(bw*scale),round(bh*scale))
    # One uniform scale, no stretching or face/body independently fitting.
    reduced=image.crop(box).convert('RGBa').resize(size,Image.Resampling.LANCZOS).convert('RGBA')
    x=round((refbox[0]+refbox[2]-size[0])/2)
    y=refbox[3]-size[1]
    out=Image.new('RGBA',(WIDTH,HEIGHT))
    out.alpha_composite(reduced,(x,y))
    a=np.asarray(out).copy()
    a[a[...,3]==0,:3]=0
    return Image.fromarray(a),dict(inputAlphaBbox=list(box),referenceAlphaBbox=list(refbox),
                                  uniformScale=scale,paste=[x,y],resizedSize=list(size))


def composite(im,bg):
    out=Image.new('RGBA',im.size,bg)
    out.alpha_composite(im)
    return out.convert('RGB')


def main():
    rawpath=OUT/'artwork.png'
    artwork=Image.open(rawpath).convert('RGBA')
    original=crop(load_source(),0,0)
    rejected=Image.open(ROOT/'candidates/phase4/static/idle.png').convert('RGBA')
    front,transform=fit_for_preview(artwork,original)
    front.save(OUT/'front.png')
    for width in [80,113,192,224]:
        height=round(width*HEIGHT/WIDTH)
        panel=Image.new('RGB',(3*(width+20),2*(height+28)),'#23252b')
        d=ImageDraw.Draw(panel)
        for bgrow,bg in enumerate(['#23252b','#f1f0ee']):
            for i,(label,im) in enumerate([('original',original),('rejected4',rejected),('new master',front)]):
                x,y=i*(width+20),bgrow*(height+28)
                scaled=im.resize((width,height),Image.Resampling.NEAREST)
                panel.paste(composite(scaled,bg),(x+10,y+24))
                d.text((x+3,y+3),label,fill='white')
        panel.save(OUT/f'comparison-{width}px.png')
    metadata=dict(artworkSha256=hashlib.sha256(rawpath.read_bytes()).hexdigest().upper(),
                  artworkSize=list(artwork.size),previewSha256=hashlib.sha256(front.tobytes()).hexdigest().upper(),
                  generationMode='built-in image_gen edit with original r0c0 reference',
                  requestedScope='mouth only',actualScope='whole-character redraw; mouth-only invariant failed',
                  generatedArtwork=True,originalClothingPixelsPreserved=False,editedOnlyMouth=False,
                  nativeResolutionChanged=False,previewCellSize=[WIDTH,HEIGHT],
                  animationBuilt=False,userAdoptionAgreement='pending',transform=transform)
    (OUT/'review.json').write_text(json.dumps(metadata,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(metadata,indent=2))


if __name__=='__main__':main()
