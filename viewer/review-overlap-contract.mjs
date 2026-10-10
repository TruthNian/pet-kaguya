import {durations} from './clock.mjs';
import {candidateCelKey} from './candidate-clock.mjs';
import {validateReviewMetadata} from './review-contract.mjs';

const same=(a,b)=>JSON.stringify(a)===JSON.stringify(b);
const purpose='isolate-review-held-hands-and-cuffs';
const poses=[{bodyY:0,earAngle:0,hairAngle:0},{bodyY:0,earAngle:.06,hairAngle:0},
  {bodyY:0,earAngle:.15,hairAngle:.01},{bodyY:0,earAngle:.15,hairAngle:.02},
  {bodyY:0,earAngle:.06,hairAngle:0},{bodyY:0,earAngle:0,hairAngle:0}];
export function validateReviewOverlapMetadata(study){
  const yes=['animationBuilt','heldTimingAcceptedTemporarily','baselineActualCelsReconstructedExactly',
    'sourceAlphaPreservedExactly','nativeAlphaPreservedExactly','sourceChangesInsideHandCuffPermissionOnly',
    'sourceEyeFaceRGBAExactToBaseline','bodyEarHairPosesUnchanged','sameSourceCoordinateCamera','loopSeamRGBAExact'];
  const no=['facialGeometryRepair','newFaceGeometry','nativeInterpolation','newArtworkGeneratedThisBuild',
    'adopted','activeAtlasChanged','installableFullAtlas','installed','articulatedArmBuilt',
    'cleanLayerRecoveryClaimed','entryExitTransitionsBuilt'];
  if(!study||study.sourceSha256!=='65401EFDFEF0205D0CEA30AD08A0F14911C20B1B83468DBB6B3619E7DC89430A'
      ||study.state!=='review'||study.previewVariant!=='review_overlap'||study.nativeRow!==8
      ||study.referencePurpose!==purpose||study.handStrategy!=='low-overlapping-hands-held'
      ||study.handGeneratedSha256!=='4ACA513583BF6BD69B642D5A656E97386E3B890CD2BBD861A96B6A4A98AAB6EE'
      ||study.candidatePoseRGBAHash!=='F4A43E5B7A3DFC23D89206E148C073CDA38317303CCDDEB17BC3CB49061B09F0'
      ||study.specificPoseUserApproval!=='pending'||study.visualMotionApproval!=='pending'
      ||study.closedEyeFrames!==0||study.repeatBeforeIdle!==3||study.totalDurationMs!==1030||study.actionDurationMs!==3090
      ||study.heldTimingUserDecision!=='held-gesture-boundary-decision-20261009.json'
      ||!same(study.durationsMs,durations[8])||!same(study.keyframes,poses)||!same(study.focusOffsetSourcePx,[0,5])
      ||!same(study.handCuffMaximumSourceDisplacementPx,[0,0,0,0,0,0])
      ||yes.some(key=>study[key]!==true)||no.some(key=>study[key]!==false)
      ||study.frameHashes?.length!==6||study.baselineFrameHashes?.length!==6
      ||study.changesFromFrozenReview?.length!==6||study.changesFromFrozenReview.some(change=>
        change.changedPixels!==844||change.alphaChangedPixels!==0||!same(change.bounds,[61,105,104,140])))
    throw new Error('Unadopted review hand trial source/holds/scope mismatch');
  for(const hashes of [study.frameHashes,study.baselineFrameHashes]){
    hashes.forEach((_,index)=>candidateCelKey(hashes,index));
    if(hashes[0]!==hashes[5]||hashes[1]!==hashes[4])throw new Error('Review held loop seam mismatch');
  }
  return study;
}
export function validateReviewOverlapReference(manifest,baseline,study,current){
  validateReviewOverlapMetadata(study);
  validateReviewMetadata(baseline);validateReviewMetadata(current);
  if(manifest.commit!=='274abbb5122625de604a6e51299a80443c4c4bb9'
      ||manifest.referenceRole!=='frozen-source-input-not-active-animation'||manifest.referencePurpose!==purpose
      ||manifest.file!=='review.webp'||manifest.contract!=='contract.json'
      ||manifest.fileSha256!=='885A19AA646D3B5EF3E1E978D95E116D745650F419CCEE22ED6C6B2CBFF28B63'
      ||manifest.visualApprovalInherited!==false||manifest.installableFullAtlas!==false||manifest.installed!==false
      ||['sourceSha256','state','nativeRow','camera','durationsMs','focusOffsetSourcePx','repeatBeforeIdle',
         'heldTimingUserDecision','heldTimingAcceptedTemporarily'].some(key=>
        study[key]===undefined||!same(study[key],baseline[key])||!same(study[key],current[key]))
      ||!same(study.baselineFrameHashes,baseline.frameHashes)||!same(baseline.frameHashes,current.frameHashes))
    throw new Error('Frozen review reference and actual current source/poses/timing mismatch');
  return baseline;
}
