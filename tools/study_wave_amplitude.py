"""Lower the existing raised cel, without a new face/hand drawing.

This is an adopted development basis, not a completed action. The patch coverage and premultiplied
paint move together over the existing hidden backing. The open hand has one
rigid translation; the cuff/sleeve attachment is an estimated deformation, not
recovered artist layers or a complete joint rig.
"""
import hashlib
import json
import math

import numpy as np
from PIL import Image, ImageDraw

from canonical import ROOT, ACCEPTED_SHA, bounded_masks, camera, clean_cutout
from build_idle import sample, smooth
from build_waving import original_inputs as wave_inputs
from review_wave import inputs as art_inputs, native_frame
from review_arm_backing import specification, localized_backing, load_generated
from occlusion_material import over
from animation_output import write_animation
from protocol import DURATIONS

OUT = ROOT/'candidates/phase5/wave-amplitude-v1'
DECISION='sources/canonical/waving-amplitude-decision-20261010.json'
ADOPTION='sources/canonical/waving-amplitude-adoption-20261010.json'
REFERENCE='sources/reference/waving-amplitude-high'
APPROVED_PEAK='61C09D34D0A702F5AA5B472FAE38D8945BED2836E7EA61A55E63C0B1F65EF3D6'
BOX = (250, 545, 527, 1001)
SPEC = dict(verticalOffsetSourcePx=55., wristSourcePx=[362.,617.],
    attachmentX=[426.,520.], handRigidRect=[295,545,426,660],
    attachmentEstimated=True, userDirection='retain gentle arm lift; lower amplitude')


def rgba_hash(image):
    return hashlib.sha256(image.tobytes()).hexdigest().upper()


def forward(x, y, amount):
    if isinstance(amount,bool) or not math.isfinite(amount) or not 0<=amount<=55:
        raise ValueError('Only the bounded lowered-arm study is supported')
    attachment=1-smooth(*SPEC['attachmentX'],x)
    # x-only vertical shear has determinant 1, and leaves the entire hand
    # rectangle rigid. It still shears cuff material; area equality is not
    # proof of a natural sleeve. The original -30deg rotation trial reduced
    # the real patch's minimum area ratio to .6952 and was not retained.
    return x.copy(),y+amount*attachment


def inverse(x,y,amount):
    forward(x,y,amount)  # Validate even at the neutral amount.
    sx,sy=x.copy(),y-amount*(1-smooth(*SPEC['attachmentX'],x))
    fx,fy=forward(sx,sy,amount)
    error=float(np.hypot(fx-x,fy-y).max())
    if error>1e-6:
        raise ValueError('Lowered-arm inverse did not converge')
    return sx,sy,error


def material(mother):
    _,patch,generated=art_inputs('peak')
    definition=specification()
    backing,old_allowed=localized_backing(mother,load_generated(),definition)
    allowed,beta,_=bounded_masks(mother.size,[patch['foregroundPolygon']],patch['edgeFeatherSourcePx'])
    pixels=np.asarray(generated,dtype=float)
    pixels[...,:3]*=pixels[...,3:4]/255
    paint=pixels*beta[...,None]
    protection=Image.new('L',mother.size)
    draw=ImageDraw.Draw(protection)
    for polygon in definition['preservedForegroundPolygons']:
        draw.polygon(polygon,fill=255)
    for x0,y0,x1,y1 in definition['protectedRects']:
        draw.rectangle((x0,y0,x1-1,y1-1),fill=255)
    return dict(mother=mother,backing=backing,paint=paint,beta=beta,
        protected=np.asarray(protection)>0,oldAllowed=old_allowed,
        patchAllowed=allowed,patch=patch)


