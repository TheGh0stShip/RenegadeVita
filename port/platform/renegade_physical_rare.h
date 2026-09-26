#pragma once
#include "bitstream.h"

struct RenegadePhysicalRarePrefix {
    int RadarColor = 0, RadarShape = 0, CollisionGroup = 0;
    unsigned char TeamVisibility = 0;
    bool ClearAnimation = false;
};

inline void Renegade_Read_Physical_Rare_Prefix(BitStreamClass &packet,
    RenegadePhysicalRarePrefix &prefix)
{
    packet.Get(prefix.RadarColor);
    packet.Get(prefix.RadarShape);
    packet.Get(prefix.TeamVisibility);
    packet.Get(prefix.CollisionGroup);
    packet.Get(prefix.ClearAnimation);
}

// Validate the complete physical portion before model/animation mutation.
// Subclasses still own their suffix. This layout is pinned TT b9000, not a
// version-independent promise. Non-default team visibility is not supported yet.
inline bool Renegade_Validate_Physical_Rare(const BitStreamClass &packet,
    bool modern, bool vehicle)
{
    BitStreamClass scan;
    scan = packet;
    if (modern) {
        RenegadePhysicalRarePrefix prefix;
        Renegade_Read_Physical_Rare_Prefix(scan, prefix);
        if (prefix.TeamVisibility != 0 || prefix.CollisionGroup < 0 || prefix.CollisionGroup > 31)
            return false;
    }
    char name[1024];
    scan.Get_Terminated_String(name, modern ? 1024 : 256, true);
    if (scan.Has_Read_Error() || !name[0]) return false;
    scan.Get_Terminated_String(name, modern ? 1024 : 256, true);
    int frame = 0, target = 0, mode = 0, host = 0, bone = 0, team = 0;
    scan.Get(frame); scan.Get(target); scan.Get(mode);
    scan.Get(host); scan.Get(bone); scan.Get(team);
    bool flag = false;
    scan.Get(flag);
    if (modern || vehicle) scan.Get(flag);
    return !scan.Has_Read_Error() && mode >= 0 && mode <= 3;
}
