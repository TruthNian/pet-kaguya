"""Small source-space side-sleeve response; an unadopted motion study.

Compact geometric influence is not a foreground matte. It also bends nearby
visible backing pixels. No hidden layer, measured mass or native interpolation
is claimed; only the already selected frontal eight-hold gait is used.
"""
import hashlib
import json

import numpy as np
from PIL import Image, ImageDraw

from canonical import ROOT, ACCEPTED_SHA
from build_idle import smooth
import build_locomotion as walk
import locomotion_follow as follow
import locomotion_render as renderer
from animation_output import write_animation

OUT = ROOT/'candidates/phase5/cloth-follow-v1'
METHOD = 'compact-side-sleeve-source-field; periodic-held-root-lag'
SPEC = dict(timeConstantMs=190,gain=.25,maximumOffsetSourcePx=2.5,
    sample='native-hold-midpoint',boundary='periodic-steady-state',
    ellipses=[dict(center=[353,915],radii=[69,82]),dict(center=[857,919],radii=[68,78])],
    protectedRects=[[275,20,955,485],[264,705,413,808],[812,705,952,815],
        [395,450,815,936],[400,912,830,1240]],protectionFadeSourcePx=24)


def rgba_hash(frame):
    return hashlib.sha256(frame.tobytes()).hexdigest().upper()


def influence(canvas,spec=SPEC):
    if canvas != [1205,1306] or spec != SPEC:
        raise ValueError('Study may not silently change source or geometric ownership')
    yy,xx = np.mgrid[:canvas[1],:canvas[0]].astype(float)
    weight = np.zeros_like(xx)
    for part in spec['ellipses']:
        cx,cy = part['center'];rx,ry = part['radii']
        radius_squared = ((xx-cx)/rx)**2+((yy-cy)/ry)**2
        # Compact C2 support: no Gaussian tail reaching faces or hands.
        weight = np.maximum(weight,np.maximum(0,1-radius_squared)**3)
    for x0,y0,x1,y1 in spec['protectedRects']:
        distance = np.maximum.reduce([x0-xx,xx-x1,y0-yy,yy-y1,np.zeros_like(xx)])
        weight *= smooth(0,spec['protectionFadeSourcePx'],distance)
    return weight


def response(motion):
    walk.validate_motion(motion)
    value = follow.periodic_lag([p['rootSourcePx'][0] for p in motion['keyframes']],
        motion['durationsMs'],SPEC['timeConstantMs'],SPEC['gain'])
    if max(abs(v) for v in value['offsetsSourcePx'])>SPEC['maximumOffsetSourcePx']:
        raise ValueError('Sleeve response exceeds the restrained source budget')
    return value


def inputs():
    # Keep archived cloth research reproducible without rebuilding it after
    # unrelated eye fixes. It is not a comparison against today's artwork.
    data = walk.inputs(corrected_gaze=False)
    weight = influence([1205,1306]);lag = response(data['motion'])
    results = {}
    for name,result in data['results'].items():
        active = json.loads((ROOT/'sources/reference/gaze-action-v1'/f'{name}.json').read_text(encoding='utf-8'))
        if [rgba_hash(frame) for frame in result['frames']] != active['frameHashes']:
            raise ValueError('Parent must independently reconstruct the frozen study-epoch gait')
        material = dict(result['material'],followFields={**result['material']['followFields'],'cloth':weight})
        frames,keys = [],[]
        for index,key in enumerate(result['renderKeys']):
            trial = dict(key,followSourcePx={**key['followSourcePx'],'cloth':lag['offsetsSourcePx'][index]})
            frames.append(renderer.render(material,trial,result['state']['direction'],data['transform']))
            keys.append(trial)
        differences = []
        for index,(old,new) in enumerate(zip(result['frames'],frames)):
            a,b = np.asarray(old),np.asarray(new)
            yy,xx = np.where(np.any(a!=b,axis=2))
            # Narrow actual output bounds include terminal filter support.
            if not len(xx):raise ValueError('Study produced no actual changed pixels')
            bounds = [int(xx.min()),int(yy.min()),int(xx.max()+1),int(yy.max()+1)]
            if any(y<132 or y>=174 or not (42<=x<71 or 120<=x<153) for x,y in zip(xx,yy)):
                raise ValueError('Study escaped the two inspected lower side regions')
            for box in ((40,117,68,138),(126,117,154,139),(70,80,120,174),(67,174,135,206)):
                x0,y0,x1,y1=box
                if not np.array_equal(a[y0:y1,x0:x1],b[y0:y1,x0:x1]):
                    raise ValueError(f'Actual native hand/front/leg protection failed: {name} slot {index}; {box}')
            differences.append(dict(changedRGBAPixels=int(len(xx)),
                changedRGBPixels=int(np.any(a[...,:3]!=b[...,:3],axis=2).sum()),bounds=bounds,
                maximumChannelDifference=int(np.abs(a.astype(int)-b.astype(int)).max()),
                changedAlphaPixels=int((a[...,3]!=b[...,3]).sum()),
                maximumAlphaDifference=int(np.abs(a[...,3].astype(int)-b[...,3].astype(int)).max())))
        results[name] = dict(parent=active,baseline=result['frames'],frames=frames,keys=keys,
            material=material,differences=differences)
    return dict(data=data,weight=weight,lag=lag,results=results)


