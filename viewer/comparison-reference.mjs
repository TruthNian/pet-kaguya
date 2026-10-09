import {durations} from './clock.mjs';
import {candidateRows,candidateCelKey} from './candidate-clock.mjs';

const fields=['sourceSha256','state','nativeRow','camera','durationsMs','projection','supportFeet',
  'footOffsetsSourcePx','rootOffsetsSourcePx','focusOffsetSourcePx','legCompositionVersion',
  'legBackingGeneratedSha256','eyeBackingGeneratedSha256'];
export function validateRigidReference(metadata,state,current){
  if(!['run_right','run_left'].includes(state)
      ||metadata.sourceSha256!==current.sourceSha256
      ||metadata.commit!=='d804cd5e6eefdf1de106c97c2f5470837fab9dc2'
      ||metadata.referenceRole!=='frozen-source-input-not-active-animation'
      ||metadata.referencePurpose!=='isolate-ear-hair-follow-through'
      ||metadata.visualApprovalInherited!==false||metadata.installableFullAtlas!==false||metadata.installed!==false)
    throw new Error('Invalid frozen comparison boundary');
  const entry=metadata.states?.[state];
  if(!entry||entry.file!==`${state}.webp`||entry.frameHashes?.length!==8
      ||fields.some(key=>current[key]===undefined||JSON.stringify(entry.contract?.[key])!==JSON.stringify(current[key])))
    throw new Error('Reference and candidate do not have the same pose/timing/source contract');
  entry.frameHashes.forEach((_,index)=>candidateCelKey(entry.frameHashes,index));
  return entry;
}
export function comparisonReference(choice,state,index){
  if(!['idle','rigid'].includes(choice)||!Number.isInteger(index)||index<0
      ||!durations[candidateRows[state]]||index>=durations[candidateRows[state]].length)
    throw new Error('Invalid comparison selection');
  if(choice==='idle')return {kind:'candidate',state:'idle',index:0,synchronized:false};
  if(['run_right','run_left'].includes(state))return {kind:'rigid',state,index,synchronized:true};
  if(state==='idle')return {kind:'candidate',state,index,synchronized:true};
  throw new Error('Rigid gait reference cannot compare a different action');
}
