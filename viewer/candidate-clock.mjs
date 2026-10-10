import {durations,cycles} from './clock.mjs';

// Trial variants reuse existing native rows; they are not additional pet states.
export const candidateRows=Object.freeze({idle:0,run_right:1,run_left:2,failed:5,jumping:4,waving:3,waving_source:3,waiting:6,processing:7,review:8});
const rows=candidateRows;
export function candidateCelKey(hashes,index){
  if(!Array.isArray(hashes)||!Number.isInteger(index)||index<0||index>=hashes.length
      ||typeof hashes[index]!=='string'||!/^[A-F0-9]{64}$/.test(hashes[index]))throw new Error('invalid candidate cel hash');
  return hashes[index];
}
export function candidatePoseOffset(mode,index){
  const schedule=durations[rows[mode]];
  if(!schedule||!Number.isInteger(index)||index<0||index>=schedule.length)throw new Error('invalid candidate pose');
  return schedule.slice(0,index).reduce((a,b)=>a+b,0);
}
export function candidateSlot(mode,elapsed){
  if(!Object.keys(rows).includes(mode)||!Number.isFinite(elapsed))throw new Error('invalid candidate clock');
  let time=Math.max(0,elapsed),state=mode,completedAction=false;
  if(mode!=='idle'&&time>=3*cycles[rows[mode]]){state='idle';time-=3*cycles[rows[mode]];completedAction=true;}
  const schedule=durations[rows[state]],cycle=cycles[rows[state]];
  time%=cycle;
  let index=0,offset=0;
  while(time>=offset+schedule[index])offset+=schedule[index++];
  return {state,index,static:false,completedAction,holdMs:schedule[index],cycleMs:cycle,untilNext:offset+schedule[index]-time};
}
