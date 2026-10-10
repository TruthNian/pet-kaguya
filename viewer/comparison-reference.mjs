import {durations} from './clock.mjs';
import {candidateRows,candidateCelKey} from './candidate-clock.mjs';
import {validateMaterialSupport} from './material-support-contract.mjs';

const fields=['sourceSha256','state','nativeRow','camera','durationsMs','projection','supportFeet',
  'footOffsetsSourcePx','rootOffsetsSourcePx','focusOffsetSourcePx','legCompositionVersion',
  'legBackingGeneratedSha256','eyeBackingGeneratedSha256'];
export function validateRigidReference(metadata,state,current){
  validateMaterialSupport(current);
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
  if(!['idle','rigid','contact','mouth','height','hands','cloth','wave','link','calm'].includes(choice)||!Number.isInteger(index)||index<0
      ||!durations[candidateRows[state]]||index>=durations[candidateRows[state]].length)
    throw new Error('Invalid comparison selection');
  if(choice==='idle')return {kind:'candidate',state:'idle',index:0,synchronized:false};
  if(choice==='rigid'&&['run_right','run_left'].includes(state))return {kind:'rigid',state,index,synchronized:true};
  if(choice==='cloth'&&['run_right','run_left'].includes(state))return {kind:'current',state,index,synchronized:true};
  if(choice==='wave'&&state==='waving')return {kind:'wave',state,index,synchronized:true};
  if(choice==='link'&&state==='waving')return {kind:'middle-before',state,index,synchronized:true};
  if(choice==='link'&&state==='waving_link')return {kind:'candidate',state:'waving',index,synchronized:true};
  if(choice==='contact'&&state==='jumping')return {kind:'contact',state,index,synchronized:true};
  if(choice==='mouth'&&state==='failed')return {kind:'mouth',state:'failed',index,synchronized:true};
  if(choice==='calm'&&state==='failed')return {kind:'failed-before',state,index,synchronized:true};
  if(choice==='height'&&state==='jumping')return {kind:'height',state,index,synchronized:true};
  if(choice==='hands'&&state==='review')return {kind:'hand-before',state,index,synchronized:true};
  if(choice==='hands'&&state==='review_overlap')return {kind:'hands',state:'review',index,synchronized:true};
  if(state==='idle')return {kind:'candidate',state,index,synchronized:true};
  throw new Error('Synchronized reference cannot compare a different action');
}

// A trial has no entry in the current-atlas float study. Reset incompatible
// references rather than silently comparing different states or art epochs.
export function comparisonPolicy(mode,choice,reset=false){
  if(!Object.keys(candidateRows).includes(mode))throw new Error('Invalid comparison mode');
  const actionChoices=mode==='jumping'?['height','contact']:mode==='failed'?['calm']
    :mode==='waving'?['link']:mode==='review'?['hands']:[];
  const allowed=['idle',...actionChoices];
  // Archived trials with v1 eye materials cannot be same-art comparisons
  // against actions that now use corrected eye extraction.
  if(['idle','jumping','waiting'].includes(mode))allowed.push('sampling');
  return {allowed,choice:reset||!allowed.includes(choice)?actionChoices[0]??'idle':choice};
}

export function validateFailedBodyReference(before,current){
  const same=(a,b)=>JSON.stringify(a)===JSON.stringify(b);
  const fields=['sourceSha256','state','nativeRow','camera','durationsMs','repeatBeforeIdle',
    'mouthArt','mouthGeneratedSha256','mouthPoseRGBAHash','mouthLineVisualApproval','mouthApprovalScope','mouthUserDecision'];
  if(current.failedBodyDevelopmentBasis!=='developer-selected-calm-body-hold'
      ||current.bodyMotionUserApproval!=='pending'||current.bodyMotionUserApprovalClaimed!==false
      ||current.failedBodyReference!=='sources/reference/failed-body-before'
      ||current.bodyHeldAtCanonicalHeight!==true||current.earHairPosesAndTimingUnchanged!==true
      ||current.newArtworkGeneratedThisIteration!==false||current.sourceAlphaPreservedExactly!==true
      ||current.nativeAlphaPreservedExactly!==false||current.bodyEarHairPosesUnchanged!==false
      ||current.loopSeamRGBAExact!==true||current.visualMotionApproval!=='pending'
      ||current.installed!==false||current.installableFullAtlas!==false
      ||before.failedBodyDevelopmentBasis!==undefined||before.state!=='failed'||before.nativeRow!==5
      ||before.mouthLineVisualApproval!=='approved-as-development-basis'
      ||fields.some(key=>before[key]===undefined||!same(before[key],current[key]))
      ||before.keyframes?.length!==8||current.keyframes?.length!==8
      ||!same(before.keyframes.map(p=>p.bodyY),[.2,.5,.8,1,1,.8,.4,.1])
      ||current.keyframes.some((p,i)=>p.bodyY!==0||p.earAngle!==before.keyframes[i].earAngle
        ||p.hairAngle!==before.keyframes[i].hairAngle)
      ||before.frameHashes?.length!==8||current.frameHashes?.length!==8)
    throw new Error('Failed body comparison must keep accepted mouth source and actual native holds; no human motion approval');
  for(const hashes of [before.frameHashes,current.frameHashes])
    hashes.forEach((_,index)=>candidateCelKey(hashes,index));
  return before;
}

