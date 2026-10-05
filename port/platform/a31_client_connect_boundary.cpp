#include "a31_client_connect_boundary.h"
#include "a4_frontend_lifecycle_boundary.h"
#include "cnetwork.h"
#include "connect.h"
#include "gamedata.h"
#include "gameinitmgr.h"
#include "gametype.h"
#include "campaign.h"
#include "bioevent.h"
#include "combat.h"
#include "soldier.h"
#include "player.h"
#include "networkobjectmgr.h"
#include <stdio.h>
#include <string.h>
#include "renegade_client_message.h"
#include "ffactorylist.h"
#include "realcrc.h"
#include "packetmgr.h"
#include "wwfile.h"
#include "miscutil.h"
#include "renegade_client_effects.h"
#include "a35_level_load_status.h"
#include <new>

extern bool g_is_loading;

bool Renegade_Client_Disables_Camera_Shake()
{
    return Renegade_Client_Uses_TT_Replication() &&
        cNetwork::PClientConnection->Get_TT_Options_Flag();
}

bool Renegade_Client_Uses_TT_Replication()
{
    cConnection *connection = cNetwork::PClientConnection;
    return !IS_SOLOPLAY && cNetwork::I_Am_Only_Client() && connection &&
        !connection->Is_Destroy() && connection->Has_TT_Client_Greeting();
}

A31ClientConnect *A31ClientConnect::Active = nullptr;
A31ClientConnect::A31ClientConnect() : Status(Idle), Game(nullptr), Connection(nullptr),
    MessageCount(0), ResourceFactory(nullptr) {}
A31ClientConnect::~A31ClientConnect() { Reset(); }

void A31ClientConnect::Reset()
{
	Abort_Pending_Round();
    if (ResourceChain && ResourceChain == FileFactoryListClass::Get_Instance() &&
        ResourceChain->Peek_Temp_FileFactory() == ResourceFactory.get())
        ResourceChain->Remove_Temp_FileFactory();
    ResourceChain = nullptr;
    if (ResourceFactory) ResourceFactory->Unmount();
    ResourcesMounted = HaveMapIdentity = ResourceOwnsLevel = false;
    MapCRC = ModCRC = ResourceGroupId = 0;
    ResourceHostedGame = -1;
    ResourceCache.clear(); CertificateFile.clear(); ResourceMap.clear(); ResourceGroupName.clear();
    ResourcePackages.clear();
    ResourceProgress = {};
    if (Active == this) Active = nullptr;
    Game = nullptr;
    Connection = nullptr;
    Status = Idle;
    MessageCount = 0;
}

bool A31ClientConnect::Begin()
{
#if RENEGADE_VITA_M00_DEMO
    return false;
#endif
    if (Active || !PTheGameData || !cNetwork::I_Am_Only_Client() || IS_SOLOPLAY)
        return false;
    if (!ResourceFactory) {
        ResourceFactory.reset(new (std::nothrow) RenegadeTTFSFactory);
        if (!ResourceFactory) return false;
    }
    Game = PTheGameData;
    Connection = cNetwork::PClientConnection;
    Status = WaitingOptions;
    Active = this;
    return true;
}

bool A31ClientConnect::Matches_Session() const
{
    return Active == this && Game == PTheGameData && Connection &&
        Connection == cNetwork::PClientConnection && cNetwork::I_Am_Only_Client() && !IS_SOLOPLAY;
}

