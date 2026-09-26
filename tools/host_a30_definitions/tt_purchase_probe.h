#pragma once
#include "purchasesettings.h"
#include "teampurchasesettings.h"
#include "networkobjectfactorymgr.h"
#include "networkobjectfactory.h"
#include "networkobjectmgr.h"
#include "cnetwork.h"
#include "connect.h"
#include "gametype.h"
#include "combat.h"

class TTPurchaseProfileScope {
public:
    TTPurchaseProfileScope() : Client(cNetwork::PClientConnection), Server(cNetwork::PServerConnection),
        Type(cGameType::Get_Game_Type()), Compression(cEncoderList::Is_Compression_Enabled()) {
        Connection.Set_TT_Client_Greeting(true);
        cNetwork::PClientConnection = &Connection;
        cNetwork::PServerConnection = NULL;
        cGameType::Set_Game_Type(GAMETYPE_MULTIPLAY);
    }
    ~TTPurchaseProfileScope() {
        cNetwork::PClientConnection = Client; cNetwork::PServerConnection = Server;
        cGameType::Set_Game_Type(Type);
        cEncoderList::Set_Compression_Enabled(Compression);
    }
private:
    cConnection Connection;
    cConnection *Client, *Server;
    GameTypeEnum Type;
    bool Compression;
};

class TTPurchaseDefinitionFixture : public PurchaseSettingsDefClass {
public:
    TTPurchaseDefinitionFixture() {
        Team = TEAM_NOD; Type = TYPE_NAVAL;
        Previous = DefinitionArray[Type][Team]; DefinitionArray[Type][Team] = this;
    }
    ~TTPurchaseDefinitionFixture() { DefinitionArray[Type][Team] = Previous; }
private:
    PurchaseSettingsDefClass *Previous;
};

class TTTeamPurchaseDefinitionFixture : public TeamPurchaseSettingsDefClass {
public:
    TTTeamPurchaseDefinitionFixture() {
        Team = TEAM_NOD;
        Previous = DefinitionArray[Team]; DefinitionArray[Team] = this;
    }
    ~TTTeamPurchaseDefinitionFixture() { DefinitionArray[Team] = Previous; }
private:
    TeamPurchaseSettingsDefClass *Previous;
};

inline void TT_Purchase_Write_Flags(BitStreamClass &packet, int count, int pattern)
{
    for (int i = 0; i < count; ++i) packet.Add(pattern == 1 || (pattern == 2 && i % 3 == 1));
}

inline int Validate_TT_Purchase_Catalogs()
{
    TTPurchaseProfileScope profile;
    bool passed = true;
    unsigned vector = 0, truncations = 0;
    const auto check = [&](bool ok, const char *name) {
        if (!ok) printf("tt_purchase.failure=%s\n", name);
        passed = ok && passed;
    };
    TTPurchaseDefinitionFixture page;
    TTTeamPurchaseDefinitionFixture team;
    check(page.Get_Network_ID() == 0 && team.Get_Network_ID() == 0, "deferred_registration");
    for (bool team_catalog : {false, true}) {
        NetworkObjectClass *object = team_catalog ? static_cast<NetworkObjectClass *>(&team) : &page;
        const int count = team_catalog ? 12 : 33;
        auto *factory = NetworkObjectFactoryMgrClass::Find_Factory(team_catalog ? 2005 : 2004);
        if (!factory) return 1;
        for (int pattern : {0, 1, 2}) for (bool compression : {false, true}) {
            cEncoderList::Set_Compression_Enabled(compression);
            BitStreamClass packet;
            TT_Purchase_Write_Flags(packet, count, pattern);
            object->Import_Occasional(packet);
            check(!packet.Has_Read_Error() && packet.Is_Flushed(), "import");
            const int entries = team_catalog ? 4 : 10;
            for (int i = 0; i < entries; ++i) {
                const auto expected = [&](int flag) { return pattern == 1 || (pattern == 2 && flag % 3 == 1); };
                check((team_catalog ? team.Get_Hidden(i) : page.Get_Hidden(i)) == expected(i), "hidden");
                check((team_catalog ? team.Get_Disabled(i) : page.Get_Disabled(i)) == expected(i + entries), "disabled");
                check((team_catalog ? team.Get_Busy(i) : page.Get_Busy(i)) == expected(i + entries * 2), "busy");
            }
            if (!team_catalog) {
                check(page.Get_Page_Hidden() == (pattern == 1) &&
                    page.Get_Page_Disabled() == (pattern != 0) && page.Get_Page_Busy() == (pattern == 1), "page_flags");
            }
            BitStreamClass output;
            object->Export_Occasional(output);
            printf("tt_purchase.vector_%u=%u:", vector++, output.Get_Bit_Write_Position());
            for (unsigned i = 0; i < (output.Get_Bit_Write_Position() + 7) / 8; ++i)
                printf("%02x", static_cast<unsigned char>(output.Get_Data()[i]));
            printf("\n");
            for (unsigned end = 0; end < output.Get_Bit_Write_Position(); ++end) {
                BitStreamClass malformed;
                TT_Purchase_Write_Flags(malformed, count, pattern == 0 ? 1 : 0);
                malformed.Set_Bit_Write_Position(end);
                object->Import_Occasional(malformed);
                BitStreamClass unchanged;
                object->Export_Occasional(unchanged);
                check(malformed.Has_Read_Error() && unchanged.Get_Bit_Write_Position() == output.Get_Bit_Write_Position() &&
                    memcmp(unchanged.Get_Data(), output.Get_Data(), (output.Get_Bit_Write_Position() + 7) / 8) == 0, "transactional_truncation");
                ++truncations;
            }
            cPacket identity;
            factory->Prep_Packet(object, identity);
            printf("tt_purchase.factory_%u=%u:", vector - 1, identity.Get_Bit_Write_Position());
            for (unsigned i = 0; i < identity.Get_Bit_Write_Position() / 8; ++i)
                printf("%02x", static_cast<unsigned char>(identity.Get_Data()[i]));
            printf("\n");
            check(factory->Create(identity) == object && identity.Is_Flushed(), "factory_existing_identity");
            for (unsigned end = 0; end < identity.Get_Bit_Write_Position(); ++end) {
                cPacket malformed;
                factory->Prep_Packet(object, malformed);
                malformed.Set_Bit_Write_Position(end);
                check(factory->Create(malformed) == NULL && malformed.Has_Read_Error(), "factory_truncation");
            }
        }
        for (int invalid : {-2147483647, -1, 7, 2147483647}) {
            cPacket bad;
            if (!team_catalog) bad.Add(invalid);
            bad.Add(invalid);
            check(factory->Create(bad) == NULL, "factory_index_bounds");
        }
        object->Set_Network_ID(900001 + int(team_catalog));
        check(NetworkObjectMgrClass::Find_Object(object->Get_Network_ID()) == object, "network_registration");
        object->Set_Delete_Pending(); object->Delete();
        NetworkObjectMgrClass::Delete_Pending();
        check(!object->Is_Delete_Pending() && NetworkObjectMgrClass::Find_Object(object->Get_Network_ID()) == object,
            "definition_owned_lifetime");
    }
    printf("tt_purchase.transactional_truncations=%u result=%s\n", truncations, passed ? "PASS" : "FAIL");
    return passed ? 0 : 1;
}
