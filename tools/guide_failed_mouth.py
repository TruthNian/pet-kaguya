"""Fixed-coordinate mouth-only editing inputs; no face/eye/jaw input."""
import hashlib
import json
import numpy as np
from PIL import Image
from canonical import ROOT, ACCEPTED_SHA, load_canonical
import review_failed

OUT = ROOT / 'candidates/phase5/failed-mouth-v2'
BOX = (570, 370, 670, 430)
SIDE = 100


def parent():
    mother = load_canonical()
    pose, _ = review_failed.localized_pose(mother, review_failed.load_generated(),
                                          review_failed.specification())
    meta = json.loads((review_failed.OUT / 'build.json').read_text(encoding='utf-8'))
    if hashlib.sha256(pose.tobytes()).hexdigest().upper() != meta['poseRGBAHash']:
        raise ValueError('Failed-expression parent does not match the saved actual pose')
    return pose


def square(image):
    result = Image.new('RGBA', (SIDE, SIDE))
    result.paste(image.crop(BOX), (0, 0))
    return result


def line_diagnostic(image):
    # Only a descriptive threshold inside an inspected mouth rectangle.
    # Never used to select pixels for editing or establish aesthetic quality.
    pixels = np.asarray(image)[383:419, 582:650].astype(int)
    selected = (pixels[...,0] < 210) & (pixels[...,1] < 150) & (pixels[...,2] < 150)
    yy, xx = np.where(selected)
    return dict(thresholdDefinesEditMask=False, thresholdIsBeautyScore=False,
                count=int(selected.sum()), bounds=None if not len(xx) else
                [int(xx.min()+582),int(yy.min()+383),int(xx.max()+583),int(yy.max()+384)])


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    mother, pose = load_canonical(), parent()
    square(pose).save(OUT / 'edit-guide.png')
    square(mother).save(OUT / 'width-reference.png')
    metadata = dict(sourceSha256=ACCEPTED_SHA,
                    parentPoseRGBAHash=hashlib.sha256(pose.tobytes()).hexdigest().upper(),
                    crop=list(BOX), squareCanvas=[SIDE,SIDE], bottomTransparentPx=40,
                    eyeJawOrWholeFaceIncluded=False,
                    motherMouthLineDiagnostic=line_diagnostic(mother),
                    currentFrownLineDiagnostic=line_diagnostic(pose),
                    diagnosticIsSemanticSelection=False,
                    intention='slightly disappointed closed mouth with original smile-line width; '
                              'no eyes, brows, cheeks, jaw, camera, alpha or body changes',
                    visualAcceptance='pending', adopted=False, installed=False)
    (OUT / 'guide.json').write_text(json.dumps(metadata, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(metadata, indent=2))


if __name__ == '__main__':
    main()
