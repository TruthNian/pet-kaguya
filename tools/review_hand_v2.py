"""Background-conditioned hand layer with a measured neutral reconstruction."""
import hashlib
import json
import math

import numpy as np
from PIL import Image,ImageDraw,ImageFilter

from canonical import ROOT,ACCEPTED_SHA,load_canonical
from review_hand import inputs,HAND,ANCHOR,PARENT_HASH
from review_review_v2 import comparison,specification as parent_spec
from review_wave import native_frame

OUT = ROOT/'candidates/phase5/review-hand-v2'
BOX = (492,670,612,741)
BACKGROUND_HASH = '3FCEE4E4EB55B119CA1BD126E56BCAC7610027E1A5A4D9507A8CA4B9275432A3'


def materials(parent,background):
    if hashlib.sha256(parent.tobytes()).hexdigest().upper()!=PARENT_HASH:
        raise ValueError('Hand material needs the unchanged current parent')
    if (background.size!=parent.size
            or hashlib.sha256(background.tobytes()).hexdigest().upper()!=BACKGROUND_HASH):
        raise ValueError('Hand background changes the recorded plate/camera')
    mask = Image.new('L',parent.size)
    ImageDraw.Draw(mask).polygon(HAND,fill=255)
    mask = mask.filter(ImageFilter.MaxFilter(7)).filter(ImageFilter.GaussianBlur(.8))
    protected = Image.new('L',parent.size)
    draw = ImageDraw.Draw(protected)
    draw.polygon(parent_spec()['preservedForegroundPolygons'][4],fill=255)
    # The current cream cuff/forearm must stay still as well as the wrist.
    draw.rectangle((600,714,620,742),fill=255)
    protection = np.asarray(protected)>0
    allowed = np.zeros_like(protection)
    x0,y0,x1,y1=BOX;allowed[y0:y1,x0:x1]=True;allowed&=~protection
    beta = np.asarray(mask,dtype=float)/255
    beta[~allowed]=0
    a,b = np.asarray(parent)[...,:3].astype(float),np.asarray(background)[...,:3].astype(float)
    # Given B and an estimated beta, F=(I-(1-beta)B)/beta. Minimum feasible
    # beta keeps each channel in range, but does NOT prove a clean matte.
    delta = a-b
    minimum = np.max(np.where(delta>=0,delta/np.maximum(255-b,1),-delta/np.maximum(b,1)),axis=2)
    beta = np.where(beta>0,np.maximum(beta,minimum),0)
    beta = np.clip(beta,0,1)
    premultiplied = a-(1-beta[...,None])*b
    premultiplied[beta==0]=0
    return premultiplied,beta,allowed,protection


