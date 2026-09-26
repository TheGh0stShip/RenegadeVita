#pragma once

#include <stddef.h>
#include <stdint.h>
#include <string>
#include <vector>

// TT 4.8.4 PackageEditor manifests; no changes to retail MIX formats.
namespace RenegadeTTFS {
// Called on the requesting thread, outside engine packet dispatch. A false
// return cancels preparation; no engine ownership is transferred to curl.
struct Progress {
    bool (*pump)(void *) = nullptr;
    void *context = nullptr;
    bool Continue() const { return !pump || pump(context); }
};
struct File {
    uint32_t crc;
    uint32_t size;
    std::string name;
    std::string Cache_Name() const;
};
struct Manifest {
    uint32_t id = 0;
    uint32_t metadata_word = 0; // Observed value 2; other layouts are rejected.
    std::string name, version, author;
    std::vector<File> files;
};
struct Limits {
    size_t manifest_bytes = 8 * 1024 * 1024;
    uint32_t file_count = 65536;
    uint32_t file_bytes = 512 * 1024 * 1024;
    uint64_t total_bytes = 2ULL * 1024 * 1024 * 1024;
};
struct CachedPackage {
    uint32_t id;
    std::string directory;
};

// On failure output is cleared; error names the failing field/boundary.
bool Parse(const void *data, size_t bytes, uint32_t expected_id,
           Manifest &output, std::string &error, const Limits &limits = Limits());
bool Validate_Cache(const std::string &directory, uint32_t expected_id,
                    Manifest &output, std::string &error, const Limits &limits = Limits(),
                    const Progress &progress = Progress());

// Operator-selected HTTP(S) repository only. Caller owns curl global/network
// initialization and must run outside simulation. No redirects or credentials.
// Destination must not exist; it is committed with manifest.tpi only after all
// lengths and CRCs match. It must be beneath writable cache, never retail.
// CRC is format integrity, not authentication. No package code is executed.
bool Download(const std::string &repository, uint32_t id,
              const std::string &destination, std::string &error,
              const Limits &limits = Limits(), unsigned timeout_seconds = 120,
              const char *ca_file = nullptr, const Progress &progress = Progress());

// Prepare a complete ordered set without changing engine lookup. Existing
// invalid caches are preserved and reported, never silently overwritten.
// Caller selects a session cache root outside retail and owns network init.
// Preparation holds a matched curl global reference for its bounded operation.
bool Prepare(const std::string &repository, const std::vector<uint32_t> &ids,
             const std::string &root, std::vector<CachedPackage> &output,
             std::string &error, const Limits &limits = Limits(),
             unsigned timeout_seconds = 120, const char *ca_file = nullptr,
             const Progress &progress = Progress());
}
