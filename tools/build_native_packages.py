"""Frozen local-v2 file packages. No artwork rebuild, installation or release approval."""
import argparse
import hashlib
import io
import json
import subprocess
import zipfile

from PIL import Image
from canonical import ROOT

OUT=ROOT/'deliverables'
CURRENT='0ac132cea9de5db54721d6e617e3f9c7de3ae76d'
BASELINE='97ec2aba368d91faf5a127127a04105f58231247'
CURRENT_SHA='5A1A93C1A709F98E6F3359F5E6A3241ABFECE2850695BC1E05590C895F9DC94B'
CURRENT_RGBA='ED21FAEFBB0F986B1F3E6667EF7452817186053C048E569958F1E16F5FE3124F'
LATEST='f5eb77fb5576d062916e19e2296292890ea4ab57'
LATEST_SHA='FEE52726F71E85BC0AAD5745287A18C0731F2567F4DD3CE8E22ACE324BD6233B'
LATEST_RGBA='7AC9394B6AB37C7D0C3D74B0E93AC1180233D5E196076D5D46DBF1D322C06A8E'
BASELINE_SHA='71F7E36AD459D99C9DE1AC6033A968CDF4C125EB742FFD5FF19B8E81BBA56EF7'


def sha(data):
    return hashlib.sha256(data).hexdigest().upper()


def blob(commit,path):
    # Git blobs keep the frozen source bytes independent of checkout CRLF.
    return subprocess.run(['git','show',f'{commit}:{path}'],cwd=ROOT,
        check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).stdout


def encoded(value):
    return (json.dumps(value,ensure_ascii=False,indent=2)+'\n').encode('utf-8')


def native_config(payload):
    config=json.loads(payload)
    if (set(config)!={'id','displayName','description','spriteVersionNumber','spritesheetPath','kind'}
            or config['id']!='kaguya' or config['spriteVersionNumber']!=2
            or config['spritesheetPath']!='spritesheet.webp' or config['kind']!='person'):
        raise ValueError('Expected exact local v2 config layout, not cloud Work Pets metadata')
    return config


def payloads(candidate, *, latest=False):
    if latest and not candidate:raise ValueError('Latest is a development snapshot, not a replacement baseline')
    commit=LATEST if latest else CURRENT if candidate else BASELINE
    folder='candidates/phase5/global' if candidate else 'baseline/phase2'
    atlas=blob(commit,f'{folder}/spritesheet.webp')
    if sha(atlas)!=(LATEST_SHA if latest else CURRENT_SHA if candidate else BASELINE_SHA):
        raise ValueError('Frozen source atlas bytes changed')
    with Image.open(io.BytesIO(atlas)) as opened:
        image=opened.convert('RGBA')
        if image.size!=(1536,2288):raise ValueError('Local v2 atlas geometry changed')
        rgba=sha(image.tobytes())
    if candidate and rgba!=(LATEST_RGBA if latest else CURRENT_RGBA):raise ValueError('Frozen current pixels changed')
    config_bytes=blob(BASELINE,'baseline/phase2/pet.json')
    config=native_config(config_bytes)
    if candidate:
        source=json.loads(blob(commit,f'{folder}/build.json'))
        if (source['atlasRGBAHash']!=rgba or source['visualAcceptance']!='pending'
                or source['hostIntegrationVerified'] or source['installed']
                or source['allStateTransitionsAccepted'] or source['directionCount']!=16
                or len(source['actionRows'])!=9):
            raise ValueError('Do not turn complete cell coverage into release approval')
        config.update(displayName='Kaguya（开发候选）',description=
            'Locked canonical-v3, gentle local-v2 development candidate; full visual and native-host acceptance pending.')
        config_bytes=encoded(config)
    native_config(config_bytes)
    manifest=dict(packageRole='development-candidate' if candidate else 'historical-baseline-archive',
        sourceCommit=commit,sourceURL=f'https://github.com/TruthNian/pet-kaguya/tree/{commit}',
        localV2FileLayoutChecked=True,cloudWorkPetCompatibleClaimed=False,
        atlasSize=[1536,2288],cellSize=[192,208],decodedRGBABytes=len(image.tobytes()),
        decodedRGBAHash=rgba,atlasReencoded=False,artworkRebuilt=False,
        visualAcceptance='pending' if candidate else 'historical-usable-baseline-not-new-art-recommendation',
        approvedForInstallation=False,requiresExplicitUserDecisionBeforeInstallation=True,
        nativeHostLoadingVerified=False,installedFilesWritten=False,
        currentInstalledBackup=False,applicationModificationRequired=False,
        fpsImprovementClaimed=False,resolutionImprovementClaimed=False,
        files={name:dict(sha256=sha(data),bytes=len(data)) for name,data in
            [('pet.json',config_bytes),('spritesheet.webp',atlas)]})
    if candidate:
        manifest.update(motherSHA256=source['sourceSha256'],actionStates=source['states'],lookDirections=16,
            nativeHoldCounts=[row['frameCount'] for row in source['actionRows']],
            humanApprovedDevelopmentBases=['frontal restrained steps','failed mouth line','4px hop',
                'lowered waving peak','original-eye texture flow'],
            developerSelectedOnly=['waving turning-palm middle','review relaxed overlapping hands'],
            remainingIssues=['hand/cuff and sleeve aesthetics','small-size expression',
                'discrete state cuts and held-hand entry/exit','complete visual acceptance',
                'native-host loading and real performance evidence'])
        if latest:
            failed=json.loads(blob(commit,'candidates/phase5/failed/build.json'))
            if (failed.get('failedBodyDevelopmentBasis')!='developer-selected-calm-body-hold'
                    or failed.get('bodyMotionUserApproval')!='pending'
                    or failed.get('bodyMotionUserApprovalClaimed') is not False
                    or failed.get('newArtworkGeneratedThisIteration') is not False
                    or failed.get('mouthLineVisualApproval')!='approved-as-development-basis'
                    or failed.get('nativeAlphaPreservedExactly') is not False
                    or len(failed['keyframes'])!=8 or any(p['bodyY']!=0 for p in failed['keyframes'])):
                raise ValueError('Latest failed snapshot must not inherit human body approval or old alpha claims')
            manifest['developerSelectedOnly'].append('failed calm body hold')
    readme=('Pet Kaguya · '+('开发候选资源包' if candidate else '原始 Phase 2 历史基准包')+'\n\n'
        '包中含 pet.json 和 spritesheet.webp，符合本地 v2 文件布局；并非 ChatGPT 云端宠物格式。\n'
        '未执行安装，也未验证实际宿主加载。本包不是已获批准的正式发布。\n'
        '不要直接覆盖已安装的 kaguya 目录；安装需另行明确决定，并先保存当前实际安装副本。\n'
        'manifest.json 保存冻结来源、两文件哈希、权限和验收边界；本包不含安装脚本。\n\n'
        +('这是现用开发图集的精确副本，没有重采样或重编码。脸型锁定 v3。\n'
          +('招手中间格、相叠手、failed身体保持仅为开发者选择，不冒称用户批准；完整造型/动作仍待验收。\n'
           if latest else '招手中间格、相叠手仅为开发者选择，不冒称用户批准；完整造型/动作仍待验收。\n')
          +'固定分辨率、持帧、状态优先级未改变，不承诺高帧率或自然进入/退出。\n'
          if candidate else
          '这是冻结 Git 基准的精确两文件存档，不是当前已安装版本的备份，也不是当前推荐形象。\n'
          '禁止将其当作新母版，或自动回退到用户已否决的旧形象。\n'))
    return {'pet.json':config_bytes,'spritesheet.webp':atlas,
        'manifest.json':encoded(manifest),'README.txt':readme.encode('utf-8')},manifest


