const source='65401EFDFEF0205D0CEA30AD08A0F14911C20B1B83468DBB6B3619E7DC89430A';
export function validateGazeFamily(metadata,family){
  if(!['rigid','current','surface'].includes(family)||metadata?.sourceSha256!==source
      ||metadata.directionCount!==16||JSON.stringify(metadata.nativeRows)!=='[9,10]'
      ||metadata.bodyRotated!==false||metadata.artMirrored!==false
      ||metadata.facialGeometryRepair!==false||metadata.eyeOutlineFixed!==true
      ||metadata.installableFullAtlas!==false||metadata.installed!==false
      ||metadata.visualAcceptance!=='pending'||metadata.frameHashes?.length!==16
      ||metadata.frameHashes.some(hash=>!(/^[A-F0-9]{64}$/).test(hash))
      ||!(/^[A-F0-9]{64}$/).test(metadata.neutralFrameHash))
    throw new Error('Gaze source/shape/candidate boundary mismatch');
  if(family==='rigid'&&metadata.irisShapeWarp!==false)
    throw new Error('Frozen rigid gaze cannot become a surface-flow replacement');
  if(family!=='rigid'&&(metadata.method!=='original-aperture-surface-flow-v1'
      ||metadata.sourceRig!=='sources/canonical/gaze-surface-v1.json'
      ||metadata.irisShapeWarp!==true
      ||metadata.newArtworkGenerated!==false||metadata.sourceRGBAExactAtZero!==true
      ||metadata.sourceAlphaPreservedExactly!==true||metadata.nativeAlphaPreservedExactly!==true
      ||JSON.stringify(metadata.maximumDisplacementSourcePx)!=='[6,4]'
      ||!Number.isFinite(metadata.minimumSampledJacobian)||metadata.minimumSampledJacobian<=0))
    throw new Error('Unadopted original-surface candidate boundary mismatch');
  if(family==='surface'&&(metadata.adopted!==false||metadata.activeAtlasChanged!==false))
    throw new Error('Frozen proposal cannot inherit later approval');
  if(family==='current'&&(metadata.adopted!==true||metadata.activeAtlasChanged!==true
      ||metadata.eyeMotionApprovalScope!=='gaze-surface-development-basis-only'
      ||metadata.eyeMotionVisualApproval!=='approved-as-development-basis'
      ||metadata.eyeMotionUserDecision!=='sources/canonical/gaze-surface-adoption-20261010.json'
      ||metadata.approvalDoesNotIncludeFullEyeQuality!==true||metadata.approvalDoesNotIncludeFullMotion!==true
      ||metadata.eyeBackingUsed!==false))
    throw new Error('Current flow requires narrow development-basis approval');
  return metadata;
}
