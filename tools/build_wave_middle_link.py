"""One bounded middle cel; reuse the accepted peak/rest without rerendering."""
import hashlib
import json

import numpy as np
from PIL import Image

from canonical import ROOT,ACCEPTED_SHA,load_canonical
from arm_material import project_fixed_crop,localized_arm_pose
from review_wave import native_frame
from animation_output import write_animation
from guide_wave_middle_link import OUT,BOX

SHA='2E5DFACB79D7649034D46FE368D87411DEFD9CA5423C99BF484BAF9ABE05A0B8'
POLYGON=[(399,574),(444,576),(482,578),(492,598),(505,623),(516,628),
    (513,651),(499,693),(477,734),(449,776),(416,809),(386,832),
    (373,834),(359,814),(347,781),(339,748),(338,725),(322,723),
    (306,718),(295,712),(294,703),(309,692),(317,687),(301,684),
    (292,679),(292,670),(300,665),(321,668),(314,662),(302,658),
    (299,651),(306,646),(317,647),(339,657),(339,647),(338,642),
    (343,637),(349,638),(360,625),(376,605)]


def main():
    mother=load_canonical()
    if hashlib.sha256((OUT/'generated.png').read_bytes()).hexdigest().upper()!=SHA:
        raise ValueError('Middle cel input changed')
    with Image.open(OUT/'generated.png') as image:
        mapped=project_fixed_crop(mother,image.convert('RGBA'),[1024,1536],BOX)
    pose,allowed=localized_arm_pose(mother,mapped,
        dict(foregroundPolygon=POLYGON,edgeFeatherSourcePx=1.5))
    pose.save(OUT/'pose.png')
    frame=native_frame(pose)
    current_root=ROOT/'candidates/phase5/waving'
    current=json.loads((current_root/'build.json').read_text(encoding='utf-8'))
    old=[]
    for i,digest in enumerate(current['frameHashes']):
        with Image.open(current_root/f'frame-{i}.png') as image:
            cell=image.convert('RGBA')
        if hashlib.sha256(cell.tobytes()).hexdigest().upper()!=digest:
            raise ValueError('Current wave frame differs from its actual contract')
        old.append(cell)
    frames=[frame,old[1],frame,old[3]]
    # Native filtering can change only the bounded arm/backing support.
    guard=np.ones((208,192),bool);guard[86:176,35:87]=False
    if np.any(np.asarray(frame)[guard]!=np.asarray(old[0])[guard]):
        raise ValueError('Intermediate cel changed face/body/shoes or outside arm support')
    write_animation(OUT,frames,current['durationsMs'])
    hashes=[hashlib.sha256(f.tobytes()).hexdigest().upper() for f in frames]
    metadata=dict(sourceSha256=ACCEPTED_SHA,state='waving',previewVariant='waving_link',
        nativeRow=3,camera=current['camera'],durationsMs=current['durationsMs'],
        repeatBeforeIdle=3,totalDurationMs=700,actionDurationMs=2100,
        frameHashes=hashes,baselineFrameHashes=current['frameHashes'],
        unchangedHoldIndices=[1,3],returnedMiddleCelReused=True,
        sourceCrop=list(BOX),generatedSha256=SHA,rawCanvas=[1024,1536],
        foregroundPolygon=POLYGON,foregroundBoundaryEstimated=True,
        sourceChangePermissionPixels=int(allowed.sum()),
        nativeChangedPixels=[int(np.any(np.asarray(a)!=np.asarray(b),axis=2).sum()) for a,b in zip(old,frames)],
        facialGeometryRepair=False,nativeInterpolation=False,adopted=False,activeAtlasChanged=False,
        visualMotionApproval='pending',installableFullAtlas=False,installed=False,
        method='one face-free authored intermediate arm; same bounded hidden backing/cape/frontlock; exact accepted peak and rest reused',
        limitations=['Anatomy and cloth continuity require actual visual judgement; no clean artist layers or mathematically exact midpoint claimed.',
            'Only holds 0/2 change; entry/exit hard cuts and the fixed 700ms three-cycle schedule remain.',
            'This candidate has not replaced the accepted current wave, global atlas or installed pet.'])
    (OUT/'build.json').write_text(json.dumps(metadata,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(frameHashes=hashes,nativeChangedPixels=metadata['nativeChangedPixels'],adopted=False)))


if __name__=='__main__':main()
