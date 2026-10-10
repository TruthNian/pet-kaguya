import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {validateGazeFamily} from '../viewer/gaze-contract.mjs';
const read=name=>JSON.parse(readFileSync(new URL(`../candidates/phase5/${name}/build.json`,import.meta.url),'utf8'));
const current=read('look'),surface=read('look-surface-v1');
const rigid=JSON.parse(readFileSync(new URL('../sources/reference/gaze-rigid-v2/build.json',import.meta.url),'utf8'));
test('accepted current pixels retain the proposal identity, with separate old-rigid evidence',()=>{
  assert.equal(validateGazeFamily(current,'current'),current);
  assert.equal(validateGazeFamily(surface,'surface'),surface);
  assert.equal(validateGazeFamily(rigid,'rigid'),rigid);
  assert.deepEqual(current.frameHashes,surface.frameHashes);
  assert.equal(current.neutralFrameHash,rigid.neutralFrameHash);
  assert.throws(()=>validateGazeFamily(surface,'current'));
  assert.throws(()=>validateGazeFamily(current,'surface'));
});
test('development-basis approval cannot become full acceptance',()=>{
  for(const [key,value] of [['adopted',false],['eyeMotionApprovalScope','full-release'],
      ['approvalDoesNotIncludeFullEyeQuality',false],['approvalDoesNotIncludeFullMotion',false],
      ['installed',true],['eyeBackingUsed',true],['irisShapeWarp',false]]){
    assert.throws(()=>validateGazeFamily({...current,[key]:value},'current'));
  }
});
test('unadopted surface flow cannot claim approval, host changes or unchanged iris shape',()=>{
  for(const [key,value] of [['adopted',true],['activeAtlasChanged',true],['installed',true],
      ['irisShapeWarp',false],['eyeOutlineFixed',false],['sourceRGBAExactAtZero',false],
      ['newArtworkGenerated',true],['minimumSampledJacobian',0],['sourceSha256','other']]){
    assert.throws(()=>validateGazeFamily({...surface,[key]:value},'surface'));
  }
});
