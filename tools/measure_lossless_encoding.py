"""Measured offline WebP effort, exact decoded RGBA; never a FPS benchmark."""
import hashlib
import io
import json
import argparse
from pathlib import Path
import time
from PIL import Image,features
from canonical import ROOT

OUT=ROOT/'work/lossless-encoding-study-20261010'


def measure(path,baseline=False):
    with Image.open(path) as image:source=image.convert('RGBA')
    raw=source.tobytes()
    records=[]
    plans=((6,80),) if baseline else ((6,0),(6,50),(6,75),(6,90),(6,100),(4,100))
    for method,quality in plans:
        buffer=io.BytesIO();start=time.perf_counter()
        source.save(buffer,format='WEBP',lossless=True,exact=True,method=method,quality=quality)
        encoded=buffer.getvalue();seconds=time.perf_counter()-start
        with Image.open(io.BytesIO(encoded)) as image:
            if image.convert('RGBA').tobytes()!=raw:
                raise ValueError('Lossless/exact claim failed for '+str(path))
        record=dict(method=method,quality=quality,bytes=len(encoded),encodeSeconds=round(seconds,6),
                    decodedRGBAExact=True,sha256=hashlib.sha256(encoded).hexdigest().upper())
        records.append(record)
        print(json.dumps(dict(asset=path.relative_to(ROOT).as_posix(),**record)),flush=True)
        if path.name=='spritesheet.webp':
            (OUT/f'global-m{method}-q{quality}.webp').write_bytes(encoded)
    return dict(asset=path.relative_to(ROOT).as_posix(),sourceEncodedBytes=path.stat().st_size,
                sourceEncodedSHA256=hashlib.sha256(path.read_bytes()).hexdigest().upper(),
                sourceRGBAHash=hashlib.sha256(raw).hexdigest().upper(),measurements=records,
                best=min(records,key=lambda record:record['bytes']))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline',action='store_true',help='Measure the actual Pillow default quality=80 separately')
    args=parser.parse_args()
    OUT.mkdir(parents=True,exist_ok=True)
    records=[measure(ROOT/'candidates/phase5/global/spritesheet.webp',args.baseline),
             measure(ROOT/'candidates/phase5/waiting/strip.webp',args.baseline)]
    report=dict(codecVersion=features.version('webp'),lossless=True,exact=True,records=records,
                installedChanged=False,activeAssetsChanged=False,
                scope='Offline encoding time and payload only; no browser decode/network/host FPS/memory claim.')
    (OUT/('baseline.json' if args.baseline else 'measurements.json')).write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')


if __name__=='__main__':main()
