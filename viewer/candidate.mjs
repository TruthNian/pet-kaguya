// Current v3-only development candidates. Historical preview is separate.
import {durations} from './clock.mjs';
import {candidateRows as rows,candidateSlot,candidatePoseOffset,candidateCelKey} from './candidate-clock.mjs?v=20261010-wave-link-1';
import {paintCel} from './cel-painter.mjs?v=20261010-terminal-precision-v1';
import {comparisonReference,comparisonPolicy,validateRigidReference,validateHopReference,validateMouthReference} from './comparison-reference.mjs?v=20261010-wave-middle-dev-1';
import {validateWaveAmplitude,validateCurrentWave,validateWaveMiddleReference} from './wave-amplitude-contract.mjs?v=20261010-wave-middle-dev-1';
import {validateClothStudy} from './cloth-follow-contract.mjs';
import {validateReviewOverlapMetadata,validateReviewOverlapReference} from './review-overlap-contract.mjs';
import {validateMaterialSupport} from './material-support-contract.mjs';
import {validateReviewMetadata} from './review-contract.mjs';
import {validateWaitingMetadata} from './waiting-contract.mjs';
import {validateSamplingStudy} from './sampling-contract.mjs';
import {validateHopHeightStudy} from './height-contract.mjs?v=20261010-support-2';

