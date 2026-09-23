/*
** GCC does not apply the default arguments written on function-pointer
** members in the original ScriptCommands ABI table.  The 2002 MSVC build
** did, and original script providers rely on those defaults.  This header is
** force-included only for original script translation units that need the
** call-site defaults.  It adds omitted arguments while leaving full-arity calls
** and the callback table layout unchanged.
*/
#ifndef RENEGADE_SCRIPT_CALL_DEFAULTS_H
#define RENEGADE_SCRIPT_CALL_DEFAULTS_H

/* Admit the original declarations before the call-site macros so unrelated
** methods such as ActionParamsStruct::Set_Animation remain untouched. */
#include "../../../upstream/CnC_Renegade/Code/Scripts/scripts.h"

#define RENEGADE_SCRIPT_SELECT_4(_1, _2, _3, _4, NAME, ...) NAME
#define RENEGADE_SCRIPT_SELECT_5(_1, _2, _3, _4, _5, NAME, ...) NAME
#define RENEGADE_SCRIPT_SELECT_7(_1, _2, _3, _4, _5, _6, _7, NAME, ...) NAME

#define RENEGADE_SCRIPT_CREATE_EXPLOSION_AT_BONE_3(explosion, object, bone) \
	Create_Explosion_At_Bone(explosion, object, bone, NULL)
#define RENEGADE_SCRIPT_CREATE_EXPLOSION_AT_BONE_4(explosion, object, bone, creator) \
	Create_Explosion_At_Bone(explosion, object, bone, creator)
#define Create_Explosion_At_Bone(...) \
	RENEGADE_SCRIPT_SELECT_4(__VA_ARGS__, \
		RENEGADE_SCRIPT_CREATE_EXPLOSION_AT_BONE_4, \
		RENEGADE_SCRIPT_CREATE_EXPLOSION_AT_BONE_3)(__VA_ARGS__)

#define RENEGADE_SCRIPT_APPLY_DAMAGE_3(object, amount, warhead) \
	Apply_Damage(object, amount, warhead, NULL)
#define RENEGADE_SCRIPT_APPLY_DAMAGE_4(object, amount, warhead, damager) \
	Apply_Damage(object, amount, warhead, damager)
#define Apply_Damage(...) \
	RENEGADE_SCRIPT_SELECT_4(__VA_ARGS__, \
		RENEGADE_SCRIPT_APPLY_DAMAGE_4, \
		RENEGADE_SCRIPT_APPLY_DAMAGE_3)(__VA_ARGS__)

#define RENEGADE_SCRIPT_CREATE_CONVERSATION_1(name) \
	Create_Conversation(name, 0, 0.0F, true)
#define RENEGADE_SCRIPT_CREATE_CONVERSATION_2(name, priority) \
	Create_Conversation(name, priority, 0.0F, true)
#define RENEGADE_SCRIPT_CREATE_CONVERSATION_3(name, priority, max_dist) \
	Create_Conversation(name, priority, max_dist, true)
#define RENEGADE_SCRIPT_CREATE_CONVERSATION_4(name, priority, max_dist, interruptable) \
	Create_Conversation(name, priority, max_dist, interruptable)
#define Create_Conversation(...) \
	RENEGADE_SCRIPT_SELECT_4(__VA_ARGS__, \
		RENEGADE_SCRIPT_CREATE_CONVERSATION_4, \
		RENEGADE_SCRIPT_CREATE_CONVERSATION_3, \
		RENEGADE_SCRIPT_CREATE_CONVERSATION_2, \
		RENEGADE_SCRIPT_CREATE_CONVERSATION_1)(__VA_ARGS__)

#define RENEGADE_SCRIPT_ENABLE_ENEMY_SEEN_1(object) \
	Enable_Enemy_Seen(object, true)
#define RENEGADE_SCRIPT_ENABLE_ENEMY_SEEN_2(object, enable) \
	Enable_Enemy_Seen(object, enable)
#define Enable_Enemy_Seen(...) \
	RENEGADE_SCRIPT_SELECT_4(__VA_ARGS__, \
		Enable_Enemy_Seen, \
		Enable_Enemy_Seen, \
		RENEGADE_SCRIPT_ENABLE_ENEMY_SEEN_2, \
		RENEGADE_SCRIPT_ENABLE_ENEMY_SEEN_1)(__VA_ARGS__)