def archive(prefix,files):
    stream=io.BytesIO()
    with zipfile.ZipFile(stream,'w',compression=zipfile.ZIP_STORED) as bundle:
        for name,data in sorted(files.items()):
            info=zipfile.ZipInfo(f'{prefix}/{name}',date_time=(1980,1,1,0,0,0))
            info.create_system=3;info.external_attr=0o100644<<16
            bundle.writestr(info,data)
    result=stream.getvalue()
    with zipfile.ZipFile(io.BytesIO(result)) as bundle:
        if bundle.testzip() is not None or bundle.namelist()!=[f'{prefix}/{name}' for name in sorted(files)]:
            raise ValueError('Package CRC or file layout mismatch')
        for name,data in files.items():
            if bundle.read(f'{prefix}/{name}')!=data:raise ValueError('Packaged source bytes changed')
    return result


def save_or_verify(path,data,verify):
    if path.exists():
        if path.read_bytes()!=data:raise ValueError(f'Refusing to overwrite a different frozen package: {path.name}')
    elif verify:raise ValueError(f'Missing package: {path.name}')
    else:path.write_bytes(data)


def save_index(path,data,previous,verify):
    # ZIPs are immutable. Only advance the index from the exact known two-pack
    # index to the known three-pack index; never discard unexpected entries.
    existing=path.read_bytes().replace(b'\r\n',b'\n') if path.exists() else None
    if verify:
        if existing!=data:raise ValueError('Package index does not match the three frozen sources')
    elif existing==data:return
    elif existing not in (None,previous):raise ValueError('Refusing to replace an unexpected package index')
    else:path.write_bytes(data)


def main(verify=False):
    if OUT.resolve().parent!=ROOT.resolve():raise ValueError('Deliverables directory redirects outside repository')
    if not verify:OUT.mkdir(exist_ok=True)
    entries=[]
    for candidate,prefix in [(True,'kaguya-candidate-0ac132c'),(False,'kaguya-baseline-phase2')]:
        files,manifest=payloads(candidate);data=archive(prefix,files)
        save_or_verify(OUT/f'{prefix}.zip',data,verify)
        entries.append(dict(file=f'{prefix}.zip',bytes=len(data),sha256=sha(data),
            sourceCommit=manifest['sourceCommit'],packageRole=manifest['packageRole'],
            atlasSHA256=manifest['files']['spritesheet.webp']['sha256'],
            petConfigSHA256=manifest['files']['pet.json']['sha256']))
    index=dict(packages=entries,installationPerformed=False,artworkRebuilds=0,
        releaseApprovalClaimed=False,archiveRoundTripByteExact=True)
    previous=encoded(index)
    prefix='kaguya-candidate-f5eb77f'
    files,manifest=payloads(True,latest=True);data=archive(prefix,files)
    save_or_verify(OUT/f'{prefix}.zip',data,verify)
    entries.append(dict(file=f'{prefix}.zip',bytes=len(data),sha256=sha(data),
        sourceCommit=manifest['sourceCommit'],packageRole=manifest['packageRole'],
        atlasSHA256=manifest['files']['spritesheet.webp']['sha256'],
        petConfigSHA256=manifest['files']['pet.json']['sha256']))
    index['currentDevelopmentPackage']=f'{prefix}.zip'
    save_index(OUT/'index.json',encoded(index),previous,verify)
    print(json.dumps(index,ensure_ascii=False,indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--verify',action='store_true',help='Read-only package/source comparison; no output writes')
    main(parser.parse_args().verify)
