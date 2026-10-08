import test from 'node:test';
import assert from 'node:assert/strict';
import {idleSlot,idlePoseOffset} from '../viewer/idle-clock.mjs';
import {frameAt,durations,cycles} from '../viewer/clock.mjs';

test('idle deadlines agree with every actual native frame boundary',()=>{
  for(let i=0;i<6;i++){
    const start=idlePoseOffset(i),end=start+durations[0][i];
    assert.equal(idleSlot(start).index,i);
    assert.equal(idleSlot(end-.01).index,i);
    assert.equal(idleSlot(start).untilNext,durations[0][i]);
    assert.equal(idleSlot(end).index,(i+1)%6);
  }
});
test('late timers and long playback select native pose without invented frames',()=>{
  for(const t of [0,1680,3225,6600,cycles[0]*12345+4701,1e10,-5]){
    assert.equal(idleSlot(t).index,frameAt('idle',t).col);
    assert.ok(idleSlot(t).untilNext>0);
    assert.ok(idleSlot(t).untilNext<=1920);
  }
});
test('illegal manual indices and elapsed values are rejected',()=>{
  for(const i of [-1,6,1.5,NaN])assert.throws(()=>idlePoseOffset(i),RangeError);
  for(const t of [Infinity,NaN])assert.throws(()=>idleSlot(t),RangeError);
});
