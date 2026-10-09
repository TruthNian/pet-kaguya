"""Aggregate v3 development atlas for global QA, never installation authority."""
import hashlib
import json

from PIL import Image,ImageDraw

from canonical import ROOT,ACCEPTED_SHA,load_canonical,clean_cutout,camera
from protocol import WIDTH,HEIGHT,ATLAS_SIZE,DURATIONS

OUT = ROOT/'candidates/phase5/global'
STATES = ['idle','run_right','run_left','waving','jumping','failed','waiting','processing','review']
REPRESENTATIVE = [0,2,6,1,2,3,3,3,3]


def assemble():
    load_canonical()
    atlas = Image.new('RGBA',ATLAS_SIZE)
    summaries,frames = [],[]
    expected_camera = camera(clean_cutout(load_canonical())[0])
    for row,name in enumerate(STATES):
        folder = ROOT/'candidates/phase5'/name
        metadata = json.loads((folder/'build.json').read_text(encoding='utf-8'))
        if (metadata['sourceSha256'] != ACCEPTED_SHA or metadata['state'] != name
                or metadata['facialGeometryRepair'] or metadata['installableFullAtlas'] or metadata['installed']
                or metadata['camera'] != expected_camera or metadata['durationsMs'] != DURATIONS[row]
                or metadata['visualMotionApproval'] != 'pending'):
            raise ValueError('Global QA cannot aggregate changed sources/timing or imply acceptance')
        with Image.open(folder/'strip.webp') as opened:
            strip = opened.convert('RGBA')
        if strip.size != (1536,208):
            raise ValueError('Wrong action strip dimensions')
        atlas.paste(strip,(0,row*HEIGHT))
        hashes = []
        for index in range(len(DURATIONS[row])):
            frame = strip.crop((index*WIDTH,0,(index+1)*WIDTH,HEIGHT))
            hashes.append(hashlib.sha256(frame.tobytes()).hexdigest().upper())
        if hashes != metadata['frameHashes']:
            raise ValueError('Global QA strip differs from its decoded frame hashes')
        frames.append(strip.crop((REPRESENTATIVE[row]*WIDTH,0,(REPRESENTATIVE[row]+1)*WIDTH,HEIGHT)))
        summaries.append(dict(state=name,nativeRow=row,frameCount=len(DURATIONS[row]),
                              sourceRowRGBAHash=hashlib.sha256(strip.tobytes()).hexdigest().upper(),
                              representativeFrame=REPRESENTATIVE[row],visualMotionApproval='pending'))
    look = ROOT/'candidates/phase5/look'
    metadata = json.loads((look/'build.json').read_text(encoding='utf-8'))
    if (metadata['sourceSha256'] != ACCEPTED_SHA or metadata['directionCount'] != 16
            or metadata['facialGeometryRepair'] or metadata['installableFullAtlas'] or metadata['installed']
            or metadata['camera'] != expected_camera or metadata['visualAcceptance'] != 'pending'):
        raise ValueError('Global QA requires exactly sixteen unapproved v3 gaze cells')
    with Image.open(look/'strip.webp') as opened:
        strip = opened.convert('RGBA')
    if strip.size != (1536,416):
        raise ValueError('Wrong gaze strip dimensions')
    for index in range(16):
        col,row = index%8,index//8
        frame = strip.crop((col*WIDTH,row*HEIGHT,(col+1)*WIDTH,(row+1)*HEIGHT))
        if hashlib.sha256(frame.tobytes()).hexdigest().upper() != metadata['frameHashes'][index]:
            raise ValueError('Global QA gaze strip differs from decoded frame hashes')
    atlas.paste(strip,(0,9*HEIGHT))
    return atlas,summaries,frames,expected_camera


def contact(frames,width):
    height = round(width*HEIGHT/WIDTH)
    board = Image.new('RGB',(3*(width+12),6*(height+28)),'#23252b')
    draw = ImageDraw.Draw(board)
    for background_row,color in enumerate(('#23252b','#f1f0ee')):
        for index,(frame,label) in enumerate(zip(frames,STATES)):
            col,row = index%3,index//3+3*background_row
            x,y = col*(width+12),row*(height+28)
            tile = Image.new('RGBA',frame.size,color);tile.alpha_composite(frame)
            board.paste(tile.resize((width,height),Image.Resampling.NEAREST).convert('RGB'),(x+6,y+24))
            draw.text((x+3,y+3),label,fill='white')
    return board


def main():
    atlas,summaries,frames,transform = assemble()
    OUT.mkdir(parents=True,exist_ok=True)
    atlas.save(OUT/'spritesheet.webp',lossless=True,exact=True,method=6)
    for width in (80,113,192,224):
        contact(frames,width).save(OUT/f'contact-{width}px.png')
    metadata = dict(sourceSha256=ACCEPTED_SHA,source='sources/canonical/artwork.png',
        atlasCoverageComplete=True,states=STATES,nativeRows=list(range(11)),directionCount=16,
        atlasSize=list(ATLAS_SIZE),cell=[WIDTH,HEIGHT],camera=transform,
        decodedTextureBytes=ATLAS_SIZE[0]*ATLAS_SIZE[1]*4,
        actionRows=summaries,atlasRGBAHash=hashlib.sha256(atlas.tobytes()).hexdigest().upper(),
        construction='exact paste of verified decoded v3 candidate strips; no new geometry or sampling',
        visualAcceptance='pending',allStateTransitionsAccepted=False,hostIntegrationVerified=False,
        facialGeometryRepair=False,generatedFromRejectedSources=False,
        installableFullAtlas=False,installed=False,
        limitations=['Complete cell coverage is NOT complete/approved animation quality or release authority.',
                     'Frontal small-step direction is approved, not finished gait. Waiting/review held timing is temporarily accepted, not hand/sleeve structure or full action/gaze aesthetics.',
                     'Global state changes, weak 80px cues, pose connections and arbitrary drag exits remain under review.',
                     'Fixed native resolution/timing/priority and decoded texture size are unchanged.',
                     'No pet.json or installer target is produced; this is a development QA artifact.'])
    (OUT/'build.json').write_text(json.dumps(metadata,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(atlasSize=metadata['atlasSize'],states=len(STATES),directions=16,
                         decodedTextureBytes=metadata['decodedTextureBytes'],installableFullAtlas=False)))


if __name__ == '__main__':
    main()
