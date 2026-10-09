"""Actual current low-held hands; face-free fixed-square anatomy edit guide."""
import hashlib
import json
from PIL import Image
from canonical import ROOT,ACCEPTED_SHA,load_canonical

OUT=ROOT/'candidates/phase5/review-hands-pair-v1'
BOX=(400,585,675,805)
SIDE=275
PARENT_HASH='3701641146B3CDF39C71F43A1EF9648511AB6D8565751C31C1BB205CC87664FE'


def parent():
    load_canonical()
    with Image.open(ROOT/'candidates/phase5/review-art-v6/pose.png') as image:pose=image.convert('RGBA')
    if hashlib.sha256(pose.tobytes()).hexdigest().upper()!=PARENT_HASH:
        raise ValueError('Guide requires the recorded current v6, not a rejected compact-hand variant')
    return pose


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    square=Image.new('RGBA',(SIDE,SIDE))
    square.paste(parent().crop(BOX),(0,0));square.save(OUT/'edit-target.png')
    meta=dict(sourceSha256=ACCEPTED_SHA,parentCompositionVersion='review-art-v6',
        parentPoseRGBAHash=PARENT_HASH,sourceCrop=list(BOX),guideCanvas=[SIDE,SIDE],
        transparentPaddingBottomSourcePx=55,faceIncluded=False,
        intent='same low-held hands; plausible palm/thumb/finger/cuff relationships, no fixed-factor scaling',
        faceGeometryChangeAllowed=False,wholeCharacterRedrawAccepted=False,
        poseRedesignAllowed=False,heldTimingChangeAllowed=False,activeAtlasChanged=False,
        visualAcceptance='pending',installed=False)
    (OUT/'guide.json').write_text(json.dumps(meta,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(meta,indent=2))


if __name__=='__main__':main()
