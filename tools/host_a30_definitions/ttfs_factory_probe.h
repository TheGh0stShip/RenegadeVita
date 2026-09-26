#pragma once
#include "renegade_ttfs_factory.h"
#include "ffactorylist.h"
#include "wwfile.h"
#include <stdio.h>
#include <string.h>

inline int Validate_TTFS_Fixture_Factory(const char *cache) {
    RenegadeTTFSFactory factory;
    std::string error;
    if (!factory.Mount(cache, 0x2b1cb7bdU, error)) {
        fprintf(stderr, "ttfs.mount=%s\n", error.c_str()); return 1;
    }
    FileFactoryListClass chain;
    chain.Add_FileFactory(&factory, "TTFS-fixture");
    FileClass *file = chain.Get_File("VITA_BYTES.BIN");
    bool ok = file && file->Is_Available() && file->Open(FileClass::READ) && file->Size() == 768;
    unsigned char bytes[768] = {};
    if (ok) {
        ok = file->Read(bytes, sizeof(bytes)) == 768;
        for (size_t i = 0; i < sizeof(bytes); ++i) ok = (bytes[i] == (i & 255)) && ok;
        ok = file->Seek(257, SEEK_SET) == 257 && file->Read(bytes, 3) == 3 &&
             bytes[0] == 1 && bytes[1] == 2 && bytes[2] == 3 && ok;
        ok = file->Write("x", 1) == 0 && file->Delete() == 0 && file->Create() == 0 && ok;
        ok = file->Open(FileClass::WRITE) == 0 && file->Set_Name("../escape") == nullptr && ok;
        file->Close();
    }
    if (file) chain.Return_File(file);
    ok = factory.Get_File("../vita_bytes.bin") == nullptr && ok;
    ok = !factory.Mount(cache, 0x12345678U, error) && factory.Get_File("vita_bytes.bin") == nullptr && ok;
    ok = factory.Mount(cache, 0x2b1cb7bdU, error) && ok;
    factory.Unmount();
    ok = factory.Get_File("vita_bytes.bin") == nullptr && ok;
    printf("ttfs.original_file_factory_read_seek_readonly_remount=%s\n", ok ? "PASS" : "FAIL");
    return ok ? 0 : 1;
}