def pose(data,amount):
    x0,y0,x1,y1=BOX
    yy,xx=np.mgrid[y0:y1,x0:x1].astype(float)
    sx,sy,error=inverse(xx,yy,amount)
    # Sample actual patch paint/visibility, not two completed poses blended
    # together. Unknown pixels outside this complete bounded patch stay zero.
    beta=sample(data['beta'],sx,sy)
    paint=sample(data['paint'],sx,sy)
    backing=np.asarray(data['backing'],dtype=float).copy()
    backing[...,:3]*=backing[...,3:4]/255
    composed=over(paint,beta,backing[y0:y1,x0:x1])
    np.divide(composed[...,:3]*255,composed[...,3:4],out=composed[...,:3],where=composed[...,3:4]>0)
    composed[composed[...,3]==0,:3]=0
    result=np.asarray(data['backing']).copy()
    # Outside actual patch coverage preserve the backing bytes, including
    # the mother's invisible RGB. Unpremultiplying the whole ROI wrongly
    # cleared 13 transparent, out-of-permission source pixels in the first run.
    use=beta>0
    result[y0:y1,x0:x1][use]=np.clip(np.rint(composed[use]),0,255).astype(np.uint8)
    source=np.asarray(data['mother'])
    result[data['protected']]=source[data['protected']]
    changed=np.any(result!=source,axis=2)
    permission=data['oldAllowed'].copy()
    permission[y0:y1,x0:x1]|=beta>0
    permission&=~data['protected']
    if np.any(changed&~permission):
        raise ValueError('Lowered arm changed protected/outside source pixels')
    # Inspect real source support, not only the destination inverse grid.
    fy,fx=np.where(data['beta']>0)
    fx,fy=fx.astype(float),fy.astype(float)
    px,py=forward(fx,fy,amount)
    ax,ay=forward(fx+.01,fy,amount)
    bx,by=forward(fx,fy+.01,amount)
    cx,cy=forward(fx-.01,fy,amount)
    dx,dy=forward(fx,fy-.01,amount)
    determinant=((ax-cx)*(by-dy)-(bx-dx)*(ay-cy))/.0004
    if np.min(determinant)<.5 or np.any(px<x0+1) or np.any(px>x1-2) or np.any(py<y0+1) or np.any(py>y1-2):
        raise ValueError('Patch folds or escapes the fixed source ROI')
    wx,wy=forward(np.array([SPEC['wristSourcePx'][0]]),np.array([SPEC['wristSourcePx'][1]]),amount)
    return Image.fromarray(result),dict(verticalOffsetSourcePx=amount,
        wristSourcePx=[round(float(wx[0]),8),round(float(wy[0]),8)],
        minimumMaterialJacobian=round(float(determinant.min()),8),
        maximumMaterialJacobian=round(float(determinant.max()),8),
        maximumInverseErrorSourcePx=round(error,10),changedSourcePixels=int(changed.sum()),
        changedOutsidePermission=0,poseRGBAHash=rgba_hash(Image.fromarray(result)))


def frozen_reference(baseline):
    root=ROOT/REFERENCE
    manifest=json.loads((root/'manifest.json').read_text(encoding='utf-8'))
    contract=json.loads((root/'contract.json').read_text(encoding='utf-8'))
    if (manifest['commit']!='2a9688600e17a63253b2a3623fc8cd538c0d7453'
            or manifest['referenceRole']!='frozen-source-input-not-active-animation'
            or manifest['referencePurpose']!='isolate-lowered-wave-peak-with-local-cloth-repair'
            or manifest['file']!='waving.webp' or manifest['contract']!='contract.json'
            or manifest['visualApprovalInherited'] or manifest['installableFullAtlas'] or manifest['installed']
            or hashlib.sha256((root/'waving.webp').read_bytes()).hexdigest().upper()!=manifest['fileSha256']
            or manifest['fileSha256']!='15FBB171AF825AD5B26CE93F4CEFC9A9A16E3DD9BAC58F751BCCA4F9D8C33692'
            or contract['sourceSha256']!=ACCEPTED_SHA or contract['state']!='waving'
            or contract['durationsMs']!=DURATIONS[3]
            or contract['frameHashes']!=[rgba_hash(frame) for frame in baseline]):
        raise ValueError('Original wave reference drifted')
    with Image.open(root/'waving.webp') as saved:
        strip=saved.convert('RGBA')
    if strip.size!=(1536,208) or any(strip.crop((192*i,0,192*(i+1),208)).tobytes()!=frame.tobytes()
                                  for i,frame in enumerate(baseline)):
        raise ValueError('Frozen wave strip does not reconstruct actual old cels')
    return manifest,contract


