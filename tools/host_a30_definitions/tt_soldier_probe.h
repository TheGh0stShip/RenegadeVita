#pragma once
#include "renegade_soldier_rare.h"
#include "soldier.h"
#include "humanphys.h"
#include "cnetwork.h"
#include "connect.h"
#include "gametype.h"
#include "bitpackids.h"
#include "encoderlist.h"
#include "ramfile.h"
#include "chunkio.h"
#include "weaponbag.h"
#include "weapons.h"
#include "networkobjectfactory.h"
#include "networkobjectfactorymgr.h"
#include <cstdio>

inline void Write_TT_Soldier_Frequent(BitStreamClass &packet, int state,
    bool weapon = false, bool damage = false, bool do_tilt = true)
{
    packet.Add(state == HumanStateClass::IN_VEHICLE);
    if (state != HumanStateClass::IN_VEHICLE) {
        packet.Add(weapon);
        if (weapon) packet.Add(123456);
        packet.Add(100.125f); packet.Add(200.25f); packet.Add(30.5f);
        packet.Add(state, BITPACK_HUMAN_STATE);
        packet.Add(1, BITPACK_HUMAN_SUB_STATE);
        if (state == HumanStateClass::LADDER) packet.Add(1.5707963267948966f);
        if (state == HumanStateClass::AIRBORNE) {
            packet.Add(1.0f); packet.Add(2.0f); packet.Add(3.0f);
        }
        if (state == HumanStateClass::ANIMATION || state == HumanStateClass::TRANSITION)
            packet.Add_Terminated_String("S_A_HUMAN.H_A_422A");
        packet.Add(damage);
        if (damage) packet.Add(1);
        packet.Add(do_tilt);
    }
    // Complete reference payload includes Smart state even for a diving soldier.
    packet.Add(false);
    packet.Add(12.5f); packet.Add(-20.25f); packet.Add(31.125f);
    packet.Add(false); packet.Add(true);
    ControlClass control;
    control.Set_Boolean(ControlClass::BOOLEAN_WEAPON_FIRE_PRIMARY, true);
    control.Set_Boolean(ControlClass::BOOLEAN_WALK, true);
    control.Set_Analog(ControlClass::ANALOG_MOVE_FORWARD, 1.0f);
    control.Set_Analog(ControlClass::ANALOG_MOVE_LEFT, -1.0f);
    control.Set_Analog(ControlClass::ANALOG_TURN_LEFT, 0.5f);
    control.Export_Sc(packet);
}

inline int Validate_TT_Soldier_Frequent()
{
    ControlClass::Set_Precision();
    HumanStateClass::Set_Precision();
    const int states[] = {0, 2, 5, 6, 8, 9, 10, 0, 0};
    for (int profile = 0; profile < 9; ++profile) {
        BitStreamClass packet;
        Write_TT_Soldier_Frequent(packet, states[profile], profile == 7, profile == 8);
        printf("tt_soldier_frequent.vector_%d=%u:", profile, packet.Get_Bit_Write_Position());
        for (unsigned i = 0; i < (packet.Get_Bit_Write_Position() + 7) / 8; ++i)
            printf("%02x", static_cast<unsigned char>(packet.Get_Data()[i]));
        printf("\n");
    }
    for (int sniping : {0, 1}) {
        BitStreamClass packet;
        packet.Add(sniping != 0);
        packet.Add(12.5f - 100.125f);
        packet.Add(-20.25f - 200.25f);
        packet.Add(31.125f - 30.5f);
        printf("tt_soldier_cs.vector_%d=%u:", sniping, packet.Get_Bit_Write_Position());
        for (unsigned i = 0; i < (packet.Get_Bit_Write_Position() + 7) / 8; ++i)
            printf("%02x", static_cast<unsigned char>(packet.Get_Data()[i]));
        printf("\n");
    }
    return 0;
}

