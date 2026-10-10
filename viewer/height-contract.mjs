import {candidateCelKey} from './candidate-clock.mjs';
import {validateMaterialSupport} from './material-support-contract.mjs';

const shared=['sourceSha256','state','nativeRow','camera','durationsMs','repeatBeforeIdle',
  'bodyCompressionOutputPx','tipAnglesDegrees','groundedFrames',
  'groundedContactVersion','legCompositionVersion','legBackingGeneratedSha256'];
export function validateHopHeightStudy(study,baseline,current,manifest){
  const repair=validateMaterialSupport(current);
  if(manifest.commit!=='603b9ba02f6bc5c89ff971b54d087156a1a845c8'
      ||manifest.referenceRole!=='frozen-source-input-not-active-animation'
      ||manifest.referencePurpose!=='isolate-flight-height-only'
      ||manifest.file!=='jumping.webp'||manifest.contract!=='contract.json'||manifest.motion!=='motion.json'
      ||manifest.fileSha256!=='9BD0F25575A378F9CB4519581A10E7A15FFF8B08066009CB0E09D9FF335D9ACB'
      ||manifest.visualApprovalInherited!==false||manifest.installed!==false||manifest.installableFullAtlas!==false)
    throw new Error('Invalid frozen 8px hop reference');
  if(current.state!=='jumping'||current.nativeRow!==4||current.visualMotionApproval!=='pending'
      ||current.sourceSha256!=='65401EFDFEF0205D0CEA30AD08A0F14911C20B1B83468DBB6B3619E7DC89430A'
      ||study.previewVariant!=='jumping_height'||study.referencePurpose!=='isolate-flight-height-only'
      ||study.baselineApexOutputPx!==8||study.candidateApexOutputPx!==4||current.apexOutputPx!==4
      ||study.baselineActualCelsRGBAExact!==true||study.groundedCelsRGBAExact!==true
      ||study.onlyFlightActorTranslationChanged!==true||study.animationBuilt!==true
      ||study.adopted!==true||study.activeAtlasChanged!==true||study.currentJumpingCelsRGBAExact!==false
      ||study.acceptedHeightBasisPreservedExactly!==true
      ||study.adoptionScope!=='hop-height-development-basis-only'||current.heightApprovalScope!==study.adoptionScope
      ||study.heightVisualApproval!=='approved-as-development-basis'||current.heightVisualApproval!==study.heightVisualApproval
      ||current.heightUserDecision!=='sources/canonical/jumping-height-decision-20261010.json'
      ||study.userDecision!==current.heightUserDecision
      ||[study,baseline,current].some(m=>m.installed!==false||m.installableFullAtlas!==false
        ||m.visualMotionApproval!=='pending'||m.strategyUserApproval!=='pending')
      ||study.installableFullAtlas!==false||study.facialGeometryRepair!==false
      ||study.newArtworkGenerated!==false||study.nativeInterpolation!==false
      ||study.continuousLandingProven!==false||study.physicalBalanceProven!==false
      ||study.visualMotionApproval!=='pending'||study.strategyUserApproval!=='pending'
      ||shared.some(key=>current[key]===undefined||JSON.stringify(current[key])!==JSON.stringify(study[key])
        ||JSON.stringify(baseline[key])!==JSON.stringify(study[key]))
      ||JSON.stringify(study.baselineFrameHashes)!==JSON.stringify(baseline.frameHashes)
      ||JSON.stringify(study.baselineActorOffsetsPx)!==JSON.stringify(baseline.actorOffsetsPx)
      ||JSON.stringify(study.frameHashes)!==JSON.stringify(repair.baselineFrameHashes)
      ||JSON.stringify(study.currentJumpingFrameHashes)!==JSON.stringify(current.frameHashes)
      ||JSON.stringify(study.materialSupportRepair)!==JSON.stringify(repair)
      ||JSON.stringify(study.actorOffsetsPx)!==JSON.stringify(current.actorOffsetsPx)
      ||study.frameHashes?.length!==5||study.actorOffsetsPx?.length!==5
      ||study.keyframes?.length!==5||study.baselineKeyframes?.length!==5)
    throw new Error('Hop-height reference/current source or narrow approval boundary mismatch');
  study.frameHashes.forEach((_,i)=>candidateCelKey(study.frameHashes,i));
  current.frameHashes.forEach((_,i)=>candidateCelKey(current.frameHashes,i));
  baseline.frameHashes.forEach((_,i)=>candidateCelKey(baseline.frameHashes,i));
  for(let i=0;i<5;i++){
    const grounded=i===0||i===4;
    const before=study.baselineKeyframes[i],after=study.keyframes[i];
    if(before.grounded!==grounded||after.grounded!==grounded
        ||before.actorY!==baseline.actorOffsetsPx[i]
        ||after.actorY!==(grounded?before.actorY:before.actorY/2)
        ||after.actorY!==study.actorOffsetsPx[i]
        ||JSON.stringify({...before,actorY:after.actorY})!==JSON.stringify(after)
        ||(grounded&&study.frameHashes[i]!==baseline.frameHashes[i]))
      throw new Error('Hop-height study changed a pose or grounded cel');
  }
  return study;
}
