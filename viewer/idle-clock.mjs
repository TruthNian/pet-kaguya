import {durations,cycles} from './clock.mjs';

export function idleSlot(elapsed){
  if(!Number.isFinite(elapsed))throw new RangeError('Invalid idle elapsed time');
  const t=Math.max(0,elapsed)%cycles[0];
  let start=0;
  for(let index=0;index<durations[0].length;index++){
    const end=start+durations[0][index];
    if(t<end)return {index,untilNext:end-t,cycleTime:t};
    start=end;
  }
  throw new RangeError('Invalid idle schedule');
}

export function idlePoseOffset(index){
  if(!Number.isInteger(index)||index<0||index>=durations[0].length)throw new RangeError('Invalid idle pose');
  return durations[0].slice(0,index).reduce((a,b)=>a+b,0);
}
