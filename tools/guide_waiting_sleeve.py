"""Face-free fixed-crop study of the actual held waiting sleeve."""
import hashlib
import json
from PIL import Image
from canonical import ROOT, ACCEPTED_SHA, load_canonical

OUT=ROOT/'candidates/phase5/waiting-sleeve-v1'
BOX=(280,480,620,975)
PARENT_HASH='115DC5C3C52D75A3DB9FEA5E783DC80192C56B58705094954318F7829A30C488'
SIDE=495


def parent():
    load_canonical()
    with Image.open(ROOT/'candidates/phase5/waiting-art-v1/pose.png') as image:pose=image.convert('RGBA')
    if hashlib.sha256(pose.tobytes()).hexdigest().upper()!=PARENT_HASH:
        raise ValueError('Waiting guide requires the actual held-pose source')
    return pose


def square(image):
    result=Image.new('RGBA',(SIDE,SIDE))
    result.paste(image.crop(BOX),(0,0))
    return result


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    square(parent()).save(OUT/'edit-target.png')
    square(load_canonical()).save(OUT/'style-reference.png')
    metadata=dict(sourceSha256=ACCEPTED_SHA,parentPoseRGBAHash=PARENT_HASH,
        parentCompositionVersion='waiting-art-v1',sourceCrop=list(BOX),guideCanvas=[SIDE,SIDE],
        transparentPaddingRightSourcePx=155,faceIncluded=False,faceGeometryChangeAllowed=False,
        heldHandPositionChangeAllowed=False,newPoseAllowed=False,
        role='complete raised sleeve flow/volume, not recoloring disconnected patches',
        inputRoles=['current waiting sleeve and fixed wrist/shoulder context',
                    'canonical material/style only, not its relaxed arm pose'],
        adoption='guide only; current bounded development adoption is recorded separately in waiting-art-v2',
        activeAtlasChanged=False,installed=False)
    (OUT/'guide.json').write_text(json.dumps(metadata,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(metadata,indent=2))


if __name__=='__main__':main()
