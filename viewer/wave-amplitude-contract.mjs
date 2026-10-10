import {candidateCelKey} from './candidate-clock.mjs';

export function validateCurrentWave(current){
  if(current.state!=='waving'||current.nativeRow!==3||current.repeatBeforeIdle!==3
      ||current.amplitudeVisualApproval!=='approved-as-development-basis'
      ||current.amplitudeApprovalScope!=='waving-lower-amplitude-development-basis-only'
      ||current.amplitudeUserDecision!=='sources/canonical/waving-amplitude-adoption-20261010.json'
      ||current.handLoweringSourcePx!==55
      ||current.frameHashes?.[1]!=='61C09D34D0A702F5AA5B472FAE38D8945BED2836E7EA61A55E63C0B1F65EF3D6'
      ||current.visualMotionApproval!=='pending'||current.installed!==false||current.installableFullAtlas!==false)
    throw new Error('Wave development-basis approval/source boundary mismatch');
  if(current.middleDevelopmentBasis===undefined){
    if(JSON.stringify(current.unchangedOriginalHoldIndices)!=='[0,2,3]')
      throw new Error('Frozen amplitude-only wave must preserve original middle/rest');
  }else if(current.middleDevelopmentBasis!=='developer-selected-continuity-improvement'
      ||current.middleSource!=='candidates/phase5/wave-middle-link-v1'
      ||current.middleGeneratedSha256!=='2E5DFACB79D7649034D46FE368D87411DEFD9CA5423C99BF484BAF9ABE05A0B8'
      ||current.middleVisualApproval!=='pending'||current.middleUserApprovalClaimed!==false
      ||current.newMiddleArtworkGeneratedThisIteration!==false
      ||current.middleUsesAuthoredHandNotOriginalPalmPixels!==true
      ||JSON.stringify(current.unchangedOriginalHoldIndices)!=='[3]'
      ||JSON.stringify(current.unchangedAcceptedAmplitudeHoldIndices)!=='[1,3]'
      ||current.middleReference!=='sources/reference/waving-middle-before'
      ||current.middleNativeRGBAHash!=='1ADE339D8E003656323BC65FCECCE5B9E6591BF1B53486DBD4A82C4322E4D043'
      ||[0,2].some(i=>current.frameHashes[i]!==current.middleNativeRGBAHash))
    throw new Error('Developer-selected middle cannot inherit human/full-motion approval');
  return current;
}

export function validateWaveMiddleReference(before,current){
  validateCurrentWave(current);validateCurrentWave(before);
  if(current.middleDevelopmentBasis!=='developer-selected-continuity-improvement'
      ||before.middleDevelopmentBasis!==undefined
      ||['sourceSha256','state','nativeRow','camera','durationsMs','sequence','repeatBeforeIdle'].some(key=>
        JSON.stringify(before[key])!==JSON.stringify(current[key]))
      ||before.frameHashes?.length!==4||current.frameHashes?.length!==4
      ||before.frameHashes[0]!=='D4B92531FFB5559FD99A006816D011601E83C56E2E15F2465FED768C7F0E6789'
      ||before.frameHashes[0]!==before.frameHashes[2]
      ||[1,3].some(i=>before.frameHashes[i]!==current.frameHashes[i]))
    throw new Error('Middle comparison must share exact accepted peak/rest, source and holds');
  before.frameHashes.forEach((_,i)=>candidateCelKey(before.frameHashes,i));
  return before;
}

export function validateWaveAmplitude(study,current,manifest,baseline){
  validateCurrentWave(current);
  if(manifest?.commit!=='2a9688600e17a63253b2a3623fc8cd538c0d7453'
      ||manifest.referenceRole!=='frozen-source-input-not-active-animation'
      ||manifest.referencePurpose!=='isolate-lowered-wave-peak-with-local-cloth-repair'
      ||manifest.file!=='waving.webp'||manifest.contract!=='contract.json'
      ||manifest.fileSha256!=='15FBB171AF825AD5B26CE93F4CEFC9A9A16E3DD9BAC58F751BCCA4F9D8C33692'
      ||manifest.visualApprovalInherited!==false||manifest.installed!==false||manifest.installableFullAtlas!==false
      ||baseline?.state!=='waving'||baseline.nativeRow!==3)
    throw new Error('Invalid frozen old-wave reference');
  if(current.state!=='waving'||current.nativeRow!==3
      ||study.state!=='waving'||study.nativeRow!==3||study.repeatBeforeIdle!==3
      ||study.totalDurationMs!==700||study.actionDurationMs!==2100
      ||study.frameHashes?.length!==4||study.baselineFrameHashes?.length!==4
      ||['sourceSha256','camera','durationsMs','sequence'].some(key=>
        current[key]===undefined||JSON.stringify(study[key])!==JSON.stringify(current[key])
          ||JSON.stringify(baseline[key])!==JSON.stringify(current[key]))
      ||!Number.isFinite(current.camera?.scale)||current.camera.scale<=0
      ||JSON.stringify(study.frameHashes)!==JSON.stringify(current.frameHashes)
      ||JSON.stringify(study.baselineFrameHashes)!==JSON.stringify(baseline.frameHashes)
      ||JSON.stringify(study.unchangedHoldIndices)!==JSON.stringify([0,2,3])
      ||[0,2,3].some(i=>study.frameHashes[i]!==baseline.frameHashes[i])
      ||study.frameHashes[1]===baseline.frameHashes[1]
      ||study.specification?.verticalOffsetSourcePx!==55
      ||study.sameMaterialNeutralPeakRGBAExact!==true||study.canonicalRestRGBAExact!==true
      ||study.clothRepair?.generatedSha256!=='D5AC19778E9C260ACA276F10B05417BB921563808FFE185A18A1B5FE16502113'
      ||study.clothRepair?.handChangedSourcePixels!==0||study.clothRepair?.protectedChangedPixels!==0
      ||study.clothRepair?.handProtectionEstimated!==true
      ||study.clothRepair?.generatedHandNotUsed!==true||study.clothRepair?.generatedCapeNotUsed!==true
      ||study.newClothArtworkGenerated!==true||study.newHandArtworkUsed!==false
      ||study.handScaleChanged!==false||study.handOrientationChanged!==false
      ||study.faceGeometryChanged!==false||study.wholeBodyRotation!==false
      ||study.nativeInterpolation!==false||study.amplitudeDirectionUserApproved!==true
      ||study.directionUserDecision!=='sources/canonical/waving-amplitude-decision-20261010.json'
      ||study.reference!=='sources/reference/waving-amplitude-high'
      ||study.amplitudeVisualApproval!==current.amplitudeVisualApproval
      ||study.adoptionScope!==current.amplitudeApprovalScope||study.userDecision!==current.amplitudeUserDecision
      ||study.currentWavingCelsRGBAExact!==true
      ||study.visualMotionApproval!=='pending'||study.adopted!==true
      ||study.activeAtlasChanged!==true||study.installableFullAtlas!==false||study.installed!==false)
    throw new Error('Lowered-wave source, timing, pixel protection or narrow adoption boundary mismatch');
  study.frameHashes.forEach((_,i)=>candidateCelKey(study.frameHashes,i));
  baseline.frameHashes.forEach((_,i)=>candidateCelKey(baseline.frameHashes,i));
  return study;
}