A31ClientConnect::State A31ClientConnect::Poll()
{
    if ((Status == WaitingOptions || Status == Ready || Status == StartRequested ||
        Status == LoadingWorld || Status == WaitingPlayer || Status == InGame ||
        Status == WaitingResources || Status == PreparingResources ||
        Status == WaitingRoundResources || Status == PreparingRoundResources ||
        Status == RoundReady || Status == LoadingRound || Status == WaitingRoundPlayer) &&
        (!Matches_Session() || Connection->Is_Destroy())) Status = ConnectionLost;
    if (Status == Ready && !ResourcesMounted && !ResourceCache.empty() &&
        Connection->Get_TT_Server_Info().Present &&
        (!Connection->Get_TT_Resources().Get_Groups().empty() ||
         Connection->Get_TT_Resources().Get_Remaining())) Status = WaitingResources;
    if ((Status == Ready || Status == StartRequested) && ResourcesMounted && !Resource_Group_Matches()) {
        Status = ResourceFailed;
        fprintf(stderr, "client-connect: selected resource group changed before world load\n");
    }
    if ((Status == WaitingRoundResources || Status == PreparingRoundResources ||
        Status == RoundReady) && HaveRoundIdentity && Connection &&
        Connection->Get_TT_Resources().Get_Generation() != RoundObservedResourceGeneration) {
        Status = ResourceFailed;
        fprintf(stderr, "client-connect: next-round resource offer mutated after win identity\n");
    }
    if (Status == WaitingPlayer) {
        cPlayer *player = cNetwork::Get_My_Player_Object();
        SoldierGameObj *star = CombatManager::Get_The_Star();
        if (player && star && player->Get_GameObj() == star &&
            star->Get_Control_Owner() == cNetwork::Get_My_Id()) Status = InGame;
    }
    if (Status == WaitingRoundPlayer) {
        cPlayer *player = cNetwork::Get_My_Player_Object();
        SoldierGameObj *star = CombatManager::Get_The_Star();
        if (player && player->Get_Is_Active().Is_True() &&
            player->Get_Is_In_Game().Is_True() && star &&
            player->Get_GameObj() == star && star->Get_Player_Data() == player &&
            star->Get_Control_Owner() == cNetwork::Get_My_Id()) Status = InGame;
    }
    return Status;
}

bool A31ClientConnect::Begin_World_Load()
{
    if (Poll() != StartRequested || !Connection->Is_Established()) return false;
    Status = LoadingWorld;
    return true;
}

bool A31ClientConnect::Complete_World_Load(int team, unsigned long clan)
{
    if (Poll() != LoadingWorld || g_is_loading || !CombatManager::Get_Scene()) return false;
    // Initial join follows GameInitMgr::Transmit_Player_Data after Load_Level.
    // The server's BioEvent handler alone creates the player and soldier.
    cBioEvent *bio = new cBioEvent;
    bio->Init(team, clan);
    cNetwork::Flush();
    NetworkObjectMgrClass::Delete_Pending();
    Status = WaitingPlayer;
    return true;
}

void A31ClientConnect::Connection_Ended(cConnection *connection)
{
    if (Active && Active->Connection == connection) {
        Active->Status = ConnectionLost;
        Active->Connection = nullptr;
    }
}

void A31ClientConnect::Unsupported_Network_Class(int class_id)
{
    fprintf(stderr, "client-connect: unsupported network class=%d; join/gameplay stopped\n", class_id);
    if (Active && Active->Matches_Session()) Active->Status = ProtocolMismatch;
}

void A31ClientConnect::Identity_Failed()
{
    fprintf(stderr, "client-connect: identity unavailable or invalid; join stopped\n");
    if (Active && Active->Matches_Session()) Active->Status = ProtocolMismatch;
}

bool A31ClientConnect::Protocol_Failed()
{
    return Active && Active->Status == ProtocolMismatch;
}

void A31ClientConnect::Invalid_Game_Options()
{
    fprintf(stderr, "client-connect: invalid game options layout; session stopped\n");
    if (Active && Active->Matches_Session()) Active->Status = ProtocolMismatch;
    if (cNetwork::I_Am_Only_Client()) cNetwork::PClientConnection->Abort_Client();
}

void A31ClientConnect::Object_Creation_Failed(int class_id, int object_id)
{
    fprintf(stderr, "client-connect: object creation failed class=%d object=%d; session stopped\n",
        class_id, object_id);
    if (Active && Active->Matches_Session()) Active->Status = ProtocolMismatch;
}

