"""Inspect the hand-contact boundary; coordinate labels are not pet pixels."""
from PIL import Image,ImageDraw
from canonical import ROOT
from review_hand import inputs
from review_review_v2 import inputs as original_inputs
from review_review_v2 import localized_pose as original_compose
import numpy as np


def main():
    parent,background=inputs()
    base,spec,mapped=original_inputs()
    _,allowed,preserved=original_compose(base,mapped,spec)
    with Image.open(ROOT/'candidates/phase5/review-hand-v2/pose.png') as image:
        compact=image.convert('RGBA')
    box=(480,660,570,740);scale=5
    board=Image.new('RGB',(4*450,430),'#23252b');draw=ImageDraw.Draw(board)
    for i,(image,label) in enumerate(zip([background,mapped,parent,compact],
            ['existing pre-hand plate','original mapped right art','current v3','conditioned compact'])):
        tile=Image.new('RGBA',(450,400),'#23252b')
        tile.alpha_composite(image.crop(box).resize((450,400),Image.Resampling.NEAREST))
        board.paste(tile.convert('RGB'),(450*i,30));draw.text((450*i+5,7),label,fill='white')
        for x in range(480,570,10):
            draw.line((450*i+(x-480)*scale,30,450*i+(x-480)*scale,430),fill='#999999')
            draw.text((450*i+(x-480)*scale+2,32),str(x),fill='#222222')
        for y in range(660,740,10):
            draw.line((450*i,30+(y-660)*scale,450*i+450,30+(y-660)*scale),fill='#999999')
            draw.text((450*i+2,32+(y-660)*scale),str(y),fill='#222222')
    path=ROOT/'work/review-joint/contact-grid.png';path.parent.mkdir(parents=True,exist_ok=True)
    board.save(path)
    a,r=np.asarray(parent),np.asarray(mapped)
    # Inspect only the lower hand, not the generally changed raw crop.
    rows=[]
    for y in range(680,735):
        for x in range(490,608):
            rgb=r[y,x,:3].astype(int)
            skin=(rgb[0]>160 and rgb[1]>145 and rgb[2]>120
                  and 0<=rgb[0]-rgb[1]<55 and 0<=rgb[1]-rgb[2]<50)
            if skin and not np.array_equal(a[y,x],r[y,x]):
                rows.append((x,y,'preserved' if preserved[y,x] else 'outside' if not allowed[y,x] else 'inside'))
    for kind in ('preserved','outside','inside'):
        points=[(x,y) for x,y,k in rows if k==kind]
        if points:print(kind,len(points),'bounds',min(x for x,y in points),min(y for x,y in points),max(x for x,y in points),max(y for x,y in points))
    for x,y in [(499,699),(503,704),(506,709),(518,718),(527,725),(536,727)]:
        print((x,y),'current',tuple(a[y,x]),'raw',tuple(r[y,x]),'allowed',bool(allowed[y,x]),'preserved',bool(preserved[y,x]))
    print(path)


if __name__=='__main__':main()