def main():
    study = inputs();data=study['data'];OUT.mkdir(parents=True,exist_ok=True)
    receipt = dict(sourceSha256=ACCEPTED_SHA,method=METHOD,spec=SPEC,response=study['lag'],
        camera=data['transform'],durationsMs=data['motion']['durationsMs'],repeatBeforeIdle=3,
        animationBuilt=True,newArtworkGenerated=False,facialGeometryRepair=False,
        nativeInterpolation=False,cleanClothLayersRecovered=False,physicalClothSimulation=False,
        liveDragLagInitialization=False,visualMotionApproval='pending',specificMotionUserApproval='pending',
        adopted=False,activeAtlasChanged=False,installableFullAtlas=False,installed=False,
        maximumOffsetOutputPx=max(abs(v) for v in study['lag']['offsetsSourcePx'])*data['transform']['scale'],
        states={},limitations=['Compact influence bends existing flattened side-sleeve/backing pixels, not an independently recovered garment layer.',
            'Face, head, wrists/hands, waist/front ornaments and the leg material region are excluded geometrically; actual native changes are bounded to two lower side windows.',
            'No new hidden artwork or hem disocclusion is reconstructed. Native alpha may change only inside the same bounded windows; original near-opaque source alpha is sampled, never forced to 255 or pasted back.',
            'Periodic midpoint response is not initialized per live drag and does not fix entry/release or arbitrary task cuts.',
            'Eight original holds, feet, body sway, gaze and ear/hair response are unchanged; native frame rate/size are unchanged.',
            'Naturalness and actual-size visibility need visual judgment; pixel deltas are not quality scores.'])
    for name,result in study['results'].items():
        write_animation(OUT/name,result['frames'],data['motion']['durationsMs'])
        parent=result['parent']
        receipt['states'][name] = dict(nativeRow=parent['nativeRow'],
            parentFrameHashes=parent['frameHashes'],frameHashes=[rgba_hash(f) for f in result['frames']],
            parentSourceSha256=parent['sourceSha256'],rootOffsetsSourcePx=parent['rootOffsetsSourcePx'],
            footOffsetsSourcePx=parent['footOffsetsSourcePx'],focusOffsetSourcePx=parent['focusOffsetSourcePx'],
            tipOffsetsSourcePx=parent['tipOffsetsSourcePx'],
            allNativeAlphaExact=all(d['changedAlphaPixels']==0 for d in result['differences']),
            actualCurrentParentReconstructedExactly=True,differences=result['differences'])
        # Same pose, camera and background, not a translated native bitmap.
        for width in (113,224):
            height=round(width*208/192)
            board=Image.new('RGB',(4*(width+12),2*(height+28)),'#23252b');draw=ImageDraw.Draw(board)
            for row,bg in enumerate(('#23252b','#f1f0ee')):
                for col,(index,label,new) in enumerate(((2,'current peak',False),(2,'trial peak',True),
                                                        (6,'current reverse',False),(6,'trial reverse',True))):
                    tile=Image.new('RGBA',(192,208),bg)
                    tile.alpha_composite(result['frames' if new else 'baseline'][index])
                    board.paste(tile.resize((width,height),Image.Resampling.NEAREST).convert('RGB'),
                        (col*(width+12)+6,row*(height+28)+24))
                    draw.text((col*(width+12)+3,row*(height+28)+3),label,fill='white')
            board.save(OUT/f'{name}-comparison-{width}px.png')
    (OUT/'build.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(output=str(OUT),maximumOffsetOutputPx=receipt['maximumOffsetOutputPx'],
        changedRGBAPixels={name:[d['changedRGBAPixels'] for d in result['differences']] for name,result in study['results'].items()},
        adopted=False),indent=2))


if __name__ == '__main__':main()
