"""One-time byte archive from a local Git commit; no download or overwrite.

The archived WebPs are frozen source inputs. CI validates their actual bytes
and all decoded cels without fetching Git history or regenerating them.
"""
import hashlib
import io
import json
import subprocess

from PIL import Image

from canonical import ROOT,ACCEPTED_SHA,load_canonical
from locomotion_reference import OUT,COMMIT,CONTRACT_FIELDS,load


def preserve(path,payload):
    if path.exists():
        if path.read_bytes()!=payload:
            raise ValueError(f'Refusing to overwrite frozen source: {path.name}')
    else:
        path.write_bytes(payload)


def main():
    load_canonical()
    states={}; payloads={}
    for name in ('run_right','run_left'):
        root=f'candidates/phase5/{name}'
        raw=subprocess.check_output(['git','show',f'{COMMIT}:{root}/strip.webp'],cwd=ROOT)
        old=json.loads(subprocess.check_output(['git','show',f'{COMMIT}:{root}/build.json'],cwd=ROOT))
        with Image.open(io.BytesIO(raw)) as opened:
            strip=opened.convert('RGBA')
        hashes=[hashlib.sha256(strip.crop((i*192,0,(i+1)*192,208)).tobytes()).hexdigest().upper() for i in range(8)]
        if (strip.size!=(1536,208) or hashes!=old['frameHashes'] or old['sourceSha256']!=ACCEPTED_SHA
                or old['secondaryMotion']!='rigid-follow-only; delayed ear/hair response remains missing'):
            raise ValueError('Git source is not the pre-follow-through row')
        states[name]=dict(file=f'{name}.webp',encodedSha256=hashlib.sha256(raw).hexdigest().upper(),
                          frameHashes=hashes,contract={key:old[key] for key in CONTRACT_FIELDS})
        payloads[name]=raw
    metadata=dict(sourceSha256=ACCEPTED_SHA,commit=COMMIT,
                  referenceRole='frozen-source-input-not-active-animation',
                  referencePurpose='isolate-ear-hair-follow-through',visualApprovalInherited=False,
                  installableFullAtlas=False,installed=False,states=states)
    OUT.mkdir(parents=True,exist_ok=True)
    for name,raw in payloads.items():preserve(OUT/f'{name}.webp',raw)
    preserve(OUT/'manifest.json',(json.dumps(metadata,indent=2)+'\n').encode('utf-8'))
    load()
    print(json.dumps(dict(archivedCommit=COMMIT,states=list(states),decodedCelsVerified=16,installed=False)))


if __name__=='__main__':main()
