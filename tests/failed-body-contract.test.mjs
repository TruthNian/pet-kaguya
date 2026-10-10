import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {comparisonReference,comparisonPolicy,validateFailedBodyReference} from '../viewer/comparison-reference.mjs';
import {candidateSlot,candidatePoseOffset} from '../viewer/candidate-clock.mjs';
const load=path=>JSON.parse(readFileSync(new URL(path,import.meta.url),'utf8'));
const before=load('../sources/reference/failed-body-before/build.json');
const current=load('../candidates/phase5/failed/build.json');

test('failed body hold preserves accepted source mouth, ears and real holds without human motion approval',()=>{
  assert.equal(validateFailedBodyReference(before,current),before);
  assert.equal(current.mouthPoseRGBAHash,before.mouthPoseRGBAHash);
  assert.deepEqual(current.keyframes.map(p=>p.bodyY),Array(8).fill(0));
  assert.deepEqual(comparisonPolicy('failed','mouth',true),{allowed:['idle','calm'],choice:'calm'});
  for(const [key,value] of [['mouthPoseRGBAHash','bad'],['nativeAlphaPreservedExactly',true],
      ['bodyMotionUserApprovalClaimed',true],['bodyMotionUserApproval','approved'],['durationsMs',[]]])
    assert.throws(()=>validateFailedBodyReference(before,{...current,[key]:value}));
  const changed=structuredClone(current);changed.keyframes[3].bodyY=1;
  assert.throws(()=>validateFailedBodyReference(before,changed));
});
test('same eight holds and three-cycle fallback drive old body and calm body together',()=>{
  for(let cycle=0;cycle<3;cycle++)for(let index=0;index<8;index++){
    const slot=candidateSlot('failed',cycle*1220+candidatePoseOffset('failed',index));
    assert.deepEqual(comparisonReference('calm',slot.state,slot.index),
      {kind:'failed-before',state:'failed',index,synchronized:true});
  }
  const slot=candidateSlot('failed',3660);
  assert.equal(slot.state,'idle');
  assert.deepEqual(comparisonReference('calm',slot.state,slot.index),
    {kind:'candidate',state:'idle',index:slot.index,synchronized:true});
});