const el=id=>document.getElementById(id);
const canvases=[el('idle-reference'),el('idle-animated')];
const contexts=canvases.map(canvas=>canvas.getContext('2d',{alpha:true}));
const media=matchMedia('(prefers-reduced-motion: reduce)');
el('idle-reduced').checked=media.matches;
const sources={idle:'idle',run_right:'run_right',run_left:'run_left',failed:'failed',jumping:'jumping',waving:'waving',waving_source:'wave-source-rig-v3',waving_link:'wave-middle-link-v1',processing:'processing',waiting:'waiting',review:'review',review_overlap:'review-hands-overlap-v1/animation'};
const cache=new Map();
const rigidCache=new Map();
const contactCache=new Map();
const clothCache=new Map();
let samplingPromise=null;
let mouthPromise=null;
let heightPromise=null;
let handsPromise=null;
let wavePromise=null;
let middleBeforePromise=null;
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
    if(state==='waving')validateCurrentWave(metadata);
    if(state==='waving_link'){
      const current=(await asset('waving')).metadata;
      if(metadata.state!=='waving'||metadata.previewVariant!=='waving_link'||metadata.nativeRow!==3
          ||metadata.adopted!==false||metadata.activeAtlasChanged!==false||metadata.nativeInterpolation!==false
          ||metadata.visualMotionApproval!=='pending'||metadata.repeatBeforeIdle!==3
          ||metadata.generatedSha256!=='2E5DFACB79D7649034D46FE368D87411DEFD9CA5423C99BF484BAF9ABE05A0B8'
          ||JSON.stringify(metadata.camera)!==JSON.stringify(current.camera)
          ||JSON.stringify(metadata.baselineFrameHashes)!==JSON.stringify(current.frameHashes)
          ||[1,3].some(i=>metadata.frameHashes[i]!==current.frameHashes[i])
          ||metadata.frameHashes[0]!==metadata.frameHashes[2])
        throw new Error('Wave middle candidate source, unchanged peak/rest or pending boundary mismatch');
    }
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
    if(state==='review_overlap')validateReviewOverlapMetadata(metadata);
    if(['jumping','run_right','run_left'].includes(state))validateMaterialSupport(metadata);
    if(state==='jumping'&&(metadata.groundedContactVersion!=='two-link-source-material-v1'
        ||metadata.originalAirCelsRGBAExact!==true||metadata.airMaterialIdentityProven!==false
        ||metadata.strategyApprovalInheritedFromLocomotion!==false
        ||metadata.artistLayerRecoveryClaimed!==false||metadata.newArtworkGenerated!==false
        ||metadata.continuousLandingProven!==false||metadata.physicalBalanceProven!==false
        ||metadata.apexOutputPx!==4||metadata.heightVisualApproval!=='approved-as-development-basis'
        ||metadata.heightApprovalScope!=='hop-height-development-basis-only'
        ||metadata.heightUserDecision!=='sources/canonical/jumping-height-decision-20261010.json'
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
async function clothAsset(state,current){
  if(!clothCache.has(state))clothCache.set(state,(async()=>{
    const root='../candidates/phase5/cloth-follow-v1';
    const response=await fetch(`${root}/build.json`,{cache:'no-cache'});
    if(!response.ok)throw new Error('Sleeve study metadata unavailable');
    const metadata=await response.json();
    const entry=validateClothStudy(metadata,state,current);
    const image=new Image();image.src=`${root}/${state}/strip.webp?v=${entry.frameHashes.join('')}`;
    await image.decode();
    if(image.naturalWidth!==1536||image.naturalHeight!==208)throw new Error('Sleeve study dimensions mismatch');
    return {image,metadata};
  })().catch(error=>{clothCache.delete(state);throw error;}));
  const result=await clothCache.get(state);
  return {...result,entry:validateClothStudy(result.metadata,state,current)};
}
function stopClock(){
  if(startedAt!==null){baseElapsed+=performance.now()-startedAt;startedAt=null;}
  if(timer!==null){clearTimeout(timer);timer=null;}
}
async function waveAsset(current){
  if(wavePromise===null)wavePromise=(async()=>{
    const root='../sources/reference/waving-amplitude-high';
    const paths=[`${root}/manifest.json`,`${root}/contract.json`,'../candidates/phase5/wave-amplitude-v1/build.json'];
    const [manifest,baseline,metadata]=await Promise.all(paths.map(async path=>{
      const response=await fetch(path,{cache:'no-cache'});
      if(!response.ok)throw new Error('Frozen wave reference unavailable');
      return response.json();
    }));
    validateWaveAmplitude(metadata,current,manifest,baseline);
    const image=new Image();image.src=`${root}/${manifest.file}?v=${manifest.fileSha256}`;
    await image.decode();
    if(image.naturalWidth!==1536||image.naturalHeight!==208)throw new Error('Lowered wave dimensions mismatch');
    return {image,metadata,manifest,baseline,frameHashes:baseline.frameHashes};
  })().catch(error=>{wavePromise=null;throw error;});
  const result=await wavePromise;validateWaveAmplitude(result.metadata,current,result.manifest,result.baseline);return result;
}
async function middleBeforeAsset(current){
  if(middleBeforePromise===null)middleBeforePromise=(async()=>{
    const root='../sources/reference/waving-middle-before';
    const response=await fetch(`${root}/build.json`,{cache:'no-cache'});
    if(!response.ok)throw new Error('Pre-middle wave reference unavailable');
    const metadata=validateWaveMiddleReference(await response.json(),current);
    const image=new Image();image.src=`${root}/strip.webp?v=${metadata.frameHashes[0]}`;
    await image.decode();
    if(image.naturalWidth!==1536||image.naturalHeight!==208)throw new Error('Pre-middle wave dimensions mismatch');
    return {image,metadata,frameHashes:metadata.frameHashes};
  })().catch(error=>{middleBeforePromise=null;throw error;});
  const result=await middleBeforePromise;validateWaveMiddleReference(result.metadata,current);return result;
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
async function heightAsset(current){
  if(heightPromise===null)heightPromise=(async()=>{
    const root='../sources/reference/jumping-height-8px';
    const paths=[`${root}/manifest.json`,`${root}/contract.json`,'../candidates/phase5/jumping-height-v1/build.json'];
    const [manifest,baseline,study]=await Promise.all(paths.map(async path=>{
      const response=await fetch(path,{cache:'no-cache'});
      if(!response.ok)throw new Error('8px hop reference metadata unavailable');
      return response.json();
    }));
    validateHopHeightStudy(study,baseline,current,manifest);
    const image=new Image();image.src=`${root}/${manifest.file}?v=${manifest.fileSha256}`;await image.decode();
    if(image.naturalWidth!==1536||image.naturalHeight!==208)throw new Error('8px hop reference dimensions mismatch');
    return {image,manifest,baseline,study,frameHashes:baseline.frameHashes};
  })().catch(error=>{heightPromise=null;throw error;});
  const result=await heightPromise;
  validateHopHeightStudy(result.study,result.baseline,current,result.manifest);
  return result;
}
async function handsAsset(study){
  const current=(await asset('review')).metadata;
  if(handsPromise===null)handsPromise=(async()=>{
    const root='../sources/reference/review-held-v6';
    const [manifest,baseline]=await Promise.all(['manifest.json','contract.json'].map(async file=>{
      const response=await fetch(`${root}/${file}`,{cache:'no-cache'});
      if(!response.ok)throw new Error('Frozen review hand reference unavailable');
      return response.json();
    }));
    validateReviewOverlapReference(manifest,baseline,study,current);
    const image=new Image();image.src=`${root}/${manifest.file}?v=${manifest.fileSha256}`;await image.decode();
    if(image.naturalWidth!==1536||image.naturalHeight!==208)throw new Error('Frozen review dimensions mismatch');
    return {image,metadata:baseline,manifest,frameHashes:baseline.frameHashes};
  })().catch(error=>{handsPromise=null;throw error;});
  const result=await handsPromise;
  validateReviewOverlapReference(result.manifest,result.metadata,study,current);
  return result;
}
function comparisonMode(reset=false){
  const policy=comparisonPolicy(mode,el('idle-comparison').value,reset);
  el('idle-comparison').disabled=policy.allowed.length===1;
  for(const choice of ['height','sampling','mouth','rigid','contact','hands','cloth','wave','link'])
    el(`${choice}-reference-choice`).disabled=!policy.allowed.includes(choice);
  el('idle-comparison').value=policy.choice;
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
  const cloth=choice==='cloth'&&['run_right','run_left'].includes(selected.state);
  const wave=choice==='wave'&&selected.state==='waving';
  const reference=precision?{kind:'current',state:selected.state,index:selected.index,synchronized:true}
    :comparisonReference(choice,selected.state,selected.index);
  const precisionAsset=precision?await samplingAsset(selected.state,metadata):null;
  const sleeveAsset=cloth?await clothAsset(selected.state,metadata):null;
  const referenceAsset=precision||reference.kind==='current'?{image,metadata}:reference.kind==='rigid'?await rigidAsset(reference.state,metadata)
    :reference.kind==='middle-before'?await middleBeforeAsset(metadata)
    :reference.kind==='wave'?await waveAsset(metadata)
    :reference.kind==='contact'?await contactAsset(metadata)
    :reference.kind==='height'?await heightAsset(metadata)
    :reference.kind==='mouth'?await mouthAsset(metadata)
    :reference.kind==='hands'?await handsAsset(metadata):await asset(reference.state);
  const current=slot();
  if(!ready||thisRequest!==request||key!==`${current.state}:${current.index}`||choice!==el('idle-comparison').value)return;
  const referenceKey=candidateCelKey(referenceAsset.frameHashes??referenceAsset.metadata.frameHashes,reference.index);
  if(referenceKey!==lastReferenceKey){
    paintCel(contexts[0],referenceAsset.image,reference.index);
    lastReferenceKey=referenceKey;referencePaintCount++;
  }
  el('reference-candidate-title').textContent=wave?`同步旧招手 · 第 ${reference.index+1} 格`
    :reference.state==='waving'&&reference.kind==='candidate'?`同步现用招手 · 第 ${reference.index+1} 格`
    :cloth?`同步现用袖角 · ${reference.state} 第 ${reference.index+1} 格`
    :precision?`同步现用采样 · ${reference.state} 第 ${reference.index+1} 格`
    :reference.kind==='middle-before'?`同步改动前招手 · 第 ${reference.index+1} 格`
    :reference.kind==='rigid'?`同步旧小步 · ${reference.state} 第 ${reference.index+1} 格`
    :reference.kind==='contact'?`同步旧轻跃（高度场） · 第 ${reference.index+1} 格`
    :reference.kind==='mouth'?`同步旧嘴线 · failed 第 ${reference.index+1} 格`
    :reference.kind==='height'?`同步旧幅度 · 8px · 第 ${reference.index+1} 格`
    :reference.kind==='hands'?`同步现用双手 · review v6 第 ${reference.index+1} 格`
    :reference.synchronized?`同步回退 · idle 第 ${reference.index+1} 格`:'同一母版 · 固定第 1 帧';
  el('reference-status').textContent=choice==='link'
    ?`左右同钟/同格；左冻结改动前，右现用中间格开发改进 · ${referencePaintCount} 次参考绘制 · ${selected.state==='waving'?'只改第1/3格；认可的峰值及原图放松格保持精确。开发者选择，完整手形/招手待确认，不继承用户批准':'三轮已结束，两侧同步同一idle'}`
    :choice==='wave'
    ?`左右同钟/同格；左冻结旧招手，右现用降低抬手开发基础 · ${referencePaintCount} 次参考绘制 · ${wave?'仅第2格手掌降低约8.7原生像素；原掌按估计掩码保护，局部补画袖带连接。你已确认此版为开发基础，完整动作未通过':'三轮已结束，两侧同步同一idle'}`
    :choice==='cloth'
    ?`左右同钟/同格；左现用，右袖角跟随试验，未采用 · ${referencePaintCount} 次参考绘制 · ${cloth?'只改下垂袖角附近源坐标，也影响附近可见底图；局部alpha如实变化，脸/手/腰饰/腿鞋与步态固定，不是真实布料模拟':'三轮已结束，两侧同步同一idle，未附加袖角变形'}`
    :precision
    ?`左右同源/同姿势/同钟/同格；右侧仅末端浮点采样试验，未采用 · ${referencePaintCount} 次参考绘制 · 数值误差不代表审美通过`
    :reference.synchronized
    ?`左右共用同一时钟/帧位，暂停、单帧、减少动态及三轮回退同步 · ${referencePaintCount} 次参考绘制 · ${choice==='hands'?'历史手对照已停用，不代表现用眼层':choice==='height'?'左冻结8px、右现用4px开发基础；另含局部采样修复（最多1通道值，alpha/轨迹不变），不代表完整动作通过':choice==='contact'?'旧高度场按现用4px参数重建，非冻结8px版本或视觉批准':choice==='mouth'?'failed时左旧嘴线、右现用新嘴线；回退时两侧同一idle。仅嘴线获开发基础批准，完整动作待验收':'旧版归档d804cd5；右版含耳发跟随、局部滤波及眼部提取修复，非严格单变量或完整视觉批准'}`
    :'固定 idle 只用于身份检查，不是同节奏动作对照。';
  const paintKey=candidateCelKey(cloth?sleeveAsset.entry.frameHashes:precision?precisionAsset.entry.candidateFrameHashes:metadata.frameHashes,selected.index);
  if(paintKey!==lastKey){
    paintCel(contexts[1],cloth?sleeveAsset.image:precision?precisionAsset.image:image,selected.index,precision?precisionAsset.entry.nativeRows[0]:0);
    lastKey=paintKey;paintCount++;
  }
  el('idle-frame').max=String(durations[rows[selected.state]].length-1);
  el('idle-frame').value=String(selected.index);
  el('idle-frame').disabled=false;
  el('idle-pause').disabled=reduced();
  el('idle-pause').textContent=paused?'播放候选':'暂停候选';
  const labels={run_right:'run_right · 正面向右小步原型',run_left:'run_left · 正面向左小步原型',review:'review · 六格低手下视候选',waiting:'waiting · 六格托腮保持候选',failed:'failed · 八帧轻微失落',jumping:'jumping · 五帧轻跃候选',waving:'waving · 四格招手候选',processing:'processing · 清醒专注候选',idle:'idle · 六帧微呼吸'};
  labels.waving_source='waving · 原像素低位试验，未采用';
  labels.waving_link='waving · 中间格衔接试验，未采用';
  labels.review_overlap='review · 六格低位相叠手试验，未采用';
  labels.jumping='jumping · 4px轻跃开发基础';
  labels.failed='failed · 八格新嘴线开发基础';
  labels.waving='waving · 中间格衔接开发改进';
  const label=labels[selected.state];
  el('current-candidate-title').textContent=cloth?`${label} · 袖角跟随试验，未采用`:precision?`${label} · 浮点采样试验，未采用`:label;
  const status=manualIndex!==null?'单帧检查':reduced()?'减少动态':paused?'已暂停':selected.completedAction?'三轮已结束，已回 idle':'实际时长播放';
  const timing=` · 第 ${selected.index+1}/${durations[rows[selected.state]].length} 帧 · 停留 ${selected.holdMs} ms · 周期 ${selected.cycleMs} ms`;
  const followHint=['run_right','run_left'].includes(selected.state)?' · 耳发按身体运动轻微滞后，非实时物理':'';
  const dragBoundary=['run_right','run_left'].includes(mode)?' · 此处仅行内时钟；真实拖拽可随时中断/恢复底层状态，无速度同步':'';
  el('idle-status').textContent=`${label}${cloth?' · 袖角跟随试验，未采用':precision?' · 浮点采样试验，未采用':''} · ${status}${timing}${followHint}${dragBoundary} · ${paintCount} 次候选绘制 · 未经完整视觉验收，非完成宠物，未安装`;
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
    if(selectedMode==='jumping')await Promise.all([contactAsset(current.metadata),heightAsset(current.metadata)]);
    if(selectedMode==='failed')await mouthAsset(current.metadata);
    if(selectedMode==='review_overlap')await handsAsset(current.metadata);
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
