"""Face-free two-hand review guide; geometry marks are never pet pixels."""
import sys
from PIL import Image,ImageDraw

from canonical import ROOT
from arm_material import localized_arm_pose,project_fixed_crop
from review_processing import inputs
from review_waiting import grid

OUT = ROOT/'candidates/phase5/review-art-v1'
BOX = (450,500,970,1010)


def base_pose():
    mother,spec,generated = inputs()
    return localized_arm_pose(mother,generated,spec)[0]


def main():
    base = base_pose()
    if '--inspect-generated' in sys.argv:
        with Image.open(OUT/'generated.png') as image:
            mapped = project_fixed_crop(base,image.convert('RGBA'),[1266,1242],BOX)
        diagnostic = ROOT/'work/review-inspection'
        diagnostic.mkdir(parents=True,exist_ok=True)
        grid(base,(450,500,975,1005)).save(diagnostic/'base-grid.png')
        grid(mapped,(450,500,975,1005)).save(diagnostic/'raw-grid.png')
        grid(base,(585,630,755,820)).resize((510,570),Image.Resampling.NEAREST).save(diagnostic/'source-cords-grid.png')
        return
    reference = base.crop(BOX)
    guide = reference.copy()
    draw = ImageDraw.Draw(guide)
    draw.line([(310,85),(350,285),(145,245),(82,213)],fill='#00bbff',width=7)
    draw.rounded_rectangle((33,178,126,248),radius=16,outline='#00bbff',width=6)
    # A small crossed marker indicates the obsolete outward right hand.
    draw.line([(404,233),(450,275)],fill='#aa55ff',width=5)
    draw.line([(450,233),(404,275)],fill='#aa55ff',width=5)
    OUT.mkdir(parents=True,exist_ok=True)
    guide.save(OUT/'guide.png')
    reference.save(OUT/'reference.png')
    print('review guide: fixed 520x510 source crop, no head/face included')


if __name__ == '__main__':
    main()
