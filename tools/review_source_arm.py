"""Source-pixel forearm prototype, not a recovered clean/full arm rig.

The original palm uses an estimated elbow rotation. The upper cuff still
blends toward its fixed attachment, so it is not wholly rigid. Upper attachment
is fixed; the lower hanging sleeve follows wrist translation, not a rigid
rotation that would make the whole sleeve point sideways. Use a conditioned
RGB material over the archived hidden backing, retaining the mother alpha.
"""
import hashlib
import json
import math

import numpy as np
from PIL import Image,ImageDraw,ImageFilter

from canonical import ROOT,ACCEPTED_SHA,load_canonical
from review_arm_backing import localized_backing,load_generated,specification,GENERATED_SHA
from build_idle import smooth,sample
from review_wave import native_frame
from animation_output import write_animation
from protocol import DURATIONS
from review_sleeves import component,fill_holes

OUT = ROOT/'candidates/phase5/wave-source-rig-v1'
BOX = (250,565,527,1001)
SHOULDER = (476.,585.)
ELBOW = (449.,703.)
WRIST = (356.,743.)
ANGLES = (0.,6.,-3.,0.)
FAILED_AA_RGBA = '6D652F1AC28346FBF9A74D5723849C22D29A67EE6969C436A07F8FEB486788FE'
ARM = [(411,575),(459,576),(489,580),(486,607),(499,590),(521,604),
       (519,634),(498,678),(471,723),(449,775),(442,805),(429,847),
       (413,886),(396,931),(378,956),(351,978),(331,982),(313,972),
       (303,951),(298,927),(300,876),(304,828),(313,777),(309,774),
       (295,777),(283,771),(282,763),(292,757),(279,753),(270,747),
       (271,738),(282,736),(308,728),(333,718),(324,703),(312,691),
       (310,678),(324,666),(348,638),(380,607),(406,581)]
TORSO = [(512,657),(532,659),(542,666),(579,682),(627,675),(685,696),
         (704,737),(734,780),(764,817),(802,871),(807,884),(782,893),
         (756,911),(729,891),(712,875),(687,891),(687,916),(665,924),
         (637,927),(624,908),(612,918),(560,923),(516,920),(480,913),
         (480,890),(461,884),(450,908),(421,901),(397,884),(397,872),
         (425,816),(458,749),(492,690)]


def rgba_hash(image):
    return hashlib.sha256(image.tobytes()).hexdigest().upper()


