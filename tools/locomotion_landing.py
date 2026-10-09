"""Select rising/landing poses using real cyclic holds, not interpolation."""
from fractions import Fraction


def reference(spec,durations):
    if (spec!=dict(curve='cubic-zero-endpoint-slope',
                   sampleTimes='rise/peak/approach midpoints; takeoff hold end; contact start',
                   peakOffsetSourcePx=[5,-7.5],offsetDecimalPlaces=12,
                   steps=[dict(foot='left',takeoff=0,rise=1,peak=2,approach=3,contact=4,contactCycle=0),
                          dict(foot='right',takeoff=4,rise=5,peak=6,approach=7,contact=0,contactCycle=1)])
            or len(durations)!=8
            or any(isinstance(t,bool) or not isinstance(t,int) or t<=0 for t in durations)):
        raise ValueError('Landing reference must use the two real frontal swing slots')
    starts=[sum(durations[:index]) for index in range(8)]
    output=[]
    for step in spec['steps']:
        takeoff,rise,peak,approach,contact=[step[key] for key in ('takeoff','rise','peak','approach','contact')]
        takeoff_time=Fraction(starts[takeoff]+durations[takeoff])
        rise_time=Fraction(2*starts[rise]+durations[rise],2)
        peak_time=Fraction(2*starts[peak]+durations[peak],2)
        approach_time=Fraction(2*starts[approach]+durations[approach],2)
        contact_time=Fraction(starts[contact]+step['contactCycle']*sum(durations))
        rising_u=(rise_time-takeoff_time)/(peak_time-takeoff_time)
        rising_weight=3*rising_u*rising_u-2*rising_u*rising_u*rising_u
        u=(approach_time-peak_time)/(contact_time-peak_time)
        # Cubic Hermite rise/descent: zero *reference* endpoint slopes.
        # Native playback still holds the selected pose for the whole slot.
        weight=1-3*u*u+2*u*u*u
        offset=[round(float(Fraction(str(v))*weight),12) for v in spec['peakOffsetSourcePx']]
        rising=[round(float(Fraction(str(v))*rising_weight),12) for v in spec['peakOffsetSourcePx']]
        output.append(dict(**step,takeoffReferenceMs=float(takeoff_time),riseReferenceMs=float(rise_time),
                           peakReferenceMs=float(peak_time),riseWeightFraction=[rising_weight.numerator,rising_weight.denominator],
                           approachReferenceMs=float(approach_time),contactReferenceMs=float(contact_time),
                           approachWeightFraction=[weight.numerator,weight.denominator],
                           riseOffsetSourcePx=rising,peakOffsetSourcePx=spec['peakOffsetSourcePx'],approachOffsetSourcePx=offset,
                           contactOffsetSourcePx=[0,0]))
    return output
