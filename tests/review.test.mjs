import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {reviewCell,reviewStates} from '../viewer/review.mjs';
import {validateReviewMetadata} from '../viewer/review-contract.mjs';

test('static review does not silently compare waiting with an unrelated source row',()=>{
  assert.deepEqual(reviewCell('waiting','source'),{row:7,col:1});
  assert.deepEqual(reviewCell('waving','source'),{row:3,col:1});
  assert.deepEqual(reviewCell('review','source'),{row:8,col:2});
  assert.deepEqual(reviewCell('failed','source'),{row:5,col:0});
});
test('historical versions retain their own static state coordinates',()=>{
  for(const baseline of ['phase2','phase3'])for(const [row,state] of reviewStates.entries()){
    assert.deepEqual(reviewCell(state,baseline),{row,col:0});
  }
});
test('static review selections reject invalid values',()=>{
  assert.throws(()=>reviewCell('unknown','phase3'),RangeError);
  assert.throws(()=>reviewCell('idle','unknown'),RangeError);
});

test('the actual viewer accepts the current restored-hair composition metadata',()=>{
  const metadata=JSON.parse(readFileSync(new URL('../candidates/phase5/review/build.json',import.meta.url),'utf8'));
  assert.equal(validateReviewMetadata(metadata),metadata);
  assert.equal(metadata.rightArmCompositionVersion,'review-art-v5');
  assert.equal(metadata.observedHairAlphaHolesRestored,true);
});

test('old or incomplete composition and art/motion overclaims still fail the viewer contract',()=>{
  const metadata=JSON.parse(readFileSync(new URL('../candidates/phase5/review/build.json',import.meta.url),'utf8'));
  for(const [field,value] of [['rightArmCompositionVersion','review-art-v4'],
    ['observedHairAlphaHolesRestored',false],['knownSourceHairRGBAExact',false],
    ['handScaled',true],['visualMotionApproval','approved'],['strategyUserApproval','approved'],
    ['nativeRow',6],['repeatBeforeIdle',1],['newArtworkGenerated',true]]){
    assert.throws(()=>validateReviewMetadata({...metadata,[field]:value}),/boundary mismatch/);
  }
  assert.throws(()=>validateReviewMetadata(null));
});
