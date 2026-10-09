"""Inspect, never adopt, an edit that did not establish better hand anatomy."""
import hashlib
import json
import numpy as np
from PIL import Image,ImageDraw
from canonical import ROOT,ACCEPTED_SHA,load_canonical
from guide_review_hands_pair import OUT,BOX,SIDE,PARENT_HASH,parent
from review_wave import native_frame
from review_review_v2 import comparison

GENERATED_SHA='9BDE1968DDDA322D2BA487E2637AB79AC0A963A6A01742549D7C33378910CD01'
RAW_SIZE=(1254,1254)


def inputs():
    before=parent();path=OUT/'generated.png'
    if hashlib.sha256(path.read_bytes()).hexdigest().upper()!=GENERATED_SHA:
        raise ValueError('Cannot replace the failed study with a different generated edit')
    with Image.open(path) as image:raw=image.convert('RGBA')
    if raw.size!=RAW_SIZE:raise ValueError('Measured square canvas changed')
    square=raw.convert('RGBa').resize((SIDE,SIDE),Image.Resampling.LANCZOS).convert('RGBA')
    mapped=before.copy();mapped.paste(square.crop((0,0,275,220)),BOX[:2])
    return before,mapped


def main():
    before,mapped=inputs();mother=load_canonical()
    mapped.save(OUT/'raw-mapped-NOT-adopted.png')
    frames=[native_frame(mother),native_frame(before),native_frame(mapped)]
    for width in (80,113,192,224):
        comparison(frames,width,['mother v3','current v6','raw edit NOT adopted']).save(OUT/f'contact-{width}px.png')
    detail=Image.new('RGB',(825,245),'#23252b');draw=ImageDraw.Draw(detail)
    for index,(image,label) in enumerate(((mother,'actual mother costume'),(before,'current v6'),(mapped,'raw edit NOT adopted'))):
        tile=Image.new('RGBA',(275,220),'#ededed');tile.alpha_composite(image.crop(BOX))
        detail.paste(tile.convert('RGB'),(275*index,25));draw.text((275*index+3,7),label,fill='white')
    detail.save(OUT/'detail.png')
    a,b=np.asarray(before),np.asarray(mapped);different=np.any(a!=b,axis=2)
    meta=dict(sourceSha256=ACCEPTED_SHA,parentPoseRGBAHash=PARENT_HASH,generatedSha256=GENERATED_SHA,
        rawCanvas=list(RAW_SIZE),sourceCrop=list(BOX),fixedSquareProjection=True,objectBoundsFit=False,
        changedSourcePixels=int(different.sum()),faceIncluded=False,facialGeometryRepair=False,
        anatomyImprovementProven=False,originalMoonMotifRemovalAllowed=False,
        withdrawnPromptInstruction='Clean up the ambiguous disconnected cream strip just above the lower hand so it no longer resembles a spare wrist/cuff attached to the belt.',
        correctedSourceFact='The light fragment is the original waist crescent partially occluded by the hand, not an extra cuff. Preserve it.',
        noThumbVisibilityDoesNotProveExtraOrMissingFinger=True,
        adopted=False,activeAtlasChanged=False,installed=False,animationBuilt=False,visualAcceptance='pending',
        rejection='Redrawn line/shading alone does not establish a coherent improved pair. No active artwork or cels were substituted. '
            'The target diagnosis also mistakenly treated an occluded original costume motif as a detached cuff; that instruction is withdrawn.',
        remaining='Hand silhouette, volume, wrist/cuff integration and the desired low-hand contact arrangement remain unapproved.')
    (OUT/'build.json').write_text(json.dumps(meta,indent=2)+'\n',encoding='utf-8');print(json.dumps(meta,indent=2))


if __name__=='__main__':main()