#define RENEGADE_SCRIPT_GIVE_POWERUP_2(object, preset) \
	Give_PowerUp(object, preset, false)
#define RENEGADE_SCRIPT_GIVE_POWERUP_3(object, preset, display_on_hud) \
	Give_PowerUp(object, preset, display_on_hud)
#define Give_PowerUp(...) \
	RENEGADE_SCRIPT_SELECT_4(__VA_ARGS__, \
		Give_PowerUp, \
		RENEGADE_SCRIPT_GIVE_POWERUP_3, \
		RENEGADE_SCRIPT_GIVE_POWERUP_2, \
		RENEGADE_SCRIPT_GIVE_POWERUP_2)(__VA_ARGS__)

#define RENEGADE_SCRIPT_JOIN_CONVERSATION_2(object, conversation) \
	Join_Conversation(object, conversation, true, true, true)
#define RENEGADE_SCRIPT_JOIN_CONVERSATION_3(object, conversation, allow_move) \
	Join_Conversation(object, conversation, allow_move, true, true)
#define RENEGADE_SCRIPT_JOIN_CONVERSATION_4(object, conversation, allow_move, allow_head_turn) \
	Join_Conversation(object, conversation, allow_move, allow_head_turn, true)
#define RENEGADE_SCRIPT_JOIN_CONVERSATION_5(object, conversation, allow_move, allow_head_turn, allow_face) \
	Join_Conversation(object, conversation, allow_move, allow_head_turn, allow_face)
#define Join_Conversation(...) \
	RENEGADE_SCRIPT_SELECT_5(__VA_ARGS__, \
		RENEGADE_SCRIPT_JOIN_CONVERSATION_5, \
		RENEGADE_SCRIPT_JOIN_CONVERSATION_4, \
		RENEGADE_SCRIPT_JOIN_CONVERSATION_3, \
		RENEGADE_SCRIPT_JOIN_CONVERSATION_2)(__VA_ARGS__)

#define RENEGADE_SCRIPT_SEND_CUSTOM_EVENT_4(from, to, type, param) \
	Send_Custom_Event(from, to, type, param, 0.0F)
#define RENEGADE_SCRIPT_SEND_CUSTOM_EVENT_5(from, to, type, param, delay) \
	Send_Custom_Event(from, to, type, param, delay)
#define Send_Custom_Event(...) \
	RENEGADE_SCRIPT_SELECT_5(__VA_ARGS__, \
		RENEGADE_SCRIPT_SEND_CUSTOM_EVENT_5, \
		RENEGADE_SCRIPT_SEND_CUSTOM_EVENT_4)(__VA_ARGS__)

#define RENEGADE_SCRIPT_SET_ANIMATION_2(animation, looping) \
	Set_Animation(animation, looping)
#define RENEGADE_SCRIPT_SET_ANIMATION_3(object, animation, looping) \
	Set_Animation(object, animation, looping, NULL, 0.0F, -1.0F, false)
#define RENEGADE_SCRIPT_SET_ANIMATION_4(object, animation, looping, sub_object) \
	Set_Animation(object, animation, looping, sub_object, 0.0F, -1.0F, false)
#define RENEGADE_SCRIPT_SET_ANIMATION_5(object, animation, looping, sub_object, start_frame) \
	Set_Animation(object, animation, looping, sub_object, start_frame, -1.0F, false)
#define RENEGADE_SCRIPT_SET_ANIMATION_6(object, animation, looping, sub_object, start_frame, end_frame) \
	Set_Animation(object, animation, looping, sub_object, start_frame, end_frame, false)
#define RENEGADE_SCRIPT_SET_ANIMATION_7(object, animation, looping, sub_object, start_frame, end_frame, blended) \
	Set_Animation(object, animation, looping, sub_object, start_frame, end_frame, blended)
#define Set_Animation(...) \
	RENEGADE_SCRIPT_SELECT_7(__VA_ARGS__, \
		RENEGADE_SCRIPT_SET_ANIMATION_7, \
		RENEGADE_SCRIPT_SET_ANIMATION_6, \
		RENEGADE_SCRIPT_SET_ANIMATION_5, \
		RENEGADE_SCRIPT_SET_ANIMATION_4, \
		RENEGADE_SCRIPT_SET_ANIMATION_3, \
		RENEGADE_SCRIPT_SET_ANIMATION_2)(__VA_ARGS__)

#endif
