param([Parameter(Mandatory=$true)][string]$DllPath,
      [Parameter(Mandatory=$true)][string]$ExpectedSha256)
$ErrorActionPreference = 'Stop'
if ([IntPtr]::Size -ne 4) { throw 'Run in 32-bit Windows PowerShell.' }
if ((Get-FileHash -Algorithm SHA256 -LiteralPath $DllPath).Hash.ToLowerInvariant() -ne $ExpectedSha256.ToLowerInvariant()) {
    throw 'Reference DLL identity mismatch.'
}
Add-Type -TypeDefinition @'
using System;
using System.IO;
using System.Runtime.InteropServices;
public static class MilesWaveProbe {
    [DllImport("kernel32", CharSet=CharSet.Unicode, SetLastError=true)]
    static extern IntPtr LoadLibrary(string path);
    [DllImport("kernel32", CharSet=CharSet.Ansi, SetLastError=true)]
    static extern IntPtr GetProcAddress(IntPtr module, string name);
    [DllImport("kernel32")] static extern bool FreeLibrary(IntPtr module);
    [UnmanagedFunctionPointer(CallingConvention.StdCall)]
    delegate int Inspect(IntPtr source, IntPtr info);
    public static string Run(string path) {
        IntPtr module = LoadLibrary(path);
        if (module == IntPtr.Zero) throw new Exception("LoadLibrary failed");
        try {
            IntPtr entry = GetProcAddress(module, "_AIL_WAV_info@8");
            if (entry == IntPtr.Zero) throw new Exception("WAV inspection export missing");
            Inspect inspect = (Inspect)Marshal.GetDelegateForFunctionPointer(entry, typeof(Inspect));
            string result = "";
            for (int variant=0; variant<8; ++variant) {
                bool adpcm = variant >= 4;
                // Authored mono PCM/IMA fixtures; no retail media.
                MemoryStream stream = new MemoryStream();
                BinaryWriter writer = new BinaryWriter(stream);
                writer.Write(new byte[] {82,73,70,70});
                writer.Write((uint)((adpcm ? 60 : 40) + ((variant & 1) != 0 ? 7 : 0) + ((variant & 2) != 0 ? 8 : 0)));
                writer.Write(new byte[] {87,65,86,69,102,109,116,32});
                writer.Write((uint)(adpcm ? 20 : 16)); writer.Write((ushort)(adpcm ? 17 : 1)); writer.Write((ushort)1);
                writer.Write((uint)22050); writer.Write((uint)(adpcm ? 19600 : 44100));
                writer.Write((ushort)(adpcm ? 8 : 2)); writer.Write((ushort)(adpcm ? 4 : 16));
                if (adpcm) {
                    writer.Write((ushort)2); writer.Write((ushort)9);
                    writer.Write(new byte[] {102,97,99,116}); writer.Write((uint)4); writer.Write((uint)9);
                }
                writer.Write(new byte[] {100,97,116,97}); writer.Write((uint)(adpcm ? 8 : 4));
                if (adpcm) writer.Write(new byte[8]);
                else { writer.Write((short)0); writer.Write((short)100); }
                if ((variant & 2) != 0) writer.Write(new byte[] {106,117,110,107,255,255,255,255});
                byte[] data = stream.ToArray();
                // Guard storage is not counted as source data. This legacy API
                // has no length argument; no memory-safety acceptance is inferred.
                byte[] storage = new byte[data.Length + 4096];
                Array.Copy(data, storage, data.Length);
                IntPtr source = Marshal.AllocHGlobal(storage.Length);
                IntPtr info = Marshal.AllocHGlobal(36);
                try {
                    Marshal.Copy(storage, 0, source, storage.Length);
                    Marshal.Copy(new byte[36], 0, info, 36);
                    int accepted = inspect(source, info);
                    long offset = accepted != 0 ? Marshal.ReadIntPtr(info,4).ToInt64() - source.ToInt64() : 0;
                    int bytes = accepted != 0 ? Marshal.ReadInt32(info,8) : 0;
                    if (accepted != 0 && (offset < 0 || offset > data.Length || bytes < 0 || bytes > data.Length-offset))
                        throw new Exception("Returned payload exceeds authored source");
                    int frames = accepted != 0 ? Marshal.ReadInt32(info,24) : 0;
                    result += variant + ":" + accepted + ":" + offset + ":" + bytes + ":" + frames + ";";
                } finally { Marshal.FreeHGlobal(info); Marshal.FreeHGlobal(source); }
            }
            return result;
        } finally { FreeLibrary(module); }
    }
}
'@
[MilesWaveProbe]::Run($DllPath)
