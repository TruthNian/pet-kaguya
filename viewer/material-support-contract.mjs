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
  scope.forEach(([count,bounds],i)=>{
    candidateCelKey(current.frameHashes,i);candidateCelKey(repair.baselineFrameHashes,i);
    const change=repair.changes[i];
    if(change?.changedPixels!==count||change.maximumChannelDifference!==(count?1:0)
        ||JSON.stringify(change.bounds)!==JSON.stringify(bounds)
        ||(repair.baselineFrameHashes[i]===current.frameHashes[i])!==(count===0))
      throw new Error('Local texture support repair exceeds its measured pixel scope');
  });
  return repair;
}
