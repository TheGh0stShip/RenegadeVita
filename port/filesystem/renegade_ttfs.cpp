#include "renegade_ttfs.h"

#include <stdio.h>
#include <string.h>
#include <set>
#include <utility>

namespace RenegadeTTFS {
namespace {
class Reader {
public:
    const unsigned char *data;
    size_t remaining;
    Reader(const void *p, size_t n) : data(static_cast<const unsigned char *>(p)), remaining(n) {}
    bool U32(uint32_t &value) {
        if (remaining < 4) return false;
        value = uint32_t(data[0]) | (uint32_t(data[1]) << 8) |
                (uint32_t(data[2]) << 16) | (uint32_t(data[3]) << 24);
        data += 4; remaining -= 4; return true;
    }
    bool Text(std::string &value) {
        if (remaining < 2) return false;
        size_t length = size_t(data[0]) | (size_t(data[1]) << 8);
        data += 2; remaining -= 2;
        if (length > remaining || length > 4096) return false;
        value.assign(reinterpret_cast<const char *>(data), length);
        data += length; remaining -= length;
        for (unsigned char c : value) if (c < 32 || c == 127) return false;
        return true;
    }
    bool Chunk(const char *tag, Reader &body) {
        if (remaining < 8 || memcmp(data, tag, 4) != 0) return false;
        data += 4; remaining -= 4;
        uint32_t bytes;
        if (!U32(bytes) || bytes > remaining) return false;
        body = Reader(data, bytes); data += bytes; remaining -= bytes;
        return true;
    }
};

bool Safe_Name(const std::string &name, std::string &folded) {
    if (name.empty() || name.size() > 240 || name == "." || name == ".." ||
        name.back() == '.' || name.back() == ' ') return false;
    folded.clear();
    for (unsigned char c : name) {
        if (c < 32 || c >= 127 || strchr("\\/:*?\"<>|", c)) return false;
        folded.push_back(c >= 'A' && c <= 'Z' ? char(c + ('a' - 'A')) : char(c));
    }
    const size_t dot = folded.rfind('.');
    const std::string extension = dot == std::string::npos ? "" : folded.substr(dot);
    const char *blocked[] = {".exe", ".dll", ".com", ".bat", ".cmd", ".ps1",
                            ".sh", ".elf", ".self", ".suprx", ".skprx", ".vpk"};
    for (const char *candidate : blocked) if (extension == candidate) return false;
    return true;
}
}

std::string File::Cache_Name() const {
    char prefix[10];
    snprintf(prefix, sizeof(prefix), "%08X.", unsigned(crc));
    return std::string(prefix) + name;
}

bool Parse(const void *data, size_t bytes, uint32_t expected_id,
           Manifest &output, std::string &error, const Limits &limits) {
    output = Manifest(); error.clear();
    auto fail = [&error](const char *why) { error = why; return false; };
    if (!data || bytes > limits.manifest_bytes) return fail("manifest byte limit/null input");
    Reader input(data, bytes), chunk(nullptr, 0);
    Manifest parsed;
    uint32_t count = 0;
    if (!input.Chunk("DAEH", chunk) || !chunk.U32(parsed.id) ||
        !chunk.U32(count) || chunk.remaining || parsed.id != expected_id)
        return fail("manifest header/package ID");
    if (!input.Chunk("ATAD", chunk) || !chunk.Text(parsed.name) ||
        !chunk.Text(parsed.version) || !chunk.Text(parsed.author) ||
        !chunk.U32(parsed.metadata_word) || chunk.remaining || parsed.name.empty() ||
        parsed.metadata_word != 2)
        return fail("manifest metadata");
    if (count > limits.file_count || count > input.remaining / 18)
        return fail("manifest file count");
    uint64_t total = 0;
    std::set<std::string> names;
    for (uint32_t i = 0; i < count; ++i) {
        File file{};
        std::string folded;
        if (!input.Chunk("ELIF", chunk) || !chunk.U32(file.crc) ||
            !chunk.U32(file.size) || !chunk.Text(file.name) || chunk.remaining)
            return fail("manifest file record");
        if (!Safe_Name(file.name, folded) || !names.insert(folded).second)
            return fail("manifest unsafe/duplicate filename");
        total += file.size;
        if (file.size > limits.file_bytes || total > limits.total_bytes)
            return fail("manifest payload byte limit");
        parsed.files.push_back(std::move(file));
    }
    if (input.remaining) return fail("manifest trailing/unknown chunks");
    output = std::move(parsed);
    return true;
}
}