inline void Write_TT_Smart_Frequent(BitStreamClass &packet, bool modern, bool alternate)
{
    packet.Add(false);
    const Vector3 target(12.5f, -20.25f, 31.125f);
    if (modern) {
        packet.Add(target.X); packet.Add(target.Y); packet.Add(target.Z);
        packet.Add(alternate); packet.Add(!alternate);
    } else {
        packet.Add(target.X, BITPACK_WORLD_POSITION_X);
        packet.Add(target.Y, BITPACK_WORLD_POSITION_Y);
        packet.Add(target.Z, BITPACK_WORLD_POSITION_Z);
    }
    ControlClass control;
    control.Set_Boolean(ControlClass::BOOLEAN_WEAPON_FIRE_PRIMARY, true);
    control.Set_Boolean(ControlClass::BOOLEAN_WALK, true);
    control.Set_Analog(ControlClass::ANALOG_MOVE_FORWARD, 1.0f);
    control.Set_Analog(ControlClass::ANALOG_MOVE_LEFT, -1.0f);
    control.Set_Analog(ControlClass::ANALOG_TURN_LEFT, 0.5f);
    control.Export_Sc(packet);
}

inline int Validate_TT_Smart_Frequent()
{
    ControlClass::Set_Precision();
    for (int field : {BITPACK_WORLD_POSITION_X, BITPACK_WORLD_POSITION_Y, BITPACK_WORLD_POSITION_Z})
        cEncoderList::Set_Precision(field, -1000.0, 1000.0, 0.01);
    for (int profile = 0; profile < 3; ++profile) {
        BitStreamClass packet;
        Write_TT_Smart_Frequent(packet, profile != 0, profile == 2);
        printf("tt_smart.vector_%d=%u:", profile, packet.Get_Bit_Write_Position());
        for (unsigned i = 0; i < (packet.Get_Bit_Write_Position() + 7) / 8; ++i)
            printf("%02x", static_cast<unsigned char>(packet.Get_Data()[i]));
        printf("\n");
    }
    return 0;
}

inline void Write_TT_Defense(BitStreamClass &packet, bool modern, bool zero = false)
{
    packet.Add(zero);
    packet.Add(zero ? 0 : (modern ? 8000 : 100), modern ? BITPACK_TT_HEALTH : BITPACK_HEALTH);
    packet.Add(modern ? 5000 : 50, modern ? BITPACK_TT_SHIELD_STRENGTH : BITPACK_SHIELD_STRENGTH);
    packet.Add(3u, BITPACK_SHIELD_TYPE);
    if (modern) {
        packet.Add(9000, BITPACK_TT_HEALTH);
        packet.Add(6000, BITPACK_TT_SHIELD_STRENGTH);
        packet.Add(1u, BITPACK_SHIELD_TYPE);
    }
}

inline int Validate_TT_Defense()
{
    cEncoderList::Set_Precision(BITPACK_HEALTH, 0, 2000);
    cEncoderList::Set_Precision(BITPACK_SHIELD_STRENGTH, 0, 2000);
    cEncoderList::Set_Precision(BITPACK_SHIELD_TYPE, 0, 31);
    cEncoderList::Set_Precision(BITPACK_TT_HEALTH, 0, 10000);
    cEncoderList::Set_Precision(BITPACK_TT_SHIELD_STRENGTH, 0, 10000);
    for (int profile = 0; profile < 3; ++profile) {
        BitStreamClass packet;
        Write_TT_Defense(packet, profile != 0, profile == 2);
        printf("tt_defense.vector_%d=%u:", profile, packet.Get_Bit_Write_Position());
        for (unsigned i = 0; i < (packet.Get_Bit_Write_Position() + 7) / 8; ++i)
            printf("%02x", static_cast<unsigned char>(packet.Get_Data()[i]));
        printf("\n");
    }
    return 0;
}

