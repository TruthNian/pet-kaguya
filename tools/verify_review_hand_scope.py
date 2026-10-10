"""Read-only current hand scope check, not an anatomy/motion certificate."""
import hashlib
import json
import numpy as np
from PIL import Image
from canonical import ROOT


def main():
    before=ROOT/'work/pre-review-hands-a9cfee0.webp'
    if hashlib.sha256(before.read_bytes()).hexdigest().upper()!='EBC1EF3DC54B7AD83B861D50CA05F21B3517CA973002205F6AB62745A4AE5669':
        raise ValueError('Expected exact pre-hand development atlas')
    with Image.open(before) as image:old=np.asarray(image.convert('RGBA'))
    path=ROOT/'candidates/phase5/global/spritesheet.webp'
    with Image.open(path) as image:new=np.asarray(image.convert('RGBA'))
    if old.shape!=new.shape:raise ValueError('Hand update changed native atlas geometry')
    allowed=np.zeros(old.shape[:2],bool)
    for col in range(6):allowed[8*208+90:8*208+145,col*192+55:col*192+110]=True
    changed=np.any(old!=new,axis=2)
    if np.any(changed&~allowed) or not np.array_equal(old[...,3],new[...,3]):
        raise ValueError('Hand update changed non-hand RGBA or coverage')
    report=dict(changedPixelsByRow=[int(changed[row*208:(row+1)*208].sum()) for row in range(11)],
        changedPixelsByReviewCel=[int(changed[8*208:9*208,col*192:(col+1)*192].sum()) for col in range(8)],
        onlyHandCuffRGBChanged=True,allAlphaExact=True,otherTenRowsRGBAExact=True,
        encodedBytes=path.stat().st_size,decodedBytes=new.nbytes,
        encodedSha256=hashlib.sha256(path.read_bytes()).hexdigest().upper(),
        decodedSha256=hashlib.sha256(new.tobytes()).hexdigest().upper(),
        sourceRebuilds=0,humanHandApprovalClaimed=False,fullMotionApproved=False)
    (ROOT/'work/review-hand-scope.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report))


if __name__=='__main__':main()