void A31ClientConnect::Packet_Decode_Failed(int object_id, const char *stage)
{
    fprintf(stderr, "client-connect: invalid replication object=%d stage=%s; session stopped\n",
        object_id, stage);
    if (Active && Active->Matches_Session()) Active->Status = ProtocolMismatch;
    if (cNetwork::I_Am_Only_Client()) cNetwork::PClientConnection->Abort_Client();
}

void A31ClientConnect::Server_Message(const WideStringClass &message)
{
    if (!Active || !Active->Matches_Session() || Active->Status != WaitingOptions ||
        Active->MessageCount >= 4) return;
    ++Active->MessageCount;
    StringClass text;
    message.Convert_To(text);
    char safe[512];
    snprintf(safe, sizeof(safe), "%s", text.Peek_Buffer());
    Renegade_Redact_Admission_Message(safe);
    fprintf(stderr, "client-connect: server admission message: %s\n", safe);
}

bool A31ClientConnect::Game_Options(cGameData *game, bool map_valid)
{
    if (!Active || !Active->Matches_Session() || Active->Game != game ||
        Active->Status != WaitingOptions) return false;
    const auto &tt = Active->Connection->Get_TT_Server_Info();
    const auto &resources = Active->Connection->Get_TT_Resources();
    Active->Status = tt.Present && !Active->ResourceCache.empty() &&
        (!map_valid || !resources.Get_Groups().empty() || resources.Get_Remaining()) ?
        WaitingResources : (map_valid ? Ready : MissingMap);
    fprintf(stderr, "client-connect: server options %s map=%s\n",
        map_valid ? "ready" : "missing-map", game->Get_Map_Name().Peek_Buffer());
    return true;
}

void A31ClientConnect::Configure_Resources(const char *cache, const char *ca_file)
{
    if (Status != WaitingOptions || !cache || !*cache) return;
    ResourceCache = cache;
    CertificateFile = ca_file ? ca_file : "";
}

void A31ClientConnect::Game_Options_Identity(unsigned map_crc, unsigned mod_crc, int hosted_game)
{
    if (!Active || !Active->Matches_Session() || Active->Status != WaitingOptions) return;
    Active->MapCRC = map_crc;
    Active->ModCRC = mod_crc;
    Active->HaveMapIdentity = true;
    Active->ResourceHostedGame = hosted_game;
}

