param([Parameter(Mandatory=$true)][string]$ReceiptPath,
      [Parameter(Mandatory=$true)][string]$Reason)
$ErrorActionPreference = 'Stop'
$receipt = Get-Content -Raw -LiteralPath $ReceiptPath | ConvertFrom-Json
if ($receipt.evidence_class -ne 'Vita3K' -or $receipt.title_id -ne 'RNEGA3101' -or $receipt.candidate -notmatch '^A[0-9]+\.[0-9]+-dev[0-9]+$') { throw 'Wrong owned run' }
$process = Get-Process -Id $receipt.process_id -ErrorAction SilentlyContinue
if ($null -eq $process) { Write-Output 'Owned process already stopped'; exit 0 }
$start = [DateTime]::Parse($receipt.started_utc).ToUniversalTime()
if ($process.ProcessName -ne 'Vita3K' -or $process.StartTime.ToUniversalTime() -lt $start -or $process.StartTime.ToUniversalTime() -gt $start.AddSeconds(60)) { throw 'Process identity mismatch' }
$directory = Split-Path -Parent $ReceiptPath
$tag = [DateTime]::UtcNow.ToString('yyyyMMddTHHmmssfffZ')
$stem = $receipt.candidate.ToLowerInvariant().Replace('.', '')
$log = Join-Path $env:APPDATA "Vita3K\Vita3K\ux0\data\renegade\user\logs\$stem-runtime.log"
$destination = Join-Path $directory "runtime-before-stop-$tag.log"
if (Test-Path -LiteralPath $log) { Copy-Item -LiteralPath $log -Destination $destination }
$closed = $process.CloseMainWindow()
$forced = -not $process.WaitForExit(10000)
if ($forced) { Stop-Process -Id $process.Id; $process.WaitForExit() }
$record = [ordered]@{ candidate=$receipt.candidate; process_id=$process.Id; close_requested=$closed; forced=$forced; stopped=$process.HasExited; reason=$Reason; timestamp_utc=[DateTime]::UtcNow.ToString('o') }
if (Test-Path -LiteralPath $destination) { $record.log_sha256=(Get-FileHash -Algorithm SHA256 -LiteralPath $destination).Hash }
$record | ConvertTo-Json | Set-Content -Encoding UTF8 -LiteralPath (Join-Path $directory "stop-$tag.json")
$record | ConvertTo-Json
