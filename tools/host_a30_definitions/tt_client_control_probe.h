#pragma once
#include "clientcontrol.h"
#include "soldier.h"
#include "vehicle.h"
#include "gameobjmanager.h"
#include <cstdio>

template<class SoldierProbe>
bool Validate_TT_Client_Control(SoldierProbe &soldier, VehicleGameObj &vehicle)
{
    CClientControl outgoing;
    bool passed = true;
    const auto emit = [&passed](BitStreamClass &packet, unsigned profile, int expected_id) {
        int id = 0;
        packet.Get(id);
        passed = passed && !packet.Has_Read_Error() && id == expected_id;
        printf("tt_client_control.vector_%u=%d:%u:", profile, expected_id, packet.Get_Bit_Write_Position());
        for (unsigned i = 0; i < (packet.Get_Bit_Write_Position() + 7) / 8; ++i)
            printf("%02x", static_cast<unsigned char>(packet.Get_Data()[i]));
        printf("\n");
    };
    BitStreamClass creation;
    outgoing.Export_Creation(creation);
    emit(creation, 0, -1);
    for (unsigned profile = 1; profile <= 3; ++profile) {
        SmartGameObj &object = profile == 3 ? static_cast<SmartGameObj &>(vehicle) :
            static_cast<SmartGameObj &>(soldier);
        object.Set_Position(Vector3(100.125f, 200.25f, 30.5f));
        object.ArmedGameObj::Set_Targeting(Vector3(12.5f, -20.25f, 31.125f));
        soldier.Set_Sniping(profile == 2);
        auto &control = object.Get_Control();
        control.Clear_Control();
        // Clear_Control preserves pending one-shot events until transmission.
        BitStreamClass drain;
        control.Export_Cs(drain);
        for (auto flag : {ControlClass::BOOLEAN_JUMP, ControlClass::BOOLEAN_ACTION,
                          ControlClass::BOOLEAN_VEHICLE_TOGGLE_GUNNER,
                          ControlClass::BOOLEAN_WEAPON_FIRE_PRIMARY, ControlClass::BOOLEAN_WALK})
            control.Set_Boolean(flag, true);
        control.Set_Analog(ControlClass::ANALOG_MOVE_FORWARD, 1);
        control.Set_Analog(ControlClass::ANALOG_MOVE_LEFT, -1);
        control.Set_Analog(ControlClass::ANALOG_TURN_LEFT, 0.5f);
        outgoing.Set_Update_Flag(object.Get_ID());
        BitStreamClass packet;
        outgoing.Export_Frequent(packet);
        emit(packet, profile, object.Get_ID());
        BitStreamClass reset;
        outgoing.Export_Frequent(reset);
        int reset_id = 0;
        reset.Get(reset_id);
        passed = passed && reset_id == -1 && reset.Get_Bit_Write_Position() == 32;
        BitStreamClass pending;
        control.Export_Cs(pending);
        ULONG once = 1;
        BYTE continuous = 1;
        pending.Get(once, BITPACK_ONE_TIME_BOOLEAN_BITS);
        pending.Get(continuous, BITPACK_CONTINUOUS_BOOLEAN_BITS);
        passed = passed && once == 0 && continuous == 0;
        control.Clear_Control();
    }
    soldier.Set_Sniping(false);
    const int missing = 0x7ffffffe;
    passed = passed && GameObjManager::Find_SmartGameObj(missing) == NULL;
    outgoing.Set_Update_Flag(missing);
    BitStreamClass absent;
    outgoing.Export_Frequent(absent);
    emit(absent, 4, -1);
    {
        // The original deletion queue owns this object through world teardown.
        SoldierGameObj *removed = new SoldierGameObj;
        removed->Init(soldier.Get_Definition());
        removed->Set_Delete_Pending();
        outgoing.Set_Update_Flag(removed->Get_ID());
        BitStreamClass deleted;
        outgoing.Export_Frequent(deleted);
        emit(deleted, 5, -1);
    }
    BitStreamClass idle;
    outgoing.Export_Frequent(idle);
    emit(idle, 6, -1);
    printf("tt_client_control.runtime.result=%s\n", passed ? "PASS" : "FAIL");
    return passed;
}