bool A31ClientConnect::Observe_Round_Identity(cGameData *game, unsigned map_crc,
    unsigned mod_crc, int hosted_game, bool map_cycle_over, bool stock_resolved,
    const char *stock_map, StringClass &selected_map)
{
    if (!Active || !Active->Matches_Session() || Active->Game != game) return false;
    selected_map = "";
    if (map_cycle_over) {
        Active->Abort_Pending_Round();
        return true;
    }
    const State observed_state = Active->Poll();
    if (observed_state != InGame && !Active->HaveRoundIdentity) {
        fprintf(stderr, "client-connect: next-round identity arrived in invalid state=%d\n",
            int(observed_state));
        Active->Status = ResourceFailed;
        return true;
    }

    if (Active->HaveRoundIdentity) {
        if (Active->RoundMapCRC == map_crc && Active->RoundModCRC == mod_crc &&
            Active->RoundHostedGame == hosted_game) {
            if (!Active->RoundMap.empty()) selected_map = Active->RoundMap.c_str();
            return true;
        }
        fprintf(stderr, "client-connect: conflicting next-round identity hosted=%d crc=%08x/%08x\n",
            hosted_game, map_crc, mod_crc);
        Active->Status = ResourceFailed;
        return true;
    }

    Active->HaveRoundIdentity = true;
    Active->RoundMapCRC = map_crc;
    Active->RoundModCRC = mod_crc;
    Active->RoundHostedGame = hosted_game;
    Active->RoundMode = NoRound;
    Active->RoundMap.clear();
    Active->RoundStockMap.clear();
    Active->RoundGroupId = 0;
    Active->RoundObservedResourceGeneration =
        Active->Connection->Get_TT_Resources().Get_Generation();
    Active->RoundOfferedGroups = Active->Connection->Get_TT_Resources().Get_Groups();
    Active->RoundGroupName.clear();
    Active->RoundPackages.clear();
    Active->PendingOwnsLevel = false;
    Active->PendingStockBaseAvailable = false;

    // Native Direct-IP does not publish original .pkg providers. Claim the
    // event even on rejection so Set_Mod_Name cannot adopt and later delete
    // the A31-owned temporary provider.
    if (mod_crc != 0) {
        fprintf(stderr, "client-connect: unsupported next-round mod crc=%08x\n", mod_crc);
        Active->Status = ResourceFailed;
        return true;
    }

    char archive[96];
    if (stock_resolved && stock_map != nullptr &&
        A4_Frontend_Resolve_Skirmish_Archive(stock_map, archive, sizeof(archive)) &&
        uint32_t(CRC_Stringi(archive)) == map_crc) {
        Active->RoundStockMap = archive;
        selected_map = archive;
    }

    // Reliable packets before cWin have already been serviced. Treat this
    // frozen session offer as the round boundary and fail if it mutates before
    // publication; Remaining still describes only one group's package tail.
    Active->Status = WaitingRoundResources;
    if (Active->Connection->Get_TT_Resources().Get_Remaining()) {
        Active->Status = ResourceFailed;
        return true;
    }
    Active->Resolve_Round_Source();
    if (!Active->RoundMap.empty()) selected_map = Active->RoundMap.c_str();
    return true;
}

bool A31ClientConnect::Resolve_Round_Source()
{
    if (Poll() != WaitingRoundResources || !HaveRoundIdentity || RoundModCRC != 0)
        return false;
    const RenegadeTTResources::Group *group_match = nullptr;
    std::string group_map;
    for (const auto &group : RoundOfferedGroups) {
        std::string candidate = group.Name;
        if (candidate.size() < 4 ||
            stricmp(candidate.c_str() + candidate.size() - 4, ".mix"))
            candidate += ".mix";
        char archive[96];
        if (!A4_Frontend_Resolve_Skirmish_Archive(candidate.c_str(), archive,
            sizeof(archive)) || uint32_t(CRC_Stringi(archive)) != RoundMapCRC) continue;
        if (group_match != nullptr) {
            fprintf(stderr, "client-connect: ambiguous next-round TT groups crc=%08x\n",
                RoundMapCRC);
            Status = ResourceFailed;
            return false;
        }
        group_match = &group;
        group_map = archive;
    }

    if (group_match != nullptr) {
        RoundMap = group_map;
        RoundGroupId = group_match->Id;
        RoundGroupName = group_match->Name;
        RoundPackages = group_match->Packages;
        const bool retain_current = ResourcesMounted && MapCRC == RoundMapCRC &&
            ResourceGroupId == group_match->Id &&
            ResourceGroupName == group_match->Name &&
            ResourcePackages == group_match->Packages &&
            !stricmp(ResourceMap.c_str(), group_map.c_str());
        RoundMode = retain_current ? RetainCurrentTT : ReplaceCurrentTT;
        Status = retain_current ? RoundReady : WaitingRoundResources;
        Game->Set_Map_Name(RoundMap.c_str());
        return true;
    }

    if (!RoundStockMap.empty()) {
        RoundMap = RoundStockMap;
        RoundMode = StockOnly;
        Status = RoundReady;
        Game->Set_Map_Name(RoundMap.c_str());
        return true;
    }

    fprintf(stderr, "client-connect: unresolved next-round map crc=%08x\n", RoundMapCRC);
    Status = ResourceFailed;
    return false;
}

bool A31ClientConnect::Resource_Group_Matches() const
{
    const auto &groups = Connection->Get_TT_Resources().Get_Groups();
    for (const auto &group : groups)
        if (group.Id == ResourceGroupId)
            return group.Name == ResourceGroupName && group.Packages == ResourcePackages;
    return false;
}

