// Shared by the actual viewer and Node tests: current development composition,
// not a waiver of hand/sleeve aesthetics or motion/release approval.
import {candidateCelKey} from './candidate-clock.mjs';
export function validateReviewMetadata(metadata){
  const overlap=metadata?.handCompositionVersion==='review-hands-overlap-v1';
  if(!metadata||metadata.animationBuilt!==true||metadata.nativeRow!==8
      ||metadata.rightArmCompositionVersion!=='review-art-v6'||metadata.newArtworkGenerated!==true
      ||metadata.clothCompositionVersion!=='review-sleeves-v2'
      ||metadata.clothGeneratedSha256!=='41BAC8EC07B2EF55B9E89382CAA4B5FE1A34F105377E12DADEE291FEF48CB678'
      ||metadata.heldHandsUnchangedFromV5!==!overlap||metadata.clothAlphaPreservedExactly!==true
      ||metadata.observedHairAlphaHolesRestored!==true
      ||metadata.originalLowerHandContourRestored!==!overlap||metadata.handScaled!==false
      ||metadata.knownSourceHairRGBAExact!==true||metadata.paintedHairAlphaContinuityEstimated!==true
      ||metadata.handStrategy!==(overlap?'low-overlapping-hands-held':'two-low-hands-held')||metadata.strategyUserApproval!=='pending'
      ||metadata.closedEyeFrames!==0||metadata.bodyPulse!==false||metadata.ornamentFlash!==false
      ||metadata.repeatBeforeIdle!==3||metadata.visualMotionApproval!=='pending')
    throw new Error('review state or unapproved-motion boundary mismatch');
  if(overlap&&(metadata.handGeneratedSha256!=='4ACA513583BF6BD69B642D5A656E97386E3B890CD2BBD861A96B6A4A98AAB6EE'
      ||metadata.handPoseRGBAHash!=='F4A43E5B7A3DFC23D89206E148C073CDA38317303CCDDEB17BC3CB49061B09F0'
      ||metadata.handDevelopmentBasis!=='developer-selected-relaxed-hand-structure'
      ||metadata.handUserApprovalClaimed!==false||metadata.specificPoseUserApproval!=='pending'
      ||metadata.newArtworkGeneratedThisIteration!==false||metadata.entryExitTransitionsBuilt!==false
      ||metadata.handReference!=='sources/reference/review-hands-before'
      ||metadata.legacyHandStrategy!=='two-low-hands-held'))
    throw new Error('review state or unapproved-motion boundary mismatch');
  return metadata;
}

export function validateReviewHandReference(before,current){
  validateReviewMetadata(before);validateReviewMetadata(current);
  const fields=['sourceSha256','state','nativeRow','camera','durationsMs','repeatBeforeIdle',
    'focusOffsetSourcePx','sourceEyeRig','sourceEyeGeometryRevision','eyeMotionApprovalScope','eyeMotionUserDecision',
    'heldTimingUserDecision','heldTimingAcceptedTemporarily'];
  if(before.handCompositionVersion!==undefined||current.handCompositionVersion!=='review-hands-overlap-v1'
      ||fields.some(key=>before[key]===undefined||JSON.stringify(before[key])!==JSON.stringify(current[key]))
      ||before.frameHashes?.length!==6||current.frameHashes?.length!==6
      ||before.installed!==false||current.installed!==false
      ||before.installableFullAtlas!==false||current.installableFullAtlas!==false)
    throw new Error('Review hand comparison must preserve actual eye model, source, poses and holds');
  for(const hashes of [before.frameHashes,current.frameHashes])
    hashes.forEach((_,index)=>candidateCelKey(hashes,index));
  return before;
}
