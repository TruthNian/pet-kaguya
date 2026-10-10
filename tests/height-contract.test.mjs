import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {validateHopHeightStudy} from '../viewer/height-contract.mjs';
import {candidateSlot,candidatePoseOffset} from '../viewer/candidate-clock.mjs';
import {comparisonReference} from '../viewer/comparison-reference.mjs';
import {durations} from '../viewer/clock.mjs';
const read=path=>JSON.parse(readFileSync(new URL(path,import.meta.url),'utf8'));
const current=read('../candidates/phase5/jumping/build.json');
const study=read('../candidates/phase5/jumping-height-v1/build.json');

test('actual 4px study has the same current source/contact/holds, only three flight translations change',()=>{
  assert.equal(validateHopHeightStudy(study,current),study);
  for(let i=0;i<5;i++){
    assert.equal(study.actorOffsetsPx[i],current.actorOffsetsPx[i]/2);
    if(i===0||i===4)assert.equal(study.frameHashes[i],current.frameHashes[i]);
    else assert.notEqual(study.frameHashes[i],current.frameHashes[i]);
  }
});
test('adoption, changed art/poses/timing/current reference and broad quality claims are rejected',()=>{
  for(const [key,value] of [['adopted',true],['activeAtlasChanged',true],['installed',true],
    ['installableFullAtlas',true],['candidateApexOutputPx',6],['baselineApexOutputPx',4],
    ['newArtworkGenerated',true],['facialGeometryRepair',true],['continuousLandingProven',true],
    ['physicalBalanceProven',true],['visualMotionApproval','approved'],['durationsMs',[140,140]],
    ['sourceSha256','bad'],['baselineActualCelsRGBAExact',false],['groundedCelsRGBAExact',false]])
    assert.throws(()=>validateHopHeightStudy({...study,[key]:value},current));
  const changed=structuredClone(study);changed.keyframes[1].earAngle=0;
  assert.throws(()=>validateHopHeightStudy(changed,current));
  const changedGround=structuredClone(study);changedGround.frameHashes[0]=study.frameHashes[1];
  assert.throws(()=>validateHopHeightStudy(changedGround,current));
  assert.throws(()=>validateHopHeightStudy(study,{...current,actorOffsetsPx:[0,-3,-5,-3,0]}));
});
test('one ideal row slot synchronizes current/trial through every real hold and exact three-cycle fallback',()=>{
  for(let round=0;round<3;round++)for(let i=0;i<5;i++){
    const start=round*840+candidatePoseOffset('jumping_height',i);
    for(const time of [start,start+durations[4][i]-.001]){
      const selected=candidateSlot('jumping_height',time),reference=comparisonReference('height',selected.state,selected.index);
      assert.equal(reference.state,'jumping');assert.equal(reference.index,i);assert.equal(reference.synchronized,true);
      assert.equal(selected.index,candidateSlot('jumping',time).index);
    }
  }
  for(const time of [2520,2520+1680,2520+6600,2520+660000]){
    const slot=candidateSlot('jumping_height',time),ref=comparisonReference('height',slot.state,slot.index);
    assert.equal(slot.state,'idle');assert.equal(ref.state,'idle');assert.equal(ref.index,slot.index);
    assert.equal(ref.synchronized,true);
  }
});
test('height reference shares manual slots but cannot compare another action or invent extra frames',()=>{
  for(let i=0;i<5;i++)assert.equal(comparisonReference('height','jumping_height',i).index,i);
  for(const state of ['failed','review','waiting','jumping','run_right','waving'])
    assert.throws(()=>comparisonReference('height',state,0));
  assert.throws(()=>candidatePoseOffset('jumping_height',5));
  assert.throws(()=>comparisonReference('height','jumping_height',5));
});
