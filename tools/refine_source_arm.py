"""Inspect and refine nonzero source-arm edges; never promote on neutral equality."""
import json

import numpy as np
from PIL import Image, ImageDraw

from canonical import ROOT, ACCEPTED_SHA
from review_source_arm import materials, pose, forward, BOX, ANGLES, rgba_hash, native_frame, editor_material
from review_source_backing import load_projected
from visible_hair_boundary import solve
from animation_output import write_animation
from protocol import DURATIONS

WORK = ROOT/'work/source-arm-edge-inspection'
OUT = ROOT/'candidates/phase5/wave-source-rig-v3'


def slope_boundary(source, corrected, domain, known):
    """Estimate one inward sample from two real outside hair samples.

    These inward values are inferred, NOT newly observed hair. Refuse sharp
    outside gradients rather than extrapolating across a genuine strand edge.
    """
    h,w=domain.shape
    y,x=np.nonzero(domain)
    totals=np.zeros((h,w,3),dtype=float);counts=np.zeros((h,w),dtype=np.int32)
    for dy,dx in [(-1,0),(1,0),(0,-1),(0,1)]:
        py,px=y+dy,x+dx;qy,qx=y+2*dy,x+2*dx
        inside=(qy>=0)&(qy<h)&(qx>=0)&(qx<w)
        iy,ix=y[inside],x[inside]
        py,px,qy,qx=py[inside],px[inside],qy[inside],qx[inside]
        observed=known[py,px]&known[qy,qx]
        p=source[py,px,:3].astype(float);q=source[qy,qx,:3].astype(float)
        gentle=(np.max(np.abs(p-q),axis=1)<=20)
        valid=observed&gentle
        totals[iy[valid],ix[valid]]+=2*p[valid]-q[valid]
        counts[iy[valid],ix[valid]]+=1
    inferred=(counts>0)&domain
    target=corrected.copy()
    values=totals[inferred]/counts[inferred,None]
    target[inferred,:3]=np.clip(np.rint(values),0,255).astype(np.uint8)
    # Propagate the small boundary correction without calling the inferred
    # ribbon a source observation. The old source outside the domain stays
    # byte-exact; the original material gives the interior strand gradients.
    revised,diagnostics=solve(target,corrected,domain&~inferred,known|inferred)
    diagnostics['inferredPixels']=int(inferred.sum())
    diagnostics['clippedInferredChannels']=int(((values<0)|(values>255)).sum())
    return revised,inferred,diagnostics


def refine(data):
    x0,y0,x1,y1=BOX
    a=np.asarray(data['mother'])
    support=data['beta'][y0:y1,x0:x1]>0
    yy,xx=np.mgrid[y0:y1,x0:x1].astype(float)
    fx,fy=forward(xx,yy,6.)
    # A fixed root touching the ROI is still foreground, not a hair anchor.
    # It never exposes its backing in this field. Solve only moving material,
    # while excluding all old foreground (moving or fixed) from observations.
    domain=support&(np.hypot(fx-xx,fy-yy)>1e-7)
    r,g,b=np.moveaxis(a[y0:y1,x0:x1,:3].astype(np.int16),-1,0)
    green_cloth=(g-r>=-8)&(g-b>16)&(g>75)
    known=(~support)&(~data['protected'][y0:y1,x0:x1])&(a[y0:y1,x0:x1,3]>=240)&~green_cloth
    corrected,diagnostics=solve(a[y0:y1,x0:x1],np.asarray(load_projected())[y0:y1,x0:x1],domain,known)
    corrected,inferred,slope_diagnostics=slope_boundary(a[y0:y1,x0:x1],corrected,domain,known)
    background=a.copy();background[y0:y1,x0:x1]=corrected
    beta=data['beta'].copy()
    s,b=a[...,:3].astype(float),background[...,:3].astype(float)
    difference=s-b
    minimum=np.max(np.where(difference>=0,difference/np.maximum(255-b,1),-difference/np.maximum(b,1)),axis=2)
    beta=np.where(beta>0,np.maximum(beta,minimum),0)
    foreground=s-(1-beta[...,None])*b;foreground[beta==0]=0
    if np.any(foreground<-1e-9) or np.any(foreground>255*beta[...,None]+1e-9):
        raise ValueError('Boundary-corrected foreground must remain valid')
    revised=dict(data,background=Image.fromarray(background),beta=beta,foreground=foreground)
    return revised,domain,known,diagnostics,inferred,slope_diagnostics


