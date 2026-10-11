"""Package the exact visually accepted snapshot, without rebuilding or installing."""
import argparse
import io
import json

from PIL import Image
from canonical import ROOT, ACCEPTED_SHA
from build_native_packages import LATEST, LATEST_SHA, LATEST_RGBA, blob, encoded, sha, archive, save_or_verify, native_config

DECISION = 'sources/canonical/whole-review-acceptance-20261011.json'
PREFIX = 'kaguya-v3-reviewed-20261011'


def reviewed_payloads():
    decision = json.loads((ROOT / DECISION).read_text(encoding='utf-8'))
    if (decision['scope'] != 'current-whole-review-visual-acceptance'
            or decision['visualAcceptance'] != 'accepted'
            or decision['sourceCommit'] != LATEST or decision['motherSHA256'] != ACCEPTED_SHA
            or decision['atlasSHA256'] != LATEST_SHA or decision['atlasRGBAHash'] != LATEST_RGBA
            or decision['installationAuthorized'] is not True
            or decision['applicationChangeAuthorized'] or decision['independentPetHostAuthorized']
            or decision['nativeHostLoadingVerified'] or decision['allArbitraryStateTransitionsAccepted']
            or decision['performanceImprovementClaimed']):
        raise ValueError('Missing exact visual/installation authority or changed scope')
    atlas = blob(LATEST, 'candidates/phase5/global/spritesheet.webp')
    if sha(atlas) != LATEST_SHA or (ROOT / 'candidates/phase5/global/spritesheet.webp').read_bytes() != atlas:
        raise ValueError('Current atlas is not the reviewed frozen snapshot')
    with Image.open(io.BytesIO(atlas)) as opened:
        pixels = opened.convert('RGBA')
        if pixels.size != (1536, 2288) or sha(pixels.tobytes()) != LATEST_RGBA:
            raise ValueError('Reviewed geometry/pixels changed')
    config = dict(id='kaguya', displayName='Kaguya',
        description='A gentle moon-rabbit Kaguya with restrained breathing, ear and hair motion.',
        spriteVersionNumber=2, spritesheetPath='spritesheet.webp', kind='person')
    config_bytes = encoded(config)
    native_config(config_bytes)
    manifest = dict(packageRole='visually-accepted-native-loading-unverified',
        sourceCommit=LATEST, acceptanceReceipt=DECISION, visualAcceptance='accepted-in-whole-review',
        installationAuthorized=True, nativeHostLoadingVerified=False,
        applicationModified=False, independentPetHostCreated=False,
        allArbitraryStateTransitionsAccepted=False, performanceImprovementClaimed=False,
        atlasSize=[1536, 2288], cellSize=[192, 208], actionStates=9, lookDirections=16,
        decodedRGBABytes=14057472, atlasRGBAHash=LATEST_RGBA,
        artworkRebuilt=False, atlasReencoded=False,
        files={name:dict(sha256=sha(data), bytes=len(data)) for name, data in
            [('pet.json', config_bytes), ('spritesheet.webp', atlas)]},
        remainingLimits=decision['limitations'])
    readme = ('Pet Kaguya · v3 整套观感认可版\n\n'
        '用户已认可完整观看页中的当前九动作/十六视线，并明确允许备份后安装。\n'
        '图集与冻结 f5eb77f 完全一致，未重画、重采样或重编码。\n'
        '认可不等于真实宿主加载、任意切换或性能提升已验证；不修改应用。\n'
        '固定持帧/状态硬切/保持手势入退场及小尺寸提示仍有限制。\n'
        'approval.json 记录本次共识，manifest.json 记录资源哈希与边界。\n'
        '安装前完整备份实际 pet.json 和图集；旧候选包不被覆盖。\n')
    return {'pet.json': config_bytes, 'spritesheet.webp': atlas,
        'manifest.json': encoded(manifest), 'approval.json': encoded(decision),
        'README.txt': readme.encode('utf-8')}, manifest


def main(verify=False):
    files, manifest = reviewed_payloads()
    data = archive(PREFIX, files)
    out = ROOT / 'deliverables'
    if out.resolve().parent != ROOT.resolve():
        raise ValueError('Deliverables redirects outside repository')
    if not verify:
        out.mkdir(exist_ok=True)
    save_or_verify(out / f'{PREFIX}.zip', data, verify)
    index = dict(currentPackage=f'{PREFIX}.zip', bytes=len(data), sha256=sha(data),
        sourceCommit=LATEST, packageRole=manifest['packageRole'], visualAcceptance=manifest['visualAcceptance'],
        installationAuthorized=True, nativeHostLoadingVerified=False,
        atlasSHA256=LATEST_SHA, atlasRGBAHash=LATEST_RGBA, acceptanceReceipt=DECISION,
        historicalPackageIndex='deliverables/index.json')
    previous_index = encoded(index)
    deployment_path = ROOT / 'docs/DEPLOYMENT-20261011.json'
    if deployment_path.exists():
        deployment = json.loads(deployment_path.read_text(encoding='utf-8'))
        if (deployment['reviewedAtlasSHA256'] != LATEST_SHA
                or deployment['reviewedAtlasRGBAHash'] != LATEST_RGBA
                or deployment['cloudUpdate']['storedDecodedPixelsExactToReviewedAtlas'] is not True
                or deployment['activation']['actualAppLoadingUserAnswer'] != '已显示新版，加载正常'):
            raise ValueError('Deployment readback does not match reviewed snapshot')
        index.update(nativeHostLoadingVerified=True,
            nativeHostLoadingEvidence='explicit-user-confirmation',
            localFilesInstalled=True, originalCloudPetUpdated=True,
            originalCloudPetActive=True, deploymentReceipt='docs/DEPLOYMENT-20261011.json')
    path = out / 'current.json'
    existing = path.read_bytes().replace(b'\r\n', b'\n') if path.exists() else None
    if existing != encoded(index):
        if verify:
            raise ValueError('Current delivery index does not match recorded deployment')
        if existing not in (None, previous_index):
            raise ValueError('Refusing to replace an unexpected current delivery index')
        path.write_bytes(encoded(index))
    print(json.dumps(index, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--verify', action='store_true')
    main(parser.parse_args().verify)
