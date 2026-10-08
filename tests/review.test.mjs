import test from 'node:test';
import assert from 'node:assert/strict';
import {reviewCell,reviewStates} from '../viewer/review.mjs';

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
