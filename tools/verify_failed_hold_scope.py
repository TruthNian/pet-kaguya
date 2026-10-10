"""Read-only body-only failed update scope; no art rebuild or aesthetics claim."""
import hashlib
import json
import numpy as np
from PIL import Image
from canonical import ROOT


def main():
    before=ROOT/'work/pre-failed-hold-5ba08eb.webp'
    if hashlib.sha256(before.read_bytes()).hexdigest().upper()!='5A1A93C1A709F98E6F3359F5E6A3241ABFECE2850695BC1E05590C895F9DC94B':
        raise ValueError('Expected the exact pre-hold current atlas')
    with Image.open(before) as image:old=np.asarray(image.convert('RGBA'))
    path=ROOT/'candidates/phase5/global/spritesheet.webp'
    with Image.open(path) as image:new=np.asarray(image.convert('RGBA'))
    if old.shape!=new.shape:raise ValueError('Body update changed native atlas geometry')
    changed=np.any(old!=new,axis=2)
    if np.any(changed[:5*208]) or np.any(changed[6*208:]):
        raise ValueError('Failed update changed another state or a gaze cell')
    baseline=json.loads((ROOT/'sources/reference/failed-body-before/build.json').read_text(encoding='utf-8'))
    current=json.loads((ROOT/'candidates/phase5/failed/build.json').read_text(encoding='utf-8'))
    if (baseline['mouthPoseRGBAHash']!=current['mouthPoseRGBAHash']
            or baseline['durationsMs']!=current['durationsMs'] or baseline['camera']!=current['camera']
            or any(p['bodyY']!=0 for p in current['keyframes'])
            or any((a['earAngle'],a['hairAngle'])!=(b['earAngle'],b['hairAngle'])
                for a,b in zip(baseline['keyframes'],current['keyframes']))):
        raise ValueError('Source mouth or retained ear/hair poses changed')
    report=dict(changedPixelsByRow=[int(changed[row*208:(row+1)*208].sum()) for row in range(11)],
        alphaChangedPixels=int((old[...,3]!=new[...,3]).sum()),
        otherTenRowsRGBAExact=True,mouthSourcePoseRGBAExact=True,earHairPosesAndHoldsUnchanged=True,
        sourceRebuilds=0,encodedBytes=path.stat().st_size,decodedBytes=new.nbytes,
        encodedSha256=hashlib.sha256(path.read_bytes()).hexdigest().upper(),
        decodedSha256=hashlib.sha256(new.tobytes()).hexdigest().upper(),
        fullMotionApproved=False,humanBodyApprovalClaimed=False)
    (ROOT/'work/failed-hold-scope.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report))


if __name__=='__main__':main()