def materials(semantic=True, background_override=None):
    mother = load_canonical()
    definition = specification()
    if background_override is None:
        background, _ = localized_backing(mother,load_generated(),definition)
    else:
        if background_override.size != mother.size or background_override.mode != 'RGBA':
            raise ValueError('Hidden backing must retain the fixed mother canvas')
        background = background_override.copy()
    hint = Image.new('L',mother.size)
    ImageDraw.Draw(hint).polygon(ARM,fill=255)
    protected = Image.new('L',mother.size)
    draw = ImageDraw.Draw(protected)
    for polygon in definition['preservedForegroundPolygons']+[TORSO]:
        draw.polygon(polygon,fill=255)
    for rect in definition['protectedRects']:
        draw.rectangle(rect,fill=255)
    protection = np.asarray(protected)>0
    allowed = np.zeros(protection.shape,dtype=bool)
    x0,y0,x1,y1 = BOX
    allowed[y0:y1,x0:x1] = True
    allowed &= ~protection
    if semantic:
        # A guessed sparse contour missed the original fingertips/hem ink.
        # Select the actual colored parts within its bounded 14px search
        # envelope, then include their ink edges. These are estimated masks,
        # not recovered artist layers or a general object detector.
        broad = np.asarray(hint.filter(ImageFilter.MaxFilter(29)))>0
        rgb = np.asarray(mother)[y0:y1,x0:x1,:3].astype(np.int16)
        r,g,b = np.moveaxis(rgb,-1,0)
        classes = [((g-r>=-8)&(g-b>16)&(g>75),[(435,688),(341,881)]),
                   ((r-g>30)&(r-b>50)&(r>100)&(g>20),[(390,629)])]
        selected = np.zeros(rgb.shape[:2],dtype=bool)
        local_budget = broad[y0:y1,x0:x1]&allowed[y0:y1,x0:x1]
        for binary,seeds in classes:
            for sx,sy in seeds:
                selected |= component(binary&local_budget,(sx-x0,sy-y0))
        # Finger shading and ink can disconnect individual skin islands from
        # the palm; a single color seed omitted the original thumb. All skin
        # islands in this hand-only rectangle participate, not body/face skin.
        hand_box = np.zeros(selected.shape,dtype=bool)
        hand_box[724-y0:800-y0,264-x0:370-x0] = True
        skin = ((r>=170)&(g>=135)&(b>=130)&(r>=g)&(g>=b)&(r-g<100)&(g-b<65))
        selected |= skin&hand_box&local_budget
        cuff = Image.new('L',(x1-x0,y1-y0))
        ImageDraw.Draw(cuff).polygon([(x-x0,y-y0) for x,y in
            [(310,675),(324,676),(414,779),(404,790)]],fill=255)
        cream = (r>170)&(g>165)&(b>145)&(r-g<35)&(g-b<50)
        selected |= cream&(np.asarray(cuff)>0)&local_budget
        core = Image.fromarray(selected.astype(np.uint8)*255)
        closed = core.filter(ImageFilter.MaxFilter(9)).filter(ImageFilter.MinFilter(9))
        surface = Image.fromarray(fill_holes(np.asarray(closed)>0).astype(np.uint8)*255)
        # Include measured thick ink up to 8px away, not an 8px opaque halo
        # of adjacent hair. At (340,982), a 4px dilation left the old hem ink.
        surface_values = np.asarray(surface)>0
        nearby = np.asarray(surface.filter(ImageFilter.MaxFilter(17)))>0
        # Retirement includes the brown antialias fringe too: samples
        # (350,982)=(161,110,57), (346,983)=(180,134,78) were left static
        # by the earlier dark-ink-only threshold. It is still a bounded
        # estimated edge permission, not proof of semantic ownership.
        ink = (r<225)&(g<195)&(b<145)
        ink_support = surface_values|(nearby&ink)
        ink_support = fill_holes(ink_support)
        ink_support &= local_budget
        hard = Image.new('L',mother.size)
        hard.paste(Image.fromarray(ink_support.astype(np.uint8)*255),(x0,y0))
        # The torso polygon missed parts of its dark outline. Isolate its
        # actual connected red cloth and preserve the ink beside that cloth.
        torso_box = (380,650,825,935)
        tx0,ty0,tx1,ty1 = torso_box
        torso_rgb = np.asarray(mother)[ty0:ty1,tx0:tx1,:3].astype(np.int16)
        tr,tg,tb = np.moveaxis(torso_rgb,-1,0)
        torso_core = component((tr-tg>25)&(tr>140)&(tg>50),(560-tx0,800-ty0))
        torso_mask = Image.fromarray(torso_core.astype(np.uint8)*255).filter(ImageFilter.MaxFilter(9))
        torso_ink = np.zeros(protection.shape,dtype=bool)
        torso_ink[ty0:ty1,tx0:tx1] = np.asarray(torso_mask)>0
        protection |= torso_ink
        allowed &= ~protection
        hard_values = np.asarray(hard)>0
        hard_values &= allowed
        hard = Image.fromarray(hard_values.astype(np.uint8)*255)
        # Outside the old material, the mother's hair is already visible and
        # known. Do not substitute generated backing there or carry those
        # source/backing color differences along with the moving arm.
        old_backing = np.asarray(background).copy()
        source_pixels = np.asarray(mother)
        old_backing[~hard_values] = source_pixels[~hard_values]
        background = Image.fromarray(old_backing)
        hint = hard.filter(ImageFilter.GaussianBlur(.75))
        hint_values = np.asarray(hint).copy()
        hint_values[~hard_values] = 0
        hint = Image.fromarray(hint_values)
    else:
        hint = hint.filter(ImageFilter.GaussianBlur(.75))
    beta = np.asarray(hint,dtype=np.float64)/255
    beta[~allowed] = 0
    a,b = np.asarray(mother)[...,:3].astype(float),np.asarray(background)[...,:3].astype(float)
    delta = a-b
    minimum = np.max(np.where(delta>=0,delta/np.maximum(255-b,1),-delta/np.maximum(b,1)),axis=2)
    beta = np.where(beta>0,np.maximum(beta,minimum),0)
    beta = np.clip(beta,0,1)
    foreground = a-(1-beta[...,None])*b
    foreground[beta==0] = 0
    if np.any(foreground < -1e-9) or np.any(foreground > 255*beta[...,None]+1e-9):
        raise ValueError('Conditioned foreground must have valid premultiplied RGB')
    return dict(mother=mother,background=background,beta=beta,foreground=foreground,
                allowed=allowed,protected=protection)


