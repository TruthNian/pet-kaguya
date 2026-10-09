// Current v3-only development candidates. Historical preview is separate.
import {durations} from './clock.mjs';
import {candidateRows as rows,candidateSlot,candidatePoseOffset,candidateCelKey} from './candidate-clock.mjs';

const el=id=>document.getElementById(id);
const canvases=[el('idle-reference'),el('idle-animated')];
const contexts=canvases.map(canvas=>canvas.getContext('2d',{alpha:true}));
const media=matchMedia('(prefers-reduced-motion: reduce)');
el('idle-reduced').checked=media.matches;
const sources={idle:'idle',run_right:'run_right',run_left:'run_left',failed:'failed',jumping:'jumping',waving:'waving',waving_source:'wave-source-rig-v3',processing:'processing',waiting:'waiting',review:'review'};
const cache=new Map();
let mode='idle',ready=false,timer=null,baseElapsed=0,startedAt=null,paused=false,manualIndex=null,lastKey='',paintCount=0,request=0;
const reduced=()=>el('idle-reduced').checked;
const elapsed=()=>baseElapsed+(startedAt===null?0:performance.now()-startedAt);
const canRun=()=>ready&&!paused&&!reduced()&&!document.hidden;

async function asset(state){
  if(!cache.has(state))cache.set(state,(async()=>{
    const root=`../candidates/phase5/${sources[state]}`;
    const response=await fetch(`${root}/build.json`);
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
    if(state==='waiting'&&(metadata.animationBuilt!==true||metadata.nativeRow!==6
        ||metadata.handStrategy!=='held-chin-contact'||metadata.strategyUserApproval!=='pending'
        ||metadata.closedEyeFrames!==0||metadata.bodyPulse!==false||metadata.repeatBeforeIdle!==3))
      throw new Error('waiting held-contact candidate boundary mismatch');
    if(state==='processing'&&(metadata.nativeState!=='running'||metadata.nativeRow!==7
        ||metadata.closedEyeFrames!==0||metadata.bodyPulse!==false||metadata.ornamentFlash!==false
        ||metadata.repeatBeforeIdle!==3||metadata.visualMotionApproval!=='pending'))
      throw new Error('processing state or restrained-motion boundary mismatch');
    if(state==='review'&&(metadata.animationBuilt!==true||metadata.nativeRow!==8
        ||metadata.rightArmCompositionVersion!=='review-art-v4'||metadata.newArtworkGenerated!==false
        ||metadata.originalLowerHandContourRestored!==true||metadata.handScaled!==false
        ||metadata.knownSourceHairRGBAExact!==true||metadata.paintedHairAlphaContinuityEstimated!==true
        ||metadata.handStrategy!=='two-low-hands-held'||metadata.strategyUserApproval!=='pending'
        ||metadata.closedEyeFrames!==0||metadata.bodyPulse!==false||metadata.ornamentFlash!==false
        ||metadata.repeatBeforeIdle!==3||metadata.visualMotionApproval!=='pending'))
      throw new Error('review state or unapproved-motion boundary mismatch');
    if(['run_right','run_left'].includes(state)&&(metadata.animationBuilt!==true||metadata.nativeRow!==rows[state]
        ||metadata.projection!=='front-held-alternating-small-steps'||metadata.strategyUserApproval!=='approved'
        ||metadata.strategyApprovalScope!=='front-held-small-steps-only'
        ||metadata.strategyUserDecision!=='sources/canonical/locomotion-decision-20261009.json'
        ||metadata.artMirrored!==false||metadata.hostVelocitySynchronization!==false||metadata.screenWorldNoSlipProven!==false
        ||metadata.actualDragReleaseCanInterruptAnyCel!==true||metadata.visualMotionApproval!=='pending'))
      throw new Error('drag-feedback candidate boundary mismatch');
    if(['run_right','run_left'].includes(state)&&(metadata.legCompositionVersion!=='leg-material-v2'
        ||metadata.neutralLegCompositorRGBAExact!==true||metadata.neutralLegCompositorNativeRGBAExact!==true
        ||metadata.sourceAlphaAndOcclusionSeparated!==true||metadata.artistLayerRecoveryClaimed!==false))
      throw new Error('conditioned leg composition boundary mismatch');
    const image=new Image();image.src=`${root}/strip.webp`;await image.decode();
    if(image.naturalWidth!==1536||image.naturalHeight!==208)throw new Error(`${state} dimensions mismatch`);
    return {image,metadata};
  })().catch(error=>{cache.delete(state);throw error;}));
  return cache.get(state);
}
function stopClock(){
  if(startedAt!==null){baseElapsed+=performance.now()-startedAt;startedAt=null;}
  if(timer!==null){clearTimeout(timer);timer=null;}
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
  const selected=slot(),key=`${selected.state}:${selected.index}`;
  const {image,metadata}=await cache.get(selected.state);
  const current=slot();
  if(!ready||key!==`${current.state}:${current.index}`)return;
  const paintKey=candidateCelKey(metadata.frameHashes,selected.index);
  if(paintKey!==lastKey){
    const context=contexts[1];context.clearRect(0,0,192,208);context.imageSmoothingEnabled=false;
    context.drawImage(image,selected.index*192,0,192,208,0,0,192,208);
    lastKey=paintKey;paintCount++;
  }
  el('idle-frame').max=String(durations[rows[selected.state]].length-1);
  el('idle-frame').value=String(selected.index);
  el('idle-frame').disabled=false;
  el('idle-pause').disabled=reduced();
  el('idle-pause').textContent=paused?'播放候选':'暂停候选';
  const labels={run_right:'run_right · 正面向右小步原型',run_left:'run_left · 正面向左小步原型',review:'review · 六格低手下视候选',waiting:'waiting · 六格托腮保持候选',failed:'failed · 八帧轻微失落',jumping:'jumping · 五帧轻跃候选',waving:'waving · 四格招手候选',processing:'processing · 清醒专注候选',idle:'idle · 六帧微呼吸'};
  labels.waving_source='waving · 原像素低位试验，未采用';
  const label=labels[selected.state];
  el('current-candidate-title').textContent=label;
  const status=manualIndex!==null?'单帧检查':reduced()?'减少动态':paused?'已暂停':selected.completedAction?'三轮已结束，已回 idle':'实际时长播放';
  const timing=` · 第 ${selected.index+1}/${durations[rows[selected.state]].length} 帧 · 停留 ${selected.holdMs} ms · 周期 ${selected.cycleMs} ms`;
  const dragBoundary=['run_right','run_left'].includes(mode)?' · 此处仅行内时钟；真实拖拽可随时中断/恢复底层状态，无速度同步':'';
  el('idle-status').textContent=`${label} · ${status}${timing}${dragBoundary} · ${paintCount} 次候选绘制 · 未经完整视觉验收，非完成宠物，未安装`;
}
function schedule(){
  if(!canRun())return;
  if(startedAt===null)startedAt=performance.now();
  if(timer!==null)clearTimeout(timer);
  timer=setTimeout(async()=>{timer=null;await draw();schedule();},Math.max(1,candidateSlot(mode,elapsed()).untilNext+.5));
}
async function selectMode(){
  const thisRequest=++request;
  stopClock();ready=false;mode=el('idle-action').value;baseElapsed=0;manualIndex=null;paused=false;lastKey='';
  el('idle-status').textContent=`正在解码 ${mode} 候选…`;
  el('idle-frame').max=String(durations[rows[mode]]?.length-1);
  el('idle-frame').value='0';el('idle-pause').disabled=true;
  try{
    if(!(mode in sources))throw new Error('unsupported candidate');
    const [{image}]=await Promise.all([asset('idle'),asset(mode)]);
    if(thisRequest!==request)return;
    contexts[0].imageSmoothingEnabled=false;contexts[0].drawImage(image,0,0,192,208,0,0,192,208);
    ready=true;size();await draw();schedule();
  }catch(error){if(thisRequest===request)el('idle-status').textContent=`候选加载失败：${error.message}`;console.error(error);}
}
el('idle-action').addEventListener('change',selectMode);
el('idle-pause').addEventListener('click',async()=>{stopClock();paused=!paused;manualIndex=null;await draw();schedule();});
el('idle-restart').addEventListener('click',async()=>{stopClock();baseElapsed=0;manualIndex=null;paused=false;await draw();schedule();});
el('idle-frame').addEventListener('input',async()=>{
  // After action fallback the displayed frames belong to idle, not the
  // shorter hop row. Inspect the displayed state; restart still replays the
  // selected action until the user deliberately starts manual inspection.
  const inspectState=slot().state,index=Number(el('idle-frame').value);
  stopClock();mode=inspectState;el('idle-action').value=mode;
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
