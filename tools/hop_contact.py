"""Grounded hop contact using original leg materials and two-link knees.

Root translation and foot world position are independent. A grounded root
descends while both shoes remain at the original plane; the two links bend
without changing their design lengths. These are frontal puppet hypotheses,
not recovered anatomy, measured forces or continuous host physics.
"""
import math
from numbers import Real

import numpy as np
from PIL import Image

from build_idle import coordinates
from leg_material import inverse_kinematics
from locomotion_render import evaluate, integration_coordinates, quantize
from protocol import WIDTH, HEIGHT


def key(pose,scale):
    values=[scale,*[pose.get(name) for name in ('actorY','bodyY','earAngle','hairAngle')]]
    if (any(isinstance(value,bool) or not isinstance(value,Real) or not math.isfinite(value)
            for value in values) or scale<=0
            or not isinstance(pose.get('grounded'),bool)
            or not -8<=pose['actorY']<=0
            or not 0<=pose['bodyY']<=.8
            or abs(pose['earAngle'])>.2 or abs(pose['hairAngle'])>.08
            or pose['grounded'] is not (pose['actorY']==0)
            or (not pose['grounded'] and pose['bodyY']!=0)):
        raise ValueError('Hop contact needs original small compression and actual contact flags')
    # Actor flight is inverted in output-pixel camera arithmetic, separately
    # from the local contact rig. This retains the old air-cel sampling order
    # at exact integer-rounding boundaries; no frozen neutral/source shortcut.
    root=pose['bodyY']/scale
    return dict(rootSourcePx=[0,root],left=[0,0],right=[0,0])


def sample_pose(material,x,y,pose,transform,regions,masks):
    """Sample in actor-local coordinates (flight already inverted by camera)."""
    x,y=np.asarray(x,dtype=float),np.asarray(y,dtype=float)
    current=key(pose,transform['scale'])
    # The root already carries bodyY. Only old ear/hair angular fields enter
    # backing coordinates, never the old vertical leg/dress compression.
    tips=dict(bodyY=0,earAngle=pose['earAngle'],hairAngle=pose['hairAngle'])
    def fields(qx,qy):
        return coordinates(qx,qy,tips,transform,regions,masks)
    return evaluate(material,x,y,current,1,source_fields=fields)


def render(material,pose,transform,regions,masks,*,terminal=None):
    key(pose,transform['scale'])
    x,y=integration_coordinates(transform,actor_y=pose['actorY'])
    pixels=sample_pose(material,x,y,pose,transform,regions,masks)
    if terminal is not None:
        return terminal(pixels)
    high=quantize(pixels)
    frame=high.convert('RGBa').resize((WIDTH,HEIGHT),Image.Resampling.LANCZOS).convert('RGBA')
    result=np.asarray(frame).copy()
    result[result[...,3]==0,:3]=0
    return Image.fromarray(result)


def joint_evidence(data,pose,transform):
    current=key(pose,transform['scale'])
    root=np.asarray(current['rootSourcePx'])
    actor=np.array([0,pose['actorY']/transform['scale']])
    evidence=[]
    for name,leg in zip(('left','right'),data['spec']['legs']):
        offset=np.asarray(current[name])-root
        hip,knee,ankle,lengths=inverse_kinematics(leg,*offset)
        actual=[float(np.linalg.norm(knee-hip)),float(np.linalg.norm(ankle-knee))]
        world=[(point+root+actor).tolist() for point in (hip,knee,ankle)]
        expected=np.asarray(leg['ankle'])+actor
        if max(abs(a-b) for a,b in zip(actual,lengths))>1e-9:
            raise ValueError('Contact changed a design bone length')
        if not np.allclose(world[2],expected,rtol=0,atol=1e-12):
            raise ValueError('Contact moved a planted foot target')
        evidence.append(dict(name=name,rootSourcePx=(root+actor).tolist(),
            relativeAnkleOffsetSourcePx=offset.tolist(),worldJointSourcePx=world,
            designSegmentLengthsSourcePx=lengths,actualSegmentLengthsSourcePx=actual,
            grounded=pose['grounded']))
    # Statistics precision is declared, not a tolerance on raster rebuilds.
    # Validate unrounded geometry above; only the serialized evidence rounds.
    for entry in evidence:
        for name in ('rootSourcePx','relativeAnkleOffsetSourcePx','worldJointSourcePx',
                     'designSegmentLengthsSourcePx','actualSegmentLengthsSourcePx'):
            entry[name]=np.round(entry[name],9).tolist()
    return evidence
