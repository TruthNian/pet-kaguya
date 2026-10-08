import {states} from './clock.mjs';

export const baselineUrls={phase2:'../baseline/phase2/spritesheet.webp',
  phase3:'../baseline/phase3/spritesheet.webp',source:'../sources/pre-expression/spritesheet.webp'};
export const baselineLabels={phase2:'Phase 2 可用基准',phase3:'Phase 3 旧候选',source:'未拼接源图'};
export const reviewStates=states.slice(0,9);

export function reviewCell(state,baseline){
  const row=reviewStates.indexOf(state);
  if(row<0||!(baseline in baselineUrls))throw new RangeError('Invalid static review selection');
  // Show the ACTUAL body source when the user chooses provenance comparison.
  if(baseline==='source'){
    if(row===6)return {row:7,col:1};
    if(row===3)return {row:3,col:1};
    if(row===8)return {row:8,col:2};
  }
  return {row,col:0};
}
