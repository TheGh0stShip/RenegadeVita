#requires -Version 5.1
<#
Optional Windows launcher for the canonical Renegade Vita Bash/CMake/VitaSDK
build. It contains no embedded payload and never deploys to a Vita.
#>
[CmdletBinding()]
param(
    [string]$Workspace,
    [string]$CandidateLabel,
    [int]$BuildJobs = 0
)

$ErrorActionPreference = 'Stop'
$ScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
if ([string]::IsNullOrWhiteSpace($Workspace)) {
    $Workspace = $ScriptRoot
}
$Workspace = (Resolve-Path -LiteralPath $Workspace).Path
$BuilderRoot = if ($env:RENEGADE_BUILDER_ROOT) {
    $env:RENEGADE_BUILDER_ROOT
} else {
    Join-Path $env:LOCALAPPDATA 'RenegadeVitaBuilder'
}
$Logs = Join-Path $BuilderRoot 'logs'
$Dist = Join-Path $BuilderRoot 'dist'
$BuildScript = Join-Path $Workspace 'tools\build.sh'

if (-not (Get-Command wsl.exe -ErrorAction SilentlyContinue)) {
    throw 'wsl.exe was not found. WSL2 Ubuntu is required.'
}
if (-not (Test-Path -LiteralPath $BuildScript -PathType Leaf)) {
    throw "Canonical build script is missing: $BuildScript"
}
foreach ($Directory in @($Logs, $Dist)) {
    if (-not (Test-Path -LiteralPath $Directory)) {
        New-Item -ItemType Directory -Force -Path $Directory | Out-Null
    }
}

$Timestamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$ConsoleLog = Join-Path $Logs ($Timestamp + '-wsl-console.log')
if (-not [string]::IsNullOrWhiteSpace($CandidateLabel)) {
    $env:RENEGADE_CANDIDATE_LABEL = $CandidateLabel
}
if ($BuildJobs -gt 0) {
    $env:RENEGADE_BUILD_JOBS = [string]$BuildJobs
}
Write-Host 'Starting canonical WSL Bash/CMake/VitaSDK build.'
Write-Host 'No Vita connection or deployment will be attempted.'
& wsl.exe --cd $Workspace -e bash ./tools/build.sh 2>&1 |
    Tee-Object -FilePath $ConsoleLog
$BuildExitCode = $LASTEXITCODE
if ($BuildExitCode -ne 0) {
    Write-Host ''
    Write-Host 'Build failed. Console tail:' -ForegroundColor Red
    Get-Content -LiteralPath $ConsoleLog -Tail 160
    throw "Renegade Vita build failed with exit code $BuildExitCode."
}

$Vpk = Get-ChildItem -LiteralPath $Dist -Filter 'RenegadeVita-A*.vpk' |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1
Write-Host ''
Write-Host 'RENEGADE VITA CANONICAL BUILD COMPLETE' -ForegroundColor Green
if ($Vpk) {
    Write-Host "Latest VPK for manual installation: $($Vpk.FullName)"
}
Write-Host "Artifacts: $Dist"
Write-Host "Complete console log: $ConsoleLog"
Write-Host 'No automatic Vita deployment was performed.'
