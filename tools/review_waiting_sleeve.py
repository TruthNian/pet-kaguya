"""Whole raised-garment component for development only; not release authority.

Includes limited occlusion backing beside its contour, not a recovered matte.
Never substitutes the generator's face, hand, shoulder cape or torso.
"""
import hashlib
import json
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from canonical import ROOT, ACCEPTED_SHA, bounded_masks
from guide_waiting_sleeve import OUT, BOX, SIDE, PARENT_HASH, parent
import review_waiting
from review_wave import native_frame
from review_review_v2 import comparison

GENERATED_SHA='60B513037DBCEDDF647C500D84C17BBF2706D81DB8EF85F9228DBE80CBC15F8F'
RAW_SIZE=(1254,1254)
ENVELOPE=[(476,505),(493,493),(507,491),(514,525),(551,533),(562,565),(560,618),
          (544,672),(508,739),(480,795),(451,839),(421,866),(372,900),(348,918),
          (327,918),(305,898),(304,870),(311,836),(338,779),(359,724),(382,681),
          (380,629),(390,589),(412,557),(447,528)]
FIRST_CAPE=[(418,514),(448,510),(498,500),(504,523),(470,546),(426,550)]
PROTECTED=[[(427,539),(445,524),(474,503),(491,493),(493,506),(462,535),(447,546),(430,546)],
           [(566,480),(620,480),(620,975),(450,975),(442,900),(448,841),
            (480,796),(505,742),(545,685),(559,650),(570,599),(568,549)]]


def rgba_hash(image):return hashlib.sha256(image.tobytes()).hexdigest().upper()


def cape_overlap_counts(base):
    """Color diagnostics, not semantic segmentation or permission selection."""
    a=np.asarray(base).astype(int)
    warm=(a[...,0]>200)&(a[...,1]>140)&(a[...,2]>130)&(a[...,0]-a[...,1]>30)
    pink=warm&(a[...,1]-a[...,2]<35)
    result={}
    for name,points in [('failed',FIRST_CAPE),('corrected',PROTECTED[0])]:
        mask=Image.new('L',base.size);ImageDraw.Draw(mask).polygon(points,fill=255)
        selected=np.asarray(mask)>0
        result[name]=dict(warmColorPixels=int((warm&selected).sum()),
                          pinkColorPixels=int((pink&selected).sum()))
    return result


def inputs():
    base=parent();path=OUT/'generated.png'
    if hashlib.sha256(path.read_bytes()).hexdigest().upper()!=GENERATED_SHA:
        raise ValueError('Waiting sleeve source changed')
    with Image.open(path) as image:raw=image.convert('RGBA')
    if raw.size!=RAW_SIZE:raise ValueError('Measured square framing changed')
    square=raw.convert('RGBa').resize((SIDE,SIDE),Image.Resampling.LANCZOS).convert('RGBA')
    mapped=base.copy();mapped.paste(square.crop((0,0,340,495)),BOX[:2])
    return base,mapped


def compose(base,mapped,legacy_cape=False):
    _,expected=inputs()
    if rgba_hash(base)!=PARENT_HASH or rgba_hash(mapped)!=rgba_hash(expected):
        raise ValueError('Cannot silently change the recorded waiting crop')
    spec=review_waiting.specification()
    old_allowed,_,hand_mask=review_waiting.masks(spec)
    envelope,_,_=bounded_masks(base.size,[ENVELOPE],0)
    protection=Image.new('L',base.size);draw=ImageDraw.Draw(protection)
    for points in ([FIRST_CAPE,PROTECTED[1]] if legacy_cape else PROTECTED):draw.polygon(points,fill=255)
    # Retain the actual complete hand, not a re-generated same-sized hand.
    hand=Image.fromarray(hand_mask.astype(np.uint8)*255).filter(ImageFilter.MaxFilter(9))
    protected=(np.asarray(protection)>0)|(np.asarray(hand)>0)
    allowed=envelope&old_allowed&~protected
    hard=Image.fromarray(allowed.astype(np.uint8)*255)
    weights=np.asarray(hard.filter(ImageFilter.MinFilter(5)).filter(ImageFilter.GaussianBlur(1))).copy()
    weights[~allowed]=0
    a,b=np.asarray(base),np.asarray(mapped)
    af,bf=a.astype(float),b.astype(float)
    af[...,:3]*=af[...,3:4]/255;bf[...,:3]*=bf[...,3:4]/255
    w=weights.astype(float)/255
    mixed=af*(1-w[...,None])+bf*w[...,None]
    np.divide(mixed[...,:3]*255,mixed[...,3:4],out=mixed[...,:3],where=mixed[...,3:4]>0)
    mixed[mixed[...,3]==0,:3]=0
    result=a.copy();result[allowed]=np.clip(np.rint(mixed[allowed]),0,255).astype(np.uint8)
    return Image.fromarray(result),allowed,protected,Image.fromarray(weights)


