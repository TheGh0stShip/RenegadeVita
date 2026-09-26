#pragma once
#include "bitstream.h"
#include "bitpackids.h"
#include "vector3.h"

struct RenegadeC4RareState {
    int AmmoID = 0, OwnerID = 0, ObjectID = -1, Bone = 0;
    unsigned StaticID = 0xffffffffU;
    Vector3 Velocity{0, 0, 0}, Position{0, 0, 0}, Offset{0, 0, 0};
    bool Stuck = false, MCT = false, Dynamic = false, Static = false;
};

inline bool Renegade_Read_C4_Rare(BitStreamClass &packet, RenegadeC4RareState &result, bool modern = true)
{
    RenegadeC4RareState state;
    const int velocity = modern ? BitStreamClass::NO_ENCODER : BITPACK_VEHICLE_VELOCITY;
    packet.Get(state.AmmoID); packet.Get(state.OwnerID);
    packet.Get(state.Velocity.X, velocity); packet.Get(state.Velocity.Y, velocity); packet.Get(state.Velocity.Z, velocity);
    packet.Get(state.Stuck);
    if (state.Stuck) {
        packet.Get(state.Position.X, modern ? BitStreamClass::NO_ENCODER : BITPACK_WORLD_POSITION_X);
        packet.Get(state.Position.Y, modern ? BitStreamClass::NO_ENCODER : BITPACK_WORLD_POSITION_Y);
        packet.Get(state.Position.Z, modern ? BitStreamClass::NO_ENCODER : BITPACK_WORLD_POSITION_Z);
        packet.Get(state.MCT); packet.Get(state.Dynamic); packet.Get(state.ObjectID);
        if (state.Dynamic) {
            packet.Get(state.Offset.X, velocity); packet.Get(state.Offset.Y, velocity); packet.Get(state.Offset.Z, velocity);
            packet.Get(state.Bone);
        }
        packet.Get(state.Static);
        if (state.Static) packet.Get(state.StaticID);
    }
    if (packet.Has_Read_Error() || !state.Velocity.Is_Valid() || !state.Position.Is_Valid() || !state.Offset.Is_Valid())
        return false;
    result = state;
    return true;
}
