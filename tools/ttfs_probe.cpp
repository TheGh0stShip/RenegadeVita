#include "renegade_ttfs.h"
#include <curl/curl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <fstream>
#include <iterator>

struct Pump {
    unsigned count = 0, stop = 0;
    static bool Continue(void *opaque) {
        auto &self = *static_cast<Pump *>(opaque);
        return ++self.count != self.stop;
    }
};

int main(int argc, char **argv) {
    if (argc < 4) {
        fprintf(stderr, "inspect MANIFEST ID | download REPOSITORY ID NEW_CACHE\n");
        return 2;
    }
    char *end = nullptr;
    unsigned long id = strtoul(argv[3], &end, 16);
    if (strlen(argv[3]) != 8 || !end || *end || id > UINT32_MAX) return 2;
    std::string error;
    if (std::string(argv[1]) == "prepare" && argc >= 5) {
        std::vector<uint32_t> ids{uint32_t(id)};
        for (int i = 5; i < argc; ++i) {
            unsigned long next = strtoul(argv[i], &end, 16);
            if (strlen(argv[i]) != 8 || !end || *end || next > UINT32_MAX) return 2;
            ids.push_back(uint32_t(next));
        }
        if (curl_global_init(CURL_GLOBAL_DEFAULT) != CURLE_OK) return 2;
        Pump pump;
        const char *stop = getenv("TTFS_PROBE_CANCEL_AT");
        if (stop) pump.stop = unsigned(strtoul(stop, nullptr, 10));
        RenegadeTTFS::Progress progress{Pump::Continue, &pump};
        std::vector<RenegadeTTFS::CachedPackage> packages;
        bool ok = RenegadeTTFS::Prepare(argv[2], ids, argv[4], packages, error,
            RenegadeTTFS::Limits(), 15, nullptr, progress);
        curl_global_cleanup();
        printf("prepared=%u pumps=%u\n", unsigned(packages.size()), pump.count);
        if (!ok) { fprintf(stderr, "%s\n", error.c_str()); return 1; }
        return 0;
    }
    if (std::string(argv[1]) == "download" && (argc == 5 || argc == 6)) {
        if (curl_global_init(CURL_GLOBAL_DEFAULT) != CURLE_OK) return 2;
        bool ok = RenegadeTTFS::Download(argv[2], uint32_t(id), argv[4], error,
                                        RenegadeTTFS::Limits(), 15, argc == 6 ? argv[5] : nullptr);
        curl_global_cleanup();
        if (!ok) { fprintf(stderr, "%s\n", error.c_str()); return 1; }
        puts("TTFS verified cache committed");
        return 0;
    }
    if (std::string(argv[1]) == "cache") {
        RenegadeTTFS::Manifest manifest;
        bool ok = RenegadeTTFS::Validate_Cache(argv[2], uint32_t(id), manifest, error);
        if (!ok) fprintf(stderr, "%s\n", error.c_str());
        return ok ? 0 : 1;
    }
    if (std::string(argv[1]) != "inspect") return 2;
    std::ifstream stream(argv[2], std::ios::binary | std::ios::ate);
    if (!stream || stream.tellg() > 8 * 1024 * 1024) return 2;
    stream.seekg(0);
    std::vector<char> bytes((std::istreambuf_iterator<char>(stream)), {});
    RenegadeTTFS::Manifest manifest;
    if (!RenegadeTTFS::Parse(bytes.data(), bytes.size(), uint32_t(id), manifest, error)) {
        fprintf(stderr, "%s\n", error.c_str()); return 1;
    }
    printf("%08x %s %s %s files=%zu\n", unsigned(manifest.id), manifest.name.c_str(),
           manifest.version.c_str(), manifest.author.c_str(), manifest.files.size());
    for (const auto &file : manifest.files)
        printf("%s %u\n", file.Cache_Name().c_str(), unsigned(file.size));
}