def forward(x,y,angle):
    if isinstance(angle,bool) or not math.isfinite(angle) or not -6<=angle<=8:
        raise ValueError('This small-motion study permits -6 to 8 degrees only')
    theta = math.radians(angle)
    ex,ey = ELBOW
    # Fading displacement only by height compresses the upper left cloth:
    # 6deg gave material Jacobian .824669, despite positive global orientation.
    # In polar coordinates, theta'=theta+phi(theta) has area ratio
    # 1+dphi/dtheta. Broad angular ramps keep attachment fixed without the
    # large radial lever arm of that height-only fade. Only the palm sector
    # is exactly rigid; the upper cuff partly lies outside it.
    # Shoulder sector is exactly fixed. Do not call the entire cuff rigid.
    polar_degrees = np.degrees(np.arctan2(y-ey,x-ex)) % 360
    attachment = smooth(50,110,polar_degrees)*(1-smooth(180,280,polar_degrees))
    local_theta = theta*attachment
    cosine,sine = np.cos(local_theta),np.sin(local_theta)
    rx = (x-ex)*cosine-(y-ey)*sine+ex-x
    ry = (x-ex)*sine+(y-ey)*cosine+ey-y
    wx,wy = WRIST
    dx = (wx-ex)*math.cos(theta)-(wy-ey)*math.sin(theta)+ex-wx
    dy = (wx-ex)*math.sin(theta)+(wy-ey)*math.cos(theta)+ey-wy
    # Spread the cloth handoff over the real long sleeve. A 70px handoff
    # compressed material near (407,819) to .885394 at +6deg.
    hanging = smooth(790,960,y)
    return (np.round(x+(1-hanging)*rx+hanging*attachment*dx,12),
            np.round(y+(1-hanging)*ry+hanging*attachment*dy,12))


def inverse(x,y,angle):
    sx,sy = x.copy(),y.copy()
    for _ in range(24):
        fx,fy = forward(sx,sy,angle)
        sx += x-fx
        sy += y-fy
    fx,fy = forward(sx,sy,angle)
    error = np.hypot(fx-x,fy-y)
    if np.max(error)>1e-5:
        raise ValueError('Inverse field did not converge; do not hide a fold')
    return sx,sy,round(float(np.max(error)),8)


def diagnose_field():
    data = materials()
    x0,y0,x1,y1 = BOX
    yy,xx = np.mgrid[y0:y1,x0:x1].astype(float)
    support = data['beta'][y0:y1,x0:x1]>0
    for angle in (6.,4.,-3.):
        sx,sy = xx.copy(),yy.copy()
        errors = {}
        for i in range(1,33):
            fx,fy = forward(sx,sy,angle)
            sx += xx-fx;sy += yy-fy
            if i in (12,20,32):
                fx,fy = forward(sx,sy,angle)
                errors[i] = float(np.hypot(fx-xx,fy-yy).max())
        fx,fy = forward(xx,yy,angle)
        dxx,dxy = np.gradient(fx);dyx,dyy = np.gradient(fy)
        jacobian = dxy*dyx-dxx*dyy
        iy,ix = np.unravel_index(np.argmin(jacobian),jacobian.shape)
        material_jacobian = np.where(support,jacobian,np.inf)
        my,mx = np.unravel_index(np.argmin(material_jacobian),jacobian.shape)
        print(dict(angle=angle,inverseErrors=errors,minimumGlobalJacobian=float(jacobian.min()),
                   minimumMaterialJacobian=float(jacobian[support].min()),
                   minimumGlobalSourcePoint=[int(xx[iy,ix]),int(yy[iy,ix])],
                   minimumMaterialSourcePoint=[int(xx[my,mx]),int(yy[my,mx])]))


