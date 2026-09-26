#pragma once

#include "renegade_ttfs_factory.h"

class cGameData;
class cConnection;
class WideStringClass;
class FileFactoryListClass;

// Replaces the connecting popup's deferred notification, not WWNet transport
// or GameInitMgr loading. One original client session can be pending at a time.
class A31ClientConnect {
public:
    enum State { Idle, WaitingOptions, Ready, MissingMap, InvalidSettings,
        ConnectionLost, StartRequested, LoadingWorld, WaitingPlayer, InGame,
        ProtocolMismatch, WaitingResources, PreparingResources, ResourceFailed };
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
    static void Game_Options_Identity(unsigned map_crc, unsigned mod_crc, int hosted_game);
    static bool Is_Prepared_Map(const char *name);
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
    RenegadeTTFSFactory ResourceFactory;
    FileFactoryListClass *ResourceChain = nullptr;
    static bool Resource_Pump(void *context);
    bool Resource_Group_Matches() const;
    RenegadeTTFS::Progress ResourceProgress;
    static A31ClientConnect *Active;
};
