// Independent rule simulator: no copied application code, no native-host patch.
export const states = ['idle','run_right','run_left','waving','jumping','failed','waiting','running','review'];
export const durations = [
  [1680,660,660,840,840,1920], [120,120,120,120,120,120,120,220],
  [120,120,120,120,120,120,120,220], [140,140,140,280],
  [140,140,140,140,280], [140,140,140,140,140,140,140,240],
  [150,150,150,150,150,260], [120,120,120,120,120,220],
  [150,150,150,150,150,280]
];
export const cycles=durations.map(row=>row.reduce((a,b)=>a+b,0));
export function lookIndex(dx,dy) {
  if(Math.hypot(dx,dy)<=1) return null;
  const degrees=(Math.atan2(dx,-dy)*180/Math.PI+360)%360;
  const i=Math.round(degrees/22.5)%16;
  return {row:9+Math.floor(i/8),col:i%8,kind:'look'};
}
export function frameAt(state,elapsed,{loop=false,reduced=false,look=null}={}) {
  const row=states.indexOf(state);
  if(row<0||!Number.isFinite(elapsed)) throw new Error('invalid state or elapsed');
  if(look!==null&&['idle','running','waving'].includes(state)) return look;
  if(reduced) return {row,col:0,kind:'reduced'};
  let selected=row,time=Math.max(0,elapsed);
  if(row!==0&&!loop&&time>=3*cycles[row]) {
    selected=0;time-=3*cycles[row];
  }
  time%=cycles[selected];
  let col=0,acc=0;
  for(const d of durations[selected]) {
    if(time<acc+d) break;
    acc+=d;col++;
  }
  return {row:selected,col,kind:'animation'};
}
