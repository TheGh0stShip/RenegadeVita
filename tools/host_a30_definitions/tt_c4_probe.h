#pragma once
#include "renegade_c4_state.h"
#include "tt_purchase_probe.h"
#include "c4.h"
#include "projectile.h"
#include "definitionmgr.h"
#include "weaponmanager.h"
#include "vehicle.h"

inline void Write_TT_C4(BitStreamClass &packet, int mode, int ammo = 123456, int owner = 1234, int target = 5678)
{
    packet.Add(ammo); packet.Add(owner);
    for (float value : {1.0f, 2.0f, 3.0f}) packet.Add(value);
    packet.Add(mode != 0);
    if (mode) {
        for (float value : {100.125f, 200.25f, 30.5f}) packet.Add(value);
        packet.Add(mode == 3); packet.Add(mode == 2); packet.Add(mode == 2 ? target : -1);
        if (mode == 2) {
            for (float value : {0.25f, -0.5f, 0.75f}) packet.Add(value);
            packet.Add(3);
        }
        packet.Add(mode == 3);
        if (mode == 3) packet.Add(42U);
    }
}

inline int Validate_TT_C4_Vectors()
{
    bool passed = true;
    unsigned truncations = 0;
    for (int mode = 0; mode < 4; ++mode) {
        BitStreamClass packet;
        Write_TT_C4(packet, mode);
        const unsigned bits = packet.Get_Bit_Write_Position();
        printf("tt_c4.vector_%d=%u:", mode, bits);
        for (unsigned i = 0; i < (bits + 7) / 8; ++i) printf("%02x", static_cast<unsigned char>(packet.Get_Data()[i]));
        printf("\n");
        RenegadeC4RareState state;
        passed = Renegade_Read_C4_Rare(packet, state) && packet.Is_Flushed() &&
            state.AmmoID == 123456 && state.OwnerID == 1234 && state.Stuck == (mode != 0) &&
            state.Dynamic == (mode == 2) && state.Static == (mode == 3) &&
            state.Velocity == Vector3(1, 2, 3) && passed;
        for (unsigned end = 0; end < bits; ++end) {
            BitStreamClass short_packet;
            Write_TT_C4(short_packet, mode);
            short_packet.Set_Bit_Write_Position(end);
            RenegadeC4RareState sentinel;
            sentinel.OwnerID = 999;
            passed = !Renegade_Read_C4_Rare(short_packet, sentinel) && short_packet.Has_Read_Error() &&
                sentinel.OwnerID == 999 && passed;
            ++truncations;
        }
    }
    printf("tt_c4.truncations=%u result=%s\n", truncations, passed ? "PASS" : "FAIL");
    return passed ? 0 : 1;
}

inline bool Validate_TT_C4_Runtime(SoldierGameObj &owner)
{
    auto *definition = DefinitionMgrClass::Find_Typed_Definition("Tossed C4", CLASSID_GAME_OBJECT_DEF_C4);
    // This ID is the ammunition definition in the captured RenCorner C4 update.
    const auto *ammo = WeaponManager::Find_Ammo_Definition(3077);
    if (!definition || !ammo || static_cast<int>(ammo->AmmoType) == AmmoDefinitionClass::AMMO_TYPE_NORMAL) return false;
    TTPurchaseProfileScope profile;
    VehicleGameObj::Set_Precision();
    for (int field : {BITPACK_WORLD_POSITION_X, BITPACK_WORLD_POSITION_Y, BITPACK_WORLD_POSITION_Z})
        cEncoderList::Set_Precision(field, -1000.0, 1000.0, 0.01);
    C4GameObj charge;
    charge.Init(*static_cast<C4GameObjDef *>(definition));
    charge.Init_C4(ammo, &owner, 1, owner.Get_Transform());
    bool passed = charge.Peek_Physical_Object()->As_ProjectileClass() != NULL;
    const auto prefix = [&](BitStreamClass &packet) {
        packet.Add(1); packet.Add(0); packet.Add(BYTE(0)); packet.Add(8); packet.Add(false);
        packet.Add_Terminated_String(charge.Peek_Model()->Get_Name(), true);
        packet.Add_Terminated_String("", true);
        for (int value : {0, 0, 3, 0, 0, 1}) packet.Add(value);
        packet.Add(false); packet.Add(false);
    };
    for (int mode : {0, 1, 2}) {
        BitStreamClass packet;
        prefix(packet); Write_TT_C4(packet, mode, ammo->Get_ID(), owner.Get_ID(), owner.Get_ID());
        packet.Add(0x12345678);
        charge.Import_Rare(packet);
        int following = 0; packet.Get(following);
        const bool imported = !packet.Has_Read_Error() && packet.Is_Flushed() && following == 0x12345678 &&
            charge.Get_Owner() == &owner;
        passed = imported && passed;
        // Read back original serialized C4 state, not test-only access to private fields.
        BitStreamClass inherited, outgoing;
        charge.SimpleGameObj::Export_Rare(inherited);
        charge.Export_Rare(outgoing);
        for (unsigned bits = inherited.Get_Bit_Write_Position(); bits;) {
            const unsigned width = bits > 32 ? 32 : bits;
            ULONG ignored = 0;
            outgoing.Get_Bits(ignored, width);
            bits -= width;
        }
        RenegadeC4RareState state;
        const bool exported = Renegade_Read_C4_Rare(outgoing, state, false) && outgoing.Is_Flushed();
        passed = exported &&
            state.AmmoID == ammo->Get_ID() && state.OwnerID == owner.Get_ID() &&
            state.Stuck == (mode != 0) && state.Dynamic == (mode == 2) &&
            (state.Velocity - Vector3(1, 2, 3)).Length() < 0.02f && passed;
        if (mode) passed = (state.Position - Vector3(100.125f, 200.25f, 30.5f)).Length() < 0.1f && passed;
        if (mode == 2) passed = state.ObjectID == owner.Get_ID() && state.Bone == 3 &&
            (state.Offset - Vector3(0.25f, -0.5f, 0.75f)).Length() < 0.02f && passed;
        printf("tt_c4.mode=%d import=%d export=%d owner=%d/%d ammo=%d/%d stuck=%d dynamic=%d "
               "velocity=%.3f,%.3f,%.3f position=%.3f,%.3f,%.3f offset=%.3f,%.3f,%.3f bone=%d\n",
               mode, imported, exported, state.OwnerID, owner.Get_ID(), state.AmmoID, ammo->Get_ID(),
               state.Stuck, state.Dynamic, state.Velocity.X, state.Velocity.Y, state.Velocity.Z,
               state.Position.X, state.Position.Y, state.Position.Z, state.Offset.X, state.Offset.Y,
               state.Offset.Z, state.Bone);
    }
    BitStreamClass bad_ammo;
    prefix(bad_ammo); Write_TT_C4(bad_ammo, 0, owner.Get_Definition().Get_ID());
    charge.Import_Rare(bad_ammo);
    passed = bad_ammo.Has_Read_Error() && passed;
    printf("tt_c4.loaded_state=%s\n", passed ? "PASS" : "FAIL");
    return passed;
}
