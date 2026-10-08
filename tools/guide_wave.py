"""Explicit low-arm pose guide, never rendered as a pet frame."""
from PIL import Image, ImageDraw

from canonical import ROOT, load_canonical
from review_arm_backing import localized_backing, load_generated, specification


def main():
    mother = load_canonical()
    plate,_ = localized_backing(mother,load_generated(),specification())
    guide = plate.copy()
    draw = ImageDraw.Draw(guide)
    shoulder,elbow,wrist,palm = [(445,585),(385,745),(342,700),(315,650)]
    draw.line([shoulder,elbow,wrist,palm],fill='#00bbff',width=9)
    for x,y in (shoulder,elbow,wrist):
        draw.ellipse((x-9,y-9,x+9,y+9),fill='#00bbff')
    # The palm/fingers use geometry only; not substitute production artwork.
    draw.rounded_rectangle((286,601,356,691),radius=19,outline='#00bbff',width=8)
    target = ROOT/'candidates/phase5/wave-art-v2'
    target.mkdir(parents=True,exist_ok=True)
    guide.save(target/'guide.png')


if __name__=='__main__':
    main()
