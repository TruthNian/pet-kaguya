"""Face-free structural edit input; guide ink never enters the pet atlas."""
from PIL import Image, ImageDraw

from canonical import ROOT,load_canonical

OUT = ROOT/'candidates/phase5/review-structure-v1'
BOX = (300,500,960,1040)


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    with Image.open(ROOT/'candidates/phase5/review-art-v3/pose.png') as image:
        current = image.convert('RGBA')
    reference = current.crop(BOX)
    mother = load_canonical().crop(BOX)
    reference.save(OUT/'reference.png')
    mother.save(OUT/'mother-style.png')
    guide = reference.copy()
    draw = ImageDraw.Draw(guide)
    # The edit locations are explanatory envelopes, not foreground mattes.
    for polygon in (
        [(341,605),(443,594),(477,642),(517,645),(521,704),(475,730),
         (444,760),(409,833),(388,867),(351,816),(321,750),(306,705)],
        [(724,604),(764,594),(793,671),(811,705),(808,752),(829,818),
         (846,871),(835,897),(809,920),(762,882),(731,846),(697,826),
         (650,789),(615,767),(602,732),(560,730),(520,725),(498,698),
         (507,683),(545,673),(571,685),(598,699),(638,677),(683,659),
         (712,643),(737,642)]):
        draw.line([(x-BOX[0],y-BOX[1]) for x,y in polygon+[polygon[0]]],fill='#00bbff',width=3)
    guide.save(OUT/'guide.png')
    print('660x540 fixed source crop; head and face are absent; no atlas changes')


if __name__ == '__main__':
    main()
