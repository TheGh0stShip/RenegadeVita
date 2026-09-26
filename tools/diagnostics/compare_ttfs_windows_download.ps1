param(
    [Parameter(Mandatory=$true)][string]$ToolsDirectory,
    [Parameter(Mandatory=$true)][string]$WorkDir,
    [Parameter(Mandatory=$true)][ValidatePattern('^[0-9a-f]{8}$')][string]$PackageId,
    [Parameter(Mandatory=$true)][string]$Repository
)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$uri = [Uri]$Repository
if (!$uri.IsAbsoluteUri -or $uri.Scheme -ne 'https' -or $uri.UserInfo -or $uri.Query -or $uri.Fragment) {
    throw 'Expected an unauthenticated HTTPS repository URL.'
}
if (Test-Path -LiteralPath $WorkDir) { throw 'Use a fresh evidence directory.' }
$pins = @{
    'PackageEditor.exe' = '6c9f93b11d598c0ac772d0ef9a1bf450758a21e0c22544152574144efb23f492'
    'MemoryManager.dll' = 'b60a2b3f6a07d729ee5c2902cb9a6bedaf55eedb13f8514bac0ad6f5d51dd0c2'
}
foreach ($name in $pins.Keys) {
    if ((Get-FileHash -LiteralPath (Join-Path $ToolsDirectory $name) -Algorithm SHA256).Hash -ne $pins[$name]) {
        throw "Reference hash mismatch: $name"
    }
}
New-Item -ItemType Directory -Path $WorkDir | Out-Null
foreach ($name in $pins.Keys) {
    Copy-Item -LiteralPath (Join-Path $ToolsDirectory $name) -Destination (Join-Path $WorkDir $name)
}
$saved = @{}
foreach ($name in @('APPDATA', 'LOCALAPPDATA', 'USERPROFILE')) {
    $saved[$name] = [Environment]::GetEnvironmentVariable($name, 'Process')
    [Environment]::SetEnvironmentVariable($name, $WorkDir, 'Process')
}
$process = $null
try {
    $process = Start-Process -FilePath (Join-Path $WorkDir 'PackageEditor.exe') `
        -ArgumentList "download $PackageId $Repository" -WorkingDirectory $WorkDir `
        -RedirectStandardOutput (Join-Path $WorkDir 'stdout.txt') `
        -RedirectStandardError (Join-Path $WorkDir 'stderr.txt') -PassThru
    $handle = $process.Handle
    $finished = $process.WaitForExit(60000)
    if (!$finished) { $process.Kill(); $process.WaitForExit() }
    $manifest = Join-Path $WorkDir "Renegade\FDS\ttfs\packages\$PackageId.tpi"
    $record = @{
        evidence = 'official_windows_ttfs_downloader'; package = $PackageId;
        repository = $Repository; finished = $finished; exit_code = $process.ExitCode;
        manifest_present = (Test-Path -LiteralPath $manifest); native_vita_verified = $false
        downloader_reported_success = ((Get-Content -LiteralPath (Join-Path $WorkDir 'stdout.txt') -Raw) -match 'successfully downloaded and installed')
    }
    if ($record.manifest_present) {
        $record.manifest_sha256 = (Get-FileHash -LiteralPath $manifest -Algorithm SHA256).Hash
    }
    $record | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $WorkDir 'result.json')
    $record | ConvertTo-Json
} finally {
    if ($null -ne $process -and !$process.HasExited) { $process.Kill(); $process.WaitForExit() }
    foreach ($name in $saved.Keys) { [Environment]::SetEnvironmentVariable($name, $saved[$name], 'Process') }
}