def study():
    OUT.mkdir(parents=True,exist_ok=True)
    original=materials(background_override=load_projected())
    expanded=materials(background_override=load_projected(),follow_cloth_edges=True)
    data,domain,known,diagnostics,inferred,slope_diagnostics=refine(expanded)
    rendered=[pose(data,angle) for angle in ANGLES]
    frames=[native_frame(image) for image,_ in rendered]
    write_animation(OUT,frames,DURATIONS[3])
    editor_material(data,OUT)
    for i,(image,_) in enumerate(rendered):image.save(OUT/f'pose-{i}.png')
    data['background'].save(OUT/'background.png')
    x0,y0,x1,y1=BOX
    masks=[('known-background',known),('unknown-background',domain),('inferred-boundary',inferred)]
    for name,mask in masks:
        full=np.zeros(np.asarray(data['beta']).shape,dtype=np.uint8)
        full[y0:y1,x0:x1]=mask*255
        Image.fromarray(full).save(OUT/(name+'.png'))
    for name in ('protected', 'allowed'):
        Image.fromarray(data[name].astype(np.uint8)*255).save(OUT/(name+'-mask.png'))
    board=Image.new('RGB',(1000,460),'#23252b');draw=ImageDraw.Draw(board)
    before,_=pose(original,6.)
    views=[('old +6',before),('new +6',rendered[1][0]),('old background',original['background']),('new background',data['background'])]
    for i,(name,image) in enumerate(views):
        tile=Image.new('RGBA',(277,436),'#eeeeee');tile.alpha_composite(image.crop(BOX))
        board.paste(tile.resize((250,394),Image.Resampling.LANCZOS).convert('RGB'),(250*i,35))
        draw.text((250*i+5,10),name,fill='white')
    board.save(OUT/'detail.png')
    metadata=dict(sourceSha256=ACCEPTED_SHA,
        parent='wave-source-rig-v2',roi=list(BOX),state='waving',nativeRow=3,
        durationsMs=DURATIONS[3],totalDurationMs=sum(DURATIONS[3]),repeatBeforeIdle=3,
        method='gradient-guided hidden RGB with visible-hair constraints and inferred gentle boundary slopes',
        knownBackgroundConstraintEdges=diagnostics['anchors'],
        solverRelativeTolerance=1e-8,solverMaxIterations=1600,
        solverConvergedBelowTolerance=diagnostics['relativeResidual']<=1.1e-8,
        inferredBoundaryPixels=slope_diagnostics['inferredPixels'],
        clippedInferredChannels=slope_diagnostics['clippedInferredChannels'],
        slopeSolveConvergedBelowTolerance=slope_diagnostics['relativeResidual']<=1.1e-8,
        colorSolveClippedChannels=diagnostics['clippedChannels'],
        slopeSolveClippedChannels=slope_diagnostics['clippedChannels'],
        inferredBoundaryIsNotSourceObservation=True,
        sourceAlphaPreserved=True,foregroundMaterialDomainPreserved=False,
        originalConnectedSleeveEdgeFollowed=True,
        newlyIncludedMaterialPixels=int(((data['beta']>0)&(original['beta']==0)).sum()),
        retiredOriginalGreenBoundaryPoints=[[427,903],[426,905],[425,908],[423,913],[422,915]],
        foregroundMatteStillEstimated=True,newArtworkGenerated=False,facialGeometryRepair=False,
        cleanLayerRecoveryClaimed=False,articulatedArmBuilt=False,nativeInterpolation=False,
        neutralFromSameMaterialNotSourceShortcut=True,
        neutralRestRGBAExact=rendered[0][0].tobytes()==data['mother'].tobytes(),
        measurements=[measure for _,measure in rendered],frameHashes=[rgba_hash(image) for image in frames],
        backgroundRGBAHash=rgba_hash(data['background']),visualMotionApproval='pending',
        strategyUserApproval='pending',adopted=False,activeAtlasChanged=False,
        installableFullAtlas=False,installed=False,
        unresolved=['No guarantee that generated strand paths match the original.',
                    'Estimated foreground may carry visible hair along with the hand.',
                    'Upper cuff is not wholly rigid; gesture and native discrete entry/exit remain unapproved.'])
    (OUT/'build.json').write_text(json.dumps(metadata,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(solver=diagnostics,slopeSolver=slope_diagnostics,measurements=metadata['measurements']),indent=2))


def inspect():
    WORK.mkdir(parents=True,exist_ok=True)
    data = materials(background_override=load_projected())
    moved,_ = pose(data,6.)
    source = data['mother']
    mask = Image.fromarray(np.rint(data['beta']*255).astype(np.uint8)).convert('RGBA')
    for name,box in [('hem',(290,915,415,1000)),('hand',(255,710,380,805))]:
        width,height = box[2]-box[0],box[3]-box[1]
        board = Image.new('RGB',(width*8,(height*4+30)*2),'#23252b')
        draw = ImageDraw.Draw(board)
        for i,(label,image) in enumerate([('source',source),('current +6',moved),
                                         ('background',data['background']),('estimated beta',mask)]):
            tile = Image.new('RGBA',(width,height),'#eeeeee')
            tile.alpha_composite(image.crop(box))
            x,y = (i%2)*width*4,(i//2)*(height*4+30)
            board.paste(tile.resize((width*4,height*4),Image.Resampling.NEAREST).convert('RGB'),(x,y+30))
            draw.text((x+5,y+5),label+' '+str(box),fill='white')
        board.save(WORK/(name+'.png'))
    rgb = np.asarray(source)
    for x,y in [(340,982),(350,982),(346,983),(344,984),(345,987),(350,985),(365,975),(380,962),(396,940),
                (290,769),(300,777),(315,784),(329,788)]:
        print(json.dumps(dict(point=[x,y],source=rgb[y,x].tolist(),
             beta=round(float(data['beta'][y,x]),5),background=np.asarray(data['background'])[y,x].tolist(),
             moved=np.asarray(moved)[y,x].tolist())))


if __name__=='__main__':
    import sys
    inspect() if '--inspect' in sys.argv else study()
