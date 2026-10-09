"""Separate paint-alpha from moving occlusion for the existing leg hypothesis."""
import hashlib
import json

import numpy as np
from PIL import Image,ImageDraw

from canonical import ROOT,ACCEPTED_SHA
import leg_material as legacy
from build_idle import sample
from review_wave import native_frame
from occlusion_material import condition,over

OUT=ROOT/'candidates/phase5/leg-material-v2'
DECISION='sources/canonical/locomotion-decision-20261009.json'


def strategy_decision():
    decision=json.loads((ROOT/DECISION).read_text(encoding='utf-8'))
    if (decision['sourceSha256']!=ACCEPTED_SHA or decision['strategyUserApproval']!='approved'
            or decision['projection']!='front-held-alternating-small-steps'
            or decision['scope']!='front-held-small-steps-only'
            or any(decision[key] for key in ('visualMotionApproved','sideViewAuthorized',
                                            'faceGeometryChangeAuthorized','installedHostChangeAuthorized'))):
        raise ValueError('The user approved a direction, not finished motion or expanded authority')
    return decision


def inputs():
    strategy_decision()
    return material_inputs()


def material_inputs():
    """Original texture/matte hypothesis, without locomotion-style approval.

    Reuse in another frontal motion must not inherit the user's approval of
    small-step direction. inputs() retains that guard for existing consumers.
    """
    original=legacy.inputs()
    source=legacy.premult(original['mother'].crop(original['box']))
    hints=[np.asarray(mask,dtype=float)/255*original['allowed'] for mask in original['masks']]
    if np.any((hints[0]>0)&(hints[1]>0)):
        raise ValueError('This decomposition needs disjoint original leg permissions')
    material=[];coverage=[]
    for hint in hints:
        local=source.copy()
        local[hint>0]=original['background'][hint>0]
        paint,beta=condition(source,local,hint)
        material.append(paint);coverage.append(beta)
    data=dict(original,layers=material,occlusions=coverage)
    return data


def composite(data,offsets):
    if len(offsets)!=2:raise ValueError('Provide two leg offsets')
    x0,y0,x1,y1=data['box']
    yy,xx=np.mgrid[y0:y1,x0:x1].astype(float)
    result=data['background'].copy();active=data['allowed'].copy()
    for leg,paint,beta,offset in zip(data['spec']['legs'],data['layers'],data['occlusions'],offsets):
        sx,sy=legacy.leg_coordinates(xx,yy,leg,*offset)
        moved=sample(paint,sx-x0,sy-y0)
        weight=sample(beta,sx-x0,sy-y0)
        result=over(moved,weight,result)
        active|=weight>0
    if (not np.isfinite(result).all() or np.any(result<-1e-7)
            or np.any(result[...,3]>255+1e-7)
            or np.any(result[...,:3]>result[...,3:4]+1e-7)):
        raise ValueError('Moving material produced invalid RGBA')
    pixels=np.asarray(data['mother'].crop(data['box'])).copy()
    pixels[active]=np.asarray(legacy.unpremult(result))[active]
    image=data['mother'].copy();image.paste(Image.fromarray(pixels),(x0,y0))
    return image


def main():
    data=inputs();OUT.mkdir(parents=True,exist_ok=True)
    old=legacy.composite(legacy.inputs(),[(0,0),(0,0)])
    poses=[data['mother'],old,composite(data,[(0,0),(0,0)]),
           composite(data,[(5,-7.5),(0,0)]),composite(data,[(0,0),(5,-7.5)])]
    labels=['mother','old neutral','new neutral','left lifted','right lifted']
    frames=[native_frame(image) for image in poses]
    for image,label in zip(poses,labels):image.save(OUT/(label.replace(' ','-')+'.png'))
    for width in (80,113,192,224):
        height=round(width*208/192)
        board=Image.new('RGB',(5*(width+12),2*(height+28)),'#23252b');draw=ImageDraw.Draw(board)
        for row,color in enumerate(('#23252b','#f1f0ee')):
            for i,(frame,label) in enumerate(zip(frames,labels)):
                tile=Image.new('RGBA',frame.size,color);tile.alpha_composite(frame)
                x,y=i*(width+12),row*(height+28)
                board.paste(tile.resize((width,height),Image.Resampling.NEAREST).convert('RGB'),(x+6,y+24))
                draw.text((x+3,y+3),label,fill='white')
        board.save(OUT/f'contact-{width}px.png')
    for leg,paint,beta in zip(data['spec']['legs'],data['layers'],data['occlusions']):
        legacy.unpremult(paint).save(OUT/(leg['name']+'-conditioned-paint.png'))
        Image.fromarray(np.rint(beta*255).astype(np.uint8)).save(OUT/(leg['name']+'-occlusion.png'))
    native_error=np.abs(legacy.premult(frames[0])-legacy.premult(frames[2]))
    metadata=dict(sourceSha256=ACCEPTED_SHA,generatedSha256=legacy.GENERATED_SHA,
        method='conditioned premultiplied RGBA plus separately moving occlusion weight',
        neutralRestRGBAExact=poses[0].tobytes()==poses[2].tobytes(),
        neutralNativeRGBAExact=frames[0].tobytes()==frames[2].tobytes(),
        neutralNativeMaximumPremultRGBAError=round(float(native_error.max()),9),
        neutralFromSameMaterialNotSourceShortcut=True,sourceAlphaAndOcclusionSeparated=True,
        estimatedMatte=True,artistLayerRecoveryClaimed=False,newArtworkGenerated=False,
        facialGeometryRepair=False,visualMotionApproval='pending',strategyUserApproval='approved',
        strategyApprovalScope='front-held-small-steps-only',strategyUserDecision=DECISION,
        usedByDevelopmentLocomotion=True,developmentAtlasChanged=True,
        visualApprovalClaimed=False,installableFullAtlas=False,installed=False,
        poseHashes=[hashlib.sha256(image.tobytes()).hexdigest().upper() for image in poses],
        unresolved=['Estimated silhouettes can still carry hair or miss original fine edges.',
                    'Hidden hair and puppet anatomy remain estimates.',
                    'Frontal view is intentional; body-weight shift, entry/exit and screen-world velocity synchronization remain missing.'])
    (OUT/'build.json').write_text(json.dumps(metadata,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(metadata,indent=2))


if __name__=='__main__':main()
