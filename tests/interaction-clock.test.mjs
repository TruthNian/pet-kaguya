import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {InteractionClock,selectedInteraction,taskStates,validateInteractionAtlas} from '../viewer/interaction-clock.mjs';
import {durations} from '../viewer/clock.mjs';
const read=path=>JSON.parse(readFileSync(new URL(path,import.meta.url),'utf8'));
const contract=read('../sources/canonical/host-interaction-contract.json');
const defaults={base:'idle',drag:null,hover:false,look:null,reduced:false};

test('model boundary is based on actual rechecked member hashes, not a version-only or native quality claim',()=>{
  assert.equal(contract.members[0].sha256,'0CFCC8B3294BC924FAEC0A22F751C462A6209F55981C97A5F213CDE14F2295E0');
  assert.equal(contract.members[1].sha256,'1A69752C18B48771390DCE47C4D0C1C036AF11C983A1A3B4D2059AF76A566642');
  assert.equal(contract.members[2].sha256,'BDDF0E4E79918F7157682015C598B97EB833553C036026004555F88FA0CB9D3B');
  assert.equal(contract.facts.lateCallbackSkipsIntermediateFrames,false);
  assert.equal(contract.facts.lookCellTakesPrecedenceOverReducedMotion,true);
  assert.equal(contract.installedApplicationModified,false);
  assert.equal(contract.independentPetHostCreated,false);
});
test('all base states respect drag > hover jump > task priority without erasing the base',()=>{
  for(const base of taskStates)for(const hover of [false,true])for(const drag of [null,'run_left','run_right']){
    const clock=new InteractionClock({base,hover,drag});
    assert.equal(clock.frame().base,base);
    assert.equal(clock.frame().selected,drag??(hover?'jumping':base));
    assert.equal(clock.frame().index,0);
  }
});
test('changing base under an unchanged drag preserves its current slot; release enters new underlying state immediately',()=>{
  for(const base of taskStates)for(const drag of ['run_left','run_right']){
    const clock=new InteractionClock({base,drag});
    for(let slot=0;slot<8;slot++){
      const before=clock.frame();
      const alternate=base==='review'?'waiting':'review';
      assert.equal(clock.update({base:alternate},before.deadline-1).reset,false);
      assert.equal(clock.frame().index,slot);
      assert.equal(clock.frame().deadline,before.deadline);
      assert.equal(clock.update({base},before.deadline-1).reset,false);
      clock.advance(before.deadline);
    }
    const release=clock.update({drag:null},clock.frame().deadline-1);
    assert.equal(release.reset,true);assert.equal(release.frame.state,base);assert.equal(release.frame.index,0);
  }
});
test('hover enters jumping on any base; leaving does not wait for a landing cel or force idle',()=>{
  for(const base of taskStates)for(let count=0;count<5;count++){
    const clock=new InteractionClock({base,hover:true});
    for(let i=0;i<count;i++)clock.advance(clock.frame().deadline);
    const result=clock.update({hover:false},clock.frame().deadline-1);
    // If the base already is jumping, pointer leave changes no effective
    // effect dependency. It must preserve the slot rather than restart it.
    assert.equal(result.reset,base!=='jumping');assert.equal(result.frame.state,base);
    assert.equal(result.frame.index,base==='jumping'?count:0);
  }
});
test('release under an active hover selects jumping, not base task; changing direction resets a drag row',()=>{
  const clock=new InteractionClock({base:'failed',drag:'run_right',hover:true});
  clock.advance(120);
  assert.equal(clock.update({drag:'run_left'},121).frame.index,0);
  const released=clock.update({drag:null},122).frame;
  assert.equal(released.state,'jumping');assert.equal(released.base,'failed');
  assert.equal(clock.update({hover:false},123).frame.state,'failed');
});
test('look overrides only eligible selected states, including in reduced motion',()=>{
  for(const base of taskStates)for(let direction=0;direction<16;direction++){
    const clock=new InteractionClock({base,reduced:true,look:{direction}});
    const eligible=['idle','processing','waving'].includes(base),frame=clock.frame();
    assert.equal(frame.state,eligible?'look':base);assert.equal(frame.static,true);
    if(eligible){assert.equal(frame.row,9+Math.floor(direction/8));assert.equal(frame.index,direction%8);}
    assert.equal(clock.update({hover:true},1).frame.state,'jumping');
    assert.equal(clock.update({drag:'run_left'},2).frame.state,'run_left');
  }
});
test('look identity updates and removing look reset the effect; the same object does not restart',()=>{
  const look={direction:4},clock=new InteractionClock({base:'waving',look});
  assert.equal(clock.update({look},10).reset,false);
  assert.equal(clock.update({look:{direction:4}},11).reset,true);
  const result=clock.update({look:null},12);
  assert.equal(result.frame.state,'waving');assert.equal(result.frame.index,0);assert.equal(result.frame.deadline,152);
});
test('every real hold, all three action cycles and six slow idle slots match native durations',()=>{
  for(const base of taskStates.filter(state=>state!=='idle')){
    const row={waving:3,jumping:4,failed:5,waiting:6,processing:7,review:8}[base];
    const clock=new InteractionClock({base});let time=0;
    for(let round=0;round<3;round++)for(let index=0;index<durations[row].length;index++){
      assert.equal(clock.frame().state,base);assert.equal(clock.frame().index,index);
      assert.equal(clock.frame().holdMs,durations[row][index]);
      assert.equal(clock.advance(time+durations[row][index]-.001),false);
      time+=durations[row][index];assert.equal(clock.advance(time),true);
    }
    for(let index=0;index<6;index++){
      assert.equal(clock.frame().state,'idle');assert.equal(clock.frame().index,index);
      assert.equal(clock.frame().completedAction,true);
      time+=durations[0][index];clock.advance(time);
    }
    assert.equal(clock.frame().index,0);
  }
});
test('late native-style callback advances only one frame and schedules the next complete hold',()=>{
  const clock=new InteractionClock({base:'failed'});
  assert.equal(clock.advance(5000),true);
  assert.equal(clock.frame().state,'failed');assert.equal(clock.frame().index,1);
  assert.equal(clock.frame().deadline,5140);
  assert.equal(clock.advance(5000),false);
  assert.equal(clock.advance(5140),true);assert.equal(clock.frame().index,2);
});
test('same effective properties preserve a slot, while reduced/restart changes reset deliberately',()=>{
  const clock=new InteractionClock({base:'review'});clock.advance(150);
  assert.equal(clock.update({},200).reset,false);assert.equal(clock.frame().index,1);
  assert.equal(clock.update({reduced:true},201).frame.index,0);assert.equal(clock.advance(99999),false);
  assert.equal(clock.update({reduced:false},100000).frame.deadline,100150);
  clock.advance(100150);
  assert.equal(clock.update({},100151,true).frame.index,0);
});
test('invalid states, look values, booleans and nonmonotonic time fail before mutation',()=>{
  for(const props of [{base:'running'},{base:'run_left'},{drag:'jumping'},{hover:1},{reduced:null},
    {look:{direction:16}},{look:{direction:-1}},{look:{direction:.5}},{look:4}])
    assert.throws(()=>selectedInteraction({...defaults,...props}));
  const clock=new InteractionClock({base:'failed'},20),before=clock.frame();
  for(const time of [NaN,Infinity,-1,19])assert.throws(()=>clock.advance(time));
  assert.throws(()=>clock.update({base:'bad'},20));assert.deepEqual(clock.frame(),before);
});
test('the complete actual development atlas is accepted, but geometry/installation/approval drift is rejected',()=>{
  const current=read('../candidates/phase5/global/build.json');
  assert.equal(validateInteractionAtlas(current),current);
  for(const [key,value] of [['installed',true],['installableFullAtlas',true],['hostIntegrationVerified',true],
    ['allStateTransitionsAccepted',true],['visualAcceptance','approved'],['sourceSha256','bad'],
    ['atlasSize',[1536,1872]],['directionCount',8],['atlasRGBAHash','bad'],['actionRows',[]]])
    assert.throws(()=>validateInteractionAtlas({...current,[key]:value}));
  const bad=structuredClone(current);bad.actionRows[5].frameCount=7;
  assert.throws(()=>validateInteractionAtlas(bad));
});
