"""Compare current actions to the exact pre-propagation atlas, without rebuilding artwork."""
import hashlib
import json
import argparse
import numpy as np
from PIL import Image,ImageDraw
from canonical import ROOT

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--before',type=str)
    args=parser.parse_args()
    ref=ROOT/'sources/reference/gaze-opening-v1'
    frozen=json.loads((ref/'manifest.json').read_text(encoding='utf-8'))
    if hashlib.sha256((ref/'atlas.webp').read_bytes()).hexdigest().upper()!=frozen['atlasEncodedSha256']:
        raise ValueError('Pre-correction atlas input changed')
    with Image.open(ref/'atlas.webp') as image:old=np.asarray(image.convert('RGBA')).copy()
    action_ref=ROOT/'sources/reference/gaze-action-v1'
    action_manifest=json.loads((action_ref/'manifest.json').read_text(encoding='utf-8'))
    look_path=action_ref/'look.webp'
    if hashlib.sha256(look_path.read_bytes()).hexdigest().upper()!=action_manifest['lookEncodedSha256']:
        raise ValueError('Frozen corrected look input changed')
    with Image.open(look_path) as image:old[9*208:]=np.asarray(image.convert('RGBA'))
    if hashlib.sha256(old.tobytes()).hexdigest().upper()!=action_manifest['reconstructedAtlasDecodedSha256']:
        raise ValueError('Frozen inputs do not reconstruct the exact pre-propagation atlas')
    if args.before:
        before=ROOT/args.before
        if hashlib.sha256(before.read_bytes()).hexdigest().upper()!='3368D25B3B1B5EC000EAD89EBD0016EDC91727222242D493B5480D3936FC007A':
            raise ValueError('Expected the exact 41078b0 pre-surface current atlas')
        with Image.open(before) as image:old=np.asarray(image.convert('RGBA')).copy()
    path=ROOT/'candidates/phase5/global/spritesheet.webp'
    with Image.open(path) as image:new=np.asarray(image.convert('RGBA'))
    if old.shape!=new.shape or not np.array_equal(old[...,3],new[...,3]):
        raise ValueError('Eye correction altered atlas geometry or any coverage alpha')
    changed=np.any(old!=new,axis=2)
    allowed=np.zeros(changed.shape,bool)
    look=json.loads((ROOT/'candidates/phase5/look/build.json').read_text(encoding='utf-8'))
    rows_allowed=(1,2,7,8,9,10) if look.get('eyeMotionApprovalScope')=='gaze-surface-development-basis-only' else (1,2,7,8)
    for row in rows_allowed:
        for col in range(8):
            for x0,y0,x1,y1 in ((68,44,100,76),(97,41,129,75)):
                allowed[row*208+y0:row*208+y1,col*192+x0:col*192+x1]=True
    if np.any(changed&~allowed):raise ValueError('Eye revision escaped its selected rows or native eye windows')
    rows=[int(changed[i*208:(i+1)*208].sum()) for i in range(11)]
    report=dict(otherFiveActionRowsRGBAExact=not any(rows[i] for i in (0,3,4,5,6)),lookRowsRGBAExact=not any(rows[9:]),
        allNativeAlphaExact=True,changedPixelsByRow=rows,baseline=args.before or 'reconstructed-a3c898d',
        encodedBytes=path.stat().st_size,encodedSHA256=hashlib.sha256(path.read_bytes()).hexdigest().upper(),
        decodedSHA256=hashlib.sha256(new.tobytes()).hexdigest().upper(),fullVisualApproval=False)
    out=ROOT/'work/gaze-sclera-inspection';out.mkdir(parents=True,exist_ok=True)
    (out/'atlas-scope.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    proof=Image.new('RGB',(488,424),'#ededed');draw=ImageDraw.Draw(proof)
    for col,(label,pixels) in enumerate((('before action-eye correction',old),('current development',new))):
        frame=Image.fromarray(pixels[8*208:9*208,:192])
        tile=Image.new('RGBA',frame.size,'#ededed');tile.alpha_composite(frame)
        proof.paste(tile.resize((224,243),Image.Resampling.NEAREST).convert('RGB'),(col*244+10,28))
        draw.text((col*244+4,5),label,fill='#222222')
        face=tile.crop((68,41,129,76)).resize((244,140),Image.Resampling.NEAREST).convert('RGB')
        proof.paste(face,(col*244,284))
    proof.save(out/'action-eye-comparison.png')
    print(json.dumps(report))

if __name__=='__main__':main()