def compact(parent,background,long_scale=.85,cross_scale=1.08):
    if not (math.isfinite(long_scale) and math.isfinite(cross_scale)
            and .8<=long_scale<=1 and 1<=cross_scale<=1.12):
        raise ValueError('Hand shape exceeds the local study range')
    premult,beta,allowed,protected = materials(parent,background)
    direction = np.array([-.98,-.2]);direction/=np.linalg.norm(direction)
    basis=np.array([[direction[0],-direction[1]],[direction[1],direction[0]]])
    matrix=basis@np.diag([long_scale,cross_scale])@basis.T
    inverse=np.linalg.inv(matrix)
    x0,y0,x1,y1=BOX
    origin=np.array([x0,y0]);anchor=ANCHOR-origin
    offset=anchor-inverse@anchor
    coefficients=(*inverse[0],offset[0],*inverse[1],offset[1])
    # Work only in the 120x71 ROI, with floating premultiplied channels.
    channels=[premult[y0:y1,x0:x1,i] for i in range(3)]+[beta[y0:y1,x0:x1]]
    warped=[]
    for channel in channels:
        field=Image.fromarray(channel.astype(np.float32))
        warped.append(np.asarray(field.transform(field.size,Image.Transform.AFFINE,
            coefficients,Image.Resampling.BICUBIC),dtype=float))
    alpha=np.clip(warped[3],0,1)
    color=np.stack(warped[:3],axis=2)
    color=np.clip(color,0,255*alpha[...,None])
    a,b=np.asarray(parent),np.asarray(background)
    result=a.copy()
    # Repaint only the estimated original/destination hand support; all
    # other RGB/alpha, including upper hand and cuff, are copied unchanged.
    use=allowed[y0:y1,x0:x1]&((beta[y0:y1,x0:x1]>0)|(alpha>0))
    composed=color+(1-alpha[...,None])*b[y0:y1,x0:x1,:3]
    result[y0:y1,x0:x1,:3][use]=np.clip(np.rint(composed[use]),0,255).astype(np.uint8)
    return Image.fromarray(result),allowed,protected,beta,matrix


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    parent,background=inputs()
    pose,allowed,protected,beta,matrix=compact(parent,background)
    neutral,_,_,_,_=compact(parent,background,1,1)
    for name,image in [('pose',pose),('neutral',neutral)]:image.save(OUT/f'{name}.png')
    for name,mask in [('allowed-mask',allowed),('protected-mask',protected)]:
        Image.fromarray(mask.astype(np.uint8)*255).save(OUT/f'{name}.png')
    Image.fromarray(np.rint(beta*255).astype(np.uint8)).save(OUT/'estimated-matte.png')
    frames=[native_frame(parent),native_frame(neutral),native_frame(pose)]
    frames[-1].save(OUT/'frame.png')
    for width in (80,113,192,224):comparison(frames,width,['current v3','neutral estimate','conditioned hand']).save(OUT/f'contact-{width}px.png')
    detail=Image.new('RGB',(900,260),'#23252b');draw=ImageDraw.Draw(detail)
    for i,(image,label) in enumerate(zip([parent,neutral,pose],['current','neutral estimate','conditioned hand'])):
        tile=Image.new('RGBA',(300,230),'#23252b')
        tile.alpha_composite(image.crop((470,635,620,750)).resize((300,230),Image.Resampling.NEAREST))
        detail.paste(tile.convert('RGB'),(300*i,30));draw.text((300*i+5,7),label,fill='white')
    detail.save(OUT/'detail.png')
    a,b,n=np.asarray(parent),np.asarray(pose),np.asarray(neutral)
    changed=np.any(a!=b,axis=2)
    meta=dict(sourceSha256=ACCEPTED_SHA,parentPoseRGBAHash=PARENT_HASH,parentCompositionVersion='review-art-v3',
        backgroundRGBAHash=hashlib.sha256(background.tobytes()).hexdigest().upper(),
        method='background-conditioned floating premultiplied hand material, fixed-wrist local affine',
        roi=list(BOX),wristSourcePx=ANCHOR.tolist(),longAxisScale=.85,crossAxisScale=1.08,affineMatrix=matrix.tolist(),
        sourceMatteEstimated=True,neutralChangedPixels=int(np.any(a!=n,axis=2).sum()),
        neutralMaximumRGBAError=int(np.abs(a.astype(int)-n.astype(int)).max()),
        changedPixels=int(changed.sum()),changedPixelsOutsidePermission=int((changed&~allowed).sum()),
        protectedRGBAExact=bool(np.array_equal(a[protected],b[protected])),parentAlphaPreserved=True,
        poseRGBAHash=hashlib.sha256(pose.tobytes()).hexdigest().upper(),newArtworkGenerated=False,
        facialGeometryRepair=False,fullRedrawAccepted=False,articulatedArmBuilt=False,animationBuilt=False,
        visualAcceptance='pending',strategyUserApproval='pending',adopted=False,activeAtlasChanged=False,
        installableFullAtlas=False,installed=False,
        limitation='Exact neutral algebra would not prove a clean matte or natural hand anatomy. Background-conditioned edge colors and the fixed cuff/upper-hand protection remain an estimated local material; all visual and motion gates remain pending.')
    (OUT/'build.json').write_text(json.dumps(meta,indent=2)+'\n',encoding='utf-8');print(json.dumps(meta,indent=2))


if __name__=='__main__':main()
