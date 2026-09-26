#include "purchasesettings.h"
#include "teampurchasesettings.h"
#include "networkobjectfactory.h"
#include "renegade_client_effects.h"

#if defined(RENEGADE_A4_ORIGINAL_FRONTEND) && !RENEGADE_VITA_M00_DEMO
namespace {
// Retail b9000 factories resolve existing definitions; they do not allocate.
class PurchaseNetworkFactory final : public NetworkObjectFactoryClass {
public:
    uint32 Get_Class_ID() const override { return 2004; }
    NetworkObjectClass *Create(cPacket &packet) const override {
        int type = -1, team = -1;
        packet.Get(type); packet.Get(team);
        if (packet.Has_Read_Error() || !Renegade_Client_Uses_TT_Replication()) return NULL;
        return PurchaseSettingsDefClass::Find_Network_Definition(type, team);
    }
    void Prep_Packet(NetworkObjectClass *object, cPacket &packet) const override {
        auto *definition = static_cast<PurchaseSettingsDefClass *>(object);
        packet.Add(static_cast<int>(definition->Get_Type()));
        packet.Add(static_cast<int>(definition->Get_Team()));
    }
} PurchaseFactory;

class TeamPurchaseNetworkFactory final : public NetworkObjectFactoryClass {
public:
    uint32 Get_Class_ID() const override { return 2005; }
    NetworkObjectClass *Create(cPacket &packet) const override {
        int team = -1;
        packet.Get(team);
        if (packet.Has_Read_Error() || !Renegade_Client_Uses_TT_Replication()) return NULL;
        return TeamPurchaseSettingsDefClass::Get_Definition(
            static_cast<TeamPurchaseSettingsDefClass::TEAM>(team));
    }
    void Prep_Packet(NetworkObjectClass *object, cPacket &packet) const override {
        auto *definition = static_cast<TeamPurchaseSettingsDefClass *>(object);
        packet.Add(static_cast<int>(definition->Get_Team()));
    }
} TeamPurchaseFactory;
}

void PurchaseSettingsDefClass::Import_Occasional(BitStreamClass &packet)
{
    if (!Renegade_Client_Uses_TT_Replication()) { packet.Mark_Read_Error(); return; }
    bool hidden[MAX_ENTRIES] = {}, disabled[MAX_ENTRIES] = {}, busy[MAX_ENTRIES] = {};
    bool page_hidden = false, page_disabled = false, page_busy = false;
    for (bool &value : hidden) packet.Get(value);
    for (bool &value : disabled) packet.Get(value);
    for (bool &value : busy) packet.Get(value);
    packet.Get(page_hidden); packet.Get(page_disabled); packet.Get(page_busy);
    if (packet.Has_Read_Error()) return;
    for (int i = 0; i < MAX_ENTRIES; ++i) {
        Hidden[i] = hidden[i]; Disabled[i] = disabled[i]; Busy[i] = busy[i];
    }
    PageHidden = page_hidden; PageDisabled = page_disabled; PageBusy = page_busy;
}

void PurchaseSettingsDefClass::Export_Occasional(BitStreamClass &packet)
{
    for (bool value : Hidden) packet.Add(value);
    for (bool value : Disabled) packet.Add(value);
    for (bool value : Busy) packet.Add(value);
    packet.Add(PageHidden); packet.Add(PageDisabled); packet.Add(PageBusy);
}

void TeamPurchaseSettingsDefClass::Import_Occasional(BitStreamClass &packet)
{
    if (!Renegade_Client_Uses_TT_Replication()) { packet.Mark_Read_Error(); return; }
    bool hidden[MAX_ENTRIES] = {}, disabled[MAX_ENTRIES] = {}, busy[MAX_ENTRIES] = {};
    for (bool &value : hidden) packet.Get(value);
    for (bool &value : disabled) packet.Get(value);
    for (bool &value : busy) packet.Get(value);
    if (packet.Has_Read_Error()) return;
    for (int i = 0; i < MAX_ENTRIES; ++i) {
        Hidden[i] = hidden[i]; Disabled[i] = disabled[i]; Busy[i] = busy[i];
    }
}

void TeamPurchaseSettingsDefClass::Export_Occasional(BitStreamClass &packet)
{
    for (bool value : Hidden) packet.Add(value);
    for (bool value : Disabled) packet.Add(value);
    for (bool value : Busy) packet.Add(value);
}
#endif
