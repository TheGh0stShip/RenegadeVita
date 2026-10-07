#include "renegade_ttfs.h"

#include <curl/curl.h>
#include <zlib.h>
#include <fcntl.h>
#include <sys/stat.h>
#include <unistd.h>
#include <stdio.h>
#include <time.h>
#include <limits>

namespace {
// Vita sceIoRename refuses an existing destination. Same contract as
// Renegade_Replace_File in renegade_file_factory.cpp, kept local so the TTFS
// unit (and its link probe) does not depend on the file factory.
bool Replace_Manifest(const char *source, const char *destination)
{
    if (rename(source, destination) == 0) return true;
    char previous[1040];
    const int length = snprintf(previous, sizeof(previous), "%s.previous", destination);
    if (length <= 0 || length >= static_cast<int>(sizeof(previous))) return false;
    remove(previous);
    if (rename(destination, previous) != 0) return false;
    if (rename(source, destination) != 0) {
        (void)rename(previous, destination);
        return false;
    }
    remove(previous);
    return true;
}
}
#include <errno.h>
#include <new>

namespace RenegadeTTFS {
namespace {
struct Sink {
    std::vector<unsigned char> *memory;
    int fd;
    size_t limit, received = 0;
    uLong crc = crc32(0, Z_NULL, 0);
};
int Transfer_Progress(void *opaque, curl_off_t, curl_off_t, curl_off_t, curl_off_t) {
    return static_cast<const Progress *>(opaque)->Continue() ? 0 : 1;
}
size_t Write(char *data, size_t size, size_t count, void *opaque) {
    Sink &sink = *static_cast<Sink *>(opaque);
    if (size && count > std::numeric_limits<size_t>::max() / size) return 0;
    size_t bytes = size * count;
    if (bytes > sink.limit - sink.received) return 0;
    if (sink.fd >= 0) {
        size_t written = 0;
        while (written < bytes) {
            ssize_t n = write(sink.fd, data + written, bytes - written);
            if (n < 0 && errno == EINTR) continue;
            if (n <= 0) return 0;
            written += size_t(n);
        }
    }
    if (sink.memory) {
#if defined(__cpp_exceptions)
        try { sink.memory->insert(sink.memory->end(), data, data + bytes); }
        catch (const std::bad_alloc &) { return 0; }
#else
        sink.memory->insert(sink.memory->end(), data, data + bytes);
#endif
    }
    sink.crc = crc32(sink.crc, reinterpret_cast<Bytef *>(data), static_cast<uInt>(bytes));
    sink.received += bytes;
    return bytes;
}
uint64_t Milliseconds() {
    timespec now{};
    clock_gettime(CLOCK_MONOTONIC, &now);
    return uint64_t(now.tv_sec) * 1000 + uint64_t(now.tv_nsec) / 1000000;
}
template <class T>
bool Option(CURL *curl, CURLoption option, T value, std::string &error) {
    CURLcode code = curl_easy_setopt(curl, option, value);
    if (code == CURLE_OK) return true;
    error = "curl option " + std::to_string(int(option)) + ": " + curl_easy_strerror(code);
    return false;
}
bool Get(CURL *curl, const std::string &url, Sink &sink, uint64_t deadline, std::string &error) {
    uint64_t now = Milliseconds();
    if (now >= deadline) { error = "package deadline exceeded"; return false; }
    if (!Option(curl, CURLOPT_URL, url.c_str(), error) ||
        !Option(curl, CURLOPT_WRITEFUNCTION, Write, error) ||
        !Option(curl, CURLOPT_WRITEDATA, &sink, error) ||
        !Option(curl, CURLOPT_TIMEOUT_MS, long(deadline - now), error) ||
        !Option(curl, CURLOPT_MAXFILESIZE_LARGE, curl_off_t(sink.limit), error)) return false;
    CURLcode code = curl_easy_perform(curl);
    long status = 0;
    CURLcode info = curl_easy_getinfo(curl, CURLINFO_RESPONSE_CODE, &status);
    if (code != CURLE_OK || info != CURLE_OK || status != 200) {
        error = url + ": HTTP " + std::to_string(status) + ": " + curl_easy_strerror(code);
        return false;
    }
    return true;
}
}

bool Download(const std::string &repository, uint32_t id,
              const std::string &destination, std::string &error,
              const Limits &limits, unsigned timeout_seconds, const char *ca_file,
              const Progress &progress) {
    error.clear();
    if (!progress.Continue()) { error = "download cancelled"; return false; }
    for (unsigned char c : repository) {
        if (c <= 32 || c >= 127) { error = "repository URL requires escaped ASCII"; return false; }
    }
    if (timeout_seconds == 0 || timeout_seconds > 600 || repository.size() > 2048 ||
        (repository.compare(0, 7, "http://") && repository.compare(0, 8, "https://")) ||
        repository.find_first_of("?#@\\\r\n\t ") != std::string::npos) {
        error = "invalid operator repository URL/timeout"; return false;
    }
    CURL *curl = curl_easy_init();
    if (!curl) { error = "curl initialization failed"; return false; }
    // An isolated new cache is never visible to the engine until committed.
    if (mkdir(destination.c_str(), 0700) != 0) {
        curl_easy_cleanup(curl); error = "cache must be a new writable directory"; return false;
    }
    std::vector<std::string> created;
    auto finish = [&](bool success) {
        curl_easy_cleanup(curl);
        if (!success) {
            for (const std::string &path : created) unlink(path.c_str());
            rmdir(destination.c_str());
        }
        return success;
    };
    // Do not inherit host proxy credentials for a server-selected URL.
    if (!Option(curl, CURLOPT_FOLLOWLOCATION, 0L, error) ||
        !Option(curl, CURLOPT_PROTOCOLS_STR, "http,https", error) ||
        !Option(curl, CURLOPT_SSL_VERIFYPEER, 1L, error) ||
        !Option(curl, CURLOPT_SSL_VERIFYHOST, 2L, error) ||
        !Option(curl, CURLOPT_SSLVERSION, long(CURL_SSLVERSION_TLSv1_2), error) ||
        !Option(curl, CURLOPT_CONNECTTIMEOUT, 10L, error) ||
        !Option(curl, CURLOPT_NOSIGNAL, 1L, error) ||
        !Option(curl, CURLOPT_NOPROGRESS, 0L, error) ||
        !Option(curl, CURLOPT_XFERINFOFUNCTION, Transfer_Progress, error) ||
        !Option(curl, CURLOPT_XFERINFODATA, &progress, error) ||
        !Option(curl, CURLOPT_FAILONERROR, 1L, error) ||
        !Option(curl, CURLOPT_PROXY, "", error) ||
        // Repository compatibility header from pinned b9000's WinINet owner.
        // RenCorner rejects both our custom agent and an appended port suffix.
        // This identifies the TTFS wire client, not Vita's build/gameplay status.
        !Option(curl, CURLOPT_USERAGENT, "TT/4.80.9000-20252502", error))
        return finish(false);
    if (ca_file && !Option(curl, CURLOPT_CAINFO, ca_file, error)) return finish(false);
    std::string base = repository;
    while (!base.empty() && base.back() == '/') base.pop_back();
    uint64_t deadline = Milliseconds() + uint64_t(timeout_seconds) * 1000;
    char manifest_name[32];
    snprintf(manifest_name, sizeof(manifest_name), "/packages/%08x.tpi", unsigned(id));
    std::vector<unsigned char> bytes;
    Sink manifest_sink{&bytes, -1, limits.manifest_bytes};
    if (!Get(curl, base + manifest_name, manifest_sink, deadline, error)) return finish(false);
    Manifest manifest;
    if (!Parse(bytes.data(), bytes.size(), id, manifest, error, limits)) return finish(false);
    for (const File &file : manifest.files) {
        const std::string name = file.Cache_Name();
        char *escaped = curl_easy_escape(curl, name.c_str(), int(name.size()));
        if (!escaped) { error = "URL allocation failed"; return finish(false); }
        std::string url = base + "/files/" + escaped;
        curl_free(escaped);
        std::string path = destination + "/" + name;
        int fd = open(path.c_str(), O_WRONLY | O_CREAT | O_EXCL, 0600);
        if (fd < 0) { error = "cache file creation failed: " + name; return finish(false); }
        created.push_back(path);
        Sink sink{nullptr, fd, file.size};
        bool ok = Get(curl, url, sink, deadline, error);
        if (close(fd) != 0) { error = "cache close failed: " + name; ok = false; }
        if (!ok) return finish(false);
        if (sink.received != file.size || uint32_t(sink.crc) != file.crc) {
            error = "payload length/CRC mismatch: " + name; return finish(false);
        }
    }
    std::string pending = destination + "/manifest.part";
    if (!progress.Continue()) { error = "download cancelled"; return finish(false); }
    created.push_back(pending);
    FILE *output = fopen(pending.c_str(), "wb");
    if (!output) { error = "manifest cache creation failed"; return finish(false); }
    bool ok = fwrite(bytes.data(), 1, bytes.size(), output) == bytes.size();
    if (fclose(output) != 0) ok = false;
    if (!ok || !Replace_Manifest(pending.c_str(), (destination + "/manifest.tpi").c_str())) {
        error = "manifest cache commit failed"; return finish(false);
    }
    return finish(true);
}
}
