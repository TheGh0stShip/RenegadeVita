#pragma once
#include "tt_soldier_probe.h"
#include "renegade_vehicle_state.h"
#include "vehicle.h"
#include "vehiclephys.h"
#include "weaponbag.h"
#include "weapons.h"
#include "purchasesettings.h"
#include "definitionmgr.h"
#include "gameobjmanager.h"
#include "tt_client_control_probe.h"
#include <algorithm>

inline void Write_TT_Vehicle_Rare(BitStreamClass &packet, const std::vector<int> &seats,
    bool alternate, int owner = 0, int team = -1)
{
    for (int id : seats) packet.Add(id);
    packet.Add(alternate); packet.Add(alternate);
    packet.Add(BYTE(team < 0 ? (alternate ? 1 : 2) : team)); packet.Add(owner);
    packet.Add(alternate); packet.Add(!alternate);
    packet.Add(alternate ? 0.25f : 0.0f);
    packet.Add(alternate ? 0.5f : 0.0f);
    packet.Add(alternate ? 0.75f : 0.0f);
}

inline void Write_TT_Vehicle_Frequent(BitStreamClass &packet, bool moving, bool alternate)
{
    if (moving) {
        packet.Add(true);
        packet.Add(100.125f); packet.Add(200.25f); packet.Add(30.5f);
        for (float value : {0.0f, 0.0f, 0.0f, 1.0f})
            packet.Add(value, BITPACK_VEHICLE_QUATERNION);
        for (float value : {1.0f, 2.0f, 3.0f}) packet.Add(value, BITPACK_VEHICLE_VELOCITY);
        for (float value : {0.1f, -0.2f, 0.3f}) packet.Add(value, BITPACK_VEHICLE_ANGULAR_VELOCITY);
    }
    packet.Add(!alternate); packet.Add(alternate); packet.Add(!alternate);
    packet.Add(alternate); packet.Add(alternate);
    if (alternate) { packet.Add(0.75f); packet.Add(-0.25f); }
    Write_TT_Smart_Frequent(packet, true, false);
}

inline int Validate_TT_Vehicle_Vectors()
{
    VehicleGameObj::Set_Precision();
    ControlClass::Set_Precision();
    unsigned profile = 0, truncations = 0;
    bool passed = true;
    const auto output = [&profile](BitStreamClass &packet) {
        printf("tt_vehicle.vector_%u=%u:", profile++, packet.Get_Bit_Write_Position());
        for (unsigned i = 0; i < (packet.Get_Bit_Write_Position() + 7) / 8; ++i)
            printf("%02x", static_cast<unsigned char>(packet.Get_Data()[i]));
        printf("\n");
    };
    for (bool alternate : {false, true}) {
        BitStreamClass packet;
        Write_TT_Vehicle_Rare(packet, {alternate ? 1234 : -1, -1}, alternate, alternate ? 1234 : 0);
        output(packet);
        for (unsigned end = 0; end < packet.Get_Bit_Write_Position(); ++end) {
            BitStreamClass short_packet;
            short_packet = packet;
            short_packet.Set_Bit_Write_Position(end);
            RenegadeVehicleRareState state;
            state.OwnerID = 99;
            passed = !Renegade_Read_Vehicle_Rare(short_packet, 2, state) &&
                short_packet.Has_Read_Error() && state.OwnerID == 99 && passed;
            ++truncations;
        }
        RenegadeVehicleRareState state;
        passed = Renegade_Read_Vehicle_Rare(packet, 2, state) && packet.Is_Flushed() &&
            state.CanDrive == !alternate && state.LockTeam == (alternate ? 1 : 2) && passed;
    }
    for (bool alternate : {false, true}) {
        BitStreamClass packet;
        packet.Add(alternate ? 1 : 0);
        if (alternate) packet.Add(123456);
        packet.Add(alternate ? 1 : 0);
        output(packet);
    }
    for (bool moving : {true, false}) for (bool alternate : {false, true}) {
        BitStreamClass packet;
        Write_TT_Vehicle_Frequent(packet, moving, alternate);
        output(packet);
        RenegadeVehicleFrequentState state;
        passed = Renegade_Read_Vehicle_Frequent(packet, moving, state) &&
            state.FixedTurret == alternate && state.CanFire == !alternate &&
            (!moving || state.Position == Vector3(100.125f, 200.25f, 30.5f)) && passed;
        const unsigned prefix = packet.Get_Bit_Read_Position();
        for (unsigned end = 0; end < prefix; ++end) {
            BitStreamClass short_packet;
            Write_TT_Vehicle_Frequent(short_packet, moving, alternate);
            short_packet.Set_Bit_Write_Position(end);
            RenegadeVehicleFrequentState sentinel;
            sentinel.TurretTurn = 99;
            passed = !Renegade_Read_Vehicle_Frequent(short_packet, moving, sentinel) &&
                short_packet.Has_Read_Error() && sentinel.TurretTurn == 99 && passed;
            ++truncations;
        }
    }
    printf("tt_vehicle.transactional_truncations=%u result=%s\n", truncations, passed ? "PASS" : "FAIL");
    for (bool alternate : {false, true}) {
        BitStreamClass packet;
        packet.Add(alternate ? 1 : 0);
        if (alternate) packet.Add(123456);
        packet.Add(alternate); packet.Add(alternate);
        printf("tt_soldier_occasional.vector_%u=%u:", unsigned(alternate), packet.Get_Bit_Write_Position());
        for (unsigned i = 0; i < (packet.Get_Bit_Write_Position() + 7) / 8; ++i)
            printf("%02x", static_cast<unsigned char>(packet.Get_Data()[i]));
        printf("\n");
    }
    return passed ? 0 : 1;
}

