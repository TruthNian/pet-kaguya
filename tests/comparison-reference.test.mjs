import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {comparisonReference,validateRigidReference,validateHopReference,validateMouthReference} from '../viewer/comparison-reference.mjs';
import {candidateSlot,candidatePoseOffset} from '../viewer/candidate-clock.mjs';
import {durations} from '../viewer/clock.mjs';

const metadata=JSON.parse(readFileSync(new URL('../sources/reference/locomotion-rigid/manifest.json',import.meta.url),'utf8'));

test('archived rigid comparisons retain their original eye-material epoch',()=>{
  for(const state of ['run_right','run_left']){
    const current=JSON.parse(readFileSync(new URL(`../sources/reference/gaze-action-v1/${state}.json`,import.meta.url),'utf8'));
    const entry=validateRigidReference(metadata,state,current);
    assert.equal(entry.file,`${state}.webp`);assert.equal(entry.frameHashes.length,8);
  }
  assert.equal(metadata.visualApprovalInherited,false);
});
test('actual quieter eye flow cannot masquerade as the old single-factor rigid comparison',()=>{
  for(const state of ['run_right','run_left']){
    const current=JSON.parse(readFileSync(new URL(`../candidates/phase5/${state}/build.json`,import.meta.url),'utf8'));
    assert.throws(()=>validateRigidReference(metadata,state,current));
  }
});

test('one selected native slot drives both sides at every hold and three-cycle fallback',()=>{
  for(const [state,row] of [['run_right',1],['run_left',2]]){
    for(let cycle=0;cycle<3;cycle++)for(let index=0;index<8;index++){
      const start=cycle*1060+candidatePoseOffset(state,index);
      for(const time of [start,start+durations[row][index]-.001]){
        const selected=candidateSlot(state,time),reference=comparisonReference('rigid',selected.state,selected.index);
        assert.equal(reference.kind,'rigid');assert.equal(reference.state,state);
        assert.equal(reference.index,selected.index);assert.equal(reference.synchronized,true);
      }
    }
    for(const time of [3180,3180+1680,3180+6600,999999]){
      const selected=candidateSlot(state,time),reference=comparisonReference('rigid',selected.state,selected.index);
      assert.equal(selected.state,'idle');assert.equal(reference.state,'idle');
      assert.equal(reference.index,selected.index);assert.equal(reference.kind,'candidate');
    }
  }
});

test('manual and reduced-motion slots are shared; identity reference remains explicitly static',()=>{
  for(const state of ['run_right','run_left'])for(let index=0;index<8;index++)
    assert.equal(comparisonReference('rigid',state,index).index,index);
  for(const [state,index] of [['waiting',5],['run_right',7],['idle',4]])
    assert.deepEqual(comparisonReference('idle',state,index),{kind:'candidate',state:'idle',index:0,synchronized:false});
});

test('changed root, feet, focus, source, camera or schedule cannot masquerade as the same-pose comparison',()=>{
  const current=structuredClone(metadata.states.run_right.contract);
  for(const key of Object.keys(current)){
    const changed=structuredClone(current);changed[key]=null;
    assert.throws(()=>validateRigidReference(metadata,'run_right',changed));
  }
  for(const [key,value] of [['commit','bad'],['visualApprovalInherited',true],['installableFullAtlas',true],
    ['installed',true],['referenceRole','current-approved-animation']]){
    const changed=structuredClone(metadata);changed[key]=value;
    assert.throws(()=>validateRigidReference(changed,'run_right',current));
  }
  const changed=structuredClone(metadata);changed.states.run_right.frameHashes[0]='bad';
  assert.throws(()=>validateRigidReference(changed,'run_right',current));
});

test('invalid references and indices fail before selecting a misleading cel',()=>{
  for(const [choice,state,index] of [['phase3','idle',0],['rigid','waiting',0],['rigid','run_left',8],
    ['idle','idle',6],['rigid','run_right',.5],['rigid','run_right',NaN],['idle','none',0]])
    assert.throws(()=>comparisonReference(choice,state,index));
});

