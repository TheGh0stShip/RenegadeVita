#pragma once
#include "bitstream.h"
#include "widestring.h"
#include "wwmath.h"

// TT b9000 soldier rare suffix. Runtime state, never a serialized C++ layout.
struct RenegadeSoldierRareState {
    bool CanStealVehicles = true, CanDriveVehicles = true;
    bool BlockActionKey = false, Freeze = false, CanPlayDamageAnimations = true;
    float NetworkScale = 1.0f;
    bool MovementLoitersAllowed = true;
    float MaxSpeed = 1.0f;
    bool OverrideMuzzleDirection = false;
    float SkeletonHeight = 0, SkeletonWidth = 0;
    int WeaponHoldStyle = -1;
    bool HumanAnimOverride = true;
    WideStringClass BotTag;
    bool Footsteps = true;
    float TargetHeight = 0, TargetWidth = 0, HeightSpeed = 0, WidthSpeed = 0;
};

inline void Renegade_Read_TT_Float(BitStreamClass &packet, float &value)
{
    packet.Get(value);
    if (!WWMath::Is_Valid_Float(value)) value = 0;
}

// Decode transactionally: truncated updates must not partly replace live state.
inline bool Renegade_Read_Soldier_Rare(BitStreamClass &packet,
    RenegadeSoldierRareState &state)
{
    RenegadeSoldierRareState next;
    packet.Get(next.CanStealVehicles); packet.Get(next.CanDriveVehicles);
    packet.Get(next.BlockActionKey); packet.Get(next.Freeze);
    packet.Get(next.CanPlayDamageAnimations);
    Renegade_Read_TT_Float(packet, next.NetworkScale);
    packet.Get(next.MovementLoitersAllowed);
    Renegade_Read_TT_Float(packet, next.MaxSpeed);
    packet.Get(next.OverrideMuzzleDirection);
    Renegade_Read_TT_Float(packet, next.SkeletonHeight);
    Renegade_Read_TT_Float(packet, next.SkeletonWidth);
    packet.Get(next.WeaponHoldStyle); packet.Get(next.HumanAnimOverride);
    WCHAR tag[256] = {};
    packet.Get_Wide_Terminated_String(tag, 256, true);
    packet.Get(next.Footsteps);
    Renegade_Read_TT_Float(packet, next.TargetHeight);
    Renegade_Read_TT_Float(packet, next.TargetWidth);
    Renegade_Read_TT_Float(packet, next.HeightSpeed);
    Renegade_Read_TT_Float(packet, next.WidthSpeed);
    if (packet.Has_Read_Error()) return false;
    next.BotTag = tag;
    state = next;
    return true;
}
