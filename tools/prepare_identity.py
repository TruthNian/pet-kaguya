"""Inspectable pre-expression sources; no input mutates and no subject fitting."""
from pathlib import Path
import hashlib
import json

from PIL import Image, ImageDraw
from protocol import WIDTH, HEIGHT, crop

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT/'sources/pre-expression/spritesheet.webp'
SOURCE_HASH = '9A56A238A4D8656E11D30D5183735A5A4CEBF5854E22B53879520E6BF222146D'


def load_source():
    if hashlib.sha256(SOURCE.read_bytes()).hexdigest().upper() != SOURCE_HASH:
        raise ValueError('Pre-expression source hash changed')
    return Image.open(SOURCE).convert('RGBA')


def main():
    atlas = load_source()
    out = ROOT/'work/identity'
    out.mkdir(parents=True, exist_ok=True)
    anchors = [(0,i) for i in range(6)] + [(5,0),(6,0),(7,0),(7,1),(8,0),(8,3)]
    panel = Image.new('RGB',(6*352,2*344),'#23252b')
    draw = ImageDraw.Draw(panel)
    for i,(row,col) in enumerate(anchors):
        image = crop(atlas,row,col)
        image.save(out/f'r{row}c{col}.png')
        region = image.crop((52,20,140,100))
        bg = Image.new('RGBA',region.size,'#23252b')
        bg.alpha_composite(region)
        x,y=(i%6)*352,(i//6)*344
        panel.paste(bg.resize((352,320),Image.Resampling.NEAREST).convert('RGB'),(x,y+24))
        draw.text((x+3,y+3),f'original r{row}c{col}',fill='white')
    panel.save(out/'source-faces.png')
    for row,count in [(3,4),(8,6)]:
        body=Image.new('RGB',(count*WIDTH*2,HEIGHT*2+24),'#23252b')
        d=ImageDraw.Draw(body)
        for col in range(count):
            im=crop(atlas,row,col)
            bg=Image.new('RGBA',im.size,'#23252b')
            bg.alpha_composite(im)
            body.paste(bg.resize((WIDTH*2,HEIGHT*2),Image.Resampling.NEAREST).convert('RGB'),(col*WIDTH*2,24))
            d.text((col*WIDTH*2+3,3),f'original r{row}c{col}',fill='white')
        body.save(out/f'body-r{row}.png')
    # Coordinates, not independently fitted crops, are needed to align features.
    for row,col in [(0,0),(7,0),(7,1)]:
        bg = Image.new('RGBA',(WIDTH,HEIGHT),'#23252b')
        bg.alpha_composite(crop(atlas,row,col))
        board = bg.resize((WIDTH*5,HEIGHT*5),Image.Resampling.NEAREST).convert('RGB')
        d = ImageDraw.Draw(board)
        for xx in range(50,141,5):
            d.line((xx*5,0,xx*5,HEIGHT*5),fill='#6d7577',width=1)
            d.text((xx*5+1,10),str(xx),fill='white')
        for yy in range(30,91,5):
            d.line((0,yy*5,WIDTH*5,yy*5),fill='#6d7577',width=1)
            d.text((10,yy*5+1),str(yy),fill='white')
        board.save(out/f'coordinates-r{row}c{col}.png')
    print(json.dumps({'sourceSha256':SOURCE_HASH,'preview':'work/identity/source-faces.png'}))


if __name__ == '__main__':
    main()
