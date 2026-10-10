"""Four native holds, three cels; exact canonical rest and no face redraw."""
import hashlib
import json

import numpy as np

from canonical import ROOT, ACCEPTED_SHA, load_canonical, clean_cutout, camera
from review_wave import inputs as art_inputs, localized_pose, native_frame
from animation_output import write_animation
from protocol import DURATIONS
import wave_middle_basis as middle

OUT = ROOT/'candidates/phase5/waving'


def original_inputs():
    motion = json.loads((ROOT/'sources/canonical/waving-motion.json').read_text(encoding='utf-8'))
    if (motion['sourceSha256'] != ACCEPTED_SHA or not motion['faceShapeLocked']
            or motion['nativeRow'] != 3 or motion['durationsMs'] != DURATIONS[3]
            or motion['sequence'] != ['middle','peak','middle','relaxed']
            or motion['repeatBeforeIdle'] != 3 or motion['nativeInterpolation']
            or motion['visualMotionApproval'] != 'pending'):
        raise ValueError('Wave violates the source/native hold/approval boundary')
    mother = load_canonical()
    poses = {'relaxed':mother}
    for kind in ('middle','peak'):
        _,spec,generated = art_inputs(kind)
        poses[kind] = localized_pose(mother,generated,spec)[0]
    frames = [native_frame(poses[kind]) for kind in motion['sequence']]
    return mother,motion,poses,frames


def inputs():
    mother,motion,poses,baseline=original_inputs()
    # The study always reconstructs original_inputs(), never the adopted
    # production peak, so the frozen old benchmark cannot drift.
    from study_wave_amplitude import lowered_inputs
    data=lowered_inputs(mother,motion,poses,baseline,include_failure=False)
    poses['peak']=data['repaired']
    frames=middle.apply(poses,data['frames'],camera(clean_cutout(mother)[0]))
    return mother,motion,poses,frames


def main():
    mother,motion,poses,frames = inputs()
    for frame in frames:
        pixels = np.asarray(frame)
        if pixels[0,:,3].any() or pixels[-1,:,3].any() or pixels[:,0,3].any() or pixels[:,-1,3].any():
            raise ValueError('Wave touches a cell edge')
    write_animation(OUT,frames,DURATIONS[3])
    metadata = dict(sourceSha256=ACCEPTED_SHA,source='sources/canonical/artwork.png',
        state='waving',nativeRow=3,statesInThisArtifact=['waving'],durationsMs=DURATIONS[3],
        totalDurationMs=sum(DURATIONS[3]),repeatBeforeIdle=3,actionDurationMs=3*sum(DURATIONS[3]),
        sequence=motion['sequence'],uniqueCels=3,returnedMiddleCelReused=True,
        camera=camera(clean_cutout(mother)[0]),sameSourceCoordinateCamera=True,
        facialGeometryRepair=False,generatedFromRejectedSources=False,
        bodyTranslationPx=0,wholeBodyRotation=False,sourceCapeAndForegroundLockPreserved=True,
        fullRedrawAccepted=False,articulatedArmBuilt=False,nativeInterpolation=False,
        canonicalRestRGBAExact=frames[-1].tobytes()==native_frame(mother).tobytes(),
        frameHashes=[hashlib.sha256(frame.tobytes()).hexdigest().upper() for frame in frames],
        amplitudeVisualApproval='approved-as-development-basis',
        amplitudeApprovalScope='waving-lower-amplitude-development-basis-only',
        amplitudeUserDecision='sources/canonical/waving-amplitude-adoption-20261010.json',
        handLoweringSourcePx=55,handLoweringNativePx=55*camera(clean_cutout(mother)[0])['scale'],
        unchangedOriginalHoldIndices=[3],
        **middle.descriptor(),
        method='selected face-free turning-palm middle cel; exact accepted lowered peak and canonical rest; fixed native holds',
        sampling='middle insert first uses a fixed crop-to-source uniform projection; all native frames then share canonical camera, 3x coverage and one terminal Lanczos downsample',
        visualMotionApproval='pending',installableFullAtlas=False,installed=False,
        unresolved=motion['limitations'])
    (OUT/'build.json').write_text(json.dumps(metadata,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(metadata,indent=2))


if __name__=='__main__':
    main()
