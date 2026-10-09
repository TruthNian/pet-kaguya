"""Choose landing-approach poses from real holds; do not invent interpolation."""
from fractions import Fraction


def reference(spec,durations):
    if (spec!=dict(curve='cubic-zero-endpoint-slope',
                   sampleTimes='peak midpoint; approach midpoint; contact start',
                   peakOffsetSourcePx=[5,-7.5],offsetDecimalPlaces=12,
                   steps=[dict(foot='left',peak=1,approach=2,contact=3),
                          dict(foot='right',peak=5,approach=6,contact=7)])
            or len(durations)!=8
            or any(isinstance(t,bool) or not isinstance(t,int) or t<=0 for t in durations)):
        raise ValueError('Landing reference must use the two real frontal swing slots')
    starts=[sum(durations[:index]) for index in range(8)]
    output=[]
    for step in spec['steps']:
        peak,approach,contact=[step[key] for key in ('peak','approach','contact')]
        peak_time=Fraction(2*starts[peak]+durations[peak],2)
        approach_time=Fraction(2*starts[approach]+durations[approach],2)
        contact_time=Fraction(starts[contact])
        u=(approach_time-peak_time)/(contact_time-peak_time)
        # Cubic Hermite descent: zero *reference* slope at either end.
        # Native playback still holds the selected pose for the whole slot.
        weight=1-3*u*u+2*u*u*u
        offset=[round(float(Fraction(str(v))*weight),12) for v in spec['peakOffsetSourcePx']]
        output.append(dict(**step,peakReferenceMs=float(peak_time),
                           approachReferenceMs=float(approach_time),contactReferenceMs=float(contact_time),
                           approachWeightFraction=[weight.numerator,weight.denominator],
                           peakOffsetSourcePx=spec['peakOffsetSourcePx'],approachOffsetSourcePx=offset,
                           contactOffsetSourcePx=[0,0]))
    return output
