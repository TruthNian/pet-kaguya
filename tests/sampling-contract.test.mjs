import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {validateSamplingStudy} from '../viewer/sampling-contract.mjs';

const metadata=JSON.parse(readFileSync(new URL('../candidates/phase5/terminal-sampling-v1/build.json',import.meta.url),'utf8'));
const current=name=>JSON.parse(readFileSync(new URL(`../candidates/phase5/${name}/build.json`,import.meta.url),'utf8'));
const frozenReview=JSON.parse(readFileSync(new URL('../sources/reference/gaze-action-v1/review.json',import.meta.url),'utf8'));

test('only unchanged action metadata still match the frozen precision study',()=>{
  for(const name of ['idle','jumping','failed','waiting']){
    const entry=validateSamplingStudy(metadata,name,current(name));
    assert.equal(entry.candidateFrameHashes.length,current(name).frameHashes.length);
    assert.deepEqual(entry.legacyFrameHashes,current(name).frameHashes);
  }
  for(const name of ['run_right','run_left','processing','review','waving'])
    assert.throws(()=>validateSamplingStudy(metadata,name,current(name)));
});
test('different actual cels/camera/timing or wrong action are rejected',()=>{
  validateSamplingStudy(metadata,'review',frozenReview);
  for(const edit of [m=>m.frameHashes[0]='A'.repeat(64),m=>m.camera.x+=1,m=>m.durationsMs[0]+=1,
                    m=>m.nativeRow=0,m=>m.state='idle']){
    const m=structuredClone(frozenReview);edit(m);
    assert.throws(()=>validateSamplingStudy(metadata,'review',m));
  }
});
test('artwork, adoption, host/FPS or scope claims cannot be silently inherited',()=>{
  for(const [field,value] of [['sourceSha256','wrong'],['method','nearest'],['adopted',true],
    ['visualApproval','approved'],['hostFpsChanged',true],['activeAtlasChanged',true],['installed',true],
    ['geometryAndSourcePixelsUnchanged',false],['allLegacyCelsReconstructedExactly',false]]){
    const m=structuredClone(metadata);m[field]=value;
    assert.throws(()=>validateSamplingStudy(m,'review',frozenReview));
  }
  const m=structuredClone(metadata);m.states.idle.nativeRows=[8];
  assert.throws(()=>validateSamplingStudy(m,'idle',current('idle')));
  assert.throws(()=>validateSamplingStudy(metadata,'waving_source',current('waving')));
});
