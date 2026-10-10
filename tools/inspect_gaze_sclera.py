"""Bounded original-pixel diagnosis; no candidate/global/installed files written."""
import json
import numpy as np
from PIL import Image,ImageDraw
import build_gaze as gaze
from canonical import ROOT,clean_cutout
from build_idle import render

OUT=ROOT/'work/gaze-sclera-inspection'
FACE=(420,235,805,410)

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    source,generated,spec,old,transform,regions,masks=gaze.inputs(corrected=False)
    geometry=Image.new('RGB',(1050,525),'#ededed');gd=ImageDraw.Draw(geometry)
    for eye_i,eye in enumerate(spec['eyes']):
        x0,y0,x1,y1=eye['box'];ox=eye_i*525;oy=30
        crop=source.crop(eye['box']).resize(((x1-x0)*4,(y1-y0)*4),Image.Resampling.NEAREST)
        geometry.paste(crop.convert('RGB'),(ox,oy))
        for x in range(((x0+9)//10)*10,x1,10):
            px=ox+(x-x0)*4;gd.line((px,oy,px,oy+(y1-y0)*4),fill='#b4b1aa');gd.text((px+1,10),str(x),fill='#111111')
        for y in range(((y0+9)//10)*10,y1,10):
            py=oy+(y-y0)*4;gd.line((ox,py,ox+(x1-x0)*4,py),fill='#b4b1aa');gd.text((ox+1,py+1),str(y),fill='#444444')
    geometry.save(OUT/'source-geometry.png')
    corrected_spec=gaze.specification(corrected=True)
    new=gaze.layers(source,generated,corrected_spec)
    if gaze.pose(source,new,0,0).tobytes()!=source.tobytes():
        raise ValueError('Corrected eye opening cannot change neutral mother pixels')
    board=Image.new('RGB',(3*385,5*200),'#ededed');draw=ImageDraw.Draw(board)
    a=np.asarray(source);allowed=gaze.aperture_union(source,new)
    rows=[]
    for row,index in enumerate((0,4,8,12)):
        old_pose=gaze.pose(source,old,*gaze.offsets(index,spec))
        new_pose=gaze.pose(source,new,*gaze.offsets(index,spec))
        b=np.asarray(new_pose)
        if np.any(np.any(a!=b,axis=2)&~allowed) or not np.array_equal(a[...,3],b[...,3]):
            raise ValueError('Classification changed alpha or outside the corrected eye openings')
        for col,(label,pose) in enumerate((('mother',source),('legacy v1',old_pose),('observed opening',new_pose))):
            board.paste(pose.crop(FACE).convert('RGB'),(col*385,row*200+25))
            draw.text((col*385+5,row*200+5),f'{index}: {label}',fill='#222222')
        rows.append(dict(direction=index,sourceEyeRGBPixelsChanged=int(np.any(np.asarray(old_pose)!=b,axis=2).sum())))
    old_down=gaze.pose(source,old,0,7);new_down=gaze.pose(source,new,0,7)
    native_tiles=[]
    for col,(label,pose) in enumerate((('mother',source),('legacy down',old_down),('new down',new_down))):
        native=render(clean_cutout(pose)[0],dict(bodyY=0,earAngle=0,hairAngle=0),transform,regions,masks)
        tile=Image.new('RGBA',native.size,'#ededed');tile.alpha_composite(native)
        native_tile=tile.resize((160,173),Image.Resampling.NEAREST).convert('RGB')
        native_tiles.append(native_tile)
        board.paste(native_tile,(col*385+110,825))
        draw.text((col*385+5,805),label+' native 160px',fill='#222222')
    board.save(OUT/'comparison.png')
    stats=[]
    for before,after in zip(old,new):
        added=after['knownSclera']&~before['knownSclera']
        stats.append(dict(eye=before['eye']['name'],newFixedScleraPixels=int(added.sum()),
            newlyFixedRGBMin=int(before['original'][added,:3].min()) if added.any() else None))
    protected_points=[]
    for point in ((550,380),(683,370)):
        if new_down.getpixel(point)!=source.getpixel(point):raise ValueError('Known lower-eye skin pixel moved')
        protected_points.append(dict(sourcePoint=point,mother=source.getpixel(point),legacyDown=old_down.getpixel(point),correctedDown=new_down.getpixel(point)))
    report=dict(neutralRGBAExact=True,onlyEyeRGBChanged=True,installedOrAtlasWritten=False,directions=rows,eyes=stats,protectedLowerSkin=protected_points)
    proof=Image.new('RGB',(1155,410),'#ededed');pd=ImageDraw.Draw(proof)
    for col,(label,pose) in enumerate((('mother',source),('before: down',old_down),('corrected: down',new_down))):
        proof.paste(pose.crop(FACE).convert('RGB'),(col*385,25))
        pd.text((col*385+5,5),label,fill='#222222')
        proof.paste(native_tiles[col],(col*385+110,223))
    proof.save(OUT/'skin-boundary-proof.png')
    (OUT/'report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report))

if __name__=='__main__':main()
