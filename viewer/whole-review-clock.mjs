import {durations} from './clock.mjs';

// One authored walkthrough, not a native-host recording or extra pet state.
export const reviewChapters=['idle','waving','run_right','run_left','jumping','failed','waiting','processing','review','look'];
const rows={idle:0,run_right:1,run_left:2,waving:3,jumping:4,failed:5,waiting:6,processing:7,review:8};
export function reviewSchedule(){
  const steps=[];
  for(const chapter of reviewChapters.slice(0,-1)){
    const row=rows[chapter];
    for(let cycle=0;cycle<(row===0?1:3);cycle++)
      durations[row].forEach((holdMs,index)=>steps.push({chapter,state:chapter,row,index,holdMs,cycle:cycle+1}));
    if(row!==0)steps.push({chapter,state:'idle',row:0,index:0,holdMs:durations[0][0],after:chapter});
  }
  // A direction is a static pointer selection; its 600ms demonstration hold
  // is explicitly not an animation duration supplied by the installed host.
  for(let i=0;i<16;i++)steps.push({chapter:'look',state:'look',row:9+Math.floor(i/8),index:i%8,holdMs:600,direction:i});
  steps.push({chapter:'look',state:'idle',row:0,index:0,holdMs:durations[0][0],after:'look'});
  return steps;
}
