"""Single final quantization, with an independent float64 Lanczos reference.

Colours stay in the existing nonlinear sRGB convention. This changes neither
geometry nor host sampling. A float resize is not new detail or a higher FPS.
"""
from functools import lru_cache

import numpy as np
from PIL import Image

from protocol import WIDTH, HEIGHT

METHOD = 'float32-premult-lanczos; single-final-straight-rgba8-quantization'


def validate(pixels):
    a = np.asarray(pixels, dtype=np.float64)
    if (a.ndim != 3 or a.shape[2] != 4 or min(a.shape[:2]) < 1
            or not np.isfinite(a).all() or a.min() < -1e-7
            or a[..., 3].max() > 255+1e-7
            or np.any(a[..., :3] > a[..., 3:4]+1e-7)):
        raise ValueError('Terminal input must be finite premultiplied RGBA in 0..255')
    return a


def legacy(pixels, size=(WIDTH, HEIGHT)):
    """The actual existing uint8 straight -> uint8 associated -> resize route."""
    straight = validate(pixels).copy()
    np.divide(straight[..., :3]*255, straight[..., 3:4], out=straight[..., :3],
              where=straight[..., 3:4] > 0)
    straight[straight[..., 3] == 0, :3] = 0
    high = Image.fromarray(np.clip(np.rint(straight), 0, 255).astype(np.uint8))
    result = np.asarray(high.convert('RGBa').resize(size, Image.Resampling.LANCZOS).convert('RGBA')).copy()
    result[result[..., 3] == 0, :3] = 0
    return Image.fromarray(result)


def constrain(filtered):
    """Bound Lanczos overshoot before unassociation, not a source threshold."""
    a = np.asarray(filtered, dtype=np.float64).copy()
    a[..., 3] = np.clip(a[..., 3], 0, 255)
    a[..., :3] = np.clip(a[..., :3], 0, a[..., 3:4])
    return a


def rgba8(filtered):
    a = constrain(filtered)
    np.divide(a[..., :3]*255, a[..., 3:4], out=a[..., :3], where=a[..., 3:4] > 0)
    result = np.clip(np.rint(a), 0, 255).astype(np.uint8)
    result[result[..., 3] == 0, :3] = 0
    return Image.fromarray(result)


def filtered_float(pixels, size=(WIDTH, HEIGHT)):
    a = validate(pixels)
    # Pillow's F mode retains floating samples at both separable filter passes.
    planes = [np.asarray(Image.fromarray(a[..., i].astype(np.float32)).resize(
        size, Image.Resampling.LANCZOS), dtype=np.float64) for i in range(4)]
    return np.stack(planes, axis=-1)


def floating(pixels, size=(WIDTH, HEIGHT)):
    return rgba8(filtered_float(pixels, size))


@lru_cache(maxsize=16)
def coefficients(source, destination):
    if (type(source) is not int or type(destination) is not int
            or source < 1 or destination < 1):
        raise ValueError('Positive integer filter dimensions required')
    scale = source/destination
    support_scale = max(scale, 1.)
    rows = []
    for i in range(destination):
        center = (i+.5)*scale
        start = max(0, int(center-3*support_scale+.5))
        stop = min(source, int(center+3*support_scale+.5))
        u = (np.arange(start, stop, dtype=np.float64)+.5-center)/support_scale
        weights = np.sinc(u)*np.sinc(u/3)
        weights[np.abs(u) >= 3] = 0
        weights /= weights.sum()
        weights.flags.writeable = False
        rows.append((start, stop, weights))
    return tuple(rows)


def reference64(pixels, size=(WIDTH, HEIGHT)):
    """Independent NumPy separable float64 sum; not Pillow's F output reused."""
    a = validate(pixels)
    horizontal = np.empty((a.shape[0], size[0], 4), dtype=np.float64)
    for i, (start, stop, weights) in enumerate(coefficients(a.shape[1], size[0])):
        horizontal[:, i] = (a[:, start:stop]*weights[None, :, None]).sum(axis=1)
    result = np.empty((size[1], size[0], 4), dtype=np.float64)
    for i, (start, stop, weights) in enumerate(coefficients(a.shape[0], size[1])):
        result[i] = (horizontal[start:stop]*weights[:, None, None]).sum(axis=0)
    return result


def composite_error(image, reference):
    """Display-colour error versus the unquantized reference, in 8-bit units.

    Straight RGB alone exaggerates low-alpha errors. Composite onto both black
    and white, retaining separate mean/max and alpha measurements.
    """
    p = np.asarray(image, dtype=np.float64)
    a = p[..., 3:4]/255
    actual = p[..., :3]*a
    expected = constrain(reference)
    errors = [np.abs(actual+bg*(1-a) -
        (expected[..., :3]+bg*(1-expected[..., 3:4]/255))) for bg in (0, 255)]
    error = np.stack(errors)
    return dict(compositedMeanAbsoluteError=float(error.mean()),
                compositedMaximumAbsoluteError=float(error.max()),
                alphaMeanAbsoluteError=float(np.abs(p[..., 3]-expected[..., 3]).mean()),
                alphaMaximumAbsoluteError=float(np.abs(p[..., 3]-expected[..., 3]).max()))