def main():
    base,mapped=inputs();pose,allowed,protected,weight=compose(base,mapped)
    failed,_,_,_=compose(base,mapped,legacy_cape=True)
    failed.save(OUT/'failed-cape-overlap.png')
    for name,image in [('pose',pose),('mapped-material',mapped),('blend-weight',weight),
                       ('allowed-mask',Image.fromarray(allowed.astype(np.uint8)*255)),
                       ('protected-mask',Image.fromarray(protected.astype(np.uint8)*255))]:
        image.save(OUT/(name+'.png'))
    frames=[native_frame(base),native_frame(pose)];frames[-1].save(OUT/'frame.png')
    for width in (80,113,192,224):
        comparison(frames,width,['current waiting','whole sleeve candidate']).save(OUT/f'contact-{width}px.png')
    board=Image.new('RGB',(680,525),'#23252b');draw=ImageDraw.Draw(board)
    for i,(image,label) in enumerate(((base,'current waiting'),(pose,'whole sleeve candidate'))):
        tile=Image.new('RGBA',(340,495),'#ededed');tile.alpha_composite(image.crop(BOX))
        board.paste(tile.convert('RGB'),(340*i,30));draw.text((340*i+4,8),label,fill='white')
    board.save(OUT/'detail.png')
    # Source-coordinate object-boundary inspection; no clean-layer claim.
    zoom=Image.new('RGB',(495,140),'#23252b');draw=ImageDraw.Draw(zoom)
    for i,(image,label) in enumerate(((base,'actual parent'),(mapped,'raw mapped'),(pose,'protected composite'))):
        tile=review_waiting.grid(image,(410,480,575,590))
        zoom.paste(tile,(165*i,25));draw.text((165*i+3,6),label,fill='white')
    zoom.save(OUT/'wrist-cape-detail.png')
    a,b,c=np.asarray(base),np.asarray(pose),np.asarray(mapped);changed=np.any(a!=b,axis=2)
    meta=dict(sourceSha256=ACCEPTED_SHA,parentPoseRGBAHash=PARENT_HASH,materialGeneratedSha256=GENERATED_SHA,
        rawCanvas=list(RAW_SIZE),sourceCrop=list(BOX),wholeSquareProjection=True,objectBoundsFitting=False,
        allowedEnvelope=ENVELOPE,allowedPixels=int(allowed.sum()),changedPixels=int(changed.sum()),
        changedOutsidePermission=int((changed&~allowed).sum()),
        rawChangedPixelsOutsidePermission=int((np.any(a!=c,axis=2)&~allowed).sum()),
        alphaChangedPixels=int((a[...,3]!=b[...,3]).sum()),protectedRGBAExact=bool(np.array_equal(a[protected],b[protected])),
        handRGBAExact=bool(np.array_equal(a[review_waiting.masks(review_waiting.specification())[2]],
                                        b[review_waiting.masks(review_waiting.specification())[2]])),
        capeOverlapColorDiagnostic=cape_overlap_counts(base),colorDiagnosticIsSemanticSegmentation=False,
        failedCapePoseRGBAHash=rgba_hash(failed),
        poseRGBAHash=rgba_hash(pose),frameRGBAHash=rgba_hash(frames[-1]),
        visualAcceptance='pending',adoptedIntoDevelopmentOnly=True,installed=False,
        clothOnlyPixelChangeClaimed=False,cleanSemanticMatteClaimed=False,animationBuilt=False,
        limitation='Whole raised garment plus bounded contour-side occlusion plate, not pure cloth-only RGB edits. '
            'Hand/cape/torso protected by inspected but estimated boundaries; hard shadows, fold/contour integration '
            'and full structure/motion remain visually unapproved.')
    (OUT/'build.json').write_text(json.dumps(meta,indent=2)+'\n',encoding='utf-8');print(json.dumps(meta,indent=2))


if __name__=='__main__':main()
