#pragma once
#include "gamemode.h"

// Direct-IP sessions do not register the retired LAN/WOL frontend providers.
inline bool Renegade_Network_Mode_Active(const char *name)
{
    GameModeClass *mode = GameModeManager::Find(name);
    return mode && mode->Is_Active();
}
