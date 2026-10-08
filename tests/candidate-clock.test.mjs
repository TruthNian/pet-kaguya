import test from 'node:test';
import assert from 'node:assert/strict';
import {candidateSlot,candidatePoseOffset} from '../viewer/candidate-clock.mjs';
import {durations,cycles,frameAt} from '../viewer/clock.mjs';

test('failed candidate uses all real holds and exactly three loops before idle',()=>{
  for(let round=0;round<3;round++)for(let index=0;index<8;index++){
    const offset=round*cycles[5]+candidatePoseOffset('failed',index);
    for(const time of [offset,offset+durations[5][index]-.001]){
      const actual=candidateSlot('failed',time),expected=frameAt('failed',time);
      assert.equal(actual.state,'failed');assert.equal(actual.index,expected.col);
      assert.equal(actual.completedAction,false);assert.ok(actual.untilNext>0);
    }
  }
  for(const time of [3660,3660+1680,3660+6600,3660+6600*100+.5]){
    const actual=candidateSlot('failed',time),expected=frameAt('failed',time);
    assert.equal(actual.state,'idle');assert.equal(actual.index,expected.col);assert.equal(actual.completedAction,true);
  }
});
test('idle clock and waiting static never invent an animated waiting row',()=>{
  for(let time=0;time<40000;time+=37.5)assert.equal(candidateSlot('idle',time).index,frameAt('idle',time).col);
  assert.deepEqual(candidateSlot('waiting',999999),{state:'waiting',index:0,static:true,completedAction:false});
  assert.equal(candidatePoseOffset('waiting',0),0);
});
test('hop uses five real holds and three loops, then returns to the actual idle clock',()=>{
  for(let round=0;round<3;round++)for(let index=0;index<5;index++){
    const offset=round*cycles[4]+candidatePoseOffset('jumping',index);
    for(const time of [offset,offset+durations[4][index]-.001]){
      const actual=candidateSlot('jumping',time),expected=frameAt('jumping',time);
      assert.equal(actual.state,'jumping');assert.equal(actual.index,expected.col);
      assert.equal(actual.completedAction,false);assert.ok(actual.untilNext>0);
    }
  }
  for(const time of [2520,2520+1680,2520+6600,2520+6600*100+.5]){
    const actual=candidateSlot('jumping',time),expected=frameAt('jumping',time);
    assert.equal(actual.state,'idle');assert.equal(actual.index,expected.col);assert.equal(actual.completedAction,true);
  }
});
test('invalid states, manual frames and elapsed values fail closed',()=>{
  for(const mode of ['phase3','running','none'])assert.throws(()=>candidateSlot(mode,0));
  for(const time of [NaN,Infinity,-Infinity])assert.throws(()=>candidateSlot('failed',time));
  for(const [mode,index] of [['failed',8],['jumping',5],['idle',6],['waiting',1],['idle',.5],['failed',-1]])assert.throws(()=>candidatePoseOffset(mode,index));
  assert.equal(candidateSlot('failed',-1).index,0);
});
