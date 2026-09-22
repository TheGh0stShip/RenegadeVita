param(
    [Parameter(Mandatory=$true)][string]$EvidenceDirectory,
    [Parameter(Mandatory=$true)][string]$ExpectedEbootSha256,
    [string]$Candidate = 'A3.5-dev100',
    [string]$Vita3K = 'D:\Vita3K\Vita3K.exe',
    [string]$Vfs = "$env:APPDATA\Vita3K\Vita3K",
    [ValidateRange(10,1800)][int]$TimeoutSeconds = 90,
    [switch]$EnableNativeScreenshot,
    [ValidateSet('Configured','OpenGL','Vulkan')][string]$Backend = 'Configured',
    [switch]$EnableGuestDebugger
)

$ErrorActionPreference = 'Stop'
if ($Candidate -notmatch '^A[0-9]+\.[0-9]+-dev[0-9]+$') { throw 'Invalid candidate label' }
if ($ExpectedEbootSha256 -notmatch '^[0-9a-fA-F]{64}$') { throw 'Invalid expected SELF hash' }
if (Get-Process -Name Vita3K -ErrorAction SilentlyContinue) {
    throw 'An existing Vita3K process is running; refusing to interfere with it'
}
$eboot = Join-Path $Vfs 'ux0\app\RNEGA3101\eboot.bin'
$actualHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $eboot).Hash.ToLowerInvariant()
if ($actualHash -ne $ExpectedEbootSha256.ToLowerInvariant()) { throw 'Installed SELF hash mismatch' }
if (Test-Path -LiteralPath $EvidenceDirectory) { throw 'Evidence directory already exists; use a new run directory' }
New-Item -ItemType Directory -Path $EvidenceDirectory | Out-Null
$EvidenceDirectory = (Resolve-Path -LiteralPath $EvidenceDirectory).Path
$receiptPath = Join-Path $EvidenceDirectory 'windows-run-receipt.json'
$receipt = [ordered]@{
    schema = 1; candidate = $Candidate; title_id = 'RNEGA3101'; evidence_class = 'Vita3K'
    physical_acceptance = $false; pstv_acceptance = $false; status = 'PREPARING'
    started_utc = [DateTime]::UtcNow.ToString('o'); eboot_sha256 = $actualHash
    executable_sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $Vita3K).Hash.ToLowerInvariant()
    timeout_seconds = $TimeoutSeconds; synthetic_input_used = $false; captures = @()
}
function Save-Receipt { $receipt | ConvertTo-Json -Depth 8 | Set-Content -Encoding UTF8 -LiteralPath $receiptPath }
Save-Receipt

$process = $null
$stem = $Candidate.ToLowerInvariant().Replace('.', '')
$runtimeLog = Join-Path $Vfs "ux0\data\renegade\user\logs\$stem-runtime.log"
$receipt.runtime_log_path = $runtimeLog
try {
    # Modify only a candidate-owned config, never the user's global settings.
    $sourceConfig = Join-Path (Split-Path -Parent $Vita3K) 'config.yml'
    $config = Get-Content -Raw -LiteralPath $sourceConfig
    $prefLine = "pref-path: '" + $Vfs.Replace("'", "''") + "\'"
    if ($config -notmatch '(?m)^pref-path:') { throw 'Existing Vita3K config lacks pref-path' }
    $config = [regex]::Replace($config, '(?m)^pref-path:.*$', [System.Text.RegularExpressions.MatchEvaluator]{ param($match) $prefLine })
    $config = [regex]::Replace($config, '(?m)^initial-setup:.*$', 'initial-setup: true')
    if ($Backend -ne 'Configured') {
        if ($config -notmatch '(?m)^backend-renderer:') { throw 'Existing Vita3K config lacks renderer setting' }
        # Vita3K 84184a36 merge() ignores values equal to its default ("Vulkan"),
        # retaining a global OpenGL value. set_backend_renderer() uppercases its
        # input, so this spelling preserves the requested backend through merge.
        $backendConfigValue = $Backend.ToUpperInvariant()
        $config = [regex]::Replace($config, '(?m)^backend-renderer:.*$', "backend-renderer: $backendConfigValue")
        $receipt.backend_override = $Backend
        $receipt.backend_config_value = $backendConfigValue
    }
    if ($EnableGuestDebugger) {
        if ($config -notmatch '(?m)^gdbstub:' -or $config -notmatch '(?m)^wait-for-debugger:') {
            throw 'Existing Vita3K config lacks debugger settings'
        }
        $config = [regex]::Replace($config, '(?m)^gdbstub:.*$', 'gdbstub: true')
        $config = [regex]::Replace($config, '(?m)^wait-for-debugger:.*$', 'wait-for-debugger: false')
        $receipt.guest_debugger_enabled = $true
        $receipt.wait_for_debugger = $false
    }
    if ($EnableNativeScreenshot) {
        if ($config -notmatch '(?m)^keyboard-take-screenshot:') {
            throw 'Existing Vita3K config lacks its native screenshot binding'
        }
        $config = [regex]::Replace($config, '(?m)^keyboard-take-screenshot:.*$', 'keyboard-take-screenshot: F12')
        if ($config -match '(?m)^screenshot-format:') {
            # Vita3K settings enum: None=0, JPEG=1, PNG=2.
            $config = [regex]::Replace($config, '(?m)^screenshot-format:.*$', 'screenshot-format: 2')
        }
        $receipt.native_screenshot_key = 'F12'
    }
    $configPath = Join-Path $EvidenceDirectory 'vita3k-run.yml'
    [IO.File]::WriteAllText($configPath, $config, (New-Object Text.UTF8Encoding($false)))
    $receipt.config_sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $configPath).Hash.ToLowerInvariant()
    if (Test-Path -LiteralPath $runtimeLog) {
        Copy-Item -LiteralPath $runtimeLog -Destination (Join-Path $EvidenceDirectory 'runtime-before.log')
        $receipt.runtime_before_sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $runtimeLog).Hash.ToLowerInvariant()
    }
    Add-Type -AssemblyName System.Drawing
    Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
