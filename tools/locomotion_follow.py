"""Root-driven, periodic visible-tip response; not recovered physical layers.

The held root is the input to a first-order lag. Native cels sample that
response at hold midpoints; the host still displays discrete static images.
"""
import math

import numpy as np

from build_idle import region_masks, sample, smooth


METHOD = 'periodic-first-order-root-lag; visible-tip-fields-only'


def periodic_lag(roots, durations, tau, gain):
    if (not roots or len(roots) != len(durations)
            or any(isinstance(x, bool) or not math.isfinite(x) for x in roots)
            or any(isinstance(t, bool) or not math.isfinite(t) or t <= 0 for t in durations)
            or isinstance(tau, bool) or not math.isfinite(tau) or tau <= 0
            or isinstance(gain, bool) or not math.isfinite(gain) or not 0 <= gain <= 1):
        raise ValueError('Invalid held-input lag')
    # Compose one cycle S_end=A*S_start+B, then solve its fixed point.
    decays = [math.exp(-t/tau) for t in durations]
    b = 0.
    for root, decay in zip(roots, decays):
        b = decay*b+(1-decay)*root
    denominator = -math.expm1(-sum(durations)/tau)
    initial = b/denominator
    state = initial
    offsets = []
    for root, duration, decay in zip(roots, durations, decays):
        midpoint = root+(state-root)*math.exp(-duration/(2*tau))
        offsets.append(round(gain*(midpoint-root), 12))
        state = root+(state-root)*decay
    return dict(initialStateSourcePx=round(initial,12), endStateSourcePx=round(state,12),
                offsetsSourcePx=offsets)


def profile(motion):
    spec = motion['followThrough']
    if (motion['secondaryMotion'] != METHOD or spec['input'] != 'held-root-horizontal-source-px'
            or spec['sample'] != 'native-hold-midpoint' or spec['boundary'] != 'periodic-steady-state'
            or spec['maximumTipOffsetSourcePx'] != 2.1
            or spec['protectedHeadRect'] != [275,20,955,485]
            or spec['protectedFrontRect'] != [290,450,950,1040]
            or spec['protectedLegRect'] != [425,936,810,1240]
            or spec['protectionFadeSourcePx'] != 32
            or set(spec['parts']) != {'ear','hair'}):
        raise ValueError('Follow-through may not change source ownership or host contract')
    roots = [key['rootSourcePx'][0] for key in motion['keyframes']]
    result = {}
    for name, part in spec['parts'].items():
        if set(part) != {'timeConstantMs','gain'}:
            raise ValueError('Unexpected lag parameters')
        result[name] = periodic_lag(roots,motion['durationsMs'],part['timeConstantMs'],part['gain'])
        if max(abs(v) for v in result[name]['offsetsSourcePx']) > spec['maximumTipOffsetSourcePx']:
            raise ValueError('Tip response exceeds the restrained source-space budget')
    return result


def fields(regions, spec):
    """Soft geometry influence, with exact front/leg/face/shoe exclusions.

    These masks identify visible tips only; they are not foreground mattes.
    The single backing inverse map bends existing pixels and creates no
    independently moving layer or newly observed occluded artwork.
    """
    masks = region_masks(regions)
    width,height = regions['canvas']
    yy,xx = np.mgrid[:height,:width].astype(float)
    protected = [regions['protectedFace'],spec['protectedHeadRect'],spec['protectedFrontRect'],
                 spec['protectedLegRect'],*regions['shoeProtectedRects']]
    protection = np.ones((height,width), dtype=float)
    for x0,y0,x1,y1 in protected:
        distance = np.maximum.reduce([x0-xx,xx-x1,y0-yy,yy-y1,np.zeros_like(xx)])
        protection *= smooth(0,spec['protectionFadeSourcePx'],distance)
    result = {name:np.zeros_like(protection) for name in ('ear','hair')}
    for region in regions['regions']:
        name = region['name'].split('_')[0]
        px,py = region['pivot']
        influence = masks[region['name']]*smooth(*region['ramp'],np.hypot(xx-px,yy-py))*protection
        result[name] = np.maximum(result[name],influence)
    return result


def coordinates(x,y,key,weights):
    offset = np.zeros_like(x)
    for name,amount in key.get('followSourcePx',{}).items():
        offset += amount*sample(weights[name],x,y)
    return x-offset,y
