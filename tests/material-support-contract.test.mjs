import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {validateMaterialSupport} from '../viewer/material-support-contract.mjs';
const states=['jumping','run_right','run_left'];
const read=state=>JSON.parse(readFileSync(new URL(`../candidates/phase5/${state}/build.json`,import.meta.url),'utf8'));
test('all 21 current cels expose bounded support repair, not new geometry or approval',()=>{
  for(const state of states){const current=read(state);assert.equal(validateMaterialSupport(current),current.materialSupportRepair);}
});
test('missing support version or falsified geometry/alpha/timing/approval and pixel bounds are rejected',()=>{
  for(const state of states){
    const current=read(state);
    for(const [key,value] of [['scope','new-art'],['sourceArtworkChanged',true],['geometryChanged',true],
      ['timingChanged',true],['nativeAlphaPreservedExactly',false],['fullMotionApproved',true],['baselineCommit','bad']]){
      const changed=structuredClone(current);changed.materialSupportRepair[key]=value;
      assert.throws(()=>validateMaterialSupport(changed));
    }
    assert.throws(()=>validateMaterialSupport({...current,localFilterSupport:'clipped-local-v1'}));
    for(const field of ['changedPixels','maximumChannelDifference','bounds']){
      const changed=structuredClone(current);changed.materialSupportRepair.changes[1][field]=null;
      assert.throws(()=>validateMaterialSupport(changed));
    }
    const changed=structuredClone(current);changed.materialSupportRepair.currentFrameHashes[0]='bad';
    assert.throws(()=>validateMaterialSupport(changed));
    if(current.sourceEyeGeometryRevision){
      const bad=structuredClone(current);bad.materialSupportRepair.independentEyeSourceRevision.onlyNativeEyeWindowsChanged=false;
      assert.throws(()=>validateMaterialSupport(bad));
      const missing=structuredClone(current);delete missing.materialSupportRepair.independentEyeSourceRevision;
      assert.throws(()=>validateMaterialSupport(missing));
    }
  }
});
