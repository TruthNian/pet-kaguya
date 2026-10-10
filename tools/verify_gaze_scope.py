"""Compare actual atlases, including untouched action rows and original alpha."""
import hashlib
import json
import numpy as np
from PIL import Image
from canonical import ROOT

def main():
    ref=ROOT/'sources/reference/gaze-opening-v1'
    frozen=json.loads((ref/'manifest.json').read_text(encoding='utf-8'))
    if hashlib.sha256((ref/'atlas.webp').read_bytes()).hexdigest().upper()!=frozen['atlasEncodedSha256']:
        raise ValueError('Pre-correction atlas input changed')
    with Image.open(ref/'atlas.webp') as image:old=np.asarray(image.convert('RGBA'))
    path=ROOT/'candidates/phase5/global/spritesheet.webp'
    with Image.open(path) as image:new=np.asarray(image.convert('RGBA'))
    if old.shape!=new.shape or not np.array_equal(old[...,3],new[...,3]):
        raise ValueError('Eye correction altered atlas geometry or any coverage alpha')
    changed=np.any(old!=new,axis=2)
    allowed=np.zeros(changed.shape,bool)
    for row in (9,10):
        for col in range(8):
            for x0,y0,x1,y1 in ((72,47,96,73),(100,45,125,73)):
                allowed[row*208+y0:row*208+y1,col*192+x0:col*192+x1]=True
    if np.any(changed&~allowed):raise ValueError('Current changes escaped the 16 native eye windows')
    rows=[int(changed[i*208:(i+1)*208].sum()) for i in range(11)]
    report=dict(actionRowsRGBAExact=not any(rows[:9]),allNativeAlphaExact=True,changedPixelsByRow=rows,
        encodedBytes=path.stat().st_size,encodedSHA256=hashlib.sha256(path.read_bytes()).hexdigest().upper(),
        decodedSHA256=hashlib.sha256(new.tobytes()).hexdigest().upper(),fullVisualApproval=False)
    out=ROOT/'work/gaze-sclera-inspection';out.mkdir(parents=True,exist_ok=True)
    (out/'atlas-scope.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report))

if __name__=='__main__':main()
