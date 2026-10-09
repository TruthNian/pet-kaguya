"""Compact existing hand pixels over an existing pre-hand body plate."""
import hashlib
import json
import math

import numpy as np
from PIL import Image,ImageDraw,ImageFilter

from canonical import ROOT,ACCEPTED_SHA,load_canonical
from guide_review import base_pose
from review_wave import native_frame
from review_review_v2 import comparison
from guide_review_hand import OUT

PARENT_HASH = '29B889E8F9EC0BADF3762B1D9EE0C78F4CA752E95A9071F8AD77119562F748C5'
HAND = [[512,682],[531,675],[552,678],[573,688],[591,700],[597,711],
        [603,724],[590,728],[575,730],[559,727],[549,727],[542,723],
        [534,728],[526,726],[521,720],[516,720],[510,713],[510,707],
        [505,709],[501,705],[500,700],[498,696],[501,689]]
PERMISSION = [[511,677],[531,670],[556,673],[579,685],[596,698],[602,712],
              [608,728],[590,735],[557,732],[543,733],[531,735],[520,730],
              [511,724],[505,716],[502,714],[494,704],[494,693],[501,682]]
ANCHOR = np.array([603.0,721.0])


def inputs():
    load_canonical()
    with Image.open(ROOT/'candidates/phase5/review-art-v3/pose.png') as image:
        parent = image.convert('RGBA')
    if hashlib.sha256(parent.tobytes()).hexdigest().upper()!=PARENT_HASH:
        raise ValueError('Hand study needs unchanged locked-v3 composition')
    return parent,base_pose()


def polygon_mask(size,points):
    mask = Image.new('L',size)
    ImageDraw.Draw(mask).polygon(points,fill=255)
    return mask


def compact(parent,background,long_scale=.85,cross_scale=1.08):
    if hashlib.sha256(parent.tobytes()).hexdigest().upper()!=PARENT_HASH or background.size!=parent.size:
        raise ValueError('Hand study cannot substitute the recorded parent/camera')
    if not (math.isfinite(long_scale) and math.isfinite(cross_scale)
            and .8<=long_scale<=1 and 1<=cross_scale<=1.12):
        raise ValueError('Hand compactness exceeds the local study range')
    hard = polygon_mask(parent.size,HAND)
    # This is an estimated silhouette, not a recovered author matte. The
    # neutral reconstruction is measured separately and can fail visibly.
    matte = np.asarray(hard.filter(ImageFilter.GaussianBlur(.65)),dtype=float)/255
    a,b = np.asarray(parent),np.asarray(background)
    layer = a.copy()
    layer[...,3] = np.rint(a[...,3]*matte).astype(np.uint8)
    source_layer = Image.fromarray(layer)
    direction = np.array([-.98,-.2]); direction/=np.linalg.norm(direction)
    basis = np.array([[direction[0],-direction[1]],[direction[1],direction[0]]])
    matrix = basis@np.diag([long_scale,cross_scale])@basis.T
    inverse = np.linalg.inv(matrix)
    offset = ANCHOR-inverse@ANCHOR
    coefficients = (*inverse[0],offset[0],*inverse[1],offset[1])
    moved = source_layer.convert('RGBa').transform(parent.size,Image.Transform.AFFINE,
        coefficients,Image.Resampling.BICUBIC).convert('RGBA')
    old_domain = np.asarray(hard)>0
    allowed = np.asarray(polygon_mask(parent.size,PERMISSION))>0
    moved_alpha = np.asarray(moved)[...,3]>8
    if np.any(moved_alpha&~allowed):
        raise ValueError('Moved hand exceeds the explicit local repair permission')
    cleared = a.copy()
    cleared[old_domain&allowed] = b[old_domain&allowed]
    result = Image.fromarray(cleared)
    result.alpha_composite(moved)
    pixels = np.asarray(result).copy()
    pixels[~allowed] = a[~allowed]
    pixels[...,3] = a[...,3]
    return Image.fromarray(pixels),allowed,matte,matrix,moved


def main():
    parent,background = inputs()
    pose,allowed,matte,matrix,moved = compact(parent,background)
    neutral,_,_,_,_ = compact(parent,background,1.0,1.0)
    for name,image in [('pose',pose),('neutral',neutral),('moved-hand',moved)]:
        image.save(OUT/f'{name}.png')
    Image.fromarray(allowed.astype(np.uint8)*255).save(OUT/'allowed-mask.png')
    Image.fromarray(np.rint(matte*255).astype(np.uint8)).save(OUT/'estimated-matte.png')
    frames = [native_frame(parent),native_frame(neutral),native_frame(pose)]
    frames[-1].save(OUT/'frame.png')
    for width in (80,113,192,224):
        comparison(frames,width,['current v3','neutral estimate','compact hand']).save(OUT/f'contact-{width}px.png')
    detail = Image.new('RGB',(900,480),'#23252b')
    draw = ImageDraw.Draw(detail)
    for i,(image,label) in enumerate(zip([parent,neutral,pose],['current','neutral estimate','compact hand'])):
        tile = Image.new('RGBA',(300,450),'#23252b')
        tile.alpha_composite(image.crop((470,635,620,860)).resize((300,450),Image.Resampling.NEAREST))
        detail.paste(tile.convert('RGB'),(300*i,30));draw.text((300*i+5,7),label,fill='white')
    detail.save(OUT/'detail.png')
    a,b,n = np.asarray(parent),np.asarray(pose),np.asarray(neutral)
    changed = np.any(a!=b,axis=2)
    meta = dict(sourceSha256=ACCEPTED_SHA,parentPoseRGBAHash=PARENT_HASH,parentCompositionVersion='review-art-v3',
        method='same existing hand pixels, anisotropic local affine about a fixed wrist, existing pre-hand body plate',
        handPolygon=HAND,permissionPolygon=PERMISSION,wristSourcePx=ANCHOR.tolist(),
        longAxisScale=.85,crossAxisScale=1.08,affineMatrix=matrix.tolist(),
        sourceMatteEstimated=True,neutralChangedPixels=int(np.any(a!=n,axis=2).sum()),
        neutralMaximumRGBAError=int(np.abs(a.astype(int)-n.astype(int)).max()),
        changedPixels=int(changed.sum()),changedPixelsOutsidePermission=int((changed&~allowed).sum()),
        poseRGBAHash=hashlib.sha256(pose.tobytes()).hexdigest().upper(),parentAlphaPreserved=True,
        newArtworkGenerated=False,facialGeometryRepair=False,fullRedrawAccepted=False,articulatedArmBuilt=False,
        visualAcceptance='pending',strategyUserApproval='pending',adopted=False,activeAtlasChanged=False,
        animationBuilt=False,installableFullAtlas=False,installed=False,
        limitation='A 2-D hand proportion study, not a new anatomical view or clean matte. Existing body plate is restored only under the removed hand. Neutral reconstruction, crease continuity and visual volume must be inspected.')
    (OUT/'build.json').write_text(json.dumps(meta,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(meta,indent=2))


if __name__ == '__main__':
    main()
