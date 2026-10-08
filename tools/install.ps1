[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [string]$PetDirectory = (Join-Path $env:USERPROFILE '.codex\pets\kaguya'),
    [string]$ExpectedCurrentHash = '71F7E36AD459D99C9DE1AC6033A968CDF4C125EB742FFD5FF19B8E81BBA56EF7',
    [string]$BackupRoot = (Join-Path $env:USERPROFILE '.codex\backups\pets'),
    [switch]$Baseline
)
$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
$sourceDir = if ($Baseline) { Join-Path $repoRoot 'baseline\phase2' } else { Join-Path $repoRoot 'pet' }
$atlasSource = Join-Path $sourceDir 'spritesheet.webp'
$configSource = Join-Path $sourceDir 'pet.json'
$targetDir = (Resolve-Path -LiteralPath $PetDirectory).Path
$targetAtlas = Join-Path $targetDir 'spritesheet.webp'
$targetConfig = Join-Path $targetDir 'pet.json'
if ((Get-Item -LiteralPath $targetDir).Attributes -band [IO.FileAttributes]::ReparsePoint) {
    throw 'Refusing to overwrite a redirected pet directory.'
}
$config = Get-Content -Raw -LiteralPath $targetConfig | ConvertFrom-Json
if ($config.id -ne 'kaguya' -or $config.spriteVersionNumber -ne 2 -or $config.spritesheetPath -ne 'spritesheet.webp') {
    throw 'Destination is not the expected local Kaguya v2 installation.'
}
$currentHash = (Get-FileHash -LiteralPath $targetAtlas -Algorithm SHA256).Hash
$sourceHash = (Get-FileHash -LiteralPath $atlasSource -Algorithm SHA256).Hash
if ($currentHash -eq $sourceHash) {
    Write-Output 'Selected atlas is already installed. No write or backup needed.'
    return
}
if ($currentHash -ne $ExpectedCurrentHash) {
    throw "Installed atlas changed. Inspect it and explicitly supply its hash before replacing. Found: $currentHash"
}
if (-not $Baseline) {
    $build = Get-Content -Raw -LiteralPath (Join-Path $sourceDir 'build.json') | ConvertFrom-Json
    if ($sourceHash -ne $build.outputSha256) { throw 'Candidate hash differs from build manifest.' }
}
if (-not $PSCmdlet.ShouldProcess($targetDir, 'Back up and replace ONLY Kaguya atlas/config; do not change app selection or application binaries')) { return }
$suffix = (Get-Date -Format 'yyyyMMdd-HHmmss') + '-' + [Guid]::NewGuid().ToString('N').Substring(0,8)
$backupDir = Join-Path $BackupRoot ('kaguya-before-gentle-' + $suffix)
New-Item -ItemType Directory -Path $backupDir | Out-Null
Copy-Item -LiteralPath $targetAtlas -Destination (Join-Path $backupDir 'spritesheet.webp')
Copy-Item -LiteralPath $targetConfig -Destination (Join-Path $backupDir 'pet.json')
$tempAtlas = Join-Path $targetDir ('spritesheet-' + [Guid]::NewGuid().ToString('N') + '.webp')
$tempConfig = Join-Path $targetDir ('pet-' + [Guid]::NewGuid().ToString('N') + '.json')
try {
    Copy-Item -LiteralPath $atlasSource -Destination $tempAtlas
    Copy-Item -LiteralPath $configSource -Destination $tempConfig
    # PowerShell coerces a null string argument to an empty path on some .NET
    # overloads. Use explicit backup filenames; the existing byte-exact copies
    # are safely refreshed by Replace with the previous destination contents.
    [IO.File]::Replace($tempAtlas, $targetAtlas, (Join-Path $backupDir 'spritesheet.webp'))
    [IO.File]::Replace($tempConfig, $targetConfig, (Join-Path $backupDir 'pet.json'))
    if ((Get-FileHash -LiteralPath $targetAtlas).Hash -ne $sourceHash) { throw 'Installed hash mismatch.' }
} catch {
    Copy-Item -LiteralPath (Join-Path $backupDir 'spritesheet.webp') -Destination $targetAtlas
    Copy-Item -LiteralPath (Join-Path $backupDir 'pet.json') -Destination $targetConfig
    throw
}
Write-Output "Installed atlas SHA-256: $sourceHash"
Write-Output "Recoverable backup: $backupDir"
Write-Output 'Local files changed. The running host may require reselection/reload; live activation is not confirmed.'