bool A31ClientConnect::Round_Resource_Group_Matches() const
{
    if (!Connection || !HaveRoundIdentity) return false;
    const auto &groups = Connection->Get_TT_Resources().Get_Groups();
    for (const auto &group : groups)
        if (group.Id == RoundGroupId)
            return group.Name == RoundGroupName && group.Packages == RoundPackages;
    return false;
}

bool A31ClientConnect::Resource_Pump(void *context)
{
    auto &self = *static_cast<A31ClientConnect *>(context);
    const State state = self.Poll();
    if ((state != PreparingResources && state != PreparingRoundResources) ||
        !self.ResourceProgress.Continue()) return false;
    // No world update or recursive loader: retain the original admission pump
    // while curl/CRC work yields on this same main thread.
    self.Connection->Service_Read();
    const State serviced = self.Poll();
    if (serviced != PreparingResources && serviced != PreparingRoundResources) return false;
    self.Connection->Service_Send(true);
    PacketManager.Flush(true);
    NetworkObjectMgrClass::Delete_Pending();
    const State after = self.Poll();
    return (after == PreparingResources && self.Resource_Group_Matches()) ||
        (after == PreparingRoundResources && self.Round_Resource_Group_Matches());
}

bool A31ClientConnect::Prepare_Resources(const RenegadeTTFS::Progress &progress)
{
#if RENEGADE_VITA_M00_DEMO
    (void)progress;
    return false;
#else
    if (Poll() != WaitingResources) return false;
    const auto &resources = Connection->Get_TT_Resources();
    if (resources.Get_Remaining() || resources.Get_Groups().empty()) return false;
    const RenegadeTTResources::Group *selected = nullptr;
    std::string selected_map;
    // Live TT offers use the level basename; original options checksum the
    // archive filename. Resolve that boundary, never a package ID or list order.
    for (const auto &offered : resources.Get_Groups()) {
        std::string candidate = offered.Name;
        if (candidate.size() < 4 || stricmp(candidate.c_str() + candidate.size() - 4, ".mix"))
            candidate += ".mix";
        char archive[96];
        if (!A4_Frontend_Resolve_Skirmish_Archive(candidate.c_str(), archive, sizeof(archive)) ||
            uint32_t(CRC_Stringi(archive)) != MapCRC) continue;
        if (selected) {
            fprintf(stderr, "client-connect: ambiguous resource groups for map checksum=%08x\n", MapCRC);
            Status = ResourceFailed;
            return false;
        }
        selected = &offered;
        selected_map = archive;
    }
    if (!HaveMapIdentity || ModCRC != 0 ||
        !selected ||
        !FileFactoryListClass::Get_Instance() ||
        FileFactoryListClass::Get_Instance()->Peek_Temp_FileFactory()) {
        fprintf(stderr, "client-connect: resource group does not match map options crc=%08x mod=%08x\n", MapCRC, ModCRC);
        Status = ResourceFailed;
        return false;
    }
    const auto group = *selected;
    ResourceGroupId = group.Id;
    ResourceGroupName = group.Name;
    ResourceMap = selected_map;
    ResourcePackages = group.Packages;
    ResourceProgress = progress;
    Status = PreparingResources;
    RenegadeTTFS::Progress pump{Resource_Pump, this};
    std::vector<RenegadeTTFS::CachedPackage> packages;
    std::string error;
    bool ok = RenegadeTTFS::Prepare(Connection->Get_TT_Server_Info().Repository,
        group.Packages, ResourceCache, packages, error, RenegadeTTFS::Limits(), 600,
        CertificateFile.empty() ? nullptr : CertificateFile.c_str(), pump);
    if (ok) ok = ResourceFactory->Mount(packages, error, pump);
    // Packages may contain flat files or original MIX archives. Require the
    // original level pair through their factory before changing game settings.
    std::string level = ResourceMap.substr(0, ResourceMap.size() - 4);
    bool level_pair = true;
    for (const char *extension : {".ldd", ".lsd"}) {
        if (!ok) break;
        FileClass *file = ResourceFactory->Get_File((level + extension).c_str());
        level_pair = file && file->Is_Available() && level_pair;
        if (file) ResourceFactory->Return_File(file);
    }
    // A server may provide only overrides for a stock MIX. In that case the
    // normal original archive still supplies the level, with TT files first.
    if (ok && !level_pair && !cMiscUtil::File_Exists(ResourceMap.c_str())) {
        error = "resource set is missing original level files";
        ok = false;
    }
    if (ok) ok = Resource_Pump(this);
    ResourceProgress = {};
    if (!ok) {
        ResourceFactory->Unmount();
        if (Status == PreparingResources) Status = ResourceFailed;
        fprintf(stderr, "client-connect: resource preparation failed: %.512s\n", error.c_str());
        return false;
    }
    ResourceChain = FileFactoryListClass::Get_Instance();
    // Pre_Load_Game resets the normal search index. The original temporary
    // override remains first across that reset and is detached with this join.
    ResourceChain->Add_Temp_FileFactory(ResourceFactory.get());
    ResourcesMounted = true;
    ResourceOwnsLevel = level_pair;
    Game->Set_Map_Name(ResourceMap.c_str());
    Game->Set_Hosted_Game_Number(ResourceHostedGame);
    Status = Ready;
    fprintf(stderr, "client-connect: resource set mounted map=%s packages=%u; world not loaded\n",
        ResourceMap.c_str(), unsigned(packages.size()));
    return true;
#endif
}

