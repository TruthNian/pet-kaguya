import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {reviewCell,reviewStates} from '../viewer/review.mjs';
import {validateReviewMetadata,validateReviewHandReference} from '../viewer/review-contract.mjs';
import {validateWaitingMetadata} from '../viewer/waiting-contract.mjs';

test('visual review keeps technical prose folded without hiding adoption boundaries',()=>{
  const html=readFileSync(new URL('../viewer/index.html',import.meta.url),'utf8');
  for(const id of ['comparison-evidence','candidate-evidence']){
    const block=html.match(new RegExp(`<details\\b[^>]*id="${id}"[^>]*>[\\s\\S]*?</details>`));
    assert.ok(block,`missing ${id}`);
    assert.doesNotMatch(block[0].split('>')[0],/\bopen(?:\s|=|$)/);
    assert.doesNotMatch(block[0],/<(?:canvas|select|output)\b/);
  }
  const guide=html.match(/<p class="comparison-guide">([\s\S]*?)<\/p>/)?.[1];
  assert.match(guide,/降低抬手和原图眼动仅获接受为开发基础/);
  assert.match(guide,/review相叠手现为开发者选择/);
  assert.match(guide,/袖角跟随及精度试验未采用/);
  assert.match(guide,/完整动作未通过，安装文件未改/);
  assert.ok(html.indexOf('id="idle-stage"')<html.indexOf('id="candidate-evidence"'));
});

test('visual review retains one copy of each control and its actual native canvas size',()=>{
  const html=readFileSync(new URL('../viewer/index.html',import.meta.url),'utf8');
  const ids=[...html.matchAll(/\bid="([^"]+)"/g)].map(match=>match[1]);
  assert.equal(new Set(ids).size,ids.length);
  for(const id of ['idle-action','idle-comparison','idle-size','idle-background','idle-reduced',
    'idle-pause','idle-restart','idle-frame','idle-status','reference-status'])assert.ok(ids.includes(id));
  for(const id of ['idle-reference','idle-animated']){
    assert.match(html,new RegExp(`<canvas id="${id}" width="192" height="208"`));
  }
  assert.doesNotMatch(html,/<option value="review_overlap">/);
  assert.match(html,/<option id="hands-reference-choice" value="hands" disabled>[^<]*左改动前，右现用/);
  assert.match(html,/<option id="wave-reference-choice" value="wave" disabled>[^<]*停用/);
});

test('static review does not silently compare waiting with an unrelated source row',()=>{
  assert.deepEqual(reviewCell('waiting','source'),{row:7,col:1});
  assert.deepEqual(reviewCell('waving','source'),{row:3,col:1});
  assert.deepEqual(reviewCell('review','source'),{row:8,col:2});
  assert.deepEqual(reviewCell('failed','source'),{row:5,col:0});
});
test('historical versions retain their own static state coordinates',()=>{
  for(const baseline of ['phase2','phase3'])for(const [row,state] of reviewStates.entries()){
    assert.deepEqual(reviewCell(state,baseline),{row,col:0});
  }
});
test('static review selections reject invalid values',()=>{
  assert.throws(()=>reviewCell('unknown','phase3'),RangeError);
  assert.throws(()=>reviewCell('idle','unknown'),RangeError);
});

test('the actual viewer accepts the current cloth composition and retains the hair repair',()=>{
  const metadata=JSON.parse(readFileSync(new URL('../candidates/phase5/review/build.json',import.meta.url),'utf8'));
  assert.equal(validateReviewMetadata(metadata),metadata);
  assert.equal(metadata.rightArmCompositionVersion,'review-art-v6');
  assert.equal(metadata.clothCompositionVersion,'review-sleeves-v2');
  assert.equal(metadata.observedHairAlphaHolesRestored,true);
});

test('old or incomplete composition and art/motion overclaims still fail the viewer contract',()=>{
  const metadata=JSON.parse(readFileSync(new URL('../candidates/phase5/review/build.json',import.meta.url),'utf8'));
  for(const [field,value] of [['rightArmCompositionVersion','review-art-v5'],
    ['clothCompositionVersion','review-sleeves-v1'],['clothGeneratedSha256','changed'],
    ['heldHandsUnchangedFromV5',true],['originalLowerHandContourRestored',true],['clothAlphaPreservedExactly',false],
    ['observedHairAlphaHolesRestored',false],['knownSourceHairRGBAExact',false],
    ['handScaled',true],['visualMotionApproval','approved'],['strategyUserApproval','approved'],
    ['nativeRow',6],['repeatBeforeIdle',1],['newArtworkGenerated',false],
    ['handUserApprovalClaimed',true],['specificPoseUserApproval','approved'],['handPoseRGBAHash','bad'],
    ['newArtworkGeneratedThisIteration',true],['entryExitTransitionsBuilt',true]]){
    assert.throws(()=>validateReviewMetadata({...metadata,[field]:value}),/boundary mismatch/);
  }
  assert.throws(()=>validateReviewMetadata(null));
});

test('current hand comparison preserves the actual approved eye epoch and held timing',()=>{
  const load=path=>JSON.parse(readFileSync(new URL(path,import.meta.url),'utf8'));
  const before=load('../sources/reference/review-hands-before/build.json');
  const current=load('../candidates/phase5/review/build.json');
  assert.equal(validateReviewHandReference(before,current),before);
  assert.equal(current.handUserApprovalClaimed,false);
  for(const [key,value] of [['sourceEyeGeometryRevision','old'],['focusOffsetSourcePx',[0,5]],
      ['durationsMs',[]],['handUserApprovalClaimed',true]])
    assert.throws(()=>validateReviewHandReference(before,{...current,[key]:value}));
});

test('the viewer accepts current waiting garment while retaining held-contact limits',()=>{
  const metadata=JSON.parse(readFileSync(new URL('../candidates/phase5/waiting/build.json',import.meta.url),'utf8'));
  assert.equal(validateWaitingMetadata(metadata),metadata);
  assert.equal(metadata.heldTimingAcceptedTemporarily,true);
  assert.equal(metadata.clothAlphaPreservedExactly,false);
});

test('waiting rejects stale art and misleading alpha/approval/rig claims',()=>{
  const metadata=JSON.parse(readFileSync(new URL('../candidates/phase5/waiting/build.json',import.meta.url),'utf8'));
  for(const [field,value] of [['artworkCompositionVersion','waiting-art-v1'],
    ['clothCompositionVersion','wrong'],['clothGeneratedSha256','changed'],['heldHandRGBAExactFromV1',false],
    ['wholeRaisedGarmentAndBoundedBacking',false],['clothAlphaPreservedExactly',true],
    ['clothOnlyPixelChangeClaimed',true],['cleanSemanticMatteClaimed',true],['newArtworkGenerated',false],
    ['heldTimingAcceptedTemporarily',false],['handStrategy','raise-hold-lower'],
    ['strategyUserApproval','approved'],['visualMotionApproval','approved'],['nativeRow',8]]){
    assert.throws(()=>validateWaitingMetadata({...metadata,[field]:value}),/boundary mismatch/);
  }
  assert.throws(()=>validateWaitingMetadata(null));
});
