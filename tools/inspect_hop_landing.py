"""Current five-hold landing tradeoff; diagnostic only, never promotes a pose."""
import hashlib
import json
import math

import numpy as np
from PIL import Image,ImageDraw

from canonical import ROOT
import build_jumping as hop
from build_idle import render, specification as idle_specification, sample, coordinates
from leg_material import leg_coordinates
from locomotion_render import integration_coordinates, source_coordinates, relative_offsets, evaluate, quantize
from material_support import sample_local
import hop_contact
from animation_output import write_animation
from protocol import DURATIONS

OUT = ROOT/'work/hop-landing-audit-20261010'
COMPRESSIONS = (0.25,0.125,0.0,0.4)


def rgba_hash(image):
    return hashlib.sha256(image.tobytes()).hexdigest().upper()


def root_tradeoff(landing,anticipation,rest):
    values = (landing,anticipation,rest)
    if any(isinstance(v,bool) or not isinstance(v,(float,int)) or not math.isfinite(v) for v in values):
        raise ValueError('Root comparison needs finite output-pixel displacements')
    return dict(nextAnticipationRootJumpPx=abs(anticipation-landing),
        finalIdleRootJumpPx=abs(rest-landing),
        twoExitWorstRootJumpPx=max(abs(anticipation-landing),abs(rest-landing)))


def pixel_delta(a,b):
    x,y = np.asarray(a),np.asarray(b)
    return dict(changedRGBAPixels=int(np.any(x!=y,axis=2).sum()),
        changedAlphaPixels=int((x[...,3]!=y[...,3]).sum()))


def shoe_support_probe(material,before,after,transform,regions,masks,point):
    """Separate stable foreground samples from moving backing near one output pixel."""
    px,py = point
    xx,yy = integration_coordinates(transform)
    # Conservative neighbourhood containing the 3x->native Lanczos support.
    x,y = xx[(py-4)*3:(py+5)*3,(px-4)*3:(px+5)*3],yy[(py-4)*3:(py+5)*3,(px-4)*3:(px+5)*3]
    x0,y0,_,_ = material['data']['box']
    records = []
    for pose in (before,after):
        current = hop_contact.key(pose,transform['scale'])
        tips = dict(bodyY=0,earAngle=pose['earAngle'],hairAngle=pose['hairAngle'])
        def fields(qx,qy):return coordinates(qx,qy,tips,transform,regions,masks)
        qx,qy = source_coordinates(x,y,current)
        bx,by = fields(qx,qy)
        backing = sample(material['backing'],bx,by)
        visible = sample(material['visibility'],bx,by)
        known = sample(material['visibleBacking'],bx,by)
        np.divide(known,visible[...,None],out=backing,where=visible[...,None]>1e-12)
        paints,betas,coords = [],[],[]
        for leg,paint,beta,offset in zip(material['data']['spec']['legs'],
                material['data']['layers'],material['data']['occlusions'],relative_offsets(current,1)):
            sx,sy = fields(*leg_coordinates(qx,qy,leg,*offset))
            coords.append((sx,sy))
            paints.append(sample_local(paint,sx-x0,sy-y0,material['localFilterSupport']))
            betas.append(sample_local(beta,sx-x0,sy-y0,material['localFilterSupport']))
        raw = evaluate(material,x,y,current,1,source_fields=fields,rebase_roundoff=False)
        records.append(dict(backing=backing,paints=paints,betas=betas,coords=coords,raw=raw))
    a,b = records
    coefficient = (1-a['betas'][0])*(1-a['betas'][1])
    contribution = coefficient[...,None]*(b['backing']-a['backing'])
    def center(pixels):
        return list(quantize(pixels).convert('RGBa').resize((9,9),Image.Resampling.LANCZOS).convert('RGBA').getpixel((4,4)))
    before_pixel,after_pixel = center(a['raw']),center(b['raw'])
    corrected_pixel = center(b['raw']-contribution)
    return dict(nativePoint=list(point),highGridSupportShape=list(x.shape),
        foregroundCoordinateMaximumDifference=max(float(np.max(np.abs(u-v)))
            for ca,cb in zip(a['coords'],b['coords']) for u,v in zip(ca,cb)),
        foregroundPaintMaximumDifference=max(float(np.max(np.abs(u-v))) for u,v in zip(a['paints'],b['paints'])),
        occlusionMaximumDifference=max(float(np.max(np.abs(u-v))) for u,v in zip(a['betas'],b['betas'])),
        backingContributionMaximumDifference=float(np.max(np.abs(contribution))),
        residualAfterBackingContribution=float(np.max(np.abs((b['raw']-a['raw'])-contribution))),
        nativePixelBefore=before_pixel,nativePixelAfter=after_pixel,
        nativePixelWithBackingDifferenceRemoved=corrected_pixel,
        sameBackingRestoresPixel=corrected_pixel==before_pixel,
        scope='actual support neighbourhood before roundoff rebasing and terminal quantization; not a whole-shoe or arbitrary-pose proof')


