"""Run inside GIMP 3's python-fu-eval interpreter, not system Python.

Create a real editable mask project, export it, reopen the XCF and export
again. This is an editor workflow check, not aesthetic or rig approval.
"""
import json
from array import array
from pathlib import Path

import gi
gi.require_version('Gimp', '3.0')
gi.require_version('Gegl', '0.4')
from gi.repository import Gimp, Gegl, Gio

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT/'candidates/phase5/review-hand-outline-v1'
OUT = Path(globals().get('PROJECT_OUTPUT', ROOT/'work/gimp-review-v2')).resolve()
if ROOT not in OUT.parents:
    raise ValueError('Editor output must stay in a fresh repository subdirectory')


def file(path):
    return Gio.File.new_for_path(str(path))


def load_layer(image, path, name, visible=True, locked=False):
    layer = Gimp.file_load_layer(Gimp.RunMode.NONINTERACTIVE, image, file(path))
    if layer is None or not image.insert_layer(layer, None, 0):
        raise RuntimeError('GIMP could not insert '+str(path))
    layer.set_name(name)
    layer.set_visible(visible)
    layer.set_lock_content(locked)
    layer.set_lock_position(True)
    return layer


def save(image, path):
    if not Gimp.file_save(Gimp.RunMode.NONINTERACTIVE, image, file(path), None):
        raise RuntimeError('GIMP failed to save '+str(path))


def export(image, path):
    duplicate = image.duplicate()
    duplicate.merge_visible_layers(Gimp.MergeType.CLIP_TO_IMAGE)
    duplicate.convert_precision(Gimp.Precision.U8_NON_LINEAR)
    save(duplicate, path)
    duplicate.delete()


def set_mask(layer, rect, values):
    mask = layer.create_mask(Gimp.AddMaskType.BLACK)
    if not layer.add_mask(mask):
        raise RuntimeError('GIMP could not add a layer mask')
    mask.get_buffer().set(rect, 'Y float', array('f', values).tobytes())
    return mask


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    xcf = OUT/'kaguya-review-hand.xcf'
    if xcf.exists():
        raise RuntimeError('Preserve existing editable project; choose a fresh output directory')
    image = Gimp.file_load(Gimp.RunMode.NONINTERACTIVE,
                           file(ROOT/'candidates/phase5/review-art-v3/pose.png'))
    if image is None or (image.get_width(), image.get_height()) != (1205,1306):
        raise RuntimeError('GIMP must keep the full source-space camera')
    image.convert_precision(Gimp.Precision.FLOAT_NON_LINEAR)
    base = image.get_layers()[0]
    base.set_name('01 Before repair - locked review composition v3')
    base.set_lock_position(True)
    repair = load_layer(image, SOURCE/'mapped-source.png',
                        '02 Original lower hand - edit its mask, not its pixels')
    # REPLACE is a paint-internal mode, not a persistent image-layer mode:
    # GIMP resets it to NORMAL. Use normal-over with a compensated base mask.
    repair.set_mode(Gimp.LayerMode.NORMAL)
    repair.set_blend_space(Gimp.LayerColorSpace.RGB_NON_LINEAR)
    repair.set_composite_space(Gimp.LayerColorSpace.RGB_NON_LINEAR)
    mask_image = Gimp.file_load(Gimp.RunMode.NONINTERACTIVE, file(SOURCE/'blend-weight.png'))
    rect = Gegl.Rectangle.new(0, 0, image.get_width(), image.get_height())
    # Copy the numeric grayscale weights, without treating them as sRGB colors.
    weights = mask_image.get_layers()[0].get_buffer().get(rect, 1.0, "Y' u8", Gegl.AbyssPolicy.NONE)
    weights = [value/255 for value in weights]
    rgba = array('f')
    rgba.frombytes(repair.get_buffer().get(rect, 1.0, 'RGBA float', Gegl.AbyssPolicy.NONE))
    # alpha_out = alpha_raw*w + alpha_base*k*(1-alpha_raw*w).
    # k=(1-w)/(1-alpha_raw*w) gives the intended premultiplied crossfade,
    # instead of stacking another nearly opaque painted image on the parent.
    compensation = [(1-w)/(1-rgba[4*i+3]*w) if rgba[4*i+3]*w<1 else 0
                    for i,w in enumerate(weights)]
    set_mask(base, rect, compensation)
    base.set_lock_content(True)
    set_mask(repair, rect, weights)
    repair.set_edit_mask(True)
    load_layer(image, ROOT/'sources/canonical/artwork.png',
               'REFERENCE ONLY - selected canonical v3, face locked', visible=False, locked=True)
    load_layer(image, SOURCE/'protected-mask.png',
               'GUIDE ONLY - protected foreground, never replace', visible=False, locked=True)
    image.set_selected_layers([repair])
    save(image, xcf)
    # Use duplicates so exporting cannot discard layers from the saved project.
    export(image, OUT/'gimp-export.png')
    reopened = Gimp.file_load(Gimp.RunMode.NONINTERACTIVE, file(xcf))
    export(reopened, OUT/'gimp-reopened-export.png')
    layers = reopened.get_layers()
    metadata = dict(editor='GIMP', editorVersion=Gimp.version(), canvas=[1205,1306],
                    project=xcf.name, projectReopened=True,
                    layers=[dict(name=layer.get_name(), visible=layer.get_visible(),
                                 locked=layer.get_lock_content(), hasMask=layer.get_mask() is not None)
                            for layer in layers],
                    composition='normal-over with float base-mask compensation; nonlinear RGB',
                    maskEditingRequiresBaseCompensationRebuild=True,
                    nativeDesktopPaintingClaimed=False, cleanRigClaimed=False,
                    userVisualApproval='pending', installedPetChanged=False)
    (OUT/'editor-check.json').write_text(json.dumps(metadata,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(metadata,indent=2))
    mask_image.delete()
    image.delete()
    reopened.delete()


if __name__ == '__main__':
    main()
