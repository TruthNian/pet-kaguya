import {lookIndex} from './clock.mjs';

export function gazeFrame(index){
  if(index===null)return {neutral:true,x:0,y:0,row:null,col:null};
  if(!Number.isInteger(index)||index<0||index>15)throw new Error('invalid gaze direction');
  return {neutral:false,x:index%8*192,y:Math.floor(index/8)*208,row:9+Math.floor(index/8),col:index%8};
}
export function pointerGaze(dx,dy){
  if(!Number.isFinite(dx)||!Number.isFinite(dy))throw new Error('invalid pointer delta');
  const native=lookIndex(dx,dy);
  return native===null?null:(native.row-9)*8+native.col;
}