def lowered_inputs(mother,motion,poses,baseline,include_failure=True):
    decision=json.loads((ROOT/DECISION).read_text(encoding='utf-8'))
    if (decision['scope']!='waving-lower-amplitude-direction-only'
            or decision['answer']!='保留轻抬手，降低幅度（建议）'
            or any(decision[key] for key in ('candidatePixelsApproved','fullMotionApproved',
                'faceGeometryChangeApproved','hostChangeApproved','installationApproved'))):
        raise ValueError('Direction approval must not become rendered-pixel/full-motion approval')
    adoption=json.loads((ROOT/ADOPTION).read_text(encoding='utf-8'))
    if (adoption['scope']!='waving-lower-amplitude-development-basis-only'
            or adoption['answer']!='作为招手开发基础，继续打磨（建议）'
            or adoption['candidatePixelsApprovedAsDevelopmentBasis'] is not True
            or adoption['approvedPeakRGBAHash']!=APPROVED_PEAK or adoption['sourceOffsetPx']!=55
            or any(adoption[key] for key in ('fullMotionApproved','entryExitApproved',
                'faceGeometryChangeApproved','hostChangeApproved','installationApproved'))):
        raise ValueError('Rendered basis approval must not become full-motion/installation approval')
    frozen_reference(baseline)
    data=material(mother)
    neutral,neutral_measure=pose(data,0.)
    if neutral.tobytes()!=poses['peak'].tobytes():
        raise ValueError('Same-material neutral does not reconstruct frozen original raised cel')
    lowered,measure=pose(data,SPEC['verticalOffsetSourcePx'])
    from repair_wave_amplitude import repair
    repaired,repair_measure,hand_mask,repair_allowed=repair(lowered,data['protected'])
    failed_repair=repair(lowered,data['protected'],exclude_old_red=False)[0] if include_failure else None
    frames=[baseline[0],native_frame(repaired),baseline[2],baseline[3]]
    if rgba_hash(frames[1])!=APPROVED_PEAK:
        raise ValueError('Lowered wave does not match the exact rendered peak the user approved')
    return dict(mother=mother,motion=motion,data=data,baseline=baseline,frames=frames,
        lowered=lowered,repaired=repaired,repairMeasure=repair_measure,
        failedRepair=failed_repair,
        handMask=hand_mask,repairAllowed=repair_allowed,
        neutral=neutral,neutralMeasure=neutral_measure,measure=measure)


def inputs():
    return lowered_inputs(*wave_inputs())


