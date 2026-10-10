"""Accepted original-eye flow; legacy rigid layers remain explicit archive inputs."""
import hashlib
import json
import shutil
from functools import lru_cache

from PIL import Image, ImageDraw

import build_gaze as gaze
import gaze_surface as surface
from canonical import ROOT, ACCEPTED_SHA, load_canonical

DECISION='sources/canonical/gaze-surface-adoption-20261010.json'
SCOPE='gaze-surface-development-basis-only'
METHOD=surface.METHOD


@lru_cache(maxsize=1)
def approved():
    decision=json.loads((ROOT/DECISION).read_text(encoding='utf-8'))
    folder=ROOT/'candidates/phase5/look-surface-v1'
    digest=lambda path:hashlib.sha256(path.read_bytes()).hexdigest().upper()
    # Only text line endings are normalized for Git's Windows/Linux checkout;
    # the approved lossless image bytes and every decoded RGBA hash stay exact.
    metadata_digest=hashlib.sha256((folder/'build.json').read_text(encoding='utf-8').encode('utf-8')).hexdigest().upper()
    if (decision['sourceSha256']!=ACCEPTED_SHA or decision['scope']!=SCOPE
            or decision['candidatePixelsApprovedAsDevelopmentBasis'] is not True
            or decision['irisTextureShapeWarpAccepted'] is not True
            or decision['maximumDisplacementSourcePx']!=[6,4]
            or decision['actionFocusPolicy']!='preserve direction and relative focus with axis ratios 6/12 and 4/7'
            or any(decision[key] for key in ('fullMotionApproved','fullEyeQualityApproved',
                'faceOutlineChangeApproved','hostChangeApproved','installationApproved'))
            or metadata_digest!=decision['approvedCandidateBuildLfSha256']
            or digest(folder/'strip.webp')!=decision['approvedLookStripEncodedSha256']):
        raise ValueError('Eye adoption must retain the exact approved candidate and narrow scope')
    return json.loads((folder/'build.json').read_text(encoding='utf-8'))


def layers(source,*,corrected=True):
    spec=gaze.specification(corrected=corrected)
    if not corrected:
        return gaze.layers(source,gaze.load_generated(),spec)
    approved()
    return surface.fields(spec)


def offsets(dx,dy,*,corrected=True):
    # Old motion files encode the intent against a 12x7 range; do not silently
    # report these inputs as the actual quieter source displacement.
    return [round(dx*.5,12),round(dy*4/7,12)] if corrected else [dx,dy]


def pose(source,eye_layers,dx,dy,*,corrected=True):
    actual=offsets(dx,dy,corrected=corrected)
    return surface.pose(source,eye_layers,*actual) if corrected else gaze.pose(source,eye_layers,*actual)


def descriptor():
    approved()
    return dict(sourceEyeRig='sources/canonical/gaze-surface-v1.json',sourceEyeGeometryRevision=METHOD,
        eyeMotionApprovalScope=SCOPE,eyeMotionUserDecision=DECISION,
        eyeMotionVisualApproval='approved-as-development-basis',irisShapeWarp=True,eyeOutlineFixed=True,
        newEyeArtworkGenerated=False,eyeBackingUsed=False,eyeBackingGeneratedSha256=None)


def adopt_look():
    metadata=dict(approved())
    folder=ROOT/'candidates/phase5/look-surface-v1'
    frames=[]
    with Image.open(folder/'strip.webp') as image:strip=image.convert('RGBA')
    with Image.open(folder/'neutral.png') as image:neutral=image.convert('RGBA')
    digest=lambda image:hashlib.sha256(image.tobytes()).hexdigest().upper()
    if strip.size!=(1536,416) or neutral.size!=(192,208) or digest(neutral)!=metadata['neutralFrameHash']:
        raise ValueError('Approved native gaze geometry changed')
    for index in range(16):
        with Image.open(folder/f'frame-{index}.png') as image:frame=image.convert('RGBA')
        x,y=index%8*192,index//8*208
        if digest(frame)!=metadata['frameHashes'][index] or frame.tobytes()!=strip.crop((x,y,x+192,y+208)).tobytes():
            raise ValueError('Approved gaze pixels changed; do not redraw an accepted candidate')
        frames.append(frame)
    out=gaze.OUT;out.mkdir(parents=True,exist_ok=True)
    for name in ['strip.webp','neutral.png',*[f'frame-{i}.png' for i in range(16)]]:
        shutil.copyfile(folder/name,out/name)
    for width in (80,113,192,224):gaze.contact(frames,width).save(out/f'contact-{width}px.png')
    # Presentation only: source eye chart derived from the same accepted flow.
    mother=load_canonical();fields=layers(mother)
    board=Image.new('RGB',(4*385,4*175),'#ededed');draw=ImageDraw.Draw(board)
    for index,offset in enumerate(metadata['sourceOffsetsPx']):
        x,y=index%4*385,index//4*175
        board.paste(surface.pose(mother,fields,*offset).crop(surface.FACE).convert('RGB'),(x,y))
        draw.text((x+3,y+3),str(index),fill='#344860')
    board.save(out/'eyes-contact.png')
    metadata.update(state='look',adopted=True,activeAtlasChanged=True,originalSourceModified=False,
        directionZero='up',clockwiseStepDegrees=22.5,sourceOffsetDecimalPlaces=12,
        eyeMotionApprovalScope=SCOPE,eyeMotionUserDecision=DECISION,
        eyeMotionVisualApproval='approved-as-development-basis',eyeBackingUsed=False,
        approvalDoesNotIncludeFullEyeQuality=True,approvalDoesNotIncludeFullMotion=True)
    (out/'build.json').write_text(json.dumps(metadata,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(directionCount=16,approvedCandidatePixelsCopiedExactly=True,
        adoptionScope=SCOPE,fullMotionApproved=False,installed=False)))
