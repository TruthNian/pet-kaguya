// Shared by the actual viewer and Node tests: current development composition,
// not a waiver of hand/sleeve aesthetics or motion/release approval.
export function validateReviewMetadata(metadata){
  if(!metadata||metadata.animationBuilt!==true||metadata.nativeRow!==8
      ||metadata.rightArmCompositionVersion!=='review-art-v6'||metadata.newArtworkGenerated!==true
      ||metadata.clothCompositionVersion!=='review-sleeves-v2'
      ||metadata.clothGeneratedSha256!=='41BAC8EC07B2EF55B9E89382CAA4B5FE1A34F105377E12DADEE291FEF48CB678'
      ||metadata.heldHandsUnchangedFromV5!==true||metadata.clothAlphaPreservedExactly!==true
      ||metadata.observedHairAlphaHolesRestored!==true
      ||metadata.originalLowerHandContourRestored!==true||metadata.handScaled!==false
      ||metadata.knownSourceHairRGBAExact!==true||metadata.paintedHairAlphaContinuityEstimated!==true
      ||metadata.handStrategy!=='two-low-hands-held'||metadata.strategyUserApproval!=='pending'
      ||metadata.closedEyeFrames!==0||metadata.bodyPulse!==false||metadata.ornamentFlash!==false
      ||metadata.repeatBeforeIdle!==3||metadata.visualMotionApproval!=='pending')
    throw new Error('review state or unapproved-motion boundary mismatch');
  return metadata;
}
