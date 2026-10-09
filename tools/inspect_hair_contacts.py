"""Coordinate evidence only; annotation ink never enters pet assets."""
from PIL import Image, ImageDraw
from canonical import ROOT,load_canonical

OUT = ROOT/'work/hair-contacts'
BOX = (760,570,980,1020)


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    paths = [None,ROOT/'candidates/phase5/review-art-v2/pose.png',
             ROOT/'candidates/phase5/review-hair-v2/harmonic-rgb-pose.png']
    for name,path in zip(['mother','current','unadopted'],paths):
        if path:
            with Image.open(path) as image:
                pose = image.convert('RGBA')
        else:
            pose = load_canonical()
        tile = Image.new('RGBA',(220,450),'#24262b')
        tile.alpha_composite(pose.crop(BOX))
        tile = tile.resize((660,1350),Image.Resampling.NEAREST)
        draw = ImageDraw.Draw(tile)
        for x in range(780,981,20):
            px = (x-BOX[0])*3
            draw.line((px,0,px,1350),fill='#88cccc',width=1)
            draw.text((px+2,3),str(x),fill='white')
        for y in range(580,1021,20):
            py = (y-BOX[1])*3
            draw.line((0,py,660,py),fill='#88cccc',width=1)
            draw.text((2,py+2),str(y),fill='white')
        tile.convert('RGB').save(OUT/f'{name}-grid.png')
    print('inspection-only grids in work/hair-contacts')


if __name__ == '__main__':
    main()
