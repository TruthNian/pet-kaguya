import test from 'node:test';
import assert from 'node:assert/strict';
import {gazeFrame,pointerGaze} from '../viewer/gaze-frame.mjs';

test('all sixteen gaze cells map to native rows without mirroring or missing cells',()=>{
  for(let i=0;i<16;i++)assert.deepEqual(gazeFrame(i),{neutral:false,x:i%8*192,y:Math.floor(i/8)*208,row:9+Math.floor(i/8),col:i%8});
  assert.deepEqual(gazeFrame(null),{neutral:true,x:0,y:0,row:null,col:null});
});
test('pointer gaze uses clockwise sectors and the real one-pixel dead zone',()=>{
  assert.equal(pointerGaze(0,0),null);assert.equal(pointerGaze(1,0),null);
  for(let i=0;i<16;i++){
    const angle=i*Math.PI/8;
    assert.equal(pointerGaze(Math.sin(angle)*100,-Math.cos(angle)*100),i);
  }
  assert.equal(pointerGaze(100,0),4);assert.equal(pointerGaze(0,100),8);
  assert.equal(pointerGaze(-100,0),12);assert.equal(pointerGaze(0,-100),0);
});
test('illegal directions and pointer values fail closed',()=>{
  for(const i of [-1,16,.5,NaN,Infinity,'4',undefined])assert.throws(()=>gazeFrame(i));
  for(const d of [NaN,Infinity,-Infinity])assert.throws(()=>pointerGaze(d,0));
});
