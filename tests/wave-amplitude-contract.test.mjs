import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {validateWaveAmplitude} from '../viewer/wave-amplitude-contract.mjs';
import {comparisonReference,comparisonPolicy} from '../viewer/comparison-reference.mjs';
import {candidateSlot,candidatePoseOffset} from '../viewer/candidate-clock.mjs';

const load=path=>JSON.parse(readFileSync(new URL(path,import.meta.url),'utf8'));
const study=load('../candidates/phase5/wave-amplitude-v1/build.json');
const current=load('../candidates/phase5/waving/build.json');
const manifest=load('../sources/reference/waving-amplitude-high/manifest.json');
const baseline=load('../sources/reference/waving-amplitude-high/contract.json');
const validate=(trial=study,active=current,frozen=manifest,old=baseline)=>validateWaveAmplitude(trial,active,frozen,old);

test('actual lowered wave is tied to current four cels, not an approved atlas',()=>{
  assert.equal(validate(),study);
  assert.deepEqual(study.unchangedHoldIndices,[0,2,3]);
  assert.equal(study.clothRepair.generatedHandNotUsed,true);
  assert.equal(study.clothRepair.handProtectionEstimated,true);
});
test('source/clock/current hashes, protection and approval cannot be forged',()=>{
  for(const [key,value] of [['sourceSha256','bad'],['camera',{}],['sequence',[]],
    ['baselineFrameHashes',study.frameHashes],['handScaleChanged',true],['newHandArtworkUsed',true],
    ['nativeInterpolation',true],['directionUserDecision','bad'],['visualMotionApproval','approved'],['adopted',false],['installed',true],
    ['userDecision','bad'],['adoptionScope','full-motion'],['currentWavingCelsRGBAExact',false],
    ['unchangedHoldIndices',[3]],['frameHashes',baseline.frameHashes]])
    assert.throws(()=>validate({...study,[key]:value}));
  assert.throws(()=>validate({...study,clothRepair:{...study.clothRepair,handChangedSourcePixels:1}}));
  assert.throws(()=>validate(study,{...current,amplitudeApprovalScope:'full-motion'}));
  assert.throws(()=>validate(study,current,{...manifest,fileSha256:'bad'}));
  assert.throws(()=>validate(study,current,manifest,{...baseline,frameHashes:study.frameHashes}));
  for(const scale of ( [0,NaN,Infinity,'0.158'] ))
    assert.throws(()=>validate({...study,camera:{...study.camera,scale}},{...current,camera:{...current.camera,scale}}));
});
test('every wave hold and all three cycles use one reference slot, then the same idle',()=>{
  for(let cycle=0;cycle<3;cycle++)for(let i=0;i<4;i++){
    const start=cycle*700+candidatePoseOffset('waving',i);
    for(const ms of [start,start+current.durationsMs[i]-.001]){
      const selected=candidateSlot('waving',ms);
      assert.deepEqual(comparisonReference('wave',selected.state,selected.index),
        {kind:'wave',state:'waving',index:i,synchronized:true});
    }
  }
  for(const ms of [2100,2500,999999]){
    const selected=candidateSlot('waving',ms);
    assert.equal(selected.state,'idle');
    assert.deepEqual(comparisonReference('wave',selected.state,selected.index),
      {kind:'candidate',state:'idle',index:selected.index,synchronized:true});
  }
});
test('wave comparison is not silently available for other state or sampling trials',()=>{
  assert.deepEqual(comparisonPolicy('waving','idle',true),{allowed:['idle','wave','sampling'],choice:'wave'});
  assert.equal(comparisonPolicy('jumping','wave').choice,'height');
  assert.equal(comparisonPolicy('waving_source','wave').choice,'idle');
  for(const state of ['failed','review','run_right','waving_source'])
    assert.throws(()=>comparisonReference('wave',state,0));
});
