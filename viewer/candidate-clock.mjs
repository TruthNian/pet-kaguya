import {durations,cycles} from './clock.mjs';

export const candidateRows=Object.freeze({idle:0,failed:5,jumping:4,waving:3,processing:7});
const rows=candidateRows;
export function candidatePoseOffset(mode,index){
  const schedule=mode==='waiting'?[0]:durations[rows[mode]];
  if(!schedule||!Number.isInteger(index)||index<0||index>=schedule.length)throw new Error('invalid candidate pose');
  return schedule.slice(0,index).reduce((a,b)=>a+b,0);
}
export function candidateSlot(mode,elapsed){
  if(![...Object.keys(rows),'waiting'].includes(mode)||!Number.isFinite(elapsed))throw new Error('invalid candidate clock');
  if(mode==='waiting')return {state:'waiting',index:0,static:true,completedAction:false};
  let time=Math.max(0,elapsed),state=mode,completedAction=false;
  if(mode!=='idle'&&time>=3*cycles[rows[mode]]){state='idle';time-=3*cycles[rows[mode]];completedAction=true;}
  const schedule=durations[rows[state]],cycle=cycles[rows[state]];
  time%=cycle;
  let index=0,offset=0;
  while(time>=offset+schedule[index])offset+=schedule[index++];
  return {state,index,static:false,completedAction,holdMs:schedule[index],cycleMs:cycle,untilNext:offset+schedule[index]-time};
}
