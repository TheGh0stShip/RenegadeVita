/* Test_RAD owns M13's squad rescue and repaired-tank handoff. Keep the
 * original ScriptCommands layout; supply MSVC call defaults only in this TU.
 * A global Start_Conversation macro would collide with ActionParamsStruct's
 * unrelated one-argument method, so do not put this in the shared bridge. */
#ifndef RENEGADE_M13_AREA2_SCRIPT_DEFAULTS_H
#define RENEGADE_M13_AREA2_SCRIPT_DEFAULTS_H

#include "renegade_script_call_defaults.h"

#define RENEGADE_AREA2_SELECT_2(_1, _2, NAME, ...) NAME
#define RENEGADE_AREA2_START_CONVERSATION_1(id) Start_Conversation(id, 0)
#define RENEGADE_AREA2_START_CONVERSATION_2(id, action) Start_Conversation(id, action)
#define Start_Conversation(...) \
    RENEGADE_AREA2_SELECT_2(__VA_ARGS__, \
        RENEGADE_AREA2_START_CONVERSATION_2, \
        RENEGADE_AREA2_START_CONVERSATION_1)(__VA_ARGS__)

#define RENEGADE_AREA2_TRIGGER_WEAPON_3(obj, trigger, target) \
    Trigger_Weapon(obj, trigger, target, true)
#define RENEGADE_AREA2_TRIGGER_WEAPON_4(obj, trigger, target, primary) \
    Trigger_Weapon(obj, trigger, target, primary)
#define Trigger_Weapon(...) \
    RENEGADE_SCRIPT_SELECT_4(__VA_ARGS__, \
        RENEGADE_AREA2_TRIGGER_WEAPON_4, \
        RENEGADE_AREA2_TRIGGER_WEAPON_3)(__VA_ARGS__)

#endif
