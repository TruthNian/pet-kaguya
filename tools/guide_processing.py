"""Face-free arm guide for a quiet, attentive processing pose."""
from PIL import ImageDraw
from canonical import ROOT,load_canonical
from review_arm_backing import localized_backing,load_generated,specification

OUT=ROOT/'candidates/phase5/processing-art-v1'
BOX=(250,500,550,1000)


def main():
    mother=load_canonical()
    plate,_=localized_backing(mother,load_generated(),specification())
    guide=plate.crop(BOX)
    draw=ImageDraw.Draw(guide)
    draw.line([(195,85),(135,245),(207,205),(237,177)],fill='#00bbff',width=7)
    draw.rounded_rectangle((196,140,276,215),radius=16,outline='#00bbff',width=7)
    OUT.mkdir(parents=True,exist_ok=True)
    guide.save(OUT/'guide.png')
    mother.crop(BOX).save(OUT/'relaxed-reference.png')


if __name__=='__main__':
    main()
