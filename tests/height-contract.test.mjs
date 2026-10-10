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
const baseline=read('../sources/reference/jumping-height-8px/contract.json');
const manifest=read('../sources/reference/jumping-height-8px/manifest.json');
const validate=(s=study,c=current,b=baseline,m=manifest)=>validateHopHeightStudy(s,b,c,m);

test('actual 4px study has the same current source/contact/holds, only three flight translations change',()=>{
  assert.equal(validate(),study);
  for(let i=0;i<5;i++){
    assert.equal(study.actorOffsetsPx[i],baseline.actorOffsetsPx[i]/2);
    assert.equal(study.frameHashes[i],current.frameHashes[i]);
    if(i===0||i===4)assert.equal(study.frameHashes[i],baseline.frameHashes[i]);
    else assert.notEqual(study.frameHashes[i],baseline.frameHashes[i]);
  }
});
test('missing narrow approval, changed art/poses/timing/reference and broad quality claims are rejected',()=>{
  for(const [key,value] of [['adopted',false],['activeAtlasChanged',false],['installed',true],
    ['adoptionScope','full-motion'],['heightVisualApproval','approved'],['currentJumpingCelsRGBAExact',false],
    ['installableFullAtlas',true],['candidateApexOutputPx',6],['baselineApexOutputPx',4],
    ['newArtworkGenerated',true],['facialGeometryRepair',true],['continuousLandingProven',true],
    ['physicalBalanceProven',true],['visualMotionApproval','approved'],['durationsMs',[140,140]],
    ['sourceSha256','bad'],['baselineActualCelsRGBAExact',false],['groundedCelsRGBAExact',false]])
    assert.throws(()=>validate({...study,[key]:value}));
  const changed=structuredClone(study);changed.keyframes[1].earAngle=0;
  assert.throws(()=>validate(changed));
  const changedGround=structuredClone(study);changedGround.frameHashes[0]=study.frameHashes[1];
  assert.throws(()=>validate(changedGround));
  assert.throws(()=>validate(study,{...current,actorOffsetsPx:[0,-3,-5,-3,0]}));
  assert.throws(()=>validate(study,current,baseline,{...manifest,fileSha256:'bad'}));
  assert.throws(()=>validate(study,current,{...baseline,actorOffsetsPx:current.actorOffsetsPx}));
});
test('one ideal row slot synchronizes current/trial through every real hold and exact three-cycle fallback',()=>{
  for(let round=0;round<3;round++)for(let i=0;i<5;i++){
    const start=round*840+candidatePoseOffset('jumping',i);
    for(const time of [start,start+durations[4][i]-.001]){
      const selected=candidateSlot('jumping',time),reference=comparisonReference('height',selected.state,selected.index);
      assert.equal(reference.kind,'height');
      assert.equal(reference.state,'jumping');assert.equal(reference.index,i);assert.equal(reference.synchronized,true);
      assert.equal(selected.index,candidateSlot('jumping',time).index);
    }
  }
  for(const time of [2520,2520+1680,2520+6600,2520+660000]){
    const slot=candidateSlot('jumping',time),ref=comparisonReference('height',slot.state,slot.index);
    assert.equal(slot.state,'idle');assert.equal(ref.state,'idle');assert.equal(ref.index,slot.index);
    assert.equal(ref.synchronized,true);
  }
});
test('height reference shares manual slots but cannot compare another action or invent extra frames',()=>{
  for(let i=0;i<5;i++)assert.equal(comparisonReference('height','jumping',i).index,i);
  for(const state of ['failed','review','waiting','jumping_height','run_right','waving'])
    assert.throws(()=>comparisonReference('height',state,0));
  assert.throws(()=>candidatePoseOffset('jumping',5));
  assert.throws(()=>comparisonReference('height','jumping',5));
});
