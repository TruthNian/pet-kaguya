// Complete garment adoption does not imply pure-RGB editing or visual approval.
export function validateWaitingMetadata(metadata){
  if(!metadata||metadata.animationBuilt!==true||metadata.nativeRow!==6
      ||metadata.artworkCompositionVersion!=='waiting-art-v2'
      ||metadata.clothCompositionVersion!=='waiting-sleeve-v1'
      ||metadata.clothGeneratedSha256!=='60B513037DBCEDDF647C500D84C17BBF2706D81DB8EF85F9228DBE80CBC15F8F'
      ||metadata.heldHandRGBAExactFromV1!==true||metadata.newArtworkGenerated!==true
      ||metadata.wholeRaisedGarmentAndBoundedBacking!==true||metadata.clothAlphaPreservedExactly!==false
      ||metadata.cleanSemanticMatteClaimed!==false||metadata.clothOnlyPixelChangeClaimed!==false
      ||metadata.handStrategy!=='held-chin-contact'||metadata.strategyUserApproval!=='pending'
      ||metadata.closedEyeFrames!==0||metadata.bodyPulse!==false||metadata.repeatBeforeIdle!==3
      ||metadata.heldTimingAcceptedTemporarily!==true||metadata.visualMotionApproval!=='pending')
    throw new Error('waiting held-contact candidate boundary mismatch');
  return metadata;
}
