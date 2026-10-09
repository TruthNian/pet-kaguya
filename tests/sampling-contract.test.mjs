import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {validateSamplingStudy} from '../viewer/sampling-contract.mjs';

const metadata=JSON.parse(readFileSync(new URL('../candidates/phase5/terminal-sampling-v1/build.json',import.meta.url),'utf8'));
const current=name=>JSON.parse(readFileSync(new URL(`../candidates/phase5/${name}/build.json`,import.meta.url),'utf8'));

test('all actual nine action metadata match one synchronized, unadopted precision study',()=>{
  for(const name of ['idle','run_right','run_left','waving','jumping','failed','waiting','processing','review']){
    const entry=validateSamplingStudy(metadata,name,current(name));
    assert.equal(entry.candidateFrameHashes.length,current(name).frameHashes.length);
    assert.deepEqual(entry.legacyFrameHashes,current(name).frameHashes);
  }
});
test('different actual cels/camera/timing or wrong action are rejected',()=>{
  for(const edit of [m=>m.frameHashes[0]='A'.repeat(64),m=>m.camera.x+=1,m=>m.durationsMs[0]+=1,
                    m=>m.nativeRow=0,m=>m.state='idle']){
    const m=structuredClone(current('review'));edit(m);
    assert.throws(()=>validateSamplingStudy(metadata,'review',m));
  }
});
test('artwork, adoption, host/FPS or scope claims cannot be silently inherited',()=>{
  for(const [field,value] of [['sourceSha256','wrong'],['method','nearest'],['adopted',true],
    ['visualApproval','approved'],['hostFpsChanged',true],['activeAtlasChanged',true],['installed',true],
    ['geometryAndSourcePixelsUnchanged',false],['allLegacyCelsReconstructedExactly',false]]){
    const m=structuredClone(metadata);m[field]=value;
    assert.throws(()=>validateSamplingStudy(m,'review',current('review')));
  }
  const m=structuredClone(metadata);m.states.idle.nativeRows=[8];
  assert.throws(()=>validateSamplingStudy(m,'idle',current('idle')));
  assert.throws(()=>validateSamplingStudy(metadata,'waving_source',current('waving')));
});
