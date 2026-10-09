"""Independent source-protected surface study, not automatic art promotion."""
import hashlib
import json

import numpy as np
from PIL import Image,ImageDraw

from canonical import ROOT,ACCEPTED_SHA,load_canonical,bounded_artwork
from arm_material import project_fixed_crop
from review_wave import native_frame
from review_review_v2 import comparison,specification as right_spec
from review_arm_backing import specification as left_spec
from guide_review_structure import BOX,OUT

PARENT_HASH = '29B889E8F9EC0BADF3762B1D9EE0C78F4CA752E95A9071F8AD77119562F748C5'
GENERATED_SHA = '87FA2A01EA75F082F81E1D0BDC9C932DAB1C710A2F5E3F925016B8008BD4ACDF'


def specification():
    spec = json.loads((OUT/'patch.json').read_text(encoding='utf-8'))
    if (spec['sourceSha256'] != ACCEPTED_SHA or spec['parentPoseRGBAHash'] != PARENT_HASH
            or spec['parentCompositionVersion'] != 'review-art-v3' or spec['generatedSha256'] != GENERATED_SHA
            or spec['canvas'] != [1205,1306] or spec['rawCanvas'] != [1387,1134]
            or spec['sourceCrop'] != list(BOX) or spec['editBudget'] != [321,625,840,875]
            or spec['edgeFeatherSourcePx'] != 2.0 or spec['visualAcceptance'] != 'pending'
            or spec['strategyUserApproval'] != 'pending'
            or any(spec[key] is not False for key in ('currentOuterSleeveOutlineChanged','backgroundHairChanged',
                'sourceAccessoriesChanged','newFaceGeometryAllowed','fullRedrawAccepted','cleanLayerRecoveryClaimed',
                'articulatedArmBuilt','animationBuilt','adopted','installableFullAtlas','installed'))):
        raise ValueError('Structure study violates locked source, parent or unapproved scope')
    x0,y0,x1,y1 = spec['editBudget']
    for key in ('handPolygons','sleeveSurfacePolygons'):
        for points in spec[key]:
            p = np.asarray(points)
            if (p.ndim!=2 or p.shape[1]!=2 or len(p)<3 or not np.isfinite(p).all()
                    or np.any(p[:,0]<x0) or np.any(p[:,0]>x1)
                    or np.any(p[:,1]<y0) or np.any(p[:,1]>y1)):
                raise ValueError('Hand/sleeve surface exceeds inspected budget')
    return spec


def inputs():
    load_canonical()
    spec = specification()
    with Image.open(ROOT/'candidates/phase5/review-art-v3/pose.png') as image:
        parent = image.convert('RGBA')
    if hashlib.sha256(parent.tobytes()).hexdigest().upper()!=PARENT_HASH:
        raise ValueError('Structure study needs the unchanged current parent')
    path = OUT/'generated.png'
    if hashlib.sha256(path.read_bytes()).hexdigest().upper()!=GENERATED_SHA:
        raise ValueError('Generated structure study bytes changed')
    with Image.open(path) as image:
        raw = image.convert('RGBA')
    return parent,spec,project_fixed_crop(parent,raw,spec['rawCanvas'],spec['sourceCrop'])


def localized_pose(parent,spec,mapped):
    if spec!=specification() or hashlib.sha256(parent.tobytes()).hexdigest().upper()!=PARENT_HASH:
        raise ValueError('Structure study cannot substitute source or permission')
    proposed,allowed,_ = bounded_artwork(parent,mapped,
        spec['handPolygons']+spec['sleeveSurfacePolygons'],spec['edgeFeatherSourcePx'])
    protected = Image.new('L',parent.size)
    draw = ImageDraw.Draw(protected)
    # Retain original cape/front-lock, belt/butterfly, bow/tassel pixel plates.
    # Exclude the old left-hand protection because this study edits that hand.
    for points in left_spec()['preservedForegroundPolygons']+right_spec()['preservedForegroundPolygons'][:4]:
        draw.polygon(points,fill=255)
    draw.rectangle((510,568,712,664),fill=255)
    protection = np.asarray(protected)>0
    a,b = np.asarray(parent),np.asarray(proposed).copy()
    b[protection] = a[protection]
    # This study only changes already painted surfaces, not transparency or
    # the character's silhouette. Keep the parent's complete alpha plane.
    b[...,3] = a[...,3]
    allowed &= ~protection
    changed = np.any(a!=b,axis=2)
    if np.any(changed&~allowed):
        raise ValueError('Structure study changed protected/exterior pixels')
    return Image.fromarray(b),allowed,protection


def main():
    parent,spec,mapped = inputs()
    bounded,allowed,protected = localized_pose(parent,spec,mapped)
    bounded.save(OUT/'pose.png')
    Image.fromarray(allowed.astype(np.uint8)*255).save(OUT/'allowed-mask.png')
    Image.fromarray(protected.astype(np.uint8)*255).save(OUT/'protected-mask.png')
    frames = [native_frame(load_canonical()),native_frame(parent),native_frame(bounded)]
    frames[-1].save(OUT/'frame.png')
    for width in (80,113,192,224):
        comparison(frames,width,
            ['mother v3','current v3','surface study']).save(OUT/f'contact-{width}px.png')
    detail = Image.new('RGB',(990,225),'#23252b')
    draw = ImageDraw.Draw(detail)
    for i,(pose,label) in enumerate(zip([parent,mapped,bounded],['current','raw redraw NOT adopted','bounded surface study'])):
        tile = Image.new('RGBA',(660,390),'#23252b')
        tile.alpha_composite(pose.crop((300,555,960,945)))
        detail.paste(tile.resize((330,195),Image.Resampling.NEAREST).convert('RGB'),(330*i,30))
        draw.text((330*i+4,7),label,fill='white')
    detail.save(OUT/'detail.png')
    a,b,r = np.asarray(parent),np.asarray(bounded),np.asarray(mapped)
    meta = dict(sourceSha256=ACCEPTED_SHA,parentCompositionVersion='review-art-v3',parentPoseRGBAHash=PARENT_HASH,
        generatedSha256=GENERATED_SHA,sourceCrop=list(BOX),rawCanvas=spec['rawCanvas'],role=spec['role'],
        newArtworkGenerated=True,changedPixels=int(np.any(a!=b,axis=2).sum()),
        changedPixelsOutsidePermission=int((np.any(a!=b,axis=2)&~allowed).sum()),
        rawMappedChangedPixelsOutsidePermission=int((np.any(a!=r,axis=2)&~allowed).sum()),
        poseRGBAHash=hashlib.sha256(bounded.tobytes()).hexdigest().upper(),
        frameRGBAHash=hashlib.sha256(frames[-1].tobytes()).hexdigest().upper(),
        parentAlphaPreserved=bool(np.array_equal(a[...,3],b[...,3])),
        protectedForegroundRGBAExact=bool(np.array_equal(a[protected],b[protected])),
        fullRedrawAccepted=False,cleanLayerRecoveryClaimed=False,facialGeometryRepair=False,
        animationBuilt=False,articulatedArmBuilt=False,visualAcceptance='pending',strategyUserApproval='pending',
        adopted=False,activeAtlasChanged=False,installableFullAtlas=False,installed=False,
        limitation='Sparse source-space repair envelopes, not clean semantic mattes. Raw crop redraw is not adopted. Rounded cloth shading alone does not establish hand scale, arm volume, seam or motion acceptance.')
    (OUT/'build.json').write_text(json.dumps(meta,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(meta,indent=2))


if __name__ == '__main__':
    main()
