import test from 'node:test';
import assert from 'node:assert/strict';
import {candidateSlot,candidatePoseOffset,candidateCelKey} from '../viewer/candidate-clock.mjs';
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
test('idle candidate clock agrees with native idle over long playback',()=>{
  for(let time=0;time<40000;time+=37.5)assert.equal(candidateSlot('idle',time).index,frameAt('idle',time).col);
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
  for(const [mode,index] of [['failed',8],['jumping',5],['waving',4],['processing',6],['review',6],['idle',6],['waiting',6],['idle',.5],['failed',-1]])assert.throws(()=>candidatePoseOffset(mode,index));
  assert.equal(candidateSlot('failed',-1).index,0);
});

test('built waiting row uses six real holds and three cycles, never stays static by accident',()=>{
  assert.deepEqual(durations[6],[150,150,150,150,150,260]);
  assert.equal(cycles[6],1010);
  for(let round=0;round<3;round++)for(let index=0;index<6;index++){
    const offset=round*1010+candidatePoseOffset('waiting',index);
    for(const time of [offset,offset+durations[6][index]-.001]){
      const actual=candidateSlot('waiting',time),expected=frameAt('waiting',time);
      assert.equal(actual.state,'waiting');assert.equal(actual.index,expected.col);
      assert.equal(actual.static,false);assert.equal(actual.completedAction,false);
      assert.equal(actual.holdMs,durations[6][index]);assert.ok(actual.untilNext>0);
    }
  }
  for(const time of [3030,3030+1680,3030+6600,999999]){
    const actual=candidateSlot('waiting',time),expected=frameAt('waiting',time);
    assert.equal(actual.state,'idle');assert.equal(actual.index,expected.col);
    assert.equal(actual.completedAction,true);
  }
});

test('review uses row eight native holds and falls back after exactly 3090 ms',()=>{
  assert.deepEqual(durations[8],[150,150,150,150,150,280]);
  assert.equal(cycles[8],1030);
  for(let round=0;round<3;round++)for(let index=0;index<6;index++){
    const offset=round*1030+candidatePoseOffset('review',index);
    for(const time of [offset,offset+durations[8][index]-.001]){
      const actual=candidateSlot('review',time),expected=frameAt('review',time);
      assert.equal(actual.state,'review');assert.equal(actual.index,expected.col);
      assert.equal(actual.static,false);assert.equal(actual.completedAction,false);
      assert.equal(actual.holdMs,durations[8][index]);assert.ok(actual.untilNext>0);
    }
  }
  for(const time of [3090,3090+1680,3090+6600,999999]){
    const actual=candidateSlot('review',time),expected=frameAt('review',time);
    assert.equal(actual.state,'idle');assert.equal(actual.index,expected.col);
    assert.equal(actual.completedAction,true);
  }
});

test('processing means native running row, six real holds and three cycles then idle',()=>{
  assert.deepEqual(durations[7],[120,120,120,120,120,220]);
  assert.equal(cycles[7],820);
  for(let round=0;round<3;round++)for(let index=0;index<6;index++){
    const offset=round*820+candidatePoseOffset('processing',index);
    for(const time of [offset,offset+durations[7][index]-.001]){
      const actual=candidateSlot('processing',time),expected=frameAt('running',time);
      assert.equal(actual.state,'processing');assert.equal(actual.index,expected.col);
      assert.equal(actual.completedAction,false);assert.equal(actual.holdMs,durations[7][index]);
      assert.ok(actual.untilNext>0);
    }
  }
  for(const time of [2460,2460+1680,2460+6600,2460+6600*100+.5]){
    const actual=candidateSlot('processing',time),expected=frameAt('running',time);
    assert.equal(actual.state,'idle');assert.equal(actual.index,expected.col);
    assert.equal(actual.completedAction,true);
  }
});

test('wave uses four real holds with a 280 ms rest, exactly three cycles then idle',()=>{
  assert.deepEqual(durations[3],[140,140,140,280]);
  assert.equal(cycles[3],700);
  for(let round=0;round<3;round++)for(let index=0;index<4;index++){
    const offset=round*700+candidatePoseOffset('waving',index);
    for(const time of [offset,offset+durations[3][index]-.001]){
      const actual=candidateSlot('waving',time),expected=frameAt('waving',time);
      assert.equal(actual.state,'waving');assert.equal(actual.index,expected.col);
      assert.equal(actual.completedAction,false);assert.equal(actual.holdMs,durations[3][index]);
      assert.ok(actual.untilNext>0);
    }
  }
  for(const time of [2100,2100+1680,2100+6600,2100+6600*100+.5]){
    const actual=candidateSlot('waving',time),expected=frameAt('waving',time);
    assert.equal(actual.state,'idle');assert.equal(actual.index,expected.col);
    assert.equal(actual.completedAction,true);
  }
});

test('left/right drag-feedback rows use real eight holds only while the row is uninterrupted',()=>{
  for(const [mode,row] of [['run_right',1],['run_left',2]]){
    assert.deepEqual(durations[row],[120,120,120,120,120,120,120,220]);
    assert.equal(cycles[row],1060);
    for(let round=0;round<3;round++)for(let index=0;index<8;index++){
      const start=round*1060+candidatePoseOffset(mode,index);
      for(const time of [start,start+durations[row][index]-.001]){
        const actual=candidateSlot(mode,time),expected=frameAt(mode,time);
        assert.equal(actual.state,mode);assert.equal(actual.index,expected.col);
        assert.equal(actual.completedAction,false);assert.ok(actual.untilNext>0);
      }
    }
    for(const time of [3180,3180+1680,3180+6600,999999]){
      const actual=candidateSlot(mode,time),expected=frameAt(mode,time);
      assert.equal(actual.state,'idle');assert.equal(actual.index,expected.col);
      assert.equal(actual.completedAction,true);
    }
    assert.throws(()=>candidatePoseOffset(mode,8));
  }
  // This pure row clock has no live drag input/velocity. These assertions
  // intentionally do NOT certify arbitrary host drag-release transitions.
});

test('identical cels still advance native time slots but do not require another canvas paint',()=>{
  const [a,b,c,d,e]=['A','B','C','D','E'].map(value=>value.repeat(64));
  const hashes=[a,b,c,a,a,d,e,a];
  let previous=null,paints=0;
  for(let index=0;index<8;index++){
    const key=candidateCelKey(hashes,index);
    if(key!==previous)paints++;
    previous=key;
    assert.equal(candidateSlot('run_right',candidatePoseOffset('run_right',index)).index,index);
  }
  assert.equal(paints,7); // Only consecutive identical display content is skipped, not necessary repeated poses.
  assert.throws(()=>candidateCelKey(['bad'],0));
  assert.throws(()=>candidateCelKey([a],1));assert.throws(()=>candidateCelKey([a],.5));
  assert.throws(()=>candidateCelKey(null,0));
});
