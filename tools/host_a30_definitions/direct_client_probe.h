#pragma once
#include "cnetwork.h"
#include "gdcnc.h"
#include "gametype.h"
#include "netinterface.h"
#include "connect.h"
#include "wwpacket.h"
#include "packetmgr.h"
#include "singlepl.h"
#include "networkobjectmgr.h"
#include "networkobjectfactorymgr.h"
#include "networkobjectfactory.h"
#include "netclassids.h"
#include "definitionfactorymgr.h"
#include "definitionmgr.h"
#include "combatchunkid.h"
#include "announceevent.h"
#include "harvester.h"
#include "refinerygameobj.h"
#include "vehicle.h"
#include "pscene.h"
#include "comnetrcvinst.h"
#include "gameoptionsevent.h"
#include "modpackagemgr.h"
#include "realcrc.h"
#include "a31_client_connect_boundary.h"
#include "renegade_file_factory.h"
#include "renegade_find_files.h"
#include "renegade_network_provider.h"
#include "renegade_client_identity.h"
#include "renegade_tt_client_greeting.h"
#include "renegade_client_options.h"
#include "renegade_client_effects.h"
#include "renegade_physical_rare.h"
#include "weaponmanager.h"
#include "weaponbag.h"
#include <sys/stat.h>
#include <fcntl.h>
#include <arpa/inet.h>
#include <sys/socket.h>
#include <unistd.h>
#include <chrono>

