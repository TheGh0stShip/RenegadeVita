/* M13's authored ledge-drop cinematic reuses M08_Petra_C_Helo. Link its
 * original unit with the original MSVC callback defaults, without changing
 * ScriptCommands layout or copying the helper into a replacement provider. */
#ifndef RENEGADE_M08_SCRIPT_DEFAULTS_H
#define RENEGADE_M08_SCRIPT_DEFAULTS_H
#include "renegade_script_call_defaults.h"

#define RENEGADE_M08_MODIFY_3(a, b, c) Modify_Action(a, b, c, true, true)
#define RENEGADE_M08_MODIFY_4(a, b, c, d) Modify_Action(a, b, c, d, true)
#define RENEGADE_M08_MODIFY_5(a, b, c, d, e) Modify_Action(a, b, c, d, e)
#define Modify_Action(...) \
    RENEGADE_SCRIPT_SELECT_5(__VA_ARGS__, RENEGADE_M08_MODIFY_5, \
        RENEGADE_M08_MODIFY_4, RENEGADE_M08_MODIFY_3)(__VA_ARGS__)

#define RENEGADE_M08_SELECT_3(_1, _2, _3, NAME, ...) NAME
#define RENEGADE_M08_EXPLOSION_2(a, b) Create_Explosion(a, b, NULL)
#define RENEGADE_M08_EXPLOSION_3(a, b, c) Create_Explosion(a, b, c)
#define Create_Explosion(...) \
    RENEGADE_M08_SELECT_3(__VA_ARGS__, RENEGADE_M08_EXPLOSION_3, \
        RENEGADE_M08_EXPLOSION_2)(__VA_ARGS__)
#endif
