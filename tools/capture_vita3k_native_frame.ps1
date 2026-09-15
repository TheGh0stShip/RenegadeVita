param(
    [Parameter(Mandatory=$true)][string]$RunReceipt,
    [Parameter(Mandatory=$true)][string]$OutputReceipt
)
$ErrorActionPreference = 'Stop'
if (Test-Path -LiteralPath $OutputReceipt) { throw 'Output receipt already exists' }
$run = Get-Content -Raw -LiteralPath $RunReceipt | ConvertFrom-Json
if ($run.status -ne 'RUNNING_UNASSESSED' -or $run.title_id -ne 'RNEGA3101' -or
    $run.evidence_class -ne 'Vita3K') { throw 'Expected an active owned Renegade run' }
$process = Get-Process -Id $run.process_id
if ($process.ProcessName -ne 'Vita3K' -or $process.StartTime.ToUniversalTime() -lt [datetime]$run.started_utc) {
    throw 'Owned emulator process identity mismatch'
}
$config = Get-Content -Raw -LiteralPath (Join-Path (Split-Path $RunReceipt) 'vita3k-run.yml')
if ($config -notmatch '(?m)^keyboard-button-select: ShiftRight\r?$' -or
    $config -notmatch '(?m)^keyboard-button-square: KeyZ\r?$') {
    throw 'Capture shortcut does not match the admitted emulator key mapping'
}
Add-Type -TypeDefinition @'
using System;
using System.Text;
using System.Runtime.InteropServices;
public static class RenegadeFrameKeys {
    public delegate bool EnumProc(IntPtr h, IntPtr p);
    [DllImport("user32.dll")] static extern bool EnumWindows(EnumProc f, IntPtr p);
    [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
    [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
    [DllImport("user32.dll")] static extern uint GetWindowThreadProcessId(IntPtr h, out uint p);
    [DllImport("user32.dll", CharSet=CharSet.Unicode)] static extern int GetWindowText(IntPtr h, StringBuilder s, int n);
    [DllImport("user32.dll")] static extern bool IsWindowVisible(IntPtr h);
    [DllImport("user32.dll")] public static extern short GetAsyncKeyState(int key);
    [StructLayout(LayoutKind.Sequential)] struct Key { public ushort vk, scan; public uint flags, time; public UIntPtr extra; }
    [StructLayout(LayoutKind.Explicit, Size=32)] struct Union { [FieldOffset(0)] public Key key; }
    [StructLayout(LayoutKind.Sequential)] struct Input { public uint type; public Union value; }
    [DllImport("user32.dll", SetLastError=true)] static extern uint SendInput(uint n, Input[] inputs, int size);
    public static IntPtr Find(uint pid) {
        IntPtr result = IntPtr.Zero;
        EnumWindows(delegate(IntPtr h, IntPtr unused) {
            uint owner; GetWindowThreadProcessId(h, out owner);
            if (owner != pid || !IsWindowVisible(h)) return true;
            var title = new StringBuilder(256); GetWindowText(h, title, title.Capacity);
            if (title.ToString().StartsWith("Renegade Vita")) { result = h; return false; }
            return true;
        }, IntPtr.Zero);
        return result;
    }
    public static uint Chord(bool release) {
        ushort[] scans = release ? new ushort[]{0x36} : new ushort[]{0x36};
        var keys = new Input[1];
        for (int i=0; i<1; ++i) { keys[i].type=1; keys[i].value.key.scan=scans[i]; keys[i].value.key.flags=(uint)(8 | (release ? 2 : 0)); }
        return SendInput(1, keys, Marshal.SizeOf(typeof(Input)));
    }
}
'@
$window = [RenegadeFrameKeys]::Find($process.Id)
if ($window -eq [IntPtr]::Zero) { throw 'Owned gameplay window not found' }
foreach ($key in @(0x10,0x11,0x12,0x5b,0x5c,0x5a)) {
    if (([RenegadeFrameKeys]::GetAsyncKeyState($key) -band 0x8000) -ne 0) { throw 'Capture shortcut/modifier currently held by user' }
}
$previous = [RenegadeFrameKeys]::GetForegroundWindow()
$record = [ordered]@{schema=1; candidate=$run.candidate; process_id=$process.Id; evidence_class='Vita3K';
    action='original Select framebuffer capture only'; navigation_input=$false; framebuffer_validity='UNASSESSED'; keys_released=$false}
$pressed = $false
try {
    if ($previous -ne $window) { [void][RenegadeFrameKeys]::SetForegroundWindow($window); Start-Sleep -Milliseconds 100 }
    if ([RenegadeFrameKeys]::GetForegroundWindow() -ne $window) { throw 'Cannot focus owned gameplay window safely' }
    $pressed = $true
    $record.keydown_count = [RenegadeFrameKeys]::Chord($false)
    if ($record.keydown_count -ne 1) { throw 'Capture shortcut injection incomplete' }
    Start-Sleep -Milliseconds 250
} finally {
    if ($pressed) { $record.keys_released = ([RenegadeFrameKeys]::Chord($true) -eq 1) }
    if ($previous -ne $window -and [RenegadeFrameKeys]::GetForegroundWindow() -eq $window) {
        [void][RenegadeFrameKeys]::SetForegroundWindow($previous)
    }
    $record | ConvertTo-Json | Set-Content -Encoding UTF8 -LiteralPath $OutputReceipt
}
$record | ConvertTo-Json
