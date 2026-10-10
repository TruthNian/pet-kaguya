"""Developer-selected continuity improvement; no fabricated user/art acceptance."""
import hashlib
import json

import numpy as np
from PIL import Image

from canonical import ROOT, ACCEPTED_SHA

SOURCE='candidates/phase5/wave-middle-link-v1'
FRAME='1ADE339D8E003656323BC65FCECCE5B9E6591BF1B53486DBD4A82C4322E4D043'
GENERATED='2E5DFACB79D7649034D46FE368D87411DEFD9CA5423C99BF484BAF9ABE05A0B8'
REFERENCE='sources/reference/waving-middle-before'


def apply(poses,frames,camera):
    folder=ROOT/SOURCE
    metadata=json.loads((folder/'build.json').read_text(encoding='utf-8'))
    digest=lambda image:hashlib.sha256(image.tobytes()).hexdigest().upper()
    if (metadata['sourceSha256']!=ACCEPTED_SHA or metadata['camera']!=camera
            or metadata['frameHashes'][0]!=FRAME or metadata['frameHashes'][2]!=FRAME
            or metadata['baselineFrameHashes']!=[digest(frame) for frame in frames]
            or hashlib.sha256((folder/'generated.png').read_bytes()).hexdigest().upper()!=GENERATED
            or metadata['durationsMs']!=[140,140,140,280] or metadata['visualMotionApproval']!='pending'):
        raise ValueError('Middle source, unchanged accepted peak/rest or frozen baseline changed')
    with Image.open(folder/'frame-0.png') as image:middle=image.convert('RGBA')
    if middle.size!=(192,208) or digest(middle)!=FRAME:
        raise ValueError('Use the selected actual middle cel, not an untracked redraw')
    allowed=np.zeros((208,192),bool);allowed[86:176,35:87]=True
    if np.any(np.any(np.asarray(middle)!=np.asarray(frames[0]),axis=2)&~allowed):
        raise ValueError('Middle cel changed the face, other body or shoes')
    with Image.open(folder/'pose.png') as image:poses['middle']=image.convert('RGBA')
    result=[middle,frames[1],middle,frames[3]]
    return result


def descriptor():
    return dict(middleDevelopmentBasis='developer-selected-continuity-improvement',
        middleSource=SOURCE,middleGeneratedSha256=GENERATED,middleNativeRGBAHash=FRAME,
        middleVisualApproval='pending',middleUserApprovalClaimed=False,
        middleReference=REFERENCE,unchangedAcceptedAmplitudeHoldIndices=[1,3],
        newMiddleArtworkGeneratedThisIteration=False,middleUsesAuthoredHandNotOriginalPalmPixels=True)
