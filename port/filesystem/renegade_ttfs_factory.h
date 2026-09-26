#pragma once
#include "ffactory.h"
#include "renegade_ttfs.h"
#include <map>
#include <memory>

class MixFileFactoryClass;

// Explicit per-session mount beneath original FileFactoryListClass. Does not
// change campaign lookup or mount packages simply because they are downloaded.
class RenegadeTTFSFactory : public FileFactoryClass {
public:
    RenegadeTTFSFactory();
    ~RenegadeTTFSFactory() override;
    bool Mount(const std::string &cache, uint32_t id, std::string &error);
    // Preserve TT wire order: the last package wins duplicate names. Commit
    // only after all payloads validate; a failed replacement clears selection.
    bool Mount(const std::vector<RenegadeTTFS::CachedPackage> &packages,
               std::string &error, const RenegadeTTFS::Progress &progress = {});
    void Unmount();
    FileClass *Get_File(const char *name) override;
    void Return_File(FileClass *file) override;
private:
    class PayloadFactory;
    FileClass *Get_Payload(const char *name);
    std::map<std::string, std::string> Paths;
    std::unique_ptr<PayloadFactory> Payload;
    std::vector<std::unique_ptr<MixFileFactoryClass>> Archives;
};
