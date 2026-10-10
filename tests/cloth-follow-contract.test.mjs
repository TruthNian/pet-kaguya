import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {validateClothStudy} from '../viewer/cloth-follow-contract.mjs';
import {comparisonPolicy,comparisonReference} from '../viewer/comparison-reference.mjs';
import {candidateSlot,candidatePoseOffset} from '../viewer/candidate-clock.mjs';

const metadata=JSON.parse(readFileSync(new URL('../candidates/phase5/cloth-follow-v1/build.json',import.meta.url),'utf8'));
const current=name=>JSON.parse(readFileSync(new URL(`../sources/reference/gaze-action-v1/${name}.json`,import.meta.url),'utf8'));

test('archived sleeve trials match their frozen gait, not current corrected eyes',()=>{
  for(const state of ['run_right','run_left']){
    const entry=validateClothStudy(metadata,state,current(state));
    assert.equal(entry,metadata.states[state]);
    assert.deepEqual(entry.parentFrameHashes,current(state).frameHashes);
    assert.equal(entry.allNativeAlphaExact,false);
  }
  assert.equal(comparisonPolicy('run_right','idle',true).choice,'rigid');
  assert.equal(comparisonPolicy('run_left','cloth').choice,'rigid');
  assert.equal(comparisonPolicy('run_left','cloth').allowed.includes('cloth'),false);
  for(const state of ['failed','jumping','review_overlap','waving_source','idle']){
    assert.equal(comparisonPolicy(state,'cloth').allowed.includes('cloth'),false);
    assert.notEqual(comparisonPolicy(state,'cloth').choice,'cloth');
  }
});

test('one slot drives both sides at every real hold and three-cycle idle fallback',()=>{
  for(const state of ['run_left','run_right']){
    for(let cycle=0;cycle<3;cycle++)for(let index=0;index<8;index++){
      const time=cycle*1060+candidatePoseOffset(state,index);
      for(const elapsed of [time,time+metadata.durationsMs[index]-.001]){
        const selected=candidateSlot(state,elapsed);
        assert.deepEqual(comparisonReference('cloth',selected.state,selected.index),
          {kind:'current',state,index,synchronized:true});
      }
    }
    for(const time of [3180,5000,100000]){
      const selected=candidateSlot(state,time);
      assert.deepEqual(comparisonReference('cloth',selected.state,selected.index),
        {kind:'candidate',state:'idle',index:selected.index,synchronized:true});
    }
  }
  for(const state of ['failed','waiting','review'])assert.throws(()=>comparisonReference('cloth',state,0));
});

test('source camera poses and parent pixel epoch cannot drift unnoticed',()=>{
  for(const field of ['sourceSha256','camera','durationsMs','frameHashes','rootOffsetsSourcePx',
    'footOffsetsSourcePx','focusOffsetSourcePx','tipOffsetsSourcePx','nativeRow']){
    const parent=structuredClone(current('run_right'));parent[field]=null;
    assert.throws(()=>validateClothStudy(metadata,'run_right',parent));
  }
  const bad=structuredClone(metadata);bad.states.run_left.parentFrameHashes[0]='A'.repeat(64);
  assert.throws(()=>validateClothStudy(bad,'run_left',current('run_left')));
  assert.throws(()=>validateClothStudy(metadata,'failed',current('failed')));
});

test('ownership alpha and installation/approval overclaims fail closed',()=>{
  for(const [field,value] of [['adopted',true],['activeAtlasChanged',true],['installed',true],
    ['newArtworkGenerated',true],['physicalClothSimulation',true],['cleanClothLayersRecovered',true],
    ['nativeInterpolation',true],['liveDragLagInitialization',true],['specificMotionUserApproval','approved'],
    ['visualMotionApproval','approved'],['maximumOffsetOutputPx',NaN]]){
    const bad=structuredClone(metadata);bad[field]=value;
    assert.throws(()=>validateClothStudy(bad,'run_right',current('run_right')));
  }
  for(const scale of [0,-1,'invalid',Infinity]){
    const bad=structuredClone(metadata),parent=structuredClone(current('run_right'));
    bad.camera.scale=scale;parent.camera.scale=scale;
    assert.throws(()=>validateClothStudy(bad,'run_right',parent));
  }
  for(const edit of [m=>m.spec.protectedRects=[],m=>m.response.offsetsSourcePx[0]=10,
    m=>m.response.endStateSourcePx+=1,m=>m.states.run_right.allNativeAlphaExact=true,
    m=>m.states.run_right.differences[0].maximumAlphaDifference=-1,
    m=>m.states.run_right.differences[0].bounds[1]=20]){
    const bad=structuredClone(metadata);edit(bad);
    assert.throws(()=>validateClothStudy(bad,'run_right',current('run_right')));
  }
});