inline bool Validate_TT_Vehicle_Runtime(const SoldierGameObjDef &soldier_definition)
{
    // Direct world fixtures bypass CombatGameMode's network precision setup.
    ControlClass::Set_Precision();
    DefenseObjectClass::Set_Precision();
    VehicleGameObj::Set_Precision();
    class ProbeVehicle : public VehicleGameObj {
    public:
        int Seats() const { return SeatOccupants.Length(); }
        bool Can_Drive() const { return NetworkCanDrive; }
        bool Can_Fire() const { return NetworkCanFire; }
        bool Fixed_Turret() const { return NetworkFixedTurret; }
        float Turn() const { return TurretTurn; }
    } vehicle;
    const VehicleGameObjDef *definition = NULL;
    auto *catalog = PurchaseSettingsDefClass::Find_Definition(
        PurchaseSettingsDefClass::TYPE_VEHICLES, static_cast<PurchaseSettingsDefClass::TEAM>(0));
    if (catalog) for (int i = 0; i < 10 && !definition; ++i) {
        DefinitionClass *candidate = DefinitionMgrClass::Find_Definition(catalog->Get_Definition(i));
        if (candidate && candidate->Get_Class_ID() == CLASSID_GAME_OBJECT_DEF_VEHICLE)
            definition = static_cast<VehicleGameObjDef *>(candidate);
    }
    if (!definition) { printf("tt_vehicle.runtime.missing_catalog_vehicle\n"); return false; }
    vehicle.Init(*definition);
    printf("tt_vehicle.runtime.preset=%s id=%u seats=%d\n", definition->Get_Name(), definition->Get_ID(), vehicle.Seats());
    if (vehicle.Seats() < 2 || !vehicle.Peek_Model() || !vehicle.Peek_Vehicle_Phys()) return false;
    struct ProbeSoldier : SoldierGameObj {
        void Set_Sniping(bool on) {
            if (Is_Sniping() != on) HumanState.Toggle_State_Flag(HumanStateClass::SNIPING_FLAG);
        }
    } driver;
    SoldierGameObj gunner;
    driver.Init(soldier_definition); gunner.Init(soldier_definition);
    bool passed = true;
    const auto check = [&passed](bool result, const char *name) {
        printf("tt_vehicle.runtime.%s=%s\n", name, result ? "PASS" : "FAIL");
        fflush(stdout);
        passed = passed && result;
    };
    cConnection connection;
    connection.Set_TT_Client_Greeting(true);
    cConnection *old_client = cNetwork::PClientConnection, *old_server = cNetwork::PServerConnection;
    const GameTypeEnum old_type = cGameType::Get_Game_Type();
    const bool old_server_flag = CombatManager::I_Am_Server(), old_client_flag = CombatManager::I_Am_Client();
    SoldierGameObj *old_star = COMBAT_STAR;
    cNetwork::PClientConnection = &connection; cNetwork::PServerConnection = NULL;
    CombatManager::Set_I_Am_Server(false); CombatManager::Set_I_Am_Client(true);
    cGameType::Set_Game_Type(GAMETYPE_MULTIPLAY);
    vehicle.Set_Control_Owner(SmartGameObj::SERVER_CONTROL_OWNER);
    driver.Set_Control_Owner(CombatManager::Get_My_Id());
    gunner.Set_Control_Owner(CombatManager::Get_My_Id());
    driver.Set_Player_Type(1); gunner.Set_Player_Type(1);
    check(Validate_TT_Client_Control(driver, vehicle), "outgoing_client_control");
    const auto rare = [&](const std::vector<int> &seats, bool alternate, int owner = 0, int team = -1) {
        BitStreamClass packet;
        packet.Add(2); packet.Add(1); packet.Add(BYTE(0)); packet.Add(6); packet.Add(false);
        packet.Add_Terminated_String(vehicle.Peek_Model()->Get_Name(), true);
        packet.Add_Terminated_String("", true);
        for (int value : {0, 0, 3, 0, 0, 1}) packet.Add(value);
        packet.Add(false); packet.Add(false);
        Write_TT_Vehicle_Rare(packet, seats, alternate, owner, team);
        vehicle.Import_Rare(packet);
        return !packet.Has_Read_Error() && packet.Is_Flushed();
    };
    std::vector<int> seats(vehicle.Seats(), -1);
    seats[0] = driver.Get_ID(); seats[1] = gunner.Get_ID();
    check(driver.Get_ID() > 0 && gunner.Get_ID() > 0 && driver.Get_ID() != gunner.Get_ID(), "object_ids");
    check(rare(seats, false) && vehicle.Get_Driver() == &driver && vehicle.Get_Gunner() == &gunner &&
        vehicle.Get_Occupant_Count() == 2, "occupants_enter");
    std::swap(seats[0], seats[1]);
    check(rare(seats, false) && vehicle.Get_Driver() == &gunner && vehicle.Get_Gunner() == &driver &&
        vehicle.Get_Occupant_Count() == 2, "occupants_swap");
    std::swap(seats[0], seats[1]);
    check(rare(seats, true, driver.Get_ID()) && !vehicle.Can_Drive(), "rare_permissions");
    for (bool local_gunner : {false, true}) {
        CombatManager::Set_The_Star(local_gunner ? &gunner : &driver);
        vehicle.SmartGameObj::Set_Targeting(Vector3(3, 4, 5));
        BitStreamClass packet;
        Write_TT_Vehicle_Frequent(packet, true, true);
        vehicle.Import_Frequent(packet);
        check(!packet.Has_Read_Error() && packet.Is_Flushed() && vehicle.Fixed_Turret() &&
            !vehicle.Can_Fire() && vehicle.Peek_Physical_Object()->Is_Immovable(), "frequent_flags");
        check(vehicle.Get_Targeting_Pos() == (local_gunner ? Vector3(3, 4, 5) : Vector3(12.5f, -20.25f, 31.125f)),
            "actual_gunner_aim_owner");
        driver.Set_Analog_Control(ControlClass::ANALOG_MOVE_FORWARD, 1);
        gunner.Set_Boolean_Control(ControlClass::BOOLEAN_WEAPON_FIRE_PRIMARY, true);
        gunner.Set_Boolean_Control(ControlClass::BOOLEAN_WEAPON_RELOAD, true);
        vehicle.Apply_Control();
        check(vehicle.Get_Control().Get_Analog(ControlClass::ANALOG_MOVE_FORWARD) == 0 &&
            !vehicle.Get_Control().Get_Boolean(ControlClass::BOOLEAN_WEAPON_FIRE_PRIMARY) &&
            !vehicle.Get_Control().Get_Boolean(ControlClass::BOOLEAN_WEAPON_RELOAD), "disabled_controls");
        vehicle.Post_Think();
    }
    check(rare(seats, false), "driving_reenabled");
    BitStreamClass enabled;
    Write_TT_Vehicle_Frequent(enabled, true, false);
    vehicle.Import_Frequent(enabled);
    driver.Set_Boolean_Control(ControlClass::BOOLEAN_WEAPON_FIRE_PRIMARY, true);
    vehicle.Apply_Control();
    check(!enabled.Has_Read_Error() && vehicle.Can_Fire() && vehicle.Can_Drive() &&
        !vehicle.Peek_Physical_Object()->Is_Immovable() &&
        vehicle.Get_Control().Get_Analog(ControlClass::ANALOG_MOVE_FORWARD) == 1 &&
        vehicle.Get_Control().Get_Boolean(ControlClass::BOOLEAN_WEAPON_FIRE_PRIMARY), "enabled_controls");
    CombatManager::Set_The_Star(old_star);
    seats[1] = seats[0];
    check(!rare(seats, false) && vehicle.Get_Occupant_Count() == 2, "duplicate_seat_rejected");
    seats[1] = vehicle.Get_ID();
    check(!rare(seats, false) && vehicle.Get_Occupant_Count() == 2, "nonsoldier_seat_rejected");
    std::fill(seats.begin(), seats.end(), -1);
    check(rare(seats, false) && !driver.Get_Vehicle() && !gunner.Get_Vehicle() &&
        vehicle.Get_Occupant_Count() == 0, "occupants_exit");
    check(rare(seats, true, driver.Get_ID()) && !vehicle.Is_Entry_Permitted(&gunner), "owned_vehicle_entry_denied");
    check(rare(seats, false), "permissions_reset");
    vehicle.Startup();
    check(vehicle.Is_Entry_Permitted(&driver), "normal_entry_permitted");
    vehicle.Lock_Vehicle(&gunner, 10);
    check(!vehicle.Is_Entry_Permitted(&driver), "purchase_lock_enforced");
    check(rare(seats, true, 0, 2), "stealing_permissions_received");
    driver.Set_Player_Type(0);
    check(vehicle.Is_Entry_Permitted(&driver), "enemy_purchase_lock_stealable");
    check(rare(seats, true, 0, 1) && !vehicle.Is_Entry_Permitted(&driver), "team_lock_enforced");
    driver.Set_Player_Type(1);
    check(rare(seats, true, 0, 2) && !vehicle.Is_Entry_Permitted(&driver), "friendly_purchase_lock_enforced");
    vehicle.Lock_Vehicle(NULL, 0);
    auto *bag = vehicle.Get_Weapon_Bag();
    WeaponClass *weapon = vehicle.Get_Weapon();
    check(weapon != NULL, "preset_weapon_available");
    if (weapon) {
        const int id = weapon->Get_ID(), index = bag->Get_Index();
        weapon->Set_Clip_Rounds(3); weapon->Set_Inventory_Rounds(7);
        BitStreamClass packet;
        Write_TT_Defense(packet, true);
        packet.Add(1); packet.Add(id); packet.Add(index);
        vehicle.Import_Occasional(packet);
        check(!packet.Has_Read_Error() && packet.Is_Flushed() && vehicle.Get_Weapon() == weapon &&
            weapon->Get_Clip_Rounds() == 3 && weapon->Get_Inventory_Rounds() == 7, "occasional_preserves_ammo");
        for (unsigned end = 0; end < 96; ++end) {
            BitStreamClass short_packet;
            short_packet.Add(1); short_packet.Add(id); short_packet.Add(index);
            short_packet.Set_Bit_Write_Position(end);
            bag->Import_TT_Weapon_Selection(short_packet);
            if (!short_packet.Has_Read_Error() || bag->Get_Weapon() != weapon) check(false, "inventory_truncation");
        }
        BitStreamClass invalid;
        invalid.Add(1); invalid.Add(id); invalid.Add(2);
        bag->Import_TT_Weapon_Selection(invalid);
        check(invalid.Has_Read_Error() && bag->Get_Weapon() == weapon, "invalid_selection_atomic");
        BitStreamClass empty;
        Write_TT_Defense(empty, true);
        empty.Add(0); empty.Add(0);
        vehicle.Import_Occasional(empty);
        check(!empty.Has_Read_Error() && empty.Is_Flushed() && bag->Get_Count() == 1 && !vehicle.Get_Weapon(),
            "inventory_removal");
        bag->Add_Weapon(id, 10);
        bag->Select_Index(1);
        bag->Remove_Weapon(0);
        check(bag->Get_Count() == 2 && bag->Get_Weapon() != NULL, "null_weapon_slot_preserved");
        bag->Clear_Weapons();
        check(bag->Get_Count() == 1 && bag->Get_Index() == 0 && !bag->Get_Weapon(), "selected_inventory_clear");
    }
    cNetwork::PClientConnection = old_client; cNetwork::PServerConnection = old_server;
    CombatManager::Set_I_Am_Server(old_server_flag); CombatManager::Set_I_Am_Client(old_client_flag);
    cGameType::Set_Game_Type(old_type);
    printf("tt_vehicle.runtime.result=%s\n", passed ? "PASS" : "FAIL");
    return passed;
}
