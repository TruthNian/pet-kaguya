$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
$testRoot = Join-Path $repoRoot ('work\install-test-' + [Guid]::NewGuid().ToString('N'))
$petDir = Join-Path $testRoot 'pet'
$backups = Join-Path $testRoot 'backups'
New-Item -ItemType Directory -Path $petDir | Out-Null
Copy-Item -LiteralPath (Join-Path $repoRoot 'baseline\phase2\spritesheet.webp') -Destination $petDir
Copy-Item -LiteralPath (Join-Path $repoRoot 'baseline\phase2\pet.json') -Destination $petDir
$atlas = Join-Path $petDir 'spritesheet.webp'
$baselineHash = (Get-FileHash -LiteralPath $atlas).Hash
$candidateHash = (Get-FileHash -LiteralPath (Join-Path $repoRoot 'pet\spritesheet.webp')).Hash
# 0. Default install is denied even with a valid historical pet; no mutation.
$rejected = $false
try { & (Join-Path $PSScriptRoot 'install.ps1') -PetDirectory $petDir -BackupRoot $backups -Confirm:$false } catch { $rejected = $true }
if (-not $rejected -or (Get-FileHash -LiteralPath $atlas).Hash -ne $baselineHash -or (Test-Path -LiteralPath $backups)) { throw 'Unapproved default install was not safely denied.' }
# Historical opt-in without explicit sandbox paths must also fail before resolution/write.
$rejected = $false
try { & (Join-Path $PSScriptRoot 'install.ps1') -HistoricalRegression -WhatIf } catch { $rejected = $true }
if (-not $rejected) { throw 'Historical opt-in accepted default real installation paths.' }
# A non-work target is denied before attempting to read or write that path.
$rejected = $false
try { & (Join-Path $PSScriptRoot 'install.ps1') -HistoricalRegression -PetDirectory $repoRoot -BackupRoot $backups -WhatIf } catch { $rejected = $true }
if (-not $rejected) { throw 'Historical regression escaped the isolated work directory.' }
# 1. WhatIf must not mutate files or create a backup.
& (Join-Path $PSScriptRoot 'install.ps1') -HistoricalRegression -PetDirectory $petDir -BackupRoot $backups -WhatIf
if ((Get-FileHash -LiteralPath $atlas).Hash -ne $baselineHash -or (Test-Path -LiteralPath $backups)) { throw 'WhatIf mutated files.' }
# 2. Backup and install only in isolated test pet; backup is byte exact.
& (Join-Path $PSScriptRoot 'install.ps1') -HistoricalRegression -PetDirectory $petDir -BackupRoot $backups -Confirm:$false
if ((Get-FileHash -LiteralPath $atlas).Hash -ne $candidateHash) { throw 'Install failed.' }
$backupDirs = @(Get-ChildItem -LiteralPath $backups -Directory)
if ($backupDirs.Count -ne 1) { throw 'Unexpected backup count.' }
if ((Get-FileHash -LiteralPath (Join-Path $backupDirs[0].FullName 'spritesheet.webp')).Hash -ne $baselineHash) { throw 'Backup differs from baseline.' }
# 3. Idempotent re-install is read-only.
& (Join-Path $PSScriptRoot 'install.ps1') -HistoricalRegression -PetDirectory $petDir -BackupRoot $backups -Confirm:$false
if (@(Get-ChildItem -LiteralPath $backups -Directory).Count -ne 1) { throw 'Idempotent install created unnecessary backup.' }
# 4. Wrong expected hash must reject restore, before any write.
$rejected = $false
try { & (Join-Path $PSScriptRoot 'install.ps1') -PetDirectory $petDir -BackupRoot $backups -Baseline -ExpectedCurrentHash 'INVALID' -Confirm:$false } catch { $rejected = $true }
if (-not $rejected -or (Get-FileHash -LiteralPath $atlas).Hash -ne $candidateHash) { throw 'Stale-hash guard failed.' }
# 5. Explicit restore archives the candidate and restores exact baseline.
& (Join-Path $PSScriptRoot 'install.ps1') -PetDirectory $petDir -BackupRoot $backups -Baseline -ExpectedCurrentHash $candidateHash -Confirm:$false
if ((Get-FileHash -LiteralPath $atlas).Hash -ne $baselineHash) { throw 'Restore failed.' }
Write-Output 'PASS: default install denial, isolated historical opt-in, WhatIf, byte-exact backup/install, idempotence, stale-hash rejection, exact restore.'
Write-Output "Test artifacts retained for inspection: $testRoot"
