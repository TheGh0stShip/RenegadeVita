#pragma once
#include "bitstream.h"
#include "bitpackids.h"
#include "vector3.h"
#include "quat.h"
#include "wwmath.h"
#include <vector>

// TT b9000 wire state. These are runtime values, not packed disk/ABI layouts.
struct RenegadeVehicleRareState {
    std::vector<int> Occupants;
    bool Delivered = false, AllowEmptyStealth = false;
    BYTE LockTeam = 2;
    int OwnerID = 0;
    bool CanBeStolen = false, CanDrive = true;
    Vector3 UndergroundColor = Vector3(0, 0, 0);
};

inline void Renegade_Read_Vehicle_Float(BitStreamClass &packet, float &value,
    int precision = -1)
{
    packet.Get(value, precision);
    if (!WWMath::Is_Valid_Float(value)) value = 0;
}

inline bool Renegade_Read_Vehicle_Rare(BitStreamClass &packet, int seats,
    RenegadeVehicleRareState &state)
{
    if (packet.Has_Read_Error() || seats < 0 ||
        unsigned(seats) > (packet.Get_Bit_Write_Position() - packet.Get_Bit_Read_Position()) / 32) {
        packet.Mark_Read_Error();
        return false;
    }
    RenegadeVehicleRareState next;
    next.Occupants.resize(seats);
    for (int &id : next.Occupants) packet.Get(id);
    packet.Get(next.Delivered);
    packet.Get(next.AllowEmptyStealth);
    packet.Get(next.LockTeam);
    packet.Get(next.OwnerID);
    packet.Get(next.CanBeStolen);
    packet.Get(next.CanDrive);
    for (int axis = 0; axis < 3; ++axis)
        Renegade_Read_Vehicle_Float(packet, next.UndergroundColor[axis]);
    if (packet.Has_Read_Error()) return false;
    state = next;
    return true;
}

struct RenegadeVehicleFrequentState {
    bool Engine = false, DriverIsGunner = false, DamageMeshes = false;
    bool CanFire = true, Immovable = false, FixedTurret = false;
    Vector3 Position = Vector3(0, 0, 0);
    Quaternion Orientation = Quaternion(0, 0, 0, 1);
    Vector3 Velocity = Vector3(0, 0, 0), AngularVelocity = Vector3(0, 0, 0);
    float TurretTurn = 0, BarrelTilt = 0;
};

inline bool Renegade_Read_Vehicle_Frequent(BitStreamClass &packet, bool moving,
    RenegadeVehicleFrequentState &state)
{
    RenegadeVehicleFrequentState next;
    if (moving) {
        packet.Get(next.Engine);
        for (int axis = 0; axis < 3; ++axis)
            Renegade_Read_Vehicle_Float(packet, next.Position[axis]);
        for (int axis = 0; axis < 4; ++axis)
            Renegade_Read_Vehicle_Float(packet, next.Orientation[axis], BITPACK_VEHICLE_QUATERNION);
        next.Orientation.Normalize();
        for (int axis = 0; axis < 3; ++axis)
            Renegade_Read_Vehicle_Float(packet, next.Velocity[axis], BITPACK_VEHICLE_VELOCITY);
        for (int axis = 0; axis < 3; ++axis)
            Renegade_Read_Vehicle_Float(packet, next.AngularVelocity[axis], BITPACK_VEHICLE_ANGULAR_VELOCITY);
    }
    packet.Get(next.DriverIsGunner); packet.Get(next.DamageMeshes);
    packet.Get(next.CanFire); packet.Get(next.Immovable);
    packet.Get(next.FixedTurret);
    if (next.FixedTurret) {
        Renegade_Read_Vehicle_Float(packet, next.TurretTurn);
        Renegade_Read_Vehicle_Float(packet, next.BarrelTilt);
    }
    if (packet.Has_Read_Error()) return false;
    state = next;
    return true;
}
