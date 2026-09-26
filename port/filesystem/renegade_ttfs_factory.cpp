#include "renegade_ttfs_factory.h"
#include "bufffile.h"
#include "mixfile.h"
#include <string.h>

namespace {
std::string Fold(const char *name) {
    std::string folded;
    if (!name) return folded;
    for (const unsigned char *p = reinterpret_cast<const unsigned char *>(name); *p; ++p) {
        if (*p < 32 || *p >= 127 || strchr("\\/:", *p) || folded.size() >= 240) return "";
        folded += (*p >= 'A' && *p <= 'Z') ? char(*p + 32) : char(*p);
    }
    return folded;
}
class CachedFile : public BufferedFileClass {
public:
    CachedFile(const char *path, const char *name) : BufferedFileClass(path), LogicalName(name) {}
    const char *File_Name() const override { return LogicalName.c_str(); }
    const char *Set_Name(const char *name) override {
        return Fold(name) == Fold(LogicalName.c_str()) ? LogicalName.c_str() : nullptr;
    }
    int Open(int rights = READ) override { return rights == READ ? RawFileClass::Open(READ) : 0; }
    int Open(const char *name, int rights = READ) override {
        return Set_Name(name) ? Open(rights) : 0;
    }
    bool Is_Available(int = false) override { return RawFileClass::Is_Available(false); }
    int Create() override { return 0; }
    int Delete() override { return 0; }
    int Write(const void *, int) override { return 0; }
    bool Set_Date_Time(unsigned long) override { return false; }
private:
    std::string LogicalName;
};

uint32_t LE32(const unsigned char *p) {
    return uint32_t(p[0]) | (uint32_t(p[1]) << 8) | (uint32_t(p[2]) << 16) | (uint32_t(p[3]) << 24);
}

// Download CRCs do not make an archive trustworthy. Bound the original MIX
// index allocation and every biased read before handing it to the engine.
bool Validate_Archive(FileClass &file, uint32_t &remaining,
                      const RenegadeTTFS::Progress &progress) {
    unsigned char header[12], word[4], entry[12];
    if (!file.Open(FileClass::READ)) return false;
    const int size = file.Size();
    if (size < 16 || file.Read(header, 12) != 12 || memcmp(header, "MIX1", 4)) return false;
    const uint32_t index = LE32(header + 4), names = LE32(header + 8);
    if (index < 12 || index > uint32_t(size - 4) || names < 12 || names > uint32_t(size - 4) ||
        file.Seek(int(index), SEEK_SET) != int(index) || file.Read(word, 4) != 4) return false;
    const uint32_t count = LE32(word);
    if (count > remaining || count > (uint32_t(size) - index - 4) / 12) return false;
    for (uint32_t i = 0; i < count; ++i) {
        if ((i % 1024 == 0 && !progress.Continue()) || file.Read(entry, 12) != 12) return false;
        const uint32_t offset = LE32(entry + 4), bytes = LE32(entry + 8);
        if (offset < 12 || offset > uint32_t(size) ||
            bytes > uint32_t(size) - offset) return false;
    }
    remaining -= count;
    return progress.Continue();
}
}

// Archive reads must go directly to the validated payload, never recursively
// search their own member factories (including an identically named member).
class RenegadeTTFSFactory::PayloadFactory : public FileFactoryClass {
public:
    explicit PayloadFactory(RenegadeTTFSFactory &owner) : Owner(owner) {}
    FileClass *Get_File(const char *name) override { return Owner.Get_Payload(name); }
    void Return_File(FileClass *file) override { delete file; }
private:
    RenegadeTTFSFactory &Owner;
};
RenegadeTTFSFactory::RenegadeTTFSFactory() : Payload(new PayloadFactory(*this)) {}
RenegadeTTFSFactory::~RenegadeTTFSFactory() = default;
void RenegadeTTFSFactory::Unmount() {
    Archives.clear();
    Paths.clear();
}

bool RenegadeTTFSFactory::Mount(const std::string &cache, uint32_t id, std::string &error) {
    return Mount(std::vector<RenegadeTTFS::CachedPackage>{{id, cache}}, error);
}
bool RenegadeTTFSFactory::Mount(const std::vector<RenegadeTTFS::CachedPackage> &packages,
                              std::string &error, const RenegadeTTFS::Progress &progress) {
    // A failed replacement must not leave stale server resources selected.
    Unmount();
    error.clear();
    if (packages.size() > 4096) { error = "mount package count"; return false; }
    std::map<std::string, std::string> candidate;
    std::vector<std::string> archives;
    RenegadeTTFS::Limits remaining;
    for (const auto &package : packages) {
        RenegadeTTFS::Manifest manifest;
        if (!RenegadeTTFS::Validate_Cache(package.directory, package.id, manifest, error,
                                        remaining, progress)) return false;
        for (const auto &file : manifest.files) {
            const auto name = Fold(file.name.c_str());
            candidate[name] = package.directory + "/" + file.Cache_Name();
            const auto dot = name.rfind('.');
            if (dot != std::string::npos && (name.substr(dot) == ".mix" || name.substr(dot) == ".dat" ||
                                           name.substr(dot) == ".pkg"))
                archives.push_back(name);
            remaining.total_bytes -= file.size;
        }
        remaining.file_count -= uint32_t(manifest.files.size());
    }
    if (!progress.Continue()) { error = "mount cancelled"; return false; }
    Paths.swap(candidate);
    uint32_t remaining_entries = 65536;
    for (const auto &name : archives) {
        std::unique_ptr<FileClass> file(Get_Payload(name.c_str()));
        if (!file || !Validate_Archive(*file, remaining_entries, progress)) {
            error = "invalid or oversized MIX index: " + name;
            Unmount();
            return false;
        }
        file.reset();
        std::unique_ptr<MixFileFactoryClass> archive(new MixFileFactoryClass(name.c_str(), Payload.get()));
        if (!archive->Is_Valid()) {
            error = "original MIX factory rejected: " + name;
            Unmount();
            return false;
        }
        Archives.push_back(std::move(archive));
    }
    return true;
}
FileClass *RenegadeTTFSFactory::Get_File(const char *name) {
    if (Fold(name).empty()) return nullptr;
    // TT inserts each archive at the front of the original chain, before its
    // loose resource factory. Preserve that priority, not alphabetical order.
    for (auto archive = Archives.rbegin(); archive != Archives.rend(); ++archive)
        if (FileClass *file = (*archive)->Get_File(name)) return file;
    return Get_Payload(name);
}
FileClass *RenegadeTTFSFactory::Get_Payload(const char *name) {
    auto item = Paths.find(Fold(name));
    return item == Paths.end() ? nullptr : new CachedFile(item->second.c_str(), name);
}
void RenegadeTTFSFactory::Return_File(FileClass *file) { delete file; }
