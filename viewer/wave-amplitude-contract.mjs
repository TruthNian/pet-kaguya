import {candidateCelKey} from './candidate-clock.mjs';

export function validateCurrentWave(current){
  if(current.state!=='waving'||current.nativeRow!==3||current.repeatBeforeIdle!==3
      ||current.amplitudeVisualApproval!=='approved-as-development-basis'
      ||current.amplitudeApprovalScope!=='waving-lower-amplitude-development-basis-only'
      ||current.amplitudeUserDecision!=='sources/canonical/waving-amplitude-adoption-20261010.json'
      ||current.handLoweringSourcePx!==55
      ||JSON.stringify(current.unchangedOriginalHoldIndices)!==JSON.stringify([0,2,3])
      ||current.frameHashes?.[1]!=='61C09D34D0A702F5AA5B472FAE38D8945BED2836E7EA61A55E63C0B1F65EF3D6'
      ||current.visualMotionApproval!=='pending'||current.installed!==false||current.installableFullAtlas!==false)
    throw new Error('Wave development-basis approval/source boundary mismatch');
  return current;
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
