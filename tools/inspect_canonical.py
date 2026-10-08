"""Coordinate inspection of the accepted source; never modifies it."""
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from canonical import load_canonical, clean_cutout, static_frame, camera

ROOT = Path(__file__).resolve().parents[1]


def main():
    original = load_canonical()
    clean, cleanup = clean_cutout(original)
    out = ROOT/'work/canonical-inspection'
    out.mkdir(parents=True, exist_ok=True)
    font = ImageFont.load_default(size=13)
    for name, box in [('left-arm', (250, 500, 560, 1000)),
                      ('right-arm', (650, 500, 950, 1000)),
                      ('legs-shoes', (425, 880, 780, 1250))]:
        canvas = Image.new('RGBA', original.size, '#23252b')
        canvas.alpha_composite(original)
        draw = ImageDraw.Draw(canvas)
        for x in range(box[0]//25*25, box[2], 25):
            draw.line((x, box[1], x, box[3]), fill='#607277', width=1)
            draw.text((x+1, box[1]+1), str(x), font=font, fill='white')
        for y in range(box[1]//25*25, box[3], 25):
            draw.line((box[0], y, box[2], y), fill='#607277', width=1)
            draw.text((box[0]+1, y+1), str(y), font=font, fill='white')
        canvas.crop(box).convert('RGB').save(out/f'{name}.png')
    board = Image.new('RGB', (424, 472), '#23252b')
    draw = ImageDraw.Draw(board)
    for i, image in enumerate((original, clean)):
        frame = static_frame(image, camera(clean))
        for row, background in enumerate(('#23252b', '#f1f0ee')):
            tile = Image.new('RGBA', frame.size, background)
            tile.alpha_composite(frame)
            board.paste(tile.convert('RGB'), (i*212+10, row*236+24))
        draw.text((i*212+8, 4), ['unchanged artwork', 'alpha-dust cleanup'][i], fill='white')
    board.save(out/'cleanup-comparison.png')
    print(json.dumps(dict(cleanup=cleanup, camera=camera(clean)), indent=2))


if __name__ == '__main__':
    main()
