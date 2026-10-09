"""Create and really reopen the independent cloth study in GIMP 3.

Run with GIMP's python-fu-eval batch interpreter. No desktop UI automation.
"""
from array import array
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from gimp_review_project import Gimp, Gegl, file, load_layer, save, export, set_mask

SOURCE = ROOT/'candidates/phase5/review-sleeves-v1'
OUT = Path(globals().get('PROJECT_OUTPUT',ROOT/'work/gimp-review-sleeves-v1')).resolve()


def main():
    if ROOT not in OUT.parents:
        raise ValueError('Project must stay in a fresh repository subdirectory')
    OUT.mkdir(parents=True,exist_ok=True)
    xcf = OUT/'kaguya-review-sleeves.xcf'
    if xcf.exists():
        raise RuntimeError('Do not overwrite an existing editable project')
    image = Gimp.file_load(Gimp.RunMode.NONINTERACTIVE,
        file(ROOT/'candidates/phase5/review-art-v4/pose.png'))
    if image is None or (image.get_width(),image.get_height())!=(1205,1306):
        raise RuntimeError('Source-space camera must not change')
    image.convert_precision(Gimp.Precision.FLOAT_NON_LINEAR)
    base = image.get_layers()[0]
    base.set_name('01 Locked v4 - face, hands, accessories and silhouette')
    base.set_lock_position(True)
    cloth = load_layer(image,SOURCE/'mapped-cloth.png','02 Complete cloth surface - editable mask')
    cloth.set_mode(Gimp.LayerMode.NORMAL)
    cloth.set_blend_space(Gimp.LayerColorSpace.RGB_NON_LINEAR)
    cloth.set_composite_space(Gimp.LayerColorSpace.RGB_NON_LINEAR)
    mask_image = Gimp.file_load(Gimp.RunMode.NONINTERACTIVE,file(SOURCE/'blend-weight.png'))
    rect = Gegl.Rectangle.new(0,0,image.get_width(),image.get_height())
    weights = [value/255 for value in mask_image.get_layers()[0].get_buffer().get(
        rect,1.0,"Y' u8",Gegl.AbyssPolicy.NONE)]
    rgba = array('f')
    rgba.frombytes(cloth.get_buffer().get(rect,1.0,'RGBA float',Gegl.AbyssPolicy.NONE))
    compensation = [(1-w)/(1-rgba[4*i+3]*w) if rgba[4*i+3]*w<1 else 0
                    for i,w in enumerate(weights)]
    set_mask(base,rect,compensation)
    base.set_lock_content(True)
    set_mask(cloth,rect,weights)
    cloth.set_edit_mask(True)
    load_layer(image,ROOT/'sources/canonical/artwork.png',
               'REFERENCE ONLY - canonical v3, never replace',False,True)
    load_layer(image,SOURCE/'protected-mask.png','GUIDE ONLY - protected foreground',False,True)
    image.set_selected_layers([cloth])
    save(image,xcf)
    export(image,OUT/'gimp-export.png')
    reopened = Gimp.file_load(Gimp.RunMode.NONINTERACTIVE,file(xcf))
    export(reopened,OUT/'gimp-reopened-export.png')
    metadata = dict(editor='GIMP',editorVersion=Gimp.version(),canvas=[1205,1306],
        project=xcf.name,projectSha256=hashlib.sha256(xcf.read_bytes()).hexdigest().upper(),
        projectReopened=True,parentCompositionVersion='review-art-v4',
        layers=[dict(name=layer.get_name(),visible=layer.get_visible(),
                     locked=layer.get_lock_content(),hasMask=layer.get_mask() is not None)
                for layer in reopened.get_layers()],
        composition='normal-over with float base-mask compensation; nonlinear RGB',
        maskEditingRequiresBaseCompensationRebuild=True,nativeDesktopPaintingClaimed=False,
        cleanRigClaimed=False,userVisualApproval='pending',activeAtlasChanged=False,installedPetChanged=False)
    (OUT/'editor-check.json').write_text(json.dumps(metadata,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(metadata,indent=2))
    mask_image.delete()
    reopened.delete()
    image.delete()


if __name__=='__main__':
    main()
