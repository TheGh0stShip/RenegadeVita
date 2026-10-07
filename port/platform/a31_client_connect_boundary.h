#pragma once

#include "renegade_ttfs_factory.h"
#include "renegade_tt_resources.h"
#include <memory>
#include <stdint.h>
#include <string>
#include <vector>

class cGameData;
class cConnection;
class WideStringClass;
class StringClass;
class FileFactoryListClass;

// Replaces the connecting popup's deferred notification, not WWNet transport
// or GameInitMgr loading. One original client session can be pending at a time.
class A31ClientConnect {
public:
    enum State { Idle, WaitingOptions, Ready, MissingMap, InvalidSettings,
        ConnectionLost, StartRequested, LoadingWorld, WaitingPlayer, InGame,
        ProtocolMismatch, WaitingResources, PreparingResources, ResourceFailed,
        WaitingRoundResources, PreparingRoundResources, RoundReady,
        LoadingRound, WaitingRoundPlayer };
    enum RoundDisposition { NoRound, StockOnly, RetainCurrentTT, ReplaceCurrentTT };
    A31ClientConnect();
    ~A31ClientConnect();
    bool Begin();
    void Reset();
    State Poll();
    bool Request_Start(int team, unsigned long clan);
    bool Begin_World_Load();
    bool Complete_World_Load(int team, unsigned long clan);
    void Configure_Resources(const char *cache, const char *ca_file = nullptr);
    bool Prepare_Resources(const RenegadeTTFS::Progress &progress = {});
    bool Prepare_Round_Resources(bool stock_base_available,
        const RenegadeTTFS::Progress &progress = {});
    bool Resolve_Round_Source();
    bool Commit_Round_Resources_After_Core_Shutdown();
    bool Complete_Round_Load();
    void Abort_Pending_Round();
    bool Round_Ready() const { return Status == RoundReady; }
    const char *Round_Map() const { return RoundMap.c_str(); }
    bool Round_Requires_Stock_Base() const {
        return RoundMode == StockOnly ||
            (RoundMode == RetainCurrentTT ? !ResourceOwnsLevel :
             RoundMode == ReplaceCurrentTT && !PendingOwnsLevel);
    }
    bool Round_Reuses_Current_TT() const { return RoundMode == RetainCurrentTT; }
    static void Game_Options_Identity(unsigned map_crc, unsigned mod_crc, int hosted_game);
    static bool Observe_Round_Identity(cGameData *game, unsigned map_crc,
        unsigned mod_crc, int hosted_game, bool map_cycle_over, bool stock_resolved,
        const char *stock_map, StringClass &selected_map);
    static bool Is_Prepared_Map(const char *name);
    static bool Round_Map_Validity(const char *name, bool &valid);
    static bool Game_Options(cGameData *game, bool map_valid);
    static void Connection_Ended(cConnection *connection);
    static void Unsupported_Network_Class(int class_id);
    static void Object_Creation_Failed(int class_id, int object_id);
    static bool Protocol_Failed();
    static void Identity_Failed();
    static void Invalid_Game_Options();
    static void Packet_Decode_Failed(int object_id, const char *stage);
    static void Server_Message(const WideStringClass &message);
private:
    A31ClientConnect(const A31ClientConnect &) = delete;
    A31ClientConnect &operator=(const A31ClientConnect &) = delete;
    bool Matches_Session() const;
    State Status;
    cGameData *Game;
    cConnection *Connection;
    unsigned MessageCount;
    unsigned MapCRC = 0, ModCRC = 0, ResourceGroupId = 0;
    int ResourceHostedGame = -1;
    bool HaveMapIdentity = false, ResourcesMounted = false, ResourceOwnsLevel = false;
    std::string ResourceCache, CertificateFile, ResourceMap, ResourceGroupName;
    std::vector<uint32_t> ResourcePackages;
    // Heap ownership keeps the published FileFactoryList pointer stable when a
    // validated generation is later promoted from pending to current.
    std::unique_ptr<RenegadeTTFSFactory> ResourceFactory;
    RoundDisposition RoundMode = NoRound;
    unsigned RoundMapCRC = 0, RoundModCRC = 0, RoundGroupId = 0;
    uint32_t RoundObservedResourceGeneration = 0;
    int RoundHostedGame = -1;
    bool HaveRoundIdentity = false, PendingOwnsLevel = false;
    bool PendingStockBaseAvailable = false;
    std::string RoundMap, RoundStockMap, RoundGroupName;
    std::vector<uint32_t> RoundPackages;
    std::vector<RenegadeTTResources::Group> RoundOfferedGroups;
    std::unique_ptr<RenegadeTTFSFactory> PendingResourceFactory;
    FileFactoryListClass *ResourceChain = nullptr;
    static bool Resource_Pump(void *context);
    bool Resource_Group_Matches() const;
    bool Round_Resource_Group_Matches() const;
    RenegadeTTFS::Progress ResourceProgress;
    static A31ClientConnect *Active;
};
