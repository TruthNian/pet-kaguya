"""Bounded two-low-hands review pose; foreground plates are not clean mattes."""
import hashlib
import json

import numpy as np
from PIL import Image,ImageDraw

from canonical import ROOT,ACCEPTED_SHA,load_canonical,bounded_artwork,clean_cutout,camera
from arm_material import project_fixed_crop
from guide_review import base_pose,BOX
from review_processing import GENERATED_SHA as LEFT_SHA
from review_waiting import comparison,grid
from review_wave import native_frame

OUT = ROOT/'candidates/phase5/review-art-v1'
GENERATED_SHA = '0E6AD86D64E5FB6B6E85B50953E2C4E717506F4340B8ECA2EC8E7A77FA151452'


def validate_specification(spec):
    if (spec['sourceSha256']!=ACCEPTED_SHA or spec['generatedSha256']!=GENERATED_SHA
            or spec['leftArmGeneratedSha256']!=LEFT_SHA or spec['canvas']!=[1205,1306]
            or spec['rawCanvas']!=[1266,1242] or spec['sourceCrop']!=list(BOX)
            or spec['editBudget']!=[498,570,940,1000] or spec['fullRedrawAccepted']
            or spec['newFaceGeometryAllowed'] or spec['articulatedArmBuilt']
            or spec['installableFullAtlas'] or spec['installed']
            or spec['visualAcceptance']!='pending' or spec['strategyUserApproval']!='pending'):
        raise ValueError('Review artwork violates locked source/crop/unapproved candidate boundary')
    for name in ('oldRightArmPolygon','foregroundRightArmPolygon'):
        points = np.asarray(spec[name])
        x0,y0,x1,y1 = spec['editBudget']
        if (points.ndim!=2 or points.shape[1]!=2 or len(points)<3 or not np.isfinite(points).all()
                or np.any(points[:,0]<x0) or np.any(points[:,0]>x1)
                or np.any(points[:,1]<y0) or np.any(points[:,1]>y1)):
            raise ValueError('Review right-arm permission exceeds its explicit source budget')


def inputs():
    spec = json.loads((OUT/'patch.json').read_text(encoding='utf-8'))
    validate_specification(spec)
    path = OUT/'generated.png'
    if hashlib.sha256(path.read_bytes()).hexdigest().upper()!=GENERATED_SHA:
        raise ValueError('Review generated input changed')
    with Image.open(path) as image:
        raw = image.convert('RGBA')
    base = base_pose()
    return base,spec,project_fixed_crop(base,raw,spec['rawCanvas'],spec['sourceCrop'])


def localized_pose(base,generated,spec):
    validate_specification(spec)
    image,allowed,_ = bounded_artwork(base,generated,
        [spec['oldRightArmPolygon'],spec['foregroundRightArmPolygon']],spec['edgeFeatherSourcePx'])
    foreground = Image.new('L',base.size)
    for polygon in spec['preservedForegroundPolygons']:
        ImageDraw.Draw(foreground).polygon(polygon,fill=255)
    preserved = np.asarray(foreground)>0
    original,pixels = np.asarray(base),np.asarray(image).copy()
    pixels[preserved] = original[preserved]
    allowed &= ~preserved
    changed = np.any(pixels!=original,axis=2)
    if np.any(changed&~allowed):
        raise ValueError('Review repainted outside the right arm/hidden background region')
    for x0,y0,x1,y1 in [(455,250,775,465),(433,1015,611,1226),(616,1015,795,1226)]:
        if np.any(allowed[y0:y1,x0:x1]) or np.any(changed[y0:y1,x0:x1]):
            raise ValueError('Review permission touched a protected face/shoe')
    return Image.fromarray(pixels),allowed,preserved


def main():
    base,spec,raw = inputs()
    pose,allowed,preserved = localized_pose(base,raw,spec)
    pose.save(OUT/'pose.png')
    Image.fromarray(allowed.astype(np.uint8)*255).save(OUT/'allowed-mask.png')
    Image.fromarray(preserved.astype(np.uint8)*255).save(OUT/'preserved-foreground-mask.png')
    frame = native_frame(pose)
    frame.save(OUT/'frame.png')
    comparison_frames = [native_frame(load_canonical()),native_frame(raw),frame]
    for width in (80,113,192,224):
        comparison(comparison_frames,width,'bounded two-hand candidate').save(OUT/f'contact-{width}px.png')
    diagnostic = ROOT/'work/review-inspection'
    diagnostic.mkdir(parents=True,exist_ok=True)
    grid(pose,(450,500,975,1005)).save(diagnostic/'bounded-grid.png')
    changed = np.any(np.asarray(base)!=np.asarray(pose),axis=2)
    metadata = dict(sourceSha256=ACCEPTED_SHA,generatedSha256=GENERATED_SHA,leftArmGeneratedSha256=LEFT_SHA,
        role=spec['role'],rawCanvas=spec['rawCanvas'],sourceCrop=spec['sourceCrop'],cropProjection=spec['cropProjection'],
        boundedRightArmChangedPixels=int(changed.sum()),boundedRightArmChangedPixelsOutsidePatch=int((changed&~allowed).sum()),
        rawMappedCropChangedPixelsOutsidePatch=int((np.any(np.asarray(base)!=np.asarray(raw),axis=2)&~allowed).sum()),
        originalHeadFaceRGBAExact=True,sourceForegroundPlatesPreserved=True,
        poseRGBAHash=hashlib.sha256(pose.tobytes()).hexdigest().upper(),frameRGBAHash=hashlib.sha256(frame.tobytes()).hexdigest().upper(),
        camera=camera(clean_cutout(load_canonical())[0]),sameSourceCoordinateCamera=True,
        fullRedrawAccepted=False,facialGeometryRepair=False,articulatedArmBuilt=False,animationBuilt=False,
        visualAcceptance='pending',strategyUserApproval='pending',placementLimitation=spec['placementLimitation'],
        installableFullAtlas=False,installed=False)
    (OUT/'build.json').write_text(json.dumps(metadata,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(metadata,indent=2))


if __name__ == '__main__':
    main()
