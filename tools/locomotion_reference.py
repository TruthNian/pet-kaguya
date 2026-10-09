"""Frozen pre-follow-through source strips, not current-animation pixel locks."""
import hashlib
import json

from PIL import Image

from canonical import ROOT, ACCEPTED_SHA

OUT = ROOT/'sources/reference/locomotion-rigid'
COMMIT = 'd804cd5e6eefdf1de106c97c2f5470837fab9dc2'
CONTRACT_FIELDS = ('sourceSha256','state','nativeRow','camera','durationsMs','projection',
                   'supportFeet','footOffsetsSourcePx','rootOffsetsSourcePx','focusOffsetSourcePx',
                   'legCompositionVersion','legBackingGeneratedSha256','eyeBackingGeneratedSha256')


def load():
    metadata=json.loads((OUT/'manifest.json').read_text(encoding='utf-8'))
    receipt=json.loads((ROOT/'sources/canonical/locomotion-cadence-decision-20261009.json').read_text(encoding='utf-8'))
    if (metadata['sourceSha256']!=ACCEPTED_SHA or metadata['commit']!=COMMIT
            or metadata['referenceRole']!='frozen-source-input-not-active-animation'
            or metadata['referencePurpose']!='isolate-ear-hair-follow-through'
            or metadata['visualApprovalInherited'] or metadata['installableFullAtlas'] or metadata['installed']
            or set(metadata['states'])!={'run_right','run_left'}):
        raise ValueError('Wrong historical comparison source or authority boundary')
    strips={}
    for name,entry in metadata['states'].items():
        if entry['file']!=f'{name}.webp':
            raise ValueError('Unexpected reference file')
        path=OUT/entry['file']
        if hashlib.sha256(path.read_bytes()).hexdigest().upper()!=entry['encodedSha256']:
            raise ValueError('Frozen reference bytes changed')
        with Image.open(path) as opened:
            strip=opened.convert('RGBA')
        hashes=[hashlib.sha256(strip.crop((i*192,0,(i+1)*192,208)).tobytes()).hexdigest().upper() for i in range(8)]
        if (strip.size!=(1536,208) or hashes!=entry['frameHashes']
                or hashes!=receipt['reviewedFrameRGBAHashes'][name]
                or entry['contract']['durationsMs']!=receipt['reviewedDurationsMs']
                or entry['contract']['rootOffsetsSourcePx']!=receipt['reviewedRootSourcePx']):
            raise ValueError('Reference differs from the actual reviewed cadence evidence')
        strips[name]=strip
    return metadata,strips
