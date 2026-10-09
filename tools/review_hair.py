"""Unadopted hidden-hair experiments; never an active pose or atlas input."""
import hashlib
import json

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from canonical import ROOT, ACCEPTED_SHA, bounded_masks
from arm_material import project_fixed_crop
from review_review_v2 import inputs as parent_inputs, localized_pose as parent_pose, specification as parent_specification
from review_review_v2 import comparison
from review_wave import native_frame
from hair_boundary import harmonic_rgb

OUT = ROOT/'candidates/phase5/review-hair-v2'
GENERATED_SHA = '9C0C8C196D44BE6C3512AB3D11E7624E6D1D48835961E99CCE8B4268168B41CC'
PARENT_HASH = '8618A3A73301ED7A3B29D63983878159C7B35D39BA33E465186584C539E32570'


def validate(spec):
    if (spec['sourceSha256'] != ACCEPTED_SHA or spec['generatedSha256'] != GENERATED_SHA
            or spec['parentPoseRGBAHash'] != PARENT_HASH or spec['canvas'] != [1205,1306]
            or spec['sourceCrop'] != [680,540,1000,1020] or spec['rawCanvas'] != [1024,1536]
            or spec['editBudget'] != [776,575,958,1000]
            or spec['foregroundProtectionRadiusSourcePx'] != 6 or spec['edgeFeatherSourcePx'] != 2
            or spec['fullyPaintedAlphaMinimum'] != 240 or not spec['parentAlphaPreservedExactly']
            or not spec['permissionMustBeSubsetOfParentArmPatch'] or spec['fullCropRedrawAccepted']
            or spec['faceIncludedInInput'] or spec['handOrSleeveRepaintAccepted']
            or spec['activePreviewSelected'] is not False or spec['adopted'] is not False
            or spec['compositingMethods'] != ['bounded-feather','harmonic-rgb']
            or spec['harmonicRelativeTolerance'] != 1e-8 or spec['harmonicMaxIterations'] != 1600
            or spec['visualAcceptance'] != 'not-accepted' or spec['installableFullAtlas'] or spec['installed']):
        raise ValueError('Hidden hair repair violates its source/pose-only boundary')
    p = np.asarray(spec['hairPolygon'])
    x0,y0,x1,y1 = spec['editBudget']
    if (p.ndim != 2 or p.shape[1] != 2 or len(p) < 3 or not np.isfinite(p).all()
            or np.any(p[:,0] < x0) or np.any(p[:,0] > x1)
            or np.any(p[:,1] < y0) or np.any(p[:,1] > y1)):
        raise ValueError('Hidden hair permission exceeds its inspected budget')


def specification():
    spec = json.loads((OUT/'patch.json').read_text(encoding='utf-8'))
    validate(spec)
    return spec


def load_generated():
    path = OUT/'generated.png'
    if hashlib.sha256(path.read_bytes()).hexdigest().upper() != GENERATED_SHA:
        raise ValueError('Hidden hair generated input changed')
    with Image.open(path) as image:
        result = image.convert('RGBA')
    if result.size != (1024,1536):
        raise ValueError('Hidden hair raw framing changed')
    return result


def repair(pose,parent_spec,parent_allowed,preserved,spec=None,method='bounded-feather'):
    spec = specification() if spec is None else spec
    validate(spec)
    if spec != specification() or parent_spec != parent_specification():
        raise ValueError('Hidden hair permission differs from its recorded experiment')
    if method not in spec['compositingMethods']:
        raise ValueError('Unknown hidden-hair compositing experiment')
    if hashlib.sha256(pose.tobytes()).hexdigest().upper() != PARENT_HASH:
        raise ValueError('Hidden hair cannot reframe or change its parent pose')
    raw = load_generated()
    mapped = project_fixed_crop(pose,raw,spec['rawCanvas'],spec['sourceCrop'])
    foreground = Image.new('L',pose.size)
    draw = ImageDraw.Draw(foreground)
    draw.polygon(parent_spec['foregroundRightArmPolygon'],fill=255)
    for polygon in parent_spec['preservedForegroundPolygons']:
        draw.polygon(polygon,fill=255)
    protected = np.asarray(foreground.filter(ImageFilter.MaxFilter(13))) > 0
    original_foreground = Image.new('L',pose.size)
    for polygon in parent_spec['preservedForegroundPolygons']:
        ImageDraw.Draw(original_foreground).polygon(polygon,fill=255)
    expected_preserved = np.asarray(original_foreground)>0
    expected_allowed = bounded_masks(pose.size,
        [parent_spec['oldRightArmPolygon'],parent_spec['foregroundRightArmPolygon']],
        parent_spec['edgeFeatherSourcePx'])[0] & ~expected_preserved
    if (parent_allowed.dtype != np.bool_ or preserved.dtype != np.bool_
            or not np.array_equal(preserved,expected_preserved)
            or not np.array_equal(parent_allowed,expected_allowed)):
        raise ValueError('Hidden hair cannot enlarge the parent permission or remove foreground protection')
    domain = Image.new('L',pose.size)
    ImageDraw.Draw(domain).polygon(spec['hairPolygon'],fill=255)
    before,generated = np.asarray(pose),np.asarray(mapped)
    # Do not use an opaque output to fill a transparent gap or invent a new
    # outer outline. This interior RGB repair keeps every parent alpha byte.
    allowed = (np.asarray(domain)>0) & parent_allowed & ~protected & ~preserved
    allowed &= (before[...,3]>=240) & (generated[...,3]>=240)
    hard = Image.fromarray(allowed.astype(np.uint8)*255)
    interior = np.asarray(hard.filter(ImageFilter.MinFilter(3))) > 0
    diagnostics = {}
    if method == 'harmonic-rgb':
        result, diagnostics = harmonic_rgb(before,generated,interior,
            spec['harmonicRelativeTolerance'],spec['harmonicMaxIterations'])
    else:
        weight = np.asarray(hard.filter(ImageFilter.MinFilter(5)).filter(
            ImageFilter.GaussianBlur(spec['edgeFeatherSourcePx'])),dtype=float)/255
        weight *= interior
        result = before.copy()
        mixed = before[...,:3].astype(float)*(1-weight[...,None])+generated[...,:3]*weight[...,None]
        result[allowed,:3] = np.clip(np.rint(mixed[allowed]),0,255).astype(np.uint8)
    changed = np.any(result!=before,axis=2)
    if np.any(changed & (~allowed | protected | preserved)) or not np.array_equal(result[...,3],before[...,3]):
        raise ValueError('Hidden hair changed foreground, silhouette or outside pixels')
    return Image.fromarray(result),allowed,protected,mapped,diagnostics


