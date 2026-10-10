import test from 'node:test';
import assert from 'node:assert/strict';
import {reviewSchedule,reviewChapters} from '../viewer/whole-review-clock.mjs';
import {durations} from '../viewer/clock.mjs';

test('whole review covers real holds, three-cycle idle returns and separately labelled direction holds',()=>{
  const steps=reviewSchedule();
  for(const chapter of reviewChapters.slice(0,-1)){
    const action=steps.filter(step=>step.chapter===chapter&&!step.after),row=action[0].row;
    const repeats=row===0?1:3;
    assert.deepEqual(action.map(step=>step.holdMs),Array.from({length:repeats},()=>durations[row]).flat());
    assert.deepEqual(action.map(step=>step.index),Array.from({length:repeats},()=>durations[row].map((_,i)=>i)).flat());
    if(row!==0){const end=steps.filter(step=>step.chapter===chapter).at(-1);assert.equal(end.state,'idle');assert.equal(end.holdMs,1680);}
  }
  const look=steps.filter(step=>step.state==='look');
  assert.deepEqual(look.map(step=>[step.row,step.index,step.direction,step.holdMs]),Array.from({length:16},(_,i)=>[9+Math.floor(i/8),i%8,i,600]));
  assert(steps.every(step=>step.index>=0&&step.index<8&&step.row>=0&&step.row<11));
  assert.equal(steps.reduce((n,step)=>n+step.holdMs,0),54540);
  assert.equal(steps.at(-1).state,'idle');
});
