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
  if(!['idle','rigid','contact'].includes(choice)||!Number.isInteger(index)||index<0
      ||!durations[candidateRows[state]]||index>=durations[candidateRows[state]].length)
    throw new Error('Invalid comparison selection');
  if(choice==='idle')return {kind:'candidate',state:'idle',index:0,synchronized:false};
  if(choice==='rigid'&&['run_right','run_left'].includes(state))return {kind:'rigid',state,index,synchronized:true};
  if(choice==='contact'&&state==='jumping')return {kind:'contact',state,index,synchronized:true};
  if(state==='idle')return {kind:'candidate',state,index,synchronized:true};
  throw new Error('Synchronized reference cannot compare a different action');
}

export function validateHopReference(metadata,current){
  const fields=['sourceSha256','state','nativeRow','camera','durationsMs','actorOffsetsPx',
    'bodyCompressionOutputPx','tipAnglesDegrees','nativeInterpolation','repeatBeforeIdle'];
  if(current.state!=='jumping'||current.nativeRow!==4
      ||current.groundedContactVersion!=='two-link-source-material-v1'
      ||current.strategyApprovalInheritedFromLocomotion!==false
      ||current.visualMotionApproval!=='pending'||current.originalAirCelsRGBAExact!==true
      ||metadata.referenceRole!=='regenerated-counterfactual-not-active-animation'
      ||metadata.referencePurpose!=='isolate-grounded-two-link-knees-vs-vertical-height-field'
      ||metadata.file!=='comparison-old-strip.webp'||metadata.frameHashes?.length!==5
      ||metadata.visualApprovalInherited!==false||metadata.installableFullAtlas!==false||metadata.installed!==false
      ||JSON.stringify(metadata.airCelsRGBAExact)!==JSON.stringify([true,true,true])
      ||JSON.stringify(metadata.candidateFrameHashes)!==JSON.stringify(current.frameHashes)
      ||fields.some(key=>current[key]===undefined||JSON.stringify(metadata.contract?.[key])!==JSON.stringify(current[key])))
    throw new Error('Hop comparison source/poses/timing or candidate boundary mismatch');
  metadata.frameHashes.forEach((_,index)=>candidateCelKey(metadata.frameHashes,index));
  current.frameHashes.forEach((_,index)=>candidateCelKey(current.frameHashes,index));
  return metadata;
}
