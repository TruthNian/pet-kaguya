"""Create, reopen and export a real GIMP source-arm matte project.

Run in GIMP's python-fu-eval interpreter. This is estimated RGB material,
not recovered artist layers, a completed rig or native brush painting.
"""
from array import array
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from gimp_review_project import Gimp, Gegl, file, load_layer, save, export, set_mask

SOURCE = ROOT/'candidates/phase5/wave-source-rig-v2'
OUT = Path(globals().get('PROJECT_OUTPUT',ROOT/'work/gimp-source-arm-v1')).resolve()


def floats(path, expected_sha, length):
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest().upper() != expected_sha or len(raw) != length*4:
        raise ValueError('Archived float material changed')
    data = array('f');data.frombytes(raw)
    if sys.byteorder != 'little': data.byteswap()
    return data


def main():
    if ROOT not in OUT.parents:
        raise ValueError('Use a fresh repository subdirectory')
    OUT.mkdir(parents=True,exist_ok=True)
    xcf = OUT/'kaguya-source-arm.xcf'
    if xcf.exists(): raise RuntimeError('Preserve existing editable projects')
    record = json.loads((SOURCE/'gimp-material.json').read_text(encoding='utf-8'))
    x0,y0,x1,y1 = record['roi']
    width,height = x1-x0,y1-y0
    rgba = floats(SOURCE/'gimp-foreground-rgba.f32',record['foregroundSha256'],width*height*4)
    weights = floats(SOURCE/'gimp-foreground-mask.f32',record['maskSha256'],width*height)
    image = Gimp.file_load(Gimp.RunMode.NONINTERACTIVE,file(SOURCE/'gimp-background.png'))
    if image is None or [image.get_width(),image.get_height()]!=record['canvas']:
        raise RuntimeError('Fixed source camera must not change')
    image.convert_precision(Gimp.Precision.FLOAT_NON_LINEAR)
    base = image.get_layers()[0]
    base.set_name('01 Hidden hair backing - estimated, locked')
    base.set_lock_position(True)
    arm = Gimp.Layer.new(image,'02 Original arm artwork - estimated editable matte',
        width,height,Gimp.ImageType.RGBA_IMAGE,100,Gimp.LayerMode.NORMAL)
    if not image.insert_layer(arm,None,0): raise RuntimeError('Cannot insert foreground')
    arm.set_offsets(x0,y0)
    arm.set_lock_position(True)
    arm.set_blend_space(Gimp.LayerColorSpace.RGB_NON_LINEAR)
    arm.set_composite_space(Gimp.LayerColorSpace.RGB_NON_LINEAR)
    local = Gegl.Rectangle.new(0,0,width,height)
    arm.get_buffer().set(local,"R'G'B'A float",rgba.tobytes())
    mask = set_mask(arm,local,weights)
    arm.set_edit_mask(True)
    compensation = [1.]*(image.get_width()*image.get_height())
    for y in range(height):
        for x in range(width):
            i = y*width+x
            w,a = weights[i],rgba[4*i+3]
            compensation[(y0+y)*image.get_width()+x0+x] = (1-w)/(1-a*w) if a*w<1 else 0
    full = Gegl.Rectangle.new(0,0,image.get_width(),image.get_height())
    set_mask(base,full,compensation)
    base.set_lock_content(True)
    load_layer(image,ROOT/'sources/canonical/artwork.png',
        'REFERENCE ONLY - locked canonical v3',False,True)
    load_layer(image,SOURCE/'pose-1.png',
        'DIAGNOSTIC ONLY - +6 deg, seams unresolved',False,True)
    load_layer(image,SOURCE/'protected-mask.png',
        'GUIDE ONLY - fixed foreground',False,True)
    image.set_selected_layers([arm])
    save(image,xcf)
    export(image,OUT/'gimp-export.png')
    reopened = Gimp.file_load(Gimp.RunMode.NONINTERACTIVE,file(xcf))
    export(reopened,OUT/'gimp-reopened-export.png')
    metadata = dict(editor='GIMP',editorVersion=Gimp.version(),canvas=record['canvas'],
        project=xcf.name,projectSha256=hashlib.sha256(xcf.read_bytes()).hexdigest().upper(),
        projectReopened=True,sourceMaterial=SOURCE.relative_to(ROOT).as_posix(),
        layers=[dict(name=layer.get_name(),visible=layer.get_visible(),
                     locked=layer.get_lock_content(),hasMask=layer.get_mask() is not None)
                for layer in reopened.get_layers()],
        composition='nonlinear RGB normal-over with compensated base mask',
        floatEstimatedMaterial=True,sourceArtworkPreserved=True,
        maskEditingRequiresBaseCompensationRebuild=True,nativeDesktopPaintingClaimed=False,
        cleanRigClaimed=False,userVisualApproval='pending',activeAtlasChanged=False,
        installedPetChanged=False)
    (OUT/'editor-check.json').write_text(json.dumps(metadata,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(metadata,indent=2))
    reopened.delete();image.delete()


if __name__=='__main__': main()
