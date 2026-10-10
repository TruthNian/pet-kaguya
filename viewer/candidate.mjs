// Current v3-only development candidates. Historical preview is separate.
import {durations} from './clock.mjs';
import {candidateRows as rows,candidateSlot,candidatePoseOffset,candidateCelKey} from './candidate-clock.mjs?v=20261010-mouth-adopt-1';
import {paintCel} from './cel-painter.mjs?v=20261010-terminal-precision-v1';
import {comparisonReference,validateRigidReference,validateHopReference,validateMouthReference} from './comparison-reference.mjs?v=20261010-mouth-adopt-1';
import {validateReviewMetadata} from './review-contract.mjs';
import {validateWaitingMetadata} from './waiting-contract.mjs';
import {validateSamplingStudy} from './sampling-contract.mjs';

const el=id=>document.getElementById(id);
const canvases=[el('idle-reference'),el('idle-animated')];
const contexts=canvases.map(canvas=>canvas.getContext('2d',{alpha:true}));
const media=matchMedia('(prefers-reduced-motion: reduce)');
el('idle-reduced').checked=media.matches;
const sources={idle:'idle',run_right:'run_right',run_left:'run_left',failed:'failed',jumping:'jumping',waving:'waving',waving_source:'wave-source-rig-v3',processing:'processing',waiting:'waiting',review:'review'};
const cache=new Map();
const rigidCache=new Map();
const contactCache=new Map();
let samplingPromise=null;
let mouthPromise=null;
let mode='idle',ready=false,timer=null,baseElapsed=0,startedAt=null,paused=false,manualIndex=null,lastKey='',paintCount=0,request=0;
let lastReferenceKey='',referencePaintCount=0;
const reduced=()=>el('idle-reduced').checked;
const elapsed=()=>baseElapsed+(startedAt===null?0:performance.now()-startedAt);
const canRun=()=>ready&&!paused&&!reduced()&&!document.hidden;

