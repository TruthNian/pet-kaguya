"""Original eye-surface flow prototype: fixed apertures, no iris extraction/inpainting.

Unlike the current rigid-iris model, this deliberately allows small texture and
iris-shape deformation. It is stylized 2-D flow, not recovered 3-D eye rotation.
"""
import json
import hashlib

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

import build_gaze as gaze
from canonical import ROOT, clean_cutout
from build_idle import render, sample

OUT=ROOT/'candidates/phase5/look-surface-v1'
FACE=(420,235,805,410)
STEPS=24
FALLOFF=14
METHOD='original-aperture-surface-flow-v1'


def fields(spec):
    result=[]
    for eye in spec['eyes']:
        mask=gaze.polygon_mask(eye,'aperturePolygon')
        inside=np.asarray(mask)>0
        distance=np.zeros(inside.shape,float)
        eroded=mask
        while np.any(np.asarray(eroded)):
            distance+=np.asarray(eroded)>0
            eroded=eroded.filter(ImageFilter.MinFilter(3))
        t=np.clip((distance-1)/FALLOFF,0,1)
        weight=t*t*t*(10+t*(-15+6*t))
        result.append(dict(eye=eye,inside=inside,aperture=inside,weight=weight))
    return result


def mapping(field,dx,dy):
    height,width=field['weight'].shape
    yy,xx=np.mgrid[:height,:width].astype(float)
    x,y=xx.copy(),yy.copy()
    for _ in range(STEPS):
        a=sample(field['weight'],x,y)
        midpoint=sample(field['weight'],x-dx*a/(2*STEPS),y-dy*a/(2*STEPS))
        x-=dx*midpoint/STEPS;y-=dy*midpoint/STEPS
    xy,xx_derivative=np.gradient(x)
    yy_derivative,yx=np.gradient(y)
    determinant=xx_derivative*yy_derivative-xy*yx
    if determinant.min()<=0:
        raise ValueError('Eye-surface flow folded the observed source texture')
    return x,y,determinant


def render_pose(source,eye_fields,dx,dy):
    if not np.isfinite([dx,dy]).all() or abs(dx)>6 or abs(dy)>4:
        raise ValueError('Eye-surface displacement exceeds current source range')
    result=np.asarray(source).copy()
    minima=[]
    for field in eye_fields:
        x0,y0,x1,y1=field['eye']['box']
        x,y,jacobian=mapping(field,dx,dy)
        minima.append(float(jacobian.min()))
        original=np.asarray(source.crop((x0,y0,x1,y1)))
        rgb=np.clip(np.rint(sample(original[...,:3],x,y)),0,255).astype(np.uint8)
        selected=field['weight']>0
        result[y0:y1,x0:x1,:3][selected]=rgb[selected]
    return Image.fromarray(result),min(minima)


def pose(source,eye_fields,dx,dy):
    return render_pose(source,eye_fields,dx,dy)[0]


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    source,_,spec,layers,transform,regions,masks=gaze.inputs()
    flow_spec=json.loads((ROOT/'sources/canonical/gaze-surface-v1.json').read_text(encoding='utf-8'))
    if (flow_spec['sourceSha256']!=spec['sourceSha256'] or flow_spec['method']!=METHOD
            or flow_spec['maximumDisplacementSourcePx']!=[6,4]
            or flow_spec['boundaryFalloffSourcePx']!=FALLOFF or flow_spec['inverseFlowMidpointSteps']!=STEPS
            or flow_spec['adopted'] or flow_spec['visualApproval']!='pending'):
        raise ValueError('Surface candidate changed its explicit source/method/approval boundary')
    eye_fields=fields(spec)
    original=np.asarray(source);allowed=gaze.aperture_union(source,layers)
    displacement_spec=dict(spec,maximumDisplacementSourcePx=[6,4])
    report=[];poses=[];frames=[]
    zero=dict(bodyY=0,earAngle=0,hairAngle=0)
    neutral=pose(source,eye_fields,0,0)
    if neutral.tobytes()!=source.tobytes():
        raise ValueError('Zero flow must reproduce every mother pixel without a bypass')
    neutral_frame=render(clean_cutout(neutral)[0],zero,transform,regions,masks)
    neutral_frame.save(OUT/'neutral.png')
    strip=Image.new('RGBA',(1536,416))
    for index in range(16):
        dx,dy=gaze.offsets(index,displacement_spec)
        trial,minimum=render_pose(source,eye_fields,dx,dy)
        a=np.asarray(trial)
        if not np.array_equal(a[...,3],original[...,3]) or np.any(np.any(a!=original,axis=2)&~allowed):
            raise ValueError('Eye flow modified alpha or fixed source pixels')
        frame=render(clean_cutout(trial)[0],zero,transform,regions,masks)
        if not np.array_equal(np.asarray(frame)[...,3],np.asarray(neutral_frame)[...,3]):
            raise ValueError('Eye-flow candidate changed native coverage alpha')
        frame.save(OUT/f'frame-{index}.png');frames.append(frame);poses.append(trial)
        strip.paste(frame,(index%8*192,index//8*208))
        report.append(dict(offset=[dx,dy],minimumSampledJacobian=minimum))
    strip.save(OUT/'strip.webp',lossless=True,exact=True,method=6)
    for width in (113,224):gaze.contact(frames,width).save(OUT/f'contact-{width}px.png')
    board=Image.new('RGB',(3*385,4*200),'#ededed');draw=ImageDraw.Draw(board)
    for row,index in enumerate((0,4,8,12)):
        current=gaze.pose(source,layers,*gaze.offsets(index,spec))
        for col,(label,image) in enumerate((('mother',source),('current: max 12,7',current),('surface: max 6,4',poses[index]))):
            board.paste(image.crop(FACE).convert('RGB'),(col*385,row*200+25))
            draw.text((col*385+3,row*200+5),f'{label}: direction {index}',fill='#222222')
    board.save(OUT/'comparison.png')
    digest=lambda f:hashlib.sha256(f.tobytes()).hexdigest().upper()
    metadata=dict(sourceSha256=spec['sourceSha256'],sourceRig='sources/canonical/gaze-surface-v1.json',method=METHOD,
        sourceRGBAExactAtZero=True,neutralReconstructionRGBAExact=True,onlyEyeAperturesMayChange=True,
        sourceAlphaPreservedExactly=True,nativeAlphaPreservedExactly=True,newArtworkGenerated=False,
        directionCount=16,nativeRows=[9,10],sourceOffsetsPx=[p['offset'] for p in report],
        bodyRotated=False,artMirrored=False,irisShapeWarp=True,eyeOutlineFixed=True,facialGeometryRepair=False,
        maximumDisplacementSourcePx=[6,4],boundaryFalloffSourcePx=FALLOFF,inverseFlowMidpointSteps=STEPS,
        minimumSampledJacobian=min(p['minimumSampledJacobian'] for p in report),
        frameHashes=[digest(f) for f in frames],neutralFrameHash=digest(neutral_frame),camera=transform,
        adopted=False,activeAtlasChanged=False,visualAcceptance='pending',installableFullAtlas=False,installed=False,
        limitations=flow_spec['limitations'])
    (OUT/'build.json').write_text(json.dumps(metadata,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(directionCount=16,minimumSampledJacobian=metadata['minimumSampledJacobian'],
        neutralRGBAExact=True,nativeAlphaExact=True,adopted=False,activeAtlasChanged=False)))


if __name__=='__main__': main()
