"""Face-free, fixed-crop inputs for a continuous current-pose sleeve edit."""
import hashlib
import json
from PIL import Image
from canonical import ROOT, ACCEPTED_SHA, load_canonical

OUT=ROOT/'candidates/phase5/review-sleeves-v2'
BOX=(300,500,960,1040)
PARENT_HASH='0F0F16D20970DC9AD1F7BB419B1E7BA22BE2C6E054A299298A53E2913EB81D45'

def parent():
    load_canonical()
    with Image.open(ROOT/'candidates/phase5/review-art-v5/pose.png') as opened:
        image=opened.convert('RGBA')
    if hashlib.sha256(image.tobytes()).hexdigest().upper()!=PARENT_HASH:
        raise ValueError('Cloth edit requires the actual current v5 pose')
    return image

def square(image):
    # No portrait/head/face is sent. Transparent padding below the fixed crop
    # makes raw-output projection explicit; never fit a character bounding box.
    result=Image.new('RGBA',(660,660))
    result.paste(image.crop(BOX),(0,0))
    return result

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    square(parent()).save(OUT/'edit-target.png')
    square(load_canonical()).save(OUT/'style-reference.png')
    metadata=dict(sourceSha256=ACCEPTED_SHA,parentPoseRGBAHash=PARENT_HASH,
        parentCompositionVersion='review-art-v5',sourceCrop=list(BOX),guideCanvas=[660,660],
        guideCropOrigin=[0,0],role='continuous green sleeves in the existing held gesture',
        inputRoles=['edit-target: current geometry and hand/cuff placement',
                    'style-reference: original cloth palette and shading, not pose'],
        faceIncluded=False,faceGeometryChangeAllowed=False,handChangeAllowed=False,
        outlineChangeAllowed=False,adopted=False,installed=False)
    (OUT/'guide.json').write_text(json.dumps(metadata,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(metadata,indent=2))

if __name__=='__main__':main()