bool A31ClientConnect::Prepare_Round_Resources(bool stock_base_available,
    const RenegadeTTFS::Progress &progress)
{
#if RENEGADE_VITA_M00_DEMO
    (void)stock_base_available;
    (void)progress;
    return false;
#else
    if (Poll() != WaitingRoundResources || RoundMode != ReplaceCurrentTT ||
        !Round_Resource_Group_Matches()) return false;
    const auto &resources = Connection->Get_TT_Resources();
    if (resources.Get_Remaining()) return false;
    const RenegadeTTResources::Group *selected = nullptr;
    for (const auto &group : resources.Get_Groups()) {
        if (group.Id == RoundGroupId && group.Name == RoundGroupName &&
            group.Packages == RoundPackages) {
            selected = &group;
            break;
        }
    }
    if (selected == nullptr) {
        Status = ResourceFailed;
        return false;
    }
    const auto group = *selected;

    PendingResourceFactory.reset(new (std::nothrow) RenegadeTTFSFactory);
    if (!PendingResourceFactory) {
        Status = ResourceFailed;
        return false;
    }
    ResourceProgress = progress;
    Status = PreparingRoundResources;
    RenegadeTTFS::Progress pump{Resource_Pump, this};
    std::vector<RenegadeTTFS::CachedPackage> packages;
    std::string error;
    bool ok = RenegadeTTFS::Prepare(Connection->Get_TT_Server_Info().Repository,
        group.Packages, ResourceCache, packages, error, RenegadeTTFS::Limits(), 600,
        CertificateFile.empty() ? nullptr : CertificateFile.c_str(), pump);
    if (ok) ok = PendingResourceFactory->Mount(packages, error, pump);
    std::string level = RoundMap.substr(0, RoundMap.size() - 4);
    bool level_pair = true;
    for (const char *extension : {".ldd", ".lsd"}) {
        if (!ok) break;
        FileClass *file = PendingResourceFactory->Get_File((level + extension).c_str());
        level_pair = file && file->Is_Available() && level_pair;
        if (file) PendingResourceFactory->Return_File(file);
    }
    if (ok && !level_pair && !stock_base_available) {
        error = "next resource set is missing original level files and stock base";
        ok = false;
    }
    if (ok) ok = Resource_Pump(this);
    ResourceProgress = {};
    if (!ok) {
        PendingResourceFactory->Unmount();
        PendingResourceFactory.reset();
        if (Status == PreparingRoundResources) Status = ResourceFailed;
        fprintf(stderr, "client-connect: next-round resource preparation failed: %.512s\n",
            error.c_str());
        return false;
    }
    PendingOwnsLevel = level_pair;
    PendingStockBaseAvailable = stock_base_available;
    Status = RoundReady;
    fprintf(stderr, "client-connect: next-round resources prepared map=%s packages=%u owns_level=%d; unpublished\n",
        RoundMap.c_str(), unsigned(packages.size()), PendingOwnsLevel ? 1 : 0);
    return true;
#endif
}

