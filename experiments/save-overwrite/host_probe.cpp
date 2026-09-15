#include "renegade_file_factory.h"
#include "chunkio.h"
#include "wwfile.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>

// Synthetic bytes only; never opens retail or an actual gameplay save.
int main()
{
    char temporary[] = "/tmp/renegade-overwrite-XXXXXX";
    const char *root = mkdtemp(temporary);
    if (!root) return 2;
    char retail[512], user[512], cache[512], mods[512], physical[640];
    snprintf(retail, sizeof(retail), "%s/retail", root);
    snprintf(user, sizeof(user), "%s/user", root);
    snprintf(cache, sizeof(cache), "%s/cache", root);
    snprintf(mods, sizeof(mods), "%s/mods", root);
    if (mkdir(retail, 0700) || mkdir(user, 0700) ||
        mkdir(cache, 0700) || mkdir(mods, 0700)) return 2;
    const RenegadePathRoots roots = {retail, user, cache, mods};
    RenegadeRootedFileFactoryClass factory(roots);
    const char payload[] = "ABCDEFG";
    for (int pass = 0; pass < 2; ++pass) {
        const int length = pass == 0 ? 7 : 3;
        FileClass *file = factory.Get_File("user/overwrite.tmp");
        if (!file || !file->Open(FileClass::WRITE)) return 2;
        ChunkSaveClass chunks(file);
        const bool written = chunks.Begin_Chunk(0x1234) &&
            chunks.Write(payload, length) == length && chunks.End_Chunk();
        file->Close();
        factory.Return_File(file);
        snprintf(physical, sizeof(physical), "%s/overwrite.tmp", user);
        struct stat status = {};
        if (!written || stat(physical, &status)) return 2;
        printf("pass=%d expected_bytes=%d actual_bytes=%ld\n",
            pass, 8 + length, static_cast<long>(status.st_size));
        if (status.st_size != 8 + length) return 1;
        FILE *input = fopen(physical, "rb");
        if (!input) return 2;
        unsigned char data[16] = {};
        const size_t count = fread(data, 1, sizeof(data), input);
        fclose(input);
        if (count != static_cast<size_t>(8 + length) ||
            data[0] != 0x34 || data[1] != 0x12 || data[4] != length ||
            memcmp(data + 8, payload, length)) return 1;
    }
    printf("PASS: original rooted WRITE plus chunk backpatch truncates shorter overwrite\n");
    return 0;
}
