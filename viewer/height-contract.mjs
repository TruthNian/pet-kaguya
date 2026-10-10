import {candidateCelKey} from './candidate-clock.mjs';

const shared=['sourceSha256','state','nativeRow','camera','durationsMs','repeatBeforeIdle',
  'bodyCompressionOutputPx','tipAnglesDegrees','groundedFrames',
  'groundedContactVersion','legCompositionVersion','legBackingGeneratedSha256'];
export function validateHopHeightStudy(study,current){
  if(current.state!=='jumping'||current.nativeRow!==4||current.visualMotionApproval!=='pending'
      ||current.sourceSha256!=='65401EFDFEF0205D0CEA30AD08A0F14911C20B1B83468DBB6B3619E7DC89430A'
      ||study.previewVariant!=='jumping_height'||study.referencePurpose!=='isolate-flight-height-only'
      ||study.baselineApexOutputPx!==8||study.candidateApexOutputPx!==4
      ||study.baselineActualCelsRGBAExact!==true||study.groundedCelsRGBAExact!==true
      ||study.onlyFlightActorTranslationChanged!==true||study.animationBuilt!==true
      ||study.adopted!==false||study.activeAtlasChanged!==false||study.installed!==false
      ||study.installableFullAtlas!==false||study.facialGeometryRepair!==false
      ||study.newArtworkGenerated!==false||study.nativeInterpolation!==false
      ||study.continuousLandingProven!==false||study.physicalBalanceProven!==false
      ||study.visualMotionApproval!=='pending'||study.strategyUserApproval!=='pending'
      ||shared.some(key=>current[key]===undefined||JSON.stringify(current[key])!==JSON.stringify(study[key]))
      ||JSON.stringify(study.baselineFrameHashes)!==JSON.stringify(current.frameHashes)
      ||JSON.stringify(study.baselineActorOffsetsPx)!==JSON.stringify(current.actorOffsetsPx)
      ||study.frameHashes?.length!==5||study.actorOffsetsPx?.length!==5
      ||study.keyframes?.length!==5||study.baselineKeyframes?.length!==5)
    throw new Error('Hop-height study is not a single-factor current-source comparison');
  study.frameHashes.forEach((_,i)=>candidateCelKey(study.frameHashes,i));
  current.frameHashes.forEach((_,i)=>candidateCelKey(current.frameHashes,i));
  for(let i=0;i<5;i++){
    const grounded=i===0||i===4;
    const before=study.baselineKeyframes[i],after=study.keyframes[i];
    if(before.grounded!==grounded||after.grounded!==grounded
        ||before.actorY!==current.actorOffsetsPx[i]
        ||after.actorY!==(grounded?before.actorY:before.actorY/2)
        ||after.actorY!==study.actorOffsetsPx[i]
        ||JSON.stringify({...before,actorY:after.actorY})!==JSON.stringify(after)
        ||(grounded&&study.frameHashes[i]!==current.frameHashes[i]))
      throw new Error('Hop-height study changed a pose or grounded cel');
  }
  return study;
}