inline void Write_TT_Soldier_Suffix(BitStreamClass &packet, bool alternate, bool unit_scale = false)
{
    packet.Add(!alternate); packet.Add(true); packet.Add(alternate);
    packet.Add(alternate); packet.Add(!alternate);
    packet.Add(alternate && !unit_scale ? 1.25f : 1.0f); packet.Add(!alternate);
    packet.Add(alternate ? 1.75f : 1.0f); packet.Add(alternate);
    packet.Add(alternate ? 0.2f : 0.0f); packet.Add(alternate ? -0.1f : 0.0f);
    packet.Add(alternate ? 2 : -1); packet.Add(alternate);
    const WCHAR tag[] = {'V','i','t','a','B','o','t',0};
    const WCHAR empty[] = {0};
    packet.Add_Wide_Terminated_String(alternate ? tag : empty, true);
    packet.Add(!alternate);
    for (float number : {0.4f, 0.3f, 0.05f, 0.1f}) packet.Add(alternate ? number : 0.0f);
}

inline bool Validate_TT_Soldier_Runtime(const SoldierGameObjDef &definition)
{
    // This direct world fixture bypasses CombatGameMode's network precision setup.
    ControlClass::Set_Precision();
    DefenseObjectClass::Set_Precision();
    HumanStateClass::Set_Precision();
    struct ProbeSoldier : SoldierGameObj {
        using SoldierGameObj::Update_TT_Skeleton;
        using SoldierGameObj::Get_State;
        using SoldierGameObj::Get_Sub_State;
        using SoldierGameObj::Update_Locked_Facing;
        void Reset_State() { HumanState.Set_State(HumanStateClass::UPRIGHT); }
        bool Network_Do_Tilt() const { return NetworkDoTilt; }
        void Clear_Target_Update() { NetworkTargetUpdated = false; }
        void Set_Sniping(bool on) {
            if (Is_Sniping() != on) HumanState.Toggle_State_Flag(HumanStateClass::SNIPING_FLAG);
        }
        void Lock_Animation() { HumanState.Start_Scripted_Animation("S_A_HUMAN.H_A_422A"); }
        float Saved_Aiming_Tilt() {
            // Inspect original serialized state without exposing test-only engine accessors.
            unsigned char bytes[4096] = {};
            RAMFileClass file(bytes, sizeof(bytes));
            file.Open(FileClass::WRITE);
            ChunkSaveClass save(&file);
            HumanState.Save(save);
            file.Close(); file.Open(FileClass::READ);
            ChunkLoadClass load(&file);
            while (load.Open_Chunk()) {
                while (load.Open_Micro_Chunk()) {
                    if (load.Cur_Micro_Chunk_ID() == 6 && load.Cur_Micro_Chunk_Length() == sizeof(float)) {
                        float tilt = 0;
                        load.Read(&tilt, sizeof(tilt));
                        load.Close_Micro_Chunk(); load.Close_Chunk();
                        return tilt;
                    }
                    load.Close_Micro_Chunk();
                }
                load.Close_Chunk();
            }
            return 1.0e30f;
        }
        bool Network_Stealth_Active() const { return NetworkStealthActive; }
    };
    ProbeSoldier soldier;
    soldier.Init(definition);
    if (!soldier.Peek_Model()) return false;
    bool passed = !soldier.Get_TT_State() && soldier.Can_Drive_Vehicles() && soldier.Can_Steal_Vehicles();
    const auto check = [&passed](bool result, const char *name) {
        printf("tt_soldier.runtime.%s=%s\n", name, result ? "PASS" : "FAIL");
        passed = result && passed;
    };
    for (unsigned int word : {0u, 3u, 0x7fffffffu, 0x80000000u, 0xffffffffu}) {
        safe_unsigned_int value(word);
        safe_unsigned_int adjacent(0xdeadbeefu);
        int32_t signed_word;
        memcpy(&signed_word, &word, sizeof(signed_word));
        check(static_cast<unsigned long>(value) == static_cast<unsigned long>(word) &&
            static_cast<long>(value) == static_cast<long>(signed_word) &&
            static_cast<unsigned int>(adjacent) == 0xdeadbeefu, "datasafe_long_word");
    }
    cConnection connection;
    connection.Set_TT_Client_Greeting(true);
    cConnection *old_client = cNetwork::PClientConnection, *old_server = cNetwork::PServerConnection;
    const GameTypeEnum old_type = cGameType::Get_Game_Type();
    const bool old_is_server = CombatManager::I_Am_Server(), old_is_client = CombatManager::I_Am_Client();
    cNetwork::PClientConnection = &connection;
    cNetwork::PServerConnection = NULL;
    CombatManager::Set_I_Am_Server(false);
    CombatManager::Set_I_Am_Client(true);
    cGameType::Set_Game_Type(GAMETYPE_MULTIPLAY);
    for (bool alternate : {false, true}) {
        BitStreamClass packet;
        packet.Add(2); packet.Add(1); packet.Add(static_cast<BYTE>(0));
        packet.Add(6); packet.Add(false);
        packet.Add_Terminated_String(soldier.Peek_Model()->Get_Name(), true);
        packet.Add_Terminated_String("", true);
        for (int value : {0, 0, 3, 0, 0, 1}) packet.Add(value);
        packet.Add(false); packet.Add(false);
        packet.Add(definition.Get_ID());
        Write_TT_Soldier_Suffix(packet, alternate, true);
        soldier.Import_Rare(packet);
        const RenegadeSoldierRareState *state = soldier.Get_TT_State();
        check(!packet.Has_Read_Error() && packet.Is_Flushed() && state, "import_complete");
        if (state) {
            check(soldier.Get_Max_Speed() == (alternate ? 1.75f : 1.0f) &&
                soldier.Can_Steal_Vehicles() == !alternate && state->Freeze == alternate &&
                state->BotTag.Get_Length() == (alternate ? 7 : 0), "speed_flags_tag");
            if (alternate) {
                soldier.Set_Analog_Control(ControlClass::ANALOG_MOVE_FORWARD, 1.0f);
                soldier.Set_Boolean_Control(ControlClass::BOOLEAN_ACTION, true);
                soldier.Set_Boolean_Control(ControlClass::BOOLEAN_WEAPON_FIRE_PRIMARY, true);
                check(CombatManager::Is_Gameplay_Permitted(), "gameplay_active");
                soldier.Apply_Control();
                check(soldier.Get_Control().Get_Analog(ControlClass::ANALOG_MOVE_FORWARD) == 0 &&
                    !soldier.Get_Control().Get_Boolean(ControlClass::BOOLEAN_ACTION) &&
                    !soldier.Get_Control().Get_Boolean(ControlClass::BOOLEAN_WEAPON_FIRE_PRIMARY), "frozen_control");
                soldier.Update_TT_Skeleton(2.0f);
                check(WWMath::Fabs(state->SkeletonHeight - 0.3f) < 0.00001f &&
                    WWMath::Fabs(state->SkeletonWidth - 0.1f) < 0.00001f, "skeleton_approach");
                soldier.Update_TT_Skeleton(100.0f);
                check(state->SkeletonHeight == 0.4f && state->SkeletonWidth == 0.3f, "skeleton_target");
            }
        }
    }
    for (bool local : {false, true}) {
        soldier.Set_Control_Owner(local ? CombatManager::Get_My_Id() : SmartGameObj::SERVER_CONTROL_OWNER);
        check(soldier.Is_Controlled_By_Me() == local, "control_ownership");
        soldier.SmartGameObj::Set_Targeting(Vector3(3, 4, 5));
        soldier.Clear_Control();
        soldier.Set_Analog_Control(ControlClass::ANALOG_MOVE_FORWARD, 0.25f);
        for (bool alternate : {false, true}) {
            BitStreamClass packet;
            Write_TT_Smart_Frequent(packet, true, alternate);
            packet.Add(0x12345678);
            soldier.SmartGameObj::Import_Frequent(packet);
            int following = 0;
            packet.Get(following);
            check(!packet.Has_Read_Error() && packet.Is_Flushed() && following == 0x12345678,
                "smart_consumes_exact_payload");
            check(soldier.Is_Stealth_Enabled() == alternate &&
                soldier.Network_Stealth_Active() == !alternate, "smart_stealth_flags");
            const Vector3 &target = soldier.Get_Targeting_Pos();
            check(target == (local ? Vector3(3, 4, 5) : Vector3(12.5f, -20.25f, 31.125f)),
                "smart_target_owner");
            check(soldier.Get_Control().Get_Analog(ControlClass::ANALOG_MOVE_FORWARD) ==
                (local ? 0.25f : 1.0f), "smart_control_owner");
        }
        for (unsigned end = 0; end < 135; ++end) {
            BitStreamClass packet;
            Write_TT_Smart_Frequent(packet, true, false);
            packet.Set_Bit_Write_Position(end);
            soldier.SmartGameObj::Import_Frequent(packet);
            if (!packet.Has_Read_Error()) check(false, "smart_truncation_rejected");
        }
    }
    soldier.Set_Control_Owner(SmartGameObj::SERVER_CONTROL_OWNER);
    DefenseObjectClass defense;
    for (bool zero : {false, true}) {
        BitStreamClass packet;
        Write_TT_Defense(packet, true, zero);
        defense.Import(packet);
        printf("tt_defense.runtime_values=health:%g,max:%g,shield:%g,max:%g,skin:%u,type:%lu,error:%d\n",
            defense.Get_Health(), defense.Get_Health_Max(), defense.Get_Shield_Strength(),
            defense.Get_Shield_Strength_Max(), defense.Get_Skin(), defense.Get_Shield_Type(),
            packet.Has_Read_Error());
        check(!packet.Has_Read_Error() && packet.Is_Flushed() &&
            defense.Get_Health() == (zero ? 0.0f : 8000.0f) && defense.Get_Health_Max() == 9000 &&
            defense.Get_Shield_Strength() == 5000 && defense.Get_Shield_Strength_Max() == 6000 &&
            defense.Get_Skin() == 1 && defense.Get_Shield_Type() == 3, "defense_state");
    }
    BitStreamClass full_defense;
    Write_TT_Defense(full_defense, true);
    for (unsigned end = 0; end < full_defense.Get_Bit_Write_Position(); ++end) {
        BitStreamClass short_packet;
        short_packet = full_defense;
        short_packet.Set_Bit_Write_Position(end);
        defense.Import(short_packet);
        if (!short_packet.Has_Read_Error() || defense.Get_Health() != 0 || defense.Get_Health_Max() != 9000)
            check(false, "defense_atomic_truncation");
    }
    printf("tt_defense.runtime_truncations=%u\n", full_defense.Get_Bit_Write_Position());
    WeaponClass *initial_weapon = soldier.Get_Weapon();
    check(initial_weapon != NULL, "occasional_initial_weapon");
    if (initial_weapon) {
        initial_weapon->Set_Clip_Rounds(3);
        initial_weapon->Set_Inventory_Rounds(7);
        BitStreamClass packet;
        Write_TT_Defense(packet, true);
        packet.Add(1); packet.Add(initial_weapon->Get_ID());
        packet.Add(false); packet.Add(false);
        packet.Add(0x12345678);
        soldier.Import_Occasional(packet);
        int following = 0;
        packet.Get(following);
        check(!packet.Has_Read_Error() && packet.Is_Flushed() && following == 0x12345678 &&
            soldier.Get_Weapon() == initial_weapon && initial_weapon->Get_Clip_Rounds() == 3 &&
            initial_weapon->Get_Inventory_Rounds() == 7, "occasional_selection_preserves_ammo_and_tail");
        auto *factory = NetworkObjectFactoryMgrClass::Find_Factory(2003);
        check(factory != NULL, "ammo_event_factory");
        if (factory) {
            const auto event = [&](int clip, int reserve, int owner, int weapon, unsigned bits = 128) {
                cPacket update;
                update.Add(clip); update.Add(reserve); update.Add(owner); update.Add(weapon);
                update.Set_Bit_Write_Position(bits);
                NetworkObjectClass *object = factory->Create(update);
                object->Import_Creation(update);
                return update.Has_Read_Error(); // Original pending-delete owner frees the event.
            };
            check(!event(2, -1, soldier.Get_ID(), initial_weapon->Get_ID()) &&
                initial_weapon->Get_Clip_Rounds() == 2 && initial_weapon->Get_Inventory_Rounds() == -1,
                "ammo_event_unlimited");
            for (unsigned end = 0; end < 128; ++end)
                if (!event(9, 17, soldier.Get_ID(), initial_weapon->Get_ID(), end) ||
                    initial_weapon->Get_Clip_Rounds() != 2 || initial_weapon->Get_Inventory_Rounds() != -1)
                    check(false, "ammo_event_atomic_truncation");
            check(!event(9, 17, 0x7ffffffe, initial_weapon->Get_ID()) &&
                !event(9, 17, soldier.Get_ID(), 0) &&
                initial_weapon->Get_Clip_Rounds() == 2 && initial_weapon->Get_Inventory_Rounds() == -1,
                "ammo_event_missing_target");
            check(!event(5, 31, soldier.Get_ID(), initial_weapon->Get_ID()) &&
                initial_weapon->Get_Clip_Rounds() == 5 && initial_weapon->Get_Inventory_Rounds() == 31,
                "ammo_event_authoritative_counts");
        }
    }
    for (bool local : {false, true}) {
        soldier.Set_Control_Owner(local ? CombatManager::Get_My_Id() : SmartGameObj::SERVER_CONTROL_OWNER);
        for (bool active : {true, false}) {
            BitStreamClass packet;
            Write_TT_Defense(packet, true);
            packet.Add(0); // Soldier ID-only list; selection belongs to frequent state.
            packet.Add(active); packet.Add(active);
            soldier.Import_Occasional(packet);
            check(!packet.Has_Read_Error() && packet.Is_Flushed(), "occasional_complete");
            check(soldier.Is_Sniping() == (!local && active), "sniping_owner");
            check(soldier.Get_State() == (active ? HumanStateClass::DEBUG_FLY : HumanStateClass::UPRIGHT),
                "fly_state_transition");
            check(soldier.Peek_Physical_Object()->Get_Collision_Group() ==
                (active ? UNCOLLIDEABLE_GROUP : SOLDIER_COLLISION_GROUP), "fly_collision_transition");
        }
    }
    soldier.Set_Control_Owner(SmartGameObj::SERVER_CONTROL_OWNER);
    soldier.Re_Init(definition);
    check(soldier.Network_Stealth_Active(), "reinit_restores_stealth_active");
    soldier.Set_Position(Vector3(100.125f, 200.25f, 30.5f));
    soldier.ArmedGameObj::Set_Targeting(Vector3(12.5f, -20.25f, 31.125f));
    for (bool sniping : {false, true}) {
        soldier.Set_Sniping(sniping);
        soldier.Set_Boolean_Control(ControlClass::BOOLEAN_ACTION, true);
        BitStreamClass packet;
        soldier.Export_State_Cs(packet);
        bool decoded_sniping = false;
        Vector3 aim(0, 0, 0);
        packet.Get(decoded_sniping);
        packet.Get(aim.X); packet.Get(aim.Y); packet.Get(aim.Z);
        check(!packet.Has_Read_Error() && packet.Get_Bit_Write_Position() == 97 &&
            packet.Is_Flushed() && decoded_sniping == sniping &&
            aim == Vector3(-87.625f, -220.5f, 0.625f), "outgoing_sniping_relative_aim");
    }
    soldier.Set_Sniping(false);
    soldier.Clear_Control();
    HumanPhysClass *physics = soldier.Peek_Human_Phys();
    physics->Set_Position(Vector3(0, 0, 30));
    physics->Set_Velocity(Vector3(1, 2, 3));
    physics->Network_Interpolated_State_Update(Vector3(1, 0, 30), false);
    Vector3 physics_position, physics_velocity;
    soldier.Get_Position(&physics_position); soldier.Get_Velocity(physics_velocity);
    check(physics_position == Vector3(0.5f, 0, 30) && physics_velocity == Vector3(1, 2, 3),
        "small_ground_correction_preserves_velocity");
    physics->Network_Interpolated_State_Update(Vector3(10, 0, 30), false);
    soldier.Get_Position(&physics_position);
    check(physics_position == Vector3(10, 0, 30), "large_ground_correction");
    physics->Network_Interpolated_State_Update(Vector3(11, 0, 30), true);
    soldier.Get_Position(&physics_position);
    check(physics_position == Vector3(11, 0, 30), "airborne_correction");
    for (int state : {0, 2, 5, 6, 8, 9, 10}) {
        soldier.Reset_State();
        BitStreamClass packet;
        Write_TT_Soldier_Frequent(packet, state, false, false, false);
        soldier.Import_Frequent(packet);
        check(!packet.Has_Read_Error(), "frequent_import_complete");
        check(state == 6 ? packet.Get_Bit_Read_Position() + 135 == packet.Get_Bit_Write_Position() :
            packet.Is_Flushed(), "frequent_consumption");
        if (state != 9) {
            check(soldier.Get_State() == state && soldier.Get_Sub_State() == 1,
                "frequent_human_state");
            check(!soldier.Network_Do_Tilt(), "frequent_do_tilt");
        }
        if (state == 5) {
            Vector3 position, velocity;
            soldier.Get_Position(&position);
            soldier.Get_Velocity(velocity);
            check(position == Vector3(100.125f, 200.25f, 30.5f) &&
                velocity == Vector3(1, 2, 3), "frequent_airborne_physics");
        }
        if (state == 8)
            check(WWMath::Fabs(soldier.Peek_Human_Phys()->Get_Heading() - 1.5707963267948966f) < 0.00001f,
                "frequent_ladder_heading");
    }
    soldier.Reset_State();
    unsigned rejected = 0;
    for (int state : {0, 2, 5, 8, 9, 10}) {
        BitStreamClass full;
        Write_TT_Soldier_Frequent(full, state);
        for (unsigned end = 0; end < full.Get_Bit_Write_Position(); ++end) {
            soldier.Reset_State();
            BitStreamClass packet;
            packet = full;
            packet.Set_Bit_Write_Position(end);
            soldier.Import_Frequent(packet);
            if (!packet.Has_Read_Error()) check(false, "frequent_truncation_rejected");
            ++rejected;
        }
    }
    soldier.Reset_State();
    for (bool do_tilt : {false, true}) {
        BitStreamClass packet;
        Write_TT_Soldier_Frequent(packet, HumanStateClass::UPRIGHT, false, false, do_tilt);
        soldier.Import_Frequent(packet);
        Vector3 pos;
        soldier.Get_Position(&pos);
        soldier.Set_Targeting(pos + Vector3(10, 0, 10));
        const float tilt = soldier.Saved_Aiming_Tilt();
        check(!packet.Has_Read_Error() && (do_tilt ? tilt > 0.1f && tilt < 1.6f : tilt == 0),
            "network_tilt_applied_to_human_state");
    }
    for (int state : {0, 9}) {
        BitStreamClass packet;
        Write_TT_Soldier_Frequent(packet, state);
        packet.Add(500.0f); packet.Add(600.0f); packet.Add(70.0f);
        soldier.Import_Frequent(packet);
        Vector3 pos;
        soldier.Get_Position(&pos);
        check(!packet.Has_Read_Error() && packet.Is_Flushed() && pos == Vector3(500, 600, 70),
            "optional_full_position_tail");
    }
    soldier.Reset_State();
    soldier.Lock_Animation();
    BitStreamClass locked_packet;
    Write_TT_Soldier_Frequent(locked_packet, HumanStateClass::UPRIGHT);
    soldier.Import_Frequent(locked_packet);
    check(!locked_packet.Has_Read_Error() && locked_packet.Is_Flushed() &&
        soldier.Get_State() == HumanStateClass::ANIMATION, "locked_animation_retains_state");
    soldier.Reset_State();
    printf("tt_soldier.frequent_truncations=%u\n", rejected);
    cGameType::Set_Game_Type(old_type);
    CombatManager::Set_I_Am_Server(old_is_server);
    CombatManager::Set_I_Am_Client(old_is_client);
    cNetwork::PClientConnection = old_client;
    cNetwork::PServerConnection = old_server;
    printf("tt_soldier.original_import_speed_flags_tag_skeleton=%s\n", passed ? "PASS" : "FAIL");
    return passed;
}

