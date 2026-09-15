param([Parameter(Mandatory=$true)][string]$ReceiptPath)
$ErrorActionPreference = 'Stop'
$receipt = Get-Content -Raw -LiteralPath $ReceiptPath | ConvertFrom-Json
if ($receipt.evidence_class -ne 'Vita3K' -or $receipt.title_id -ne 'RNEGA3101' -or
    $receipt.status -ne 'RUNNING_UNASSESSED') { throw 'No active owned run' }
$process = Get-Process -Id $receipt.process_id -ErrorAction Stop
$started = [DateTime]::Parse($receipt.started_utc).ToUniversalTime()
if ($process.ProcessName -ne 'Vita3K' -or $process.StartTime.ToUniversalTime() -lt $started -or
    $process.StartTime.ToUniversalTime() -gt $started.AddSeconds(60)) { throw 'Process identity mismatch' }
Add-Type -AssemblyName System.Drawing
Add-Type -AssemblyName System.Windows.Forms
Add-Type -TypeDefinition @'
using System;
using System.Text;
using System.Runtime.InteropServices;
public static class RenegadeVisibleCapture {
    public delegate bool EnumProc(IntPtr hwnd, IntPtr param);
    [StructLayout(LayoutKind.Sequential)] public struct RECT { public int Left, Top, Right, Bottom; }
    [DllImport("user32.dll")] public static extern bool EnumWindows(EnumProc callback, IntPtr param);
    [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr hwnd, out uint pid);
    [DllImport("user32.dll", CharSet=CharSet.Unicode)] public static extern int GetWindowText(IntPtr hwnd, StringBuilder text, int count);
    [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr hwnd);
    [DllImport("user32.dll")] public static extern bool IsIconic(IntPtr hwnd);
    [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr hwnd, out RECT rect);
    [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
    [DllImport("user32.dll")] public static extern IntPtr GetWindow(IntPtr hwnd, uint command);
    [DllImport("user32.dll", EntryPoint="GetWindowLongPtrW")] public static extern IntPtr GetWindowLongPtr(IntPtr hwnd, int index);
    [DllImport("user32.dll")] public static extern bool SetWindowPos(IntPtr hwnd, IntPtr after, int x, int y, int width, int height, uint flags);
    public static IntPtr Find(uint pid) {
        IntPtr found = IntPtr.Zero;
        EnumWindows(delegate(IntPtr hwnd, IntPtr ignored) {
            uint owner; GetWindowThreadProcessId(hwnd, out owner);
            if (owner != pid || !IsWindowVisible(hwnd) || IsIconic(hwnd)) return true;
            var title = new StringBuilder(256); GetWindowText(hwnd, title, title.Capacity);
            if (title.ToString().StartsWith("Renegade Vita") || title.ToString().Contains("RNEGA3101")) {
                found = hwnd; return false;
            }
            return true;
        }, IntPtr.Zero);
        return found;
    }
}
'@
$window = [RenegadeVisibleCapture]::Find([uint32]$process.Id)
if ($window -eq [IntPtr]::Zero) { throw 'Owned non-minimized game window unavailable' }
$rect = New-Object RenegadeVisibleCapture+RECT
if (-not [RenegadeVisibleCapture]::GetWindowRect($window, [ref]$rect)) { throw 'No window bounds' }
$width = $rect.Right - $rect.Left; $height = $rect.Bottom - $rect.Top
$desktop = [Windows.Forms.SystemInformation]::VirtualScreen
if ($width -le 0 -or $height -le 0 -or $width -gt 4096 -or $height -gt 2160 -or
    $rect.Left -lt $desktop.Left -or $rect.Top -lt $desktop.Top -or
    $rect.Right -gt $desktop.Right -or $rect.Bottom -gt $desktop.Bottom) { throw 'Unsafe screen capture bounds' }
$previous = [RenegadeVisibleCapture]::GetWindow($window, 3)
$wasTopmost = ([RenegadeVisibleCapture]::GetWindowLongPtr($window, -20).ToInt64() -band 8) -ne 0
$foreground = [RenegadeVisibleCapture]::GetForegroundWindow()
$name = 'visible-' + [DateTime]::UtcNow.ToString('yyyyMMddTHHmmssfffZ')
$directory = Split-Path -Parent $ReceiptPath
$record = [ordered]@{ candidate=$receipt.candidate; process_id=$process.Id; evidence_class='Vita3K';
    capture_method='TEMPORARILY_EXPOSED_SCREEN_NOT_FRAMEBUFFER_PROOF'; input_used=$false;
    activation_requested=$false; status='STARTED'; window_order_restored=$false }
$raised = $false
try {
    # NOMOVE | NOSIZE | NOACTIVATE | NOOWNERZORDER. Never SetForegroundWindow.
    $raised = [RenegadeVisibleCapture]::SetWindowPos($window, [IntPtr](-1), 0, 0, 0, 0, 0x213)
    if (-not $raised) { throw 'Could not expose owned game window' }
    Start-Sleep -Milliseconds 180
    $bitmap = New-Object Drawing.Bitmap($width, $height)
    $graphics = [Drawing.Graphics]::FromImage($bitmap)
    try {
        $graphics.CopyFromScreen($rect.Left, $rect.Top, 0, 0, $bitmap.Size)
        $record.capture = $name + '.png'
        $bitmap.Save((Join-Path $directory $record.capture), [Drawing.Imaging.ImageFormat]::Png)
        $record.status = 'CAPTURED_UNASSESSED'
    } finally { $graphics.Dispose(); $bitmap.Dispose() }
} finally {
    if ($raised) {
        $restored = $true
        if (-not $wasTopmost) {
            $restored = [RenegadeVisibleCapture]::SetWindowPos($window, [IntPtr](-2), 0, 0, 0, 0, 0x213)
        }
        if ($previous -ne [IntPtr]::Zero) {
            $restored = [RenegadeVisibleCapture]::SetWindowPos($window, $previous, 0, 0, 0, 0, 0x213) -and $restored
        }
        $record.window_order_restored = $restored
    }
    $record.foreground_unchanged = [RenegadeVisibleCapture]::GetForegroundWindow() -eq $foreground
    $record | ConvertTo-Json | Set-Content -Encoding UTF8 -LiteralPath (Join-Path $directory ($name + '.json'))
}
$record | ConvertTo-Json
