"""Adopted height-only basis vs frozen 8px; no complete motion approval."""
import copy
import hashlib
import json

from PIL import Image
import numpy as np

from canonical import ROOT, ACCEPTED_SHA
from animation_output import write_animation
import build_jumping as jumping
import hop_contact

OUT = ROOT/'candidates/phase5/jumping-height-v1'
REFERENCE = ROOT/'sources/reference/jumping-height-8px'
SHARED = ['sourceSha256','state','nativeRow','camera','durationsMs','repeatBeforeIdle',
          'bodyCompressionOutputPx','tipAnglesDegrees','groundedFrames',
          'groundedContactVersion','legCompositionVersion','legBackingGeneratedSha256']


def rgba_hash(image):
    return hashlib.sha256(image.convert('RGBA').tobytes()).hexdigest().upper()


def changed_poses(poses, old_apex=8, new_apex=4):
    if (isinstance(old_apex,bool) or isinstance(new_apex,bool)
            or not np.isfinite([old_apex,new_apex]).all()
            or old_apex != 8 or new_apex != 4 or len(poses) != 5):
        raise ValueError('This study isolates a fixed 8px to 4px height change')
    result=copy.deepcopy(poses)
    for index,pose in enumerate(result):
        if pose['grounded'] != (index in (0,4)):
            raise ValueError('Study cannot change the original contact phases')
        if not pose['grounded']:
            pose['actorY'] *= new_apex/old_apex
    return result


def inputs():
    motion=json.loads((REFERENCE/'motion.json').read_text(encoding='utf-8'))
    source,cleanup,transform,regions,masks,motion,baseline=jumping.inputs(motion)
    if motion['flightModel']['apexOutputPx'] != 8:
        raise ValueError('The frozen reference must be the original 8px baseline')
    current=json.loads((REFERENCE/'contract.json').read_text(encoding='utf-8'))
    manifest=json.loads((REFERENCE/'manifest.json').read_text(encoding='utf-8'))
    if (hashlib.sha256((REFERENCE/manifest['file']).read_bytes()).hexdigest().upper()
            != '9BD0F25575A378F9CB4519581A10E7A15FFF8B08066009CB0E09D9FF335D9ACB'):
        raise ValueError('Frozen 8px reference file changed')
    if (current['sourceSha256'] != ACCEPTED_SHA or current['camera'] != transform
            or current['actorOffsetsPx'] != [pose['actorY'] for pose in baseline]
            or current['visualMotionApproval'] != 'pending' or current['installed']):
        raise ValueError('Frozen hop contract does not match the study source')
    data,material=jumping.contact_inputs()
    return source,transform,regions,masks,current,material,baseline,changed_poses(baseline)


def render_frames(material,poses,transform,regions,masks):
    return [hop_contact.render(material,pose,transform,regions,masks) for pose in poses]


def main():
    source,transform,regions,masks,current,material,baseline,trial=inputs()
    old=render_frames(material,baseline,transform,regions,masks)
    if [rgba_hash(frame) for frame in old] != current['frameHashes']:
        raise ValueError('Baseline must independently reconstruct the frozen 8px five cels')
    # Contact cels are the freshly reconstructed original materials, not new poses.
    frames=[old[i] if i in (0,4) else hop_contact.render(material,pose,transform,regions,masks)
            for i,pose in enumerate(trial)]
    for frame in frames:
        a=np.asarray(frame)
        if a[0,:,3].any() or a[-1,:,3].any() or a[:,0,3].any() or a[:,-1,3].any():
            raise ValueError('Height study touches a native cell boundary')
    write_animation(OUT,frames,current['durationsMs'])
    active=json.loads((jumping.OUT/'build.json').read_text(encoding='utf-8'))
    if (active['frameHashes'] != [rgba_hash(frame) for frame in frames]
            or active['actorOffsetsPx'] != [pose['actorY'] for pose in trial]
            or any(active[field] != current[field] for field in SHARED)
            or active['heightApprovalScope'] != jumping.height_decision()['scope']):
        raise ValueError('Adopted current hop differs from the approved single-factor trial')
    old_actor=[pose['actorY'] for pose in baseline]
    new_actor=[pose['actorY'] for pose in trial]
    old_root=[pose['actorY']+pose['bodyY'] for pose in baseline]
    new_root=[pose['actorY']+pose['bodyY'] for pose in trial]
    max_step=lambda values:float(np.max(np.abs(np.diff(values))))
    metadata={field:current[field] for field in SHARED}
    metadata.update(previewVariant='jumping_height',source='sources/canonical/artwork.png',
        referencePurpose='isolate-flight-height-only',baselineApexOutputPx=8,candidateApexOutputPx=4,
        actorOffsetsPx=new_actor,baselineActorOffsetsPx=old_actor,
        keyframes=trial,baselineKeyframes=baseline,baselineFrameHashes=current['frameHashes'],
        frameHashes=[rgba_hash(frame) for frame in frames],
        baselineActualCelsRGBAExact=True,groundedCelsRGBAExact=True,
        onlyFlightActorTranslationChanged=True,facialGeometryRepair=False,newArtworkGenerated=False,
        nativeInterpolation=False,continuousLandingProven=False,physicalBalanceProven=False,
        animationBuilt=True,visualMotionApproval='pending',strategyUserApproval='pending',
        adopted=True,activeAtlasChanged=True,installableFullAtlas=False,installed=False,
        adoptionScope=jumping.height_decision()['scope'],userDecision=jumping.HEIGHT_DECISION,
        heightVisualApproval='approved-as-development-basis',currentJumpingCelsRGBAExact=True,
        actorOnlyMaximumAdjacentStepPx={'current':max_step(old_actor),'trial':max_step(new_actor)},
        rootMaximumAdjacentStepPx={'current':max_step(old_root),'trial':max_step(new_root)},
        maximumFlightHeightBeforeAbruptReturnPx={'current':8,'trial':4},
        displayHeightBeforeAbruptReturnPx=[{'width':w,'current':8*w/192,'trial':4*w/192}
                                          for w in (80,113,192,224)],
        method='same original high-resolution material/camera sampler; only three actor-flight offsets halved',
        limitations=['4px is accepted as a height-only development basis, not a unique optimum or full-motion acceptance.',
            'The five native holds, three action cycles, ground compression and tip angles are unchanged.',
            'Smaller translation may reduce a height cut but does not repair arm/pose cuts, interpolation or landing recovery.',
            'Actual-size readability, restraint and naturalness still need human review.',
            'Only the active development hop height is adopted; installed pet and host remain unchanged; no FPS/resolution/performance improvement.'])
    (OUT/'build.json').write_text(json.dumps(metadata,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({key:metadata[key] for key in ('previewVariant','candidateApexOutputPx',
        'groundedCelsRGBAExact','rootMaximumAdjacentStepPx','adopted','activeAtlasChanged')},indent=2))


if __name__ == '__main__':
    main()
