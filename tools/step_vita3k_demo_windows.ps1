param(
    [Parameter(Mandatory=$true)][string]$ReceiptPath,
    [ValidateSet('None','W','A','S','D','I','J','K','L','Q','E','X','Z','V','C','Up','Down','Left','Right','QuickSave','Select','Start','F12')][string]$Key = 'None',
    [ValidateRange(50,3000)][int]$HoldMilliseconds = 120,
    [ValidateRange(-1,959)][int]$TouchX = -1,
    [ValidateRange(-1,543)][int]$TouchY = -1
)

# Bounded interactive emulator step, never physical Vita input.
$ErrorActionPreference = 'Stop'
if (($TouchX -ge 0) -ne ($TouchY -ge 0) -or ($TouchX -ge 0 -and $Key -ne 'None')) {
    throw 'Use one complete native-screen touch or one key step'
}
$receipt = Get-Content -Raw -LiteralPath $ReceiptPath | ConvertFrom-Json
if ($receipt.evidence_class -ne 'Vita3K' -or $receipt.title_id -ne 'RNEGA3101' -or
    $receipt.status -ne 'RUNNING_UNASSESSED') { throw 'Receipt is not an active owned Renegade emulator run' }
$process = Get-Process -Id $receipt.process_id -ErrorAction Stop
if ($process.ProcessName -ne 'Vita3K') { throw 'Process identity mismatch' }
$started = [DateTime]::Parse($receipt.started_utc).ToUniversalTime()
$processStarted = $process.StartTime.ToUniversalTime()
if ($processStarted -lt $started -or $processStarted -gt $started.AddSeconds(60)) {
    throw 'Process start time does not match this run'
}
Add-Type -AssemblyName System.Drawing
Add-Type -TypeDefinition @'
using System;
using System.Text;
using System.Runtime.InteropServices;
public static class RenegadeStepWindow {
    public delegate bool EnumProc(IntPtr hwnd, IntPtr param);
    [StructLayout(LayoutKind.Sequential)] public struct RECT { public int Left, Top, Right, Bottom; }
    [DllImport("user32.dll")] public static extern bool EnumWindows(EnumProc callback, IntPtr param);
    [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr hwnd, out uint pid);
    [DllImport("user32.dll", CharSet=CharSet.Unicode)] public static extern int GetWindowText(IntPtr hwnd, StringBuilder text, int count);
    [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr hwnd);
    [DllImport("user32.dll")] public static extern bool IsIconic(IntPtr hwnd);
    [DllImport("user32.dll", SetLastError=true)] public static extern bool PostMessage(IntPtr hwnd, uint message, UIntPtr key, IntPtr detail);
    [DllImport("user32.dll")] public static extern uint MapVirtualKey(uint key, uint mode);
    [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
    [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr hwnd, out RECT rect);
    [DllImport("user32.dll")] public static extern bool GetClientRect(IntPtr hwnd, out RECT rect);
    public static bool QueueTouch(IntPtr hwnd, uint pid, int x, int y, bool release) {
        uint owner; GetWindowThreadProcessId(hwnd, out owner);
        RECT rect;
        if (owner != pid || !GetClientRect(hwnd, out rect) || rect.Right != 960 || rect.Bottom != 544) return false;
        IntPtr point = new IntPtr(x | (y << 16));
        if (!release && !PostMessage(hwnd, 0x0200U, UIntPtr.Zero, point)) return false;
        return PostMessage(hwnd, release ? 0x0202U : 0x0201U, release ? UIntPtr.Zero : new UIntPtr(1), point);
    }
    public static bool QueueKey(IntPtr hwnd, uint pid, uint key, bool release) {
        uint owner; GetWindowThreadProcessId(hwnd, out owner);
        if (owner != pid) return false;
        uint scan = MapVirtualKey(key, 0) & 0xff;
        if (scan == 0) return false;
        long detail = 1L | ((long)scan << 16);
        if (key >= 0x25 && key <= 0x28) detail |= 1L << 24;
        if (release) detail |= 0xc0000000L;
        // WM_KEY messages identify Shift generically; the scan code selects
        // right Shift (Vita Select in this candidate's emulator mapping).
        uint messageKey = key == 0xa1 ? 0x10U : key;
        return PostMessage(hwnd, release ? 0x0101U : 0x0100U, new UIntPtr(messageKey), new IntPtr(detail));
    }
    public static IntPtr FindGame(uint pid) {
        IntPtr result = IntPtr.Zero;
        EnumWindows(delegate(IntPtr hwnd, IntPtr ignored) {
            uint owner; GetWindowThreadProcessId(hwnd, out owner);
            if (owner != pid || !IsWindowVisible(hwnd) || IsIconic(hwnd)) return true;
            var title = new StringBuilder(256); GetWindowText(hwnd, title, title.Capacity);
            if (title.ToString().StartsWith("Renegade Vita") || title.ToString().Contains("RNEGA3101")) {
                result = hwnd; return false;
            }
            return true;
        }, IntPtr.Zero);
        return result;
    }
}
'@
$window = [RenegadeStepWindow]::FindGame([uint32]$process.Id)
if ($window -eq [IntPtr]::Zero) { throw 'Owned visible game window not found' }
$record = [ordered]@{ evidence_class='Vita3K'; process_id=$process.Id; candidate=$receipt.candidate;
    timestamp_utc=[DateTime]::UtcNow.ToString('o'); key=$Key; hold_milliseconds=$HoldMilliseconds;
    input_released=$false; status='STARTED'; input_method='OWNED_WINDOW_MESSAGES';
    foreground_required=$false; os_keyboard_injection=$false }
$directory = Split-Path -Parent $ReceiptPath
$name = 'step-' + [DateTime]::UtcNow.ToString('yyyyMMddTHHmmssfffZ')
try {
    if ($TouchX -ge 0) {
        $record.touch_native = @($TouchX, $TouchY)
        try {
            if (-not [RenegadeStepWindow]::QueueTouch($window, [uint32]$process.Id, $TouchX, $TouchY, $false)) {
                throw 'Owned native-size touch surface unavailable'
            }
            Start-Sleep -Milliseconds $HoldMilliseconds
        } finally {
            $record.input_released = [RenegadeStepWindow]::QueueTouch($window, [uint32]$process.Id, $TouchX, $TouchY, $true)
            $record.release_queued = $record.input_released
            if (-not $record.input_released -and -not $process.HasExited) { throw 'Could not queue touch release' }
        }
        Start-Sleep -Milliseconds 350
    }
    if ($Key -ne 'None') {
        $arrows = @{ Up=0x26; Down=0x28; Left=0x25; Right=0x27 }
        [uint32[]]$keys = if ($Key -eq 'QuickSave') { @(0xa1,0x5a) }
            elseif ($Key -eq 'Select') { @(0xa1) }
            elseif ($Key -eq 'Start') { @(0x0d) }
            elseif ($Key -eq 'F12') { @(0x7b) }
            elseif ($arrows.ContainsKey($Key)) { @($arrows[$Key]) } else { @([byte][char]$Key) }
        $record.virtual_keys = $keys
        $record.scan_codes = @($keys | ForEach-Object { [RenegadeStepWindow]::MapVirtualKey($_, 0) -band 255 })
        $record.native_action = if ($Key -eq 'QuickSave') { 'Select+Square; original QUICKSAVE; consumption unproven' } else { $Key }
        try {
            foreach ($vk in $keys) {
                if (-not [RenegadeStepWindow]::QueueKey($window, [uint32]$process.Id, $vk, $false)) {
                    throw 'Could not queue key-down to the owned game window'
                }
            }
            $timer = [Diagnostics.Stopwatch]::StartNew()
            while ($timer.ElapsedMilliseconds -lt $HoldMilliseconds) {
                if ($process.HasExited) { throw 'Owned emulator process exited' }
                Start-Sleep -Milliseconds 10
            }
        } finally {
            $record.input_released = $true
            for ($index = $keys.Length - 1; $index -ge 0; --$index) {
                $released = [RenegadeStepWindow]::QueueKey($window, [uint32]$process.Id, $keys[$index], $true)
                $record.input_released = $released -and $record.input_released
            }
            $record.release_queued = $record.input_released
            if (-not $record.input_released -and -not $process.HasExited) { throw 'Could not queue key release' }
        }
        Start-Sleep -Milliseconds 350
    }
    $rect = New-Object RenegadeStepWindow+RECT
    if (-not [RenegadeStepWindow]::GetWindowRect($window, [ref]$rect)) { throw 'Window bounds unavailable' }
    $width = $rect.Right - $rect.Left; $height = $rect.Bottom - $rect.Top
    if ($width -le 0 -or $height -le 0 -or $width -gt 4096 -or $height -gt 2160) { throw 'Unsafe capture bounds' }
    $bitmap = New-Object Drawing.Bitmap($width, $height)
    $graphics = [Drawing.Graphics]::FromImage($bitmap)
    try {
        # Do not ask the accelerated Qt window to repaint through PrintWindow.
        # Two matching runs failed in Qt; the no-PrintWindow comparison survived.
        # Input remains background-capable. Screen capture never forces focus.
        $record.capture_method = 'SKIPPED_NOT_FOREGROUND'
        if ([RenegadeStepWindow]::GetForegroundWindow() -eq $window) {
            $graphics.CopyFromScreen($rect.Left, $rect.Top, 0, 0, $bitmap.Size)
            $record.capture_method = 'SCREEN_COPY_NOT_FRAMEBUFFER_PROOF'
            $record.capture = $name + '.png'
            $bitmap.Save((Join-Path $directory $record.capture), [Drawing.Imaging.ImageFormat]::Png)
        }
    } finally { $graphics.Dispose(); $bitmap.Dispose() }
    $record.status = 'STEP_QUEUED_UNASSESSED'
} finally {
    $record | ConvertTo-Json | Set-Content -Encoding UTF8 -LiteralPath (Join-Path $directory ($name + '.json'))
}
$record | ConvertTo-Json
