param([Parameter(Mandatory=$true)][string]$WorkDir)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

# Only known asset-free inputs and pinned official tools may enter this oracle.
$pins = @{
    'PackageEditor.exe' = '6c9f93b11d598c0ac772d0ef9a1bf450758a21e0c22544152574144efb23f492'
    'MemoryManager.dll' = 'b60a2b3f6a07d729ee5c2902cb9a6bedaf55eedb13f8514bac0ad6f5d51dd0c2'
    'vita_fixture.mix' = '4ffcb05e87b7d180fb89b9888e19a12c434f999c2377d390dcadb18ac6707e39'
    'vita_edges.mix' = '554c574cc19a8ae06ce6106f1d4cf7256b27ee5bb4bf46043c571265cfd16931'
}
$WorkDir = (Resolve-Path -LiteralPath $WorkDir).Path
foreach ($name in $pins.Keys) {
    $hash = (Get-FileHash -LiteralPath (Join-Path $WorkDir $name) -Algorithm SHA256).Hash
    if ($hash -ne $pins[$name]) { throw "Fixture/tool hash mismatch: $name" }
}
if (Test-Path -LiteralPath (Join-Path $WorkDir 'Renegade')) {
    throw 'Use a fresh fixture directory; existing evidence will not be overwritten.'
}
$oldAppData = $env:APPDATA
$oldLocalData = $env:LOCALAPPDATA
$oldProfile = $env:USERPROFILE
try {
    $env:APPDATA = $WorkDir
    $env:LOCALAPPDATA = $WorkDir
    $env:USERPROFILE = $WorkDir
    foreach ($fixture in @('vita_fixture', 'vita_edges')) {
        $version = if ($fixture -eq 'vita_fixture') { '1.0' } else { '2.0' }
        $stdout = Join-Path $WorkDir "$fixture.stdout.txt"
        $stderr = Join-Path $WorkDir "$fixture.stderr.txt"
        $process = Start-Process -FilePath (Join-Path $WorkDir 'PackageEditor.exe') `
            -ArgumentList "convert $fixture.mix $version VitaFixture" `
            -WorkingDirectory $WorkDir -RedirectStandardOutput $stdout `
            -RedirectStandardError $stderr -PassThru
        if (!$process.WaitForExit(15000)) {
            $process.Kill()
            $process.WaitForExit()
            throw "PackageEditor timed out: $fixture"
        }
        Get-Content -LiteralPath $stdout
        if ((Get-Item -LiteralPath $stderr).Length -gt 0) {
            throw (Get-Content -LiteralPath $stderr -Raw)
        }
    }
    $outputs = @{
        '2b1cb7bd.tpi' = '76f706f3c9585c5666756fd54b424852e60ee1c67bc06454784706116b66eba9'
        'fb41cad5.tpi' = 'eab067734444cc1911080043edd62ad93643ccef6c9d41f89ff66a5e0c51c307'
    }
    foreach ($name in $outputs.Keys) {
        $path = Join-Path $WorkDir "Renegade\FDS\ttfs\packages\$name"
        if ((Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash -ne $outputs[$name]) {
            throw "Official output differs from pinned fixture: $name"
        }
    }
    Write-Output 'TTFS b9000 asset-free oracle: PASS'
} finally {
    $env:APPDATA = $oldAppData
    $env:LOCALAPPDATA = $oldLocalData
    $env:USERPROFILE = $oldProfile
}
