#include "netevent.h"
#include "networkobjectfactory.h"
#include "renegade_client_effects.h"
#include "gameobjmanager.h"
#include "physicalgameobj.h"
#include "armedgameobj.h"
#include "weaponbag.h"
#include "weapons.h"

#if defined(RENEGADE_A4_ORIGINAL_FRONTEND) && !RENEGADE_VITA_M00_DEMO
namespace {
// TT b9000 class 2003. Retail import/act: 0x12288100/0x122881d0.
// Own transport/lifetime through cNetEvent; ammunition remains WeaponClass state.
class RenegadeTTWeaponAmmoEvent final : public cNetEvent {
public:
    uint32 Get_Network_Class_ID() const override { return 2003; }
    void Import_Creation(BitStreamClass &packet) override {
        cNetEvent::Import_Creation(packet);
        Set_Delete_Pending();
        if (!Renegade_Client_Uses_TT_Replication()) {
            packet.Mark_Read_Error();
            return;
        }
        int clip = 0, reserve = 0, owner = 0, weapon = 0;
        packet.Get(clip); packet.Get(reserve); packet.Get(owner); packet.Get(weapon);
        if (packet.Has_Read_Error()) return;
        Clip = clip; Reserve = reserve; Owner = owner; Weapon = weapon;
        Act();
    }
    void Export_Creation(BitStreamClass &packet) override {
        cNetEvent::Export_Creation(packet);
        packet.Add(Clip); packet.Add(Reserve); packet.Add(Owner); packet.Add(Weapon);
    }
private:
    void Act() override {
        PhysicalGameObj *physical = GameObjManager::Find_PhysicalGameObj(Owner);
        ArmedGameObj *armed = physical ? physical->As_ArmedGameObj() : NULL;
        WeaponBagClass *bag = armed ? armed->Get_Weapon_Bag() : NULL;
        if (!bag) return; // Retail ignores updates for absent objects/weapons.
        for (int i = 1; i < bag->Get_Count(); ++i) {
            WeaponClass *weapon = bag->Peek_Weapon(i);
            if (weapon && weapon->Get_ID() == Weapon) {
                weapon->Set_Clip_Rounds(Clip);
                weapon->Set_Inventory_Rounds(Reserve);
            }
        }
    }
    int Clip = 0, Reserve = 0, Owner = -1, Weapon = 0;
};
DECLARE_NETWORKOBJECT_FACTORY(RenegadeTTWeaponAmmoEvent, 2003);
}
#endif
