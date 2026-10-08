from pathlib import Path
from PIL import Image, ImageDraw
from protocol import crop

root = Path(__file__).resolve().parents[1]
atlas = Image.open(root/'baseline/phase2/spritesheet.webp').convert('RGBA')
out = root/'work'
out.mkdir(exist_ok=True)
for row, col in [(0,0),(1,0),(2,0),(3,1),(5,0),(6,0),(7,0)]:
    im = crop(atlas,row,col)
    bg = Image.new('RGBA', im.size, '#23252b')
    bg.alpha_composite(im)
    canvas = bg.resize((768,832), Image.Resampling.NEAREST).convert('RGB')
    d = ImageDraw.Draw(canvas)
    for x in range(0,192,16):
        d.line((x*4,0,x*4,831), fill='#657080')
        d.text((x*4+1,2),str(x),fill='white')
    for y in range(16,208,16):
        d.line((0,y*4,767,y*4),fill='#657080')
        d.text((1,y*4+1),str(y),fill='white')
    canvas.save(out/f'source-r{row}c{col}.png')
