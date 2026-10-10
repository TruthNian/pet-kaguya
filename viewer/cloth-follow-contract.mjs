import {candidateCelKey} from './candidate-clock.mjs';

const spec={timeConstantMs:190,gain:.25,maximumOffsetSourcePx:2.5,
  sample:'native-hold-midpoint',boundary:'periodic-steady-state',
  ellipses:[{center:[353,915],radii:[69,82]},{center:[857,919],radii:[68,78]}],
  protectedRects:[[275,20,955,485],[264,705,413,808],[812,705,952,815],
    [395,450,815,936],[400,912,830,1240]],protectionFadeSourcePx:24};
const same=(a,b)=>JSON.stringify(a)===JSON.stringify(b);
const holds=[120,120,120,120,120,120,120,220];

export function validateClothStudy(metadata,state,current){
  if(!['run_right','run_left'].includes(state)||current?.state!==state
      ||metadata?.sourceSha256!=='65401EFDFEF0205D0CEA30AD08A0F14911C20B1B83468DBB6B3619E7DC89430A'
      ||metadata.sourceSha256!==current.sourceSha256
      ||typeof current.camera?.scale!=='number'||!Number.isFinite(current.camera.scale)||current.camera.scale<=0
      ||metadata.method!=='compact-side-sleeve-source-field; periodic-held-root-lag'
      ||!same(metadata.spec,spec)||!same(metadata.durationsMs,holds)
      ||!same(metadata.durationsMs,current.durationsMs)||!same(metadata.camera,current.camera)
      ||metadata.repeatBeforeIdle!==3||metadata.animationBuilt!==true
      ||metadata.visualMotionApproval!=='pending'||metadata.specificMotionUserApproval!=='pending'
      ||['newArtworkGenerated','facialGeometryRepair','nativeInterpolation','cleanClothLayersRecovered',
        'physicalClothSimulation','liveDragLagInitialization','adopted','activeAtlasChanged',
        'installableFullAtlas','installed'].some(key=>metadata[key]!==false))
    throw new Error('Invalid unadopted sleeve study boundary');
  const offsets=metadata.response?.offsetsSourcePx;
  if(!Array.isArray(offsets)||offsets.length!==8
      ||offsets.some(v=>typeof v!=='number'||!Number.isFinite(v)||Math.abs(v)>2.5)
      ||!Number.isFinite(metadata.response.initialStateSourcePx)||!Number.isFinite(metadata.response.endStateSourcePx)
      ||Math.abs(metadata.response.initialStateSourcePx-metadata.response.endStateSourcePx)>1e-9
      ||typeof metadata.maximumOffsetOutputPx!=='number'||!Number.isFinite(metadata.maximumOffsetOutputPx)
      ||Math.abs(metadata.maximumOffsetOutputPx-Math.max(...offsets.map(Math.abs))*current.camera.scale)>1e-9)
    throw new Error('Sleeve response or output-scale boundary mismatch');
  const entry=metadata.states?.[state];
  if(!entry||entry.nativeRow!==({run_right:1,run_left:2})[state]||entry.nativeRow!==current.nativeRow
      ||entry.parentSourceSha256!==current.sourceSha256||entry.actualCurrentParentReconstructedExactly!==true
      ||!same(entry.parentFrameHashes,current.frameHashes)||entry.frameHashes?.length!==8
      ||['rootOffsetsSourcePx','footOffsetsSourcePx','focusOffsetSourcePx','tipOffsetsSourcePx'].some(key=>
        current[key]===undefined||!same(entry[key],current[key]))||entry.differences?.length!==8)
    throw new Error('Sleeve comparison does not match actual current source/gait/cels');
  entry.frameHashes.forEach((_,index)=>candidateCelKey(entry.frameHashes,index));
  entry.parentFrameHashes.forEach((_,index)=>candidateCelKey(entry.parentFrameHashes,index));
  for(const d of entry.differences){
    if(!d||!Number.isInteger(d.changedRGBAPixels)||d.changedRGBAPixels<=0
        ||!Number.isInteger(d.changedRGBPixels)||d.changedRGBPixels<=0||d.changedRGBPixels>d.changedRGBAPixels
        ||!Number.isInteger(d.changedAlphaPixels)||d.changedAlphaPixels<0||d.changedAlphaPixels>d.changedRGBAPixels
        ||!Number.isInteger(d.maximumAlphaDifference)||d.maximumAlphaDifference<0||d.maximumAlphaDifference>255
        ||!Number.isInteger(d.maximumChannelDifference)||d.maximumChannelDifference<=0||d.maximumChannelDifference>255
        ||d.maximumAlphaDifference>d.maximumChannelDifference
        ||(d.changedAlphaPixels===0)!==(d.maximumAlphaDifference===0)
        ||!Array.isArray(d.bounds)||d.bounds.length!==4||d.bounds.some(v=>!Number.isInteger(v))
        ||d.bounds[0]<42||d.bounds[2]>153||d.bounds[1]<132||d.bounds[3]>174
        ||d.bounds[0]>=d.bounds[2]||d.bounds[1]>=d.bounds[3])
      throw new Error('Sleeve actual pixel evidence is missing or inconsistent');
  }
  if(entry.allNativeAlphaExact!==entry.differences.every(d=>d.changedAlphaPixels===0))
    throw new Error('Sleeve alpha preservation claim disagrees with recorded actual changes');
  return entry;
}