bool A31ClientConnect::Commit_Round_Resources_After_Core_Shutdown()
{
    if (Status != RoundReady || !HaveRoundIdentity || RoundMode == NoRound) {
        A35_Level_Load_Record_Failure(A35_LOAD_RESOURCE_PROVIDER_FAILED);
        return false;
    }
    if ((RoundMode == RetainCurrentTT || RoundMode == ReplaceCurrentTT) &&
        !Round_Resource_Group_Matches()) {
        A35_Level_Load_Record_Failure(A35_LOAD_RESOURCE_PROVIDER_FAILED);
        return false;
    }
    FileFactoryListClass *chain = FileFactoryListClass::Get_Instance();
    if (chain == nullptr ||
        (ResourcesMounted && chain->Peek_Temp_FileFactory() != ResourceFactory.get()) ||
        (!ResourcesMounted && chain->Peek_Temp_FileFactory() != nullptr)) {
        A35_Level_Load_Record_Failure(A35_LOAD_RESOURCE_PROVIDER_FAILED);
        return false;
    }

    if (RoundMode == ReplaceCurrentTT && !PendingResourceFactory) {
        A35_Level_Load_Record_Failure(A35_LOAD_RESOURCE_PROVIDER_FAILED);
        return false;
    }
    if (RoundMode == StockOnly || RoundMode == ReplaceCurrentTT) {
        if (ResourcesMounted) chain->Remove_Temp_FileFactory();
        if (ResourceFactory) ResourceFactory->Unmount();
        ResourcesMounted = false;
        ResourceOwnsLevel = false;
    }
    if (RoundMode == ReplaceCurrentTT) {
        ResourceFactory.swap(PendingResourceFactory);
        MapCRC = RoundMapCRC;
        ModCRC = 0;
        ResourceGroupId = RoundGroupId;
        ResourceHostedGame = RoundHostedGame;
        ResourceGroupName = RoundGroupName;
        ResourceMap = RoundMap;
        ResourcePackages = RoundPackages;
        ResourceOwnsLevel = PendingOwnsLevel;
        chain->Add_Temp_FileFactory(ResourceFactory.get());
        ResourceChain = chain;
        ResourcesMounted = true;
    } else if (RoundMode == StockOnly) {
        MapCRC = RoundMapCRC;
        ModCRC = 0;
        ResourceGroupId = 0;
        ResourceHostedGame = RoundHostedGame;
        ResourceGroupName.clear();
        ResourceMap.clear();
        ResourcePackages.clear();
        ResourceChain = nullptr;
    } else if (RoundMode == RetainCurrentTT) {
        MapCRC = RoundMapCRC;
        ResourceHostedGame = RoundHostedGame;
        ResourceMap = RoundMap;
    }
    if (PendingResourceFactory) PendingResourceFactory->Unmount();
    PendingResourceFactory.reset();
    PendingOwnsLevel = false;
    PendingStockBaseAvailable = false;
    Status = LoadingRound;
    return true;
}

