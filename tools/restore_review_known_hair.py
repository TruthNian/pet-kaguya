"""Recover known source hair; estimate only unknown interior continuity."""
import hashlib
import json

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from canonical import ROOT,ACCEPTED_SHA,load_canonical,bounded_masks
import review_review_v2 as parent
from review_wave import native_frame
from hair_boundary import harmonic_rgb

OUT = ROOT/'candidates/phase5/review-art-v3'
PARENT_HASH = '8618A3A73301ED7A3B29D63983878159C7B35D39BA33E465186584C539E32570'


def specification():
    spec = json.loads((OUT/'restoration.json').read_text(encoding='utf-8'))
    if (spec['sourceSha256'] != ACCEPTED_SHA or spec['parentPoseRGBAHash'] != PARENT_HASH
            or spec['parentCompositionVersion'] != 'review-art-v2' or spec['compositionVersion'] != 'review-art-v3'
            or spec['canvas'] != [1205,1306] or spec['editBudget'] != [776,570,958,1000]
            or spec['foregroundProtectionRadiusSourcePx'] != 6 or spec['fullyPaintedAlphaMinimum'] != 240
            or spec['minimumRedGreenSeparation'] != 10 or spec['minimumGreenBlueSeparation'] != 20
            or spec['originalRGBAIsCopiedExactly'] is not True or spec['permissionMustBeSubsetOfParentArmPatch'] is not True
            or spec['hiddenRGBBoundaryReconciliation'] is not True or spec['hiddenAlphaContinuityEstimation'] is not True
            or spec['hiddenAlphaNominalValue'] != 253 or spec['solverRelativeTolerance'] != 1e-8
            or spec['solverMaxIterations'] != 1600
            or spec['visualAcceptance'] != 'pending'
            or any(spec[key] is not False for key in ('newArtworkGenerated','fullRedrawAccepted','newFaceGeometryAllowed',
                   'handOrSleeveRepaintAllowed','cleanLayerRecoveryClaimed','hiddenHairReconstructionClaimed',
                   'installableFullAtlas','installed'))):
        raise ValueError('Known hair restoration violates the recorded source/foreground boundary')
    for key in ('knownHairPolygon','unknownHairPolygon'):
        polygon = np.asarray(spec[key])
        x0,y0,x1,y1 = spec['editBudget']
        if (polygon.ndim != 2 or polygon.shape[1] != 2 or len(polygon) < 3 or not np.isfinite(polygon).all()
                or np.any(polygon[:,0] < x0) or np.any(polygon[:,0] > x1)
                or np.any(polygon[:,1] < y0) or np.any(polygon[:,1] > y1)):
            raise ValueError('Known/unknown hair annotation exceeds its inspected source budget')
    return spec


