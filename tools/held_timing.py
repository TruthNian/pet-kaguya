"""A scoped human timing decision, never hand/cloth or host authority."""
import json

from canonical import ROOT, ACCEPTED_SHA

DECISION = 'held-gesture-boundary-decision-20261009.json'


def validate_decision(motion):
    if motion.get('heldTimingUserDecision') != DECISION:
        raise ValueError('Held timing must cite the actual scoped user decision')
    receipt = json.loads((ROOT/'sources/canonical'/DECISION).read_text(encoding='utf-8'))
    if (receipt['sourceSha256'] != ACCEPTED_SHA
            or receipt['scope'] != 'temporary-held-timing-boundary-only'
            or receipt['heldTimingAcceptedTemporarily'] is not True
            or receipt['knownEntryExitJumpsRemain'] is not True
            or receipt['continueStructuralImprovement'] is not True
            or any(receipt[name] is not False for name in (
                'renderedHandStructureApproved', 'sleeveAndHairSeamsApproved',
                'fullNaturalnessApproved', 'allMotionApproved',
                'independentPetHostAuthorized', 'installedHostChangeAuthorized'))):
        raise ValueError('Held timing cannot approve structure, full motion or host expansion')
