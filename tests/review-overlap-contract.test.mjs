import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {validateReviewOverlapMetadata,validateReviewOverlapReference} from '../viewer/review-overlap-contract.mjs';
import {comparisonReference,comparisonPolicy} from '../viewer/comparison-reference.mjs';
import {candidateSlot,candidatePoseOffset,candidateRows} from '../viewer/candidate-clock.mjs';
import {durations} from '../viewer/clock.mjs';
const json=path=>JSON.parse(readFileSync(new URL(`../${path}`,import.meta.url),'utf8'));
const study=json('candidates/phase5/review-hands-overlap-v1/animation/build.json');
const manifest=json('sources/reference/review-held-v6/manifest.json');
const baseline=json('sources/reference/review-held-v6/contract.json');
const current=json('sources/reference/gaze-action-v1/review.json');

test('archived hand study matches its frozen review source, focus and timing',()=>{
  assert.equal(validateReviewOverlapMetadata(study),study);
  assert.equal(validateReviewOverlapReference(manifest,baseline,study,current),baseline);
  assert.equal(candidateRows.review_overlap,8);
});
test('every trial hold and three-cycle fallback drive both sides from one slot',()=>{
  for(let round=0;round<3;round++)for(let i=0;i<6;i++){
    const start=round*1030+candidatePoseOffset('review_overlap',i);
    for(const time of [start,start+durations[8][i]-.001]){
      const slot=candidateSlot('review_overlap',time);
      assert.equal(slot.state,'review_overlap');assert.equal(slot.index,i);
      assert.equal(slot.holdMs,durations[8][i]);assert.ok(slot.untilNext>0);
      assert.deepEqual(comparisonReference('hands',slot.state,slot.index),
        {kind:'hands',state:'review',index:i,synchronized:true});
    }
  }
  for(const time of [3090,4770,9690,999999]){
    const slot=candidateSlot('review_overlap',time);
    assert.equal(slot.state,'idle');assert.equal(slot.completedAction,true);
    assert.deepEqual(comparisonReference('hands',slot.state,slot.index),
      {kind:'candidate',state:'idle',index:slot.index,synchronized:true});
  }
  assert.throws(()=>candidatePoseOffset('review_overlap',6));
  assert.throws(()=>comparisonReference('hands','review',0));
});
test('pose, image epoch and narrow pending approval cannot drift unnoticed',()=>{
  for(const [key,value] of [['adopted',true],['installed',true],['specificPoseUserApproval','approved'],
    ['visualMotionApproval','approved'],['activeAtlasChanged',true],['facialGeometryRepair',true],
    ['entryExitTransitionsBuilt',true],['sourceEyeFaceRGBAExactToBaseline',false],['focusOffsetSourcePx',[0,6]],
    ['durationsMs',[150,150,150,150,150,281]],['keyframes',[]],['frameHashes',[]],
    ['handCuffMaximumSourceDisplacementPx',[0,0,.01,0,0,0]]]){
    const bad=structuredClone(study);bad[key]=value;
    assert.throws(()=>validateReviewOverlapReference(manifest,baseline,bad,current),key);
  }
  for(const key of ['changedPixels','alphaChangedPixels','bounds']){
    const bad=structuredClone(study);bad.changesFromFrozenReview[3][key]=null;
    assert.throws(()=>validateReviewOverlapMetadata(bad));
  }
  const bad=structuredClone(study);bad.frameHashes[0]='bad';
  assert.throws(()=>validateReviewOverlapMetadata(bad));
});
test('reference provenance and current row cannot be silently replaced',()=>{
  for(const key of ['commit','fileSha256','referencePurpose','visualApprovalInherited']){
    const bad=structuredClone(manifest);bad[key]=null;
    assert.throws(()=>validateReviewOverlapReference(bad,baseline,study,current));
  }
  for(const key of ['sourceSha256','camera','durationsMs','focusOffsetSourcePx','frameHashes']){
    const bad=structuredClone(current);bad[key]=null;
    assert.throws(()=>validateReviewOverlapReference(manifest,baseline,study,bad));
  }
});
test('trial comparison disables unrelated float epoch; normal actions keep their defaults',()=>{
  assert.deepEqual(comparisonPolicy('review_overlap','sampling'),{allowed:['idle'],choice:'idle'});
  assert.equal(comparisonPolicy('review_overlap','idle').choice,'idle');
  assert.equal(comparisonPolicy('review_overlap','idle',true).choice,'idle');
  for(const [mode,choice] of [['jumping','height'],['failed','mouth'],['run_left','idle'],['review','idle']])
    assert.equal(comparisonPolicy(mode,'hands',true).choice,choice);
  assert.equal(comparisonPolicy('review','sampling').allowed.includes('sampling'),false);
  assert.equal(comparisonPolicy('review','sampling').choice,'idle');
  assert.equal(comparisonPolicy('waving_source','sampling').choice,'idle');
  assert.equal(comparisonPolicy('idle','hands').choice,'idle');
  assert.throws(()=>comparisonPolicy('unbuilt','idle'));
});
