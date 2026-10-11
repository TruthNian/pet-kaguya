"""Read-only checks of current delivery assets. No trial/historical rebuilds."""
import hashlib
import json
import time
from pathlib import Path

from PIL import Image

from canonical import ROOT, ACCEPTED_SHA
from build_global_review import assemble, OUT
from eye_motion import approved, descriptor, SCOPE, DECISION


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
    gaze=json.loads((ROOT/'candidates/phase5/look/build.json').read_text(encoding='utf-8'))
    if (gaze['frameHashes']!=approved()['frameHashes'] or gaze.get('adopted') is not True
            or gaze.get('eyeMotionApprovalScope')!=SCOPE or gaze.get('eyeMotionUserDecision')!=DECISION
            or gaze.get('eyeMotionVisualApproval')!='approved-as-development-basis'
            or gaze.get('irisShapeWarp') is not True or gaze.get('eyeBackingUsed') is not False):
        raise ValueError('Current gaze must use the exact narrowly approved candidate pixels')
    for state in ('run_right','run_left','processing','review'):
        action=json.loads((ROOT/f'candidates/phase5/{state}/build.json').read_text(encoding='utf-8'))
        if any(action.get(key)!=value for key,value in descriptor().items()):
            raise ValueError('Current eye-moving action has not adopted the same bounded eye model')
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
        installed_hash=hashlib.sha256(installed.read_bytes()).hexdigest().upper()
        original_hash='238C9ECEC64AB39B6F9CE04B9795E107996C1F97E06BA20B5E5A723EC940E3F1'
        reviewed_hash=None
        receipt=ROOT/'sources/canonical/whole-review-acceptance-20261011.json'
        if receipt.exists():
            decision=json.loads(receipt.read_text(encoding='utf-8'))
            current_hash=hashlib.sha256((OUT/'spritesheet.webp').read_bytes()).hexdigest().upper()
            if (decision['scope']=='current-whole-review-visual-acceptance'
                    and decision['visualAcceptance']=='accepted' and decision['installationAuthorized'] is True
                    and decision['applicationChangeAuthorized'] is False
                    and decision['atlasRGBAHash']==digest and decision['motherSHA256']==ACCEPTED_SHA
                    and decision['atlasSHA256']==current_hash):
                reviewed_hash=current_hash
        if installed_hash not in (original_hash,reviewed_hash):
            raise ValueError('Installed Kaguya changed without installation authority')
        installed_check='reviewed-atlas-authorized' if installed_hash==reviewed_hash else 'original-unchanged'
    print(json.dumps(dict(currentActionStates=len(states),lookDirections=16,
        actualCelsChecked=sum(row['frameCount'] for row in states)+16,
        atlasRGBAExact=True,motherSHA256=ACCEPTED_SHA,installed=installed_check,
        sourceRebuilds=0,historicalRebuilds=0,unadoptedStudyRebuilds=0,
        elapsedSeconds=round(time.perf_counter()-started,3)),indent=2))


if __name__=='__main__':
    main()