bool A31ClientConnect::Complete_Round_Load()
{
    if (Status != LoadingRound) return false;
    RoundMode = NoRound;
    RoundMapCRC = RoundModCRC = RoundGroupId = 0;
    RoundObservedResourceGeneration = 0;
    RoundHostedGame = -1;
    HaveRoundIdentity = false;
    PendingOwnsLevel = false;
    PendingStockBaseAvailable = false;
    RoundMap.clear();
    RoundStockMap.clear();
    RoundGroupName.clear();
    RoundPackages.clear();
    RoundOfferedGroups.clear();
    Status = WaitingRoundPlayer;
    return true;
}

void A31ClientConnect::Abort_Pending_Round()
{
    if (PendingResourceFactory) PendingResourceFactory->Unmount();
    PendingResourceFactory.reset();
    RoundMode = NoRound;
    RoundMapCRC = RoundModCRC = RoundGroupId = 0;
    RoundObservedResourceGeneration = 0;
    RoundHostedGame = -1;
    HaveRoundIdentity = false;
    PendingOwnsLevel = false;
    PendingStockBaseAvailable = false;
    RoundMap.clear();
    RoundStockMap.clear();
    RoundGroupName.clear();
    RoundPackages.clear();
    RoundOfferedGroups.clear();
    if (Status == WaitingRoundResources || Status == PreparingRoundResources ||
        Status == RoundReady || Status == LoadingRound || Status == WaitingRoundPlayer)
        Status = InGame;
}

bool A31ClientConnect::Is_Prepared_Map(const char *name)
{
    if (!Active || !Active->Matches_Session() || name == nullptr) return false;
    const bool current = Active->ResourcesMounted && Active->ResourceOwnsLevel &&
        Active->Resource_Group_Matches() &&
        !stricmp(name, Active->ResourceMap.c_str());
    const bool pending = Active->Status == RoundReady &&
        Active->RoundMode == ReplaceCurrentTT && Active->PendingOwnsLevel &&
        Active->PendingResourceFactory && Active->Round_Resource_Group_Matches() &&
        !stricmp(name, Active->RoundMap.c_str());
    return current || pending;
}

bool A31ClientConnect::Round_Map_Validity(const char *name, bool &valid)
{
    valid = false;
    if (!Active || !Active->Matches_Session() || !Active->HaveRoundIdentity)
        return false;
    if (name == nullptr || Active->RoundMap.empty() ||
        stricmp(name, Active->RoundMap.c_str())) return true;
    if (Active->Status == RoundReady) {
        valid = Active->RoundMode == StockOnly ||
            (Active->RoundMode == RetainCurrentTT && Active->Resource_Group_Matches()) ||
            (Active->RoundMode == ReplaceCurrentTT &&
             (Active->PendingOwnsLevel || Active->PendingStockBaseAvailable) &&
             Active->PendingResourceFactory && Active->Round_Resource_Group_Matches());
    } else if (Active->Status == LoadingRound) {
        valid = Active->RoundMode == StockOnly ||
            (Active->ResourcesMounted && Active->Resource_Group_Matches() &&
             !stricmp(name, Active->ResourceMap.c_str()));
    }
    return true;
}

bool A31ClientConnect::Request_Start(int team, unsigned long clan)
{
    if (Poll() != Ready || !Connection->Is_Established() ||
        !A4_Frontend_Is_Menu_Loop_Active()) return false;
    WideStringClass message;
    if (!Game->Is_Valid_Settings(message)) {
        Status = InvalidSettings;
        StringClass detail;
        message.Convert_To(detail);
        fprintf(stderr, "client-connect: original game settings rejected: %.256s\n", detail.Peek_Buffer());
        return false;
    }
    // Match DlgMPConnect::On_Periodic: never start a server or load reentrantly
    // inside cConnection::Service_Read. The existing frontend latches the load.
    Status = StartRequested;
    CampaignManager::Select_Backdrop_Number_By_MP_Type(Game->Get_Game_Type());
    GameInitMgrClass::Set_Is_Client_Required(true);
    GameInitMgrClass::Set_Is_Server_Required(false);
    GameInitMgrClass::Start_Game(Game->Get_Map_Name(), team, clan);
    return true;
}