public static class RenegadeEmulatorWindow {
    [StructLayout(LayoutKind.Sequential)] public struct RECT { public int Left, Top, Right, Bottom; }
    [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr handle, out RECT rect);
    [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
    [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr handle, out uint processId);
    [DllImport("user32.dll", CharSet=CharSet.Unicode)] public static extern int GetWindowText(IntPtr handle, System.Text.StringBuilder title, int capacity);
    [DllImport("user32.dll")] public static extern bool IsIconic(IntPtr handle);
}
'@
    $arguments = @('--installed-path', 'RNEGA3101', '--config-location', ('"' + $configPath + '"'), '--load-config', '--keep-config')
    if ($Backend -ne 'Configured') { $arguments += @('--backend-renderer', $Backend) }
    $receipt.arguments = $arguments
    $process = Start-Process -FilePath $Vita3K -ArgumentList $arguments -PassThru `
        -WorkingDirectory (Split-Path -Parent $Vita3K) `
        -RedirectStandardOutput (Join-Path $EvidenceDirectory 'stdout.log') `
        -RedirectStandardError (Join-Path $EvidenceDirectory 'stderr.log')
    $receipt.process_id = $process.Id
    $receipt.status = 'RUNNING_UNASSESSED'
    Save-Receipt
    $timer = [Diagnostics.Stopwatch]::StartNew()
    $nextCapture = 10
    while (-not $process.WaitForExit(1000)) {
        $process.Refresh()
        $elapsed = $timer.Elapsed.TotalSeconds
        if ($elapsed -ge $nextCapture) {
            $capture = [ordered]@{ elapsed_seconds = $elapsed; status = 'SKIPPED_NOT_FOREGROUND' }
            # The Qt launcher and game are separate windows in the same PID.
            # MainWindowHandle may name the launcher even during gameplay.
            $window = [RenegadeEmulatorWindow]::GetForegroundWindow()
            [uint32]$ownerId = 0
            [void][RenegadeEmulatorWindow]::GetWindowThreadProcessId($window, [ref]$ownerId)
            $title = New-Object Text.StringBuilder(256)
            [void][RenegadeEmulatorWindow]::GetWindowText($window, $title, $title.Capacity)
            $isGameWindow = $title.ToString().StartsWith('Renegade Vita') -or $title.ToString().Contains('RNEGA3101')
            if ($window -ne [IntPtr]::Zero -and $ownerId -eq $process.Id -and $isGameWindow -and
                -not [RenegadeEmulatorWindow]::IsIconic($window)) {
                $rect = New-Object RenegadeEmulatorWindow+RECT
                if ([RenegadeEmulatorWindow]::GetWindowRect($window, [ref]$rect)) {
                    $width = $rect.Right - $rect.Left
                    $height = $rect.Bottom - $rect.Top
                    if ($width -gt 0 -and $height -gt 0 -and $width -le 4096 -and $height -le 2160) {
                        $bitmap = New-Object Drawing.Bitmap($width, $height)
                        $graphics = [Drawing.Graphics]::FromImage($bitmap)
                        try {
                            $graphics.CopyFromScreen($rect.Left, $rect.Top, 0, 0, $bitmap.Size)
                            $name = 'window-{0:D3}.png' -f [int]$elapsed
                            $bitmap.Save((Join-Path $EvidenceDirectory $name), [Drawing.Imaging.ImageFormat]::Png)
                            $capture.status = 'WINDOW_CAPTURED_NOT_FRAMEBUFFER_PROOF'
                            $capture.file = $name
                        } finally {
                            $graphics.Dispose()
                            $bitmap.Dispose()
                        }
                    }
                }
            }
            $receipt.captures += $capture
            Save-Receipt
            $nextCapture += 20
        }
        if ($elapsed -ge $TimeoutSeconds) {
            $receipt.status = 'TIMEOUT_UNASSESSED'
            break
        }
    }
    if ($process.HasExited) {
        $receipt.exit_code = $process.ExitCode
        $receipt.status = if ($process.ExitCode -eq 0) { 'PROCESS_EXITED_ZERO_UNASSESSED' } else { 'PROCESS_FAILED' }
    }
} catch {
    $receipt.status = 'RUNNER_FAILED'
    $receipt.error = $_.Exception.Message
} finally {
    # Only the exact child process created above may be terminated.
    if ($null -ne $process -and -not $process.HasExited) {
        Stop-Process -Id $process.Id -Force
        $process.WaitForExit()
        $receipt.owned_process_terminated = $true
    }
    if (Test-Path -LiteralPath $runtimeLog) {
        Copy-Item -LiteralPath $runtimeLog -Destination (Join-Path $EvidenceDirectory 'runtime-after.log')
        $runtimeAfterHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $runtimeLog).Hash.ToLowerInvariant()
        $receipt.runtime_after_sha256 = $runtimeAfterHash
        $hadRuntimeBefore = $receipt.Contains('runtime_before_sha256')
        $receipt.runtime_changed = (-not $hadRuntimeBefore) -or ($receipt.runtime_before_sha256 -ne $runtimeAfterHash)
        $runtimeHead = @(Get-Content -LiteralPath $runtimeLog -TotalCount 16 -ErrorAction SilentlyContinue)
        $receipt.runtime_candidate_seen = @($runtimeHead | Where-Object { $_ -match [regex]::Escape($Candidate) }).Count -gt 0
        $receipt.title_launch_proven = [bool]($receipt.runtime_changed -and $receipt.runtime_candidate_seen)
    } else {
        $receipt.runtime_changed = $false
        $receipt.runtime_candidate_seen = $false
        $receipt.title_launch_proven = $false
    }
    if (-not $receipt.title_launch_proven -and
        ($receipt.status -eq 'TIMEOUT_UNASSESSED' -or $receipt.status -eq 'RUNNING_UNASSESSED' -or
         $receipt.status -eq 'PROCESS_EXITED_ZERO_UNASSESSED')) {
        $receipt.status = 'TITLE_NOT_LAUNCHED'
        $receipt.error = 'Renegade runtime log was missing, unchanged, or did not match the candidate; Vita3K launch alone is not runtime evidence'
    }
    $receipt.finished_utc = [DateTime]::UtcNow.ToString('o')
    # Separate bounded step invocations retain their own receipts. Include
    # them here rather than claiming this whole run used no synthetic input.
    $steps = @(Get-ChildItem -LiteralPath $EvidenceDirectory -Filter 'step-*.json' | ForEach-Object {
        $step = Get-Content -Raw -LiteralPath $_.FullName | ConvertFrom-Json
        if ($step.candidate -eq $Candidate -and $step.process_id -eq $receipt.process_id -and $step.key -ne 'None') { $step }
    })
    $receipt.synthetic_input_steps = $steps.Count
    # Native file-command senders can retain receipts outside this directory.
    # An empty window-message inventory cannot establish that no input occurred.
    $receipt.native_input_receipt_coverage = 'EXTERNAL_RECEIPTS_NOT_AGGREGATED'
    $receipt.synthetic_input_used = if ($steps.Count -gt 0) { $true } else { $null }
    $receipt.synthetic_inputs_released = if ($steps.Count -gt 0) {
        @($steps | Where-Object { -not $_.input_released }).Count -eq 0
    } else { $null }
    Save-Receipt
}
$receipt | ConvertTo-Json -Depth 8
if ($receipt.status -eq 'RUNNER_FAILED' -or $receipt.status -eq 'PROCESS_FAILED') { exit 1 }
if ($receipt.status -eq 'TITLE_NOT_LAUNCHED') { exit 2 }
if ($receipt.status -eq 'TIMEOUT_UNASSESSED') { exit 124 }
