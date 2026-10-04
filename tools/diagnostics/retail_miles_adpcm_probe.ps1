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
public static class MilesAdpcmProbe {
    [DllImport("kernel32", CharSet=CharSet.Unicode)] static extern IntPtr LoadLibrary(string path);
    [DllImport("kernel32", CharSet=CharSet.Ansi)] static extern IntPtr GetProcAddress(IntPtr module, string name);
    [DllImport("kernel32")] static extern bool FreeLibrary(IntPtr module);
    [UnmanagedFunctionPointer(CallingConvention.StdCall)] delegate int Inspect(IntPtr source, IntPtr info);
    [UnmanagedFunctionPointer(CallingConvention.StdCall)] delegate int Decode(IntPtr info, IntPtr output, IntPtr bytes);
    [UnmanagedFunctionPointer(CallingConvention.StdCall)] delegate void Release(IntPtr output);
    static Delegate Export(IntPtr module, string name, Type type) {
        IntPtr entry = GetProcAddress(module, name);
        if (entry == IntPtr.Zero) throw new Exception("Required export missing: " + name);
        return Marshal.GetDelegateForFunctionPointer(entry, type);
    }
    public static string Run(string path) {
        IntPtr module = LoadLibrary(path);
        if (module == IntPtr.Zero) throw new Exception("LoadLibrary failed");
        try {
            Inspect inspect = (Inspect)Export(module, "_AIL_WAV_info@8", typeof(Inspect));
            Decode decode = (Decode)Export(module, "_AIL_decompress_ADPCM@12", typeof(Decode));
            Release release = (Release)Export(module, "_AIL_mem_free_lock@4", typeof(Release));
            string result = "";
            for (int variant=0; variant<16; ++variant) {
                int tail=variant%4, frames=9+(variant%8>=4 ? tail*2 : 0);
                MemoryStream stream=new MemoryStream(); BinaryWriter writer=new BinaryWriter(stream);
                writer.Write(new byte[]{82,73,70,70}); writer.Write((uint)(60+tail+(tail%2)));
                writer.Write(new byte[]{87,65,86,69,102,109,116,32}); writer.Write((uint)20);
                writer.Write((ushort)17); writer.Write((ushort)1); writer.Write((uint)22050);
                writer.Write((uint)19600); writer.Write((ushort)8); writer.Write((ushort)4);
                writer.Write((ushort)2); writer.Write((ushort)9);
                writer.Write(new byte[]{102,97,99,116}); writer.Write((uint)4); writer.Write((uint)frames);
                writer.Write(new byte[]{100,97,116,97}); writer.Write((uint)(8+tail));
                writer.Write(new byte[8+tail+(tail%2)]);
                byte[] data=stream.ToArray();
                // The original API has no source-length argument. Guard bytes
                // are private allocation protection, not logical audio payload.
                IntPtr source=Marshal.AllocHGlobal(data.Length+4096), info=Marshal.AllocHGlobal(36);
                IntPtr output=Marshal.AllocHGlobal(4), bytes=Marshal.AllocHGlobal(4);
                try {
                    byte[] storage=new byte[data.Length+4096];
                    if (variant>=8) for (int index=data.Length; index<storage.Length; ++index) storage[index]=85;
                    Marshal.Copy(storage,0,source,storage.Length);
                    Marshal.Copy(data,0,source,data.Length); Marshal.Copy(new byte[36],0,info,36);
                    Marshal.WriteIntPtr(output,IntPtr.Zero); Marshal.WriteInt32(bytes,0);
                    int admitted=inspect(source,info);
                    int decoded=admitted!=0 ? decode(info,output,bytes) : 0;
                    IntPtr image=Marshal.ReadIntPtr(output); int count=Marshal.ReadInt32(bytes);
                    try {
                        if (decoded!=0 && (image==IntPtr.Zero || count<44 || count>4096))
                            throw new Exception("Returned output bounds invalid");
                        int payload=decoded!=0 ? Marshal.ReadInt32(image,40) : 0;
                        if (decoded!=0 && (payload<0 || payload>count-44)) throw new Exception("Invalid output payload");
                        int nonzero=0;
                        for (int index=0; decoded!=0 && index<payload; ++index)
                            if (Marshal.ReadByte(image,44+index)!=0) ++nonzero;
                        result+=variant+":"+tail+":"+frames+":"+admitted+":"+decoded+":"+count+":"+payload+":"+nonzero+";";
                    } finally { if (image!=IntPtr.Zero) release(image); }
                } finally {
                    Marshal.FreeHGlobal(bytes); Marshal.FreeHGlobal(output);
                    Marshal.FreeHGlobal(info); Marshal.FreeHGlobal(source);
                }
            }
            return result;
        } finally { FreeLibrary(module); }
    }
}
'@
[MilesAdpcmProbe]::Run($DllPath)
