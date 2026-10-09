"""Fixed, face-free edit context for missing right hair behind the old sleeve."""
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from canonical import ROOT, load_canonical
from review_review_v2 import inputs, localized_pose

OUT = ROOT/'candidates/phase5/review-hair-v1'
BOX = (680,540,1000,1020)
# Illustrative guide only. Adoption gets a separate, validated permission;
# guide ink is never composited into the pet.
HAIR = [(795,580),(782,611),(798,639),(818,663),(828,695),(826,738),
        (834,790),(846,832),(860,869),(855,905),(839,926),(814,940),
        (787,939),(776,957),(789,981),(821,1000),(885,995),(902,971),
        (916,936),(924,900),(922,859),(923,820),(939,800),(958,775),
        (958,729),(935,710),(935,672),(915,644),(876,614),(824,584)]


def main():
    base,spec,raw = inputs()
    pose = localized_pose(base,raw,spec)[0]
    OUT.mkdir(parents=True,exist_ok=True)
    target = pose.crop(BOX)
    target.save(OUT/'target.png')
    load_canonical().crop(BOX).save(OUT/'mother-reference.png')
    guide = target.copy()
    draw = ImageDraw.Draw(guide)
    points = [(x-BOX[0],y-BOX[1]) for x,y in HAIR]
    draw.line(points+[points[0]],fill='#00bbff',width=3)
    guide.save(OUT/'guide.png')
    revised = ROOT/'candidates/phase5/review-hair-v2'
    revised.mkdir(parents=True,exist_ok=True)
    target.save(revised/'target.png')
    guide.save(revised/'guide.png')
    # Show only actually visible source hair. No old hand or green sleeve
    # survives in this reference, so style guidance cannot restore its pose.
    old = Image.new('L',pose.size)
    ImageDraw.Draw(old).polygon(spec['oldRightArmPolygon'],fill=255)
    old = np.asarray(old.filter(ImageFilter.MaxFilter(9))) > 0
    hair = Image.new('L',pose.size)
    ImageDraw.Draw(hair).rectangle((775,540,1000,1020),fill=255)
    # The upper-left corner contains the source cape, not hair.
    ImageDraw.Draw(hair).rectangle((775,540,835,590),fill=0)
    visible = (np.asarray(hair) > 0) & ~old
    pixels = np.asarray(load_canonical()).copy()
    pixels[~visible] = 0
    Image.fromarray(pixels).crop(BOX).save(revised/'visible-hair-reference.png')
    print('fixed 320x480 context, y>=540 excludes the entire face')


if __name__ == '__main__':
    main()
