"""Fixed face-free study: a low, lightly overlaid pair, not an approved pose."""
import json
from PIL import Image
from canonical import ACCEPTED_SHA,ROOT,load_canonical
from guide_review_hands_pair import parent,PARENT_HASH

OUT=ROOT/'candidates/phase5/review-hands-overlap-v1'
BOX=(385,575,695,825)
SIDE=310


def square(image):
    result=Image.new('RGBA',(SIDE,SIDE))
    result.paste(image.crop(BOX),(0,0))
    return result


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    square(parent()).save(OUT/'edit-target.png')
    square(load_canonical()).save(OUT/'costume-reference.png')
    meta=dict(sourceSha256=ACCEPTED_SHA,parentPoseRGBAHash=PARENT_HASH,
        parentCompositionVersion='review-art-v6',sourceCrop=list(BOX),guideCanvas=[SIDE,SIDE],
        transparentPaddingBottomSourcePx=60,faceIncluded=False,
        inputRoles=['edit target: current cuff, camera, scale and local costume',
                    'costume reference: actual original waist crescent, not an arm pose'],
        studyDirection='one relaxed hand lightly resting over the other at the waist',
        specificPoseUserApproval='pending',directionIsNotAnApprovedResult=True,
        originalMoonMotifRemovalAllowed=False,faceGeometryChangeAllowed=False,
        wholeCharacterRedrawAccepted=False,heldTimingChangeAllowed=False,
        adopted=False,activeAtlasChanged=False,installed=False,visualAcceptance='pending')
    (OUT/'guide.json').write_text(json.dumps(meta,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(meta,indent=2))


if __name__=='__main__':main()
