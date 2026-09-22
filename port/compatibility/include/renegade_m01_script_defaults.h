#ifndef RENEGADE_M01_SCRIPT_DEFAULTS_H
#define RENEGADE_M01_SCRIPT_DEFAULTS_H

#include "../../../upstream/CnC_Renegade/Code/Scripts/scripts.h"

// The original MSVC script callback table supplied defaults on function
// pointers. GCC does not apply them. These macros are scoped to Mission01.cpp.
#define RV_M01_SELECT_3(_1, _2, _3, NAME, ...) NAME
#define RV_M01_SELECT_4(_1, _2, _3, _4, NAME, ...) NAME
#define RV_M01_SELECT_5(_1, _2, _3, _4, _5, NAME, ...) NAME
#define RV_M01_SELECT_7(_1, _2, _3, _4, _5, _6, _7, NAME, ...) NAME

#define RV_M01_JOIN_2(a, b) Join_Conversation(a, b, true, true, true)
#define RV_M01_JOIN_3(a, b, c) Join_Conversation(a, b, c, true, true)
#define RV_M01_JOIN_4(a, b, c, d) Join_Conversation(a, b, c, d, true)
#define RV_M01_JOIN_5(a, b, c, d, e) Join_Conversation(a, b, c, d, e)
#define Join_Conversation(...) RV_M01_SELECT_5(__VA_ARGS__, RV_M01_JOIN_5, RV_M01_JOIN_4, RV_M01_JOIN_3, RV_M01_JOIN_2)(__VA_ARGS__)

#define RV_M01_ANIM_2(a, b) Set_Animation(a, b)
#define RV_M01_ANIM_3(a, b, c) Set_Animation(a, b, c, NULL, 0.0F, -1.0F, false)
#define RV_M01_ANIM_4(a, b, c, d) Set_Animation(a, b, c, d, 0.0F, -1.0F, false)
#define RV_M01_ANIM_5(a, b, c, d, e) Set_Animation(a, b, c, d, e, -1.0F, false)
#define RV_M01_ANIM_6(a, b, c, d, e, f) Set_Animation(a, b, c, d, e, f, false)
#define RV_M01_ANIM_7(a, b, c, d, e, f, g) Set_Animation(a, b, c, d, e, f, g)
#define Set_Animation(...) RV_M01_SELECT_7(__VA_ARGS__, RV_M01_ANIM_7, RV_M01_ANIM_6, RV_M01_ANIM_5, RV_M01_ANIM_4, RV_M01_ANIM_3, RV_M01_ANIM_2)(__VA_ARGS__)

#define RV_M01_MODIFY_3(a, b, c) Modify_Action(a, b, c, true, true)
#define RV_M01_MODIFY_4(a, b, c, d) Modify_Action(a, b, c, d, true)
#define RV_M01_MODIFY_5(a, b, c, d, e) Modify_Action(a, b, c, d, e)
#define Modify_Action(...) RV_M01_SELECT_5(__VA_ARGS__, RV_M01_MODIFY_5, RV_M01_MODIFY_4, RV_M01_MODIFY_3)(__VA_ARGS__)

#define RV_M01_EXPLOSION_2(a, b) Create_Explosion(a, b, NULL)
#define RV_M01_EXPLOSION_3(a, b, c) Create_Explosion(a, b, c)
#define Create_Explosion(...) RV_M01_SELECT_3(__VA_ARGS__, RV_M01_EXPLOSION_3, RV_M01_EXPLOSION_2)(__VA_ARGS__)

#define RV_M01_DAMAGE_3(a, b, c) Apply_Damage(a, b, c, NULL)
#define RV_M01_DAMAGE_4(a, b, c, d) Apply_Damage(a, b, c, d)
#define Apply_Damage(...) RV_M01_SELECT_4(__VA_ARGS__, RV_M01_DAMAGE_4, RV_M01_DAMAGE_3)(__VA_ARGS__)

#endif
