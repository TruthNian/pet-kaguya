"""Read-only source inspection; crops never become replacement artwork."""
import json
import numpy as np
from PIL import Image, ImageDraw
from canonical import ROOT, load_canonical
import review_waiting_sleeve as cloth
import review_waiting as hand_art


def board(images, box, scale, background):
    width, height = box[2] - box[0], box[3] - box[1]
    result = Image.new('RGB', (len(images) * width * scale, height * scale + 30), '#252830')
    draw = ImageDraw.Draw(result)
    for index, (label, source) in enumerate(images):
        tile = Image.new('RGBA', (width, height), background)
        tile.alpha_composite(source.crop(box))
        result.paste(tile.convert('RGB').resize((width * scale, height * scale),
                     Image.Resampling.NEAREST), (index * width * scale, 30))
        draw.text((index * width * scale + 6, 8), label, fill='white')
    return result


def main():
    out = ROOT / 'work/waiting-structure-inspection'
    out.mkdir(parents=True, exist_ok=True)
    parent, mapped = cloth.inputs()
    current, _, _, _ = cloth.compose(parent, mapped)
    images = [('locked mother', load_canonical()), ('held hand v1', parent),
              ('current waiting v2', current)]
    mother = np.asarray(images[0][1])
    pixels = np.asarray(current)
    hand = hand_art.masks(hand_art.specification())[2]
    lost = hand & (mother[..., 3] >= 250) & (pixels[..., 3] < 240)
    yy, xx = np.where(lost)
    report = dict(inspectionOnly=True, count=int(lost.sum()),
                  bounds=None if not len(xx) else [int(xx.min()), int(yy.min()),
                                                  int(xx.max()+1), int(yy.max()+1)],
                  pixels=[dict(x=int(x), y=int(y), motherAlpha=int(mother[y,x,3]),
                               currentAlpha=int(pixels[y,x,3])) for x,y in zip(xx,yy)],
                  thresholdIsSemanticSegmentation=False)
    (out / 'hand-alpha-loss.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k!='pixels'}))
    alpha_images = [(label, Image.merge('RGBA', (source.getchannel('A'),)*3+
                          (Image.new('L', source.size, 255),))) for label,source in images]
    board(alpha_images, (475,410,600,580), 3, '#000000').save(out/'contact-alpha.png')
    for name, box, scale in [('contact', (475, 410, 600, 580), 3),
                             ('upper-sleeve', (380, 475, 600, 725), 2)]:
        for theme, color in [('light', '#ededed'), ('dark', '#161a22')]:
            path = out / f'{name}-{theme}.png'
            board(images, box, scale, color).save(path)
            print(path)


if __name__ == '__main__':
    main()
