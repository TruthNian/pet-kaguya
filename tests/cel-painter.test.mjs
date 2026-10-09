import test from 'node:test';
import assert from 'node:assert/strict';
import {paintCel} from '../viewer/cel-painter.mjs';

function surface(){
  return {alpha:0,imageSmoothingEnabled:true,calls:[],
    clearRect(...args){this.calls.push(['clear',...args]);this.alpha=0;},
    drawImage(image,...args){this.calls.push(['draw',image,...args]);this.alpha=image.alpha+(1-image.alpha)*this.alpha;}};
}

test('native cel geometry clears first and disables browser interpolation',()=>{
  const context=surface(),image={alpha:.25};
  for(let index=0;index<8;index++){
    context.calls=[];context.imageSmoothingEnabled=true;
    paintCel(context,image,index);
    assert.deepEqual(context.calls,[['clear',0,0,192,208],['draw',image,index*192,0,192,208,0,0,192,208]]);
    assert.equal(context.imageSmoothingEnabled,false);
  }
});

test('repeated translucent reference draws and transparent replacement never retain old coverage',()=>{
  const context=surface(),reference={alpha:.25};
  for(let i=0;i<20;i++){
    paintCel(context,reference);
    assert.equal(context.alpha,.25);
  }
  paintCel(context,{alpha:1},7);assert.equal(context.alpha,1);
  paintCel(context,{alpha:0},0);assert.equal(context.alpha,0);
});

test('invalid native indices fail before altering the existing canvas',()=>{
  const context=surface();context.alpha=.75;
  for(const index of [-1,8,.5,NaN,Infinity,'0',null]){
    assert.throws(()=>paintCel(context,{alpha:.25},index),RangeError);
    assert.equal(context.alpha,.75);assert.deepEqual(context.calls,[]);
  }
});
