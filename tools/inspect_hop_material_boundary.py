"""Read-only isolation of cropped paint/beta sampling support at a hop hold.

The padded counterfactual is a diagnostic, NOT a replacement active renderer.
Both paint and occlusion need a zero-valued texel outside their local canvas;
rejecting all coordinates just outside the crop discards bilinear coverage.
"""
import json

import numpy as np

import build_jumping as jumping
import hop_contact
from build_idle import coordinates, sample
from locomotion_render import integration_coordinates
from occlusion_material import over
from material_support import LEGACY, ZERO


def inspect():
    source,cleanup,transform,regions,masks,motion,poses=jumping.inputs()
    data,material=jumping.contact_inputs(local_support=LEGACY)
    # This diagnosis applies only to the rigid ascent hold: body/leg roots
    # are zero. All material evaluation still occurs; no source-raster bypass.
    pose=poses[1]
    if pose['bodyY'] != 0 or pose['grounded'] or motion['flightModel']['apexOutputPx'] != 4:
        raise ValueError('Boundary probe requires the actual adopted 4px ascent')
    x,y=integration_coordinates(transform,actor_y=pose['actorY'])
    bx,by=coordinates(x,y,pose,transform,regions,masks)
    expected=sample(material['source'],bx,by)
    actual=hop_contact.sample_pose(material,x,y,pose,transform,regions,masks)
    _,current_material=jumping.contact_inputs(local_support=ZERO)
    current=hop_contact.sample_pose(current_material,x,y,pose,transform,regions,masks)
    visibility=sample(material['visibility'],bx,by)
    known=sample(material['visibleBacking'],bx,by)
    padded=sample(material['backing'],bx,by)
    np.divide(known,visibility[...,None],out=padded,where=visibility[...,None]>1e-12)
    x0,y0,_,_=data['box']
    for paint,beta in zip(material['data']['layers'],material['data']['occlusions']):
        padded_paint=np.pad(paint,((1,1),(1,1),(0,0)))
        padded_beta=np.pad(beta,((1,1),(1,1)))
        padded=over(sample(padded_paint,bx-x0+1,by-y0+1),
                    sample(padded_beta,bx-x0+1,by-y0+1),padded)
    difference=np.max(np.abs(actual-expected),axis=-1)
    repaired=np.max(np.abs(padded-expected),axis=-1)
    affected=difference>1e-10
    yy,xx=np.where(affected)
    if not len(yy) or float(repaired.max())>1e-10:
        raise ValueError('Crop-support hypothesis did not isolate the observed defect')
    return dict(activeRendererChanged=False,installed=False,artworkChanged=False,
        fullMotionApproved=False,probe='actual-4px-ascent-rigid-material-grid',
        localMaterialBox=list(data['box']),affectedHighGridSamples=int(affected.sum()),
        affectedOutputGridBBox=[int(xx.min()),int(yy.min()),int(xx.max()+1),int(yy.max()+1)],
        affectedSourceCoordinateBBox=[float(bx[affected].min()),float(by[affected].min()),
            float(bx[affected].max()),float(by[affected].max())],
        legacyMaximumPremultDifference=float(difference.max()),
        activeV2MaximumPremultDifference=float(np.max(np.abs(current-expected))),
        zeroExtendedMaximumPremultDifference=float(repaired.max()),
        zeroExtendedIdentityWithin1eMinus10=bool(float(repaired.max())<1e-10),
        mechanism='full-canvas visibility includes partial boundary coverage while local sample() rejects coordinates outside its crop; pad paint and beta together to retain the same support',
        limitations=['One actual rigid hold isolates a sampler defect, not all articulated poses.',
            'This diagnostic does not mutate active files or approve any animation.',
            'Grounded/other states and native protection are checked separately in test_material_support.py.'])


if __name__=='__main__':
    print(json.dumps(inspect(),indent=2))