async function asset(state){
  if(!cache.has(state))cache.set(state,(async()=>{
    const root=`../candidates/phase5/${sources[state]}`;
    const response=await fetch(`${root}/build.json`,{cache:'no-cache'});
    if(!response.ok)throw new Error(`${state} metadata unavailable`);
    const metadata=await response.json();
    if(metadata.sourceSha256!=='65401EFDFEF0205D0CEA30AD08A0F14911C20B1B83468DBB6B3619E7DC89430A'
        ||metadata.facialGeometryRepair!==false||metadata.installableFullAtlas!==false||metadata.installed!==false)
      throw new Error(`${state} source or candidate boundary mismatch`);
    if(JSON.stringify(metadata.durationsMs)!==JSON.stringify(durations[rows[state]])){
      throw new Error(`${state} native schedule mismatch`);
    }
    if(!Array.isArray(metadata.frameHashes)||metadata.frameHashes.length!==durations[rows[state]].length)
      throw new Error(`${state} cel hash count mismatch`);
    metadata.frameHashes.forEach((_,index)=>candidateCelKey(metadata.frameHashes,index));
    if(state==='waving_source'&&(metadata.state!=='waving'||metadata.nativeRow!==3
        ||metadata.originalConnectedSleeveEdgeFollowed!==true||metadata.foregroundMatteStillEstimated!==true
        ||metadata.newArtworkGenerated!==false||metadata.inferredBoundaryIsNotSourceObservation!==true
        ||metadata.cleanLayerRecoveryClaimed!==false||metadata.articulatedArmBuilt!==false
        ||metadata.nativeInterpolation!==false||metadata.adopted!==false||metadata.activeAtlasChanged!==false
        ||metadata.strategyUserApproval!=='pending'||metadata.visualMotionApproval!=='pending'
        ||metadata.repeatBeforeIdle!==3))throw new Error('source-arm experimental preview boundary mismatch');
    if(state==='waiting')validateWaitingMetadata(metadata);
    if(state==='processing'&&(metadata.nativeState!=='running'||metadata.nativeRow!==7
        ||metadata.closedEyeFrames!==0||metadata.bodyPulse!==false||metadata.ornamentFlash!==false
        ||metadata.repeatBeforeIdle!==3||metadata.visualMotionApproval!=='pending'))
      throw new Error('processing state or restrained-motion boundary mismatch');
    if(state==='review')validateReviewMetadata(metadata);
    if(state==='jumping'&&(metadata.groundedContactVersion!=='two-link-source-material-v1'
        ||metadata.originalAirCelsRGBAExact!==true||metadata.strategyApprovalInheritedFromLocomotion!==false
        ||metadata.artistLayerRecoveryClaimed!==false||metadata.newArtworkGenerated!==false
        ||metadata.continuousLandingProven!==false||metadata.physicalBalanceProven!==false
        ||metadata.strategyUserApproval!=='pending'||metadata.visualMotionApproval!=='pending'))
      throw new Error('two-link hop contact candidate boundary mismatch');
    if(['run_right','run_left'].includes(state)&&(metadata.animationBuilt!==true||metadata.nativeRow!==rows[state]
        ||metadata.projection!=='front-held-alternating-small-steps'||metadata.strategyUserApproval!=='approved'
        ||metadata.strategyApprovalScope!=='front-held-small-steps-only'
        ||metadata.strategyUserDecision!=='sources/canonical/locomotion-decision-20261009.json'
        ||metadata.artMirrored!==false||metadata.hostVelocitySynchronization!==false||metadata.screenWorldNoSlipProven!==false
        ||metadata.actualDragReleaseCanInterruptAnyCel!==true||metadata.visualMotionApproval!=='pending'))
      throw new Error('drag-feedback candidate boundary mismatch');
    if(['run_right','run_left'].includes(state)&&(metadata.legCompositionVersion!=='leg-material-v2'
        ||metadata.integerSourceMaterialNeutralRGBAExact!==true||metadata.directSamplerNeutralRGBAExact!==true
        ||metadata.directSamplerNeutralPremultMatchesWithinTolerance!==true
        ||metadata.rootShiftFollowsSupportNotTravelDirection!==true||metadata.faceGeometryRigidRootTranslation!==true
        ||metadata.normalizedKnownBacking!==true||metadata.diagnosticPosesAreNotFrameInputs!==true
        ||metadata.measuredMassCentre!==false||metadata.physicalBalanceProven!==false
        ||metadata.landingApproachAdded!==true||metadata.landingReferenceIsNotHostInterpolation!==true
        ||metadata.continuousLandingProven!==false||metadata.risingPoseAdded!==true
        ||metadata.continuousTakeoffProven!==false||metadata.loopSeamContactAtNextCycle!==true
        ||metadata.loopSeamContinuousProven!==false||metadata.loopSeamRGBAExact!==false
        ||metadata.secondaryMotion!=='periodic-first-order-root-lag; visible-tip-fields-only'
        ||metadata.secondaryGeometryCombinedBeforeBackingSampling!==true
        ||metadata.cleanTipLayersRecovered!==false||metadata.liveDragLagInitialization!==false
        ||metadata.continuousSecondaryMotionProven!==false
        ||metadata.sourceAlphaAndOcclusionSeparated!==true||metadata.artistLayerRecoveryClaimed!==false))
      throw new Error('conditioned leg composition boundary mismatch');
    // Tie the decoded strip to the metadata's actual cels. A newly built
    // metadata file must not be paired with a previously cached bitmap.
    const image=new Image();image.src=`${root}/strip.webp?v=${metadata.frameHashes.join('')}`;await image.decode();
    if(image.naturalWidth!==1536||image.naturalHeight!==208)throw new Error(`${state} dimensions mismatch`);
    return {image,metadata};
  })().catch(error=>{cache.delete(state);throw error;}));
  return cache.get(state);
}
async function rigidAsset(state,current){
  if(!rigidCache.has(state))rigidCache.set(state,(async()=>{
    const root='../sources/reference/locomotion-rigid';
    const response=await fetch(`${root}/manifest.json`);
    if(!response.ok)throw new Error('rigid reference metadata unavailable');
    const metadata=await response.json();
    const entry=validateRigidReference(metadata,state,current);
    const image=new Image();image.src=`${root}/${entry.file}`;await image.decode();
    if(image.naturalWidth!==1536||image.naturalHeight!==208)throw new Error('rigid reference dimensions mismatch');
    return {image,metadata,frameHashes:entry.frameHashes};
  })().catch(error=>{rigidCache.delete(state);throw error;}));
  const reference=await rigidCache.get(state);
  validateRigidReference(reference.metadata,state,current);
  return reference;
}
async function samplingAsset(state,current){
  if(samplingPromise===null)samplingPromise=(async()=>{
    const root='../candidates/phase5/terminal-sampling-v1';
    const response=await fetch(`${root}/build.json`,{cache:'no-cache'});
    if(!response.ok)throw new Error('terminal precision study unavailable');
    const metadata=await response.json();
    validateSamplingStudy(metadata,state,current);
    const image=new Image();image.src=`${root}/spritesheet.webp?v=${metadata.candidateAtlasRGBAHash}`;
    await image.decode();
    if(image.naturalWidth!==1536||image.naturalHeight!==2288)throw new Error('precision atlas dimensions mismatch');
    return {image,metadata};
  })().catch(error=>{samplingPromise=null;throw error;});
  const result=await samplingPromise;
  const entry=validateSamplingStudy(result.metadata,state,current);
  return {...result,entry};
}
function stopClock(){
  if(startedAt!==null){baseElapsed+=performance.now()-startedAt;startedAt=null;}
  if(timer!==null){clearTimeout(timer);timer=null;}
}
async function contactAsset(current){
  if(!contactCache.has('jumping'))contactCache.set('jumping',(async()=>{
    const root='../candidates/phase5/jumping';
    const response=await fetch(`${root}/contact-proof.json`,{cache:'no-cache'});
    if(!response.ok)throw new Error('hop comparison metadata unavailable');
    const metadata=validateHopReference(await response.json(),current);
    const image=new Image();image.src=`${root}/${metadata.file}?v=${metadata.frameHashes.join('')}`;await image.decode();
    if(image.naturalWidth!==1536||image.naturalHeight!==208)throw new Error('hop comparison dimensions mismatch');
    return {image,metadata,frameHashes:metadata.frameHashes};
  })().catch(error=>{contactCache.delete('jumping');throw error;}));
  const reference=await contactCache.get('jumping');validateHopReference(reference.metadata,current);
  return reference;
}
async function mouthAsset(current){
  if(mouthPromise===null)mouthPromise=(async()=>{
    const root='../sources/reference/failed-mouth-v1';
    const paths=[`${root}/manifest.json`,`${root}/contract.json`,'../candidates/phase5/failed-mouth-v2/animation/build.json'];
    const [manifest,baseline,study]=await Promise.all(paths.map(async path=>{
      const response=await fetch(path,{cache:'no-cache'});
      if(!response.ok)throw new Error('old-mouth reference metadata unavailable');
      return response.json();
    }));
    validateMouthReference(manifest,baseline,study,current);
    const image=new Image();image.src=`${root}/${manifest.file}?v=${manifest.fileSha256}`;await image.decode();
    if(image.naturalWidth!==1536||image.naturalHeight!==208)throw new Error('old-mouth reference dimensions mismatch');
    return {image,manifest,baseline,study,frameHashes:baseline.frameHashes};
  })().catch(error=>{mouthPromise=null;throw error;});
  const result=await mouthPromise;
  validateMouthReference(result.manifest,result.baseline,result.study,current);
  return result;
}
function comparisonMode(reset=false){
  const gait=['run_right','run_left'].includes(mode),hop=mode==='jumping';
  const mouth=mode==='failed',precision=mode!=='waving_source';
  el('idle-comparison').disabled=!gait&&!hop&&!mouth&&!precision;
  el('sampling-reference-choice').disabled=!precision;
  el('mouth-reference-choice').disabled=!mouth;
  el('rigid-reference-choice').disabled=!gait;el('contact-reference-choice').disabled=!hop;
  const choice=el('idle-comparison').value;
  if(reset||(choice==='mouth'&&!mouth)||(!gait&&!hop&&!mouth&&choice!=='sampling')||(!precision&&choice==='sampling'))
    el('idle-comparison').value=gait?'rigid':hop?'contact':mouth?'mouth':'idle';
}
function size(){
  const width=Number(el('idle-size').value);
  for(const canvas of canvases){canvas.style.width=`${width}px`;canvas.style.height=`${Math.round(width*208/192)}px`;}
}
function slot(){
  if(manualIndex!==null||reduced()){
    const index=manualIndex??0;
    return {state:mode,index,static:false,completedAction:false,
            holdMs:durations[rows[mode]]?.[index],cycleMs:durations[rows[mode]]?.reduce((a,b)=>a+b,0)};
  }
  return candidateSlot(mode,elapsed());
}
async function draw(){
  if(!ready)return;
  const selected=slot(),key=`${selected.state}:${selected.index}`,thisRequest=request;
  const choice=el('idle-comparison').value;
  const {image,metadata}=await cache.get(selected.state);
  const precision=choice==='sampling';
  const reference=precision?{kind:'current',state:selected.state,index:selected.index,synchronized:true}
    :comparisonReference(choice,selected.state,selected.index);
  const precisionAsset=precision?await samplingAsset(selected.state,metadata):null;
  const referenceAsset=precision?{image,metadata}:reference.kind==='rigid'?await rigidAsset(reference.state,metadata)
    :reference.kind==='contact'?await contactAsset(metadata)
    :reference.kind==='mouth'?await mouthAsset(metadata):await asset(reference.state);
  const current=slot();
  if(!ready||thisRequest!==request||key!==`${current.state}:${current.index}`||choice!==el('idle-comparison').value)return;
  const referenceKey=candidateCelKey(referenceAsset.frameHashes??referenceAsset.metadata.frameHashes,reference.index);
  if(referenceKey!==lastReferenceKey){
    paintCel(contexts[0],referenceAsset.image,reference.index);
    lastReferenceKey=referenceKey;referencePaintCount++;
  }
  el('reference-candidate-title').textContent=precision?`同步现用采样 · ${reference.state} 第 ${reference.index+1} 格`
    :reference.kind==='rigid'?`同步旧小步 · ${reference.state} 第 ${reference.index+1} 格`
    :reference.kind==='contact'?`同步旧轻跃（高度场） · 第 ${reference.index+1} 格`
    :reference.kind==='mouth'?`同步旧嘴线 · failed 第 ${reference.index+1} 格`
    :reference.synchronized?`同步回退 · idle 第 ${reference.index+1} 格`:'同一母版 · 固定第 1 帧';
  el('reference-status').textContent=precision
    ?`左右同源/同姿势/同钟/同格；右侧仅末端浮点采样试验，未采用 · ${referencePaintCount} 次参考绘制 · 数值误差不代表审美通过`
    :reference.synchronized
    ?`左右共用同一时钟/帧位，暂停、单帧、减少动态及三轮回退同步 · ${referencePaintCount} 次参考绘制 · ${choice==='contact'?'旧高度场按同参数重建，非历史发布或视觉批准':choice==='mouth'?'failed时左旧嘴线、右现用新嘴线；回退时两侧同一idle。仅嘴线获开发基础批准，完整动作待验收':'旧版归档d804cd5，不继承完整视觉批准'}`
    :'固定 idle 只用于身份检查，不是同节奏动作对照。';
  const paintKey=candidateCelKey(precision?precisionAsset.entry.candidateFrameHashes:metadata.frameHashes,selected.index);
  if(paintKey!==lastKey){
    paintCel(contexts[1],precision?precisionAsset.image:image,selected.index,precision?precisionAsset.entry.nativeRows[0]:0);
    lastKey=paintKey;paintCount++;
  }
  el('idle-frame').max=String(durations[rows[selected.state]].length-1);
  el('idle-frame').value=String(selected.index);
  el('idle-frame').disabled=false;
  el('idle-pause').disabled=reduced();
  el('idle-pause').textContent=paused?'播放候选':'暂停候选';
  const labels={run_right:'run_right · 正面向右小步原型',run_left:'run_left · 正面向左小步原型',review:'review · 六格低手下视候选',waiting:'waiting · 六格托腮保持候选',failed:'failed · 八帧轻微失落',jumping:'jumping · 五帧轻跃候选',waving:'waving · 四格招手候选',processing:'processing · 清醒专注候选',idle:'idle · 六帧微呼吸'};
  labels.waving_source='waving · 原像素低位试验，未采用';
  labels.failed='failed · 八格新嘴线开发基础';
  const label=labels[selected.state];
  el('current-candidate-title').textContent=precision?`${label} · 浮点采样试验，未采用`:label;
  const status=manualIndex!==null?'单帧检查':reduced()?'减少动态':paused?'已暂停':selected.completedAction?'三轮已结束，已回 idle':'实际时长播放';
  const timing=` · 第 ${selected.index+1}/${durations[rows[selected.state]].length} 帧 · 停留 ${selected.holdMs} ms · 周期 ${selected.cycleMs} ms`;
  const followHint=['run_right','run_left'].includes(selected.state)?' · 耳发按身体运动轻微滞后，非实时物理':'';
  const dragBoundary=['run_right','run_left'].includes(mode)?' · 此处仅行内时钟；真实拖拽可随时中断/恢复底层状态，无速度同步':'';
  el('idle-status').textContent=`${label}${precision?' · 浮点采样试验，未采用':''} · ${status}${timing}${followHint}${dragBoundary} · ${paintCount} 次候选绘制 · 未经完整视觉验收，非完成宠物，未安装`;
}
function schedule(){
  if(!canRun())return;
  if(startedAt===null)startedAt=performance.now();
  if(timer!==null)clearTimeout(timer);
  timer=setTimeout(async()=>{timer=null;await draw();schedule();},Math.max(1,candidateSlot(mode,elapsed()).untilNext+.5));
}
async function selectMode(){
  const thisRequest=++request;
  const selectedMode=el('idle-action').value;
  stopClock();ready=false;mode=selectedMode;baseElapsed=0;manualIndex=null;paused=false;lastKey='';
  lastReferenceKey='';
  const gait=['run_right','run_left'].includes(mode);
  comparisonMode(true);
  el('idle-status').textContent=`正在解码 ${mode} 候选…`;
  el('idle-frame').max=String(durations[rows[mode]]?.length-1);
  el('idle-frame').value='0';el('idle-pause').disabled=true;
  try{
    if(!(selectedMode in sources))throw new Error('unsupported candidate');
    const [,current]=await Promise.all([asset('idle'),asset(selectedMode)]);
    if(thisRequest!==request)return;
    if(gait)await rigidAsset(selectedMode,current.metadata);
    if(selectedMode==='jumping')await contactAsset(current.metadata);
    if(selectedMode==='failed')await mouthAsset(current.metadata);
    if(thisRequest!==request)return;
    ready=true;size();await draw();schedule();
  }catch(error){if(thisRequest!==request)return;el('idle-status').textContent=`候选加载失败：${error.message}`;console.error(error);}
}
el('idle-action').addEventListener('change',selectMode);
el('idle-comparison').addEventListener('change',async()=>{
  el('idle-status').textContent='正在加载所选对照；画面尚未完成切换…';
  try{await draw();}
  catch(error){el('idle-status').textContent=`对照加载失败，未替换上次画面：${error.message}`;console.error(error);}
});
el('idle-pause').addEventListener('click',async()=>{stopClock();paused=!paused;manualIndex=null;await draw();schedule();});
el('idle-restart').addEventListener('click',async()=>{stopClock();baseElapsed=0;manualIndex=null;paused=false;await draw();schedule();});
el('idle-frame').addEventListener('input',async()=>{
  // After action fallback the displayed frames belong to idle, not the
  // shorter hop row. Inspect the displayed state; restart still replays the
  // selected action until the user deliberately starts manual inspection.
  const inspectState=slot().state,index=Number(el('idle-frame').value);
  stopClock();mode=inspectState;el('idle-action').value=mode;
  comparisonMode();
  paused=true;manualIndex=index;baseElapsed=candidatePoseOffset(mode,index);await draw();
});
el('idle-size').addEventListener('change',size);
el('idle-background').addEventListener('change',()=>{el('idle-stage').className=`stage ${el('idle-background').value}`;});
el('idle-reduced').addEventListener('change',async()=>{stopClock();manualIndex=null;await draw();schedule();});
media.addEventListener('change',async event=>{stopClock();el('idle-reduced').checked=event.matches;manualIndex=null;await draw();schedule();});
document.addEventListener('visibilitychange',async()=>{stopClock();if(!document.hidden)await draw();schedule();});
window.addEventListener('pagehide',stopClock);
window.addEventListener('pageshow',async()=>{await draw();schedule();});
await selectMode();