namespace DirectClientProbe {
inline bool Weapon_Definition_Test() {
    DefinitionClass *wrong_type = DefinitionMgrClass::Get_First(CLASSID_GAME_OBJECT_DEF_SOLDIER);
    if (!wrong_type) return false;
    bool passed = !WeaponManager::Find_Weapon_Definition(wrong_type->Get_ID()) &&
        !WeaponManager::Find_Ammo_Definition(wrong_type->Get_ID());
    WeaponBagClass bag(nullptr);
    for (int count : {-1, 1, 0x7fffffff}) {
        BitStreamClass packet;
        packet.Add(count);
        packet.Add(wrong_type->Get_ID());
        packet.Add(100);
        bag.Import_Weapon_List(packet);
        passed = packet.Has_Read_Error() && bag.Get_Count() == 1 && passed;
    }
    printf("tt_replication.weapon_wrong_type_and_count_rejection=%s\n", passed ? "PASS" : "FAIL");
    return passed;
}

inline int Physical_Rare_Test() {
    bool passed = true;
    unsigned truncated = 0;
    for (bool modern : {false, true}) {
        for (unsigned prefix = 0; prefix < 8; ++prefix) {
            BitStreamClass packet;
            if (prefix) packet.Add_Bits(0, prefix);
            if (modern) {
                packet.Add(2); packet.Add(1); packet.Add(static_cast<BYTE>(0));
                packet.Add(3); packet.Add(false);
            }
            packet.Add_Terminated_String("VITA_MODEL", true);
            packet.Add_Terminated_String("", true);
            for (int value : {0, 0, 3, 0, 5, 1}) packet.Add(value);
            packet.Add(true);
            if (modern) packet.Add(true);
            if (!prefix) {
                printf("tt_physical.vector_%d=%u:", modern, packet.Get_Bit_Write_Position());
                for (unsigned i = 0; i < (packet.Get_Bit_Write_Position() + 7) / 8; ++i)
                    printf("%02x", static_cast<unsigned char>(packet.Get_Data()[i]));
                printf("\n");
            }
            ULONG ignored = 0;
            if (prefix) packet.Get_Bits(ignored, prefix);
            passed = Renegade_Validate_Physical_Rare(packet, modern, false) &&
                !Renegade_Validate_Physical_Rare(packet, !modern, false) && passed;
            passed = packet.Get_Bit_Read_Position() == prefix && !packet.Has_Read_Error() && passed;
            for (unsigned end = prefix; end < packet.Get_Bit_Write_Position(); ++end) {
                BitStreamClass short_packet;
                short_packet = packet;
                short_packet.Set_Bit_Write_Position(end);
                passed = !Renegade_Validate_Physical_Rare(short_packet, modern, false) && passed;
                ++truncated;
            }
        }
    }
    printf("tt_physical.profiles_unaligned_truncations=%u result=%s\n", truncated, passed ? "PASS" : "FAIL");
    return passed ? 0 : 1;
}

inline int Export_Resource_Options(const char *path, const char *map = "C&C_ResourceFixture.mix") {
    cGameDataCnc game;
    game.Set_Map_Name(map);
    game.Set_Max_Players(8);
    game.Set_Port(5001);
    game.Set_Time_Remaining_Seconds(321.0f);
    PTheGameData = &game;
    cPacket packet;
    packet.Add(900002);
    packet.Add(static_cast<BYTE>(NetworkObjectClass::BIT_CREATION));
    packet.Add(false);
    packet.Add(static_cast<int>(NETCLASSID_GAMEOPTIONSEVENT));
    cGameOptionsEvent *event = new cGameOptionsEvent;
    event->Export_Creation(packet);
    NetworkObjectMgrClass::Delete_Pending();
    PTheGameData = nullptr;
    const uint32_t bits = packet.Get_Bit_Write_Position();
    unsigned char header[] = { static_cast<unsigned char>(bits), static_cast<unsigned char>(bits >> 8),
        static_cast<unsigned char>(bits >> 16), static_cast<unsigned char>(bits >> 24) };
    FILE *file = fopen(path, "wb");
    if (!file) return 2;
    bool ok = fwrite(header, 1, 4, file) == 4 &&
        fwrite(packet.Get_Data(), 1, (bits + 7) / 8, file) == (bits + 7) / 8;
    if (fclose(file)) ok = false;
    return ok ? 0 : 1;
}
inline int Harvester_Lifetime_Test() {
    struct Tracked : HarvesterClass {
        explicit Tracked(unsigned &count) : Count(count) {}
        ~Tracked() override { ++Count; }
        unsigned &Count;
    };
    unsigned destroyed = 0;
    bool passed = true;
    if (!PhysicsSceneClass::Get_Instance()) return 1;
    DefinitionClass *definition = DefinitionMgrClass::Get_First(CLASSID_GAME_OBJECT_DEF_VEHICLE);
    StringClass error;
    while (definition && !definition->Is_Valid_Config(error))
        definition = DefinitionMgrClass::Get_Next(definition, CLASSID_GAME_OBJECT_DEF_VEHICLE);
    if (!definition) return 1;
    for (unsigned order = 0; order < 2; ++order) {
        RefineryGameObj *refinery = new RefineryGameObj;
        VehicleGameObj *vehicle = static_cast<VehicleGameObj *>(definition->Create());
        const int original_observers = vehicle->Get_Observers().Count();
        Tracked *observer = new Tracked(destroyed);
        observer->Set_Refinery(refinery);
        refinery->Set_Harvester(observer);
        vehicle->Add_Observer(observer);
        if (order == 0) {
            delete refinery;
            passed = vehicle->Get_Observers().Count() == original_observers && passed;
            delete vehicle;
        } else {
            delete vehicle;
            passed = refinery->Get_Harvester_Vehicle() == nullptr && passed;
            delete refinery;
        }
        GameObjObserverManager::Delete_Pending();
        passed = destroyed == order + 1 && passed;
    }
    printf("multiplayer.harvester_both_owner_orders=%s destructions=%u\n",
        passed ? "PASS" : "FAIL", destroyed);
    return passed ? 0 : 1;
}

inline int Building_Factory_Test() {
    bool passed = true;
    for (unsigned id = CLASSID_GAME_OBJECT_DEF_REFINERY;
         id <= CLASSID_GAME_OBJECT_DEF_REPAIR_BAY; ++id) {
        const bool present = DefinitionFactoryMgrClass::Find_Factory(id) != nullptr;
        printf("multiplayer.building_factory=%u present=%d\n", id, present);
        passed = present && passed;
    }
    return passed ? 0 : 1;
}

inline int Announcement_Test() {
    class Probe : public SCAnnouncement {
    public:
        bool Matches() const {
            return mToID == 1 && mFromID == 7 && mAnnouncementID == 0 &&
                mRadioCmdID == 23 && mType == ANNOUNCEMENT_TEAM;
        }
    };
    cPacket packet;
    packet.Add(1);
    packet.Add(7);
    packet.Add(0);
    packet.Add(23);
    packet.Add(static_cast<BYTE>(ANNOUNCEMENT_TEAM));
    const unsigned bits = packet.Get_Bit_Write_Position();
    Probe *event = new Probe;
    event->Import_Creation(packet);
    const bool passed = event->Matches() && packet.Is_Flushed() &&
        bits == packet.Get_Bit_Write_Position();
    NetworkObjectMgrClass::Delete_Pending();
    printf("multiplayer.announcement_reads_without_writing=%s\n", passed ? "PASS" : "FAIL");
    return passed ? 0 : 1;
}

inline int TT_Server_Info_Test() {
    bool passed = true;
    unsigned rejected = 0;
    RenegadeTTServerInfo info;
    cPacket legacy;
    passed = Renegade_Read_TT_Server_Info(legacy, info) && !info.Present && passed;
    const char *repository = "https://ttfs.rencorner.net.co/marathon";
    cPacket good;
    good.Add(static_cast<ULONG>(0x21545421U));
    good.Add(static_cast<ULONG>(0x4099999aU));
    good.Add_Terminated_String(repository);
    good.Add(static_cast<ULONG>(9000));
    for (unsigned bits = 1; bits < good.Get_Bit_Write_Position(); ++bits) {
        cPacket truncated;
        truncated = good;
        truncated.Set_Bit_Write_Position(bits);
        const bool failed = !Renegade_Read_TT_Server_Info(truncated, info) && !info.Present &&
            !info.Revision && !info.Repository[0];
        passed = failed && passed;
        rejected += failed;
    }
    for (const char *uri : {"file:///etc/passwd", "https://user@host", "https://host\\bad",
                            "https://host\npath"}) {
        cPacket invalid;
        invalid.Add(static_cast<ULONG>(0x21545421U));
        invalid.Add(static_cast<ULONG>(0x4099999aU));
        invalid.Add_Terminated_String(uri);
        invalid.Add(static_cast<ULONG>(9000));
        passed = !Renegade_Read_TT_Server_Info(invalid, info) && !info.Present && passed;
    }
    passed = Renegade_Read_TT_Server_Info(good, info) && info.Present &&
        info.Revision == 9000 && strcmp(info.Repository, repository) == 0 && passed;
    passed = Renegade_Read_TT_Server_Info(legacy, info) && !info.Present && passed;
    // The network header and local ID leave the original reader unaligned.
    for (unsigned prefix = 1; prefix <= 7; ++prefix) {
        cPacket unaligned;
        unaligned.Add_Bits(0, prefix);
        unaligned.Add(static_cast<ULONG>(0x21545421U));
        unaligned.Add(static_cast<ULONG>(0x4099999aU));
        unaligned.Add_Terminated_String(repository);
        unaligned.Add(static_cast<ULONG>(9000));
        ULONG ignored = 0;
        unaligned.Get_Bits(ignored, prefix);
        passed = Renegade_Read_TT_Server_Info(unaligned, info) && info.Present &&
            info.Revision == 9000 && strcmp(info.Repository, repository) == 0 && passed;
    }
    printf("tt_server_info.legacy_metadata_reset_unaligned=%s rejected_truncations=%u\n",
        passed ? "PASS" : "FAIL", rejected);
    return passed ? 0 : 1;
}

// Incoming public-options-only fixture. No sockets, identity provider or world
// adoption: this exercises the original importer and rooted map lookup offline.
inline int Replay_Options(const char *retail, const char *fixture) {
    FILE *input = fopen(fixture, "rb");
    if (!input) return 2;
    unsigned char header[4];
    const bool header_ok = fread(header, 1, 4, input) == 4;
    const uint32_t bits = header_ok ? uint32_t(header[0]) | (uint32_t(header[1]) << 8) |
        (uint32_t(header[2]) << 16) | (uint32_t(header[3]) << 24) : 0;
    cPacket packet;
    const size_t bytes = (bits + 7ULL) / 8;
    bool valid = bits && bytes <= packet.Get_Buffer_Size() &&
        fread(packet.Get_Data(), 1, bytes, input) == bytes && fgetc(input) == EOF;
    fclose(input);
    if (!valid) return 2;
    packet.Set_Bit_Write_Position(bits);
    const RenegadePathRoots roots = {retail, retail, retail, retail};
    Renegade_Set_Find_Roots(roots);
    RenegadeRootedFileFactoryClass factory(roots);
    FileFactoryClass *previous = _TheFileFactory;
    _TheFileFactory = &factory;
    cGameDataCnc game;
    PTheGameData = &game;
    cGameType::Set_Game_Type(GAMETYPE_MULTIPLAY);
    cGameOptionsEvent *event = new cGameOptionsEvent;
    event->Import_Creation(packet);
    const bool map_valid = game.Is_Map_Valid();
    printf("options_replay.map=%s valid=%d flushed=%d port=%d max_players=%d hosted=%d\n",
        game.Get_Map_Name().Peek_Buffer(), map_valid, packet.Is_Flushed(),
        game.Get_Port(), game.Get_Max_Players(), game.Get_Hosted_Game_Number());
    NetworkObjectMgrClass::Delete_Pending();
    PTheGameData = nullptr;
    _TheFileFactory = previous;
    cGameType::Set_Game_Type(GAMETYPE_NONE);
    return map_valid && packet.Is_Flushed() ? 0 : 1;
}

static bool request_seen = false;
static int client_id = 0;
static REFUSAL_CODE response = REFUSAL_CLIENT_ACCEPTED;
static int refusal_seen = 0;
static bool acceptance_seen = false;
static bool expect_tt_greeting = false;
static int broken_id = 0;
static void Accepted() {
    cNetwork::Accept_Handler();
    acceptance_seen = true;
}
static void Refused(REFUSAL_CODE code) {
    cNetwork::Refusal_Handler(code);
    refusal_seen = code;
}
static REFUSAL_CODE Accept_Request(cPacket &packet) {
    WideStringClass name, password;
    packet.Get_Wide_Terminated_String(name.Get_Buffer(256), 256, true);
    packet.Get_Wide_Terminated_String(password.Get_Buffer(256), 256, true);
    int key = 0;
    packet.Get(key);
    request_seen = name.Compare(L"PS Vita") == 0 && password.Is_Empty() && key == cNetwork::Get_Exe_Key();
    // Inspect a copy: original WWNet still consumes the bandwidth field.
    cPacket extension;
    extension = packet;
    ULONG bandwidth = 0;
    extension.Get(bandwidth);
    if (expect_tt_greeting) {
        ULONG marker = 0, version = 0, revision = 0;
        char serial[33] = {}, hardware[65] = {}, expected[33] = {};
        extension.Get(marker);
        extension.Get(version);
        extension.Get_Terminated_String(serial, sizeof(serial));
        extension.Get(revision);
        extension.Get_Terminated_String(hardware, sizeof(hardware), true);
        RenegadeClientIdentity::Serial_Hash("aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", expected);
        request_seen = request_seen && marker == 0x21545421u && version == 0x4099999au &&
            revision == 9000 && !strcmp(serial, expected) && !hardware[0];
    }
    request_seen = request_seen && bandwidth > 0 && extension.Is_Flushed();
    return request_seen ? response : REFUSAL_BY_APPLICATION;
}
static void Connected(int id) { client_id = id; }
static void Packet(cPacket &packet, int) { packet.Flush(); }
static void Broken(int id) { broken_id = id; }

inline bool Admission(A31ClientConnect &pending, bool resource_fixture = false) {
    refusal_seen = 0;
    acceptance_seen = false;
    cNetwork::PClientConnection->Install_Accept_Handler(Accepted);
    cNetwork::PClientConnection->Install_Refusal_Handler(Refused);
    const auto deadline = std::chrono::steady_clock::now() + std::chrono::seconds(10);
    while ((pending.Poll() == A31ClientConnect::WaitingOptions ||
        pending.Poll() == A31ClientConnect::WaitingResources) &&
        std::chrono::steady_clock::now() < deadline) {
        cConnection *connection = cNetwork::PClientConnection;
        if (!connection || connection->Is_Destroy()) break;
        // Same pre-world service path as the Vita frontend. No local server,
        // world update, BioEvent, replacement player or protocol override.
        connection->Service_Read();
        connection->Service_Send(true);
        PacketManager.Flush(true);
        NetworkObjectMgrClass::Delete_Pending();
        if (pending.Poll() == A31ClientConnect::WaitingResources) pending.Prepare_Resources();
        usleep(1000);
    }
    const auto state = pending.Poll();
    const bool options = state == A31ClientConnect::Ready || state == A31ClientConnect::MissingMap;
    printf("direct_admission.evidence_class=host_original_udp\n");
    printf("direct_admission.player=PS Vita\n");
    printf("direct_admission.exe_key=%d\n", cNetwork::Get_Exe_Key());
    const auto &tt = cNetwork::PClientConnection->Get_TT_Server_Info();
    printf("direct_admission.tt_metadata=%d revision=%u repository_present=%d\n",
        tt.Present, tt.Revision, tt.Repository[0] != 0);
    const auto &resources = cNetwork::PClientConnection->Get_TT_Resources();
    printf("direct_admission.resources groups=%u generation=%u pending=%u error=%s\n",
        static_cast<unsigned>(resources.Get_Groups().size()), resources.Get_Generation(),
        resources.Get_Remaining(), resources.Get_Error() ? resources.Get_Error() : "none");
    for (size_t i = 0; i < resources.Get_Groups().size() && i < 4; ++i) {
        const auto &group = resources.Get_Groups()[i];
        printf("direct_admission.resource_group id=%08x packages=%u name=%.255s\n",
            group.Id, static_cast<unsigned>(group.Packages.size()), group.Name.c_str());
        for (size_t p = 0; p < group.Packages.size() && p < 4; ++p)
            printf("direct_admission.resource_package index=%u id=%08x\n",
                static_cast<unsigned>(p), group.Packages[p]);
    }
    printf("direct_admission.accepted=%d refusal=%d options=%d state=%d joined=0\n",
        acceptance_seen, refusal_seen, options, state);
    if (options) printf("direct_admission.map=%s\n", The_Game()->Get_Map_Name().Peek_Buffer());
    if (resource_fixture && state == A31ClientConnect::Ready &&
        FileFactoryListClass::Get_Instance()->Peek_Temp_FileFactory()) {
        auto *chain = FileFactoryListClass::Get_Instance();
        chain->Reset_Search_Start();
        FileClass *override_file = chain->Get_File("stylemgr.ini");
        char sentinel[19] = {};
        const bool override_ok = override_file && override_file->Open(FileClass::READ) &&
            override_file->Read(sentinel, 18) == 18 && !strcmp(sentinel, "synthetic-sentinel");
        if (override_file) { override_file->Close(); chain->Return_File(override_file); }
        printf("direct_admission.prepared_overrides_retail_after_search_reset=%d\n", override_ok);
        A4_Frontend_Begin_Menu_Loop();
        const bool requested = pending.Request_Start(-1, 0);
        A4_Frontend_End_Menu_Loop();
        printf("direct_admission.prepared_original_start=%d\n", requested);
        // This fixture stops before world loading. Verify detach does not leave
        // the previous server's files selected for a later campaign/session.
        const bool mounted = chain->Peek_Temp_FileFactory() != nullptr;
        pending.Reset();
        printf("direct_admission.prepared_cleanup=%d\n",
            mounted && !chain->Peek_Temp_FileFactory() &&
            !A31ClientConnect::Is_Prepared_Map("C&C_ResourceFixture.mix"));
        A4_Frontend_Reset_Trace();
        return requested && override_ok;
    }
    return options;
}

inline bool Session(REFUSAL_CODE result, int options_case = 0, bool tt_greeting = false) {
    // These transport-only fixtures bypass Onetime_Init, but must still run
    // the same compatibility-key preflight before sending a connection.
    cNetwork::Compute_Exe_Key();
    const int baseline_objects = NetworkObjectMgrClass::Get_Object_Count();
    request_seen = false;
    client_id = 0;
    response = result;
    refusal_seen = 0;
    acceptance_seen = false;
    broken_id = 0;
    expect_tt_greeting = tt_greeting;
    cGameType::Set_Game_Type(GAMETYPE_MULTIPLAY);
    WideStringClass name(L"PS Vita");
    cNetInterface::Set_Nickname(name);
    cGameDataCnc game;
    PTheGameData = &game;
    int socket_fd = socket(AF_INET, SOCK_DGRAM, 0);
    sockaddr_in address{};
    address.sin_family = AF_INET;
    address.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
    if (socket_fd < 0) { PTheGameData = nullptr; return false; }
    if (bind(socket_fd, reinterpret_cast<sockaddr *>(&address), sizeof(address))) {
        close(socket_fd);
        PTheGameData = nullptr;
        return false;
    }
    socklen_t size = sizeof(address);
    if (getsockname(socket_fd, reinterpret_cast<sockaddr *>(&address), &size)) {
        close(socket_fd);
        PTheGameData = nullptr;
        return false;
    }
    unsigned short port = ntohs(address.sin_port);
    close(socket_fd);
    cConnection server;
    server.Install_Application_Acceptance_Handler(Accept_Request);
    server.Install_Conn_Handler(Connected);
    server.Install_Server_Packet_Handler(Packet);
    server.Install_Server_Broken_Connection_Handler(Broken);
    server.Set_Bandwidth_Budget_Out(2000000);
    server.Init_As_Server(port, 2, true, INADDR_LOOPBACK);
    game.Set_Ip_Address(htonl(INADDR_LOOPBACK));
    game.Set_Port(port);
    if (tt_greeting) Renegade_Arm_TT_Greeting_Probe();
    cNetwork::Init_Client();
    cNetwork::PClientConnection->Install_Accept_Handler(Accepted);
    cNetwork::PClientConnection->Install_Refusal_Handler(Refused);
    bool connected = false;
    for (int attempt = 0; attempt < 2000; ++attempt) {
        server.Service_Read();
        server.Service_Send(true);
        cNetwork::PClientConnection->Service_Read();
        cNetwork::PClientConnection->Service_Send(true);
        PacketManager.Flush(true);
        if (cNetwork::PClientConnection->Is_Established()) { connected = true; break; }
        if (cNetwork::PClientConnection->Is_Destroy()) break;
        usleep(1000);
    }
    const bool accepted = result == REFUSAL_CLIENT_ACCEPTED;
    const int objects_before_cleanup = NetworkObjectMgrClass::Get_Object_Count();
    bool passed = request_seen && cNetwork::I_Am_Only_Client() &&
        !cSinglePlayerData::Is_Single_Player();
    passed = !Renegade_Client_Disables_Camera_Shake() && passed;
    passed = passed && (accepted ?
        connected && acceptance_seen && !refusal_seen && client_id == 1 &&
            NetworkObjectMgrClass::Get_Object_Count() == baseline_objects + 2 :
        !connected && !acceptance_seen && refusal_seen == result && client_id == 0 &&
            cNetwork::PClientConnection->Is_Destroy());
    if (passed && options_case == -2) {
        A31ClientConnect pending;
        passed = pending.Begin() && passed;
        cPacket creation;
        creation.Add(900001);
        creation.Add(static_cast<BYTE>(NetworkObjectClass::BIT_CREATION));
        creation.Add(false);
        creation.Add(static_cast<int>(NETCLASSID_GAMEOBJ));
        creation.Add(0x7f000001);
        cNetwork::Client_Packet_Handler(creation);
        passed = creation.Is_Flushed() && A31ClientConnect::Protocol_Failed() &&
            pending.Poll() == A31ClientConnect::ProtocolMismatch &&
            NetworkObjectMgrClass::Find_Object(900001) == nullptr && passed;
        // Once failed, later queued packets must not mutate the partial world.
        cPacket trailing;
        trailing.Add(1);
        cNetwork::Client_Packet_Handler(trailing);
        passed = trailing.Is_Flushed() && passed;
    }
    if (passed && options_case == -3) {
        A31ClientConnect pending;
        passed = pending.Begin() && passed;
        cPacket truncated;
        truncated.Add_Bits(1, 1);
        cNetwork::Client_Packet_Handler(truncated);
        passed = truncated.Has_Read_Error() && A31ClientConnect::Protocol_Failed() &&
            cNetwork::PClientConnection->Is_Destroy() &&
            pending.Poll() == A31ClientConnect::ProtocolMismatch && passed;
    }
    if (passed && options_case == -1) {
        cPacket packet;
        packet.Add(123);
        server.Send_Packet_To_Individual(packet, client_id, SEND_RELIABLE);
        // Leave the accepted peer silent: exercise the real reliable-send
        // timeout and callback without altering engine clocks or lifetimes.
        const auto deadline = std::chrono::steady_clock::now() + std::chrono::seconds(75);
        while (!broken_id && std::chrono::steady_clock::now() < deadline) {
            server.Service_Read();
            server.Service_Send(true);
            PacketManager.Flush(true);
            usleep(10000);
        }
        passed = broken_id == client_id && server.Get_Num_RHosts() == 0 && passed;
        for (int frame = 0; frame < 4; ++frame) server.Service_Send(true);
        printf("direct_client.silent_peer_timeout_cleanup=%s\n", passed ? "PASS" : "FAIL");
    }
    if (passed && options_case > 0) {
        A31ClientConnect pending;
        if (options_case != 5) {
            passed = pending.Begin() && passed;
            A31ClientConnect competing;
            passed = !competing.Begin() && passed;
            passed = pending.Poll() == A31ClientConnect::WaitingOptions && passed;
        }
        A4_Frontend_Begin_Menu_Loop();
        // Use the original server serializer and UDP send path, then restore
        // client ownership before dispatch. No server application import here.
        cGameDataCnc server_game;
        StringClass map(options_case == 2 || options_case == 5 ? "C&C_Missing.mix" : "C&C_Fixture.mix");
        server_game.Set_Map_Name(map);
        server_game.Set_Max_Players(8);
        server_game.Set_Time_Remaining_Seconds(321.0f);
        server_game.IsPassworded.Set(options_case == 3);
        PTheGameData = &server_game;
        cNetwork::PServerConnection = &server;
        cGameData::Set_Hosted_Game_Number(42);
        cGameOptionsEvent *event = new cGameOptionsEvent;
        event->Init(client_id);
        if (tt_greeting) {
            // Original game options, with only the reference-verified suffix
            // replaced. Original transport/event dispatch still owns receipt.
            cPacket modern_options;
            modern_options.Add(event->Get_Network_ID());
            modern_options.Add(static_cast<BYTE>(NetworkObjectClass::BIT_CREATION));
            modern_options.Add(false);
            modern_options.Add(static_cast<int>(NETCLASSID_GAMEOPTIONSEVENT));
            event->Export_Creation(modern_options);
            modern_options.Set_Bit_Write_Position(modern_options.Get_Bit_Write_Position() - 64);
            modern_options.Add(true);
            server.Send_Packet_To_Individual(modern_options, client_id, SEND_RELIABLE);
        } else cNetwork::Send_Object_Update(event, client_id);
        NetworkObjectMgrClass::Delete_Pending();
        cNetwork::PServerConnection = nullptr;
        PTheGameData = &game;
        cGameData::Set_Hosted_Game_Number(-1);
        for (int attempt = 0; attempt < 2000; ++attempt) {
            server.Service_Send(true);
            PacketManager.Flush(true);
            cNetwork::PClientConnection->Service_Read();
            if (options_case == 5 ? NetworkObjectMgrClass::Get_Pending_Object_Count() > 0 :
                pending.Poll() != A31ClientConnect::WaitingOptions) break;
            usleep(1000);
        }
        passed = !A4_Frontend_Get_Trace().tutorial_start_latched && passed;
        passed = Renegade_Client_Disables_Camera_Shake() == tt_greeting && passed;
        if (tt_greeting) {
            cGameType::Set_Game_Type(GAMETYPE_MISSION);
            passed = !Renegade_Client_Disables_Camera_Shake() && passed;
            cGameType::Set_Game_Type(GAMETYPE_MULTIPLAY);
            cNetwork::PClientConnection->Set_TT_Options_Flag(false);
            passed = !Renegade_Client_Disables_Camera_Shake() && passed;
            cNetwork::PClientConnection->Set_TT_Options_Flag(true);
            cNetwork::PClientConnection->Set_TT_Client_Greeting(false);
            passed = !Renegade_Client_Disables_Camera_Shake() && passed;
            cNetwork::PClientConnection->Set_TT_Client_Greeting(true);
        }
        if (options_case == 2 || options_case == 5) {
            passed = pending.Poll() == (options_case == 5 ? A31ClientConnect::Idle : A31ClientConnect::MissingMap) &&
                cGameData::Get_Hosted_Game_Number() == -1 && !pending.Request_Start(-1, 0) && passed;
        } else {
            passed = pending.Poll() == A31ClientConnect::Ready &&
                cGameData::Get_Hosted_Game_Number() == 42 &&
                game.Get_Map_Name().Compare_No_Case("C&C_Fixture.mix") == 0 &&
                game.Get_Time_Remaining_Seconds() == 321.0f && passed;
            if (options_case == 4) cNetwork::Cleanup_Client();
            const bool started = pending.Request_Start(-1, 0);
            passed = (options_case == 4 ? !started && pending.Poll() == A31ClientConnect::ConnectionLost :
                options_case == 3 ? !started && pending.Poll() == A31ClientConnect::InvalidSettings :
                started && pending.Poll() == A31ClientConnect::StartRequested &&
                A4_Frontend_Get_Trace().client_only_selected &&
                strcmp(A4_Frontend_Get_Trace().tutorial_map, "C&C_Fixture.mix") == 0 &&
                !pending.Request_Start(-1, 0)) && passed;
        }
        printf("direct_client.original_options_case_%d=%s state=%d\n", options_case,
            passed ? "PASS" : "FAIL", pending.Poll());
        A4_Frontend_End_Menu_Loop();
        A4_Frontend_Reset_Trace();
    }
    cNetwork::Cleanup_Client();
    // The original goodbye is delete-pending; drain it before the next fixture.
    NetworkObjectMgrClass::Delete_Pending();
    passed = passed && !Renegade_Client_Disables_Camera_Shake() &&
        !cNetwork::I_Am_Client() && !cNetwork::PClientConnection &&
        NetworkObjectMgrClass::Get_Object_Count() == baseline_objects;
    printf("direct_client.original_udp_result_%d=%s request=%d id=%d refusal=%d objects=%d/%d\n",
        result, passed ? "PASS" : "FAIL", request_seen, client_id, refusal_seen,
        objects_before_cleanup, NetworkObjectMgrClass::Get_Object_Count());
    PTheGameData = nullptr;
    cGameType::Set_Game_Type(GAMETYPE_NONE);
    return passed;
}

inline int TT_Options_Layout_Test() {
    cGameDataCnc game;
    WideStringClass owner(L"Fixture");
    game.Set_Owner(owner);
    game.Set_Map_Name("C&C_Fixture.mix");
    cPacket legacy;
    game.Export_Tier_1_Data(legacy);
    game.Export_Tier_2_Data(legacy);
    legacy.Add(321.0f);
    legacy.Add(42);
    legacy.Add(static_cast<ULONG>(CRC_Stringi(game.Get_Mod_Name())));
    legacy.Add(static_cast<ULONG>(CRC_Stringi(game.Get_Map_Name())));
    bool passed = true;
    unsigned rejected = 0;
    for (bool flag : {false, true}) {
        cPacket suffix;
        suffix.Add(321.0f);
        suffix.Add(42);
        suffix.Add(flag);
        printf("tt_options.suffix_%u=%u:", unsigned(flag), suffix.Get_Bit_Write_Position());
        for (unsigned i = 0; i < suffix.Get_Compressed_Size_Bytes(); ++i)
            printf("%02x", static_cast<unsigned char>(suffix.Get_Data()[i]));
        printf("\n");
    }
    for (bool modern : {false, true}) {
        cPacket good;
        good = legacy;
        if (modern) {
            good.Set_Bit_Write_Position(good.Get_Bit_Write_Position() - 64);
            good.Add(true);
        }
        RenegadeClientOptionsLayout layout;
        passed = Renegade_Inspect_Client_Options(good, modern, layout) &&
            layout.MapCRC == static_cast<uint32_t>(CRC_Stringi("C&C_Fixture.mix")) &&
            layout.ModCRC == 0 && layout.ModernFlag == modern &&
            good.Get_Bit_Read_Position() == 0 && passed;
        passed = !Renegade_Inspect_Client_Options(good, !modern, layout) && passed;
        for (unsigned bits = 0; bits < good.Get_Bit_Write_Position(); ++bits) {
            cPacket short_packet;
            short_packet = good;
            short_packet.Set_Bit_Write_Position(bits);
            const bool failed = !Renegade_Inspect_Client_Options(short_packet, modern, layout) &&
                !layout.MapCRC && !layout.ModCRC && !layout.ModernFlag &&
                short_packet.Get_Bit_Read_Position() == 0;
            passed = failed && passed;
            rejected += failed;
        }
        for (unsigned prefix = 1; prefix < 8; ++prefix) {
            cPacket unaligned;
            unaligned.Add_Bits(0, prefix);
            for (unsigned bit = 0; bit < good.Get_Bit_Write_Position(); ++bit)
                unaligned.Add_Bits((static_cast<unsigned char>(good.Get_Data()[bit / 8]) >> (7 - bit % 8)) & 1, 1);
            ULONG ignored = 0;
            unaligned.Get_Bits(ignored, prefix);
            passed = Renegade_Inspect_Client_Options(unaligned, modern, layout) &&
                unaligned.Get_Bit_Read_Position() == prefix && passed;
        }
        good.Add(false);
        passed = !Renegade_Inspect_Client_Options(good, modern, layout) && passed;
    }
    cPacket oversized;
    oversized = legacy;
    oversized.Get_Data()[4] = '\xff';
    oversized.Get_Data()[5] = '\xff';
    RenegadeClientOptionsLayout invalid;
    passed = !Renegade_Inspect_Client_Options(oversized, false, invalid) && passed;
    printf("tt_options.layout_bounds_profiles_unaligned=%s rejected=%u\n", passed ? "PASS" : "FAIL", rejected);
    return passed ? 0 : 1;
}

inline int TT_Client_Greeting_Test() {
    const char *hash = "72da19ede7ce05ef464f898254597939";
    const wchar_t *names[] = {L"PS Vita", L"NNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNN", L"Fixture"};
    const wchar_t *passwords[] = {L"", L"password", L"P\u00e4ss"};
    const ULONG keys[] = {0x12345678u, 0xffffffffu, 0};
    const ULONG bandwidths[] = {2000000, 100000000, 10000};
    const char *hardware[] = {"synthetic-vita-identity", "",
        "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"};
    bool passed = TT_Options_Layout_Test() == 0;
    for (unsigned vector = 0; vector < 3; ++vector) {
        cPacket aligned;
        aligned.Add_Wide_Terminated_String(names[vector]);
        aligned.Add_Wide_Terminated_String(passwords[vector], true);
        aligned.Add(keys[vector]);
        aligned.Add(bandwidths[vector]);
        passed = Renegade_Write_TT_Client_Greeting(aligned, hash, hardware[vector]) && passed;
        printf("tt_greeting.vector_%u=%u:", vector, aligned.Get_Bit_Write_Position());
        for (unsigned byte = 0; byte < aligned.Get_Compressed_Size_Bytes(); ++byte)
            printf("%02x", static_cast<unsigned char>(aligned.Get_Data()[byte]));
        printf("\n");
        for (unsigned prefix = 1; prefix < 8; ++prefix) {
            cPacket unaligned;
            unaligned.Add_Bits(0, prefix);
            unaligned.Add_Wide_Terminated_String(names[vector]);
            unaligned.Add_Wide_Terminated_String(passwords[vector], true);
            unaligned.Add(keys[vector]);
            unaligned.Add(bandwidths[vector]);
            passed = Renegade_Write_TT_Client_Greeting(unaligned, hash, hardware[vector]) && passed;
            ULONG bit = 0;
            unaligned.Get_Bits(bit, prefix);
            for (unsigned i = 0; i < aligned.Get_Bit_Write_Position(); ++i) {
                unaligned.Get_Bits(bit, 1);
                passed = bit == ((static_cast<unsigned char>(aligned.Get_Data()[i / 8]) >> (7 - i % 8)) & 1u) && passed;
            }
            passed = unaligned.Is_Flushed() && passed;
        }
    }
    auto rejected_without_mutation = [&](const char *serial, const char *id, unsigned position) {
        cPacket packet;
        packet.Set_Bit_Write_Position(position);
        char before[MAX_BUFFER_SIZE];
        memcpy(before, packet.Get_Data(), sizeof(before));
        const unsigned stats = packet.Get_Uncompressed_Size_Bytes();
        return !Renegade_Write_TT_Client_Greeting(packet, serial, id) &&
            packet.Get_Bit_Write_Position() == position && packet.Get_Bit_Read_Position() == 0 &&
            packet.Get_Uncompressed_Size_Bytes() == stats && !memcmp(before, packet.Get_Data(), sizeof(before));
    };
    for (const char *invalid : {static_cast<const char *>(nullptr), "", "a", "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA", "gggggggggggggggggggggggggggggggggg"})
        passed = rejected_without_mutation(invalid, "", 0) && passed;
    for (const char *invalid : {static_cast<const char *>(nullptr), "bad\nidentifier", "bad\xff", "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"})
        passed = rejected_without_mutation(hash, invalid, 0) && passed;
    // Empty hardware requires exactly 48 bytes. Every insufficient tail fails atomically.
    for (unsigned remaining = 0; remaining < 48 * 8; ++remaining)
        passed = rejected_without_mutation(hash, "", MAX_BUFFER_SIZE * 8 - remaining) && passed;
    cPacket exact;
    exact.Set_Bit_Write_Position(MAX_BUFFER_SIZE * 8 - 48 * 8);
    passed = Renegade_Write_TT_Client_Greeting(exact, hash, "") &&
        exact.Get_Bit_Write_Position() == MAX_BUFFER_SIZE * 8 &&
        exact.Get_Uncompressed_Size_Bytes() == 48 && passed;
    FileFactoryClass *previous = _TheWritingFileFactory;
    _TheWritingFileFactory = nullptr;
    cPacket missing;
    Renegade_Arm_TT_Greeting_Probe();
    passed = !Renegade_Append_Client_Greeting(missing, true) && !missing.Get_Bit_Write_Position() && passed;
    passed = Renegade_Append_Client_Greeting(missing, true) && !missing.Get_Bit_Write_Position() && passed;
    Renegade_Arm_TT_Greeting_Probe();
    passed = !Renegade_Append_Client_Greeting(missing, false) && !missing.Get_Bit_Write_Position() && passed;
    passed = Renegade_Append_Client_Greeting(missing, true) && !missing.Get_Bit_Write_Position() && passed;
    _TheWritingFileFactory = previous;
    printf("tt_greeting.vectors_unaligned_bounds_missing_identity_one_shot=%s\n", passed ? "PASS" : "FAIL");

    char directory[] = "/tmp/renegade-tt-greeting-XXXXXX";
    if (!mkdtemp(directory)) return 1;
    const std::string config = std::string(directory) + "/config";
    if (mkdir(config.c_str(), 0700)) { rmdir(directory); return 1; }
    const std::string path = config + "/tt-identity-v1.txt";
    const int fd = open(path.c_str(), O_CREAT | O_EXCL | O_WRONLY, 0600);
    if (fd < 0) { rmdir(config.c_str()); rmdir(directory); return 1; }
    const bool written = write(fd, "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\n", 33) == 33;
    close(fd);
    const RenegadePathRoots roots = {directory, directory, directory, directory};
    RenegadeRootedFileFactoryClass factory(roots);
    _TheWritingFileFactory = &factory;
    CombatNetworkReceiverInstanceClass receiver;
    cNetwork::Set_Receiver(&receiver);
    if (written) {
        for (unsigned cycle = 0; cycle < 2; ++cycle) {
            passed = Session(REFUSAL_CLIENT_ACCEPTED, 0, true) && passed;
            passed = Session(REFUSAL_BY_APPLICATION, 0, true) && passed;
            passed = Session(REFUSAL_CLIENT_ACCEPTED) && passed;
            passed = Session(REFUSAL_CLIENT_ACCEPTED, 2, true) && passed;
        }
    } else passed = false;
    cNetwork::Set_Receiver(nullptr);
    _TheWritingFileFactory = previous;
    unlink(path.c_str()); rmdir(config.c_str()); rmdir(directory);
    printf("tt_greeting.original_udp_accept_refuse_legacy_reset=%s\n", passed ? "PASS" : "FAIL");
    return passed ? 0 : 1;
}

inline int Run() {
    setvbuf(stdout, nullptr, _IONBF, 0);
    CombatNetworkReceiverInstanceClass receiver;
    cNetwork::Set_Receiver(&receiver);
    bool passed = true;
    RenegadeNetworkProvider::Endpoint endpoint;
    passed = RenegadeNetworkProvider::Parse_Direct_IP("127.0.0.1:5001", 0, endpoint) &&
        endpoint.Address == 0x7f000001U && endpoint.PortNumber == 5001 && passed;
    passed = RenegadeNetworkProvider::Parse_Direct_IP("10.0.0.2", 1234, endpoint) &&
        endpoint.Address == 0x0a000002U && endpoint.PortNumber == 1234 && passed;
    for (const char *invalid : {"", "127.0.0.1", "127.0.0.1:0", "127.0.0.1:65536",
        "127.0.0.1:+1", "127.0.0.1:-1", "127.0.0.1: 1", "127.0.0.1:1\n",
        "127.0.0.1:1x", "127.0.0.1:", "127.0.0.256:1", "0.0.0.0:1",
        "255.255.255.255:1", "224.0.0.1:1",
        "127.0.0.1:00000000000000000000000000000000000000000000000000000001"}) {
        const auto unchanged = endpoint;
        passed = !RenegadeNetworkProvider::Parse_Direct_IP(invalid, 0, endpoint) &&
            endpoint.Address == unchanged.Address && endpoint.PortNumber == unchanged.PortNumber && passed;
    }
    printf("direct_client.endpoint_validation=%s\n", passed ? "PASS" : "FAIL");
    bool modern = false;
    passed = RenegadeNetworkProvider::Parse_Client_Request("tt://127.0.0.1:5001", 0, endpoint, modern) &&
        modern && endpoint.Address == 0x7f000001U && endpoint.PortNumber == 5001 && passed;
    passed = RenegadeNetworkProvider::Parse_Client_Request("10.0.0.2:1234", 0, endpoint, modern) &&
        !modern && endpoint.Address == 0x0a000002U && endpoint.PortNumber == 1234 && passed;
    for (const char *invalid : {static_cast<const char *>(nullptr), "tt://", "tt://127.0.0.1", "tt://127.0.0.1:0",
        "tt://127.0.0.1:5001/path", "tt://name:5001", "http://127.0.0.1:5001",
        "TT://127.0.0.1:5001", "tt://tt://127.0.0.1:5001"}) {
        const auto unchanged = endpoint;
        passed = !RenegadeNetworkProvider::Parse_Client_Request(invalid, 0, endpoint, modern) &&
            !modern && endpoint.Address == unchanged.Address && endpoint.PortNumber == unchanged.PortNumber && passed;
    }
    printf("direct_client.explicit_tt_selection=%s\n", passed ? "PASS" : "FAIL");
    for (int cycle = 0; cycle < 3; ++cycle) {
        for (int result = REFUSAL_CLIENT_ACCEPTED; result <= REFUSAL_BY_APPLICATION; ++result)
            passed = Session(static_cast<REFUSAL_CODE>(result)) && passed;
    }
    printf("direct_client.repeated_accept_refuse_cleanup=%s\n", passed ? "PASS" : "FAIL");
    cNetwork::Set_Receiver(nullptr);
    return passed ? 0 : 1;
}

inline int Run_Timeout() {
    setvbuf(stdout, nullptr, _IONBF, 0);
    CombatNetworkReceiverInstanceClass receiver;
    cNetwork::Set_Receiver(&receiver);
    const bool passed = Session(REFUSAL_CLIENT_ACCEPTED, -1);
    cNetwork::Set_Receiver(nullptr);
    return passed ? 0 : 1;
}

inline int Run_Missing_Preset() {
    NetworkObjectFactoryClass *factory = NetworkObjectFactoryMgrClass::Find_Factory(NETCLASSID_GAMEOBJ);
    if (!factory) return 1;
    bool passed = true;
    for (unsigned bits = 0; bits < 32; ++bits) {
        cPacket truncated;
        truncated.Add(0x7f000001);
        truncated.Set_Bit_Write_Position(bits);
        passed = factory->Create(truncated) == nullptr && passed;
    }
    CombatNetworkReceiverInstanceClass receiver;
    cNetwork::Set_Receiver(&receiver);
    passed = Session(REFUSAL_CLIENT_ACCEPTED, -2) && passed;
    passed = Session(REFUSAL_CLIENT_ACCEPTED, -3) && passed;
    passed = !A31ClientConnect::Protocol_Failed() && passed;
    cNetwork::Set_Receiver(nullptr);
    printf("direct_client.missing_preset_stops_session=%s\n", passed ? "PASS" : "FAIL");
    return passed ? 0 : 1;
}

inline int Run_Options() {
    char directory[] = "/tmp/renegade-client-options-XXXXXX";
    if (!mkdtemp(directory)) return 1;
    char data[256], filename[256];
    snprintf(data, sizeof(data), "%s/Data", directory);
    if (mkdir(data, 0700)) return 1;
    snprintf(filename, sizeof(filename), "%s/Data/C&C_Fixture.mix", directory);
    int fd = open(filename, O_CREAT | O_EXCL | O_WRONLY, 0600);
    if (fd < 0) return 1;
    // Only tests original map-name discovery/existence; never loaded as a MIX.
    close(fd);
    const RenegadePathRoots roots = {directory, directory, directory, directory};
    Renegade_Set_Find_Roots(roots);
    RenegadeRootedFileFactoryClass factory(roots);
    FileFactoryClass *old = _TheFileFactory;
    _TheFileFactory = &factory;
    CombatNetworkReceiverInstanceClass receiver;
    cNetwork::Set_Receiver(&receiver);
    bool passed = true;
    for (int cycle = 0; cycle < 2; ++cycle)
        for (int options = 1; options <= 5; ++options)
            passed = Session(REFUSAL_CLIENT_ACCEPTED, options) && passed;
    cNetwork::Set_Receiver(nullptr);
    _TheFileFactory = old;
    unlink(filename);
    rmdir(data);
    rmdir(directory);
    printf("direct_client.original_options_deferred_start=%s\n", passed ? "PASS" : "FAIL");
    return passed ? 0 : 1;
}
}
