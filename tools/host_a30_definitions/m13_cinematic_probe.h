#pragma once

#include "animcontrol.h"
#include "ccamera.h"
#include "combat.h"
#include "gameobjmanager.h"
#include "gameobjobserver.h"
#include "physicalgameobj.h"
#include "soldier.h"
#include "ww3d.h"

#include <cstdio>
#include <cstring>

// Observe original X00_Intro execution without spawning actors or sending events.
class M13CinematicProbe
{
	int engineers[2] = {};
	bool detached[2] = {};
	bool camera_seen = false;
	bool rappel_seen = false;
	bool rappel_advanced = false;
	float rappel_first_frame = 0.0F;
	float rappel_first_z = 0.0F;

public:
	void Observe(unsigned frame)
	{
		if (COMBAT_CAMERA != NULL && COMBAT_CAMERA->Is_In_Cinematic()) camera_seen = true;
		for (SLNode<BaseGameObj> *node = GameObjManager::Get_Game_Obj_List()->Head();
			node != NULL; node = node->Next()) {
			PhysicalGameObj *object = node->Data()->As_PhysicalGameObj();
			if (object == NULL) continue;
			AnimControlClass *animation = object->Get_Anim_Control();
			if (animation != NULL && stricmp(animation->Get_Animation_Name(),
				"S_A_Human.H_A_X00_Havoc") == 0 && object->Is_Attached_To_An_Object()) {
				Vector3 position;
				object->Get_Position(&position);
				if (!rappel_seen) {
					rappel_first_frame = animation->Get_Current_Frame();
					rappel_first_z = position.Z;
					rappel_seen = true;
				}
				if (animation->Get_Current_Frame() > rappel_first_frame + 20.0F &&
					position.Z < rappel_first_z - 1.0F) rappel_advanced = true;
				if (frame % 30U == 0U) {
					std::printf("m13.rappel\t%u\t%d\t%.3f\t%.3f\n", frame,
						object->Get_ID(), animation->Get_Current_Frame(), position.Z);
				}
			}
			const GameObjObserverList &observers = object->Get_Observers();
			for (int i = 0; i < observers.Count(); ++i) {
				const char *name = observers[i] != NULL ? observers[i]->Get_Name() : NULL;
				if (name == NULL) continue;
				int engineer = strcmp(name, "MX0_Engineer1") == 0 ? 0 :
					(strcmp(name, "MX0_Engineer2") == 0 ? 1 : -1);
				if (engineer < 0) continue;
				engineers[engineer] = object->Get_ID();
				if (!object->Is_Attached_To_An_Object()) detached[engineer] = true;
				if (frame % 60U == 0U) {
					Vector3 position;
					object->Get_Position(&position);
					SoldierGameObj *soldier = object->As_SoldierGameObj();
					std::printf("m13.engineer\t%u\t%d\t%d\t%d\t%.3f\t%.3f\t%.3f\t%s\t%s\n",
						frame, engineer + 1, object->Get_ID(),
						object->Is_Attached_To_An_Object() ? 1 : 0,
						position.X, position.Y, position.Z,
						soldier != NULL ? soldier->Get_State_Name() : "not_soldier",
						animation != NULL ? animation->Get_Animation_Name() : "none");
				}
			}
		}
		if (frame % 600U == 0U) {
			std::printf("m13.intro_progress\t%u\t%u\n", frame, WW3D::Get_Sync_Time());
			std::fflush(stdout);
		}
	}

	bool Validate() const
	{
		bool engineers_alive = true;
		for (unsigned i = 0; i < 2U; ++i) {
			ScriptableGameObj *object = engineers[i] != 0 ?
				GameObjManager::Find_ScriptableGameObj(engineers[i]) : NULL;
			SoldierGameObj *soldier = object != NULL ? object->As_SoldierGameObj() : NULL;
			const bool alive = soldier != NULL && !soldier->Is_Dead() && !soldier->Is_Delete_Pending();
			std::printf("m13.engineer_result\t%u\t%d\t%d\t%d\n", i + 1,
				engineers[i], detached[i] ? 1 : 0, alive ? 1 : 0);
			engineers_alive = engineers_alive && alive && detached[i];
		}
		const bool camera_released = COMBAT_CAMERA != NULL && !COMBAT_CAMERA->Is_In_Cinematic();
		std::printf("m13.intro_result\tcamera_seen=%d\tcamera_released=%d\trappel_seen=%d\trappel_advanced=%d\n",
			camera_seen, camera_released, rappel_seen, rappel_advanced);
		return camera_seen && camera_released && rappel_advanced && engineers_alive;
	}
};
