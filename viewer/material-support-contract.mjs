import {candidateCelKey} from './candidate-clock.mjs';

const expected={
  jumping:[[15,[78,154,113,159]],[18,[78,152,113,156]],[0,null],[18,[78,152,113,156]],[0,null]],
  run_right:[[0,null],[1,[113,156,114,157]],[0,null],[1,[113,156,114,157]],[0,null],[0,null],[0,null],[0,null]],
  run_left:[[0,null],[1,[113,156,114,157]],[0,null],[1,[113,156,114,157]],[0,null],[0,null],[0,null],[0,null]]
};
export function validateMaterialSupport(current){
  const repair=current.materialSupportRepair,scope=expected[current.state];
  if(!scope||current.localFilterSupport!=='zero-extended-local-v2'
      ||repair?.baselineCommit!=='7f58246889fbbcfef788606067a95cf9251e1a87'
      ||repair.reference!==`sources/reference/material-support-v1/${current.state}.webp`
      ||repair.scope!=='local-bilinear-support-only'||repair.sourceArtworkChanged!==false
      ||repair.geometryChanged!==false||repair.timingChanged!==false
      ||repair.nativeAlphaPreservedExactly!==true||repair.fullMotionApproved!==false
      ||repair.baselineFrameHashes?.length!==scope.length||current.frameHashes?.length!==scope.length
      ||repair.changes?.length!==scope.length
      ||JSON.stringify(repair.currentFrameHashes)!==JSON.stringify(current.frameHashes))
    throw new Error('Local texture support repair/source boundary mismatch');
  const revision=repair.independentEyeSourceRevision;
  const filterHashes=revision?repair.sameSourceFilterFrameHashes:current.frameHashes;
  if(revision){
    const rig={'observed-eye-opening-v2':'sources/canonical/gaze-rig-v2.json',
      'original-aperture-surface-flow-v1':'sources/canonical/gaze-surface-v1.json'}[current.sourceEyeGeometryRevision];
    if(!['run_right','run_left'].includes(current.state)
        ||!rig||current.sourceEyeRig!==rig
        ||revision.revision!==current.sourceEyeGeometryRevision
        ||revision.reference!==`sources/reference/gaze-action-v1/${current.state}.json`
        ||revision.onlyNativeEyeWindowsChanged!==true||revision.nativeAlphaPreservedExactly!==true
        ||repair.filterComparison!=='frozen-same-source-counterfactual; not raw current-vs-historical pixels'
        ||filterHashes?.length!==scope.length||revision.changedPixels?.length!==scope.length
        ||revision.changedPixels.some(count=>!Number.isInteger(count)||count<=0||count>2112)
        ||JSON.stringify(revision.beforeFrameHashes)!==JSON.stringify(filterHashes)
        ||JSON.stringify(revision.afterFrameHashes)!==JSON.stringify(current.frameHashes))
      throw new Error('Eye-source and historical filter evidence cannot be conflated');
    if(current.sourceEyeGeometryRevision==='original-aperture-surface-flow-v1'
        &&(current.eyeMotionApprovalScope!=='gaze-surface-development-basis-only'
          ||current.eyeMotionVisualApproval!=='approved-as-development-basis'
          ||current.irisShapeWarp!==true||current.eyeBackingUsed!==false))
      throw new Error('New eye flow requires explicit bounded development approval');
  }else if(current.sourceEyeGeometryRevision!==undefined){
    throw new Error('Corrected eyes require independent same-source filter evidence');
  }
  scope.forEach(([count,bounds],i)=>{
    candidateCelKey(current.frameHashes,i);candidateCelKey(repair.baselineFrameHashes,i);
    candidateCelKey(filterHashes,i);
    const change=repair.changes[i];
    if(change?.changedPixels!==count||change.maximumChannelDifference!==(count?1:0)
        ||JSON.stringify(change.bounds)!==JSON.stringify(bounds)
        ||(repair.baselineFrameHashes[i]===filterHashes[i])!==(count===0))
      throw new Error('Local texture support repair exceeds its measured pixel scope');
  });
  return repair;
}
