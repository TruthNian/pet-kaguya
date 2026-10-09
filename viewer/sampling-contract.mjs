import {candidateCelKey} from './candidate-clock.mjs';

export function validateSamplingStudy(metadata,state,current){
  if(metadata.sourceSha256!==current.sourceSha256
      ||metadata.role!=='full-coverage-terminal-precision-study-not-an-active-pet'
      ||metadata.method!=='float32-premult-lanczos; single-final-straight-rgba8-quantization'
      ||JSON.stringify(metadata.atlasCanvas)!==JSON.stringify([1536,2288])
      ||JSON.stringify(metadata.coverage)!==JSON.stringify({actionStates:9,lookDirections:16,actualTimedActionCels:57,comparedCels:73})
      ||metadata.allLegacyCelsReconstructedExactly!==true||metadata.geometryAndSourcePixelsUnchanged!==true
      ||metadata.nativeTimingsChanged!==false||metadata.hostResolutionChanged!==false||metadata.hostFpsChanged!==false
      ||metadata.activeAtlasChanged!==false||metadata.adopted!==false||metadata.visualApproval!=='pending'
      ||metadata.installableFullAtlas!==false||metadata.installed!==false)
    throw new Error('Invalid terminal precision study boundary');
  const entry=metadata.states?.[state];
  if(!entry||current.state!==state||entry.nativeRows?.length!==1||(entry.nativeRows[0]!==current.nativeRow&&state!=='idle')
      ||JSON.stringify(entry.legacyFrameHashes)!==JSON.stringify(current.frameHashes)
      ||JSON.stringify(entry.camera)!==JSON.stringify(current.camera)
      ||JSON.stringify(entry.durationsMs)!==JSON.stringify(current.durationsMs)
      ||entry.candidateFrameHashes?.length!==current.frameHashes.length)
    throw new Error('Precision comparison does not match actual current source/timing/cels');
  // Older idle metadata has no nativeRow; its known row must still be zero.
  if(state==='idle'&&entry.nativeRows[0]!==0)throw new Error('Idle precision row mismatch');
  entry.candidateFrameHashes.forEach((_,index)=>candidateCelKey(entry.candidateFrameHashes,index));
  return entry;
}