def pose(data,angle):
    x0,y0,x1,y1 = BOX
    yy,xx = np.mgrid[y0:y1,x0:x1].astype(float)
    sx,sy,error = inverse(xx,yy,angle)
    beta = data['beta'][y0:y1,x0:x1]
    foreground = data['foreground'][y0:y1,x0:x1]
    warped_beta = np.clip(sample(beta,sx-x0,sy-y0),0,1)
    warped_foreground = sample(foreground,sx-x0,sy-y0)
    warped_foreground = np.clip(warped_foreground,0,255*warped_beta[...,None])
    base = np.asarray(data['background'])[y0:y1,x0:x1,:3].astype(float)
    composed = np.clip(np.rint(warped_foreground+(1-warped_beta[...,None])*base),0,255).astype(np.uint8)
    result = np.asarray(data['mother']).copy()
    use = data['allowed'][y0:y1,x0:x1] & ((beta>0)|(warped_beta>0))
    result[y0:y1,x0:x1,:3][use] = composed[use]
    # Do not interpret nearly constant AI cutout alpha as a recovered
    # foreground matte. Small motions stay inside the existing hair silhouette.
    before = np.asarray(data['mother'])
    changed = np.any(result!=before,axis=2)
    if np.any(changed & ~data['allowed']):
        raise ValueError('Forearm touched a protected/outside pixel')
    fx,fy = forward(xx,yy,angle)
    dxx,dxy = np.gradient(fx)
    dyx,dyy = np.gradient(fy)
    jacobian = dxy*dyx-dxx*dyy
    if jacobian.min()<.90:
        raise ValueError('Cloth field folds or compresses beyond this study')
    wx,wy = forward(np.array([WRIST[0]]),np.array([WRIST[1]]),angle)
    metadata = dict(angleDegrees=angle,wristSourcePx=[round(float(wx[0]),8),round(float(wy[0]),8)],
        forearmLengthSourcePx=round(float(np.hypot(wx[0]-ELBOW[0],wy[0]-ELBOW[1])),8),
        minimumForwardJacobian=round(float(jacobian.min()),8),maximumInverseErrorSourcePx=error,
        changedPixels=int(changed.sum()),changedOutsidePermission=int((changed&~data['allowed']).sum()),
        poseRGBAHash=rgba_hash(Image.fromarray(result)))
    return Image.fromarray(result),metadata


def editor_material(data, output):
    """Archive float source material for actual GIMP mask editing, not a rig."""
    x0,y0,x1,y1 = BOX
    beta = data['beta'][y0:y1,x0:x1]
    foreground = data['foreground'][y0:y1,x0:x1]
    straight = np.zeros((*beta.shape,4),dtype=np.float64)
    np.divide(foreground,255*beta[...,None],out=straight[...,:3],where=beta[...,None]>0)
    straight[...,3] = np.asarray(data['mother'])[y0:y1,x0:x1,3]/255
    straight.astype('<f4').tofile(output/'gimp-foreground-rgba.f32')
    beta.astype('<f4').tofile(output/'gimp-foreground-mask.f32')
    background = np.asarray(data['background']).copy()
    background[...,3] = np.asarray(data['mother'])[...,3]
    Image.fromarray(background).save(output/'gimp-background.png')
    record = dict(canvas=list(data['mother'].size),roi=list(BOX),
        format='little-endian float32, straight nonlinear RGBA plus numeric matte',
        alphaPlane='canonical mother, not a recovered foreground alpha',
        foregroundSha256=hashlib.sha256((output/'gimp-foreground-rgba.f32').read_bytes()).hexdigest().upper(),
        maskSha256=hashlib.sha256((output/'gimp-foreground-mask.f32').read_bytes()).hexdigest().upper(),
        cleanArtistLayers=False,maskEditingRequiresRebuild=True)
    (output/'gimp-material.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')