const hop=JSON.parse(readFileSync(new URL('../candidates/phase5/jumping/build.json',import.meta.url),'utf8'));
const contact=JSON.parse(readFileSync(new URL('../candidates/phase5/jumping/contact-proof.json',import.meta.url),'utf8'));
test('actual two-link hop and old-height-field reference have the same source, poses and native holds',()=>{
  assert.equal(validateHopReference(contact,hop),contact);
  assert.deepEqual(contact.airCelsRGBAExact,[true,true,true]);
  assert.deepEqual(contact.airMaximumChannelDifference,[0,0,0]);
  assert.equal(contact.visualApprovalInherited,false);
  assert.equal(hop.strategyApprovalInheritedFromLocomotion,false);
  for(const key of Object.keys(contact.contract)){
    const changed=structuredClone(hop);changed[key]=null;
    assert.throws(()=>validateHopReference(contact,changed));
  }
  for(const [key,value] of [['referenceRole','approved-old-pet'],['visualApprovalInherited',true],
    ['installed',true],['file','bad.webp'],['airCelsRGBAExact',[false,true,false]]]){
    assert.throws(()=>validateHopReference({...contact,[key]:value},hop));
  }
  assert.throws(()=>validateHopReference({...contact,candidateFrameHashes:contact.frameHashes},hop));
  assert.throws(()=>validateHopReference(contact,{...hop,groundedContactVersion:'old-height-field'}));
});
test('same hop slot drives the counterfactual at every hold and synchronous three-cycle idle fallback',()=>{
  for(let cycle=0;cycle<3;cycle++)for(let index=0;index<5;index++){
    const start=cycle*840+candidatePoseOffset('jumping',index);
    for(const time of [start,start+durations[4][index]-.001]){
      const selected=candidateSlot('jumping',time),reference=comparisonReference('contact',selected.state,selected.index);
      assert.deepEqual(reference,{kind:'contact',state:'jumping',index,synchronized:true});
    }
  }
  for(const time of [2520,2520+1680,999999]){
    const selected=candidateSlot('jumping',time),reference=comparisonReference('contact',selected.state,selected.index);
    assert.equal(selected.state,'idle');assert.equal(reference.state,'idle');
    assert.equal(reference.kind,'candidate');assert.equal(reference.index,selected.index);
  }
});
test('manual hop reference shares the exact frame and cannot silently select gait or unrelated actions',()=>{
  for(let index=0;index<5;index++)assert.equal(comparisonReference('contact','jumping',index).index,index);
  for(const [choice,state,index] of [['contact','jumping',5],['contact','waiting',0],
    ['contact','run_right',0],['rigid','jumping',0],['contact','jumping',.5]])
    assert.throws(()=>comparisonReference(choice,state,index));
});

const currentFailed=JSON.parse(readFileSync(new URL('../candidates/phase5/failed/build.json',import.meta.url),'utf8'));
const mouthStudy=JSON.parse(readFileSync(new URL('../candidates/phase5/failed-mouth-v2/animation/build.json',import.meta.url),'utf8'));
const mouthManifest=JSON.parse(readFileSync(new URL('../sources/reference/failed-mouth-v1/manifest.json',import.meta.url),'utf8'));
const oldMouth=JSON.parse(readFileSync(new URL('../sources/reference/failed-mouth-v1/contract.json',import.meta.url),'utf8'));
test('accepted mouth and frozen old mouth share poses without broadening human approval',()=>{
  const validate=(study=mouthStudy,current=currentFailed,baseline=oldMouth,manifest=mouthManifest)=>
    validateMouthReference(manifest,baseline,study,current);
  assert.equal(validate(),oldMouth);
  for(const field of ['sourceSha256','camera','durationsMs','keyframes','repeatBeforeIdle','frameHashes']){
    const altered=structuredClone(currentFailed);altered[field]=null;
    assert.throws(()=>validate(mouthStudy,altered));
    const oldAltered=structuredClone(oldMouth);oldAltered[field]=null;
    assert.throws(()=>validate(mouthStudy,currentFailed,oldAltered));
  }
  for(const [field,value] of [['adopted',false],['adoptionScope','full-motion'],['installed',true],
    ['visualMotionApproval','approved'],['sourceAlphaPreservedExactly',false],
    ['bodyEarHairPosesUnchanged',false],['baselineFrameHashes',mouthStudy.frameHashes],['frameHashes',['bad']]]){
    assert.throws(()=>validate({...mouthStudy,[field]:value}));
  }
  for(const [field,value] of [['mouthApprovalScope','full-motion'],['mouthLineVisualApproval','approved'],
    ['mouthUserDecision','different.json'],['mouthGeneratedSha256','bad'],['installed',true]])
    assert.throws(()=>validate(mouthStudy,{...currentFailed,[field]:value}));
  for(const [field,value] of [['file','bad.webp'],['visualApprovalInherited',true],['commit','bad'],['fileSha256','bad']])
    assert.throws(()=>validate(mouthStudy,currentFailed,oldMouth,{...mouthManifest,[field]:value}));
});
test('old and accepted failed mouths share all eight native holds and three-cycle fallback',()=>{
  for(let cycle=0;cycle<3;cycle++)for(let index=0;index<8;index++){
    const start=cycle*1220+candidatePoseOffset('failed',index);
    for(const time of [start,start+durations[5][index]-.001]){
      const slot=candidateSlot('failed',time);
      assert.deepEqual(comparisonReference('mouth',slot.state,slot.index),
        {kind:'mouth',state:'failed',index,synchronized:true});
      assert.equal(slot.index,candidateSlot('failed',time).index);
    }
  }
  for(const time of [3660,3660+1680,999999]){
    const slot=candidateSlot('failed',time),reference=comparisonReference('mouth',slot.state,slot.index);
    assert.equal(slot.state,'idle');assert.equal(reference.state,'idle');assert.equal(reference.index,slot.index);
  }
  for(const state of ['waiting','jumping','run_right'])assert.throws(()=>comparisonReference('mouth',state,0));
});