def main():
    base,spec,raw = parent_inputs()
    pose,allowed,preserved = parent_pose(base,raw,spec)
    records,poses,frames = {},[pose],[native_frame(pose)]
    for method in ('bounded-feather','harmonic-rgb'):
        revised,permission,protected,mapped,solve = repair(pose,spec,allowed,preserved,method=method)
        revised.save(OUT/f'{method}-pose.png')
        frame = native_frame(revised)
        frame.save(OUT/f'{method}-frame.png')
        changed = np.any(np.asarray(pose)!=np.asarray(revised),axis=2)
        records[method] = dict(changedPixels=int(changed.sum()),outsidePermissionChangedPixels=int((changed & ~permission).sum()),
            protectedForegroundChangedPixels=int((changed & protected).sum()),
            poseRGBAHash=hashlib.sha256(revised.tobytes()).hexdigest().upper(),
            frameRGBAHash=hashlib.sha256(frame.tobytes()).hexdigest().upper(),
            parentAlphaPreservedExactly=np.array_equal(np.asarray(pose)[...,3],np.asarray(revised)[...,3]),
            adopted=False,activePreviewSelected=False)
        if solve:
            records[method]['solverConvergedBelowRelativeTolerance'] = solve['relativeResidual'] <= 1.1e-8
        poses.append(revised)
        frames.append(frame)
    Image.fromarray(permission.astype(np.uint8)*255).save(OUT/'allowed-mask.png')
    Image.fromarray(protected.astype(np.uint8)*255).save(OUT/'protected-foreground-mask.png')
    for width in (80,113,192,224):
        comparison(frames,width,['current v2','feather NO','solve NO']).save(OUT/f'contact-{width}px.png')
    board = Image.new('RGB',(960,512),'#23252b')
    draw = ImageDraw.Draw(board)
    for i,(image,label) in enumerate(zip(poses,['current v2','feather: not adopted','harmonic: not adopted'])):
        tile = Image.new('RGBA',(320,480),'#23252b')
        tile.alpha_composite(image.crop((680,540,1000,1020)))
        board.paste(tile.convert('RGB'),(320*i,32))
        draw.text((320*i+8,10),label,fill='white')
    board.save(OUT/'detail.png')
    metadata = dict(sourceSha256=ACCEPTED_SHA,parentPoseRGBAHash=PARENT_HASH,generatedSha256=GENERATED_SHA,
        sourceCrop=[680,540,1000,1020],rawCanvas=[1024,1536],
        role='unadopted face-free hidden-hair compositing study',methods=records,
        fullCropRedrawAccepted=False,handOrSleeveRepaintAccepted=False,facialGeometryRepair=False,
        activeCompositionVersion='review-art-v2',activeAtlasChanged=False,adopted=False,
        visualAcceptance='not-accepted',installableFullAtlas=False,installed=False,
        unresolved=['Generated crop repaints clothing and hair outside permission; its full redraw is not used.',
                    'Bounded feather reduces neither all color plates nor mismatched strand paths.',
                    'Harmonic RGB boundary correction improves some color joins but cannot repair strand topology.',
                    'No full-pose, motion, small-scale aesthetic or state-transition acceptance follows from pixel guards.'])
    (OUT/'build.json').write_text(json.dumps(metadata,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(metadata,indent=2))


if __name__ == '__main__':
    main()
