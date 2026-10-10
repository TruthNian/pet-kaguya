"""Read-only scope check against the actual 6c0e537 atlas; no source rebuild."""
import hashlib
import json

import numpy as np
from PIL import Image

from canonical import ROOT


def main():
    before=ROOT/'work/pre-wave-middle-6c0e537.webp'
    if hashlib.sha256(before.read_bytes()).hexdigest().upper()!='E0A52D0651977147D358465DD080C5BABCA6C0848BCD5FF7DC4EDEB18838A102':
        raise ValueError('Expected the exact pre-middle development atlas')
    with Image.open(before) as image:old=np.asarray(image.convert('RGBA'))
    path=ROOT/'candidates/phase5/global/spritesheet.webp'
    with Image.open(path) as image:new=np.asarray(image.convert('RGBA'))
    if old.shape!=new.shape:raise ValueError('Middle update changed native atlas geometry')
    allowed=np.zeros(old.shape[:2],bool)
    for col in (0,2):allowed[3*208+86:3*208+176,col*192+35:col*192+87]=True
    changed=np.any(old!=new,axis=2)
    if np.any(changed&~allowed):raise ValueError('Middle update escaped two bounded arm cells')
    rows=[int(changed[i*208:(i+1)*208].sum()) for i in range(11)]
    report=dict(changedPixelsByRow=rows,onlyTwoMiddleArmWindowsChanged=True,
        acceptedPeakAndCanonicalRestRGBAExact=True,otherTenRowsRGBAExact=True,
        sourceRebuilds=0,encodedBytes=path.stat().st_size,
        encodedSha256=hashlib.sha256(path.read_bytes()).hexdigest().upper(),
        decodedSha256=hashlib.sha256(new.tobytes()).hexdigest().upper(),
        humanMiddleApprovalClaimed=False,fullMotionApproved=False)
    (ROOT/'work/wave-middle-scope.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report))


if __name__=='__main__':main()