export function validateMouthReference(manifest,baseline,study,current){
  if(manifest.commit!=='c0e3e2fe800424ddf1792fc63792b28248fd9cc5'
      ||manifest.referenceRole!=='frozen-source-input-not-active-animation'
      ||manifest.referencePurpose!=='isolate-internal-mouth-rgb-only'
      ||manifest.file!=='failed.webp'||manifest.contract!=='contract.json'
      ||manifest.fileSha256!=='1C024F7855CB3A08DF20CC769C2F0BC13F71573D2635B188AFC12533D34D3926'
      ||manifest.visualApprovalInherited!==false||manifest.installed!==false||manifest.installableFullAtlas!==false)
    throw new Error('Invalid frozen old-mouth reference');
  if(study.state!=='failed'||study.previewVariant!=='failed_mouth'||study.nativeRow!==5
      ||study.referencePurpose!=='isolate-internal-mouth-rgb-only'
      ||study.adopted!==true||study.adoptionScope!=='mouth-line-development-basis-only'||study.installed!==false
      ||study.mouthLineVisualApproval!=='approved-as-development-basis'
      ||study.currentFailedCelsRGBAExact!==true
      ||study.installableFullAtlas!==false||study.visualMotionApproval!=='pending'
      ||study.animationBuilt!==true||study.facialGeometryRepair!==false||study.newFaceGeometry!==false
      ||study.nativeInterpolation!==false||study.sourceAlphaPreservedExactly!==true
      ||study.nativeAlphaPreservedExactly!==true||study.bodyEarHairPosesUnchanged!==true
      ||study.baselineActualCelsReconstructedExactly!==true||study.frameHashes?.length!==8
      ||current.state!=='failed'||current.nativeRow!==5||current.visualMotionApproval!=='pending'
      ||current.mouthLineVisualApproval!=='approved-as-development-basis'
      ||current.mouthApprovalScope!=='mouth-line-development-basis-only'
      ||current.mouthUserDecision!=='sources/canonical/failed-mouth-decision-20261010.json'
      ||study.userDecision!==current.mouthUserDecision
      ||study.mouthGeneratedSha256!=='695E3EC9867FB8A8A919E203E607A19D0E3A0AA7D469BDEA847B6E56397F3082'
      ||current.mouthGeneratedSha256!==study.mouthGeneratedSha256
      ||current.installed!==false||current.installableFullAtlas!==false
      ||['sourceSha256','camera','durationsMs','keyframes','repeatBeforeIdle'].some(key=>
        current[key]===undefined||JSON.stringify(study[key])!==JSON.stringify(current[key])
          ||JSON.stringify(baseline[key])!==JSON.stringify(current[key]))
      ||JSON.stringify(study.baselineFrameHashes)!==JSON.stringify(baseline.frameHashes)
      ||JSON.stringify(study.frameHashes)!==JSON.stringify(current.frameHashes))
    throw new Error('Mouth reference source/poses/timing or narrow approval boundary mismatch');
  study.frameHashes.forEach((_,index)=>candidateCelKey(study.frameHashes,index));
  current.frameHashes.forEach((_,index)=>candidateCelKey(current.frameHashes,index));
  baseline.frameHashes.forEach((_,index)=>candidateCelKey(baseline.frameHashes,index));
  return baseline;
}

export function validateHopReference(metadata,current){
  validateMaterialSupport(current);
  const fields=['sourceSha256','state','nativeRow','camera','durationsMs','actorOffsetsPx',
    'bodyCompressionOutputPx','tipAnglesDegrees','nativeInterpolation','repeatBeforeIdle'];
  if(current.state!=='jumping'||current.nativeRow!==4
      ||current.groundedContactVersion!=='two-link-source-material-v1'
      ||current.strategyApprovalInheritedFromLocomotion!==false
      ||current.visualMotionApproval!=='pending'||current.originalAirCelsRGBAExact!==true
      ||current.airMaterialIdentityProven!==false
      ||metadata.referenceRole!=='regenerated-counterfactual-not-active-animation'
      ||metadata.referencePurpose!=='isolate-grounded-two-link-knees-vs-vertical-height-field'
      ||metadata.file!=='comparison-old-strip.webp'||metadata.frameHashes?.length!==5
      ||metadata.visualApprovalInherited!==false||metadata.installableFullAtlas!==false||metadata.installed!==false
      ||JSON.stringify(metadata.airCelsRGBAExact)!==JSON.stringify([true,true,true])
      ||JSON.stringify(metadata.airChangedPixels)!==JSON.stringify(current.heightFieldAirChangedPixels)
      ||JSON.stringify(metadata.airMaximumChannelDifference)!==JSON.stringify(current.heightFieldAirMaximumChannelDifference)
      ||current.heightFieldAirMaximumChannelDifference?.length!==3
      ||current.heightFieldAirMaximumChannelDifference.some(n=>n!==0)
      ||JSON.stringify(current.heightFieldAirChangedPixels)!==JSON.stringify([0,0,0])
      ||JSON.stringify(metadata.candidateFrameHashes)!==JSON.stringify(current.frameHashes)
      ||fields.some(key=>current[key]===undefined||JSON.stringify(metadata.contract?.[key])!==JSON.stringify(current[key])))
    throw new Error('Hop comparison source/poses/timing or candidate boundary mismatch');
  metadata.frameHashes.forEach((_,index)=>candidateCelKey(metadata.frameHashes,index));
  current.frameHashes.forEach((_,index)=>candidateCelKey(current.frameHashes,index));
  return metadata;
}
