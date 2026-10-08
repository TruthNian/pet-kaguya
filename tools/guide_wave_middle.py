"""Face-free arm crop: visually explicit half-lowered hand edit target."""
from PIL import Image, ImageDraw
from canonical import ROOT,load_canonical
from review_arm_backing import localized_backing,load_generated,specification

OUT = ROOT/'candidates/phase5/wave-art-middle-v2'
BOX = (250,500,550,1000)


def main():
    mother=load_canonical()
    plate,_=localized_backing(mother,load_generated(),specification())
    guide=plate.crop(BOX)
    draw=ImageDraw.Draw(guide)
    draw.line([(195,85),(135,310),(105,270),(90,215)],fill='#00bbff',width=7)
    draw.rounded_rectangle((46,165,137,255),radius=16,outline='#00bbff',width=7)
    OUT.mkdir(parents=True,exist_ok=True)
    guide.save(OUT/'guide.png')
    with Image.open(ROOT/'candidates/phase5/wave-art-v2/pose.png') as peak:
        peak.crop(BOX).save(OUT/'peak-reference.png')
    mother.crop(BOX).save(OUT/'relaxed-reference.png')


if __name__=='__main__':
    main()
