/*
** GCC does not apply the default arguments written on function-pointer
** members in the original ScriptCommands ABI table.  The 2002 MSVC build
** did, and the original M00 script closure relies on five of those defaults.
** This header is force-included only for Mission00.cpp and its two direct
** provider dependencies.  It adds the omitted final argument while leaving
** full-arity calls and the callback table layout unchanged.
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

#define RENEGADE_SCRIPT_JOIN_CONVERSATION_4(object, conversation, allow_move, allow_head_turn) \
	Join_Conversation(object, conversation, allow_move, allow_head_turn, true)
#define RENEGADE_SCRIPT_JOIN_CONVERSATION_5(object, conversation, allow_move, allow_head_turn, allow_face) \
	Join_Conversation(object, conversation, allow_move, allow_head_turn, allow_face)
#define Join_Conversation(...) \
	RENEGADE_SCRIPT_SELECT_5(__VA_ARGS__, \
		RENEGADE_SCRIPT_JOIN_CONVERSATION_5, \
		RENEGADE_SCRIPT_JOIN_CONVERSATION_4)(__VA_ARGS__)

#define RENEGADE_SCRIPT_SEND_CUSTOM_EVENT_4(from, to, type, param) \
	Send_Custom_Event(from, to, type, param, 0.0F)
#define RENEGADE_SCRIPT_SEND_CUSTOM_EVENT_5(from, to, type, param, delay) \
	Send_Custom_Event(from, to, type, param, delay)
#define Send_Custom_Event(...) \
	RENEGADE_SCRIPT_SELECT_5(__VA_ARGS__, \
		RENEGADE_SCRIPT_SEND_CUSTOM_EVENT_5, \
		RENEGADE_SCRIPT_SEND_CUSTOM_EVENT_4)(__VA_ARGS__)

#define RENEGADE_SCRIPT_SET_ANIMATION_6(object, animation, looping, sub_object, start_frame, end_frame) \
	Set_Animation(object, animation, looping, sub_object, start_frame, end_frame, false)
#define RENEGADE_SCRIPT_SET_ANIMATION_7(object, animation, looping, sub_object, start_frame, end_frame, blended) \
	Set_Animation(object, animation, looping, sub_object, start_frame, end_frame, blended)
#define Set_Animation(...) \
	RENEGADE_SCRIPT_SELECT_7(__VA_ARGS__, \
		RENEGADE_SCRIPT_SET_ANIMATION_7, \
		RENEGADE_SCRIPT_SET_ANIMATION_6)(__VA_ARGS__)

#endif
