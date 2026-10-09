import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {comparisonReference,validateRigidReference} from '../viewer/comparison-reference.mjs';
import {candidateSlot,candidatePoseOffset} from '../viewer/candidate-clock.mjs';
import {durations} from '../viewer/clock.mjs';

const metadata=JSON.parse(readFileSync(new URL('../sources/reference/locomotion-rigid/manifest.json',import.meta.url),'utf8'));

test('actual archived contracts match both current native rows without inheriting art approval',()=>{
  for(const state of ['run_right','run_left']){
    const current=JSON.parse(readFileSync(new URL(`../candidates/phase5/${state}/build.json`,import.meta.url),'utf8'));
    const entry=validateRigidReference(metadata,state,current);
    assert.equal(entry.file,`${state}.webp`);assert.equal(entry.frameHashes.length,8);
  }
  assert.equal(metadata.visualApprovalInherited,false);
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

test('changed root, feet, focus, source, camera or schedule cannot silently masquerade as a one-factor comparison',()=>{
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
