"""Repair demonstrable hand-contour clipping, not change anatomy or pose."""
from collections import deque
import hashlib
import json

import numpy as np
from PIL import Image,ImageDraw,ImageFilter

from canonical import ROOT,ACCEPTED_SHA,load_canonical
from review_review_v2 import inputs as original_inputs,comparison,specification
from review_wave import native_frame

OUT=ROOT/'candidates/phase5/review-hand-outline-v1'
PARENT_HASH='29B889E8F9EC0BADF3762B1D9EE0C78F4CA752E95A9071F8AD77119562F748C5'
RAW_HASH='833558D9E037E4B2D217511E6D101A86EADB08B40D06DB5B00095AA559C6EA87'
BOX=(490,670,612,738)


def inputs():
    load_canonical()
    with Image.open(ROOT/'candidates/phase5/review-art-v3/pose.png') as image:
        parent=image.convert('RGBA')
    if hashlib.sha256(parent.tobytes()).hexdigest().upper()!=PARENT_HASH:
        raise ValueError('Contour repair needs the unchanged source-space parent')
    _,spec,raw=original_inputs()
    return parent,spec,raw


def skin_component(raw):
    x0,y0,x1,y1=BOX
    pixels=np.asarray(raw)[y0:y1,x0:x1,:3].astype(int)
    eligible=((pixels[...,0]>160)&(pixels[...,1]>145)&(pixels[...,2]>120)
        &(pixels[...,0]>=pixels[...,1])&(pixels[...,1]>=pixels[...,2])
        &(pixels[...,0]-pixels[...,1]<55)&(pixels[...,1]-pixels[...,2]<50))
    seen=np.zeros(eligible.shape,dtype=bool)
    seed=(700-y0,560-x0)
    if not eligible[seed]:raise ValueError('Recorded lower-palm seed is no longer painted skin')
    q=deque([seed]);seen[seed]=True
    while q:
        y,x=q.popleft()
        for ny,nx in ((y-1,x),(y+1,x),(y,x-1),(y,x+1)):
            if 0<=ny<seen.shape[0] and 0<=nx<seen.shape[1] and eligible[ny,nx] and not seen[ny,nx]:
                seen[ny,nx]=True;q.append((ny,nx))
    mask=Image.new('L',raw.size)
    mask.paste(Image.fromarray(seen.astype(np.uint8)*255),(x0,y0))
    return mask


def masks(parent,spec,raw):
    if hashlib.sha256(parent.tobytes()).hexdigest().upper()!=PARENT_HASH:
        raise ValueError('Hand contour repair cannot alter its parent pose')
    if spec!=specification() or raw.mode!='RGBA' or raw.size!=parent.size:
        raise ValueError('Contour repair requires the recorded crop and foreground protection')
    if hashlib.sha256(raw.tobytes()).hexdigest().upper()!=RAW_HASH:
        raise ValueError('Contour repair requires unchanged, uniformly registered original art')
    # The connected light region supplements the inspected source window.
    # It is not an author matte or permission to alter the upper hand.
    skin=skin_component(raw)
    core=np.asarray(skin.filter(ImageFilter.MaxFilter(13)))>0
    envelope=skin.filter(ImageFilter.MaxFilter(21))
    allowed=np.asarray(envelope)>0
    protection=Image.new('L',parent.size)
    for polygon in spec['preservedForegroundPolygons']:
        ImageDraw.Draw(protection).polygon(polygon,fill=255)
    protected=np.asarray(protection)>0
    # This repair is strictly below the belt and inside the hand neighborhood.
    budget=np.zeros_like(allowed);budget[660:749,480:622]=True
    if np.any(allowed&~budget):raise ValueError('Hand contour reconstruction exceeded its inspected budget')
    allowed&=~protected;core&=~protected
    weight=np.asarray(envelope.filter(ImageFilter.GaussianBlur(1.5)),dtype=float)/255
    weight[core]=1;weight[~allowed]=0
    return allowed,protected,core,np.asarray(skin)>0,weight


