"""Bounded geometry candidate from the SAME v2 pixels, not a donor face.

The user accepted programmatic generation/processing of animation assets.
ImageGen's three edits did not give reliable local geometry. This isolated
candidate is not animated or installed, and still requires visual approval.
"""
from pathlib import Path
import hashlib
import json

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT/'candidates/phase4/canonical-v2/artwork.png'
OUT = ROOT/'candidates/phase4/canonical-local-jaw'
SOURCE_SHA = 'A627FC599B76025E767682991027AAA3A0E96DF26465C86BD5E077E65A39394A'
REGION = (455, 388, 775, 460)
CENTER_X = 615.
AMOUNT = .08


def smoothstep(value):
    t = np.clip(value, 0., 1.)
    return t*t*(3.-2.*t)


def horizontal_map(x, y, amount=AMOUNT):
    # Zero at all support boundaries; zero in the mouth/short-chin centre.
    vertical = smoothstep((y-388)/20)*smoothstep((460-y)/18)
    exterior = smoothstep((x-455)/25)*smoothstep((775-x)/25)
    side = smoothstep((np.abs(x-CENTER_X)-65)/45)
    return x + (x-CENTER_X)*amount*vertical*exterior*side


def refine(image, amount=AMOUNT):
    if image.size != (1205, 1305):
        raise ValueError('Coordinates are authored only for the unchanged v2 canvas')
    pixels = np.asarray(image.convert('RGBA'))
    result = pixels.copy()
    x0, y0, x1, y1 = REGION
    yy, xx = np.mgrid[y0:y1, x0:x1].astype(float)
    source_x = horizontal_map(xx, yy, amount)
    affected = np.abs(source_x-xx) > 1e-8
    left = np.floor(source_x).astype(int)
    fraction = (source_x-left)[..., None]
    # Premultiplied interpolation only within the authored support. Untouched
    # pixels are copied EXACTLY: no whole-image resize, recolor or re-encoding.
    a = pixels[yy.astype(int), left].astype(float)
    b = pixels[yy.astype(int), left+1].astype(float)
    a[..., :3] *= a[..., 3:4]/255
    b[..., :3] *= b[..., 3:4]/255
    sample = a*(1-fraction)+b*fraction
    np.divide(sample[..., :3]*255, sample[..., 3:4],
              out=sample[..., :3], where=sample[..., 3:4] > 0)
    sample[sample[..., 3] == 0, :3] = 0
    replacement = np.clip(np.rint(sample), 0, 255).astype(np.uint8)
    result[y0:y1, x0:x1][affected] = replacement[affected]
    # Check the local inverse map has no fold. This does not certify anatomy.
    derivative = horizontal_map(xx+.01, yy, amount)-horizontal_map(xx-.01, yy, amount)
    min_derivative = float((derivative/.02).min())
    if min_derivative <= 0:
        raise ValueError('Invalid folded geometry')
    return Image.fromarray(result), dict(sourceSha256=SOURCE_SHA,
        canvasSize=list(image.size), authoredSupport=list(REGION),
        inverseHorizontalExpansion=amount, verticalDisplacement=0,
        protectedCentralBand=[550, 680], minimumSampledHorizontalJacobian=min_derivative,
        maxHorizontalSampleDisplacement=float(np.abs(source_x-xx).max()),
        method='same v2 pixels, bounded smooth horizontal inverse map, premultiplied bilinear interpolation',
        requestedScope='reduce lower-cheek fullness; preserve soft short chin, eyes, mouth and costume',
        actualScope='lower face sides and immediately adjacent hair boundary only',
        generatedArtwork=False, donorCompositing=False, globallyResampled=False,
        visualApproval='rejected: user chose the generated illustration and stopped programmatic face correction',
        rejectionReason='local fields kinked hair boundaries; positive Jacobian did not imply visual correctness',
        adoptedForAnimation=False, installed=False)


def main():
    digest = hashlib.sha256(TARGET.read_bytes()).hexdigest().upper()
    if digest != SOURCE_SHA:
        raise ValueError('Mother-pose source changed')
    refined, metadata = refine(Image.open(TARGET).convert('RGBA'))
    OUT.mkdir(parents=True, exist_ok=True)
    refined.save(OUT/'artwork.png')
    (OUT/'build.json').write_text(json.dumps(metadata, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(metadata, indent=2))


if __name__ == '__main__':
    raise SystemExit('Rejected experiment: facial geometry is locked. Do not use this as a production builder.')
