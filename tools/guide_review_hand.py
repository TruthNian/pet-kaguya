"""A narrower edit target: compact palm, fixed current wrist and left hand."""
from PIL import Image,ImageDraw
from canonical import ROOT

OUT = ROOT/'candidates/phase5/review-hand-v1'
BOX = (490,650,640,780)


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    with Image.open(ROOT/'candidates/phase5/review-art-v3/pose.png') as image:
        parent = image.convert('RGBA')
    reference = parent.crop(BOX)
    reference.save(OUT/'reference.png')
    guide = reference.copy()
    draw = ImageDraw.Draw(guide)
    draw.ellipse((24,34,114,80),outline='#00bbff',width=2)
    draw.line((114,64,114,80),fill='#aa55ff',width=3)
    guide.save(OUT/'guide.png')
    print('150x130 source crop; guide oval indicates compact hand, purple fixed wrist; no face')


if __name__ == '__main__':
    main()