def main(backing_v2=False):
    output = ROOT/'candidates/phase5/wave-source-rig-v2' if backing_v2 else OUT
    output.mkdir(parents=True,exist_ok=True)
    if backing_v2:
        from review_source_backing import load_projected, OUT as BACKING_OUT
        override = load_projected()
        backing_sha = json.loads((BACKING_OUT/'generated.json').read_text(encoding='utf-8'))['sha256']
        data = materials(background_override=override)
    else:
        failed,failed_measure = pose(materials(semantic=False),6.)
        failed.save(output/'failed-coarse-contour-pose.png')
        # This earlier AA-threshold result is an immutable failure fixture,
        # not generated by the final mask recipe and not silently discarded.
        with Image.open(output/'failed-incomplete-aa-pose.png') as fixture:
            if rgba_hash(fixture.convert('RGBA')) != FAILED_AA_RGBA:
                raise ValueError('Archived incomplete-AA failure changed')
        data = materials()
        backing_sha = GENERATED_SHA
    rendered = [pose(data,angle) for angle in ANGLES]
    poses,measurements = zip(*rendered)
    frames = [native_frame(image) for image in poses]
    write_animation(output,frames,DURATIONS[3])
    for i,image in enumerate(poses):
        image.save(output/f'pose-{i}.png')
    for name,mask in [('estimated-matte',data['beta']),('allowed-mask',data['allowed']),('protected-mask',data['protected'])]:
        Image.fromarray(np.rint(mask*255).astype(np.uint8)).save(output/(name+'.png'))
    data['background'].save(output/'hidden-backing.png')
    if backing_v2:
        editor_material(data,output)
    detail = Image.new('RGB',(1000,460),'#23252b')
    draw = ImageDraw.Draw(detail)
    for i,image in enumerate(poses):
        crop = Image.new('RGBA',(277,436),'#ededed')
        crop.alpha_composite(image.crop(BOX))
        detail.paste(crop.resize((250,394),Image.Resampling.LANCZOS).convert('RGB'),(250*i,35))
        draw.text((250*i+5,10),f'{i}: {ANGLES[i]} deg / {DURATIONS[3][i]} ms',fill='white')
    detail.save(output/'detail.png')
    meta = dict(sourceSha256=ACCEPTED_SHA,source='sources/canonical/artwork.png',
        backingGeneratedSha256=backing_sha,state='waving',nativeRow=3,durationsMs=DURATIONS[3],
        totalDurationMs=sum(DURATIONS[3]),repeatBeforeIdle=3,canvas=[1205,1306],roi=list(BOX),
        shoulderSourcePx=list(SHOULDER),elbowSourcePx=list(ELBOW),wristSourcePx=list(WRIST),
        jointPositionsEstimated=True,forearmRotationDriven=True,palmAndCuffShareRotation=False,
        palmRotationRigidInSector=True,upperCuffAttachmentEstimated=True,
        lowerSleeveFollowsWristTranslation=True,sourceMatteEstimated=True,
        material='background-conditioned latent RGB foreground; canonical alpha plane retained',
        armEnvelope=ARM,protectedTorso=TORSO,anglesDegrees=list(ANGLES),measurements=list(measurements),
        neutralChangedPixels=measurements[0]['changedPixels'],neutralFromSameMaterialNotSourceShortcut=True,
        neutralRestRGBAExact=poses[0].tobytes()==poses[-1].tobytes()==data['mother'].tobytes(),
        sourceBackgroundOutsideMaterialPreserved=True,
        failedCoarseContourRetained=not backing_v2,
        failedCoarseContourPoseRGBAHash=None if backing_v2 else rgba_hash(failed),
        failedIncompleteAAFixtureRGBAHash=None if backing_v2 else FAILED_AA_RGBA,
        sourceForegroundArtwork=True,newForegroundArtworkGenerated=False,
        hiddenBackingVersion=2 if backing_v2 else 1,fullRedrawAccepted=False,
        facialGeometryRepair=False,cleanLayerRecoveryClaimed=False,articulatedArmBuilt=False,
        nativeInterpolation=False,visualMotionApproval='pending',strategyUserApproval='pending',
        adopted=False,activeAtlasChanged=False,installableFullAtlas=False,installed=False,
        frameHashes=[rgba_hash(image) for image in frames],
        unresolved=['Estimated joint positions and foreground matte, not original artist layers or a complete elbow/wrist rig.',
            'Visible old-arm retirement and nonzero arm/cuff/hair seams require inspection; neutral equality is not aesthetic proof.',
            'The upper cuff lies in the attachment fade; the entire cuff does not share one rigid palm rotation.',
            'Small low-hand movement may not communicate greeting at 80px; it is not an approved replacement gesture.',
            'Four native held frames still have discrete changes; arbitrary cross-state interruption/entry is not solved.',
            'Hidden hair is generated/estimated; movement foreground comes only from the approved mother.'])
    (output/'build.json').write_text(json.dumps(meta,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(meta,indent=2))


if __name__=='__main__':
    import sys
    diagnose_field() if '--inspect-field' in sys.argv else main('--backing-v2' in sys.argv)
