"""Shared native-row presentation output; never an installable full atlas."""
from PIL import Image, ImageDraw

from protocol import WIDTH, HEIGHT


def write_animation(out, frames, durations, repeat_columns=None):
    if len(frames) != len(durations) or len(frames) > 8:
        raise ValueError('Native row poses/holds mismatch')
    out.mkdir(parents=True, exist_ok=True)
    strip = Image.new('RGBA', (WIDTH*8, HEIGHT))
    for index, frame in enumerate(frames):
        frame.save(out/f'frame-{index}.png')
        strip.paste(frame, (index*WIDTH, 0))
    for column, source in (repeat_columns or {}).items():
        strip.paste(frames[source], (column*WIDTH, 0))
    strip.save(out/'strip.webp', lossless=True, exact=True, method=6)
    for width in (80, 113, 192, 224):
        height = round(width*HEIGHT/WIDTH)
        board = Image.new('RGB', (len(frames)*(width+12), 2*(height+28)), '#23252b')
        draw = ImageDraw.Draw(board)
        for row, background in enumerate(('#23252b', '#f1f0ee')):
            for index, frame in enumerate(frames):
                tile = Image.new('RGBA', frame.size, background)
                tile.alpha_composite(frame)
                x, y = index*(width+12), row*(height+28)
                board.paste(tile.resize((width, height), Image.Resampling.NEAREST).convert('RGB'), (x+6, y+24))
                draw.text((x+3, y+3), f'{index}: {durations[index]} ms', fill='white')
        board.save(out/f'contact-{width}px.png')
    # GIF is an opaque, palette-quantized QA view, not source/atlas pixels.
    displays = []
    for frame in frames:
        tile = Image.new('RGBA', frame.size, '#23252b')
        tile.alpha_composite(frame)
        displays.append(tile.convert('RGB'))
    displays[0].save(out/'native-timing.gif', save_all=True, append_images=displays[1:],
                     duration=durations, loop=0, disposal=2)