def inputs():
    source,_,transform,regions,masks,motion,poses = hop.inputs()
    data,material = hop.contact_inputs()
    original = [hop_contact.render(material,p,transform,regions,masks) for p in poses]
    active = json.loads((hop.OUT/'build.json').read_text(encoding='utf-8'))
    if [rgba_hash(frame) for frame in original] != active['frameHashes']:
        raise ValueError('Diagnostic baseline is not the current actual five-cel hop')
    _,idle_motion = idle_specification()
    idle = render(source,idle_motion['keyframes'][0],transform,regions,masks)
    idle_meta = json.loads((ROOT/'candidates/phase5/idle/build.json').read_text(encoding='utf-8'))
    if rgba_hash(idle) != idle_meta['frameHashes'][0]:
        raise ValueError('Final reference is not the actual first idle cel')
    yy,xx = np.mgrid[270:445:7.3,470:760:8.1]
    expected_face = sample(material['source'],xx,yy)
    variants = []
    for compression in COMPRESSIONS:
        pose = dict(poses[4],bodyY=compression)
        # Render the changed hold from the original materials, not from a
        # translated native bitmap. Reuse only the four unchanged cels.
        landing = hop_contact.render(material,pose,transform,regions,masks)
        frames = [*original[:4],landing]
        face = hop_contact.sample_pose(material,xx,yy+compression/transform['scale'],
            pose,transform,regions,masks)
        face_error = float(np.max(np.abs(face-expected_face)))
        if face_error > 1e-10:
            raise ValueError('Landing counterfactual changed the original face material')
        shoe_boxes = []
        for box in ((73,181,93,199),(101,181,113,199)):
            a,b = np.asarray(original[4].crop(box)),np.asarray(landing.crop(box))
            yy_changed,xx_changed = np.where(np.any(a!=b,axis=2))
            shoe_boxes.append(dict(box=list(box),RGBAExact=not len(xx_changed),
                changedPixels=int(len(xx_changed)),maximumChannelDifference=int(np.abs(a.astype(int)-b.astype(int)).max()),
                changedNativeCoordinates=[[int(x+box[0]),int(y+box[1])] for x,y in zip(xx_changed,yy_changed)]))
        variants.append(dict(compression=compression,pose=pose,frames=frames,
            jointEvidence=hop_contact.joint_evidence(data,pose,transform),
            faceRigidPremultError=face_error,shoeBoxComparison=shoe_boxes,
            root=root_tradeoff(compression,poses[0]['bodyY'],idle_motion['keyframes'][0]['bodyY']),
            changedLanding=pixel_delta(original[4],landing),
            loopPixelDelta=pixel_delta(landing,original[0]),idlePixelDelta=pixel_delta(landing,idle)))
        variants[-1]['shoeSupportProbes'] = [shoe_support_probe(material,poses[4],pose,transform,regions,masks,point)
            for box in shoe_boxes for point in box['changedNativeCoordinates']]
        for probe in variants[-1]['shoeSupportProbes']:
            point = tuple(probe['nativePoint'])
            probe['supportReconstructsObservedNativePixels'] = (
                probe['nativePixelBefore']==list(original[4].getpixel(point))
                and probe['nativePixelAfter']==list(landing.getpixel(point)))
    return dict(motion=motion,poses=poses,original=original,idle=idle,active=active,
        transform=transform,variants=variants)


def main():
    data = inputs()
    OUT.mkdir(parents=True,exist_ok=True)
    board = Image.new('RGB',(4*236,2*290),'#23252b')
    draw = ImageDraw.Draw(board)
    receipt = []
    for column,variant in enumerate(data['variants']):
        name = f"compression-{variant['compression']:.3f}"
        write_animation(OUT/name,variant['frames'],DURATIONS[4])
        for row,color in enumerate(('#23252b','#f1f0ee')):
            tile = Image.new('RGBA',(192,208),color)
            tile.alpha_composite(variant['frames'][4])
            board.paste(tile.resize((224,243),Image.Resampling.NEAREST).convert('RGB'),
                (column*236+6,row*290+36))
            draw.text((column*236+6,row*290+4),f"landing {variant['compression']:.3f}px; hold 280ms",fill='white')
            draw.text((column*236+6,row*290+18),
                f"loop {variant['root']['nextAnticipationRootJumpPx']:.3f}; idle {variant['root']['finalIdleRootJumpPx']:.3f}",fill='white')
        receipt.append({**{key:value for key,value in variant.items() if key!='frames'},
            'frameHashes':[rgba_hash(f) for f in variant['frames']]})
    board.save(OUT/'landing-contact.png')
    metadata = dict(sourceSha256=data['active']['sourceSha256'],apexOutputPx=4,
        camera=data['transform'],durationsMs=DURATIONS[4],repeatBeforeIdle=3,
        baselineActualCelsReconstructedExactly=True,baselineFrameHashes=data['active']['frameHashes'],
        firstFourCelsRGBAExact=True,originalFaceMaterialRigid=True,
        allShoeTestRectanglesRGBAExact=all(box['RGBAExact'] for v in data['variants'] for box in v['shoeBoxComparison']),
        variants=receipt,adopted=False,activeAtlasChanged=False,installed=False,
        nativeInterpolation=False,withinHoldRecoveryBuilt=False,visualMotionApproval='pending',
        scope='change only final held body compression; ear/hair angles remain current',
        limitations=['Shoe targets/design lengths are validated. Fixed test rectangles may also contain backing/coverage; their actual pixel mismatches are recorded, never silently waived as exact paint.',
            'A single held landing cel cannot depict within-hold impact then recovery.',
            'The same landing cel is used at the loop seam and final idle exit.',
            'Root/pixel deltas are descriptive, not physical force, anatomy or aesthetic scores.',
            'Smaller idle exit error can increase the next anticipation jump. No variant is auto-adopted.',
            'First-idle comparison is not arbitrary base-task/hover interruption continuity.'])
    (OUT/'report.json').write_text(json.dumps(metadata,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(output=str(OUT),variants=[dict(compression=v['compression'],**v['root'],
        changedLanding=v['changedLanding'],shoeBoxComparison=v['shoeBoxComparison'],
        shoeSupportProbes=v['shoeSupportProbes']) for v in data['variants']],adopted=False),indent=2))


if __name__ == '__main__':main()
