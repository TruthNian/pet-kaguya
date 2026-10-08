"""Inspect neutral decomposition and one alternating step before adoption."""
from PIL import Image,ImageDraw

from canonical import ROOT
from leg_material import inputs,composite
from review_waiting import grid
from review_wave import native_frame

OUT = ROOT/'candidates/phase5/locomotion-inspection'


def main():
    data = inputs()
    OUT.mkdir(parents=True,exist_ok=True)
    poses = [data['mother'],composite(data,[(0,0),(0,0)]),
             composite(data,[(5,-7.5),(0,0)]),composite(data,[(0,0),(5,-7.5)])]
    labels = ['mother','neutral estimate','left lifted','right lifted']
    for image,label in zip(poses,labels):
        image.save(OUT/(label.replace(' ','-')+'.png'))
    frames = [native_frame(pose) for pose in poses]
    for width in (80,113,192,224):
        height = round(width*208/192)
        board = Image.new('RGB',(4*(width+12),2*(height+28)),'#23252b')
        draw = ImageDraw.Draw(board)
        for row,color in enumerate(('#23252b','#f1f0ee')):
            for index,(frame,label) in enumerate(zip(frames,labels)):
                tile = Image.new('RGBA',frame.size,color);tile.alpha_composite(frame)
                x,y = index*(width+12),row*(height+28)
                board.paste(tile.resize((width,height),Image.Resampling.NEAREST).convert('RGB'),(x+6,y+24))
                draw.text((x+3,y+3),label,fill='white')
        board.save(OUT/f'contact-{width}px.png')
    for pose,label in zip(poses[1:],labels[1:]):
        grid(pose,(425,925,810,1240)).save(OUT/(label.replace(' ','-')+'-grid.png'))
    print('original / neutral estimate / alternating step proof boards; not accepted motion')


if __name__ == '__main__':
    main()
