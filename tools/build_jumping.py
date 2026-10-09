"""Five hop holds with original-material two-link grounded contact."""
import hashlib
import json

import numpy as np
from PIL import Image, ImageDraw

from canonical import ROOT, ACCEPTED_SHA, load_canonical, clean_cutout, camera
from build_idle import specification as idle_specification, region_masks, render
from animation_output import write_animation
from protocol import DURATIONS
from refine_leg_composition import material_inputs
from leg_material import GENERATED_SHA
from locomotion_render import prepare, neutral_evidence
import hop_contact

OUT = ROOT/'candidates/phase5/jumping'


def specification():
    motion = json.loads((ROOT/'sources/canonical/jumping-motion.json').read_text(encoding='utf-8'))
    if (motion['sourceSha256'] != ACCEPTED_SHA or motion['durationsMs'] != DURATIONS[4]
            or len(motion['keyframes']) != 5 or not motion['faceShapeLocked']
            or motion['closedEyeFrames'] != 0 or motion['visualMotionApproval'] != 'pending'):
        raise ValueError('Hop violates locked source/native holds/candidate boundary')
    model = motion['flightModel']
    if (model['airtimeMs'] != sum(DURATIONS[4][1:4]) or model['nativeInterpolation']
            or not 0 < model['apexOutputPx'] <= 8):
        raise ValueError('Hop flight model exceeds the authored camera reserve')
    poses = []
    for index, key in enumerate(motion['keyframes']):
        pose = dict(key)
        if pose['grounded'] != (index in (0, 4)):
            raise ValueError('Hop contact phases changed')
        if pose['grounded']:
            if pose['actorY'] != 0 or not 0 <= pose['bodyY'] <= .8:
                raise ValueError('Grounded hop must pin shoes with only a small leg accommodation')
        else:
            expected = sum(DURATIONS[4][1:index])+DURATIONS[4][index]/2
            if pose['flightTimeMs'] != expected or pose['bodyY'] != 0:
                raise ValueError('Flight must rigidly translate the body at the actual hold midpoint')
            u = expected/model['airtimeMs']
            pose['actorY'] = -4*model['apexOutputPx']*u*(1-u)
        poses.append(pose)
    return motion, poses


def inputs():
    image, cleanup = clean_cutout(load_canonical())
    transform = camera(image)
    regions, _ = idle_specification()
    motion, poses = specification()
    return image, cleanup, transform, regions, region_masks(regions), motion, poses


def contact_inputs():
    # No locomotion approval receipt is imported or inherited by this action.
    data=material_inputs()
    return data,prepare(data,data['mother'])


def comparison(out,old,frames,metadata):
    """Regenerated old height-field counterfactual, not an approved old pet."""
    strip=Image.new('RGBA',(1536,208))
    for index,frame in enumerate(old):strip.paste(frame,(index*192,0))
    strip.save(out/'comparison-old-strip.webp',lossless=True,exact=True,method=6)
    board=Image.new('RGB',(1000,800),'#23252b');draw=ImageDraw.Draw(board)
    for col,index in enumerate((0,4)):
        for row,(frame,label) in enumerate(((old[index],f'height field: slot {index}'),
                                           (frames[index],f'two links: slot {index}'))):
            tile=Image.new('RGBA',frame.size,'#f1f0ee');tile.alpha_composite(frame)
            board.paste(tile.crop((60,143,135,204)).resize((450,366),Image.Resampling.NEAREST).convert('RGB'),
                        (col*500,row*400+20))
            draw.text((col*500+5,row*400+3),label,fill='white')
    board.save(out/'contact-detail.png')
    width=113;height=round(width*208/192)
    board=Image.new('RGB',(4*(width+12),2*(height+28)),'#23252b');draw=ImageDraw.Draw(board)
    for row,color in enumerate(('#23252b','#f1f0ee')):
        for col,(frame,label) in enumerate(((old[0],'old anticipation'),(frames[0],'new anticipation'),
                                           (old[4],'old landing'),(frames[4],'new landing'))):
            tile=Image.new('RGBA',frame.size,color);tile.alpha_composite(frame)
            board.paste(tile.resize((width,height),Image.Resampling.NEAREST).convert('RGB'),
                        (col*(width+12)+6,row*(height+28)+24))
            draw.text((col*(width+12)+3,row*(height+28)+3),label,fill='white')
    board.save(out/'contact-comparison-113px.png')
    fields=['sourceSha256','state','nativeRow','camera','durationsMs','actorOffsetsPx',
            'bodyCompressionOutputPx','tipAnglesDegrees','nativeInterpolation','repeatBeforeIdle']
    reference=dict(referenceRole='regenerated-counterfactual-not-active-animation',
        referencePurpose='isolate-grounded-two-link-knees-vs-vertical-height-field',
        file='comparison-old-strip.webp',contract={field:metadata[field] for field in fields},
        method='previous source-coordinate height field; same source, camera, poses and schedule',
        frameHashes=[hashlib.sha256(frame.tobytes()).hexdigest().upper() for frame in old],
        candidateFrameHashes=metadata['frameHashes'],
        airCelsRGBAExact=[old[i].tobytes()==frames[i].tobytes() for i in (1,2,3)],
        groundedChangedPixels=[int(np.any(np.asarray(old[i])!=np.asarray(frames[i]),axis=2).sum()) for i in (0,4)],
        visualApprovalInherited=False,installableFullAtlas=False,installed=False,
        limitations=['Regenerated comparison is not a frozen historical release or visual approval.',
                     'Only five held poses; not continuous takeoff, landing or recovery.',
                     'Changed edge colors around planted shoes may be moving backing hair, not shoe displacement.'])
    (out/'contact-proof.json').write_text(json.dumps(reference,indent=2)+'\n',encoding='utf-8')