def repair(parent,spec,raw):
    allowed,protected,core,skin,weight=masks(parent,spec,raw)
    a,b=np.asarray(parent),np.asarray(raw)
    af,bf=a.astype(float),b.astype(float)
    af[...,:3]*=af[...,3:4]/255;bf[...,:3]*=bf[...,3:4]/255
    mixed=af*(1-weight[...,None])+bf*weight[...,None]
    np.divide(mixed[...,:3]*255,mixed[...,3:4],out=mixed[...,:3],where=mixed[...,3:4]>0)
    result=a.copy();result[allowed]=np.clip(np.rint(mixed[allowed]),0,255).astype(np.uint8)
    result[core]=b[core]
    return Image.fromarray(result),allowed,protected,core,skin


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    parent,spec,raw=inputs()
    pose,allowed,protected,core,skin=repair(parent,spec,raw)
    _,_,_,_,weight=masks(parent,spec,raw)
    raw.save(OUT/'mapped-source.png')
    Image.fromarray(np.rint(weight*255).astype(np.uint8)).save(OUT/'blend-weight.png')
    pose.save(OUT/'pose.png')
    for name,mask in [('allowed-mask',allowed),('protected-mask',protected),('raw-exact-core',core),('skin-component',skin)]:
        Image.fromarray(mask.astype(np.uint8)*255).save(OUT/f'{name}.png')
    frames=[native_frame(parent),native_frame(raw),native_frame(pose)];frames[-1].save(OUT/'frame.png')
    for width in (80,113,192,224):comparison(frames,width,['current v3','raw NOT adopted','contour repair']).save(OUT/f'contact-{width}px.png')
    detail=Image.new('RGB',(900,260),'#23252b');draw=ImageDraw.Draw(detail)
    for i,(image,label) in enumerate(zip([parent,raw,pose],['current','original mapped hand','bounded contour repair'])):
        tile=Image.new('RGBA',(300,230),'#23252b')
        tile.alpha_composite(image.crop((470,635,620,750)).resize((300,230),Image.Resampling.NEAREST))
        detail.paste(tile.convert('RGB'),(300*i,30));draw.text((300*i+5,7),label,fill='white')
    detail.save(OUT/'detail.png')
    a,b=np.asarray(parent),np.asarray(pose);changed=np.any(a!=b,axis=2)
    meta=dict(sourceSha256=ACCEPTED_SHA,parentPoseRGBAHash=PARENT_HASH,parentCompositionVersion='review-art-v3',
        generatedSource=spec['generatedSource'],generatedSha256=spec['generatedSha256'],newArtworkGenerated=False,
        method='complete observed original lower-hand contour, raw-exact core plus bounded edge blend; no hand scaling',
        seedSourcePx=[560,700],connectedSkinPixels=int(skin.sum()),rawExactCorePixels=int(core.sum()),
        changedPixels=int(changed.sum()),changedPixelsOutsidePermission=int((changed&~allowed).sum()),
        protectedForegroundRGBAExact=bool(np.array_equal(a[protected],b[protected])),
        alphaChangedPixels=int((a[...,3]!=b[...,3]).sum()),poseRGBAHash=hashlib.sha256(pose.tobytes()).hexdigest().upper(),
        facialGeometryRepair=False,fullRedrawAccepted=False,cleanLayerRecoveryClaimed=False,articulatedArmBuilt=False,
        animationBuilt=False,adopted=True,activeAtlasChanged=True,
        adoptionScope='local technical contour repair in development QA; pose/motion approval remains pending',
        visualAcceptance='pending',strategyUserApproval='pending',
        installableFullAtlas=False,installed=False,
        limitation='Local contour/mixing repair only. Inspection must establish whether light-region connectivity includes the intended lower hand, and whether the protected upper hand and source plates cut it legitimately. No new finger articulation, sleeve repair or motion acceptance is claimed.')
    (OUT/'build.json').write_text(json.dumps(meta,indent=2)+'\n',encoding='utf-8');print(json.dumps(meta,indent=2))


if __name__=='__main__':main()
