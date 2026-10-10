"""Use new cloth only; the original lowered palm/cape/frontlock stay fixed."""
import hashlib
import numpy as np
from PIL import Image,ImageDraw,ImageFilter

from canonical import ROOT,bounded_artwork
from arm_material import project_fixed_crop
from guide_wave_amplitude import BOX

OUT=ROOT/'candidates/phase5/wave-amplitude-cloth-v1'
# The old peak palm contour, translated down exactly 55 source pixels.
HAND=[(327,710),(313,704),(300,693),(300,675),(311,664),(307,649),
      (311,635),(322,627),(339,637),(351,651),(354,629),(363,607),
      (377,605),(386,615),(396,647),(411,644),(424,654),(424,669),
      (414,690),(407,706)]
PATCH=[(415,570),(453,574),(482,578),(490,590),(511,608),(513,644),
       (489,692),(468,733),(442,775),(421,784),(412,735),(405,709),
       (411,687),(428,669),(419,651),(404,631),(405,607)]
GENERATED_SHA='D5AC19778E9C260ACA276F10B05417BB921563808FFE185A18A1B5FE16502113'


def repair(parent,protected,exclude_old_red=True):
    path=OUT/'generated.png'
    digest=hashlib.sha256(path.read_bytes()).hexdigest().upper()
    if digest!=GENERATED_SHA:
        raise ValueError('Frozen cloth repair input changed')
    with Image.open(path) as image:
        mapped=project_fixed_crop(parent,image.convert('RGBA'),[1024,1536],BOX)
    result,allowed,_=bounded_artwork(parent,mapped,[PATCH],1.5)
    hand=Image.new('L',parent.size);ImageDraw.Draw(hand).polygon(HAND,fill=255)
    hand_mask=np.asarray(hand.filter(ImageFilter.MaxFilter(7)))>0
    # The approximate contour also encloses a sliver of the old floating
    # bright-red band beside the thumb. It is cloth, not palm/hand ink.
    rgb=np.asarray(parent)[...,:3].astype(np.int16)
    r,g,b=np.moveaxis(rgb,-1,0)
    old_red=(r>175)&(r-g>60)&(g<140)&(b<150)
    excluded=hand_mask&old_red
    if exclude_old_red:hand_mask &= ~old_red
    # Do not trust a generation prompt to preserve fingers or the cape.
    restore=protected|hand_mask
    pixels=np.asarray(result).copy();source=np.asarray(parent)
    pixels[restore]=source[restore];allowed &= ~restore
    changed=np.any(pixels!=source,axis=2)
    if np.any(changed&~allowed):raise ValueError('Cloth repair changed protected pixels')
    detail=dict(generatedSha256=digest,sourceCrop=list(BOX),rawCanvas=[1024,1536],
        uniformProjection=True,repairPolygon=PATCH,handProtectionPolygon=HAND,
        handInkDilationSourcePx=3,changedSourcePixels=int(changed.sum()),
        oldBrightRedClothExcludedFromHandProtection=int(excluded.sum()),
        handProtectionEstimated=True,
        handChangedSourcePixels=int(changed[hand_mask].sum()),protectedChangedPixels=0,
        generatedHandNotUsed=True,generatedCapeNotUsed=True,newClothArtworkUsed=True)
    return Image.fromarray(pixels),detail,hand_mask,allowed