inline int Validate_TT_Soldier_Rare()
{
    bool passed = true;
    unsigned truncated = 0;
    for (int profile = 0; profile < 3; ++profile) {
        const bool modern = profile != 0, alternate = profile == 2;
        for (unsigned offset = 0; offset < 8; ++offset) {
            BitStreamClass packet;
            if (offset) packet.Add_Bits(0, offset);
            packet.Add(0x30010001);
            if (modern) Write_TT_Soldier_Suffix(packet, alternate);
            if (!offset) {
                printf("tt_soldier.vector_%d=%u:", profile, packet.Get_Bit_Write_Position());
                for (unsigned i = 0; i < (packet.Get_Bit_Write_Position() + 7) / 8; ++i)
                    printf("%02x", static_cast<unsigned char>(packet.Get_Data()[i]));
                printf("\n");
            }
            ULONG ignored = 0;
            if (offset) packet.Get_Bits(ignored, offset);
            int id = 0;
            packet.Get(id);
            passed = id == 0x30010001 && passed;
            if (!modern) continue;
            const unsigned start = packet.Get_Bit_Read_Position(), end = packet.Get_Bit_Write_Position();
            BitStreamClass full;
            full = packet;
            RenegadeSoldierRareState state;
            passed = Renegade_Read_Soldier_Rare(full, state) && full.Is_Flushed() && passed;
            passed = state.CanStealVehicles == !alternate && state.CanDriveVehicles &&
                state.BlockActionKey == alternate && state.Freeze == alternate &&
                state.CanPlayDamageAnimations == !alternate &&
                state.NetworkScale == (alternate ? 1.25f : 1.0f) &&
                state.MovementLoitersAllowed == !alternate &&
                state.MaxSpeed == (alternate ? 1.75f : 1.0f) &&
                state.OverrideMuzzleDirection == alternate &&
                state.SkeletonHeight == (alternate ? 0.2f : 0.0f) &&
                state.SkeletonWidth == (alternate ? -0.1f : 0.0f) &&
                state.WeaponHoldStyle == (alternate ? 2 : -1) &&
                state.HumanAnimOverride == alternate &&
                state.BotTag.Get_Length() == (alternate ? 7 : 0) &&
                state.Footsteps == !alternate && state.TargetHeight == (alternate ? 0.4f : 0.0f) &&
                state.TargetWidth == (alternate ? 0.3f : 0.0f) &&
                state.HeightSpeed == (alternate ? 0.05f : 0.0f) &&
                state.WidthSpeed == (alternate ? 0.1f : 0.0f) && passed;
            for (unsigned tail = start; tail < end; ++tail) {
                BitStreamClass short_packet;
                short_packet = packet;
                short_packet.Set_Bit_Write_Position(tail);
                RenegadeSoldierRareState unchanged;
                unchanged.MaxSpeed = 17;
                unchanged.BotTag = "unchanged";
                passed = !Renegade_Read_Soldier_Rare(short_packet, unchanged) &&
                    short_packet.Has_Read_Error() && unchanged.MaxSpeed == 17 &&
                    unchanged.BotTag.Get_Length() == 9 && passed;
                ++truncated;
            }
        }
    }
    printf("tt_soldier.transactional_truncations=%u result=%s\n", truncated, passed ? "PASS" : "FAIL");
    return passed ? 0 : 1;
}
