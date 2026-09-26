#include "renegade_ttfs.h"
#include <stdio.h>
#include <sys/stat.h>
#include <zlib.h>

namespace RenegadeTTFS {
bool Validate_Cache(const std::string &directory, uint32_t expected_id,
                    Manifest &output, std::string &error, const Limits &limits,
                    const Progress &progress) {
    output = Manifest(); error.clear();
    if (!progress.Continue()) { error = "cache validation cancelled"; return false; }
    std::string path = directory + "/manifest.tpi";
    struct stat info{};
    if (stat(path.c_str(), &info) || !S_ISREG(info.st_mode) || info.st_size < 0 ||
        uint64_t(info.st_size) > limits.manifest_bytes) {
        error = "cache manifest unavailable/oversized"; return false;
    }
    std::vector<unsigned char> bytes(size_t(info.st_size));
    FILE *input = fopen(path.c_str(), "rb");
    if (!input) { error = "cache manifest open failed"; return false; }
    bool ok = fread(bytes.data(), 1, bytes.size(), input) == bytes.size() && fgetc(input) == EOF && !ferror(input);
    if (fclose(input)) ok = false;
    if (!ok) { error = "cache manifest read failed"; return false; }
    Manifest candidate;
    if (!Parse(bytes.data(), bytes.size(), expected_id, candidate, error, limits)) return false;
    unsigned char buffer[32768];
    for (const File &file : candidate.files) {
        path = directory + "/" + file.Cache_Name();
        if (stat(path.c_str(), &info) || !S_ISREG(info.st_mode) ||
            info.st_size < 0 || uint64_t(info.st_size) != file.size) {
            error = "cache payload size/type: " + file.name; return false;
        }
        input = fopen(path.c_str(), "rb");
        if (!input) { error = "cache payload open: " + file.name; return false; }
        uLong crc = crc32(0, Z_NULL, 0);
        uint64_t total = 0;
        size_t got;
        while ((got = fread(buffer, 1, sizeof(buffer), input)) != 0) {
            if (!progress.Continue()) {
                fclose(input); error = "cache validation cancelled"; return false;
            }
            total += got;
            if (total > file.size) break;
            crc = crc32(crc, buffer, static_cast<uInt>(got));
        }
        ok = !ferror(input) && total == file.size && uint32_t(crc) == file.crc;
        if (fclose(input)) ok = false;
        if (!ok) { error = "cache payload CRC/read: " + file.name; return false; }
    }
    if (!progress.Continue()) { error = "cache validation cancelled"; return false; }
    output = std::move(candidate);
    return true;
}
}