def main():
    data=inputs()
    write_animation(OUT,data['frames'],DURATIONS[3])
    data['lowered'].save(OUT/'failed-shear-pose.png')
    data['failedRepair'].save(OUT/'failed-first-cloth-mask.png')
    data['repaired'].save(OUT/'pose.png')
    Image.fromarray(data['handMask'].astype(np.uint8)*255).save(OUT/'hand-protection.png')
    Image.fromarray(data['repairAllowed'].astype(np.uint8)*255).save(OUT/'cloth-repair-permission.png')
    # Compare all four actual native holds, at two useful display sizes.
    for width in (113,224):
        height=round(width*208/192)
        board=Image.new('RGB',(4*(width+12),2*(height+28)),'#f1f0ee')
        draw=ImageDraw.Draw(board)
        for row,frames in enumerate((data['baseline'],data['frames'])):
            for i,frame in enumerate(frames):
                tile=Image.new('RGBA',frame.size,'#f1f0ee');tile.alpha_composite(frame)
                x,y=i*(width+12),row*(height+28)
                board.paste(tile.resize((width,height),Image.Resampling.NEAREST).convert('RGB'),(x+6,y+24))
                draw.text((x+3,y+3),f'{"frozen old" if row==0 else "adopted basis"}: {i} / {DURATIONS[3][i]} ms',fill='#23252b')
        board.save(OUT/f'comparison-{width}px.png')
    transform=camera(clean_cutout(data['mother'])[0])
    detail=dict(sourceSha256=ACCEPTED_SHA,state='waving',nativeRow=3,
        durationsMs=DURATIONS[3],repeatBeforeIdle=3,totalDurationMs=sum(DURATIONS[3]),
        actionDurationMs=3*sum(DURATIONS[3]),sequence=data['motion']['sequence'],
        camera=transform,specification=SPEC,roi=list(BOX),
        peakGeneratedSha256=data['data']['patch']['generatedSha256'],
        baselineFrameHashes=[rgba_hash(f) for f in data['baseline']],
        reference=REFERENCE,
        frameHashes=[rgba_hash(f) for f in data['frames']],
        sameMaterialNeutralPeakRGBAExact=True,neutralMeasurement=data['neutralMeasure'],
        loweredMeasurement=data['measure'],canonicalRestRGBAExact=data['frames'][3].tobytes()==native_frame(data['mother']).tobytes(),
        clothRepair=data['repairMeasure'],
        handLoweringNativePx=SPEC['verticalOffsetSourcePx']*transform['scale'],
        finalPoseRGBAHash=rgba_hash(data['repaired']),
        unchangedHoldIndices=[0,2,3],returnedMiddleCelReused=True,
        newClothArtworkGenerated=True,newHandArtworkUsed=False,
        handScaleChanged=False,handOrientationChanged=False,
        palmRigidWithinEstimatedRect=True,
        faceGeometryChanged=False,wholeBodyRotation=False,nativeInterpolation=False,
        amplitudeDirectionUserApproved=True,visualMotionApproval='pending',
        directionUserDecision=DECISION,
        amplitudeVisualApproval='approved-as-development-basis',
        adoptionScope='waving-lower-amplitude-development-basis-only',userDecision=ADOPTION,
        currentWavingCelsRGBAExact=[rgba_hash(f) for f in data['frames']]==json.loads((ROOT/'candidates/phase5/waving/build.json').read_text(encoding='utf-8'))['frameHashes'],
        adopted=True,activeAtlasChanged=True,installableFullAtlas=False,installed=False,
        method='lower existing raised-cel patch over shared backing; bounded new cloth reconnects shoulder; original translated palm/cape/front hair restored',
        rejectedTrials=['Rotation: real-patch minimum Jacobian .69519551 (too much sleeve compression).',
            'Unrepaired source shear: shoulder and red band visibly disconnected; archived failed-shear-pose.png.',
            'First cloth mask preserved a sliver of old red band beside the thumb; archived failed-first-cloth-mask.png.',
            'Whole-ROI unpremultiplication cleared 13 invisible source RGB pixels; only actual coverage is now composed.'],
        unresolved=['Estimated wrist/attachment, hand protection contour and sleeve shear, not recovered artist layers or physical cloth simulation.',
            'Only the peak cel changes; new cloth edges, middle/rest art differences and shoulder/backing seams still require visual inspection.',
            'Four held frames, 700ms repeated raise/lower and arbitrary entry/exit hard cuts remain.',
            'The chosen 55-source-pixel lowering is a design trial, not a first-principles unique optimum; area preservation does not prove cloth naturalness.',
            'Rendered pixels were approved only as a waving development basis; entry/exit and complete motion remain unapproved.'])
    (OUT/'build.json').write_text(json.dumps(detail,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(detail,indent=2))


if __name__=='__main__':
    main()
