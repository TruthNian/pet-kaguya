"""Read-only checks of current delivery assets. No trial/historical rebuilds."""
import hashlib
import json
import time
from pathlib import Path

from PIL import Image

from canonical import ROOT, ACCEPTED_SHA
from build_global_review import assemble, OUT


def main():
    started=time.perf_counter()
    expected,states,_,_=assemble()  # Verify 9 strips, 16 gazes and native holds.
    with Image.open(OUT/'spritesheet.webp') as opened:
        actual=opened.convert('RGBA')
    if actual.tobytes()!=expected.tobytes():
        raise ValueError('Current global atlas does not match its actual action/gaze strips')
    metadata=json.loads((OUT/'build.json').read_text(encoding='utf-8'))
    digest=hashlib.sha256(actual.tobytes()).hexdigest().upper()
    if (metadata['atlasRGBAHash']!=digest or metadata['sourceSha256']!=ACCEPTED_SHA
            or metadata['visualAcceptance']!='pending' or metadata['installed']
            or metadata['installableFullAtlas'] or metadata['allStateTransitionsAccepted']):
        raise ValueError('Current atlas pixel/approval boundary mismatch')
    decision=json.loads((ROOT/'sources/canonical/waving-amplitude-adoption-20261010.json').read_text(encoding='utf-8'))
    wave=json.loads((ROOT/'candidates/phase5/waving/build.json').read_text(encoding='utf-8'))
    if (decision['scope']!='waving-lower-amplitude-development-basis-only'
            or decision['candidatePixelsApprovedAsDevelopmentBasis'] is not True
            or decision['approvedPeakRGBAHash']!=wave['frameHashes'][1]
            or wave['amplitudeApprovalScope']!=decision['scope']
            or wave['amplitudeVisualApproval']!='approved-as-development-basis'
            or any(decision[key] for key in ('fullMotionApproved','entryExitApproved',
                'faceGeometryChangeApproved','hostChangeApproved','installationApproved'))):
        raise ValueError('Wave pixels or narrow user approval changed')
    installed=Path.home()/'.codex/pets/kaguya/spritesheet.webp'
    installed_check='not-present-on-this-machine'
    if installed.exists():
        if hashlib.sha256(installed.read_bytes()).hexdigest().upper()!='238C9ECEC64AB39B6F9CE04B9795E107996C1F97E06BA20B5E5A723EC940E3F1':
            raise ValueError('Installed Kaguya changed without installation authority')
        installed_check='unchanged'
    print(json.dumps(dict(currentActionStates=len(states),lookDirections=16,
        actualCelsChecked=sum(row['frameCount'] for row in states)+16,
        atlasRGBAExact=True,motherSHA256=ACCEPTED_SHA,installed=installed_check,
        sourceRebuilds=0,historicalRebuilds=0,unadoptedStudyRebuilds=0,
        elapsedSeconds=round(time.perf_counter()-started,3)),indent=2))


if __name__=='__main__':
    main()
