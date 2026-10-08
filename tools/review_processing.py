"""Inspect one missing processing hand; preserve all non-arm source pixels."""
import hashlib
import json

import numpy as np
from PIL import Image

from canonical import ROOT,ACCEPTED_SHA,load_canonical,clean_cutout,camera
from arm_material import localized_arm_pose,project_fixed_crop
from review_waiting import comparison,grid
from review_wave import native_frame

OUT=ROOT/'candidates/phase5/processing-art-v1'
GENERATED_SHA='6BEEFEBA2456425C2B3648AEED8B3668F46A768D489A7A41D4F6016BD36FCDB3'


def inputs():
    spec=json.loads((OUT/'patch.json').read_text(encoding='utf-8'))
    if (spec['sourceSha256']!=ACCEPTED_SHA or spec['generatedSha256']!=GENERATED_SHA
            or spec['canvas']!=[1205,1306] or spec['rawCanvas']!=[971,1619]
            or spec['sourceCrop']!=[250,500,550,1000] or spec['editBudget']!=[295,570,525,885]
            or spec['fullRedrawAccepted'] or spec['newFaceGeometryAllowed']
            or spec['installableFullAtlas'] or spec['installed']):
        raise ValueError('Processing artwork violates locked source/crop/candidate boundary')
    points=np.asarray(spec['foregroundPolygon'])
    x0,y0,x1,y1=spec['editBudget']
    if (points.ndim!=2 or points.shape[1]!=2 or len(points)<3 or not np.isfinite(points).all()
            or np.any(points[:,0]<x0) or np.any(points[:,0]>x1)
            or np.any(points[:,1]<y0) or np.any(points[:,1]>y1)):
        raise ValueError('Processing forearm exceeds its explicit edit budget')
    path=OUT/'generated.png'
    if hashlib.sha256(path.read_bytes()).hexdigest().upper()!=GENERATED_SHA:
        raise ValueError('Processing generated input changed')
    with Image.open(path) as image:
        raw=image.convert('RGBA')
    mother=load_canonical()
    return mother,spec,project_fixed_crop(mother,raw,spec['rawCanvas'],spec['sourceCrop'])


def main():
    mother,spec,raw=inputs()
    pose,allowed=localized_arm_pose(mother,raw,spec)
    pose.save(OUT/'pose.png')
    Image.fromarray(allowed.astype(np.uint8)*255).save(OUT/'allowed-mask.png')
    frame=native_frame(pose)
    frame.save(OUT/'frame.png')
    frames=[native_frame(mother),native_frame(raw),frame]
    for width in (80,113,192,224):
        comparison(frames,width,'bounded thinking hand').save(OUT/f'contact-{width}px.png')
    diagnostic=ROOT/'work/processing-inspection'
    diagnostic.mkdir(parents=True,exist_ok=True)
    for name,image in [('source',mother),('raw',raw),('bounded',pose)]:
        grid(image,(225,500,550,1010)).save(diagnostic/f'{name}-grid.png')
    changed=np.any(np.asarray(mother)!=np.asarray(pose),axis=2)
    metadata=dict(sourceSha256=ACCEPTED_SHA,generatedSha256=GENERATED_SHA,role=spec['role'],
        boundedChangedPixels=int(changed.sum()),boundedChangedPixelsOutsidePatch=int((changed&~allowed).sum()),
        rawMappedCropChangedPixelsOutsidePatch=int((np.any(np.asarray(mother)!=np.asarray(raw),axis=2)&~allowed).sum()),
        poseRGBAHash=hashlib.sha256(pose.tobytes()).hexdigest().upper(),
        frameRGBAHash=hashlib.sha256(frame.tobytes()).hexdigest().upper(),
        rawCanvas=spec['rawCanvas'],sourceCrop=spec['sourceCrop'],cropProjection=spec['cropProjection'],
        camera=camera(clean_cutout(mother)[0]),sameSourceCoordinateCamera=True,
        sourceCapeAndForegroundLockPreserved=True,fullRedrawAccepted=False,facialGeometryRepair=False,
        articulatedArmBuilt=False,animationBuilt=False,visualAcceptance='pending',
        placementLimitation=spec['placementLimitation'],installableFullAtlas=False,installed=False)
    (OUT/'build.json').write_text(json.dumps(metadata,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(metadata,indent=2))


if __name__=='__main__':
    main()