def restore(pose,parent_spec,parent_allowed,preserved,definition=None,reconcile=True):
    spec = specification() if definition is None else definition
    if spec != specification() or parent_spec != parent.specification():
        raise ValueError('Known hair cannot alter its recorded parent/permission')
    if hashlib.sha256(pose.tobytes()).hexdigest().upper() != PARENT_HASH:
        raise ValueError('Known hair restoration needs its exact unchanged parent pose')
    source = load_canonical()
    foreground = Image.new('L',pose.size)
    draw = ImageDraw.Draw(foreground)
    draw.polygon(parent_spec['foregroundRightArmPolygon'],fill=255)
    for polygon in parent_spec['preservedForegroundPolygons']:
        draw.polygon(polygon,fill=255)
    protected = np.asarray(foreground.filter(ImageFilter.MaxFilter(13))) > 0
    original_foreground = Image.new('L',pose.size)
    for polygon in parent_spec['preservedForegroundPolygons']:
        ImageDraw.Draw(original_foreground).polygon(polygon,fill=255)
    expected_preserved = np.asarray(original_foreground) > 0
    expected_allowed = bounded_masks(pose.size,
        [parent_spec['oldRightArmPolygon'],parent_spec['foregroundRightArmPolygon']],
        parent_spec['edgeFeatherSourcePx'])[0] & ~expected_preserved
    if (parent_allowed.dtype != np.bool_ or preserved.dtype != np.bool_
            or not np.array_equal(parent_allowed,expected_allowed) or not np.array_equal(preserved,expected_preserved)):
        raise ValueError('Known hair cannot broaden permission or erase foreground protection')
    domain = Image.new('L',pose.size)
    ImageDraw.Draw(domain).polygon(spec['knownHairPolygon'],fill=255)
    before,original = np.asarray(pose),np.asarray(source)
    colors = original[...,:3].astype(int)
    # A conservative color screen supplements, never replaces, the inspected
    # visible-hair annotation. It is not a recovered semantic matte.
    warm = ((colors[...,0]-colors[...,1] >= spec['minimumRedGreenSeparation'])
            & (colors[...,1]-colors[...,2] >= spec['minimumGreenBlueSeparation']))
    allowed = (np.asarray(domain)>0) & parent_allowed & ~protected & ~preserved & warm
    allowed &= (original[...,3] >= 240) & (before[...,3] >= 240)
    result = before.copy()
    result[allowed] = original[allowed]
    known = allowed.copy()
    if not known.any():
        raise ValueError('Known hair restoration has no inspected source anchor')
    if int(np.median(original[...,3][known])) != spec['hiddenAlphaNominalValue']:
        raise ValueError('Hidden alpha estimate is not the inspected visible hair median')
    unknown = np.zeros_like(known)
    if reconcile:
        domain = Image.new('L',pose.size)
        ImageDraw.Draw(domain).polygon(spec['unknownHairPolygon'],fill=255)
        unknown = (np.asarray(domain)>0) & parent_allowed & ~protected & ~preserved & ~known
        unknown &= before[...,3] >= spec['fullyPaintedAlphaMinimum']
        if not shared_edges(known,unknown):
            raise ValueError('Unknown hair is disconnected from its known source boundary')
        result,_ = harmonic_rgb(result,before,unknown,spec['solverRelativeTolerance'],spec['solverMaxIterations'])
        # Unknown interior opacity is estimated from a continuous painted
        # lock, not advertised as a recovered alpha layer. Known RGBA stays
        # bit-identical; held foreground and exterior alpha are protected.
        alpha_parent = np.repeat(result[...,3:4],4,axis=2)
        alpha_material = np.full_like(alpha_parent,spec['hiddenAlphaNominalValue'])
        alpha,_ = harmonic_rgb(alpha_parent,alpha_material,unknown,
            spec['solverRelativeTolerance'],spec['solverMaxIterations'])
        result[unknown,3] = alpha[unknown,0]
        allowed |= unknown
    changed = np.any(result!=before,axis=2)
    if np.any(changed & (~allowed | protected | preserved)):
        raise ValueError('Known hair restoration changed a protected/exterior pixel')
    if not np.array_equal(result[known],original[known]):
        raise ValueError('Boundary reconciliation altered the restored known pixels')
    return Image.fromarray(result),allowed,protected,known,unknown


def shared_edges(known,unknown):
    return int((known[:-1]&unknown[1:]).sum()+(known[1:]&unknown[:-1]).sum()
               +(known[:,:-1]&unknown[:,1:]).sum()+(known[:,1:]&unknown[:,:-1]).sum())


def main():
    base,spec,raw = parent.inputs()
    pose,permission,preserved = parent.localized_pose(base,raw,spec)
    restored,allowed,protected,known,unknown = restore(pose,spec,permission,preserved)
    diagnostic = ROOT/'work/hair-contacts'
    diagnostic.mkdir(parents=True,exist_ok=True)
    restored.save(diagnostic/'restored-pose.png')
    source = load_canonical()
    frame = native_frame(restored)
    frames = [native_frame(pose),frame,native_frame(source)]
    for width in (80,113,192,224):
        parent.comparison(frames,width,['current v2','source restore','mother v3']).save(diagnostic/f'contact-{width}px.png')
    for name,image in [('restored',restored),('before',pose)]:
        image.crop((760,570,980,1020)).resize((440,900),Image.Resampling.NEAREST).save(diagnostic/f'{name}-detail.png')
    Image.fromarray(allowed.astype(np.uint8)*255).save(diagnostic/'restoration-mask.png')
    before,after = np.asarray(pose),np.asarray(restored)
    changed = np.any(after!=before,axis=2)
    print(json.dumps(dict(changedPixels=int(changed.sum()),outside=int((changed & ~allowed).sum()),
        knownSourcePixels=int(known.sum()),unknownInteriorPixels=int(unknown.sum()),
        restoredAlphaPixels=int((after[...,3]!=before[...,3]).sum()),
        poseRGBAHash=hashlib.sha256(restored.tobytes()).hexdigest().upper())))


if __name__ == '__main__':
    main()
