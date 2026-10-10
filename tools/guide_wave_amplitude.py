"""Face-free crop for the missing lowered-sleeve connection, not a redraw."""
from canonical import ROOT
from PIL import Image

OUT=ROOT/'candidates/phase5/wave-amplitude-cloth-v1'
BOX=(250,500,550,950)


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    for source,name in [('wave-amplitude-v1/failed-shear-pose.png','guide.png'),
                        ('wave-art-v2/pose.png','reference.png')]:
        with Image.open(ROOT/'candidates/phase5'/source) as image:
            image.convert('RGBA').crop(BOX).save(OUT/name)


if __name__=='__main__':main()
