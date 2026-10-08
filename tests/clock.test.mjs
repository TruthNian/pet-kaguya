import test from 'node:test';
import assert from 'node:assert/strict';
import {frameAt,lookIndex,cycles,states,durations} from '../viewer/clock.mjs';

test('all exact frame boundaries, long cycles, and loop seams',()=>{
  for(let row=0;row<9;row++) {
    let elapsed=0;
    durations[row].forEach((d,col)=>{
      assert.equal(frameAt(states[row],elapsed,{loop:true}).col,col);
      assert.equal(frameAt(states[row],elapsed+d-.001,{loop:true}).col,col);
      elapsed+=d;
    });
    assert.equal(frameAt(states[row],cycles[row],{loop:true}).col,0);
    assert.deepEqual(frameAt(states[row],cycles[row]*10000000+17,{loop:true}),frameAt(states[row],17,{loop:true}));
  }
});
test('action falls back only after three full loops',()=>{
  for(let row=1;row<9;row++) {
    assert.equal(frameAt(states[row],cycles[row]*3-.001).row,row);
    assert.deepEqual(frameAt(states[row],cycles[row]*3),{row:0,col:0,kind:'animation'});
    assert.equal(frameAt(states[row],cycles[row]*3+1680).col,1);
  }
});
test('idle six-times timing is used, not the fast base schedule',()=>{
  assert.equal(cycles[0],6600);
  assert.equal(frameAt('idle',1100).col,0);
  assert.equal(frameAt('idle',1680).col,1);
});
test('pointer sectors, wrap, and dead zone',()=>{
  assert.equal(lookIndex(0,0),null);
  assert.equal(lookIndex(1,0),null);
  assert.deepEqual(lookIndex(0,-10),{row:9,col:0,kind:'look'});
  assert.deepEqual(lookIndex(10,0),{row:9,col:4,kind:'look'});
  assert.deepEqual(lookIndex(0,10),{row:10,col:0,kind:'look'});
  assert.deepEqual(lookIndex(-10,0),{row:10,col:4,kind:'look'});
  assert.equal(lookIndex(-.01,-10).col,0);
});
test('pointer look overrides only the documented eligible states',()=>{
  const look=lookIndex(10,0);
  for(const state of states) {
    assert.equal(frameAt(state,100,{look}).kind,['idle','running','waving'].includes(state)?'look':'animation');
  }
});
test('reduced motion is static; elapsed time never chooses a missing cell',()=>{
  for(let row=0;row<9;row++) {
    assert.equal(frameAt(states[row],180000,{reduced:true}).col,0);
    for(let t=0;t<10000;t+=17) {
      const f=frameAt(states[row],t);
      assert.ok(f.col>=0&&f.col<durations[f.row].length);
    }
  }
});
test('invalid inputs reject, negative time is clamped',()=>{
  assert.throws(()=>frameAt('missing',10));
  assert.throws(()=>frameAt('idle',NaN));
  assert.equal(frameAt('idle',-10).col,0);
});