def main():
    source, cleanup, transform, regions, masks, motion, poses = inputs()
    data,material=contact_inputs()
    frames = [hop_contact.render(material,pose,transform,regions,masks) for pose in poses]
    old=[render(source,pose,transform,regions,masks) for pose in poses]
    if any(old[i].tobytes()!=frames[i].tobytes() for i in (1,2,3)):
        raise ValueError('Grounded-contact repair must not change the three original air cels')
    joints=[hop_contact.joint_evidence(data,pose,transform) for pose in poses]
    neutral=neutral_evidence(material,data['mother'],transform)
    if not neutral['directSamplerNeutralRGBAExact']:
        raise ValueError('The reused material changed the neutral source')
    bounds = []
    for frame in frames:
        rgba = np.asarray(frame)
        if rgba[0,:,3].any() or rgba[-1,:,3].any() or rgba[:,0,3].any() or rgba[:,-1,3].any():
            raise ValueError('Hop touches a cell border')
        yy, xx = np.where(rgba[...,3] > 8)
        bounds.append([int(xx.min()), int(yy.min()), int(xx.max()+1), int(yy.max()+1)])
    write_animation(OUT, frames, DURATIONS[4])
    metadata = dict(sourceSha256=ACCEPTED_SHA, source='sources/canonical/artwork.png',
        state='jumping', nativeRow=4, statesInThisArtifact=['jumping'],
        generatedFromRejectedSources=False, facialGeometryRepair=False, closedEyeFrames=0,
        durationsMs=DURATIONS[4], totalDurationMs=sum(DURATIONS[4]),
        repeatBeforeIdle=3, actionDurationMs=3*sum(DURATIONS[4]), camera=transform,
        alphaCleanup=cleanup, actorOffsetsPx=[pose['actorY'] for pose in poses],
        bodyCompressionOutputPx=[pose['bodyY'] for pose in poses],
        tipAnglesDegrees=[[pose['earAngle'],pose['hairAngle']] for pose in poses],
        groundedFrames=[index for index, pose in enumerate(poses) if pose['grounded']],
        visibleBoundsAlphaAbove8=bounds, nativeInterpolation=False,
        method='original-source two-link knees at grounded holds; planted shoes; rigid actor flight at actual hold midpoints; no head/body resizing',
        groundedContactVersion='two-link-source-material-v1',legCompositionVersion='leg-material-v2',
        legBackingGeneratedSha256=GENERATED_SHA,contactRigJoints=joints,jointEvidenceDecimalPlaces=9,
        sourceAlphaAndOcclusionSeparated=True,normalizedKnownBacking=True,
        artistLayerRecoveryClaimed=False,newArtworkGenerated=False,physicalBalanceProven=False,
        continuousLandingProven=False,originalAirCelsRGBAExact=True,
        strategyUserApproval='pending',strategyApprovalInheritedFromLocomotion=False,
        **neutral,
        sampling='3x coverage integration from high-resolution source, one terminal Lanczos downsample',
        visualMotionApproval='pending', installableFullAtlas=False, installed=False,
        frameHashes=[hashlib.sha256(frame.tobytes()).hexdigest().upper() for frame in frames],
        unresolved=motion['limitations'])
    (OUT/'build.json').write_text(json.dumps(metadata, indent=2)+'\n', encoding='utf-8')
    comparison(OUT,old,frames,metadata)
    print(json.dumps({key:value for key,value in metadata.items() if key not in ('frameHashes','contactRigJoints')}, indent=2))


if __name__ == '__main__':
    main()
