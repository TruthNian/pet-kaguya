[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [string]$PetDirectory = (Join-Path $env:USERPROFILE '.codex\pets\kaguya'),
    [string]$BackupRoot = (Join-Path $env:USERPROFILE '.codex\backups\pets'),
    [string]$ExpectedCurrentHash = '238C9ECEC64AB39B6F9CE04B9795E107996C1F97E06BA20B5E5A723EC940E3F1',
    [string]$ExpectedConfigHash = '6E8B039E26B4936182569C20EA657527FB6815F752D6032FA642EBAC8E966DDF'
)
$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
function Assert-NoRedirect([string]$Path) {
    $ancestor = [IO.Path]::GetFullPath($Path)
    while ($ancestor) {
        if ((Test-Path -LiteralPath $ancestor) -and
                ((Get-Item -LiteralPath $ancestor).Attributes -band [IO.FileAttributes]::ReparsePoint)) {
            throw "Refusing redirected path: $ancestor"
        }
        $parent = Split-Path -Parent $ancestor
        if ($parent -eq $ancestor) { break }
        $ancestor = $parent
    }
}
$decisionPath = Join-Path $repoRoot 'sources\canonical\whole-review-acceptance-20261011.json'
$decision = Get-Content -LiteralPath $decisionPath -Raw | ConvertFrom-Json
if ($decision.scope -ne 'current-whole-review-visual-acceptance' -or
        $decision.visualAcceptance -ne 'accepted' -or $decision.installationAuthorized -ne $true -or
        $decision.applicationChangeAuthorized -ne $false -or $decision.independentPetHostAuthorized -ne $false -or
        $decision.atlasSHA256 -ne 'FEE52726F71E85BC0AAD5745287A18C0731F2567F4DD3CE8E22ACE324BD6233B') {
    throw 'Exact visual and installation authority missing.'
}
$targetDir = [IO.Path]::GetFullPath($PetDirectory).TrimEnd([char[]]'\/')
$backupParent = [IO.Path]::GetFullPath($BackupRoot).TrimEnd([char[]]'\/')
if (-not (Test-Path -LiteralPath $targetDir -PathType Container)) { throw 'Existing actual pet directory required.' }
if ($backupParent -eq $targetDir -or $backupParent.StartsWith($targetDir + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) {
    throw 'Backup must be outside the installation.'
}
Assert-NoRedirect $targetDir
Assert-NoRedirect $backupParent
$sourceAtlas = Join-Path $repoRoot 'candidates\phase5\global\spritesheet.webp'
Assert-NoRedirect $sourceAtlas
$targetAtlas = Join-Path $targetDir 'spritesheet.webp'
$targetConfig = Join-Path $targetDir 'pet.json'
Assert-NoRedirect $targetAtlas
Assert-NoRedirect $targetConfig
$config = Get-Content -LiteralPath $targetConfig -Raw | ConvertFrom-Json
if ($config.id -ne 'kaguya' -or $config.spriteVersionNumber -ne 2 -or
        $config.spritesheetPath -ne 'spritesheet.webp' -or $config.kind -ne 'person') {
    throw 'Destination is not the expected local Kaguya v2 pet.'
}
$sourceHash = (Get-FileHash -LiteralPath $sourceAtlas -Algorithm SHA256).Hash
$currentHash = (Get-FileHash -LiteralPath $targetAtlas -Algorithm SHA256).Hash
$configHash = (Get-FileHash -LiteralPath $targetConfig -Algorithm SHA256).Hash
if ($sourceHash -ne $decision.atlasSHA256) { throw 'Source differs from exact reviewed atlas.' }
if ($configHash -ne $ExpectedConfigHash) { throw 'Installed config changed; inspect before retrying.' }
if ($currentHash -eq $sourceHash) { Write-Output 'Reviewed atlas already installed; no writes.'; return }
if ($currentHash -ne $ExpectedCurrentHash) { throw 'Installed atlas changed; inspect before retrying.' }
if (-not $PSCmdlet.ShouldProcess($targetDir, 'Back up BOTH actual pet files, atomically replace reviewed atlas; preserve config and application')) { return }
$suffix = (Get-Date -Format 'yyyyMMdd-HHmmss') + '-' + [Guid]::NewGuid().ToString('N').Substring(0,8)
$backupDir = Join-Path $backupParent ('kaguya-before-reviewed-v3-' + $suffix)
New-Item -ItemType Directory -Path $backupDir -Force | Out-Null
$backupAtlas = Join-Path $backupDir 'spritesheet.webp'
$backupConfig = Join-Path $backupDir 'pet.json'
Copy-Item -LiteralPath $targetAtlas -Destination $backupAtlas
Copy-Item -LiteralPath $targetConfig -Destination $backupConfig
if ((Get-FileHash -LiteralPath $backupAtlas).Hash -ne $currentHash -or
        (Get-FileHash -LiteralPath $backupConfig).Hash -ne $configHash) {
    throw 'Backup byte verification failed; installed files were not touched.'
}
$temporaryAtlas = Join-Path $targetDir ('spritesheet-reviewed-' + [Guid]::NewGuid().ToString('N') + '.webp')
$replaced = $false
try {
    Copy-Item -LiteralPath $sourceAtlas -Destination $temporaryAtlas
    if ((Get-FileHash -LiteralPath $temporaryAtlas).Hash -ne $sourceHash -or
            (Get-FileHash -LiteralPath $targetAtlas).Hash -ne $currentHash -or
            (Get-FileHash -LiteralPath $targetConfig).Hash -ne $configHash) {
        throw 'Source or target changed while preparing; refusing replacement.'
    }
    [IO.File]::Replace($temporaryAtlas, $targetAtlas, $backupAtlas)
    $replaced = $true
    if ((Get-FileHash -LiteralPath $targetAtlas).Hash -ne $sourceHash -or
            (Get-FileHash -LiteralPath $targetConfig).Hash -ne $configHash) {
        throw 'Installed file verification failed.'
    }
} catch {
    if ($replaced) { Copy-Item -LiteralPath $backupAtlas -Destination $targetAtlas }
    throw
} finally {
    if (Test-Path -LiteralPath $temporaryAtlas) { Remove-Item -LiteralPath $temporaryAtlas }
}
$receipt = [ordered]@{
    installedAt = (Get-Date).ToString('o'); backupDirectory = $backupDir
    previousAtlasSHA256 = $currentHash; installedAtlasSHA256 = $sourceHash
    configSHA256 = $configHash; configUnchanged = $true; backupVerified = $true
    applicationModified = $false; nativeHostLoadingVerified = $false
}
# Private generated installation receipt remains with the actual recoverable backup.
$receipt | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $backupDir 'installation.json') -Encoding utf8
Write-Output ($receipt | ConvertTo-Json)
Write-Output 'Files installed; running host may require reselection/reload. Live activation is not claimed.'
