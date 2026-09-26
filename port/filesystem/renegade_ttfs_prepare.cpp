#include "renegade_ttfs.h"
#include <curl/curl.h>
#include <errno.h>
#include <set>
#include <stdio.h>
#include <sys/stat.h>
#include <time.h>

namespace RenegadeTTFS {
namespace {
uint64_t Seconds() {
    timespec now{};
    clock_gettime(CLOCK_MONOTONIC, &now);
    return uint64_t(now.tv_sec);
}
struct Preparation {
    const Progress &parent;
    uint64_t deadline;
    static bool Pump(void *opaque) {
        const auto &self = *static_cast<Preparation *>(opaque);
        return Seconds() < self.deadline && self.parent.Continue();
    }
};
struct CurlScope {
    CURLcode result = curl_global_init(CURL_GLOBAL_DEFAULT);
    ~CurlScope() { if (result == CURLE_OK) curl_global_cleanup(); }
};
}

bool Prepare(const std::string &repository, const std::vector<uint32_t> &ids,
             const std::string &root, std::vector<CachedPackage> &output,
             std::string &error, const Limits &limits, unsigned timeout_seconds,
             const char *ca_file, const Progress &progress) {
    output.clear(); error.clear();
    if (ids.size() > 4096 || root.empty() || !timeout_seconds || timeout_seconds > 600) {
        error = "invalid package set/root/deadline"; return false;
    }
    Preparation preparation{progress, Seconds() + timeout_seconds};
    Progress bounded{Preparation::Pump, &preparation};
    if (!bounded.Continue()) { error = "preparation cancelled"; return false; }
    CurlScope curl;
    if (curl.result != CURLE_OK) { error = "curl global initialization failed"; return false; }
    struct stat info{};
    if (mkdir(root.c_str(), 0700) != 0 && errno != EEXIST) {
        error = "package cache root creation failed"; return false;
    }
    if (lstat(root.c_str(), &info) != 0 || !S_ISDIR(info.st_mode)) {
        error = "package cache root is not a directory"; return false;
    }
    std::vector<CachedPackage> candidate;
    std::set<uint32_t> seen;
    Limits remaining = limits;
    for (uint32_t id : ids) {
        if (!seen.insert(id).second) continue;
        if (!bounded.Continue()) { error = "preparation cancelled/deadline"; return false; }
        char name[9];
        snprintf(name, sizeof(name), "%08x", unsigned(id));
        std::string directory = root + "/" + name;
        if (lstat(directory.c_str(), &info) != 0) {
            if (errno != ENOENT) { error = "package cache stat failed"; return false; }
            uint64_t now = Seconds();
            if (now >= preparation.deadline) { error = "preparation deadline"; return false; }
            if (!Download(repository, id, directory, error, remaining,
                          unsigned(preparation.deadline - now), ca_file, bounded)) return false;
        } else if (!S_ISDIR(info.st_mode)) {
            error = "package cache is not a directory"; return false;
        }
        Manifest manifest;
        if (!Validate_Cache(directory, id, manifest, error, remaining, bounded)) return false;
        for (const auto &file : manifest.files) remaining.total_bytes -= file.size;
        remaining.file_count -= uint32_t(manifest.files.size());
        candidate.push_back({id, directory});
    }
    if (!bounded.Continue()) { error = "preparation cancelled/deadline"; return false; }
    output.swap(candidate);
    return true;
}
}
